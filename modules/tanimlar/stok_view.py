import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from core.db import veritabani_baglan
from core.services import kart_sil as kart_sil_service, kaydet_kart
from utils.formatters import format_currency, parse_currency
from utils.export import export_treeview_data
from ui.widgets.lookup_widget import LookupWidget
from ui.dialogs import ac_kart_dialog
from ui.widgets.pagination import SayfaliListeMixin

class StokTanimView(SayfaliListeMixin, tk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.parent = parent
        self.selected_id = None
        self.kategori_dict = {}
        self.birim_dict = {}

        self.create_widgets()
        self._load_and_configure_data()
        self.listele()

    def create_widgets(self):
        # Ana çerçeveler: Sol form, Sağ liste
        form_frame = tk.LabelFrame(self, text="Stok Kartı Bilgileri", bg="#f5f7fb", padx=10, pady=10)
        form_frame.pack(side="left", fill="y", padx=10, pady=10)

        liste_frame = tk.Frame(self, bg="#f5f7fb")
        liste_frame.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)


        # --- Form Alanları (Sol Taraf) ---
        form_alanlari = tk.Frame(form_frame, bg="#f5f7fb")
        form_alanlari.pack(fill="x")
        form_alanlari.columnconfigure(1, weight=1)

        tk.Label(form_alanlari, text="Stok Adı:", bg="#f5f7fb").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_stok_adi = tk.Entry(form_alanlari, width=40)
        self.ent_stok_adi.grid(row=0, column=1, pady=2)

        tk.Label(form_alanlari, text="Stok Kodu:", bg="#f5f7fb").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_stok_kodu = tk.Entry(form_alanlari, width=40)
        self.ent_stok_kodu.grid(row=1, column=1, pady=2)

        tk.Label(form_alanlari, text="Kategori:", bg="#f5f7fb").grid(row=2, column=0, sticky="w", pady=2)
        self.lookup_kategori = LookupWidget(form_alanlari)
        self.lookup_kategori.grid(row=2, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Birim:", bg="#f5f7fb").grid(row=3, column=0, sticky="w", pady=2)
        self.lookup_birim = LookupWidget(form_alanlari)
        self.lookup_birim.grid(row=3, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Alış Fiyatı:", bg="#f5f7fb").grid(row=4, column=0, sticky="w", pady=2)
        self.ent_alis_fiyati = tk.Entry(form_alanlari, width=40, justify="right")
        self.ent_alis_fiyati.grid(row=4, column=1, pady=2)

        tk.Label(form_alanlari, text="Satış Fiyatı:", bg="#f5f7fb").grid(row=5, column=0, sticky="w", pady=2)
        self.ent_satis_fiyati = tk.Entry(form_alanlari, width=40, justify="right")
        self.ent_satis_fiyati.grid(row=5, column=1, pady=2)

        tk.Label(form_alanlari, text="Varsayılan KDV Oranı (%):", bg="#f5f7fb").grid(row=6, column=0, sticky="w", pady=2)
        self.ent_kdv_oran = tk.Entry(form_alanlari, width=40, justify="right")
        self.ent_kdv_oran.grid(row=6, column=1, pady=2)

        tk.Label(form_alanlari, text="Kritik Miktar:", bg="#f5f7fb").grid(row=7, column=0, sticky="w", pady=2)
        self.ent_kritik_miktar = tk.Entry(form_alanlari, width=40, justify="right")
        self.ent_kritik_miktar.grid(row=7, column=1, pady=2)

        tk.Label(form_alanlari, text="Durum:", bg="#f5f7fb").grid(row=8, column=0, sticky="w", pady=2)
        self.cmb_durum = ttk.Combobox(form_alanlari, state="readonly", values=["Aktif", "Pasif"])
        self.cmb_durum.set("Aktif")
        self.cmb_durum.grid(row=8, column=1, pady=2, sticky="ew")

        # --- Form Butonları ---
        buton_frame = tk.Frame(form_frame, bg="#f5f7fb", pady=10)
        buton_frame.pack(fill="x")

        self.btn_kaydet = tk.Button(buton_frame, text="Kaydet", command=self.kaydet_kart, bg="#198754", fg="white")
        self.btn_kaydet.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_sil = tk.Button(buton_frame, text="Sil", command=self.sil_kart, bg="#dc3545", fg="white")
        self.btn_sil.pack(side="left", expand=True, fill="x")

        self.btn_temizle = tk.Button(buton_frame, text="Formu Temizle", command=self.formu_temizle)
        self.btn_temizle.pack(side="left", expand=True, fill="x", padx=(5, 0))

        # --- Filtre Alanı (Sağ Taraf - Üst) ---
        filter_frame = tk.LabelFrame(liste_frame, text="Filtrele", bg="#f5f7fb", padx=10, pady=5)
        filter_frame.pack(fill="x", pady=(0, 5))

        tk.Label(filter_frame, text="Kategori:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_kategori_filtre = ttk.Combobox(filter_frame, state="readonly", width=20)
        self.cmb_kategori_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_kategori_filtre.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Durum:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_durum_filtre = ttk.Combobox(filter_frame, state="readonly", width=10, values=["Tümü", "Aktif", "Pasif"])
        self.cmb_durum_filtre.set("Aktif")
        self.cmb_durum_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_durum_filtre.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Ara:", bg="#f5f7fb").pack(side="left", padx=(10, 2))
        self.ent_arama = tk.Entry(filter_frame)
        self.ent_arama.pack(side="left", fill="x", expand=True)
        self.ent_arama.bind("<KeyRelease>", lambda e: self.listele())

        btn_filtre_temizle = tk.Button(filter_frame, text="Filtreleri Temizle", command=self.filtreleri_temizle)
        btn_filtre_temizle.pack(side="left", padx=(10, 0))
        btn_excel = tk.Button(filter_frame, text="Excel'e Aktar", command=lambda: self.disari_aktar('excel'))
        btn_excel.pack(side="left", padx=(10, 0))

        btn_pdf = tk.Button(filter_frame, text="PDF'e Aktar", command=lambda: self.disari_aktar('pdf'))
        btn_pdf.pack(side="left", padx=(5, 0))

        # --- Liste Alanı (Sağ Taraf - Alt) ---
        tree_container = tk.Frame(liste_frame)
        tree_container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_container, columns=("id", "stok_kodu", "stok_adi", "kategori", "birim", "kdv_oran", "alis_fiyati", "satis_fiyati"), show="headings")
        
        self.tree.heading("id", text="ID")
        self.tree.heading("stok_kodu", text="Stok Kodu")
        self.tree.heading("stok_adi", text="Stok Adı")
        self.tree.heading("kategori", text="Kategori")
        self.tree.heading("birim", text="Birim")
        self.tree.heading("kdv_oran", text="KDV %", anchor="e")
        self.tree.heading("alis_fiyati", text="Alış Fiyatı", anchor="e")
        self.tree.heading("satis_fiyati", text="Satış Fiyatı", anchor="e")

        self.tree.column("id", width=50, stretch=False, anchor="center")
        self.tree.column("stok_kodu", width=120, stretch=False)
        self.tree.column("stok_adi", width=250)
        self.tree.column("kategori", width=120, stretch=False)
        self.tree.column("birim", width=80, stretch=False)
        self.tree.column("kdv_oran", width=80, stretch=False, anchor="e")
        self.tree.column("alis_fiyati", width=100, stretch=False, anchor="e")
        self.tree.column("satis_fiyati", width=100, stretch=False, anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self.kayit_secildi)
        self.tree.tag_configure('passive', foreground='gray')
        self._init_sayfalama(self.tree)

    def _load_and_configure_data(self):
        """Filtreler ve lookup'lar için gerekli veri sözlüklerini yükler."""
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT deger, id FROM genel_tanimlar WHERE grup=? AND firma_id=?", ("Stok Kategorisi", self.main_app.aktif_firma_id))
        self.kategori_dict = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute("SELECT deger, id FROM genel_tanimlar WHERE grup=? AND firma_id=?", ("Stok Birimi", self.main_app.aktif_firma_id))
        self.birim_dict = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        self.cmb_kategori_filtre['values'] = ["Tümü"] + list(self.kategori_dict.keys())
        self.cmb_kategori_filtre.set("Tümü")

        self.lookup_kategori.configure_lookup(
            title="Kategori Seç", data_dict=self.kategori_dict, on_new=lambda: self.yeni_genel_tanim("stok_kategorileri")
        )
        self.lookup_birim.configure_lookup(
            title="Birim Seç", data_dict=self.birim_dict, on_new=lambda: self.yeni_genel_tanim("stok_birimleri")
        )

    def yeni_genel_tanim(self, tablo_adi):
        yeni_kart = ac_kart_dialog(self, tablo_adi, firma_id=self.main_app.aktif_firma_id)
        if yeni_kart:
            self._load_and_configure_data()
        return yeni_kart

    def filtreleri_temizle(self):
        self.cmb_kategori_filtre.set("Tümü")
        self.cmb_durum_filtre.set("Aktif")
        self.ent_arama.delete(0, tk.END)
        self.listele()

    def disari_aktar(self, format_type):
        self._tum_veriyi_yukle()
        export_treeview_data(self.tree, "Stok Kartları", format_type)
        self.listele()

    def formu_temizle(self):
        self.selected_id = None
        self.ent_stok_adi.delete(0, tk.END)
        self.ent_stok_kodu.delete(0, tk.END)
        self.lookup_kategori.clear()
        self.lookup_birim.clear()
        self.ent_alis_fiyati.delete(0, tk.END)
        self.ent_satis_fiyati.delete(0, tk.END)
        self.ent_kdv_oran.delete(0, tk.END)
        self.ent_kdv_oran.insert(0, "20")
        self.ent_kritik_miktar.delete(0, tk.END)
        self.cmb_durum.set("Aktif")
        self.ent_stok_adi.focus_set()
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._sayfa_yuklenen = 0
        self._sayfa_tukendi = False
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            arama_metni = self.ent_arama.get().strip()
            secili_kategori = self.cmb_kategori_filtre.get()
            secili_durum = self.cmb_durum_filtre.get()

            # Stok kartlarını al (miktar/maliyet hesabı bilinçli olarak burada
            # yapılmaz; hareket tablosunda tam tarama gerektirir. Raporlar
            # core.services.stok_bakiye_ve_maliyet üzerinden kendileri hesaplar.)
            where_clauses = ["firma_id=?"]
            params = [self.main_app.aktif_firma_id]

            if secili_kategori != "Tümü":
                where_clauses.append("kategori = ?")
                params.append(secili_kategori)

            if secili_durum != "Tümü":
                where_clauses.append("durum = ?")
                params.append(1 if secili_durum == "Aktif" else 0)

            if arama_metni:
                where_clauses.append("(stok_adi LIKE ? OR stok_kodu LIKE ?)")
                params.extend([f"%{arama_metni}%", f"%{arama_metni}%"])

            self._sayfa_query = "SELECT id, stok_kodu, stok_adi, kategori, birim, alis_fiyati, satis_fiyati, durum, kdv_oran FROM stoklar"
            if where_clauses: self._sayfa_query += " WHERE " + " AND ".join(where_clauses)
            self._sayfa_query += " ORDER BY id DESC"
            self._sayfa_params = params
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Stok kartları yüklenemedi: {e}", parent=self)
        finally:
            if conn: conn.close()
        self._diger_sayfa_yukle()

    def _satirlari_ekle(self, rows):
        for stok in rows:
            stok_id, stok_kodu, stok_adi, kategori, birim, alis_fiyati, satis_fiyati, durum, kdv_oran = stok
            tags = []
            if durum == 0: tags.append('passive')
            self.tree.insert("", "end", values=(
                stok_id, stok_kodu, stok_adi, kategori, birim,
                f"{kdv_oran or 0:g}",
                format_currency(alis_fiyati), format_currency(satis_fiyati)
            ), tags=tuple(tags))

    def kayit_secildi(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items: return
        
        item_id = self.tree.item(selected_items[0], "values")[0]
        self.selected_id = item_id

        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stoklar WHERE id=?", (item_id,))
        data = cursor.fetchone()
        conn.close()

        if data:
            cols = [desc[0] for desc in cursor.description]
            stok_data = dict(zip(cols, data))

            self.formu_temizle() # Önce formu temizle
            self.selected_id = item_id # Sonra ID'yi ayarla

            self.ent_stok_adi.insert(0, stok_data.get('stok_adi', ''))
            self.ent_stok_kodu.insert(0, stok_data.get('stok_kodu', ''))
            self.ent_alis_fiyati.insert(0, format_currency(stok_data.get('alis_fiyati', 0)))
            self.ent_satis_fiyati.insert(0, format_currency(stok_data.get('satis_fiyati', 0)))
            self.ent_kdv_oran.delete(0, tk.END)
            self.ent_kdv_oran.insert(0, f"{stok_data.get('kdv_oran', 20):g}")
            self.ent_kritik_miktar.insert(0, f"{stok_data.get('kritik_miktar', 0):g}")
            self.cmb_durum.set("Aktif" if stok_data.get('durum', 1) == 1 else "Pasif")

            kategori_adi = stok_data.get('kategori', '')
            kategori_id = next((v for k, v in self.kategori_dict.items() if k == kategori_adi), None)
            if kategori_id: self.lookup_kategori.set(kategori_id)

            birim_adi = stok_data.get('birim', '')
            birim_id = next((v for k, v in self.birim_dict.items() if k == birim_adi), None)
            if birim_id: self.lookup_birim.set(birim_id)

    def kaydet_kart(self):
        stok_adi = self.ent_stok_adi.get().strip()
        if not stok_adi:
            messagebox.showerror("Hata", "Stok Adı boş bırakılamaz.", parent=self)
            return

        stok_data = {
            'id': self.selected_id,
            'stok_adi': stok_adi,
            'stok_kodu': self.ent_stok_kodu.get().strip(),
            'kategori': self.lookup_kategori.get_value() or '',
            'birim': self.lookup_birim.get_value() or '',
            'alis_fiyati': parse_currency(self.ent_alis_fiyati.get()),
            'satis_fiyati': parse_currency(self.ent_satis_fiyati.get()),
            'kdv_oran': parse_currency(self.ent_kdv_oran.get()),
            'kritik_miktar': parse_currency(self.ent_kritik_miktar.get()),
            'durum': 1 if self.cmb_durum.get() == "Aktif" else 0,
            'firma_id': self.main_app.aktif_firma_id
        }

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            kaydet_kart(cursor, "stoklar", stok_data)
            conn.commit()
            messagebox.showinfo("Başarılı", "Stok kartı başarıyla kaydedildi.", parent=self)
            self.formu_temizle()
            self.listele()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Bu stok adı veya kodu zaten mevcut.", parent=self)
            if conn: conn.rollback()
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {e}", parent=self)
            if conn: conn.rollback()
        finally:
            if conn: conn.close()

    def sil_kart(self):
        if not self.selected_id:
            messagebox.showwarning("Uyarı", "Lütfen silmek için listeden bir kart seçin.", parent=self)
            return

        stok_adi = self.ent_stok_adi.get()
        if not messagebox.askyesno("Silme Onayı", f"'{stok_adi}' adlı stok kartını silmek istediğinizden emin misiniz?", parent=self):
            return

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            kart_sil_service(cursor, "stoklar", self.selected_id, self.main_app.aktif_firma_id)
            conn.commit()
            messagebox.showinfo("Başarılı", "Stok kartı başarıyla silindi.", parent=self)
            self.formu_temizle()
            self.listele()
        except ValueError as e:
            if conn: conn.rollback()
            messagebox.showerror("Silme Hatası", str(e), parent=self)
        except Exception as e:
            if conn: conn.rollback()
            messagebox.showerror("Veritabanı Hatası", f"Silme işlemi sırasında bir hata oluştu:\n{e}", parent=self)
        finally:
            if conn: conn.close()

    def yenile(self):
        self.listele()
