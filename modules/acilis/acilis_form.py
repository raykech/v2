import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime

from core.db import veritabani_baglan
from core.services import fis_kaydet, fis_guncelle, aktif_yil_kontrolu
from ui.dialogs import ac_kart_dialog
from ui.widgets.lookup_widget import LookupWidget, LookupDialog
from ui.widgets.editable_treeview import EditableTreeview
from utils.formatters import CurrencyFormatter, parse_currency
from ui.dirty_guard import dirty_kur, anlik_yenile, iptal_onayla, yeni_fis_temel_sifirla


class AcilisFisiFormu(tk.Frame):
    """Kasa / Banka / Cari açılış fişleri için ortak çok satırlı form.

    Her satırda hesap seçilir, borç/alacak yönü ve tutar girilir.
    Fiş kaydedilirken karşı satır oluşturulmaz; sadece ilgili hesabın
    bakiyesini başlatır.
    """

    YON_BORC = "Borç"
    YON_ALACAK = "Alacak"

    # fis_turu -> (hesap_turu, tablo_adi, ad_kolonu)
    FIS_TURU_BILGILERI = {
        "Kasa Açılış Fişi": ("Kasa", "kasalar", "kasa_adi", "Kasa Seç"),
        "Banka Açılış Fişi": ("Banka", "banka_hesaplari", "hesap_adi", "Banka Hesabı Seç"),
        "Cari Açılış Fişi": ("Cari", "cariler", "unvan", "Cari Seç"),
    }

    def __init__(self, parent, main_app, view_container, fis_turu, fis_id=None, on_close=None):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.view_container = view_container
        self.fis_id = fis_id
        self.fis_turu = fis_turu
        self.on_close = on_close
        self.satir_sayaci = 0

        if fis_turu not in self.FIS_TURU_BILGILERI:
            raise ValueError(f"Desteklenmeyen açılış fişi türü: {fis_turu}")

        self.hesap_turu, self.tablo_adi, self.ad_kolonu, self.lookup_title = self.FIS_TURU_BILGILERI[fis_turu]
        self.kaynak_modul = {
            "Kasa": "Kasa",
            "Banka": "Banka",
            "Cari": "Cari",
        }[self.hesap_turu]

        self.hesap_dict = {}
        self.satirlar = {}

        self.create_widgets()
        self.verileri_yukle()
        if self.fis_id:
            self.load_fis_data()

        # U2: kaydedilmemiş değişiklik takibi (temiz anlık durum kaydı)
        dirty_kur(self, ["ent_tarih", "ent_fis_no", "ent_aciklama"], ("tree_satirlar",))

    # ---------------------------------------------------------------- UI
    def create_widgets(self):
        ust_frame = tk.Frame(self, bg="#f5f7fb")
        ust_frame.pack(fill="x", pady=10, padx=10)

        baslik_frame = tk.LabelFrame(ust_frame, text="Fiş Başlık Bilgileri", padx=10, pady=10, font=("Arial", 10, "bold"))
        baslik_frame.pack(fill="x")
        baslik_frame.grid_columnconfigure(1, weight=1)
        baslik_frame.grid_columnconfigure(3, weight=1)

        tk.Label(baslik_frame, text="Fiş Türü:").grid(row=0, column=0, sticky="w", pady=2)
        self.lbl_fis_turu = tk.Label(
            baslik_frame, text=self.fis_turu, font=("Arial", 10, "bold"),
            anchor="w", bg="white", relief="sunken", padx=5,
        )
        self.lbl_fis_turu.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Tarih:").grid(row=0, column=2, sticky="w", padx=(10, 0), pady=2)
        self.ent_tarih = DateEntry(baslik_frame, date_pattern="dd.mm.yyyy")
        self.ent_tarih.grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Fiş No:").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_fis_no = tk.Entry(baslik_frame)
        self.ent_fis_no.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Açıklama:").grid(row=1, column=2, sticky="w", padx=(10, 0), pady=2)
        self.ent_aciklama = tk.Entry(baslik_frame)
        self.ent_aciklama.grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        self.ent_tarih.bind("<Return>", lambda e: self.ent_fis_no.focus_set())
        self.ent_fis_no.bind("<Return>", lambda e: self.ent_aciklama.focus_set())
        self.ent_aciklama.bind("<Return>", lambda e: self.lookup_hesap.ent_display.focus_set())

        # --- Satır Girişi ---
        self.liste_frame = tk.LabelFrame(self, text="Açılış Satırları", padx=10, pady=10, font=("Arial", 10, "bold"))
        self.liste_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.entry_row_frame = tk.Frame(self.liste_frame)
        self.entry_row_frame.pack(fill="x", pady=(0, 10))

        self.lookup_hesap = LookupWidget(self.entry_row_frame)
        self.ent_yon = ttk.Combobox(
            self.entry_row_frame, state="readonly", width=10,
            values=[self.YON_BORC, self.YON_ALACAK],
        )
        self.ent_yon.set(self.YON_BORC)
        self.ent_satir_aciklama = tk.Entry(self.entry_row_frame)
        self.ent_tutar = tk.Entry(self.entry_row_frame, width=15, justify="right")
        CurrencyFormatter(self.ent_tutar)
        self.btn_satir_ekle = tk.Button(
            self.entry_row_frame, text="+", command=self.satir_ekle,
            font=("Arial", 9, "bold"), width=3,
        )

        tk.Label(self.entry_row_frame, text="Hesap Adı", anchor="w", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="ew")
        tk.Label(self.entry_row_frame, text="Yön", anchor="w", font=("Arial", 9, "bold")).grid(row=0, column=1, sticky="ew")
        tk.Label(self.entry_row_frame, text="Satır Açıklaması", anchor="w", font=("Arial", 9, "bold")).grid(row=0, column=2, sticky="ew")
        tk.Label(self.entry_row_frame, text="Tutar", anchor="w", font=("Arial", 9, "bold")).grid(row=0, column=3, sticky="ew")

        self.lookup_hesap.grid(row=1, column=0, sticky="ew", padx=(0, 2), pady=(2, 0))
        self.ent_yon.grid(row=1, column=1, sticky="ew", padx=(0, 2), pady=(2, 0))
        self.ent_satir_aciklama.grid(row=1, column=2, sticky="ew", padx=(0, 2), pady=(2, 0))
        self.ent_tutar.grid(row=1, column=3, sticky="ew", padx=(0, 2), pady=(2, 0))
        self.btn_satir_ekle.grid(row=1, column=4, sticky="ew", pady=(2, 0))

        self.entry_row_frame.grid_columnconfigure(0, weight=4, uniform="g")
        self.entry_row_frame.grid_columnconfigure(1, weight=1, uniform="g")
        self.entry_row_frame.grid_columnconfigure(2, weight=5, uniform="g")
        self.entry_row_frame.grid_columnconfigure(3, weight=2, uniform="g")

        self.lookup_hesap.ent_display.bind("<Return>", lambda e: self.ent_satir_aciklama.focus_set())
        self.ent_yon.bind("<<ComboboxSelected>>", lambda e: self.ent_satir_aciklama.focus_set())
        self.ent_satir_aciklama.bind("<Return>", lambda e: self.ent_tutar.focus_set())
        self.ent_tutar.bind("<Return>", lambda e: self.satir_ekle())

        # --- Satır Listesi (satır içi düzenlenebilir) ---
        self.tree_satirlar = EditableTreeview(
            self.liste_frame,
            column_config={
                "hesap_adi": {"type": "lookup", "open_dialog": self._satir_hesap_dialog_ac},
                "yon": {"type": "combobox", "values": [self.YON_BORC, self.YON_ALACAK]},
                "aciklama": {"type": "text"},
                "tutar": {"type": "number"},
            },
            on_edit=self.on_satir_edit,
            get_edit_value=self._satir_edit_degeri_al,
            columns=("hesap_adi", "yon", "aciklama", "tutar", "sil"),
            show="headings",
        )
        self.tree_satirlar.heading("hesap_adi", text="Hesap Adı")
        self.tree_satirlar.heading("yon", text="Yön")
        self.tree_satirlar.heading("aciklama", text="Satır Açıklaması")
        self.tree_satirlar.heading("tutar", text="Tutar", anchor="e")
        self.tree_satirlar.heading("sil", text="", anchor="center")

        self.tree_satirlar.column("hesap_adi", width=300)
        self.tree_satirlar.column("yon", width=80, anchor="center")
        self.tree_satirlar.column("aciklama", width=350)
        self.tree_satirlar.column("tutar", width=130, anchor="e")
        self.tree_satirlar.column("sil", width=30, anchor="center", stretch=False)

        vsb = ttk.Scrollbar(self.liste_frame, orient="vertical", command=self.tree_satirlar.yview)
        vsb.pack(side="right", fill="y")
        self.tree_satirlar.configure(yscrollcommand=vsb.set)
        self.tree_satirlar.pack(fill="both", expand=True)

        self.tree_satirlar.bind("<ButtonRelease-1>", self.on_tree_click)

        # --- Toplamlar ---
        toplamlar_frame = tk.Frame(self.liste_frame, bg="#e9ecef")
        toplamlar_frame.pack(fill="x", pady=(5, 0))
        toplamlar_frame.grid_columnconfigure(3, weight=1)

        tk.Label(toplamlar_frame, text="Borç Toplamı:", font=("Arial", 9, "bold"), bg="#e9ecef").grid(row=0, column=3, sticky="e", padx=5)
        self.lbl_borc_toplam = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 9), bg="#e9ecef", width=15, anchor="e")
        self.lbl_borc_toplam.grid(row=0, column=4, sticky="e")

        tk.Label(toplamlar_frame, text="Alacak Toplamı:", font=("Arial", 9, "bold"), bg="#e9ecef").grid(row=1, column=3, sticky="e", padx=5)
        self.lbl_alacak_toplam = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 9), bg="#e9ecef", width=15, anchor="e")
        self.lbl_alacak_toplam.grid(row=1, column=4, sticky="e")

        tk.Label(toplamlar_frame, text="Genel Toplam:", font=("Arial", 10, "bold"), bg="#e9ecef").grid(row=2, column=3, sticky="e", padx=5)
        self.lbl_genel_toplam = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 10, "bold"), bg="#e9ecef", width=15, anchor="e")
        self.lbl_genel_toplam.grid(row=2, column=4, sticky="e")

        # --- Alt Butonlar ---
        alt_buton_frame = tk.Frame(self, bg="#f5f7fb")
        alt_buton_frame.pack(fill="x", pady=(0, 10), padx=10, side="bottom")

        self.btn_kaydet = tk.Button(
            alt_buton_frame, text="Fişi Kaydet", command=self.fis_kaydet,
            bg="#198754", fg="white", font=("Arial", 11, "bold"), height=2, width=20,
        )
        self.btn_kaydet.pack(side="right")

        self.btn_kaydet_yeni = tk.Button(
            alt_buton_frame, text="Kaydet ve Yeni Fiş",
            command=lambda: self.fis_kaydet(yeni_fis=True),
            bg="#0d6efd", fg="white", font=("Arial", 11, "bold"), height=2, width=20,
        )
        self.btn_kaydet_yeni.pack(side="right", padx=10)

        self.btn_iptal = tk.Button(
            alt_buton_frame, text="İptal ve Geri Dön", command=self.iptal,
            bg="#6c757d", fg="white", font=("Arial", 11, "bold"), height=2, width=20,
        )
        self.btn_iptal.pack(side="right", padx=10)

    # ---------------------------------------------------------------- Veriler
    def verileri_yukle(self):
        firma_id = self.main_app.aktif_firma_id
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, {self.ad_kolonu} FROM {self.tablo_adi} WHERE durum=1 AND firma_id=?",
            (firma_id,),
        )
        self.hesap_dict = {row[1]: row[0] for row in cursor.fetchall()}
        conn.close()
        self.lookup_hesap.configure_lookup(
            title=self.lookup_title,
            data_dict=self.hesap_dict,
            on_new=lambda: self.yeni_kart_ekle(self.tablo_adi),
        )

    def yeni_kart_ekle(self, tablo_adi):
        sonuc = ac_kart_dialog(self, tablo_adi, firma_id=self.main_app.aktif_firma_id)
        if sonuc:
            self.verileri_yukle()
        return sonuc

    # ---------------------------------------------------------------- Satır işlemleri
    def _fmt(self, fiyat):
        return f"{fiyat:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def satir_ekle(self):
        hesap_id = self.lookup_hesap.get()
        hesap_adi = self.lookup_hesap.get_value()
        yon = self.ent_yon.get()
        aciklama = self.ent_satir_aciklama.get().strip()
        tutar = parse_currency(self.ent_tutar.get())

        if not hesap_id:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir hesap seçin.", parent=self)
            return
        if tutar <= 0:
            messagebox.showwarning("Geçersiz Tutar", "Lütfen 0'dan büyük bir tutar girin.", parent=self)
            return

        yeni_satir = {
            "hesap_turu": self.hesap_turu,
            "hesap_id": hesap_id,
            "hesap_adi": hesap_adi,
            "yon": yon,
            "tutar": tutar,
            "aciklama": aciklama,
        }

        self.satir_sayaci += 1
        item_id = f"satir_{self.satir_sayaci}"
        self.tree_satirlar.insert(
            "", "end", iid=item_id,
            values=(hesap_adi, yon, aciklama, self._fmt(tutar), "❌"),
        )
        self.satirlar[item_id] = yeni_satir

        self.temizle_giris_satiri()

    def temizle_giris_satiri(self):
        self.lookup_hesap.clear()
        self.ent_satir_aciklama.delete(0, tk.END)
        self.ent_tutar.delete(0, tk.END)
        self.ent_yon.set(self.YON_BORC)
        self.lookup_hesap.ent_display.focus_set()
        self.guncelle_toplamlari()

    def satir_sil(self, item_id_to_delete):
        if not item_id_to_delete:
            return
        try:
            self.tree_satirlar.delete(item_id_to_delete)
            del self.satirlar[item_id_to_delete]
        except KeyError:
            pass  # satır zaten listeden düşmüş — sessizce yoksay
        self.guncelle_toplamlari()

    def on_tree_click(self, event):
        region = self.tree_satirlar.identify("region", event.x, event.y)
        if region == "cell" and self.tree_satirlar.identify_column(event.x) == "#5":
            self.satir_sil(self.tree_satirlar.identify_row(event.y))

    # --------------------------------------------------------- Satır içi düzenleme
    def _satir_hesap_dialog_ac(self, iid):
        """Satırın hesap hücresi için gerçek lookup (ara + yeni kart) diyaloğunu açar."""
        dialog = LookupDialog(
            self,
            self.lookup_title,
            self.hesap_dict,
            on_new_item=self._satir_yeni_kart,
            on_edit_item=None,
            on_delete_item=None,
        )
        self.wait_window(dialog)
        if dialog.result:
            return dialog.result[1]  # seçilen hesap adı
        return None

    def _satir_yeni_kart(self):
        """Satır lookup diyaloğundan yeni hesap ekler; (id, ad) döndürür."""
        sonuc = ac_kart_dialog(self, self.tablo_adi, firma_id=self.main_app.aktif_firma_id)
        if sonuc:
            self.verileri_yukle()
        return sonuc

    def _satir_edit_degeri_al(self, iid, column):
        """Düzenlemeye açılan hücrenin başlangıç değerini döndürür."""
        satir = self.satirlar.get(iid)
        if satir is None:
            return ""
        if column == "hesap_adi":
            return satir.get('hesap_adi', '')
        if column == "yon":
            return satir.get('yon', '')
        if column == "aciklama":
            return satir.get('aciklama', '')
        if column == "tutar":
            return self._fmt(satir.get('tutar', 0))
        return ""

    def on_satir_edit(self, iid, column, value):
        """Satır içi düzenlemeden gelen değeri uygular. Geçerliyse True döner."""
        satir = self.satirlar.get(iid)
        if satir is None:
            return False

        if column == "hesap_adi":
            hesap_id = self.hesap_dict.get(value)
            if hesap_id is None:
                return False
            satir['hesap_id'] = hesap_id
            satir['hesap_adi'] = value
        elif column == "yon":
            if value not in (self.YON_BORC, self.YON_ALACAK):
                return False
            satir['yon'] = value
        elif column == "aciklama":
            satir['aciklama'] = value
        elif column == "tutar":
            try:
                val = float(value)
            except (TypeError, ValueError):
                return False
            if val <= 0:
                messagebox.showwarning("Geçersiz Tutar", "Tutar 0'dan büyük olmalıdır.", parent=self)
                return False
            satir['tutar'] = val
        else:
            return False

        self._satir_row_guncelle(iid, satir)
        self.guncelle_toplamlari()
        return True

    def _satir_row_guncelle(self, iid, satir):
        """Bir satırın görünümünü veriye göre yeniler."""
        if not self.tree_satirlar.exists(iid):
            return
        self.tree_satirlar.item(iid, values=(
            satir['hesap_adi'], satir['yon'], satir['aciklama'], self._fmt(satir['tutar']), "❌"
        ))

    def guncelle_toplamlari(self):
        borc = sum(s['tutar'] for s in self.satirlar.values() if s['yon'] == self.YON_BORC)
        alacak = sum(s['tutar'] for s in self.satirlar.values() if s['yon'] == self.YON_ALACAK)
        self.lbl_borc_toplam.config(text=self._fmt(borc))
        self.lbl_alacak_toplam.config(text=self._fmt(alacak))
        self.lbl_genel_toplam.config(text=self._fmt(borc + alacak))

    # ---------------------------------------------------------------- Kaydet
    def _satir_dik(self, s):
        tutar = s['tutar']
        if s['yon'] == self.YON_BORC:
            borc, alacak = tutar, 0
        else:
            borc, alacak = 0, tutar
        return {
            "hesap_turu": self.hesap_turu,
            "hesap_id": s['hesap_id'],
            "borc": borc,
            "alacak": alacak,
            "aciklama": s.get('aciklama', ''),
            "miktar": 1,
            "birim_fiyat": tutar,
            "kdv_oran": 0,
            "kdv_tutar": 0,
        }

    def fis_kaydet(self, yeni_fis=False):
        # Dönem dışı tarih engeli
        yil_hata = aktif_yil_kontrolu(self.ent_tarih.get_date(), self.main_app.aktif_yil)
        if yil_hata:
            messagebox.showwarning("Dönem Dışı Tarih", yil_hata, parent=self)
            return

        if not self.satirlar:
            messagebox.showwarning("Eksik Bilgi", "Fişe en az bir satır eklemelisiniz.", parent=self)
            return

        fis_satirlari = [self._satir_dik(s) for s in self.satirlar.values()]
        toplam = sum(s['tutar'] for s in self.satirlar.values())

        fis_baslik = {
            "tarih": self.ent_tarih.get_date().strftime("%Y-%m-%d"),
            "fis_turu": self.fis_turu,
            "fis_no": self.ent_fis_no.get().strip(),
            "aciklama": self.ent_aciklama.get().strip(),
            "toplam_tutar": toplam,
            "cari_id": None,
            "firma_id": self.main_app.aktif_firma_id,
            "yil": self.ent_tarih.get_date().year,
        }

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            if self.fis_id:
                fis_guncelle(cursor, self.fis_id, fis_baslik, fis_satirlari, kaynak_modul=self.kaynak_modul)
                mesaj = "Açılış fişi başarıyla güncellendi."
            else:
                fis_kaydet(cursor, fis_baslik, fis_satirlari, kaynak_modul=self.kaynak_modul)
                mesaj = "Açılış fişi başarıyla kaydedildi."
            conn.commit()
            if yeni_fis:
                self._yeni_fis_sifirla(mesaj)
            else:
                messagebox.showinfo("Başarılı", mesaj, parent=self)
                anlik_yenile(self)  # U2: kayıt temizlendi
                self.iptal()
            if self.view_container:
                self.view_container.yenile()
        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu:\n{e}", parent=self)
        finally:
            if conn:
                conn.close()

    # ---------------------------------------------------------------- Düzenleme
    def load_fis_data(self):
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("SELECT tarih, fis_no, aciklama FROM fisler WHERE id=? AND firma_id=?",
                           (self.fis_id, self.main_app.aktif_firma_id))
            baslik = cursor.fetchone()
            if not baslik:
                messagebox.showerror("Hata", "Fiş bulunamadı.", parent=self)
                self.iptal()
                return
            self.ent_tarih.set_date(datetime.strptime(baslik[0], "%Y-%m-%d").date())
            self.ent_fis_no.insert(0, baslik[1] or '')
            self.ent_aciklama.insert(0, baslik[2] or '')

            cursor.execute(
                "SELECT hesap_turu, hesap_id, borc, alacak, aciklama, miktar "
                "FROM fis_satirlari WHERE fis_id=?",
                (self.fis_id,),
            )
            satirlar = cursor.fetchall()
            conn.close()

            for hesap_turu, hesap_id, borc, alacak, aciklama, miktar in satirlar:
                tutar = (borc or 0) or (alacak or 0)
                yon = self.YON_BORC if (borc or 0) > 0 else self.YON_ALACAK
                hesap_adi = next(
                    (name for name, i in self.hesap_dict.items() if str(i) == str(hesap_id)),
                    "Bilinmeyen Hesap",
                )
                self.satir_sayaci += 1
                item_id = f"satir_{self.satir_sayaci}"
                self.tree_satirlar.insert(
                    "", "end", iid=item_id,
                    values=(hesap_adi, yon, aciklama, self._fmt(tutar), "❌"),
                )
                self.satirlar[item_id] = {
                    "hesap_turu": hesap_turu,
                    "hesap_id": hesap_id,
                    "hesap_adi": hesap_adi,
                    "yon": yon,
                    "tutar": tutar,
                    "aciklama": aciklama,
                }
            self.guncelle_toplamlari()
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Açılış fişi yüklenemedi: {e}", parent=self)
            self.iptal()

    # ---------------------------------------------------------------- Ortak
    def _yeni_fis_sifirla(self, basarili_mesaj=None):
        """U1: Kaydet ve Yeni Fiş — formu boş yeni fiş moduna alır (tarih korunur)."""
        yeni_fis_temel_sifirla(self)
        self.lookup_hesap.clear()
        self.ent_yon.set(self.YON_BORC)
        self.ent_satir_aciklama.delete(0, "end")
        self.ent_tutar.delete(0, "end")
        self.guncelle_toplamlari()
        anlik_yenile(self)
        if hasattr(self.main_app, "durum_yaz"):
            self.main_app.durum_yaz(basarili_mesaj or "Açılış fişi kaydedildi — yeni fiş için form hazır.")
        self.ent_fis_no.focus_set()

    def iptal(self):
        # U2: kirlilik varsa önce sorar
        if not iptal_onayla(self):
            return False
        self.pack_forget()
        if self.on_close:
            self.on_close()
        if self.view_container:
            self.view_container.pack(fill="both", expand=True)
        return True

    def yenile(self):
        if self.view_container:
            self.view_container.listele()
