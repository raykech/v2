import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
import uuid
from core.db import veritabani_baglan
from core.services import fis_kaydet, fis_guncelle, kdv_satiri_olustur, aktif_yil_kontrolu
from utils.formatters import format_currency, parse_currency, CurrencyFormatter, format_miktar, kdv_hesapla
from utils.eksi_uyari import eksi_kontrol_ve_onayla
from ui.dirty_guard import dirty_kur, anlik_yenile, iptal_onayla, yeni_fis_temel_sifirla
from ui.widgets.lookup_widget import LookupWidget, LookupDialog
from ui.widgets.editable_treeview import EditableTreeview
from ui.dialogs import ac_kart_dialog

class FaturaFormu(tk.Frame):
    def __init__(self, parent, main_app, list_view, fis_id=None, fis_turu=None, on_close=None):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.list_view = list_view
        self.fis_id = fis_id
        self.fis_turu = fis_turu
        self.on_close = on_close
        self.is_hizmet_faturasi = "Hizmet" in self.fis_turu
        self.satirlar = {}
        self.cari_dict, self.stok_dict, self.hizmet_dict, self.kasa_dict, self.banka_dict, self.pos_dict = {}, {}, {}, {}, {}, {}
        
        self.create_widgets()
        self.verileri_yukle()
        self.ayarla_form_yapisi()
        
        # EN SON: Stok/Hizmet lookup widget'ını ayarla (configure_lookup'dan SONRA)
        self._setup_stok_lookup()
        
        if self.fis_id:
            self.fis_verilerini_yukle()

        # U2: kaydedilmemiş değişiklik takibi (temiz anlık durum kaydı)
        dirty_kur(self, ["ent_tarih", "ent_fis_no", "ent_aciklama",
                         "lookup_cari", "cmb_odeme_tipi", "lookup_odeme_hesap"], ("tree",))

    def create_widgets(self):
        # Ana Çerçeveler
        ust_frame = tk.Frame(self, bg="#f5f7fb")
        ust_frame.pack(fill="x", padx=10, pady=10)
        
        self.liste_frame = tk.LabelFrame(self, text="Fatura Satırları", bg="#f5f7fb", padx=10, pady=10)
        self.liste_frame.pack(fill="both", expand=True, padx=10)

        alt_buton_frame = tk.Frame(self, bg="#f5f7fb")
        alt_buton_frame.pack(fill="x", padx=10, pady=10, side="bottom")

        # Üst Frame: Başlık ve Ödeme Bilgileri
        baslik_frame = tk.LabelFrame(ust_frame, text="Fatura Bilgileri", bg="#f5f7fb", padx=10, pady=10)
        baslik_frame.pack(side="left", fill="x", expand=True)
        baslik_frame.columnconfigure(1, weight=1)
        baslik_frame.columnconfigure(3, weight=1)

        odeme_frame = tk.LabelFrame(ust_frame, text="Ödeme Bilgileri", bg="#f5f7fb", padx=10, pady=10)
        odeme_frame.pack(side="left", fill="x", padx=(10, 0))
        odeme_frame.columnconfigure(1, weight=1)

        # Başlık Bilgileri
        tk.Label(baslik_frame, text="Fatura Türü:", bg="#f5f7fb").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_fis_turu = ttk.Entry(baslik_frame, font=("Arial", 10, "bold"))
        self.ent_fis_turu.insert(0, self.fis_turu)
        self.ent_fis_turu.config(state="readonly")
        self.ent_fis_turu.grid(row=0, column=1, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Tarih:", bg="#f5f7fb").grid(row=0, column=2, sticky="w", pady=2, padx=(10,0))
        self.ent_tarih = DateEntry(baslik_frame, date_pattern="dd.mm.yyyy")
        self.ent_tarih.grid(row=0, column=3, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Fatura No:", bg="#f5f7fb").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_fis_no = tk.Entry(baslik_frame)
        self.ent_fis_no.grid(row=1, column=1, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Açıklama:", bg="#f5f7fb").grid(row=1, column=2, sticky="w", pady=2, padx=(10,0))
        self.ent_aciklama = tk.Entry(baslik_frame)
        self.ent_aciklama.grid(row=1, column=3, pady=2, sticky="ew")

        self.lbl_cari = tk.Label(baslik_frame, text="Cari Hesap:", bg="#f5f7fb")
        self.lbl_cari.grid(row=2, column=0, sticky="w", pady=2)
        self.lookup_cari = LookupWidget(baslik_frame)
        self.lookup_cari.grid(row=2, column=1, columnspan=3, pady=2, sticky="ew")

        # Ödeme Bilgileri
        tk.Label(odeme_frame, text="Ödeme Tipi:", bg="#f5f7fb").grid(row=0, column=0, sticky="w", pady=2)
        self.cmb_odeme_tipi = ttk.Combobox(odeme_frame, state="readonly", values=["Vadeli", "Nakit", "Banka", "POS"])
        self.cmb_odeme_tipi.grid(row=0, column=1, pady=2, sticky="ew")
        self.cmb_odeme_tipi.set("Vadeli")
        self.cmb_odeme_tipi.bind("<<ComboboxSelected>>", self.odeme_tipi_degisti)

        self.lbl_odeme_hesap = tk.Label(odeme_frame, text="Ödeme Hesabı:", bg="#f5f7fb")
        self.lookup_odeme_hesap = LookupWidget(odeme_frame)

        # --- KASA FORMUNDAN ALINAN SATIR GİRİŞ BÖLÜMÜ ---
        self.entry_row_frame = tk.Frame(self.liste_frame, bg="#f5f7fb")
        self.entry_row_frame.pack(fill="x", pady=(0, 10))
        
        # Başlıklar
        self.lbl_hesap_baslik = tk.Label(self.entry_row_frame, text="Stok Adı", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb")
        self.lbl_hesap_baslik.grid(row=0, column=0, sticky='ew')
        tk.Label(self.entry_row_frame, text="Satır Açıklaması", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb").grid(row=0, column=1, sticky='ew')
        self.lbl_miktar_baslik = tk.Label(self.entry_row_frame, text="Miktar", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb")
        self.lbl_miktar_baslik.grid(row=0, column=2, sticky='ew')
        self.lbl_birim_fiyat_baslik = tk.Label(self.entry_row_frame, text="Birim Fiyat", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb")
        self.lbl_birim_fiyat_baslik.grid(row=0, column=3, sticky='ew')
        tk.Label(self.entry_row_frame, text="KDV %", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb").grid(row=0, column=4, sticky='ew')
        tk.Label(self.entry_row_frame, text="Tutar (KDV Dahil)", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb").grid(row=0, column=5, sticky='ew')
        tk.Label(self.entry_row_frame, text="Satır Toplamı", anchor='w', font=("Arial", 9, "bold"), bg="#f5f7fb").grid(row=0, column=6, sticky='ew')

        # Giriş satırı widget'ları
        self.ent_stok = LookupWidget(self.entry_row_frame)
        self.ent_satir_aciklama = tk.Entry(self.entry_row_frame)
        self.ent_miktar = tk.Entry(self.entry_row_frame, width=10, justify='right')
        self.ent_birim_fiyat = tk.Entry(self.entry_row_frame, width=15, justify='right')
        self.ent_kdv_oran = tk.Entry(self.entry_row_frame, width=8, justify='right')
        self.ent_genel_tutar = tk.Entry(self.entry_row_frame, width=15, justify='right')
        self.lbl_satir_toplam = tk.Label(self.entry_row_frame, text="0,00", width=15, anchor='e', relief="sunken", bg="white", padx=2)
        self.btn_satir_ekle = tk.Button(self.entry_row_frame, text="+", command=self.satir_ekle, font=("Arial", 9, "bold"), width=3)

        # Giriş satırını başlıkların altına yerleştir
        self.ent_stok.grid(row=1, column=0, sticky='ew', padx=(0,2), pady=(2,0))
        self.ent_satir_aciklama.grid(row=1, column=1, sticky='ew', padx=(0,2), pady=(2,0))
        self.ent_miktar.grid(row=1, column=2, sticky='ew', padx=(0,2), pady=(2,0))
        self.ent_birim_fiyat.grid(row=1, column=3, sticky='ew', padx=(0,2), pady=(2,0))
        self.ent_kdv_oran.grid(row=1, column=4, sticky='ew', padx=(0,2), pady=(2,0))
        self.ent_genel_tutar.grid(row=1, column=5, sticky='ew', padx=(0,2), pady=(2,0))
        self.lbl_satir_toplam.grid(row=1, column=6, sticky='ew', padx=(0,2), pady=(2,0))
        self.btn_satir_ekle.grid(row=1, column=7, sticky='ew', pady=(2,0), padx=(2,0))

        # Sütun genişliklerini ayarla
        self.entry_row_frame.grid_columnconfigure(0, weight=4, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(1, weight=5, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(2, weight=1, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(3, weight=2, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(4, weight=1, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(5, weight=2, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(6, weight=2, uniform="group1")

        # 1. Formatlayıcıları oluştur
        self.ent_miktar_formatter = CurrencyFormatter(self.ent_miktar, on_change_callback=self.giris_satiri_hesapla, decimal_places=4, trim_sifir=True)
        self.ent_birim_fiyat_formatter = CurrencyFormatter(self.ent_birim_fiyat, on_change_callback=self.giris_satiri_hesapla)
        CurrencyFormatter(self.ent_kdv_oran, on_change_callback=self.giris_satiri_hesapla)
        CurrencyFormatter(self.ent_genel_tutar, on_change_callback=self.genel_tutardan_hesapla)

        # 2. Varsayılan değerleri ekle
        self.ent_miktar.insert(0, "1,00")
        self.ent_kdv_oran.insert(0, "20")

        # 3. Odaklanma davranışını en son ekle
        self._setup_select_on_focus([self.ent_stok.ent_display, self.ent_satir_aciklama, self.ent_miktar, self.ent_birim_fiyat, self.ent_kdv_oran, self.ent_genel_tutar])

        # Başlık Alanları Enter Navigasyonu
        self.ent_tarih.bind("<Return>", lambda e: self.ent_fis_no.focus_set())
        self.ent_fis_no.bind("<Return>", lambda e: self.ent_aciklama.focus_set())
        self.ent_aciklama.bind("<Return>", lambda e: self.lookup_cari.ent_display.focus_set())
        self.lookup_cari.ent_display.bind("<Return>", lambda e: self.ent_stok.ent_display.focus_set())

        # Enter ile ilerleme
        self.ent_stok.ent_display.bind("<Return>", lambda e: self.ent_satir_aciklama.focus_set())
        self.ent_satir_aciklama.bind("<Return>", lambda e: self.ent_miktar.focus_set())
        self.ent_miktar.bind("<Return>", lambda e: self.ent_birim_fiyat.focus_set())
        self.ent_birim_fiyat.bind("<Return>", lambda e: self.ent_kdv_oran.focus_set())
        self.ent_kdv_oran.bind("<Return>", lambda e: self.ent_genel_tutar.focus_set())
        self.ent_genel_tutar.bind("<Return>", lambda e: self.satir_ekle())

        # Satır Listesi (satır içi düzenlenebilir)
        self.tree = EditableTreeview(
            self.liste_frame,
            column_config={
                "stok_adi": {"type": "lookup", "open_dialog": self._satir_stok_dialog_ac},
                "aciklama": {"type": "text"},
                "miktar": {"type": "number"},
                "birim_fiyat": {"type": "number"},
                "kdv_oran": {"type": "number"},
                "toplam_tutar": {"type": "number"},
            },
            on_edit=self.on_satir_edit,
            get_edit_value=self._satir_edit_degeri_al,
            columns=("stok_adi", "aciklama", "miktar", "birim", "birim_fiyat", "kdv_oran", "kdv_tutar", "toplam_tutar", "sil"),
            show="headings",
        )
        self.tree.heading("stok_adi", text="Stok Adı")
        self.tree.heading("aciklama", text="Açıklama")
        self.tree.heading("miktar", text="Miktar", anchor="e")
        self.tree.heading("birim", text="Birim")
        self.tree.heading("birim_fiyat", text="Birim Fiyat", anchor="e")
        self.tree.heading("kdv_oran", text="KDV %", anchor="e")
        self.tree.heading("kdv_tutar", text="KDV Tutarı", anchor="e")
        self.tree.heading("toplam_tutar", text="Toplam Tutar", anchor="e")
        self.tree.heading("sil", text="", anchor="center")
        
        vsb = ttk.Scrollbar(self.liste_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)

        def _sync_widths(event=None):
            column_map = {"stok_adi": 0, "aciklama": 1, "miktar": 2, "birim_fiyat": 3, "toplam_tutar": 6}
            for col_name, i in column_map.items():
                try:
                    width = self.entry_row_frame.grid_bbox(i, 1)[2]
                    anchor = "e" if col_name not in ["stok_adi", "aciklama"] else "w"
                    self.tree.column(col_name, width=width, anchor=anchor)
                except (TypeError, IndexError): pass
            self.tree.column("aciklama", anchor="w")
            self.tree.column("birim", width=60, anchor="center", stretch=False)
            self.tree.column("kdv_oran", width=50, anchor="e", stretch=False)
            self.tree.column("kdv_tutar", width=100, anchor="e", stretch=False)
            self.tree.column("sil", width=30, anchor="center", stretch=False)
        
        self.entry_row_frame.bind("<Configure>", _sync_widths)
        self.after(100, _sync_widths)

        # Toplamlar Alanı
        toplamlar_frame = tk.Frame(self.liste_frame, bg="#e9ecef")
        toplamlar_frame.pack(fill="x", pady=(5,0))
        toplamlar_frame.grid_columnconfigure(1, weight=1)

        self.lbl_ara_toplam = self.create_toplam_etiketi(toplamlar_frame, "Ara Toplam:", 0, 2)
        self.lbl_kdv_toplam = self.create_toplam_etiketi(toplamlar_frame, "Toplam KDV:", 1, 2)
        self.lbl_genel_toplam = self.create_toplam_etiketi(toplamlar_frame, "Genel Toplam:", 2, 2, True)

        # Alt Butonlar
        tk.Button(alt_buton_frame, text="Kaydet", command=self.kaydet, bg="#198754", fg="white", font=("Arial", 10, "bold"), width=15, height=2).pack(side="right", padx=(10, 0))
        tk.Button(alt_buton_frame, text="Kaydet ve Yeni Fiş", command=lambda: self.kaydet(yeni_fis=True), bg="#0d6efd", fg="white", font=("Arial", 10, "bold"), width=15, height=2).pack(side="right", padx=(10, 0))
        tk.Button(alt_buton_frame, text="Kapat", command=self.kapat, bg="#6c757d", fg="white", font=("Arial", 10, "bold"), width=15, height=2).pack(side="right")

    def create_toplam_etiketi(self, parent, text, row, col, is_bold=False):
        font = ("Arial", 10, "bold") if is_bold else ("Arial", 9)
        tk.Label(parent, text=text, font=font, bg="#e9ecef").grid(row=row, column=col, sticky="e", padx=5)
        lbl = tk.Label(parent, text="0,00 TL", font=font, bg="#e9ecef", width=15, anchor="e")
        lbl.grid(row=row, column=col+1, sticky="e")
        return lbl

    def _setup_stok_lookup(self):
        """Stok/Hizmet lookup widget'ına KDV güncelleme özelliği ekler."""
        
        # StringVar kullanarak ent_display'i izle
        self._stok_var = tk.StringVar()
        self._stok_var.trace('w', self._on_stok_var_change)
        self.ent_stok.ent_display.config(textvariable=self._stok_var)
        
        # Set metodunu patch'le
        original_set = self.ent_stok.set
        
        def new_set(value):
            original_set(value)
            self._stok_var.set(self.ent_stok.get_value() or '')
            self.after(50, self._force_kdv_update)
            if self.ent_stok.get_value():
                self.ent_satir_aciklama.focus_set()
        
        self.ent_stok.set = new_set
        
        # Tüm olayları yakala
        self.ent_stok.ent_display.bind("<FocusOut>", lambda e: self.after(50, self._force_kdv_update), add='+')
        self.ent_stok.ent_display.bind("<KeyRelease>", self._on_stok_key_release, add='+')
        
        # Seçim butonuna tıklandığında
        if hasattr(self.ent_stok, 'btn_select'):
            self.ent_stok.btn_select.bind("<Button-1>", lambda e: self.after(300, self._force_kdv_update), add='+')
    
    def _on_stok_var_change(self, *args):
        """StringVar değiştiğinde KDV'yi güncelle."""
        self.after(50, self._force_kdv_update)
    
    def _on_stok_key_release(self, event):
        """Tuş bırakıldığında KDV'yi güncelle."""
        if event.keysym in ['Return', 'Tab', 'Down', 'Up']:
            self.after(50, self._force_kdv_update)

    def _force_kdv_update(self):
        """KDV güncellemesini zorla yapar."""
        self._on_hesap_select()
        # Eğer bir stok/hizmet seçiliyse, satır açıklamasına odaklan
        if self.ent_stok.get_value():
            self.ent_satir_aciklama.focus_set()

    def _setup_select_on_focus(self, widgets):
        """
        Verilen widget listesine, odaklanıldığında ve tıklandığında tüm metni seçme davranışını ekler.
        """
        def _select_all(event):
            widget = event.widget
            self.after(10, lambda: widget.select_range(0, 'end'))
            self.after(10, lambda: widget.icursor('end'))

        def _on_click(event):
            widget = event.widget
            self.after(10, lambda: widget.select_range(0, 'end'))

        for widget in widgets:
            widget.bind("<FocusIn>", _select_all, add='+')
            widget.bind("<Button-1>", _on_click, add='+')

    def _on_hesap_select(self, event=None):
        """Seçilen stok/hizmet kartına göre KDV oranını otomatik doldurur."""
        try:
            hesap_adi = self.ent_stok.get_value()
            hesap_id = self.ent_stok.get()
            
            if not hesap_adi and not hesap_id:
                return

            kdv_oran = 20  # Varsayılan
            hesap_bilgisi = None
            
            # 1. Önce ID ile dene
            if hesap_id:
                if self.is_hizmet_faturasi:
                    for key, value in self.hizmet_dict.items():
                        if value.get('id') == hesap_id:
                            hesap_bilgisi = value
                            break
                else:
                    for key, value in self.stok_dict.items():
                        if value.get('id') == hesap_id:
                            hesap_bilgisi = value
                            break
            
            # 2. ID ile bulunamazsa, ad ile dene
            if not hesap_bilgisi and hesap_adi:
                temiz_adi = hesap_adi
                if '] ' in hesap_adi:
                    temiz_adi = hesap_adi.split('] ', 1)[1]
                
                if self.is_hizmet_faturasi:
                    for key, value in self.hizmet_dict.items():
                        key_adi = key.split('] ', 1)[1] if '] ' in key else key
                        if key_adi == temiz_adi or key == hesap_adi:
                            hesap_bilgisi = value
                            break
                else:
                    for key, value in self.stok_dict.items():
                        if key == temiz_adi or key == hesap_adi:
                            hesap_bilgisi = value
                            break

            if hesap_bilgisi:
                kdv_oran_db = hesap_bilgisi.get('kdv_oran')
                if kdv_oran_db is not None:
                    kdv_oran = kdv_oran_db

            # KDV alanını güncelle
            self.ent_kdv_oran.delete(0, tk.END)
            self.ent_kdv_oran.insert(0, f"{kdv_oran:g}")
            self.giris_satiri_hesapla()

        except Exception as e:
            # U9: sessiz konsola düşmek yerine kullanıcıya görünür hata
            messagebox.showerror("Hesap Seçim Hatası", f"Hesap bilgisi alınamadı:\n{e}", parent=self)

    def ayarla_form_yapisi(self):
        if "Satış Faturası" in self.fis_turu:
            self.lbl_cari.config(text="Müşteri:")
        elif "Alış Faturası" in self.fis_turu:
            self.lbl_cari.config(text="Tedarikçi:")
        elif "Satış İade" in self.fis_turu:
            self.lbl_cari.config(text="Müşteri (İade):")
        elif "Alış İade" in self.fis_turu:
            self.lbl_cari.config(text="Tedarikçi (İade):")
        elif "Hizmet Satış" in self.fis_turu:
            self.lbl_cari.config(text="Müşteri:")
        elif "Hizmet Alış" in self.fis_turu:
            self.lbl_cari.config(text="Tedarikçi:")

        if self.is_hizmet_faturasi:
            self.lbl_hesap_baslik.config(text="Hizmet/Masraf Adı")
            self.tree.heading("stok_adi", text="Hizmet/Masraf Adı")
            # Hizmet faturalarında da Miktar × Birim Fiyat kullanılır (stokla tutarlı)
            self.lbl_miktar_baslik.grid()
            self.ent_miktar.grid()
            self.tree.column("miktar", width=80, stretch=False)
            self.tree.column("birim", width=0, stretch=False)
            is_gelir = "Satış" in self.fis_turu
            hizmet_filtreli = {k: v['id'] for k, v in self.hizmet_dict.items() if (is_gelir and v['tur'] == 'Gelir') or (not is_gelir and v['tur'] == 'Gider')}
            self.ent_stok.configure_lookup(title="Hizmet/Masraf Seç", data_dict=hizmet_filtreli, on_new=lambda: self.yeni_kart_ekle("hizmet_kartlari", "Gelir" if is_gelir else "Gider"))
        else:
            self.lbl_hesap_baslik.config(text="Stok Adı")
            self.tree.heading("stok_adi", text="Stok Adı")
            self.lbl_miktar_baslik.grid()
            self.ent_miktar.grid()
            self.tree.column("miktar", width=80, stretch=False)
            self.tree.column("birim", width=60, stretch=False)
            self.ent_stok.configure_lookup(title="Stok Seç", data_dict={k: v['id'] for k, v in self.stok_dict.items()}, on_new=lambda: self.yeni_kart_ekle("stoklar"))

    def verileri_yukle(self):
        conn = veritabani_baglan()
        cursor = conn.cursor()
        firma_id = self.main_app.aktif_firma_id
        
        cursor.execute("SELECT id, unvan FROM cariler WHERE durum=1 AND firma_id=?", (firma_id,))
        self.cari_dict = {row[1]: row[0] for row in cursor.fetchall()}
        self.lookup_cari.configure_lookup(title="Cari Hesap Seç", data_dict=self.cari_dict, on_new=lambda: self.yeni_kart_ekle("cariler"))

        cursor.execute("SELECT id, stok_adi, birim, kdv_oran FROM stoklar WHERE durum=1 AND firma_id=?", (firma_id,))
        self.stok_dict = {row[1]: {'id': row[0], 'birim': row[2], 'kdv_oran': row[3]} for row in cursor.fetchall()}

        cursor.execute("SELECT id, kart_adi, tur, kdv_oran FROM hizmet_kartlari WHERE durum=1 AND firma_id=?", (firma_id,))
        self.hizmet_dict = {f"[{row[2]}] {row[1]}": {'id': row[0], 'tur': row[2], 'kdv_oran': row[3]} for row in cursor.fetchall()}

        # KDV hesap ID'lerini bul (tur='KDV' olanlar: 191 İndirilecek / 391 Hesaplanan)
        self.indirilecek_kdv_id = None
        self.hesaplanan_kdv_id = None
        for key, val in self.hizmet_dict.items():
            if val["tur"] == "KDV":
                if "191" in key or "İndirilecek" in key:
                    self.indirilecek_kdv_id = val["id"]
                elif "391" in key or "Hesaplanan" in key:
                    self.hesaplanan_kdv_id = val["id"]

        cursor.execute("SELECT id, kasa_adi FROM kasalar WHERE durum=1 AND firma_id=?", (firma_id,))
        self.kasa_dict = {row[1]: row[0] for row in cursor.fetchall()}
        cursor.execute("SELECT id, hesap_adi FROM banka_hesaplari WHERE durum=1 AND hesap_turu='Vadesiz' AND firma_id=?", (firma_id,))
        self.banka_dict = {row[1]: row[0] for row in cursor.fetchall()}
        cursor.execute("SELECT id, hesap_adi FROM banka_hesaplari WHERE durum=1 AND hesap_turu='POS' AND firma_id=?", (firma_id,))
        self.pos_dict = {row[1]: row[0] for row in cursor.fetchall()}
        
        conn.close()
        self.odeme_tipi_degisti()

    def yeni_kart_ekle(self, tablo_adi, kart_turu=None):
        yeni_kart = ac_kart_dialog(self, tablo_adi, firma_id=self.main_app.aktif_firma_id, kart_turu=kart_turu)
        if yeni_kart: 
            self.verileri_yukle()
            # Yeni kart eklendikten sonra lookup'u tekrar ayarla
            self._setup_stok_lookup()
        return yeni_kart

    def odeme_tipi_degisti(self, event=None):
        tip = self.cmb_odeme_tipi.get()
        # Kullanıcı ödeme tipini değiştirdiğinde eski hesap seçimini sıfırla
        # (event None ise düzenleme yüklemesi/veri yenileme; seçim sonradan set edilir)
        if event is not None:
            self.lookup_odeme_hesap.clear()
            self.lookup_cari.clear()
        if tip == "Vadeli":
            self.lbl_odeme_hesap.grid_remove()
            self.lookup_odeme_hesap.grid_remove()
            self.lookup_cari.enable()
            self.lbl_cari.config(state="normal")
        else:
            self.lookup_cari.clear()
            self.lookup_cari.disable()
            self.lbl_cari.config(state="disabled")
            self.lbl_odeme_hesap.grid(row=1, column=0, sticky="w", pady=2)
            self.lookup_odeme_hesap.grid(row=1, column=1, pady=2, sticky="ew")
            if tip == "Nakit":
                self.lbl_odeme_hesap.config(text="Kasa Hesabı:")
                self.lookup_odeme_hesap.configure_lookup(title="Kasa Seç", data_dict=self.kasa_dict, on_new=lambda: self.yeni_kart_ekle("kasalar"))
            elif tip == "Banka":
                self.lbl_odeme_hesap.config(text="Banka Hesabı:")
                self.lookup_odeme_hesap.configure_lookup(title="Banka Hesabı Seç", data_dict=self.banka_dict, on_new=lambda: self.yeni_kart_ekle("banka_hesaplari"))
            elif tip == "POS":
                self.lbl_odeme_hesap.config(text="POS Hesabı:")
                self.lookup_odeme_hesap.configure_lookup(title="POS Hesabı Seç", data_dict=self.pos_dict, on_new=lambda: self.yeni_kart_ekle("banka_hesaplari"))

    def giris_satiri_hesapla(self, event=None):
        try:
            miktar = parse_currency(self.ent_miktar.get())
            birim_fiyat = parse_currency(self.ent_birim_fiyat.get())
            kdv_oran = parse_currency(self.ent_kdv_oran.get())

            # Akıllı giriş: "Tutar (KDV Dahil)" doluysa birim fiyatı ondan hesapla
            genel = parse_currency(self.ent_genel_tutar.get())
            if genel > 0 and miktar > 0:
                birim_fiyat = genel / (miktar * (1 + kdv_oran / 100))

            ara_toplam, kdv_tutar, toplam = kdv_hesapla(miktar, birim_fiyat, kdv_oran)
            self.lbl_satir_toplam.config(text=format_currency(toplam).replace(" TL", ""))
        except (ValueError, TypeError, ZeroDivisionError):
            self.lbl_satir_toplam.config(text="0,00")

    def genel_tutardan_hesapla(self, event=None):
        """'Tutar (KDV Dahil)' alanı değiştiğinde birim fiyatı geriye hesaplar."""
        try:
            genel = parse_currency(self.ent_genel_tutar.get())
            miktar = parse_currency(self.ent_miktar.get())
            kdv_oran = parse_currency(self.ent_kdv_oran.get())
            if genel > 0 and miktar > 0:
                birim_fiyat = genel / (miktar * (1 + kdv_oran / 100))
                self.ent_birim_fiyat.delete(0, tk.END)
                self.ent_birim_fiyat.insert(0, f"{birim_fiyat:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."))
            self.giris_satiri_hesapla()
        except (ValueError, TypeError, ZeroDivisionError):
            self.giris_satiri_hesapla()

    def satir_ekle(self):
        stok_adi = self.ent_stok.get_value()
        if not stok_adi: 
            messagebox.showwarning("Uyarı", f"Lütfen bir {'hizmet' if self.is_hizmet_faturasi else 'stok'} seçin.", parent=self)
            return
        
        try:
            miktar = parse_currency(self.ent_miktar.get())
            birim_fiyat = parse_currency(self.ent_birim_fiyat.get())
            kdv_oran = int(parse_currency(self.ent_kdv_oran.get()))
            if miktar <= 0: raise ValueError("Miktar pozitif olmalı")
            # Akıllı giriş: "Tutar (KDV Dahil)" doluysa birim fiyatı ondan hesapla
            genel_giris = parse_currency(self.ent_genel_tutar.get())
            if genel_giris > 0 and miktar > 0:
                birim_fiyat = genel_giris / (miktar * (1 + kdv_oran / 100))
        except (ValueError, TypeError, ZeroDivisionError):
            messagebox.showwarning("Uyarı", "Lütfen geçerli miktar, birim fiyat ve KDV oranı girin.", parent=self)
            return
        
        hesap_id = self.ent_stok.get()
        hesap_adi = self.ent_stok.get_value()
        aciklama = self.ent_satir_aciklama.get().strip()
        birim = ""
        if not self.is_hizmet_faturasi:
            birim = self.stok_dict[hesap_adi]['birim']

        ara_toplam, kdv_tutar, toplam_tutar = kdv_hesapla(miktar, birim_fiyat, kdv_oran)

        satir_verisi = {
            'hesap_turu': 'Hizmet' if self.is_hizmet_faturasi else 'Stok',
            'hesap_id': hesap_id, 'stok_adi': hesap_adi, 'aciklama': aciklama,
            'miktar': miktar, 'birim': birim, 'birim_fiyat': birim_fiyat,
            'kdv_oran': kdv_oran, 'kdv_tutar': kdv_tutar, 'toplam_tutar': toplam_tutar
        }

        # İade faturaları için borç/alacak mantığını tersine çevir
        # "Satış" kök kelimesi: Satış Faturası, Satış İade Faturası, Hizmet Satış Faturası
        is_satis = "Satış" in self.fis_turu
        is_iade = "İade" in self.fis_turu
        # Satır yönü: Satış → alacaklı; Alış → borçlu; Satış İade → borçlu; Alış İade → alacaklı
        satir_borclu = (is_satis and is_iade) or (not is_satis and not is_iade)
        # Satır tutarı NET'tir (KDV hariç); KDV ayrı bir satır olarak kaydedilir (191/391)
        if not satir_borclu:
            satir_verisi['borc'] = 0
            satir_verisi['alacak'] = ara_toplam
        else:
            satir_verisi['borc'] = ara_toplam
            satir_verisi['alacak'] = 0

        if not satir_verisi['aciklama']: 
            satir_verisi['aciklama'] = f"{hesap_adi} - {self.fis_turu}"

        satir_id = str(uuid.uuid4())
        self.satirlar[satir_id] = satir_verisi
        self.tree.insert("", "end", iid=satir_id, values=(
            hesap_adi, aciklama, format_miktar(miktar), birim,
            format_currency(birim_fiyat), f"{kdv_oran:g}", format_currency(kdv_tutar), format_currency(toplam_tutar), "❌"
        ))

        self.giris_satirini_temizle()
        self.guncelle_toplamlari()

    # --------------------------------------------------------- Satır içi düzenleme
    def _satir_stok_dialog_ac(self, iid):
        """Satırın stok/hizmet hücresi için gerçek lookup (ara + yeni kart) diyaloğunu açar."""
        if self.is_hizmet_faturasi:
            is_gelir = "Satış" in self.fis_turu
            data_dict = {k: v['id'] for k, v in self.hizmet_dict.items()
                         if (is_gelir and v['tur'] == 'Gelir') or (not is_gelir and v['tur'] == 'Gider')}
            dialog = LookupDialog(
                self, "Hizmet/Masraf Seç", data_dict,
                on_new_item=lambda: self.yeni_kart_ekle("hizmet_kartlari", "Gelir" if is_gelir else "Gider"),
                on_edit_item=None, on_delete_item=None,
            )
            self.wait_window(dialog)
            return dialog.result[1] if dialog.result else None
        else:
            data_dict = {k: v['id'] for k, v in self.stok_dict.items()}
            dialog = LookupDialog(
                self, "Stok Seç", data_dict,
                on_new_item=lambda: self.yeni_kart_ekle("stoklar"),
                on_edit_item=None, on_delete_item=None,
            )
            self.wait_window(dialog)
            return dialog.result[1] if dialog.result else None

    def _satir_edit_degeri_al(self, iid, column):
        """Düzenlemeye açılan hücrenin başlangıç değerini döndürür."""
        satir = self.satirlar.get(iid)
        if satir is None:
            return ""
        if column == "stok_adi":
            return satir.get('stok_adi', '')
        if column == "aciklama":
            return satir.get('aciklama', '')
        if column == "miktar":
            return format_miktar(satir.get('miktar', 1))
        if column == "birim_fiyat":
            return format_currency(satir.get('birim_fiyat', 0)).replace(" TL", "")
        if column == "kdv_oran":
            return f"{satir.get('kdv_oran', 0):g}"
        if column == "toplam_tutar":
            return format_currency(satir.get('toplam_tutar', 0)).replace(" TL", "")
        return ""

    def _satir_row_guncelle(self, iid, satir):
        """Bir satırın görünümünü veriye göre yeniler."""
        if not self.tree.exists(iid):
            return
        self.tree.item(iid, values=(
            satir['stok_adi'], satir.get('aciklama', ''), format_miktar(satir['miktar']), satir.get('birim', ''),
            format_currency(satir['birim_fiyat']), f"{satir['kdv_oran']:g}",
            format_currency(satir['kdv_tutar']), format_currency(satir['toplam_tutar']), "❌"
        ))

    def on_satir_edit(self, iid, column, value):
        """Satır içi düzenlemeden gelen değeri uygular. Geçerliyse True döner."""
        satir = self.satirlar.get(iid)
        if satir is None:
            return False

        if column == "stok_adi":
            if self.is_hizmet_faturasi:
                bilgi = self.hizmet_dict.get(value)
                if not bilgi:
                    return False
                satir['hesap_id'] = bilgi['id']
                satir['hesap_turu'] = 'Hizmet'
                kdv = bilgi.get('kdv_oran')
                if kdv is not None:
                    satir['kdv_oran'] = kdv
            else:
                bilgi = self.stok_dict.get(value)
                if not bilgi:
                    return False
                satir['hesap_id'] = bilgi['id']
                satir['hesap_turu'] = 'Stok'
                satir['birim'] = bilgi.get('birim', '')
                kdv = bilgi.get('kdv_oran')
                if kdv is not None:
                    satir['kdv_oran'] = kdv
            satir['stok_adi'] = value
        elif column == "aciklama":
            satir['aciklama'] = value
        elif column == "toplam_tutar":
            # KDV dahil toplam girilir; birim fiyat geriye hesaplanır (üst satırdaki akışla aynı)
            try:
                val = float(value)
            except (TypeError, ValueError):
                return False
            if val <= 0:
                messagebox.showwarning("Geçersiz Değer", "Toplam 0'dan büyük olmalıdır.", parent=self)
                return False
            payda = satir['miktar'] * (1 + satir['kdv_oran'] / 100)
            if payda <= 0:
                return False
            satir['birim_fiyat'] = val / payda
        elif column in ("miktar", "birim_fiyat", "kdv_oran"):
            try:
                val = float(value)
            except (TypeError, ValueError):
                return False
            if column == "miktar" and val <= 0:
                messagebox.showwarning("Geçersiz Değer", "Miktar 0'dan büyük olmalıdır.", parent=self)
                return False
            if column == "birim_fiyat" and val <= 0:
                messagebox.showwarning("Geçersiz Değer", "Birim Fiyat 0'dan büyük olmalıdır.", parent=self)
                return False
            if column == "kdv_oran" and val < 0:
                messagebox.showwarning("Geçersiz Değer", "KDV oranı negatif olamaz.", parent=self)
                return False
            satir[column] = val
        else:
            return False

        # Tutarları yeniden hesapla (2 ondalık, ticari yuvarlama)
        ara_toplam, kdv_tutar, toplam_tutar = kdv_hesapla(satir['miktar'], satir['birim_fiyat'], satir['kdv_oran'])
        satir['kdv_tutar'] = kdv_tutar
        satir['toplam_tutar'] = toplam_tutar
        # Satır yönüne göre borç/alacak (satir_ekle ile aynı mantık)
        is_satis = "Satış" in self.fis_turu
        is_iade = "İade" in self.fis_turu
        satir_borclu = (is_satis and is_iade) or (not is_satis and not is_iade)
        if not satir_borclu:
            satir['borc'] = 0
            satir['alacak'] = ara_toplam
        else:
            satir['borc'] = ara_toplam
            satir['alacak'] = 0

        self._satir_row_guncelle(iid, satir)
        self.guncelle_toplamlari()
        return True

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#9":
                selected_item = self.tree.focus()
                if selected_item: self.satir_sil(selected_item)

    def satir_sil(self, satir_id):
        if satir_id in self.satirlar:
            del self.satirlar[satir_id]
            self.tree.delete(satir_id)
            self.guncelle_toplamlari()

    def giris_satirini_temizle(self):
        self.ent_stok.clear()
        self.ent_satir_aciklama.delete(0, tk.END)
        self.ent_miktar.delete(0, tk.END)
        self.ent_miktar.insert(0, "1,00")
        self.ent_birim_fiyat.delete(0, tk.END)
        self.ent_kdv_oran.delete(0, tk.END)
        self.ent_kdv_oran.insert(0, "20")
        self.ent_genel_tutar.delete(0, tk.END)
        self.giris_satiri_hesapla()
        self.ent_stok.ent_display.focus_set()

    def guncelle_toplamlari(self):
        kdv_toplam = sum(s['kdv_tutar'] for s in self.satirlar.values())
        genel_toplam = sum(s['toplam_tutar'] for s in self.satirlar.values())
        ara_toplam = genel_toplam - kdv_toplam
        self.lbl_ara_toplam.config(text=format_currency(ara_toplam))
        self.lbl_kdv_toplam.config(text=format_currency(kdv_toplam))
        self.lbl_genel_toplam.config(text=format_currency(genel_toplam))

    def kaydet(self, yeni_fis=False):
        cari_id = self.lookup_cari.get()
        odeme_tipi = self.cmb_odeme_tipi.get()

        # Dönem dışı tarih engeli: fiş, seçili yıl dışında bir tarihe yazılamaz
        yil_hata = aktif_yil_kontrolu(self.ent_tarih.get_date(), self.main_app.aktif_yil)
        if yil_hata:
            messagebox.showwarning("Dönem Dışı Tarih", yil_hata, parent=self)
            return

        if odeme_tipi == "Vadeli" and not cari_id: 
            messagebox.showwarning("Uyarı", "Vadeli işlem için lütfen bir cari hesap seçin.", parent=self)
            return
        if not self.satirlar: 
            messagebox.showwarning("Uyarı", "Lütfen faturaya en az bir satır ekleyin.", parent=self)
            return

        genel_toplam = sum(s['toplam_tutar'] for s in self.satirlar.values())
        
        fis_data = {
            'tarih': self.ent_tarih.get_date().strftime("%Y-%m-%d"),
            'fis_turu': self.fis_turu,
            'fis_no': self.ent_fis_no.get().strip(),
            'aciklama': self.ent_aciklama.get().strip(),
            'cari_id': cari_id,
            'toplam_tutar': genel_toplam,
            'firma_id': self.main_app.aktif_firma_id,
            'yil': self.ent_tarih.get_date().year
        }

                # Fatura satırlarını hazırla
        fis_satirlari = list(self.satirlar.values())

        # KDV ayrı satırlarını ekle (191 İndirilecek KDV / 391 Hesaplanan KDV)
        # Her satırın KDV'si, satır ile aynı yönde ayrı bir satır olarak kaydedilir
        kdv_eklenecek_satirlar = []
        for satir in self.satirlar.values():
            kdv_tutar = satir.get('kdv_tutar', 0)
            if kdv_tutar:
                line_borclu = satir.get('borc', 0) > 0
                kdv_hesap_id = self.indirilecek_kdv_id if line_borclu else self.hesaplanan_kdv_id
                if not kdv_hesap_id:
                    messagebox.showerror(
                        "KDV Kartı Eksik",
                        f"Bu {self.fis_turu} fişinde KDV var ancak "
                        f"{'191 İndirilecek' if line_borclu else '391 Hesaplanan'} KDV kartı tanımlı değil.\n\n"
                        "Kartlar bölümünden türü 'KDV' olan ilgili kartı tanımlayın (fiş dengesiz kaydedilemez).",
                        parent=self)
                    return
                kdv_satiri = kdv_satiri_olustur(
                    kdv_hesap_id, kdv_tutar,
                    yon='borc' if line_borclu else 'alacak',
                    aciklama=f"{'191 İndirilecek' if line_borclu else '391 Hesaplanan'} KDV - {satir.get('aciklama', '')}"
                )
                if kdv_satiri:
                    kdv_eklenecek_satirlar.append(kdv_satiri)
        fis_satirlari = fis_satirlari + kdv_eklenecek_satirlar

        # Vadeli faturada cari karşılık satırını ekle
        if odeme_tipi == "Vadeli" and cari_id:
            # Satış faturası: cari borçlanır (müşteri bize borçlanır)
            # Alış faturası: cari alacaklanır (biz tedarikçiye borçlanırız)
            # Satış İade: cari alacaklanır (müşteriye iade ederiz)
            # Alış İade: cari borçlanır (tedarikçi bize borçlanır)
            is_satis = "Satış" in self.fis_turu
            is_iade = ("İade" in self.fis_turu)

            # Satış (iade değilse) → cari borçlu
            # Alış iade → cari borçlu
            cari_borclu = (is_satis and not is_iade) or (not is_satis and is_iade)
            
            fis_satirlari.append({
                'hesap_turu': 'Cari',
                'hesap_id': cari_id,
                'borc': genel_toplam if cari_borclu else 0,
                'alacak': 0 if cari_borclu else genel_toplam,
                'aciklama': f"{self.fis_turu} cari karşılığı",
                'miktar': None,
                'birim_fiyat': None,
                'kdv_oran': None,
                'kdv_tutar': None,
            })

        pesin_odeme_data = None
        if odeme_tipi != "Vadeli":
            odeme_hesap_id = self.lookup_odeme_hesap.get()
            if not odeme_hesap_id: 
                messagebox.showwarning("Uyarı", f"Lütfen bir {odeme_tipi} hesabı seçin.", parent=self)
                return
            
            odeme_hesap_turu_map = {"Nakit": "Kasa", "Banka": "Banka", "POS": "Banka"}
            odeme_hesap_turu = odeme_hesap_turu_map[odeme_tipi]
            
            # Tahsilat: Satış (iade değil) veya Alış İade; Ödeme: Alış (iade değil) veya Satış İade
            is_satis = "Satış" in self.fis_turu
            is_iade = "İade" in self.fis_turu
            is_tahsilat = (is_satis and not is_iade) or (not is_satis and is_iade)
            odeme_fis_turu = f"Fatura Peşin Tahsilat ({odeme_tipi})" if is_tahsilat else f"Fatura Peşin Ödeme ({odeme_tipi})"

            pesin_odeme_data = {
                'tarih': fis_data['tarih'], 'fis_turu': odeme_fis_turu, 'toplam_tutar': genel_toplam,
                'kaynak_modul': 'Fatura', 'aciklama': f"Fatura No: {fis_data.get('fis_no', '')} peşin ödemesi",
                'firma_id': fis_data['firma_id'], 'yil': fis_data['yil']
            }
            pesin_odeme_data['satirlar'] = []
            pesin_odeme_data['satirlar'].append({
                'hesap_turu': odeme_hesap_turu,
                'hesap_id': odeme_hesap_id,
                'borc': genel_toplam if is_tahsilat else 0,
                'alacak': 0 if is_tahsilat else genel_toplam,
                'aciklama': f"{self.fis_turu} peşin ödemesi"
            })

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            # Stok eksi kontrolü — ayara göre uyar/engelle (Adım 2)
            if not eksi_kontrol_ve_onayla(
                self, cursor, self.main_app.aktif_firma_id, fis_satirlari,
                guncellenen_fis_id=self.fis_id,
            ):
                return
            if self.fis_id:
                fis_guncelle(cursor, self.fis_id, fis_data, fis_satirlari, pesin_odeme_data, kaynak_modul='Fatura')
            else:
                fis_kaydet(cursor, fis_data, fis_satirlari, pesin_odeme_data, kaynak_modul='Fatura')
            conn.commit()
            if yeni_fis:
                self._yeni_fis_sifirla("Fatura kaydedildi — yeni fiş için form hazır.")
                self.list_view.listele()
            else:
                messagebox.showinfo("Başarılı", "Fatura başarıyla kaydedildi.", parent=self)
                anlik_yenile(self)  # U2: kayıt temizlendi
                self.kapat()
        except Exception as e:
            if conn: conn.rollback()
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu:\n{e}", parent=self)
        finally:
            if conn: conn.close()

    def fis_verilerini_yukle(self):
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fisler WHERE id=? AND firma_id=?",
                           (self.fis_id, self.main_app.aktif_firma_id))
            fis_data = cursor.fetchone()
            if not fis_data:
                messagebox.showerror("Hata", "Fatura bulunamadı.", parent=self)
                self.kapat()
                return
            
            fis_cols = [desc[0] for desc in cursor.description]
            fis_dict = dict(zip(fis_cols, fis_data))

            self.ent_tarih.set_date(datetime.strptime(fis_dict['tarih'], "%Y-%m-%d"))
            self.ent_fis_no.insert(0, fis_dict.get('fis_no', ''))
            self.ent_aciklama.insert(0, fis_dict.get('aciklama', ''))
            self.lookup_cari.set(fis_dict.get('cari_id'))

            if self.is_hizmet_faturasi:
                join_table, join_col, birim_expr = "hizmet_kartlari", "kart_adi", "''"
                hesap_turu_filter = "Hizmet"
            else:
                join_table, join_col, birim_expr = "stoklar", "stok_adi", "s.birim"
                hesap_turu_filter = "Stok"

            # C6: JOIN firma kapsamlı (id çakışması yanlış firmaya bağlanmasın) ve
            # LEFT JOIN — silinmiş kartı olan satırlar sessiz düşmesin (sil-yeniden-yaz
            # yolunda kaybolmalarının önü kesilir)
            query = f"""
                SELECT fs.*, COALESCE(s.{join_col}, '[Silinmiş Kart]') as hesap_adi, {birim_expr} as birim
                FROM fis_satirlari fs
                LEFT JOIN {join_table} s ON fs.hesap_id = s.id AND s.firma_id = ?
                WHERE fs.fis_id=? AND fs.hesap_turu=?
            """
            params = [self.main_app.aktif_firma_id, self.fis_id, hesap_turu_filter]

            # KDV hesap satırlarını (191/391) normal satır listesine alma; kaydederken yeniden üretilir
            kdv_ids = [kid for kid in (self.indirilecek_kdv_id, self.hesaplanan_kdv_id) if kid]
            if kdv_ids:
                placeholders = ", ".join("?" * len(kdv_ids))
                query += f" AND NOT (fs.hesap_turu = 'Hizmet' AND fs.hesap_id IN ({placeholders}))"
                params.extend(kdv_ids)

            cursor.execute(query, params)
            satir_cols = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                satir_dict = dict(zip(satir_cols, row))
                satir_id = str(uuid.uuid4())
                ara_toplam, kdv_tutar, toplam_tutar = kdv_hesapla(satir_dict['miktar'], satir_dict['birim_fiyat'], satir_dict['kdv_oran'])
                
                # satir_ekle ile aynı mantık: Satış → alacaklı; Alış → borçlu; Satış İade → borçlu; Alış İade → alacaklı
                # satir_ekle ile aynı şekilde satır tutarı NET'tir (ara_toplam); KDV ayrı satır olarak kaydedilir
                is_line_credit = not (("Satış" in self.fis_turu and "İade" in self.fis_turu) or ("Satış" not in self.fis_turu and "İade" not in self.fis_turu))
                borc, alacak = (0, ara_toplam) if is_line_credit else (ara_toplam, 0)

                self.satirlar[satir_id] = {
                    'hesap_turu': hesap_turu_filter, 'hesap_id': satir_dict['hesap_id'], 'stok_adi': satir_dict['hesap_adi'],
                    'miktar': satir_dict['miktar'], 'birim': satir_dict['birim'], 'birim_fiyat': satir_dict['birim_fiyat'], 'aciklama': satir_dict.get('aciklama', ''),
                    'kdv_oran': satir_dict['kdv_oran'], 'kdv_tutar': kdv_tutar, 'toplam_tutar': toplam_tutar, 'borc': borc, 'alacak': alacak,
                }
                self.tree.insert("", "end", iid=satir_id, values=(
                    satir_dict['hesap_adi'], satir_dict.get('aciklama', ''), format_miktar(satir_dict['miktar']), satir_dict['birim'],
                    format_currency(satir_dict['birim_fiyat']), f"{satir_dict['kdv_oran']:g}",
                    format_currency(kdv_tutar), format_currency(toplam_tutar), "❌"
                ))
            
            cursor.execute("SELECT * FROM fisler WHERE kaynak_fis_id=? AND firma_id=?",
                           (self.fis_id, self.main_app.aktif_firma_id))
            odeme_fis = cursor.fetchone()
            if odeme_fis:
                odeme_fis_dict = dict(zip([d[0] for d in cursor.description], odeme_fis))
                odeme_tipi_str = odeme_fis_dict['fis_turu'].split('(')[-1].strip(')')
                self.cmb_odeme_tipi.set(odeme_tipi_str)
                self.odeme_tipi_degisti()

                cursor.execute("SELECT hesap_id FROM fis_satirlari WHERE fis_id=? AND hesap_turu != 'Cari'", (odeme_fis_dict['id'],))
                odeme_hesap_row = cursor.fetchone()
                if odeme_hesap_row:
                    self.lookup_odeme_hesap.set(odeme_hesap_row[0])

            self.guncelle_toplamlari()

        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Fatura verileri yüklenirken bir hata oluştu: {e}", parent=self)
        finally:
            if conn: conn.close()

    def _yeni_fis_sifirla(self, basarili_mesaj=None):
        """U1: Kaydet ve Yeni Fiş — formu boş yeni fatura moduna alır (tarih/cari/ödeme korunur)."""
        yeni_fis_temel_sifirla(self)
        self.giris_satirini_temizle()
        self.guncelle_toplamlari()
        anlik_yenile(self)
        if hasattr(self.main_app, "durum_yaz"):
            self.main_app.durum_yaz(basarili_mesaj or "Fatura kaydedildi — yeni fiş için form hazır.")
        self.ent_fis_no.focus_set()

    def kapat(self):
        # U2: kirlilik varsa önce sorar (iptal/kapat sözleşmesi bu formda destroy ile)
        if not iptal_onayla(self):
            return False
        self.destroy()
        self.list_view.pack(fill="both", expand=True)
        self.list_view.listele()
        if self.on_close:
            self.on_close()
        return True

    def yenile(self):
        self.verileri_yukle()
        self._setup_stok_lookup()