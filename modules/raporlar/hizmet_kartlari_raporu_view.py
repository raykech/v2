import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from core.db import veritabani_baglan
from utils.formatters import format_currency
from utils.export import export_treeview_data


class HizmetKartlariRaporuView(tk.Frame):
    """Hizmet kartları mizan raporu: GELİRLER üstte, GİDERLER altta, gruplar altında kartlar."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.create_widgets()

    def create_widgets(self):
        # Filtre Alanı
        filter_frame = tk.LabelFrame(self, text="Filtrele", bg="#f5f7fb", padx=10, pady=10)
        filter_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(filter_frame, text="Baş. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.ent_bas_tarih = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bas_tarih.set_date(datetime(self.main_app.aktif_yil, 1, 1))
        self.ent_bas_tarih.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Bit. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.ent_bit_tarih = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bit_tarih.pack(side="left", padx=(0, 10))

        btn_listele = tk.Button(filter_frame, text="Raporu Getir", command=self.listele)
        btn_listele.pack(side="left", padx=(10, 0))

        btn_excel = tk.Button(filter_frame, text="Excel'e Aktar", command=lambda: self.disari_aktar('excel'))
        btn_excel.pack(side="left", padx=(5, 0))

        btn_pdf = tk.Button(filter_frame, text="PDF'e Aktar", command=lambda: self.disari_aktar('pdf'))
        btn_pdf.pack(side="left", padx=(5, 0))

        # Liste Alanı
        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            tree_container,
            columns=("kart_adi", "borc", "alacak", "borc_bakiye", "alacak_bakiye"),
            show="tree headings",
        )
        self.tree.heading("kart_adi", text="Hizmet Kartı")
        self.tree.heading("borc", text="Borç", anchor="e")
        self.tree.heading("alacak", text="Alacak", anchor="e")
        self.tree.heading("borc_bakiye", text="Borç Bakiye", anchor="e")
        self.tree.heading("alacak_bakiye", text="Alacak Bakiye", anchor="e")

        self.tree.column("#0", width=20, stretch=False)
        self.tree.column("kart_adi", width=300, minwidth=200)
        self.tree.column("borc", width=130, stretch=False, anchor="e")
        self.tree.column("alacak", width=130, stretch=False, anchor="e")
        self.tree.column("borc_bakiye", width=130, stretch=False, anchor="e")
        self.tree.column("alacak_bakiye", width=130, stretch=False, anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.tag_configure('bolum', font=('Arial', 10, 'bold'), foreground='#0d6efd', background='#eaf2ff')
        self.tree.tag_configure('grup', font=('Arial', 9, 'bold'))
        self.tree.tag_configure('toplam', font=('Arial', 10, 'bold'), foreground='#198754', background='#d1e7dd')

    def _fmt(self, deger):
        return f"{deger:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        bas_tarih = self.ent_bas_tarih.get_date().strftime("%Y-%m-%d")
        bit_tarih = self.ent_bit_tarih.get_date().strftime("%Y-%m-%d")

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            # Hizmet kartı bazında borç/alacak toplamları (grup bilgisiyle)
            cursor.execute(
                """
                SELECT h.id, h.kart_adi, h.tur, h.grup_id, COALESCE(g.grup_adi, 'Diğer'),
                       COALESCE(SUM(fs.borc), 0), COALESCE(SUM(fs.alacak), 0)
                FROM hizmet_kartlari h
                LEFT JOIN hizmet_kartlari_gruplari g ON g.id = h.grup_id
                LEFT JOIN fis_satirlari fs ON fs.hesap_turu = 'Hizmet' AND fs.hesap_id = h.id AND fs.firma_id = ?
                LEFT JOIN fisler f ON f.id = fs.fis_id AND f.tarih BETWEEN ? AND ?
                WHERE h.firma_id = ?
                GROUP BY h.id, h.kart_adi, h.tur, h.grup_id, g.grup_adi
                HAVING SUM(fs.borc) != 0 OR SUM(fs.alacak) != 0
                ORDER BY h.tur, g.grup_adi, h.kart_adi
                """,
                (self.main_app.aktif_firma_id, bas_tarih, bit_tarih, self.main_app.aktif_firma_id),
            )
            satirlar = cursor.fetchall()

            # Grup bazında topla
            bolumler = {
                "Gelir": {"label": "GELİRLER", "gruplar": {}, "cards": []},
                "Gider": {"label": "GİDERLER", "gruplar": {}, "cards": []},
            }

            for kart_id, kart_adi, tur, grup_id, grup_adi, borc, alacak in satirlar:
                borc = borc or 0.0
                alacak = alacak or 0.0
                bakiye = borc - alacak
                borc_bakiye = bakiye if bakiye > 0 else 0.0
                alacak_bakiye = -bakiye if bakiye < 0 else 0.0

                if tur not in bolumler:
                    continue
                bolum = bolumler[tur]

                if grup_adi not in bolum["gruplar"]:
                    bolum["gruplar"][grup_adi] = {
                        "borc": 0.0, "alacak": 0.0,
                        "borc_bakiye": 0.0, "alacak_bakiye": 0.0,
                        "cards": [],
                    }

                bolum["gruplar"][grup_adi]["cards"].append({
                    "adi": kart_adi, "borc": borc, "alacak": alacak,
                    "borc_bakiye": borc_bakiye, "alacak_bakiye": alacak_bakiye,
                })
                bolum["gruplar"][grup_adi]["borc"] += borc
                bolum["gruplar"][grup_adi]["alacak"] += alacak
                bolum["gruplar"][grup_adi]["borc_bakiye"] += borc_bakiye
                bolum["gruplar"][grup_adi]["alacak_bakiye"] += alacak_bakiye

            toplam_borc = 0.0
            toplam_alacak = 0.0
            toplam_borc_bakiye = 0.0
            toplam_alacak_bakiye = 0.0

            for tur in ("Gelir", "Gider"):
                bolum = bolumler[tur]
                if not bolum["gruplar"]:
                    continue

                # Bölüm toplamları (GELİRLER / GİDERLER satırında gösterilir)
                bolum_borc = sum(g["borc"] for g in bolum["gruplar"].values())
                bolum_alacak = sum(g["alacak"] for g in bolum["gruplar"].values())
                bolum_borc_bakiye = sum(g["borc_bakiye"] for g in bolum["gruplar"].values())
                bolum_alacak_bakiye = sum(g["alacak_bakiye"] for g in bolum["gruplar"].values())

                # Bölüm başlık satırı (varsayılan açık) - kendi toplamıyla
                bolum_id = self.tree.insert("", "end", iid=f"bolum_{tur}", values=(
                    bolum["label"],
                    self._fmt(bolum_borc), self._fmt(bolum_alacak),
                    self._fmt(bolum_borc_bakiye), self._fmt(bolum_alacak_bakiye),
                ), tags=('bolum',))
                self.tree.item(bolum_id, open=True)

                grup_sirasi = sorted(bolum["gruplar"].keys())
                for grup_adi in grup_sirasi:
                    grp = bolum["gruplar"][grup_adi]
                    grup_id = f"bolum_{tur}_{grup_adi}"
                    self.tree.insert(bolum_id, "end", iid=grup_id, values=(
                        f"  {grup_adi}",
                        self._fmt(grp["borc"]), self._fmt(grp["alacak"]),
                        self._fmt(grp["borc_bakiye"]), self._fmt(grp["alacak_bakiye"]),
                    ), tags=('grup',))
                    self.tree.item(grup_id, open=True)

                    for kart in grp["cards"]:
                        self.tree.insert(grup_id, "end", values=(
                            f"    {kart['adi']}",
                            self._fmt(kart["borc"]), self._fmt(kart["alacak"]),
                            self._fmt(kart["borc_bakiye"]), self._fmt(kart["alacak_bakiye"]),
                        ))

                    toplam_borc += grp["borc"]
                    toplam_alacak += grp["alacak"]
                    toplam_borc_bakiye += grp["borc_bakiye"]
                    toplam_alacak_bakiye += grp["alacak_bakiye"]

            # TOPLAM satırı
            self.tree.insert("", "end", values=(
                "TOPLAM",
                self._fmt(toplam_borc), self._fmt(toplam_alacak),
                self._fmt(toplam_borc_bakiye), self._fmt(toplam_alacak_bakiye),
            ), tags=('toplam',))

        except Exception as e:
            import traceback
            messagebox.showerror("Veri Yükleme Hatası", f"Hizmet kartları raporu yüklenemedi: {e}", parent=self)
            print(traceback.format_exc())
        finally:
            if conn:
                conn.close()

    def disari_aktar(self, format_type):
        export_treeview_data(self.tree, "Hizmet Kartları Raporu", format_type)

    def yenile(self):
        self.listele()
