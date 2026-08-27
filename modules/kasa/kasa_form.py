import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from core.db import veritabani_baglan
from core.services import fis_kaydet, fis_guncelle, aktif_yil_kontrolu
from ui.dialogs import ac_kart_dialog
from ui.widgets.lookup_widget import LookupWidget, LookupDialog
from ui.widgets.editable_treeview import EditableTreeview
from utils.formatters import CurrencyFormatter, parse_currency, format_miktar, kdv_hesapla


class KasaFisiFormu(tk.Frame):
    def __init__(self, parent, main_app, view_container, fis_turu, fis_id=None, on_close=None):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.view_container = view_container
        self.fis_id = fis_id
        self.fis_turu = fis_turu
        self.on_close = on_close
        self.satir_sayaci = 0

        self.satirlar = {}
        self.hizmet_dict = {}
        self.kasa_dict = {}

        self.create_widgets()
        self.verileri_yukle()
        self.ayarla_form_yapisi()
        
        # EN SON: Lookup hesap widget'ını ayarla (configure_lookup'dan SONRA)
        self._setup_hesap_lookup()

        if self.fis_id:
            self.load_fis_data()

    def create_widgets(self):
        # Ana Çerçeveler
        ust_frame = tk.Frame(self, bg="#f5f7fb")
        ust_frame.pack(fill="x", pady=10, padx=10)

        baslik_frame = tk.LabelFrame(ust_frame, text="Fiş Başlık Bilgileri", padx=10, pady=10, font=("Arial", 10, "bold"))
        baslik_frame.pack(fill="x")

        self.liste_frame = tk.LabelFrame(self, text="Fiş Satırları", padx=10, pady=10, font=("Arial", 10, "bold"))
        self.liste_frame.pack(fill="both", expand=True, padx=10)

        alt_buton_frame = tk.Frame(self, bg="#f5f7fb")
        alt_buton_frame.pack(fill="x", pady=10, padx=10, side="bottom")

        # --- Başlık Bilgileri ---
        baslik_frame.grid_columnconfigure(1, weight=1)
        baslik_frame.grid_columnconfigure(3, weight=1)

        tk.Label(baslik_frame, text="Fiş Türü:").grid(row=0, column=0, sticky="w", pady=2)
        self.lbl_fis_turu = tk.Label(baslik_frame, text=self.fis_turu, font=("Arial", 10, "bold"), anchor="w", bg="white", relief="sunken", padx=5)
        self.lbl_fis_turu.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Ana Kasa:").grid(row=2, column=0, sticky="w", pady=2)
        self.lookup_ana_kasa = LookupWidget(baslik_frame)
        self.lookup_ana_kasa.grid(row=2, column=1, columnspan=3, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Tarih:").grid(row=0, column=2, sticky="w", padx=(10, 0), pady=2)
        self.ent_tarih = DateEntry(baslik_frame, date_pattern="dd.mm.yyyy")
        self.ent_tarih.grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Fiş No:").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_fis_no = tk.Entry(baslik_frame)
        self.ent_fis_no.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Açıklama:").grid(row=1, column=2, sticky="w", padx=(10, 0), pady=2)
        self.ent_aciklama = tk.Entry(baslik_frame)
        self.ent_aciklama.grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        # Başlık Alanları Enter Navigasyonu
        self.lookup_ana_kasa.ent_display.bind("<Return>", lambda e: self.ent_tarih.focus_set())
        self.ent_tarih.bind("<Return>", lambda e: self.ent_fis_no.focus_set())
        self.ent_fis_no.bind("<Return>", lambda e: self.ent_aciklama.focus_set())
        self.ent_aciklama.bind("<Return>", self._aciklamadan_sonra_fokus)

        # Virman için özel alan
        self.lbl_hedef_kasa = tk.Label(baslik_frame, text="Hedef Kasa:")
        self.lookup_hedef_kasa = LookupWidget(baslik_frame)
        self.lbl_virman_tutar = tk.Label(baslik_frame, text="Virman Tutarı:")
        self.ent_virman_tutar = tk.Entry(baslik_frame, justify='right')

        self.lookup_hedef_kasa.ent_display.bind("<Return>", lambda e: self.ent_virman_tutar.focus_set())
        self.ent_virman_tutar.bind("<Return>", lambda e: self.btn_kaydet.focus_set())

        # --- Excel Tarzı Giriş Satırı ---
        self.entry_row_frame = tk.Frame(self.liste_frame)
        self.entry_row_frame.pack(fill="x", pady=(0, 10))

        # Giriş satırı widget'ları
        self.lookup_hesap = LookupWidget(self.entry_row_frame)
        self.ent_satir_aciklama = tk.Entry(self.entry_row_frame)
        self.ent_miktar = tk.Entry(self.entry_row_frame, width=10, justify='right')
        self.ent_birim_fiyat = tk.Entry(self.entry_row_frame, width=15, justify='right')
        self.ent_kdv_oran = tk.Entry(self.entry_row_frame, width=8, justify='right')
        self.ent_genel_tutar = tk.Entry(self.entry_row_frame, width=15, justify='right')
        self.lbl_satir_toplam = tk.Label(self.entry_row_frame, text="0,00", width=15, anchor='e', relief="sunken", bg="white", padx=2)
        self.btn_satir_ekle = tk.Button(self.entry_row_frame, text="+", command=self.satir_ekle, font=("Arial", 9, "bold"), width=3)

        # 1. CurrencyFormatter'ları oluştur
        CurrencyFormatter(self.ent_miktar, on_change_callback=self.hesapla_satir_toplami, decimal_places=4, trim_sifir=True)
        CurrencyFormatter(self.ent_birim_fiyat, on_change_callback=self.hesapla_satir_toplami)
        CurrencyFormatter(self.ent_kdv_oran, on_change_callback=self.hesapla_satir_toplami)
        CurrencyFormatter(self.ent_genel_tutar, on_change_callback=self.genel_tutardan_hesapla)
        CurrencyFormatter(self.ent_virman_tutar)

        # 2. Varsayılan değerleri ekle
        self.ent_miktar.insert(0, "1,00")
        self.ent_kdv_oran.insert(0, "20")

        # 3. Odaklanma davranışını ekle
        self._setup_select_on_focus([
            self.ent_virman_tutar,
            self.lookup_hesap.ent_display,
            self.ent_satir_aciklama,
            self.ent_miktar,
            self.ent_birim_fiyat,
            self.ent_kdv_oran,
            self.ent_genel_tutar
        ])

        # Enter ile ilerleme
        self.lookup_hesap.ent_display.bind("<Return>", lambda e: self.ent_satir_aciklama.focus_set())
        self.ent_satir_aciklama.bind("<Return>", lambda e: self.ent_miktar.focus_set())
        self.ent_miktar.bind("<Return>", lambda e: self.ent_birim_fiyat.focus_set())
        self.ent_birim_fiyat.bind("<Return>", lambda e: self.ent_kdv_oran.focus_set())
        self.ent_kdv_oran.bind("<Return>", lambda e: self.ent_genel_tutar.focus_set())
        self.ent_genel_tutar.bind("<Return>", lambda e: self.satir_ekle())

        # --- Başlıklar ve Giriş Satırı ---
        tk.Label(self.entry_row_frame, text="Hesap Adı", anchor='w', font=("Arial", 9, "bold")).grid(row=0, column=0, sticky='ew')
        tk.Label(self.entry_row_frame, text="Satır Açıklaması", anchor='w', font=("Arial", 9, "bold")).grid(row=0, column=1, sticky='ew')
        tk.Label(self.entry_row_frame, text="Miktar", anchor='w', font=("Arial", 9, "bold")).grid(row=0, column=2, sticky='ew')
        tk.Label(self.entry_row_frame, text="Birim Fiyat", anchor='w', font=("Arial", 9, "bold")).grid(row=0, column=3, sticky='ew')
        tk.Label(self.entry_row_frame, text="KDV %", anchor='w', font=("Arial", 9, "bold")).grid(row=0, column=4, sticky='ew')
        tk.Label(self.entry_row_frame, text="Tutar (KDV Dahil)", anchor='w', font=("Arial", 9, "bold")).grid(row=0, column=5, sticky='ew')
        tk.Label(self.entry_row_frame, text="Genel Toplam", anchor='w', font=("Arial", 9, "bold")).grid(row=0, column=6, sticky='ew')

        self.lookup_hesap.grid(row=1, column=0, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.ent_satir_aciklama.grid(row=1, column=1, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.ent_miktar.grid(row=1, column=2, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.ent_birim_fiyat.grid(row=1, column=3, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.ent_kdv_oran.grid(row=1, column=4, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.ent_genel_tutar.grid(row=1, column=5, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.lbl_satir_toplam.grid(row=1, column=6, sticky='ew', padx=(0, 2), pady=(2, 0))
        self.btn_satir_ekle.grid(row=1, column=7, sticky='ew', pady=(2, 0))

        self.entry_row_frame.grid_columnconfigure(0, weight=4, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(1, weight=5, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(2, weight=1, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(3, weight=2, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(4, weight=1, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(5, weight=2, uniform="group1")
        self.entry_row_frame.grid_columnconfigure(6, weight=2, uniform="group1")

        # --- Satır Listesi (satır içi düzenlenebilir) ---
        self.tree_satirlar = EditableTreeview(
            self.liste_frame,
            column_config={
                "hesap_adi": {"type": "lookup", "open_dialog": self._satir_hesap_dialog_ac},
                "aciklama": {"type": "text"},
                "miktar": {"type": "number"},
                "birim_fiyat": {"type": "number"},
                "kdv_oran": {"type": "number"},
                "toplam_tutar": {"type": "number"},
            },
            on_edit=self.on_satir_edit,
            get_edit_value=self._satir_edit_degeri_al,
            columns=("hesap_adi", "aciklama", "miktar", "birim_fiyat", "kdv_oran", "kdv_tutar", "toplam_tutar", "sil"),
            show="headings"
        )
        self.tree_satirlar.heading("hesap_adi", text="Hesap Adı")
        self.tree_satirlar.heading("aciklama", text="Satır Açıklaması")
        self.tree_satirlar.heading("miktar", text="Miktar")
        self.tree_satirlar.heading("birim_fiyat", text="Birim Fiyat")
        self.tree_satirlar.heading("kdv_oran", text="KDV %", anchor="e")
        self.tree_satirlar.heading("kdv_tutar", text="KDV T.", anchor="e")
        self.tree_satirlar.heading("toplam_tutar", text="Genel Toplam", anchor="e")
        self.tree_satirlar.heading("sil", text="", anchor="center")

        vsb = ttk.Scrollbar(self.liste_frame, orient="vertical", command=self.tree_satirlar.yview)
        vsb.pack(side='right', fill='y')
        self.tree_satirlar.configure(yscrollcommand=vsb.set)
        self.tree_satirlar.pack(fill="both", expand=True)

        self.tree_satirlar.bind("<ButtonRelease-1>", self.on_tree_click)

        def _sync_widths(event=None):
            column_map = {
                "hesap_adi": 0, "aciklama": 1, "miktar": 2,
                "birim_fiyat": 3, "kdv_oran": 4, "toplam_tutar": 5
            }
            for col_name, i in column_map.items():
                try:
                    width = self.entry_row_frame.grid_bbox(i, 1)[2]
                    anchor = "e" if col_name not in ["hesap_adi", "aciklama"] else "w"
                    self.tree_satirlar.column(col_name, width=width, anchor=anchor)
                except (TypeError, IndexError):
                    pass
            self.tree_satirlar.column("kdv_tutar", width=70, anchor="e", stretch=False)
            self.tree_satirlar.column("sil", width=30, anchor="center", stretch=False)

        self.entry_row_frame.bind("<Configure>", _sync_widths)
        self.after(100, _sync_widths)

        # --- Toplamlar Alanı ---
        toplamlar_frame = tk.Frame(self.liste_frame, bg="#e9ecef")
        toplamlar_frame.pack(fill="x", pady=(5, 0))
        toplamlar_frame.grid_columnconfigure(1, weight=1)

        tk.Label(toplamlar_frame, text="Ara Toplam:", font=("Arial", 9, "bold"), bg="#e9ecef").grid(row=0, column=2, sticky="e", padx=5)
        self.lbl_ara_toplam = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 9), bg="#e9ecef", width=15, anchor="e")
        self.lbl_ara_toplam.grid(row=0, column=3, sticky="e")

        tk.Label(toplamlar_frame, text="Toplam KDV:", font=("Arial", 9, "bold"), bg="#e9ecef").grid(row=1, column=2, sticky="e", padx=5)
        self.lbl_toplam_kdv = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 9), bg="#e9ecef", width=15, anchor="e")
        self.lbl_toplam_kdv.grid(row=1, column=3, sticky="e")

        tk.Label(toplamlar_frame, text="Genel Toplam:", font=("Arial", 10, "bold"), bg="#e9ecef").grid(row=2, column=2, sticky="e", padx=5)
        self.lbl_genel_toplam = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 10, "bold"), bg="#e9ecef", width=15, anchor="e")
        self.lbl_genel_toplam.grid(row=2, column=3, sticky="e")

        # --- Alt Butonlar ---
        self.btn_kaydet = tk.Button(
            alt_buton_frame,
            text="Fişi Kaydet",
            command=self.fis_kaydet,
            bg="#198754",
            fg="white",
            font=("Arial", 11, "bold"),
            height=2,
            width=20
        )
        self.btn_kaydet.pack(side="right")

        self.btn_iptal = tk.Button(
            alt_buton_frame,
            text="İptal ve Geri Dön",
            command=self.iptal,
            bg="#6c757d",
            fg="white",
            font=("Arial", 11, "bold"),
            height=2,
            width=20
        )
        self.btn_iptal.pack(side="right", padx=10)

    def _setup_hesap_lookup(self):
        """Lookup hesap widget'ına KDV güncelleme özelliği ekler."""
        
        # ============================================================
        # EN KESİN ÇÖZÜM: ent_display'in değişimini SÜREKLİ izle
        # ============================================================
        
        # 1. StringVar kullanarak ent_display'i izle
        self._hesap_var = tk.StringVar()
        self._hesap_var.trace('w', self._on_hesap_var_change)
        self.lookup_hesap.ent_display.config(textvariable=self._hesap_var)
        
        # 2. Set metodunu patch'le (güvenlik için)
        original_set = self.lookup_hesap.set
        
        def new_set(value):
            original_set(value)
            self._hesap_var.set(self.lookup_hesap.get_value() or '')
            self.after(50, self._force_kdv_update)
            if self.lookup_hesap.get_value():
                self.ent_satir_aciklama.focus_set()
        
        self.lookup_hesap.set = new_set
        
        # 3. Tüm olayları yakala
        self.lookup_hesap.ent_display.bind("<FocusOut>", lambda e: self.after(50, self._force_kdv_update), add='+')
        self.lookup_hesap.ent_display.bind("<KeyRelease>", self._on_key_release, add='+')
        
        # 4. Seçim butonuna tıklandığında
        if hasattr(self.lookup_hesap, 'btn_select'):
            self.lookup_hesap.btn_select.bind("<Button-1>", lambda e: self.after(300, self._force_kdv_update), add='+')
    
    def _on_hesap_var_change(self, *args):
        """StringVar değiştiğinde KDV'yi güncelle."""
        self.after(50, self._force_kdv_update)
    
    def _on_key_release(self, event):
        """Tuş bırakıldığında KDV'yi güncelle."""
        if event.keysym in ['Return', 'Tab', 'Down', 'Up']:
            self.after(50, self._force_kdv_update)

    def _force_kdv_update(self):
        """KDV güncellemesini zorla yapar."""
        self._on_hesap_select()
        # Eğer bir hesap seçiliyse, satır açıklamasına odaklan
        if self.lookup_hesap.get_value():
            self.ent_satir_aciklama.focus_set()

    def _setup_select_on_focus(self, widgets):
        """Widget'lara odaklanıldığında tüm metni seçme davranışını ekler."""
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
        """Seçilen hizmet kartına göre KDV oranını otomatik doldurur."""
        try:
            hesap_id = self.lookup_hesap.get()
            hesap_adi = self.lookup_hesap.get_value()
            
            if not hesap_id and not hesap_adi:
                return

            kdv_oran = 20  # Varsayılan
            hesap_bilgisi = None
            
            # 1. Önce ID ile dene
            if hesap_id:
                for key, value in self.hizmet_dict.items():
                    if value.get('id') == hesap_id:
                        hesap_bilgisi = value
                        break
            
            # 2. ID ile bulunamazsa, ad ile dene
            if not hesap_bilgisi and hesap_adi:
                temiz_adi = hesap_adi
                if '] ' in hesap_adi:
                    temiz_adi = hesap_adi.split('] ', 1)[1]
                
                for key, value in self.hizmet_dict.items():
                    key_adi = key.split('] ', 1)[1] if '] ' in key else key
                    if key_adi == temiz_adi or key == hesap_adi:
                        hesap_bilgisi = value
                        break

            if hesap_bilgisi:
                kdv_oran_db = hesap_bilgisi.get('kdv_oran')
                if kdv_oran_db is not None:
                    kdv_oran = kdv_oran_db

            # KDV alanını güncelle
            self.ent_kdv_oran.delete(0, tk.END)
            self.ent_kdv_oran.insert(0, f"{kdv_oran:g}")
            self.hesapla_satir_toplami()

        except Exception as e:
            print(f"_on_hesap_select hatası: {e}")

    def verileri_yukle(self):
        """Lookup widget'ları için gerekli verileri veritabanından yükler."""
        firma_id = self.main_app.aktif_firma_id
        conn = veritabani_baglan()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, kart_adi, tur, kdv_oran FROM hizmet_kartlari WHERE durum=1 AND firma_id=?", (firma_id,)
        )
        self.hizmet_dict = {
            f"[{row[2]}] {row[1]}": {"id": row[0], "tur": row[2], "kdv_oran": row[3] if row[3] is not None else 20}
            for row in cursor.fetchall()
        }

        # KDV hesap ID'lerini bul (tur='KDV' olanlar)
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
        self.lookup_ana_kasa.configure_lookup(
            title="Ana Kasa Seç", data_dict=self.kasa_dict, on_new=lambda: self.yeni_kart_ekle("kasalar")
        )

        conn.close()

    def ayarla_form_yapisi(self):
        """Fiş türüne göre formun yapısını ayarlar."""
        if self.fis_turu == "Kasa Gider Fişi":
            gider_kartlari = {k: v['id'] for k, v in self.hizmet_dict.items() if v['tur'] == 'Gider'}
            self.lookup_hesap.configure_lookup(
                title="Gider Kartı Seç", data_dict=gider_kartlari, on_new=lambda: self.yeni_kart_ekle("hizmet_kartlari", "Gider")
            )
            self.toggle_hedef_kasa_alani(False)

        elif self.fis_turu == "Kasa Gelir Fişi":
            gelir_kartlari = {k: v['id'] for k, v in self.hizmet_dict.items() if v['tur'] == 'Gelir'}
            self.lookup_hesap.configure_lookup(
                title="Gelir Kartı Seç", data_dict=gelir_kartlari, on_new=lambda: self.yeni_kart_ekle("hizmet_kartlari", "Gelir")
            )
            self.toggle_hedef_kasa_alani(False)

        elif self.fis_turu == "Kasalar Arası Virman":
            self.lookup_hesap.configure_lookup(title="Hesap Seç", data_dict={})
            self.liste_frame.pack_forget()
            self.toggle_hedef_kasa_alani(True)

        self.lookup_hesap.clear()

    def toggle_hedef_kasa_alani(self, goster):
        """Virman için Hedef Kasa alanını gösterir/gizler."""
        if goster:
            self.lbl_hedef_kasa.grid(row=3, column=0, sticky="w", pady=2)
            self.lookup_hedef_kasa.grid(row=3, column=1, columnspan=3, padx=5, pady=2, sticky="ew")
            self.lookup_hedef_kasa.configure_lookup(
                title="Hedef Kasa Seç", data_dict=self.kasa_dict, on_new=lambda: self.yeni_kart_ekle("kasalar")
            )
            self.lbl_virman_tutar.grid(row=4, column=0, sticky="w", pady=5)
            self.ent_virman_tutar.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        else:
            self.lbl_hedef_kasa.grid_forget()
            self.lookup_hedef_kasa.grid_forget()
            self.lbl_virman_tutar.grid_forget()
            self.ent_virman_tutar.grid_forget()

    def _aciklamadan_sonra_fokus(self, event=None):
        """Fiş başlığındaki açıklamadan sonra doğru alana odaklanır."""
        if self.fis_turu == "Kasalar Arası Virman":
            self.lookup_hedef_kasa.ent_display.focus_set()
        else:
            self.lookup_hesap.ent_display.focus_set()

    def yeni_kart_ekle(self, tablo_adi, kart_turu=None):
        """Lookup widget'larından yeni kart ekleme işlemini yönetir."""
        ac_kart_dialog(self, tablo_adi, firma_id=self.main_app.aktif_firma_id, kart_turu=kart_turu)
        self.verileri_yukle()
        self.ayarla_form_yapisi()
        self._setup_hesap_lookup()

    def hesapla_satir_toplami(self, *args):
        """Satır toplamını hesaplar."""
        try:
            miktar = parse_currency(self.ent_miktar.get())
            birim_fiyat = parse_currency(self.ent_birim_fiyat.get())
            kdv_oran = parse_currency(self.ent_kdv_oran.get())

            # Akıllı giriş: "Tutar (KDV Dahil)" doluysa birim fiyatı otomatik hesapla
            genel = parse_currency(self.ent_genel_tutar.get())
            if genel > 0 and miktar > 0:
                birim_fiyat = genel / (miktar * (1 + kdv_oran / 100))

            ara_toplam, kdv_tutar, genel_toplam = kdv_hesapla(miktar, birim_fiyat, kdv_oran)

            self.lbl_satir_toplam.config(
                text=f"{genel_toplam:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        except (ValueError, tk.TclError, ZeroDivisionError):
            self.lbl_satir_toplam.config(text="0,00")

    def genel_tutardan_hesapla(self, *args):
        """'Tutar (KDV Dahil)' alanı değiştiğinde birim fiyatı geriye hesaplar."""
        try:
            genel = parse_currency(self.ent_genel_tutar.get())
            miktar = parse_currency(self.ent_miktar.get())
            kdv_oran = parse_currency(self.ent_kdv_oran.get())
            if genel > 0 and miktar > 0:
                birim_fiyat = genel / (miktar * (1 + kdv_oran / 100))
                self.ent_birim_fiyat.delete(0, tk.END)
                self.ent_birim_fiyat.insert(0, f"{birim_fiyat:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."))
            self.hesapla_satir_toplami()
        except (ValueError, tk.TclError, ZeroDivisionError):
            self.hesapla_satir_toplami()

    def satir_ekle(self):
        """Yeni satır ekler veya mevcut satırı günceller."""
        hesap_id = self.lookup_hesap.get()
        hesap_adi = self.lookup_hesap.get_value()
        aciklama = self.ent_satir_aciklama.get()
        miktar = parse_currency(self.ent_miktar.get())
        birim_fiyat = parse_currency(self.ent_birim_fiyat.get())
        kdv_oran = parse_currency(self.ent_kdv_oran.get())

        # Akıllı giriş: "Tutar (KDV Dahil)" doluysa birim fiyatı ondan hesapla
        genel_giris = parse_currency(self.ent_genel_tutar.get())
        if genel_giris > 0 and miktar > 0:
            birim_fiyat = genel_giris / (miktar * (1 + kdv_oran / 100))

        if not hesap_id:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir hesap seçin.", parent=self)
            return

        if miktar <= 0 or birim_fiyat <= 0:
            messagebox.showwarning("Geçersiz Tutar", "Lütfen 0'dan büyük bir miktar ve birim fiyat girin.", parent=self)
            return

        ara_toplam, kdv_tutar, genel_toplam = kdv_hesapla(miktar, birim_fiyat, kdv_oran)

        yeni_satir_verisi = {
            "hesap_id": hesap_id,
            "hesap_adi": hesap_adi,
            "aciklama": aciklama,
            "miktar": miktar,
            "birim_fiyat": birim_fiyat,
            "kdv_oran": kdv_oran,
            "ara_toplam": ara_toplam,
            "kdv_tutar": kdv_tutar,
            "genel_toplam": genel_toplam
        }

        self.satir_sayaci += 1
        item_id = f"satir_{self.satir_sayaci}"
        self.tree_satirlar.insert(
            "", "end", iid=item_id,
            values=(
                hesap_adi, aciklama,
                format_miktar(miktar), self._fmt_money(birim_fiyat),
                f"{kdv_oran:g}", self._fmt_money(kdv_tutar), self._fmt_money(genel_toplam), "❌"
            )
        )
        self.satirlar[item_id] = yeni_satir_verisi

        self.temizle_giris_satiri()

    def temizle_giris_satiri(self):
        """Giriş satırını temizler."""
        self.lookup_hesap.clear()
        self.ent_satir_aciklama.delete(0, tk.END)
        self.ent_miktar.delete(0, tk.END)
        self.ent_miktar.insert(0, "1,00")
        self.ent_birim_fiyat.delete(0, tk.END)
        self.ent_kdv_oran.delete(0, tk.END)
        self.ent_kdv_oran.insert(0, "20")
        self.ent_genel_tutar.delete(0, tk.END)
        self.lookup_hesap.ent_display.focus_set()
        self.guncelle_toplamlari()

    def satir_sil(self, item_id_to_delete):
        """Satırı siler."""
        if not item_id_to_delete:
            return

        try:
            self.tree_satirlar.delete(item_id_to_delete)
            del self.satirlar[item_id_to_delete]
        except KeyError:
            print(f"Satır {item_id_to_delete} bulunamadı.")

        self.guncelle_toplamlari()

    def on_tree_click(self, event):
        """Treeview'de tıklama olayını işler."""
        region = self.tree_satirlar.identify("region", event.x, event.y)
        if region == "cell" and self.tree_satirlar.identify_column(event.x) == "#8":
            self.satir_sil(self.tree_satirlar.identify_row(event.y))

    # --------------------------------------------------------- Satır içi düzenleme
    @staticmethod
    def _fmt_money(deger):
        """Sayıyı Türkçe para formatına çevirir (örn: 1.234,56)."""
        return f"{deger:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _satir_hesap_dialog_ac(self, iid):
        """Satırın hesap hücresi için gerçek lookup (ara + yeni kart) diyaloğunu açar."""
        tur = "Gider" if self.fis_turu == "Kasa Gider Fişi" else "Gelir"
        data_dict = {k: v['id'] for k, v in self.hizmet_dict.items() if v['tur'] == tur}
        dialog = LookupDialog(
            self,
            f"{tur} Kartı Seç",
            data_dict,
            on_new_item=lambda: self._satir_yeni_kart(tur),
            on_edit_item=None,
            on_delete_item=None,
        )
        self.wait_window(dialog)
        if dialog.result:
            return dialog.result[1]  # seçilen kart adı
        return None

    def _satir_yeni_kart(self, kart_turu):
        """Satır lookup diyaloğundan yeni kart ekler; (id, ad) döndürür."""
        sonuc = ac_kart_dialog(self, "hizmet_kartlari", firma_id=self.main_app.aktif_firma_id, kart_turu=kart_turu)
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
        if column == "aciklama":
            return satir.get('aciklama', '')
        if column == "miktar":
            return format_miktar(satir.get('miktar', 1))
        if column == "birim_fiyat":
            return self._fmt_money(satir.get('birim_fiyat', 0))
        if column == "kdv_oran":
            return f"{satir.get('kdv_oran', 0):g}"
        if column == "toplam_tutar":
            return self._fmt_money(satir.get('genel_toplam', 0))
        return ""

    def on_satir_edit(self, iid, column, value):
        """Satır içi düzenlemeden gelen değeri uygular. Geçerliyse True döner."""
        satir = self.satirlar.get(iid)
        if satir is None:
            return False

        if column == "hesap_adi":
            hesap_bilgisi = self.hizmet_dict.get(value)
            if not hesap_bilgisi:
                return False
            satir['hesap_adi'] = value
            satir['hesap_id'] = hesap_bilgisi['id']
            # Hesap değişince kartın varsayılan KDV oranını uygula (ekleme akışıyla aynı)
            kdv = hesap_bilgisi.get('kdv_oran')
            if kdv is not None:
                satir['kdv_oran'] = kdv

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

        # KDV ve toplamları yeniden hesapla (2 ondalık, ticari yuvarlama)
        satir['ara_toplam'], satir['kdv_tutar'], satir['genel_toplam'] = kdv_hesapla(
            satir['miktar'], satir['birim_fiyat'], satir['kdv_oran']
        )
        self._satir_row_guncelle(iid, satir)
        self.guncelle_toplamlari()
        return True

    def _satir_row_guncelle(self, iid, satir):
        """Bir satırın görünümünü veriye göre yeniler."""
        if not self.tree_satirlar.exists(iid):
            return
        self.tree_satirlar.item(iid, values=(
            satir['hesap_adi'], satir['aciklama'],
            format_miktar(satir['miktar']), self._fmt_money(satir['birim_fiyat']),
            f"{satir['kdv_oran']:g}",
            self._fmt_money(satir['kdv_tutar']), self._fmt_money(satir['genel_toplam']), "❌"
        ))

    def guncelle_toplamlari(self):
        """Fişin altındaki genel toplamları günceller."""
        ara_toplam = sum(s['ara_toplam'] for s in self.satirlar.values())
        toplam_kdv = sum(s['kdv_tutar'] for s in self.satirlar.values())
        genel_toplam = sum(s['genel_toplam'] for s in self.satirlar.values())

        self.lbl_ara_toplam.config(text=f"{ara_toplam:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.lbl_toplam_kdv.config(text=f"{toplam_kdv:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.lbl_genel_toplam.config(text=f"{genel_toplam:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def fis_kaydet(self):
        """Fişi kaydeder."""
        fis_turu = self.fis_turu

        # Dönem dışı tarih engeli: fiş, seçili yıl dışında bir tarihe yazılamaz
        yil_hata = aktif_yil_kontrolu(self.ent_tarih.get_date(), self.main_app.aktif_yil)
        if yil_hata:
            messagebox.showwarning("Dönem Dışı Tarih", yil_hata, parent=self)
            return

        if not self.satirlar and fis_turu != "Kasalar Arası Virman":
            messagebox.showwarning("Eksik Bilgi", "Fişe en az bir satır eklemelisiniz.", parent=self)
            return

        ana_kasa_id = self.lookup_ana_kasa.get()
        if not ana_kasa_id:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir Ana Kasa seçin.", parent=self)
            return

        if fis_turu == "Kasalar Arası Virman":
            hedef_kasa_id = self.lookup_hedef_kasa.get()
            if not hedef_kasa_id:
                messagebox.showwarning("Eksik Bilgi", "Lütfen bir Hedef Kasa seçin.", parent=self)
                return
            toplam_tutar = parse_currency(self.ent_virman_tutar.get())
            if toplam_tutar <= 0:
                messagebox.showwarning("Geçersiz Tutar", "Lütfen 0'dan büyük bir virman tutarı girin.", parent=self)
                return
        else:
            toplam_tutar = sum(satir['genel_toplam'] for satir in self.satirlar.values())

        fis_baslik = {
            "tarih": self.ent_tarih.get_date().strftime("%Y-%m-%d"),
            "fis_turu": fis_turu,
            "fis_no": self.ent_fis_no.get().strip(),
            "aciklama": self.ent_aciklama.get().strip(),
            "toplam_tutar": toplam_tutar,
            "cari_id": None,
            "firma_id": self.main_app.aktif_firma_id,
            "yil": self.ent_tarih.get_date().year
        }

        fis_satirlari = []
        if fis_turu == "Kasalar Arası Virman":
            fis_satirlari.append({
                "hesap_turu": "Kasa",
                "hesap_id": ana_kasa_id,
                "borc": 0,
                "alacak": toplam_tutar,
                "aciklama": f"ID:{hedef_kasa_id} kasaya virman",
                "miktar": 1,
                "birim_fiyat": toplam_tutar,
                "kdv_oran": 0,
                "kdv_tutar": 0
            })
            fis_satirlari.append({
                "hesap_turu": "Kasa",
                "hesap_id": hedef_kasa_id,
                "borc": toplam_tutar,
                "alacak": 0,
                "aciklama": f"ID:{ana_kasa_id} kasadan virman",
                "miktar": 1,
                "birim_fiyat": toplam_tutar,
                "kdv_oran": 0,
                "kdv_tutar": 0
            })
        else:
            is_gider = fis_baslik["fis_turu"] == "Kasa Gider Fişi"
            for satir in self.satirlar.values():
                fis_satirlari.append({
                    "hesap_turu": "Hizmet",
                    "hesap_id": satir['hesap_id'],
                    "borc": satir['ara_toplam'] if is_gider else 0,
                    "alacak": 0 if is_gider else satir['ara_toplam'],
                    "aciklama": satir['aciklama'],
                    "miktar": satir['miktar'],
                    "birim_fiyat": satir['birim_fiyat'],
                    "kdv_oran": satir['kdv_oran'],
                    "kdv_tutar": satir['kdv_tutar']
                })
                # KDV ayrı satır olarak eklenir (191 İndirilecek KDV / 391 Hesaplanan KDV)
                if satir.get('kdv_tutar'):
                    kdv_hesap_id = self.indirilecek_kdv_id if is_gider else self.hesaplanan_kdv_id
                    if kdv_hesap_id:
                        fis_satirlari.append({
                            "hesap_turu": "Hizmet",
                            "hesap_id": kdv_hesap_id,
                            "borc": satir['kdv_tutar'] if is_gider else 0,
                            "alacak": 0 if is_gider else satir['kdv_tutar'],
                            "aciklama": f"{'İndirilecek' if is_gider else 'Hesaplanan'} KDV",
                            "miktar": 1,
                            "birim_fiyat": satir['kdv_tutar'],
                            "kdv_oran": 0,
                            "kdv_tutar": 0
                        })

            fis_satirlari.append({
                "hesap_turu": "Kasa",
                "hesap_id": ana_kasa_id,
                "borc": 0 if is_gider else toplam_tutar,
                "alacak": toplam_tutar if is_gider else 0,
                "aciklama": fis_baslik["aciklama"],
                "miktar": 1,
                "birim_fiyat": toplam_tutar,
                "kdv_oran": 0,
                "kdv_tutar": 0
            })

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            if self.fis_id:
                fis_guncelle(cursor, self.fis_id, fis_baslik, fis_satirlari, kaynak_modul='Kasa')
                mesaj = "Kasa fişi başarıyla güncellendi."
            else:
                fis_kaydet(cursor, fis_baslik, fis_satirlari, kaynak_modul='Kasa')
                mesaj = "Kasa fişi başarıyla kaydedildi."

            conn.commit()
            messagebox.showinfo("Başarılı", mesaj, parent=self)
            self.iptal()
            self.view_container.yenile()
        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu:\n{e}", parent=self)
        finally:
            if conn:
                conn.close()

    def load_fis_data(self):
        """Düzenleme modunda fiş bilgilerini forma yükler."""
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM fisler WHERE id=?", (self.fis_id,))
            baslik = cursor.fetchone()
            if not baslik:
                messagebox.showerror("Hata", "Fiş bulunamadı.", parent=self)
                self.iptal()
                return

            baslik_cols = [desc[0] for desc in cursor.description]
            baslik_data = dict(zip(baslik_cols, baslik))

            tarih_obj = datetime.strptime(baslik_data['tarih'], '%Y-%m-%d').date()
            self.ent_tarih.set_date(tarih_obj)
            self.ent_fis_no.insert(0, baslik_data['fis_no'])
            self.ent_aciklama.insert(0, baslik_data['aciklama'])

            cursor.execute("SELECT * FROM fis_satirlari WHERE fis_id=?", (self.fis_id,))
            satirlar = cursor.fetchall()
            satir_cols = [desc[0] for desc in cursor.description]

            if baslik_data['fis_turu'] == "Kasalar Arası Virman":
                for satir in satirlar:
                    satir_data = dict(zip(satir_cols, satir))
                    if satir_data['alacak'] > 0:
                        self.lookup_ana_kasa.set(satir_data['hesap_id'])
                    elif satir_data['borc'] > 0:
                        self.lookup_hedef_kasa.set(satir_data['hesap_id'])
                self.ent_virman_tutar.delete(0, tk.END)
                self.ent_virman_tutar.insert(0, f"{baslik_data['toplam_tutar']:.2f}".replace('.', ','))
            else:
                is_gider = baslik_data['fis_turu'] == "Kasa Gider Fişi"
                for satir in satirlar:
                    satir_data = dict(zip(satir_cols, satir))
                    # KDV hesap satırları otomatik yeniden üretilir, normal listeye eklenmez
                    if satir_data['hesap_turu'] == 'Hizmet' and satir_data['hesap_id'] in (self.indirilecek_kdv_id, self.hesaplanan_kdv_id):
                        continue
                    if satir_data['hesap_turu'] == 'Kasa':
                        self.lookup_ana_kasa.set(satir_data['hesap_id'])
                    else:
                        hesap_adi = next((k for k, v in self.hizmet_dict.items() if v['id'] == satir_data['hesap_id']), "Bilinmeyen Hesap")
                        miktar = satir_data.get('miktar', 1)
                        kdv_oran = satir_data.get('kdv_oran', 0)
                        satir_tutari = satir_data['borc'] if is_gider else satir_data['alacak']
                        birim_fiyat = satir_data.get('birim_fiyat') or satir_tutari
                        # kdv_tutar DB'de saklanmaz; kdv_oran'dan yuvarlanarak yeniden hesaplanır
                        ara_toplam, kdv_tutar, genel_toplam = kdv_hesapla(miktar, birim_fiyat, kdv_oran)

                        yeni_satir_verisi = {
                            "hesap_id": satir_data['hesap_id'],
                            "hesap_adi": hesap_adi,
                            "aciklama": satir_data['aciklama'],
                            "miktar": miktar,
                            "birim_fiyat": birim_fiyat,
                            "kdv_oran": kdv_oran,
                            "kdv_tutar": kdv_tutar,
                            "ara_toplam": ara_toplam,
                            "genel_toplam": genel_toplam
                        }
                        self.satir_sayaci += 1
                        item_id = f"satir_{self.satir_sayaci}"
                        self.tree_satirlar.insert(
                            "", "end", iid=item_id,
                            values=(
                                hesap_adi, satir_data['aciklama'],
                                format_miktar(miktar), self._fmt_money(birim_fiyat),
                                f"{kdv_oran:g}", self._fmt_money(kdv_tutar), self._fmt_money(genel_toplam), "❌"
                            )
                        )
                        self.satirlar[item_id] = yeni_satir_verisi
                self.guncelle_toplamlari()

            conn.close()
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Fiş bilgileri yüklenemedi: {e}", parent=self)
            self.iptal()

    def iptal(self):
        """Formu gizle ve liste görünümünü göster."""
        self.pack_forget()
        if self.on_close:
            self.on_close()
        self.view_container.pack(fill="both", expand=True)

    def yenile(self):
        """Lookup verilerini yenile."""
        self.verileri_yukle()