import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from core.db import veritabani_baglan
from utils.formatters import format_currency, format_date
from utils.export import export_treeview_data


class CekSenetVadeRaporuView(tk.Frame):
    """Çek/senetleri vade dilimlerine göre özetler."""

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

        btn_excel = tk.Button(filter_frame, text="Excel'e Aktar", command=lambda: self.disari_aktar('excel'))
        btn_excel.pack(side="left", padx=(5, 0))

        btn_pdf = tk.Button(filter_frame, text="PDF'e Aktar", command=lambda: self.disari_aktar('pdf'))
        btn_pdf.pack(side="left", padx=(5, 0))

        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            tree_container,
            columns=("dilim", "adet", "toplam_tutar"),
            show="headings",
        )
        self.tree.heading("dilim", text="Vade Dilimi")
        self.tree.heading("adet", text="Adet", anchor="e")
        self.tree.heading("toplam_tutar", text="Toplam Tutar", anchor="e")

        self.tree.column("dilim", width=250)
        self.tree.column("adet", width=100, stretch=False, anchor="e")
        self.tree.column("toplam_tutar", width=150, stretch=False, anchor="e")

        self.tree.tag_configure('toplam', font=('Arial', 10, 'bold'), background='#d1e7dd')

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill="both", expand=True)

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

        query = f"""
            SELECT c.vade_tarihi, c.tutar, guncel_durum.durum
            FROM cekler_senetler c
            LEFT JOIN (
                SELECT h.cek_senet_id, h.durum
                FROM cek_senet_hareketleri h
                WHERE h.id = (
                    SELECT MAX(h2.id) FROM cek_senet_hareketleri h2
                    WHERE h2.cek_senet_id = h.cek_senet_id
                )
            ) guncel_durum ON guncel_durum.cek_senet_id = c.id
            WHERE {" AND ".join(where)}
        """
        dilimler = {
            "Vadesi Geçmiş": {"adet": 0, "tutar": 0.0},
            "0 - 30 Gün": {"adet": 0, "tutar": 0.0},
            "31 - 60 Gün": {"adet": 0, "tutar": 0.0},
            "61 - 90 Gün": {"adet": 0, "tutar": 0.0},
            "90+ Gün": {"adet": 0, "tutar": 0.0},
        }

        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute(query, params)
            bugun = date.today()
            for vade_tarihi, tutar, durum in cursor.fetchall():
                if not vade_tarihi:
                    continue
                try:
                    vade = date.fromisoformat(vade_tarihi)
                except ValueError:
                    continue
                gun_farki = (vade - bugun).days
                if gun_farki < 0:
                    dilim = "Vadesi Geçmiş"
                elif gun_farki <= 30:
                    dilim = "0 - 30 Gün"
                elif gun_farki <= 60:
                    dilim = "31 - 60 Gün"
                elif gun_farki <= 90:
                    dilim = "61 - 90 Gün"
                else:
                    dilim = "90+ Gün"
                dilimler[dilim]["adet"] += 1
                dilimler[dilim]["tutar"] += tutar or 0
            conn.close()

            genel_adet = 0
            genel_tutar = 0.0
            for dilim, veri in dilimler.items():
                self.tree.insert("", "end", values=(
                    dilim, veri["adet"], format_currency(veri["tutar"])
                ))
                genel_adet += veri["adet"]
                genel_tutar += veri["tutar"]

            self.tree.insert("", "end", values=(
                "GENEL TOPLAM", genel_adet, format_currency(genel_tutar)
            ), tags=('toplam',))
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Vade raporu yüklenemedi: {e}", parent=self)

    def disari_aktar(self, format_type):
        export_treeview_data(self.tree, "Çek/Senet Vade Takvimi", format_type)

    def yenile(self):
        # Sekme geçişinde otomatik listeleme yok
        pass
