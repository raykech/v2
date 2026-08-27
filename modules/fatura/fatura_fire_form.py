import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
import uuid
from core.db import veritabani_baglan
from core.services import fis_kaydet, fis_guncelle, aktif_yil_kontrolu
from utils.formatters import format_currency, parse_currency, CurrencyFormatter
from ui.widgets.lookup_widget import LookupWidget, LookupDialog
from ui.dialogs import ac_kart_dialog


class FaturaFireFormu(tk.Frame):
    def __init__(self, parent, main_app, list_view, fis_id=None, fis_turu="Fire Fişi", on_close=None):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.list_view = list_view
        self.fis_id = fis_id
        self.fis_turu = fis_turu
        self.on_close = on_close
        self.satirlar = {}
        self.stok_dict = {}
        self.gider_dict = {}
        self.gider_id = None  # Seçili gider kartı ID'si

        self.create_widgets()
        self.verileri_yukle()

        if self.fis_id:
            self.fis_verilerini_yukle()

    def create_widgets(self):
        # Ana Çerçeveler
        ust_frame = tk.Frame(self, bg="#f5f7fb")
        ust_frame.pack(fill="x", padx=10, pady=10)

        liste_frame = tk.LabelFrame(self, text="Fire Satırları", bg="#f5f7fb", padx=10, pady=10)
        liste_frame.pack(fill="both", expand=True, padx=10)

        alt_buton_frame = tk.Frame(self, bg="#f5f7fb")
        alt_buton_frame.pack(fill="x", padx=10, pady=10, side="bottom")

        # Üst Frame: Başlık Bilgileri
        baslik_frame = tk.LabelFrame(ust_frame, text="Fire Fişi Bilgileri", bg="#f5f7fb", padx=10, pady=10)
        baslik_frame.pack(side="left", fill="x", expand=True)
        baslik_frame.columnconfigure(1, weight=1)
        baslik_frame.columnconfigure(3, weight=1)

        tk.Label(baslik_frame, text="Fiş Türü:", bg="#f5f7fb").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_fis_turu = ttk.Entry(baslik_frame, font=("Arial", 10, "bold"))
        self.ent_fis_turu.insert(0, self.fis_turu)
        self.ent_fis_turu.config(state="readonly")
        self.ent_fis_turu.grid(row=0, column=1, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Tarih:", bg="#f5f7fb").grid(row=0, column=2, sticky="w", pady=2, padx=(10, 0))
        self.ent_tarih = DateEntry(baslik_frame, date_pattern="dd.mm.yyyy")
        self.ent_tarih.grid(row=0, column=3, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Fiş No:", bg="#f5f7fb").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_fis_no = tk.Entry(baslik_frame)
        self.ent_fis_no.grid(row=1, column=1, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Açıklama:", bg="#f5f7fb").grid(row=1, column=2, sticky="w", pady=2, padx=(10, 0))
        self.ent_aciklama = tk.Entry(baslik_frame)
        self.ent_aciklama.grid(row=1, column=3, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Fire Gider Kartı:", bg="#f5f7fb").grid(row=2, column=0, sticky="w", pady=2)
        self.lookup_gider = LookupWidget(baslik_frame)
        self.lookup_gider.grid(row=2, column=1, columnspan=3, pady=2, sticky="ew")

        # Satır giriş bölümü
        self.entry_row_frame = tk.Frame(liste_frame, bg="#f5f7fb")
        self.entry_row_frame.pack(fill="x", pady=(0, 10))

        # Başlıklar
        tk.Label(self.entry_row_frame, text="Stok Adı", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb").grid(row=0, column=0, sticky='ew')
        tk.Label(self.entry_row_frame, text="Açıklama", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb").grid(row=0, column=1, sticky='ew')
        tk.Label(self.entry_row_frame, text="Miktar", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb").grid(row=0, column=2, sticky='ew')
        tk.Label(self.entry_row_frame, text="Birim Fiyat", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb").grid(row=0, column=3, sticky='ew')
        tk.Label(self.entry_row_frame, text="Tutar", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb").grid(row=0, column=4, sticky='ew')

        # Giriş satırı widget'ları
        self.ent_stok = LookupWidget(self.entry_row_frame)
        self.ent_satir_aciklama = tk.Entry(self.entry_row_frame)
        self.ent_miktar = tk.Entry(self.entry_row_frame, width=10, justify='right')
        self.ent_birim_fiyat = tk.Entry(self.entry_row_frame, width=15, justify='right')
        self.lbl_satir_toplam = tk.Label(self.entry_row_frame, text="0,00", width=15, anchor='e', relief="sunken", bg="white", padx=2)
        self.btn_satir_ekle = tk.Button(self.entry_row_frame, text="+", command=self.satir_ekle, font=("Arial", 9, "bold"), width=3)

        # Yerleşim
        self.ent_stok.grid(row=1, column=0, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.ent_satir_aciklama.grid(row=1, column=1, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.ent_miktar.grid(row=1, column=2, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.ent_birim_fiyat.grid(row=1, column=3, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.lbl_satir_toplam.grid(row=1, column=4, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.btn_satir_ekle.grid(row=1, column=5, sticky='ew', pady=(2, 0), padx=(2, 0))

        # Sütun genişlikleri
        self.entry_row_frame.grid_columnconfigure(0, weight=4, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(1, weight=5, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(2, weight=1, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(3, weight=2, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(4, weight=2, uniform="group1")

        # Formatlayıcılar
        self.ent_miktar_formatter = CurrencyFormatter(self.ent_miktar, on_change_callback=self._satir_toplam_hesapla, decimal_places=4, trim_sifir=True)
        CurrencyFormatter(self.ent_birim_fiyat, on_change_callback=self._satir_toplam_hesapla)

        # Varsayılan
        self.ent_miktar.insert(0, "1,00")

        # Klavye navigasyonu
        self.ent_tarih.bind("<Return>", lambda e: self.ent_fis_no.focus_set())
        self.ent_fis_no.bind("<Return>", lambda e: self.ent_aciklama.focus_set())
        self.ent_aciklama.bind("<Return>", lambda e: self.lookup_gider.ent_display.focus_set())
        self.lookup_gider.ent_display.bind("<Return>", lambda e: self.ent_stok.ent_display.focus_set())
        self.ent_stok.ent_display.bind("<Return>", lambda e: self.ent_satir_aciklama.focus_set())
        self.ent_satir_aciklama.bind("<Return>", lambda e: self.ent_miktar.focus_set())
        self.ent_miktar.bind("<Return>", lambda e: self.ent_birim_fiyat.focus_set())
        self.ent_birim_fiyat.bind("<Return>", lambda e: self.satir_ekle())
        self.ent_miktar.bind("<FocusOut>", self._satir_toplam_hesapla)
        self.ent_birim_fiyat.bind("<FocusOut>", self._satir_toplam_hesapla)

        # Satır Listesi
        columns = ("stok_adi", "aciklama", "miktar", "birim", "birim_fiyat", "toplam_tutar", "sil")
        self.tree = ttk.Treeview(liste_frame, columns=columns, show="headings", height=10)
        self.tree.heading("stok_adi", text="Stok Adı")
        self.tree.heading("aciklama", text="Açıklama")
        self.tree.heading("miktar", text="Miktar", anchor="e")
        self.tree.heading("birim", text="Birim")
        self.tree.heading("birim_fiyat", text="Birim Fiyat", anchor="e")
        self.tree.heading("toplam_tutar", text="Tutar", anchor="e")
        self.tree.heading("sil", text="", anchor="center")

        self.tree.column("stok_adi", width=250)
        self.tree.column("aciklama", width=250)
        self.tree.column("miktar", width=80, anchor="e")
        self.tree.column("birim", width=60, anchor="center")
        self.tree.column("birim_fiyat", width=100, anchor="e")
        self.tree.column("toplam_tutar", width=100, anchor="e")
        self.tree.column("sil", width=30, anchor="center")

        vsb = ttk.Scrollbar(liste_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)

        # Toplamlar
        toplamlar_frame = tk.Frame(liste_frame, bg="#e9ecef")
        toplamlar_frame.pack(fill="x", pady=(5, 0))
        toplamlar_frame.grid_columnconfigure(1, weight=1)
        self.lbl_genel_toplam = self._create_toplam_etiketi(toplamlar_frame, "Genel Toplam:", 0, 0, True)

        # Alt Butonlar
        tk.Button(alt_buton_frame, text="Kaydet", command=self.kaydet, bg="#198754", fg="white", font=("Arial", 10, "bold"), width=15, height=2).pack(side="right", padx=(10, 0))
        tk.Button(alt_buton_frame, text="Kapat", command=self.kapat, bg="#6c757d", fg="white", font=("Arial", 10, "bold"), width=15, height=2).pack(side="right")

        # Seçili odak
        self.ent_tarih.focus_set()

    def _create_toplam_etiketi(self, parent, text, row, col, is_bold=False):
        font = ("Arial", 10, "bold") if is_bold else ("Arial", 9)
        tk.Label(parent, text=text, font=font, bg="#e9ecef").grid(row=row, column=col, sticky="e", padx=5)
        lbl = tk.Label(parent, text="0,00 TL", font=font, bg="#e9ecef", width=15, anchor="e")
        lbl.grid(row=row, column=col+1, sticky="e")
        return lbl

    def verileri_yukle(self):
        firma_id = self.main_app.aktif_firma_id
        conn = veritabani_baglan()
        cursor = conn.cursor()

        cursor.execute("SELECT id, stok_adi, birim FROM stoklar WHERE durum=1 AND firma_id=?", (firma_id,))
        self.stok_dict = {row[1]: {'id': row[0], 'birim': row[2]} for row in cursor.fetchall()}

        cursor.execute("SELECT id, kart_adi FROM hizmet_kartlari WHERE durum=1 AND tur='Gider' AND firma_id=?", (firma_id,))
        self.gider_dict = {row[1]: row[0] for row in cursor.fetchall()}

        conn.close()

        self.lookup_gider.configure_lookup(
            title="Fire Gider Kartı Seç",
            data_dict=self.gider_dict,
            on_new=lambda: self._yeni_gider_kart(),
        )

        self.ent_stok.configure_lookup(
            title="Stok Seç",
            data_dict={k: v['id'] for k, v in self.stok_dict.items()},
            on_new=lambda: self._yeni_stok(),
        )

    def _yeni_stok(self):
        sonuc = ac_kart_dialog(self, "stoklar", firma_id=self.main_app.aktif_firma_id)
        if sonuc:
            self.verileri_yukle()
        return sonuc

    def _yeni_gider_kart(self):
        sonuc = ac_kart_dialog(self, "hizmet_kartlari", firma_id=self.main_app.aktif_firma_id, kart_turu="Gider")
        if sonuc:
            self.verileri_yukle()
        return sonuc

    def _satir_toplam_hesapla(self, event=None):
        try:
            miktar = parse_currency(self.ent_miktar.get())
            birim_fiyat = parse_currency(self.ent_birim_fiyat.get())
            toplam = miktar * birim_fiyat
            self.lbl_satir_toplam.config(text=format_currency(toplam).replace(" TL", ""))
        except (ValueError, TypeError, ZeroDivisionError):
            self.lbl_satir_toplam.config(text="0,00")

    def satir_ekle(self):
        stok_adi = self.ent_stok.get_value()
        if not stok_adi:
            messagebox.showwarning("Uyarı", "Lütfen bir stok seçin.", parent=self)
            return

        try:
            miktar = parse_currency(self.ent_miktar.get())
            birim_fiyat = parse_currency(self.ent_birim_fiyat.get())
            if miktar <= 0 or birim_fiyat <= 0:
                raise ValueError("Miktar ve birim fiyat pozitif olmalı")
        except (ValueError, TypeError, ZeroDivisionError):
            messagebox.showwarning("Uyarı", "Lütfen geçerli miktar ve birim fiyat girin.", parent=self)
            return

        hesap_id = self.ent_stok.get()
        hesap_adi = self.ent_stok.get_value()
        aciklama = self.ent_satir_aciklama.get().strip()
        birim = self.stok_dict.get(hesap_adi, {}).get('birim', '')
        toplam_tutar = miktar * birim_fiyat

        satir_verisi = {
            'hesap_turu': 'Stok',
            'hesap_id': hesap_id,
            'stok_adi': hesap_adi,
            'aciklama': aciklama or f"Fire - {hesap_adi}",
            'miktar': miktar,
            'birim': birim,
            'birim_fiyat': birim_fiyat,
            'toplam_tutar': toplam_tutar,
            'kdv_oran': 0,  # Fire KDV'sizdir
            'borc': 0,      # Stok çıkışı → alacak
            'alacak': toplam_tutar,
        }

        satir_id = str(uuid.uuid4())
        self.satirlar[satir_id] = satir_verisi
        self.tree.insert("", "end", iid=satir_id, values=(
            hesap_adi, aciklama, f"{miktar:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."),
            birim, format_currency(birim_fiyat).replace(" TL", ""),
            format_currency(toplam_tutar).replace(" TL", ""), "❌"
        ))

        # Giriş satırını temizle
        self.ent_stok.clear()
        self.ent_satir_aciklama.delete(0, tk.END)
        self.ent_miktar.delete(0, tk.END)
        self.ent_miktar.insert(0, "1,00")
        self.ent_birim_fiyat.delete(0, tk.END)
        self._satir_toplam_hesapla()
        self.guncelle_toplamlari()
        self.ent_stok.ent_display.focus_set()

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#7":  # sil sütunu
                selected_item = self.tree.focus()
                if selected_item:
                    self.satir_sil(selected_item)

    def satir_sil(self, satir_id):
        if satir_id in self.satirlar:
            del self.satirlar[satir_id]
            self.tree.delete(satir_id)
            self.guncelle_toplamlari()

    def guncelle_toplamlari(self):
        genel_toplam = sum(s['toplam_tutar'] for s in self.satirlar.values())
        self.lbl_genel_toplam.config(text=format_currency(genel_toplam))

    def kaydet(self):
        gider_id = self.lookup_gider.get()
        if not gider_id:
            messagebox.showwarning("Uyarı", "Lütfen bir fire gider kartı seçin.", parent=self)
            return
        if not self.satirlar:
            messagebox.showwarning("Uyarı", "Lütfen en az bir stok satırı ekleyin.", parent=self)
            return

        # Dönem dışı tarih engeli
        yil_hata = aktif_yil_kontrolu(self.ent_tarih.get_date(), self.main_app.aktif_yil)
        if yil_hata:
            messagebox.showwarning("Dönem Dışı Tarih", yil_hata, parent=self)
            return

        genel_toplam = sum(s['toplam_tutar'] for s in self.satirlar.values())

        fis_data = {
            'tarih': self.ent_tarih.get_date().strftime("%Y-%m-%d"),
            'fis_turu': self.fis_turu,
            'fis_no': self.ent_fis_no.get().strip(),
            'aciklama': self.ent_aciklama.get().strip(),
            'cari_id': None,
            'toplam_tutar': genel_toplam,
            'firma_id': self.main_app.aktif_firma_id,
            'yil': self.ent_tarih.get_date().year,
        }

        # Stok satırları (alacak → stok çıkışı)
        fis_satirlari = list(self.satirlar.values())

        # Gider satırı (borç → fire gideri)
        gider_aciklama = self.ent_aciklama.get().strip() or "Fire kaybı"
        fis_satirlari.append({
            'hesap_turu': 'Hizmet',
            'hesap_id': gider_id,
            'borc': genel_toplam,
            'alacak': 0,
            'aciklama': gider_aciklama,
            'miktar': 1,
            'birim_fiyat': genel_toplam,
            'kdv_oran': 0,
        })

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            if self.fis_id:
                fis_guncelle(cursor, self.fis_id, fis_data, fis_satirlari, pesin_odeme_data=None, kaynak_modul='Fatura')
            else:
                fis_kaydet(cursor, fis_data, fis_satirlari, pesin_odeme_data=None, kaynak_modul='Fatura')
            conn.commit()
            messagebox.showinfo("Başarılı", "Fire fişi başarıyla kaydedildi.", parent=self)
            self.kapat()
        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu:\n{e}", parent=self)
        finally:
            if conn:
                conn.close()

    def fis_verilerini_yukle(self):
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fisler WHERE id=?", (self.fis_id,))
            fis_data = cursor.fetchone()
            if not fis_data:
                messagebox.showerror("Hata", "Fire fişi bulunamadı.", parent=self)
                self.kapat()
                return

            fis_cols = [desc[0] for desc in cursor.description]
            fis_dict = dict(zip(fis_cols, fis_data))

            self.ent_tarih.set_date(datetime.strptime(fis_dict['tarih'], "%Y-%m-%d"))
            self.ent_fis_no.insert(0, fis_dict.get('fis_no', ''))
            self.ent_aciklama.insert(0, fis_dict.get('aciklama', ''))

            # Gider kartını yükle
            cursor.execute(
                "SELECT hesap_id FROM fis_satirlari WHERE fis_id=? AND hesap_turu='Hizmet'",
                (self.fis_id,),
            )
            gider_row = cursor.fetchone()
            if gider_row:
                self.lookup_gider.set(gider_row[0])

            # Stok satırlarını yükle
            cursor.execute(
                """
                SELECT fs.*, s.stok_adi as hesap_adi, s.birim
                FROM fis_satirlari fs
                JOIN stoklar s ON fs.hesap_id = s.id
                WHERE fs.fis_id=? AND fs.hesap_turu='Stok'
                """,
                (self.fis_id,),
            )
            satir_cols = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                satir_dict = dict(zip(satir_cols, row))
                satir_id = str(uuid.uuid4())
                toplam_tutar = satir_dict['miktar'] * satir_dict['birim_fiyat']

                self.satirlar[satir_id] = {
                    'hesap_turu': 'Stok',
                    'hesap_id': satir_dict['hesap_id'],
                    'stok_adi': satir_dict['hesap_adi'],
                    'aciklama': satir_dict.get('aciklama', ''),
                    'miktar': satir_dict['miktar'],
                    'birim': satir_dict['birim'],
                    'birim_fiyat': satir_dict['birim_fiyat'],
                    'toplam_tutar': toplam_tutar,
                    'kdv_oran': satir_dict.get('kdv_oran', 0) or 0,
                    'borc': 0,
                    'alacak': toplam_tutar,
                }
                miktar_str = f"{satir_dict['miktar']:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                self.tree.insert("", "end", iid=satir_id, values=(
                    satir_dict['hesap_adi'], satir_dict.get('aciklama', ''), miktar_str, satir_dict['birim'],
                    format_currency(satir_dict['birim_fiyat']).replace(" TL", ""),
                    format_currency(toplam_tutar).replace(" TL", ""), "❌"
                ))

            self.guncelle_toplamlari()

        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Fire fişi verileri yüklenirken bir hata oluştu: {e}", parent=self)
        finally:
            if conn:
                conn.close()

    def kapat(self):
        self.destroy()
        self.list_view.pack(fill="both", expand=True)
        self.list_view.listele()
        if self.on_close:
            self.on_close()

    def yenile(self):
        self.verileri_yukle()