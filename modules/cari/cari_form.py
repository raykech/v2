import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from core.db import veritabani_baglan
from core.services import fis_kaydet, fis_guncelle
from ui.dialogs import ac_kart_dialog
from ui.widgets.lookup_widget import LookupWidget
from utils.formatters import CurrencyFormatter, parse_currency


class CariFisiFormu(tk.Frame):
    """
    Cari fişi formu. Dinamik yapıdır; seçilen fiş türüne göre başlık alanları,
    giriş satırı ve kayıt mantığı değişir.

    Fiş Türleri:
    - Alacak Dekontu   : Ana cari ALACAKLI, alt satırlar Gider hizmet kartları BORÇLU
    - Borç Dekontu     : Ana cari BORÇLU, alt satırlar Gelir hizmet kartları ALACAKLI
    - Cari Ödeme       : Cariler BORÇLU, karşı taraf kasa/banka ALACAKLI
    - Cari Tahsilat    : Cariler ALACAKLI, karşı taraf kasa/banka BORÇLU
    - Cari Virman      : Satır bazlı borç/alacak, toplam borç == toplam alacak
    """

    YON_BORC = "Borç"
    YON_ALACAK = "Alacak"

    def __init__(self, parent, main_app, view_container, fis_turu, fis_id=None, on_close=None):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.view_container = view_container
        self.fis_id = fis_id
        self.fis_turu = fis_turu
        self.on_close = on_close
        self.duzenlenen_satir_id = None
        self.satir_sayaci = 0

        self.satirlar = {}
        self.cari_dict = {}
        self.hizmet_dict = {}
        self.kasa_dict = {}
        self.banka_dict = {}

        self.create_widgets()
        self.verileri_yukle()
        self.ayarla_form_yapisi()

        if self.fis_id:
            self.load_fis_data()

    # ---------------------------------------------------------------- UI
    def create_widgets(self):
        ust_frame = tk.Frame(self, bg="#f5f7fb")
        ust_frame.pack(fill="x", pady=10, padx=10)

        self.baslik_frame = tk.LabelFrame(
            ust_frame, text="Fiş Başlık Bilgileri", padx=10, pady=10, font=("Arial", 10, "bold"),
        )
        self.baslik_frame.pack(fill="x")

        self.baslik_frame.grid_columnconfigure(1, weight=1)
        self.baslik_frame.grid_columnconfigure(3, weight=1)

        tk.Label(self.baslik_frame, text="Fiş Türü:").grid(row=0, column=0, sticky="w", pady=2)
        self.lbl_fis_turu = tk.Label(
            self.baslik_frame, text=self.fis_turu, font=("Arial", 10, "bold"),
            anchor="w", bg="white", relief="sunken", padx=5,
        )
        self.lbl_fis_turu.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        tk.Label(self.baslik_frame, text="Tarih:").grid(row=0, column=2, sticky="w", padx=(10, 0), pady=2)
        self.ent_tarih = DateEntry(self.baslik_frame, date_pattern="dd.mm.yyyy")
        self.ent_tarih.grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        tk.Label(self.baslik_frame, text="Fiş No:").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_fis_no = tk.Entry(self.baslik_frame)
        self.ent_fis_no.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        tk.Label(self.baslik_frame, text="Açıklama:").grid(row=1, column=2, sticky="w", padx=(10, 0), pady=2)
        self.ent_aciklama = tk.Entry(self.baslik_frame)
        self.ent_aciklama.grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        # Dinamik başlık alanları
        self.baslik_dinamik_frame = tk.LabelFrame(
            ust_frame, text="İşlem Bilgileri", padx=10, pady=10, font=("Arial", 10, "bold"),
        )
        self.baslik_dinamik_frame.pack(fill="x", pady=(10, 0))

        self.liste_frame = tk.LabelFrame(
            self, text="Fiş Satırları", padx=10, pady=10, font=("Arial", 10, "bold"),
        )
        self.liste_frame.pack(fill="both", expand=True, padx=10, pady=10)

        alt_buton_frame = tk.Frame(self, bg="#f5f7fb")
        alt_buton_frame.pack(fill="x", pady=(0, 10), padx=10, side="bottom")

        self.btn_kaydet = tk.Button(
            alt_buton_frame, text="Fişi Kaydet", command=self.fis_kaydet,
            bg="#198754", fg="white", font=("Arial", 11, "bold"), height=2, width=20,
        )
        self.btn_kaydet.pack(side="right")

        self.btn_iptal = tk.Button(
            alt_buton_frame, text="İptal ve Geri Dön", command=self.iptal,
            bg="#6c757d", fg="white", font=("Arial", 11, "bold"), height=2, width=20,
        )
        self.btn_iptal.pack(side="right", padx=10)

        # Excel tarzı giriş satırı
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

        # Satır listesi
        self.tree_satirlar = ttk.Treeview(
            self.liste_frame,
            columns=("hesap_adi", "yon", "aciklama", "tutar", "sil"),
            show="headings",
        )
        self.tree_satirlar.heading("hesap_adi", text="Hesap Adı")
        self.tree_satirlar.heading("yon", text="Yön")
        self.tree_satirlar.heading("aciklama", text="Satır Açıklaması")
        self.tree_satirlar.heading("tutar", text="Tutar", anchor="e")
        self.tree_satirlar.heading("sil", text="", anchor="center")

        vsb = ttk.Scrollbar(self.liste_frame, orient="vertical", command=self.tree_satirlar.yview)
        vsb.pack(side="right", fill="y")
        self.tree_satirlar.configure(yscrollcommand=vsb.set)
        self.tree_satirlar.pack(fill="both", expand=True)

        self.tree_satirlar.bind("<Double-1>", self.satir_duzenle_icin_yukle)
        self.tree_satirlar.bind("<ButtonRelease-1>", self.on_tree_click)

        toplamlar_frame = tk.Frame(self.liste_frame, bg="#e9ecef")
        toplamlar_frame.pack(fill="x", pady=(5, 0))
        toplamlar_frame.grid_columnconfigure(3, weight=1)

        tk.Label(toplamlar_frame, text="Ara Toplam:", font=("Arial", 9, "bold"), bg="#e9ecef").grid(row=0, column=3, sticky="e", padx=5)
        self.lbl_ara_toplam = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 9), bg="#e9ecef", width=15, anchor="e")
        self.lbl_ara_toplam.grid(row=0, column=4, sticky="e")

        tk.Label(toplamlar_frame, text="Borç Toplamı:", font=("Arial", 9, "bold"), bg="#e9ecef").grid(row=1, column=3, sticky="e", padx=5)
        self.lbl_borc_toplam = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 9), bg="#e9ecef", width=15, anchor="e")
        self.lbl_borc_toplam.grid(row=1, column=4, sticky="e")

        tk.Label(toplamlar_frame, text="Alacak Toplamı:", font=("Arial", 9, "bold"), bg="#e9ecef").grid(row=2, column=3, sticky="e", padx=5)
        self.lbl_alacak_toplam = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 9), bg="#e9ecef", width=15, anchor="e")
        self.lbl_alacak_toplam.grid(row=2, column=4, sticky="e")

    def _fmt(self, fiyat):
        return f"{fiyat:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # ---------------------------------------------------------------- Veriler
    def verileri_yukle(self):
        firma_id = self.main_app.aktif_firma_id
        conn = veritabani_baglan()
        cursor = conn.cursor()

        cursor.execute("SELECT id, unvan FROM cariler WHERE durum=1 AND firma_id=?", (firma_id,))
        self.cari_dict = {row[1]: row[0] for row in cursor.fetchall()}

        cursor.execute(
            "SELECT id, kart_adi, tur FROM hizmet_kartlari WHERE durum=1 AND firma_id=?", (firma_id,),
        )
        self.hizmet_dict = {
            f"[{row[2]}] {row[1]}": {"id": row[0], "tur": row[2]} for row in cursor.fetchall()
        }

        cursor.execute("SELECT id, kasa_adi FROM kasalar WHERE durum=1 AND firma_id=?", (firma_id,))
        self.kasa_dict = {row[1]: row[0] for row in cursor.fetchall()}

        cursor.execute("SELECT id, hesap_adi FROM banka_hesaplari WHERE durum=1 AND firma_id=?", (firma_id,))
        self.banka_dict = {row[1]: row[0] for row in cursor.fetchall()}

        conn.close()

    # ---------------------------------------------------------------- Dinamik yapı
    def ayarla_form_yapisi(self):
        self._baslik_dinamik_olustur(self.fis_turu)
        self._giris_satirini_ayarla(self.fis_turu)
        self.guncelle_toplamlari()

    def _baslik_dinamik_olustur(self, fis_turu):
        for child in self.baslik_dinamik_frame.winfo_children():
            child.destroy()

        self.ana_cari_lookup = None
        self.odeme_turu_cmb = None
        self.odeme_hesap_lookup = None
        self.odeme_hesap_etiket = None

        if fis_turu in ("Alacak Dekontu", "Borç Dekontu"):
            etiket = "Alacaklı Cari" if fis_turu == "Alacak Dekontu" else "Borçlu Cari"
            self.baslik_dinamik_frame.grid_columnconfigure(1, weight=1)
            tk.Label(self.baslik_dinamik_frame, text=f"{etiket}:").grid(row=0, column=0, sticky="w")
            self.ana_cari_lookup = LookupWidget(self.baslik_dinamik_frame)
            self.ana_cari_lookup.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            self.ana_cari_lookup.configure_lookup(
                title="Cari Seç", data_dict=self.cari_dict,
                on_new=lambda: self.yeni_kart_ekle("cariler"),
            )
        elif fis_turu in ("Cari Ödeme", "Cari Tahsilat"):
            self.baslik_dinamik_frame.grid_columnconfigure(2, weight=1)
            tk.Label(self.baslik_dinamik_frame, text="Ödeme Türü:").grid(row=0, column=0, sticky="w")
            self.odeme_turu_cmb = ttk.Combobox(
                self.baslik_dinamik_frame, state="readonly", width=14, values=["Kasa", "Banka"],
            )
            self.odeme_turu_cmb.set("Kasa")
            self.odeme_turu_cmb.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            self.odeme_turu_cmb.bind("<<ComboboxSelected>>", lambda e: self._odeme_turu_degisti(kurulum=False))

            self.odeme_hesap_etiket = tk.Label(self.baslik_dinamik_frame, text="Kasa Hesabı:")
            self.odeme_hesap_etiket.grid(row=0, column=2, sticky="w", padx=(10, 0))
            self.odeme_hesap_lookup = LookupWidget(self.baslik_dinamik_frame)
            self.odeme_hesap_lookup.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
            self._odeme_turu_degisti(kurulum=True)
        elif fis_turu == "Cari Virman":
            tk.Label(
                self.baslik_dinamik_frame,
                text="Borçlu ve alacaklı carileri satır bazlı girin. Toplam borç = toplam alacak olmalıdır.",
                fg="#0d6efd",
            ).pack(anchor="w")

    def _odeme_turu_degisti(self, kurulum=True):
        if not self.odeme_turu_cmb or not self.odeme_hesap_lookup:
            return
        tur = self.odeme_turu_cmb.get()
        if tur == "Kasa":
            if self.odeme_hesap_etiket:
                self.odeme_hesap_etiket.config(text="Kasa Hesabı:")
            self.odeme_hesap_lookup.configure_lookup(
                title="Kasa Seç", data_dict=self.kasa_dict,
                on_new=lambda: self.yeni_kart_ekle("kasalar"),
            )
        else:
            if self.odeme_hesap_etiket:
                self.odeme_hesap_etiket.config(text="Banka Hesabı:")
            self.odeme_hesap_lookup.configure_lookup(
                title="Banka Hesabı Seç", data_dict=self.banka_dict, on_new=None,
            )
        if not kurulum:
            self.odeme_hesap_lookup.clear()

    def _giris_satirini_ayarla(self, fis_turu):
        self.lookup_hesap.clear()

        if fis_turu == "Alacak Dekontu":
            gider_kartlari = {k: v['id'] for k, v in self.hizmet_dict.items() if v['tur'] == 'Gider'}
            self.lookup_hesap.configure_lookup(
                title="Gider Kartı Seç", data_dict=gider_kartlari,
                on_new=lambda: self.yeni_kart_ekle("hizmet_kartlari", "Gider"),
            )
            self._yon_gorunur(False)
        elif fis_turu == "Borç Dekontu":
            gelir_kartlari = {k: v['id'] for k, v in self.hizmet_dict.items() if v['tur'] == 'Gelir'}
            self.lookup_hesap.configure_lookup(
                title="Gelir Kartı Seç", data_dict=gelir_kartlari,
                on_new=lambda: self.yeni_kart_ekle("hizmet_kartlari", "Gelir"),
            )
            self._yon_gorunur(False)
        elif fis_turu in ("Cari Ödeme", "Cari Tahsilat"):
            self.lookup_hesap.configure_lookup(
                title="Cari Seç", data_dict=self.cari_dict,
                on_new=lambda: self.yeni_kart_ekle("cariler"),
            )
            self._yon_gorunur(False)
        elif fis_turu == "Cari Virman":
            self.lookup_hesap.configure_lookup(
                title="Cari Seç", data_dict=self.cari_dict,
                on_new=lambda: self.yeni_kart_ekle("cariler"),
            )
            self._yon_gorunur(True)

    def _yon_gorunur(self, gorunur):
        if gorunur:
            self.ent_yon.grid()
        else:
            self.ent_yon.grid_remove()

    def yeni_kart_ekle(self, tablo_adi, kart_turu=None):
        ac_kart_dialog(self, tablo_adi, firma_id=self.main_app.aktif_firma_id, kart_turu=kart_turu)
        self.verileri_yukle()
        self.ayarla_form_yapisi()

    # ---------------------------------------------------------------- Satır işlemleri
    def satir_ekle(self):
        hesap_id = self.lookup_hesap.get()
        hesap_adi = self.lookup_hesap.get_value()
        aciklama = self.ent_satir_aciklama.get()
        tutar = parse_currency(self.ent_tutar.get())
        yon = self.ent_yon.get()

        if not hesap_id:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir hesap seçin.", parent=self)
            return
        if tutar <= 0:
            messagebox.showwarning("Geçersiz Tutar", "Lütfen 0'dan büyük bir tutar girin.", parent=self)
            return

        satir_yonu = yon if self.fis_turu == "Cari Virman" else self._satir_icin_yon()

        yeni_satir = {
            "hesap_turu": self._satir_icin_hesap_turu(),
            "hesap_id": hesap_id,
            "hesap_adi": hesap_adi,
            "yon": satir_yonu,
            "tutar": tutar,
            "aciklama": aciklama,
        }

        if self.duzenlenen_satir_id:
            try:
                self.satirlar[self.duzenlenen_satir_id] = yeni_satir
                self.tree_satirlar.item(
                    self.duzenlenen_satir_id,
                    values=(hesap_adi, satir_yonu, aciklama, self._fmt(tutar), "❌"),
                )
            except Exception:
                self.satir_sayaci += 1
                item_id = f"satir_{self.satir_sayaci}"
                self.tree_satirlar.insert(
                    "", "end", iid=item_id,
                    values=(hesap_adi, satir_yonu, aciklama, self._fmt(tutar), "❌"),
                )
                self.satirlar[item_id] = yeni_satir
            self.duzenlenen_satir_id = None
        else:
            self.satir_sayaci += 1
            item_id = f"satir_{self.satir_sayaci}"
            self.tree_satirlar.insert(
                "", "end", iid=item_id,
                values=(hesap_adi, satir_yonu, aciklama, self._fmt(tutar), "❌"),
            )
            self.satirlar[item_id] = yeni_satir

        self.temizle_giris_satiri()

    def _satir_icin_hesap_turu(self):
        if self.fis_turu in ("Alacak Dekontu", "Borç Dekontu"):
            return "Hizmet"
        return "Cari"

    def _satir_icin_yon(self):
        if self.fis_turu in ("Alacak Dekontu", "Cari Tahsilat"):
            return self.YON_ALACAK
        return self.YON_BORC

    def temizle_giris_satiri(self):
        self.lookup_hesap.clear()
        self.ent_satir_aciklama.delete(0, tk.END)
        self.ent_tutar.delete(0, tk.END)
        self.ent_yon.set(self.YON_BORC)
        self.lookup_hesap.ent_display.focus_set()
        self.duzenlenen_satir_id = None
        self.guncelle_toplamlari()

    def satir_sil(self, item_id_to_delete):
        if not item_id_to_delete:
            return
        try:
            self.tree_satirlar.delete(item_id_to_delete)
            del self.satirlar[item_id_to_delete]
        except KeyError:
            print(f"Satır {item_id_to_delete} bulunamadı.")
        self.guncelle_toplamlari()
        if self.duzenlenen_satir_id == item_id_to_delete:
            self.temizle_giris_satiri()

    def on_tree_click(self, event):
        region = self.tree_satirlar.identify("region", event.x, event.y)
        if region == "cell" and self.tree_satirlar.identify_column(event.x) == "#5":
            self.satir_sil(self.tree_satirlar.identify_row(event.y))

    def satir_duzenle_icin_yukle(self, event=None):
        selected_items = self.tree_satirlar.selection()
        if not selected_items:
            return
        selected_item = selected_items[0]
        try:
            self.duzenlenen_satir_id = selected_item
            satir = self.satirlar[selected_item]
            self.lookup_hesap.set(satir['hesap_id'])
            self.ent_yon.set(satir['yon'])
            self.ent_satir_aciklama.delete(0, tk.END)
            self.ent_satir_aciklama.insert(0, satir['aciklama'])
            self.ent_tutar.delete(0, tk.END)
            self.ent_tutar.insert(0, f"{satir['tutar']:.2f}".replace(".", ","))
            self.lookup_hesap.ent_display.focus_set()
        except (IndexError, KeyError) as e:
            print(f"Satır yükleme hatası: {e}")
            self.duzenlenen_satir_id = None

    def guncelle_toplamlari(self):
        borc = sum(s['tutar'] for s in self.satirlar.values() if s['yon'] == self.YON_BORC)
        alacak = sum(s['tutar'] for s in self.satirlar.values() if s['yon'] == self.YON_ALACAK)

        if self.fis_turu == "Cari Virman":
            self.lbl_ara_toplam.config(text=self._fmt(borc))
            self.lbl_borc_toplam.config(text=self._fmt(borc))
            self.lbl_alacak_toplam.config(text=self._fmt(alacak))
        else:
            ara_toplam = sum(s['tutar'] for s in self.satirlar.values())
            self.lbl_ara_toplam.config(text=self._fmt(ara_toplam))
            self.lbl_borc_toplam.config(text=self._fmt(ara_toplam))
            self.lbl_alacak_toplam.config(text=self._fmt(ara_toplam))

    # ---------------------------------------------------------------- Kaydet
    def fis_kaydet(self):
        if not self.satirlar:
            messagebox.showwarning("Eksik Bilgi", "Fişe en az bir satır eklemelisiniz.", parent=self)
            return

        fis_satirlari, toplam = self._olustur_fis_satirlari()
        if fis_satirlari is None:
            return

        fis_baslik = {
            "tarih": self.ent_tarih.get_date().strftime("%Y-%m-%d"),
            "fis_turu": self.fis_turu,
            "fis_no": self.ent_fis_no.get().strip(),
            "aciklama": self.ent_aciklama.get().strip(),
            "toplam_tutar": toplam,
            "cari_id": None,
            "firma_id": self.main_app.aktif_firma_id,
            "yil": self.main_app.aktif_yil,
        }

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            if self.fis_id:
                fis_guncelle(cursor, self.fis_id, fis_baslik, fis_satirlari, kaynak_modul='Cari')
                mesaj = "Cari fişi başarıyla güncellendi."
            else:
                fis_kaydet(cursor, fis_baslik, fis_satirlari, kaynak_modul='Cari')
                mesaj = "Cari fişi başarıyla kaydedildi."

            conn.commit()
            messagebox.showinfo("Başarılı", mesaj, parent=self)
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

    def _satir_dik(self, s, hesap_turu):
        tutar = s['tutar']
        if s['yon'] == self.YON_BORC:
            borc, alacak = tutar, 0
        else:
            borc, alacak = 0, tutar
        return {
            "hesap_turu": hesap_turu,
            "hesap_id": s['hesap_id'],
            "borc": borc,
            "alacak": alacak,
            "aciklama": s.get('aciklama', ''),
            "miktar": 1,
            "birim_fiyat": tutar,
            "kdv_oran": 0,
            "kdv_tutar": 0,
        }

    def _karsi_satir(self, hesap_turu, hesap_id, tutar, yon, aciklama):
        if yon == self.YON_BORC:
            borc, alacak = tutar, 0
        else:
            borc, alacak = 0, tutar
        return {
            "hesap_turu": hesap_turu,
            "hesap_id": hesap_id,
            "borc": borc,
            "alacak": alacak,
            "aciklama": aciklama,
            "miktar": 1,
            "birim_fiyat": tutar,
            "kdv_oran": 0,
            "kdv_tutar": 0,
        }

    def _olustur_fis_satirlari(self):
        """
        Türe göre fis_satirlari listesini üretir.
        Döner: (fis_satirlari, toplam) -- hata varsa (None, 0)
        """
        fis_turu = self.fis_turu

        # --- Cari Virman ---
        if fis_turu == "Cari Virman":
            borc_toplam = sum(s['tutar'] for s in self.satirlar.values() if s['yon'] == self.YON_BORC)
            alacak_toplam = sum(s['tutar'] for s in self.satirlar.values() if s['yon'] == self.YON_ALACAK)
            if abs(borc_toplam - alacak_toplam) > 0.005:
                messagebox.showwarning(
                    "Fiş Dengesiz",
                    f"Toplam borç ({self._fmt(borc_toplam)}) ile toplam alacak ({self._fmt(alacak_toplam)}) "
                    "eşit değil.\nFiş kaydedilemez.",
                    parent=self,
                )
                return None, 0

            satirlar = [self._satir_dik(s, "Cari") for s in self.satirlar.values()]
            return satirlar, borc_toplam

        # --- Alacak / Borç Dekontu ---
        if fis_turu in ("Alacak Dekontu", "Borç Dekontu"):
            ana_cari_id = self.ana_cari_lookup.get() if self.ana_cari_lookup else None
            if not ana_cari_id:
                messagebox.showwarning("Eksik Bilgi", "Lütfen ana cariyi seçin.", parent=self)
                return None, 0

            for s in self.satirlar.values():
                if s['hesap_id'] == ana_cari_id and s['hesap_turu'] == 'Cari':
                    messagebox.showwarning(
                        "Uyarı", "Ana cari, alt satırlarda tekrar seçilmemelidir.", parent=self,
                    )
                    return None, 0

            satirlar = []
            toplam = 0.0
            for s in self.satirlar.values():
                satirlar.append(self._satir_dik(s, "Hizmet"))
                toplam += s['tutar']

            if fis_turu == "Alacak Dekontu":
                ana_satir = self._karsi_satir("Cari", ana_cari_id, toplam, self.YON_ALACAK, "Alacak Dekontu")
            else:
                ana_satir = self._karsi_satir("Cari", ana_cari_id, toplam, self.YON_BORC, "Borç Dekontu")
            satirlar.append(ana_satir)
            return satirlar, toplam

        # --- Cari Ödeme / Tahsilat ---
        if fis_turu in ("Cari Ödeme", "Cari Tahsilat"):
            odeme_id = self.odeme_hesap_lookup.get() if self.odeme_hesap_lookup else None
            if not odeme_id:
                messagebox.showwarning("Eksik Bilgi", "Lütfen kasa/banka hesabı seçin.", parent=self)
                return None, 0
            odeme_turu = self.odeme_turu_cmb.get() if self.odeme_turu_cmb else "Kasa"
            hesap_turu = "Banka" if odeme_turu == "Banka" else "Kasa"

            for s in self.satirlar.values():
                if s['hesap_id'] == odeme_id and s['hesap_turu'] == hesap_turu:
                    messagebox.showwarning(
                        "Uyarı", "Ödeme kaynağı, alt satırlarda carilerle çakışmamalı.", parent=self,
                    )
                    return None, 0

            satirlar = []
            toplam = 0.0
            for s in self.satirlar.values():
                satirlar.append(self._satir_dik(s, "Cari"))
                toplam += s['tutar']

            if fis_turu == "Cari Ödeme":
                karsi = self._karsi_satir(hesap_turu, odeme_id, toplam, self.YON_ALACAK, "Cari Ödeme")
            else:
                karsi = self._karsi_satir(hesap_turu, odeme_id, toplam, self.YON_BORC, "Cari Tahsilat")
            satirlar.append(karsi)
            return satirlar, toplam

        messagebox.showwarning("Uyarı", f"Bilinmeyen fiş türü: {fis_turu}", parent=self)
        return None, 0

    # ---------------------------------------------------------------- Düzenleme
    def load_fis_data(self):
        """Mevcut bir cari fişini düzenlemek için alanları doldurur."""
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT tarih, fis_no, aciklama FROM fisler WHERE id=?", (self.fis_id,))
        data = cursor.fetchone()
        if not data:
            conn.close()
            return

        self.ent_tarih.set_date(datetime.strptime(data[0], "%Y-%m-%d").date())
        self.ent_fis_no.insert(0, data[1] or '')
        self.ent_aciklama.insert(0, data[2] or '')

        cursor.execute(
            "SELECT hesap_turu, hesap_id, borc, alacak, aciklama, miktar "
            "FROM fis_satirlari WHERE fis_id=?",
            (self.fis_id,),
        )
        satirlar = cursor.fetchall()
        conn.close()

        # Türe göre karşıt satırı ve normal satırları ayır
        karşıt_ayır = self._karsi_satiri_bul()
        karşi_satir = None
        normal_satirlar = []

        for hesap_turu, hesap_id, borc, alacak, aciklama, miktar in satirlar:
            satir = {
                "hesap_turu": hesap_turu,
                "hesap_id": hesap_id,
                "borc": borc,
                "alacak": alacak,
                "aciklama": aciklama,
            }
            # Karşıt satır hedefiyle eşleşiyorsa ayır
            if karşıt_ayır is not None and karşıt_ayır(hesap_turu, hesap_id):
                karşi_satir = satir
            else:
                normal_satirlar.append(satir)

        # Karşıt alanları doldur
        if self.fis_turu in ("Alacak Dekontu", "Borç Dekontu"):
            if karşi_satir:
                self.ana_cari_lookup.set(karşi_satir['hesap_id'])
        elif self.fis_turu in ("Cari Ödeme", "Cari Tahsilat"):
            if karşi_satir:
                tur = "Kasa" if karşi_satir['hesap_turu'] == "Kasa" else "Banka"
                self.odeme_turu_cmb.set(tur)
                self._odeme_turu_degisti(kurulum=False)
                self.odeme_hesap_lookup.set(karşi_satir['hesap_id'])

        # Normal satırları yükle
        for satir in normal_satirlar:
            hesap_id = satir['hesap_id']
            hesap_turu = satir['hesap_turu']
            tutar = (satir['borc'] or 0) or (satir['alacak'] or 0)
            yon = self.YON_BORC if (satir['borc'] or 0) > 0 else self.YON_ALACAK

            hesap_adi = self._hesap_adi_bul(hesap_turu, hesap_id)

            self.satir_sayaci += 1
            item_id = f"satir_{self.satir_sayaci}"
            self.tree_satirlar.insert(
                "", "end", iid=item_id,
                values=(hesap_adi, yon, satir['aciklama'], self._fmt(tutar), "❌"),
            )
            self.satirlar[item_id] = {
                "hesap_turu": hesap_turu,
                "hesap_id": hesap_id,
                "hesap_adi": hesap_adi,
                "yon": yon,
                "tutar": tutar,
                "aciklama": satir['aciklama'],
            }

        self.guncelle_toplamlari()

    def _karsi_satiri_bul(self):
        """Hangi satırın 'karşıt' (ana cari / ödeme kaynağı) olduğunu belirleyen fonksiyon döner."""
        if self.fis_turu in ("Alacak Dekontu", "Borç Dekontu"):
            return lambda ht, hid: ht == "Cari"
        if self.fis_turu in ("Cari Ödeme", "Cari Tahsilat"):
            return lambda ht, hid: ht in ("Kasa", "Banka")
        return None

    def _hesap_adi_bul(self, hesap_turu, hesap_id):
        if hesap_turu == "Cari":
            return next((name for name, i in self.cari_dict.items() if str(i) == str(hesap_id)), "Cari")
        if hesap_turu == "Hizmet":
            return next((name for name, v in self.hizmet_dict.items() if str(v['id']) == str(hesap_id)), "Hizmet")
        if hesap_turu == "Kasa":
            return next((name for name, i in self.kasa_dict.items() if str(i) == str(hesap_id)), "Kasa")
        if hesap_turu == "Banka":
            return next((name for name, i in self.banka_dict.items() if str(i) == str(hesap_id)), "Banka")
        return str(hesap_id)

    def iptal(self):
        self.pack_forget()
        if self.on_close:
            self.on_close()
        if self.view_container:
            self.view_container.pack(fill="both", expand=True)

    def yenile(self):
        """Görünüm/özet alanlarını günceller; form açıkken çağrılır."""
        if self.view_container:
            self.view_container.listele()




