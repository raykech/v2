import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from core.db import veritabani_baglan
from core.services import kdv_hesap_idleri
from utils.formatters import format_currency, format_date
from utils.export import export_treeview_data


class KdvRaporuView(tk.Frame):
    """191 İndirilecek / 391 Hesaplanan KDV hareketlerini tarih aralığıyla raporlar."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.kdv_ids = (None, None)  # (indirilecek, hesaplanan)
        self.kdv_adlari = {}
        self.create_widgets()
        self._load_kdv_hesaplari()

    def create_widgets(self):
        # Filtre Alanı
        filter_frame = tk.LabelFrame(self, text="Filtrele", bg="#f5f7fb", padx=10, pady=10)
        filter_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(filter_frame, text="Baş. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(10, 2))
        self.ent_bas_tarih = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bas_tarih.set_date(datetime(self.main_app.aktif_yil, 1, 1))
        self.ent_bas_tarih.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Bit. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(10, 2))
        self.ent_bit_tarih = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bit_tarih.set_date(datetime(self.main_app.aktif_yil, 12, 31))
        self.ent_bit_tarih.pack(side="left", padx=(0, 10))

        btn_listele = tk.Button(filter_frame, text="Listele", command=self.listele)
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
            columns=("tarih", "fis_no", "fis_turu", "hesap_adi", "aciklama", "borc", "alacak"),
            show="headings",
        )
        self.tree.heading("tarih", text="Tarih")
        self.tree.heading("fis_no", text="Fiş No")
        self.tree.heading("fis_turu", text="Fiş Türü")
        self.tree.heading("hesap_adi", text="KDV Hesabı")
        self.tree.heading("aciklama", text="Açıklama")
        self.tree.heading("borc", text="Borç (191 İndirilecek)", anchor="e")
        self.tree.heading("alacak", text="Alacak (391 Hesaplanan)", anchor="e")

        self.tree.column("tarih", width=100, stretch=False, anchor="center")
        self.tree.column("fis_no", width=110, stretch=False)
        self.tree.column("fis_turu", width=180, stretch=False)
        self.tree.column("hesap_adi", width=140, stretch=False)
        self.tree.column("aciklama", width=300)
        self.tree.column("borc", width=130, stretch=False, anchor="e")
        self.tree.column("alacak", width=130, stretch=False, anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.tag_configure('ay_toplam', font=('Arial', 9, 'bold'), background='#f0f0f0')
        self.tree.tag_configure('genel_toplam', font=('Arial', 10, 'bold'), background='#d1e7dd')

        # Özet Alanı
        ozet_frame = tk.Frame(self, bg="#e9ecef")
        ozet_frame.pack(fill="x", padx=10, pady=(0, 10))
        ozet_frame.grid_columnconfigure(1, weight=1)

        tk.Label(ozet_frame, text="191 İndirilecek KDV Toplamı:", font=("Arial", 9, "bold"), bg="#e9ecef").grid(row=0, column=0, sticky="e", padx=5)
        self.lbl_toplam_191 = tk.Label(ozet_frame, text="0,00 TL", font=("Arial", 9), bg="#e9ecef", width=16, anchor="e")
        self.lbl_toplam_191.grid(row=0, column=1, sticky="e")

        tk.Label(ozet_frame, text="391 Hesaplanan KDV Toplamı:", font=("Arial", 9, "bold"), bg="#e9ecef").grid(row=1, column=0, sticky="e", padx=5)
        self.lbl_toplam_391 = tk.Label(ozet_frame, text="0,00 TL", font=("Arial", 9), bg="#e9ecef", width=16, anchor="e")
        self.lbl_toplam_391.grid(row=1, column=1, sticky="e")

        tk.Label(ozet_frame, text="Ödenecek / Devreden KDV (391 - 191):", font=("Arial", 10, "bold"), bg="#e9ecef").grid(row=2, column=0, sticky="e", padx=5)
        self.lbl_kdv_farki = tk.Label(ozet_frame, text="0,00 TL", font=("Arial", 10, "bold"), bg="#e9ecef", width=16, anchor="e")
        self.lbl_kdv_farki.grid(row=2, column=1, sticky="e")

    def _load_kdv_hesaplari(self):
        conn = veritabani_baglan()
        try:
            cursor = conn.cursor()
            self.kdv_ids = kdv_hesap_idleri(cursor, self.main_app.aktif_firma_id)
            kdv_ids = [kid for kid in self.kdv_ids if kid]
            if kdv_ids:
                placeholders = ", ".join("?" * len(kdv_ids))
                cursor.execute(
                    f"SELECT id, kart_adi FROM hizmet_kartlari WHERE id IN ({placeholders})",
                    kdv_ids,
                )
                self.kdv_adlari = {row[0]: row[1] for row in cursor.fetchall()}
            else:
                self.kdv_adlari = {}
        finally:
            conn.close()

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        indirilecek_id, hesaplanan_id = self.kdv_ids
        if not indirilecek_id and not hesaplanan_id:
            messagebox.showwarning("Uyarı", "KDV hesabı (191/391) tanımlı değil. Önce Tanımlar > Hizmet Kartları bölümünden KDV hesaplarını oluşturun.", parent=self)
            return

        bas_tarih = self.ent_bas_tarih.get_date().strftime("%Y-%m-%d")
        bit_tarih = self.ent_bit_tarih.get_date().strftime("%Y-%m-%d")

        kdv_ids = [kid for kid in (indirilecek_id, hesaplanan_id) if kid]
        placeholders = ", ".join("?" * len(kdv_ids))

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT f.tarih, f.fis_no, f.fis_turu, fs.hesap_id, fs.aciklama, fs.borc, fs.alacak
                FROM fis_satirlari fs
                JOIN fisler f ON f.id = fs.fis_id
                WHERE fs.hesap_id IN ({placeholders})
                  AND f.tarih BETWEEN ? AND ?
                  AND fs.firma_id = ?
                ORDER BY f.tarih, f.id, fs.id
            """, kdv_ids + [bas_tarih, bit_tarih, self.main_app.aktif_firma_id])

            hareketler = cursor.fetchall()

            toplam_191 = 0.0
            toplam_391 = 0.0
            son_ay = None
            ay_191 = 0.0
            ay_391 = 0.0

            def _ay_toplam_satiri_yaz():
                if son_ay is not None:
                    self.tree.insert("", "end", values=(
                        f"{son_ay} AY TOPLAMI", "", "", "", "",
                        format_currency(ay_191), format_currency(ay_391)
                    ), tags=('ay_toplam',))

            for tarih, fis_no, fis_turu, hesap_id, aciklama, borc, alacak in hareketler:
                ay = tarih[:7]
                if ay != son_ay:
                    _ay_toplam_satiri_yaz()
                    son_ay = ay
                    ay_191 = 0.0
                    ay_391 = 0.0

                borc = borc or 0.0
                alacak = alacak or 0.0
                if hesap_id == indirilecek_id:
                    ay_191 += borc
                    toplam_191 += borc
                if hesap_id == hesaplanan_id:
                    ay_391 += alacak
                    toplam_391 += alacak

                self.tree.insert("", "end", values=(
                    format_date(tarih),
                    fis_no,
                    fis_turu,
                    self.kdv_adlari.get(hesap_id, ""),
                    aciklama,
                    format_currency(borc),
                    format_currency(alacak),
                ))

            _ay_toplam_satiri_yaz()

            self.tree.insert("", "end", values=(
                "", "", "", "GENEL TOPLAM", "",
                format_currency(toplam_191), format_currency(toplam_391)
            ), tags=('genel_toplam',))

            self.lbl_toplam_191.config(text=format_currency(toplam_191))
            self.lbl_toplam_391.config(text=format_currency(toplam_391))
            self.lbl_kdv_farki.config(text=format_currency(toplam_391 - toplam_191))

        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"KDV raporu yüklenemedi: {e}", parent=self)
        finally:
            if conn:
                conn.close()

    def disari_aktar(self, format_type):
        export_treeview_data(self.tree, "KDV Raporu", format_type)

    def yenile(self):
        self._load_kdv_hesaplari()
        self.listele()
