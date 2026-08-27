import tkinter as tk
from tkinter import ttk, messagebox
from core.db import veritabani_baglan
from utils.formatters import format_currency
from utils.export import export_treeview_data


class CariBakiyeRaporuView(tk.Frame):
    """Tüm carilerin güncel borç/alacak bakiyelerini listeler."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.create_widgets()
        self.listele()

    def create_widgets(self):
        # Dışa Aktarma Butonları
        ust_frame = tk.Frame(self, bg="#f5f7fb")
        ust_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(ust_frame, text="Cari Bakiyeleri",
                 font=("Arial", 12, "bold"), bg="#f5f7fb").pack(side="left")

        btn_excel = tk.Button(ust_frame, text="Excel'e Aktar",
                              command=lambda: self.disari_aktar('excel'),
                              padx=10, pady=4)
        btn_excel.pack(side="right", padx=(5, 0))

        btn_pdf = tk.Button(ust_frame, text="PDF'e Aktar",
                            command=lambda: self.disari_aktar('pdf'),
                            padx=10, pady=4)
        btn_pdf.pack(side="right", padx=(5, 0))

        btn_yenile = tk.Button(ust_frame, text="Yenile",
                               command=self.listele,
                               padx=10, pady=4)
        btn_yenile.pack(side="right", padx=(5, 0))

        # Liste Alanı
        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            tree_container,
            columns=("id", "unvan", "tur", "borc_bakiye", "alacak_bakiye"),
            show="headings",
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("unvan", text="Cari Unvan")
        self.tree.heading("tur", text="Tür")
        self.tree.heading("borc_bakiye", text="Alacaklı (Bize Borçlu)", anchor="e")
        self.tree.heading("alacak_bakiye", text="Borçlu (Biz Borçlu)", anchor="e")

        self.tree.column("id", width=50, stretch=False, anchor="center")
        self.tree.column("unvan", width=300)
        self.tree.column("tur", width=100, stretch=False)
        self.tree.column("borc_bakiye", width=150, stretch=False, anchor="e")
        self.tree.column("alacak_bakiye", width=150, stretch=False, anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        # Toplamlar
        toplam_frame = tk.Frame(self, bg="#e9ecef")
        toplam_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.lbl_toplam_borc = tk.Label(toplam_frame, text="", bg="#e9ecef",
                                         font=("Arial", 10, "bold"))
        self.lbl_toplam_borc.pack(side="left", padx=20)
        self.lbl_toplam_alacak = tk.Label(toplam_frame, text="", bg="#e9ecef",
                                           font=("Arial", 10, "bold"))
        self.lbl_toplam_alacak.pack(side="left", padx=20)

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        conn = None
        try:
            conn = veritabani_baglan()
            c = conn.cursor()
            fid = self.main_app.aktif_firma_id

            # Her cari için net bakiye = SUM(borc) - SUM(alacak)
            # Pozitif = cari bize borçlu (bizim alacağımız)
            # Negatif = biz cariye borçlu (bizim borcumuz)
            c.execute("""
                SELECT c.id, c.unvan, c.tur,
                       COALESCE(SUM(fs.borc),0) - COALESCE(SUM(fs.alacak),0) as net_bakiye
                FROM cariler c
                LEFT JOIN fis_satirlari fs
                  ON fs.hesap_turu='Cari' AND fs.hesap_id = c.id AND fs.firma_id = ?
                LEFT JOIN fisler f ON f.id = fs.fis_id
                WHERE c.firma_id = ? AND (fs.fis_id IS NULL OR f.id IS NOT NULL)
                GROUP BY c.id
                HAVING net_bakiye != 0
                ORDER BY c.unvan
            """, (fid, fid))

            toplam_borc = 0.0
            toplam_alacak = 0.0

            for cari_id, unvan, tur, net_bakiye in c.fetchall():
                net_bakiye = net_bakiye or 0.0
                if net_bakiye > 0:
                    # Cari bize borçlu → Alacaklı (bizim alacağımız)
                    borc_bakiye = net_bakiye
                    alacak_bakiye = 0.0
                    toplam_alacak += net_bakiye
                else:
                    # Biz cariye borçlu → Borçlu (bizim borcumuz)
                    borc_bakiye = 0.0
                    alacak_bakiye = -net_bakiye
                    toplam_borc += -net_bakiye

                self.tree.insert("", "end", values=(
                    cari_id,
                    unvan,
                    tur,
                    format_currency(borc_bakiye) if borc_bakiye > 0 else "",
                    format_currency(alacak_bakiye) if alacak_bakiye > 0 else "",
                ))

            self.lbl_toplam_borc.config(
                text=f"TOPLAM BORÇ (Biz Cariye Borçlu): {format_currency(toplam_borc)}"
            )
            self.lbl_toplam_alacak.config(
                text=f"TOPLAM ALACAK (Cari Bize Borçlu): {format_currency(toplam_alacak)}"
            )

        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası",
                                 f"Cari bakiyeleri yüklenemedi: {e}", parent=self)
        finally:
            if conn:
                conn.close()

    def disari_aktar(self, format_type):
        export_treeview_data(self.tree, "Cari Bakiyeleri", format_type)

    def yenile(self):
        self.listele()