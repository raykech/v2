import tkinter as tk
from tkinter import ttk, messagebox
from core.db import veritabani_baglan
from utils.formatters import format_currency, format_date
from utils.export import export_treeview_data


class CekSenetPortfoyRaporuView(tk.Frame):
    """Tüm çek/senetlerin güncel durumunu listeler."""

    DURUMLAR = ["Portföyde", "Bankada Tahsilde", "Cirolu", "Tahsil Edildi", "İade Edildi"]

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.create_widgets()

    def create_widgets(self):
        filter_frame = tk.LabelFrame(self, text="Filtrele", bg="#f5f7fb", padx=10, pady=10)
        filter_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(filter_frame, text="Durum:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_durum = ttk.Combobox(filter_frame, state="readonly", width=18, values=["Tümü"] + self.DURUMLAR)
        self.cmb_durum.set("Tümü")
        self.cmb_durum.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_durum.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Tür:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_tur = ttk.Combobox(filter_frame, state="readonly", width=10, values=["Tümü", "Çek", "Senet"])
        self.cmb_tur.set("Tümü")
        self.cmb_tur.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_tur.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Ara:", bg="#f5f7fb").pack(side="left", padx=(10, 2))
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
            columns=("id", "seri_no", "turu", "banka", "vade", "tutar", "durum", "kesideci", "ciranta"),
            show="headings",
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("seri_no", text="Seri No")
        self.tree.heading("turu", text="Tür")
        self.tree.heading("banka", text="Banka")
        self.tree.heading("vade", text="Vade")
        self.tree.heading("tutar", text="Tutar", anchor="e")
        self.tree.heading("durum", text="Durum")
        self.tree.heading("kesideci", text="Keşideci")
        self.tree.heading("ciranta", text="Ciranta")

        self.tree.column("id", width=50, stretch=False, anchor="center")
        self.tree.column("seri_no", width=140, stretch=False)
        self.tree.column("turu", width=70, stretch=False, anchor="center")
        self.tree.column("banka", width=120, stretch=False)
        self.tree.column("vade", width=100, stretch=False, anchor="center")
        self.tree.column("tutar", width=120, stretch=False, anchor="e")
        self.tree.column("durum", width=140, stretch=False)
        self.tree.column("kesideci", width=140)
        self.tree.column("ciranta", width=140)

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        where = ["c.firma_id=?"]
        params = [self.main_app.aktif_firma_id]

        if self.cmb_durum.get() != "Tümü":
            where.append("guncel_durum.durum = ?")
            params.append(self.cmb_durum.get())
        if self.cmb_tur.get() != "Tümü":
            where.append("c.turu = ?")
            params.append(self.cmb_tur.get())
        arama = self.ent_arama.get().strip()
        if arama:
            where.append("(c.seri_no LIKE ? OR c.kesideci LIKE ? OR c.ciranta LIKE ?)")
            params.extend([f"%{arama}%", f"%{arama}%", f"%{arama}%"])

        query = f"""
            SELECT c.id, c.seri_no, c.turu, COALESCE(k.kurum_adi, c.banka, ''),
                   c.vade_tarihi, c.tutar, guncel_durum.durum,
                   c.kesideci, c.ciranta
            FROM cekler_senetler c
            LEFT JOIN banka_kurumlari k ON c.banka_id = k.id
            LEFT JOIN (
                SELECT h.cek_senet_id, h.durum
                FROM cek_senet_hareketleri h
                WHERE h.id = (
                    SELECT MAX(h2.id) FROM cek_senet_hareketleri h2
                    WHERE h2.cek_senet_id = h.cek_senet_id
                )
            ) guncel_durum ON guncel_durum.cek_senet_id = c.id
            WHERE {" AND ".join(where)}
            ORDER BY c.vade_tarihi
        """
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row in cursor.fetchall():
                self.tree.insert("", "end", values=(
                    row[0], row[1], row[2], row[3], format_date(row[4]),
                    format_currency(row[5]), row[6] or "Portföyde", row[7] or "", row[8] or "",
                ))
            conn.close()
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Portföy raporu yüklenemedi: {e}", parent=self)

    def disari_aktar(self, format_type):
        export_treeview_data(self.tree, "Çek/Senet Portföy Raporu", format_type)

    def yenile(self):
        # Sekme geçişinde otomatik listeleme yok
        pass
