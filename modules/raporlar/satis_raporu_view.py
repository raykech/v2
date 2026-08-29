# -*- coding: utf-8 -*-
import calendar
import tkinter as tk
from tkinter import ttk, messagebox
from core.db import veritabani_baglan
from utils.formatters import format_currency
from utils.export import export_treeview_data


AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# Yıllık görünümde her ay kartında gösterilecek satırlar
# (anahtar, etiket, tip, kalın_mı)
YILLIK_SATIRLAR = [
    ("satis_rakami",   "Satış",        "gelir", False),
    ("hizmet_gelir",   "Hzm. Gelir",   "gelir", False),
    ("gelir_toplam",   "Gelir Top.",   "gelir", True),
    ("cogs",           "Maliyet",      "gider", False),
    ("hizmet_gider",   "Hzm. Gider",   "gider", False),
    ("gider_toplam",   "Gider Top.",   "gider", True),
    ("sonuc",          "Sonuç",        "sonuc", True),
]

GELIR_RENK = "#198754"
GIDER_RENK = "#dc3545"
SONUC_RENK = "#0d6efd"


class SatisRaporuView(tk.Frame):
    """Kar/Zarar Raporu: Aylık ve Yıllık görünüm."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self._ay_kartlari = {}  # ay_no -> {metrik_key: deger_label}
        self._genel_etiketler = {}  # metrik_key -> deger_label
        self.create_widgets()

    # ------------------------------------------------------------
    # Arayüz
    # ------------------------------------------------------------
    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.aylik_tab = ttk.Frame(self.notebook)
        self.yillik_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.aylik_tab, text="Aylık")
        self.notebook.add(self.yillik_tab, text="Yıllık")

        self._create_aylik_widgets(self.aylik_tab)
        self._create_yillik_widgets(self.yillik_tab)

        self.notebook.bind("<<NotebookTabChanged>>", self._tab_degisti)

    def _create_aylik_widgets(self, parent):
        # Üst Alan: Ay seçimi + butonlar
        ust_frame = tk.LabelFrame(parent, text="Ay Seçimi", bg="#f5f7fb", padx=10, pady=8)
        ust_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(ust_frame, text="Ay:", bg="#f5f7fb").pack(side="left", padx=(0, 5))
        self.cmb_ay = ttk.Combobox(ust_frame, state="readonly", width=12, values=AYLAR)
        self.cmb_ay.set(AYLAR[0])
        self.cmb_ay.pack(side="left", padx=(0, 5))
        self.cmb_ay.bind("<<ComboboxSelected>>", lambda e: self.listele())

        btn_listele = tk.Button(ust_frame, text="Listele", command=self.listele)
        btn_listele.pack(side="left", padx=(5, 0))

        btn_excel = tk.Button(ust_frame, text="Excel'e Aktar",
                              command=lambda: self.disari_aktar('excel'))
        btn_excel.pack(side="right", padx=(5, 0))

        btn_pdf = tk.Button(ust_frame, text="PDF'e Aktar",
                            command=lambda: self.disari_aktar('pdf'))
        btn_pdf.pack(side="right", padx=(5, 0))

        # Liste Alanı
        tree_container = tk.Frame(parent)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            tree_container,
            columns=("aciklama", "tutar"),
            show="headings",
        )
        self.tree.heading("aciklama", text="Açıklama")
        self.tree.heading("tutar", text="Tutar", anchor="e")
        self.tree.column("aciklama", width=400)
        self.tree.column("tutar", width=180, stretch=False, anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.tag_configure('gelir', foreground=GELIR_RENK)
        self.tree.tag_configure('gider', foreground=GIDER_RENK)
        self.tree.tag_configure('toplam', font=('Arial', 10, 'bold'))
        self.tree.tag_configure('sonuc', font=('Arial', 12, 'bold'),
                                background='#ffe69c')

        self.lbl_donem = tk.Label(parent, text="", bg="#f5f7fb",
                                  font=("Arial", 10, "bold"))
        self.lbl_donem.pack(anchor="w", padx=10, pady=(0, 8))

    def _create_yillik_widgets(self, parent):
        # Yıl başlığı
        ust_yillik = tk.Frame(parent, bg="#f5f7fb")
        ust_yillik.pack(fill="x", padx=10, pady=(10, 5))
        self.lbl_yillik_yil = tk.Label(
            ust_yillik,
            text=f"YIL: {self.main_app.aktif_yil}",
            bg="#f5f7fb", font=("Arial", 12, "bold")
        )
        self.lbl_yillik_yil.pack(side="left")

        # 2 satır x 6 sütun ay kartları
        grid_frame = tk.Frame(parent, bg="#f5f7fb")
        grid_frame.pack(fill="both", expand=True, padx=10, pady=5)

        for c in range(6):
            grid_frame.columnconfigure(c, weight=1, uniform="ay")
        for r in range(2):
            grid_frame.rowconfigure(r, weight=1, uniform="ay")

        for i, ay_adi in enumerate(AYLAR):
            kart = tk.Frame(grid_frame, relief="groove", borderwidth=1,
                            bg="#ffffff", padx=6, pady=4)
            row = i // 6
            col = i % 6
            kart.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)

            # Ay başlığı
            tk.Label(kart, text=ay_adi, bg="#ffffff",
                     font=("Arial", 9, "bold"), anchor="w").grid(
                row=0, column=0, columnspan=2, sticky="ew", pady=(0, 2))

            # Her kalem için iki sütun: sol etiket, sağ değer (rakam sağa yaslı)
            ay_labels = {}
            for satir_idx, (key, baslik, tip, kalin) in enumerate(YILLIK_SATIRLAR, start=1):
                lbl_adi = tk.Label(kart, text=baslik, bg="#ffffff",
                                   font=("Arial", 8))
                if tip == "gelir":
                    lbl_adi.config(fg=GELIR_RENK)
                elif tip == "gider":
                    lbl_adi.config(fg=GIDER_RENK)
                if kalin:
                    lbl_adi.config(font=("Arial", 8, "bold"))

                lbl_deger = tk.Label(kart, text="-", bg="#ffffff",
                                     font=("Arial", 8), anchor="e")
                if tip == "gelir":
                    lbl_deger.config(fg=GELIR_RENK)
                elif tip == "gider":
                    lbl_deger.config(fg=GIDER_RENK)
                else:
                    lbl_deger.config(fg=SONUC_RENK)
                if kalin:
                    lbl_deger.config(font=("Arial", 8, "bold"))

                lbl_adi.grid(row=satir_idx, column=0, sticky="w", padx=(0, 2))
                lbl_deger.grid(row=satir_idx, column=1, sticky="e")
                kart.columnconfigure(0, weight=1)
                kart.columnconfigure(1, weight=1)

                ay_labels[key] = lbl_deger

            self._ay_kartlari[i + 1] = ay_labels

        # Genel durum (tüm yıl): sol gelirler, orta giderler, sağ sonuç
        genel_frame = tk.LabelFrame(parent, text="GENEL DURUM (TÜM YIL)",
                                    bg="#ffe69c", padx=10, pady=6,
                                    font=("Arial", 10, "bold"))
        genel_frame.pack(fill="x", padx=10, pady=10)

        genel_ic = tk.Frame(genel_frame, bg="#ffe69c")
        genel_ic.pack(fill="x", expand=True)

        # Sol: GELİRLER
        gelir_frame = tk.LabelFrame(genel_ic, text="GELİRLER", bg="#ffe69c",
                                    fg=GELIR_RENK, padx=8, pady=4,
                                    font=("Arial", 9, "bold"))
        gelir_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        for key, baslik, tip, kalin in YILLIK_SATIRLAR:
            if tip != "gelir":
                continue
            hucre = tk.Frame(gelir_frame, bg="#ffe69c")
            hucre.pack(fill="x", pady=1)
            lbl_adi = tk.Label(hucre, text=baslik, bg="#ffe69c", fg=GELIR_RENK,
                               font=("Arial", 9, "bold" if kalin else "normal"))
            lbl_adi.pack(side="left")
            lbl_deger = tk.Label(hucre, text="-", bg="#ffe69c", fg=GELIR_RENK,
                                 font=("Arial", 10, "bold" if kalin else "normal"),
                                 anchor="e")
            lbl_deger.pack(side="right", fill="x", expand=True)
            self._genel_etiketler[key] = lbl_deger

        # Orta: GİDERLER
        gider_frame = tk.LabelFrame(genel_ic, text="GİDERLER", bg="#ffe69c",
                                    fg=GIDER_RENK, padx=8, pady=4,
                                    font=("Arial", 9, "bold"))
        gider_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        for key, baslik, tip, kalin in YILLIK_SATIRLAR:
            if tip != "gider":
                continue
            hucre = tk.Frame(gider_frame, bg="#ffe69c")
            hucre.pack(fill="x", pady=1)
            lbl_adi = tk.Label(hucre, text=baslik, bg="#ffe69c", fg=GIDER_RENK,
                               font=("Arial", 9, "bold" if kalin else "normal"))
            lbl_adi.pack(side="left")
            lbl_deger = tk.Label(hucre, text="-", bg="#ffe69c", fg=GIDER_RENK,
                                 font=("Arial", 10, "bold" if kalin else "normal"),
                                 anchor="e")
            lbl_deger.pack(side="right", fill="x", expand=True)
            self._genel_etiketler[key] = lbl_deger

        # Sağ: SONUÇ (büyük ve iri)
        sonuc_frame = tk.Frame(genel_ic, bg="#ffe69c", padx=10, pady=4)
        sonuc_frame.pack(side="right", fill="y", expand=True)
        self.lbl_genel_sonuc = tk.Label(
            sonuc_frame, text="KÂR/ZARAR: -", bg="#ffe69c", fg=SONUC_RENK,
            font=("Arial", 16, "bold"), anchor="center"
        )
        self.lbl_genel_sonuc.pack(fill="both", expand=True)
        # sonuc için genel etiketi aynı tut (yıllık güncellemede kullanılır)
        self._genel_etiketler["sonuc"] = self.lbl_genel_sonuc

    def _tab_degisti(self, event=None):
        try:
            secili = self.notebook.tab(self.notebook.select(), "text")
        except Exception:
            return
        if secili == "Yıllık":
            self._yillik_listele()

    # ------------------------------------------------------------
    # Veri hesaplama
    # ------------------------------------------------------------
    def _ay_araligi(self, yil, ay_no):
        son_gun = calendar.monthrange(yil, ay_no)[1]
        bas = f"{yil}-{ay_no:02d}-01"
        bit = f"{yil}-{ay_no:02d}-{son_gun:02d}"
        return bas, bit

    def _ay_rapor_verileri(self, yil, ay_no):
        """Belirli bir ay için Kar/Zarar verilerini döndürür."""
        bas, bit = self._ay_araligi(yil, ay_no)
        conn = None
        try:
            conn = veritabani_baglan()
            c = conn.cursor()
            fid = self.main_app.aktif_firma_id

            # 1) Satış rakamı
            c.execute("""
                SELECT
                  (SELECT COALESCE(SUM(fs.alacak),0)
                   FROM fis_satirlari fs JOIN fisler f ON f.id = fs.fis_id
                   WHERE fs.hesap_turu='Stok' AND fs.firma_id=?
                     AND f.fis_turu='Satış Faturası' AND f.tarih BETWEEN ? AND ?)
                  -
                  (SELECT COALESCE(SUM(fs.borc),0)
                   FROM fis_satirlari fs JOIN fisler f ON f.id = fs.fis_id
                   WHERE fs.hesap_turu='Stok' AND fs.firma_id=?
                     AND f.fis_turu='Satış İade Faturası' AND f.tarih BETWEEN ? AND ?)
            """, (fid, bas, bit, fid, bas, bit))
            satis_rakami = c.fetchone()[0] or 0.0

            # 2) Hizmet kartı gelirleri
            c.execute("""
                SELECT COALESCE(SUM(CASE WHEN fs.alacak > 0 THEN fs.miktar * fs.birim_fiyat ELSE 0 END),0)
                     - COALESCE(SUM(CASE WHEN fs.borc > 0 THEN fs.miktar * fs.birim_fiyat ELSE 0 END),0)
                FROM fis_satirlari fs
                JOIN fisler f ON f.id = fs.fis_id
                JOIN hizmet_kartlari h ON h.id = fs.hesap_id
                WHERE fs.hesap_turu='Hizmet' AND fs.firma_id=?
                  AND h.tur='Gelir'
                  AND f.tarih BETWEEN ? AND ?
            """, (fid, bas, bit))
            hizmet_gelir = c.fetchone()[0] or 0.0

            gelir_toplam = satis_rakami + hizmet_gelir

            # 3) COGS (FIFO)
            cogs = self._cogs_hesapla(c, fid, bas, bit)

            # 4) Hizmet kartı giderleri
            c.execute("""
                SELECT COALESCE(SUM(CASE WHEN fs.borc > 0 THEN fs.miktar * fs.birim_fiyat ELSE 0 END),0)
                     - COALESCE(SUM(CASE WHEN fs.alacak > 0 THEN fs.miktar * fs.birim_fiyat ELSE 0 END),0)
                FROM fis_satirlari fs
                JOIN fisler f ON f.id = fs.fis_id
                JOIN hizmet_kartlari h ON h.id = fs.hesap_id
                WHERE fs.hesap_turu='Hizmet' AND fs.firma_id=?
                  AND h.tur='Gider'
                  AND f.tarih BETWEEN ? AND ?
            """, (fid, bas, bit))
            hizmet_gider = c.fetchone()[0] or 0.0

            gider_toplam = cogs + hizmet_gider
            sonuc = gelir_toplam - gider_toplam

            return {
                "ay": ay_no,
                "satis_rakami": satis_rakami,
                "hizmet_gelir": hizmet_gelir,
                "gelir_toplam": gelir_toplam,
                "cogs": cogs,
                "hizmet_gider": hizmet_gider,
                "gider_toplam": gider_toplam,
                "sonuc": sonuc,
            }
        finally:
            if conn:
                conn.close()

    # ------------------------------------------------------------
    # Aylık görünüm
    # ------------------------------------------------------------
    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        ay_no = AYLAR.index(self.cmb_ay.get()) + 1
        yil = self.main_app.aktif_yil
        bas, bit = self._ay_araligi(yil, ay_no)
        self.lbl_donem.config(
            text=f"DÖNEM: {bas}  →  {bit}  ({self.cmb_ay.get()} - {yil})"
        )

        veri = self._ay_rapor_verileri(yil, ay_no)
        sonuc = veri["sonuc"]

        # ---- Tabloyu doldur ----
        self.tree.insert("", "end", values=("SATIŞ RAKAMI", format_currency(veri["satis_rakami"])), tags=('gelir',))
        self.tree.insert("", "end", values=("HİZMET KARTI GELİRLERİ", format_currency(veri["hizmet_gelir"])), tags=('gelir',))
        self.tree.insert("", "end", values=("GELİRLER TOPLAMI", format_currency(veri["gelir_toplam"])), tags=('toplam',))

        self.tree.insert("", "end", values=("", ""))
        self.tree.insert("", "end", values=("SATILAN MALLARIN MALİYETİ (FIFO)", format_currency(veri["cogs"])), tags=('gider',))
        self.tree.insert("", "end", values=("HİZMET KARTI GİDERLERİ", format_currency(veri["hizmet_gider"])), tags=('gider',))
        self.tree.insert("", "end", values=("GİDERLER TOPLAMI", format_currency(veri["gider_toplam"])), tags=('toplam',))

        self.tree.insert("", "end", values=("", ""))
        if sonuc >= 0:
            sonuc_metni = f"KÂR: {format_currency(sonuc)}"
        else:
            sonuc_metni = f"ZARAR: {format_currency(-sonuc)}"
        self.tree.insert("", "end", values=("SONUÇ (KÂR / ZARAR)", sonuc_metni), tags=('sonuc',))

    # ------------------------------------------------------------
    # Yıllık görünüm
    # ------------------------------------------------------------
    def _yillik_listele(self):
        yil = self.main_app.aktif_yil
        self.lbl_yillik_yil.config(text=f"YIL: {yil}")

        toplamlar = {
            "satis_rakami": 0.0,
            "hizmet_gelir": 0.0,
            "gelir_toplam": 0.0,
            "cogs": 0.0,
            "hizmet_gider": 0.0,
            "gider_toplam": 0.0,
            "sonuc": 0.0,
        }

        for ay_no in range(1, 13):
            veri = self._ay_rapor_verileri(yil, ay_no)
            for key in toplamlar:
                toplamlar[key] += veri[key]

            ay_labels = self._ay_kartlari[ay_no]
            for key, baslik, tip, kalin in YILLIK_SATIRLAR:
                if key == "sonuc":
                    deger = veri[key]
                    if deger >= 0:
                        metin = f"KÂR {format_currency(deger)}"
                    else:
                        metin = f"ZARAR {format_currency(-deger)}"
                else:
                    metin = format_currency(veri[key])
                ay_labels[key].config(text=metin)

        # Genel toplamları yaz
        for key, baslik, tip, kalin in YILLIK_SATIRLAR:
            if key == "sonuc":
                deger = toplamlar[key]
                if deger >= 0:
                    metin = f"KÂR {format_currency(deger)}"
                else:
                    metin = f"ZARAR {format_currency(-deger)}"
            else:
                metin = format_currency(toplamlar[key])
            self._genel_etiketler[key].config(text=metin)

    # ------------------------------------------------------------
    # FIFO ve dışa aktarma
    # ------------------------------------------------------------
    def _cogs_hesapla(self, c, fid, bas, bit):
        c.execute("""
            SELECT f.tarih, fs.hesap_id, fs.miktar, fs.birim_fiyat, fs.borc, fs.alacak
            FROM fis_satirlari fs
            JOIN fisler f ON f.id = fs.fis_id
            WHERE fs.hesap_turu='Stok' AND fs.firma_id=? AND f.tarih <= ?
            ORDER BY f.tarih, f.id
        """, (fid, bit))

        katmanlar = {}
        cogs = 0.0
        for tarih, hesap_id, miktar, birim_fiyat, borc, alacak in c.fetchall():
            if hesap_id not in katmanlar:
                katmanlar[hesap_id] = []
            if borc and borc > 0:
                katmanlar[hesap_id].append([miktar, birim_fiyat])
            elif alacak and alacak > 0:
                maliyet = self._fifo_cikis(katmanlar[hesap_id], miktar)
                if bas <= tarih <= bit:
                    cogs += maliyet
        return cogs

    @staticmethod
    def _fifo_cikis(katmanlar, miktar):
        kalan = miktar
        toplam = 0.0
        while kalan > 0 and katmanlar:
            katman = katmanlar[0]
            kullanilacak = min(kalan, katman[0])
            toplam += kullanilacak * katman[1]
            katman[0] -= kullanilacak
            kalan -= kullanilacak
            if katman[0] <= 0:
                katmanlar.pop(0)
        return toplam

    def disari_aktar(self, format_type):
        export_treeview_data(self.tree, f"Kar/Zarar Raporu - {self.cmb_ay.get()} {self.main_app.aktif_yil}",
                             format_type)

    def yenile(self):
        pass
