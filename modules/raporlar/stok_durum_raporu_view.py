import tkinter as tk
from tkinter import ttk, messagebox
from core.db import veritabani_baglan
from utils.formatters import format_currency, format_miktar
from utils.export import export_treeview_data

class StokDurumRaporuView(tk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.kategori_dict = {}
        self.create_widgets()
        self._load_filter_data()

    def create_widgets(self):
        # Filtre Alanı
        filter_frame = tk.LabelFrame(self, text="Filtrele", bg="#f5f7fb", padx=10, pady=10)
        filter_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(filter_frame, text="Kategori:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_kategori_filtre = ttk.Combobox(filter_frame, state="readonly", width=20)
        self.cmb_kategori_filtre.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Durum:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_durum_filtre = ttk.Combobox(filter_frame, state="readonly", width=10, values=["Tümü", "Aktif", "Pasif"])
        self.cmb_durum_filtre.set("Aktif")
        self.cmb_durum_filtre.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Ara:", bg="#f5f7fb").pack(side="left", padx=(10, 2))
        self.ent_arama = tk.Entry(filter_frame)
        self.ent_arama.pack(side="left", fill="x", expand=True)

        btn_listele = tk.Button(filter_frame, text="Listele", command=self.listele)
        btn_listele.pack(side="left", padx=(10, 0))

        btn_excel = tk.Button(filter_frame, text="Excel'e Aktar", command=lambda: self.disari_aktar('excel'))
        btn_excel.pack(side="left", padx=(5, 0))

        btn_pdf = tk.Button(filter_frame, text="PDF'e Aktar", command=lambda: self.disari_aktar('pdf'))
        btn_pdf.pack(side="left", padx=(5, 0))

        # Liste Alanı
        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(tree_container, columns=("id", "stok_kodu", "stok_adi", "kategori", "birim", "mevcut_miktar", "kalan_maliyet"), show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("stok_kodu", text="Stok Kodu")
        self.tree.heading("stok_adi", text="Stok Adı")
        self.tree.heading("kategori", text="Kategori")
        self.tree.heading("birim", text="Birim")
        self.tree.heading("mevcut_miktar", text="Mevcut Miktar", anchor="e")
        self.tree.heading("kalan_maliyet", text="Maliyet Değeri", anchor="e")

        self.tree.column("id", width=50, stretch=False, anchor="center")
        self.tree.column("stok_kodu", width=120, stretch=False)
        self.tree.column("stok_adi", width=250)
        self.tree.column("kategori", width=120, stretch=False)
        self.tree.column("birim", width=80, stretch=False)
        self.tree.column("mevcut_miktar", width=100, stretch=False, anchor="e")
        self.tree.column("kalan_maliyet", width=100, stretch=False, anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.tag_configure('low_stock', foreground='red')

    def _load_filter_data(self):
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT deger, id FROM genel_tanimlar WHERE grup=? AND firma_id=?", ("Stok Kategorisi", self.main_app.aktif_firma_id))
        self.kategori_dict = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        self.cmb_kategori_filtre['values'] = ["Tümü"] + list(self.kategori_dict.keys())
        self.cmb_kategori_filtre.set("Tümü")

    def listele(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            # 1. Stok bakiyelerini hesapla
            cursor.execute("""
                SELECT fs.hesap_id, SUM(CASE WHEN fs.borc > 0 THEN fs.miktar WHEN fs.alacak > 0 THEN -fs.miktar ELSE 0 END)
                FROM fis_satirlari fs
                JOIN fisler f ON f.id = fs.fis_id
                WHERE fs.hesap_turu = 'Stok' AND fs.firma_id = ? GROUP BY fs.hesap_id
            """, (self.main_app.aktif_firma_id,))
            stock_balances = {row[0]: row[1] for row in cursor.fetchall()}

            # 2. FIFO Maliyetlerini hesapla
            cursor.execute("""
                SELECT fs.hesap_id, fs.miktar, fs.birim_fiyat FROM fis_satirlari fs
                JOIN fisler f ON f.id = fs.fis_id
                WHERE fs.hesap_turu = 'Stok' AND fs.borc > 0 AND fs.firma_id = ?
                ORDER BY f.tarih DESC, f.id DESC
            """, (self.main_app.aktif_firma_id,))
            purchase_transactions = cursor.fetchall()
            
            stock_costs = {stok_id: 0.0 for stok_id in stock_balances}
            remaining_quantities = stock_balances.copy()

            for stok_id, purchase_qty, unit_price in purchase_transactions:
                if stok_id in remaining_quantities and remaining_quantities[stok_id] > 0:
                    qty_to_use = min(remaining_quantities[stok_id], purchase_qty)
                    stock_costs[stok_id] += qty_to_use * unit_price
                    remaining_quantities[stok_id] -= qty_to_use

            # 3. Stok kartlarını filtreleyerek al
            where_clauses = ["firma_id=?"]
            params = [self.main_app.aktif_firma_id]
            if self.cmb_kategori_filtre.get() != "Tümü":
                where_clauses.append("kategori = ?")
                params.append(self.cmb_kategori_filtre.get())
            if self.cmb_durum_filtre.get() != "Tümü":
                where_clauses.append("durum = ?")
                params.append(1 if self.cmb_durum_filtre.get() == "Aktif" else 0)
            if self.ent_arama.get().strip():
                where_clauses.append("(stok_adi LIKE ? OR stok_kodu LIKE ?)")
                params.extend([f"%{self.ent_arama.get().strip()}%", f"%{self.ent_arama.get().strip()}%"])

            query = "SELECT id, stok_kodu, stok_adi, kategori, birim, kritik_miktar FROM stoklar WHERE " + " AND ".join(where_clauses)
            cursor.execute(query, params)
            stoklar = cursor.fetchall()

            # 4. Verileri birleştir ve Treeview'e ekle
            for stok in stoklar:
                stok_id, stok_kodu, stok_adi, kategori, birim, kritik_miktar = stok
                mevcut_miktar = stock_balances.get(stok_id, 0.0)
                kalan_maliyet = stock_costs.get(stok_id, 0.0)
                tags = ('low_stock',) if mevcut_miktar <= kritik_miktar else ()
                
                self.tree.insert("", "end", values=(
                    stok_id, stok_kodu, stok_adi, kategori, birim, 
                    format_miktar(mevcut_miktar), 
                    format_currency(kalan_maliyet)
                ), tags=tags)

        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Stok durum raporu yüklenemedi: {e}", parent=self)
        finally:
            if conn: conn.close()

    def disari_aktar(self, format_type):
        export_treeview_data(self.tree, "Stok Durum Raporu", format_type)

    def yenile(self):
        self._load_filter_data()
        self.listele()