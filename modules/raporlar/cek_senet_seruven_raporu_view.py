import tkinter as tk
from tkinter import ttk, messagebox
from core.db import veritabani_baglan
from utils.formatters import format_currency, format_date
from utils.export import export_treeview_data


class CekSenetSeruvenRaporuView(tk.Frame):
    """Seçilen çek/senedin tüm hareketlerini gösterir."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.cek_dict = {}
        self.create_widgets()
        self._load_filter_data()

    def create_widgets(self):
        filter_frame = tk.LabelFrame(self, text="Çek/Senet Seç", bg="#f5f7fb", padx=10, pady=10)
        filter_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(filter_frame, text="Çek/Senet:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_cek = ttk.Combobox(filter_frame, state="readonly", width=50)
        self.cmb_cek.pack(side="left", padx=(0, 10))
        self.cmb_cek.bind("<<ComboboxSelected>>", lambda e: self.listele())

        btn_excel = tk.Button(filter_frame, text="Excel'e Aktar", command=lambda: self.disari_aktar('excel'))
        btn_excel.pack(side="left", padx=(5, 0))

        btn_pdf = tk.Button(filter_frame, text="PDF'e Aktar", command=lambda: self.disari_aktar('pdf'))
        btn_pdf.pack(side="left", padx=(5, 0))

        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            tree_container,
            columns=("tarih", "fis_turu", "durum", "karsi_hesap", "aciklama"),
            show="headings",
        )
        self.tree.heading("tarih", text="Tarih")
        self.tree.heading("fis_turu", text="Fiş Türü")
        self.tree.heading("durum", text="Durum")
        self.tree.heading("karsi_hesap", text="Karşı Hesap")
        self.tree.heading("aciklama", text="Açıklama")

        self.tree.column("tarih", width=100, stretch=False, anchor="center")
        self.tree.column("fis_turu", width=220, stretch=False)
        self.tree.column("durum", width=150, stretch=False)
        self.tree.column("karsi_hesap", width=200)
        self.tree.column("aciklama", width=300)

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

    def _load_filter_data(self):
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, seri_no, turu, tutar FROM cekler_senetler WHERE firma_id=? ORDER BY seri_no",
            (self.main_app.aktif_firma_id,),
        )
        self.cek_dict = {
            f"{row[1]} - {row[2]} - {format_currency(row[3])}": row[0]
            for row in cursor.fetchall()
        }
        conn.close()
        self.cmb_cek['values'] = list(self.cek_dict.keys())
        if self.cmb_cek['values']:
            self.cmb_cek.set(self.cmb_cek['values'][0])
            # Otomatik listeleme YAPILMAZ; kullanıcı seçim yapınca listele tetiklenir

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        secili = self.cmb_cek.get()
        if not secili:
            return
        cek_id = self.cek_dict.get(secili)
        if not cek_id:
            return

        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT h.islem_tarihi, COALESCE(f.fis_turu, ''), h.durum,
                       COALESCE(h.karsi_hesap_ismi, ''), COALESCE(h.aciklama, '')
                FROM cek_senet_hareketleri h
                LEFT JOIN fisler f ON f.id = h.fis_id
                WHERE h.cek_senet_id = ?
                ORDER BY h.islem_tarihi, h.id
                """,
                (cek_id,),
            )
            for row in cursor.fetchall():
                self.tree.insert("", "end", values=(
                    format_date(row[0]), row[1], row[2], row[3], row[4],
                ))
            conn.close()
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Serüven raporu yüklenemedi: {e}", parent=self)

    def disari_aktar(self, format_type):
        export_treeview_data(self.tree, "Çek/Senet Serüven Raporu", format_type)

    def yenile(self):
        self._load_filter_data()
