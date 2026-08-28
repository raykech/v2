import tkinter as tk
from tkinter import ttk, messagebox
from core.db import veritabani_baglan
from utils.formatters import format_currency
from utils.export import export_treeview_data


class CekSenetCariRaporuView(tk.Frame):
    """Cari bazında çek/senet giriş, ciro ve iade özetini gösterir."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.create_widgets()

    def create_widgets(self):
        filter_frame = tk.LabelFrame(self, text="Filtrele", bg="#f5f7fb", padx=10, pady=10)
        filter_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(filter_frame, text="Ara:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.ent_arama = tk.Entry(filter_frame)
        self.ent_arama.pack(side="left", fill="x", expand=True)
        self.ent_arama.bind("<KeyRelease>", lambda e: self.listele())

        btn_excel = tk.Button(filter_frame, text="Excel'e Aktar", command=lambda: self.disari_aktar('excel'))
        btn_excel.pack(side="left", padx=(5, 0))

        btn_pdf = tk.Button(filter_frame, text="PDF'e Aktar", command=lambda: self.disari_aktar('pdf'))
        btn_pdf.pack(side="left", padx=(5, 0))

        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            tree_container,
            columns=("cari", "giris", "ciro", "iade", "toplam"),
            show="headings",
        )
        self.tree.heading("cari", text="Cari")
        self.tree.heading("giris", text="Giriş", anchor="e")
        self.tree.heading("ciro", text="Ciro", anchor="e")
        self.tree.heading("iade", text="İade", anchor="e")
        self.tree.heading("toplam", text="Toplam", anchor="e")

        self.tree.column("cari", width=300)
        self.tree.column("giris", width=140, stretch=False, anchor="e")
        self.tree.column("ciro", width=140, stretch=False, anchor="e")
        self.tree.column("iade", width=140, stretch=False, anchor="e")
        self.tree.column("toplam", width=150, stretch=False, anchor="e")

        self.tree.tag_configure('toplam', font=('Arial', 10, 'bold'), background='#d1e7dd')

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        query = """
            SELECT COALESCE(h.karsi_hesap_ismi, ''),
                   SUM(CASE WHEN h.durum = 'Portföyde' THEN c.tutar ELSE 0 END),
                   SUM(CASE WHEN h.durum = 'Cirolu' THEN c.tutar ELSE 0 END),
                   SUM(CASE WHEN h.durum = 'İade Edildi' THEN c.tutar ELSE 0 END)
            FROM cek_senet_hareketleri h
            JOIN cekler_senetler c ON c.id = h.cek_senet_id
            WHERE h.karsi_hesap_tipi = 'Cari' AND h.firma_id = ?
            GROUP BY h.karsi_hesap_id, h.karsi_hesap_ismi
        """
        params = [self.main_app.aktif_firma_id]
        arama = self.ent_arama.get().strip()
        if arama:
            query = """
                SELECT COALESCE(h.karsi_hesap_ismi, ''),
                       SUM(CASE WHEN h.durum = 'Portföyde' THEN c.tutar ELSE 0 END),
                       SUM(CASE WHEN h.durum = 'Cirolu' THEN c.tutar ELSE 0 END),
                       SUM(CASE WHEN h.durum = 'İade Edildi' THEN c.tutar ELSE 0 END)
                FROM cek_senet_hareketleri h
                JOIN cekler_senetler c ON c.id = h.cek_senet_id
                WHERE h.karsi_hesap_tipi = 'Cari' AND h.firma_id = ?
                  AND h.karsi_hesap_ismi LIKE ?
                GROUP BY h.karsi_hesap_id, h.karsi_hesap_ismi
            """
            params.append(f"%{arama}%")

        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            genel_giris = 0.0
            genel_ciro = 0.0
            genel_iade = 0.0
            for cari, giris, ciro, iade in rows:
                self.tree.insert("", "end", values=(
                    cari or "Belirtilmemiş",
                    format_currency(giris or 0),
                    format_currency(ciro or 0),
                    format_currency(iade or 0),
                    format_currency((giris or 0) + (ciro or 0) + (iade or 0)),
                ))
                genel_giris += giris or 0
                genel_ciro += ciro or 0
                genel_iade += iade or 0

            self.tree.insert("", "end", values=(
                "GENEL TOPLAM",
                format_currency(genel_giris),
                format_currency(genel_ciro),
                format_currency(genel_iade),
                format_currency(genel_giris + genel_ciro + genel_iade),
            ), tags=('toplam',))
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Cari raporu yüklenemedi: {e}", parent=self)

    def disari_aktar(self, format_type):
        export_treeview_data(self.tree, "Cari Bazlı Çek/Senet Özeti", format_type)

    def yenile(self):
        # Sekme geçişinde otomatik listeleme yok
        pass
