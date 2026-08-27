import calendar
import tkinter as tk
from tkinter import ttk, messagebox
from core.db import veritabani_baglan
from utils.formatters import format_currency
from utils.export import export_treeview_data


AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


class SatisRaporuView(tk.Frame):
    """Aylık Satış Raporu: satış rakamı, hizmet gelirleri, maliyet, giderler, kâr/zarar."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.create_widgets()
        self.listele()

    def create_widgets(self):
        # Üst Alan: Ay seçimi + butonlar
        ust_frame = tk.LabelFrame(self, text="Ay Seçimi", bg="#f5f7fb", padx=10, pady=8)
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
        tree_container = tk.Frame(self)
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

        self.tree.tag_configure('gelir', foreground="#198754")
        self.tree.tag_configure('gider', foreground="#dc3545")
        self.tree.tag_configure('toplam', font=('Arial', 10, 'bold'))
        self.tree.tag_configure('sonuc', font=('Arial', 12, 'bold'),
                                background='#ffe69c')

        self.lbl_donem = tk.Label(self, text="", bg="#f5f7fb",
                                  font=("Arial", 10, "bold"))
        self.lbl_donem.pack(anchor="w", padx=10, pady=(0, 8))

    def _ay_araligi(self):
        """Seçili ayın ilk ve son gününü döndürür (aktif yıl içinde)."""
        ay_no = AYLAR.index(self.cmb_ay.get()) + 1
        yil = self.main_app.aktif_yil
        son_gun = calendar.monthrange(yil, ay_no)[1]
        bas = f"{yil}-{ay_no:02d}-01"
        bit = f"{yil}-{ay_no:02d}-{son_gun:02d}"
        return bas, bit

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        bas, bit = self._ay_araligi()
        self.lbl_donem.config(
            text=f"DÖNEM: {bas}  →  {bit}  ({self.cmb_ay.get()} - {self.main_app.aktif_yil})"
        )

        conn = None
        try:
            conn = veritabani_baglan()
            c = conn.cursor()
            fid = self.main_app.aktif_firma_id

            # 1) Satış rakamı: Satış Faturası'ndaki Stok alacak (net, KDV hariç)
            #    - Satış İade'deki Stok borç düşülür
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

            # 2) Hizmet kartı gelirleri (tur='Gelir') - net (iade düşülür)
            c.execute("""
                SELECT COALESCE(SUM(fs.alacak),0) - COALESCE(SUM(fs.borc),0)
                FROM fis_satirlari fs
                JOIN fisler f ON f.id = fs.fis_id
                JOIN hizmet_kartlari h ON h.id = fs.hesap_id
                WHERE fs.hesap_turu='Hizmet' AND fs.firma_id=?
                  AND h.tur='Gelir'
                  AND f.tarih BETWEEN ? AND ?
            """, (fid, bas, bit))
            hizmet_gelir = c.fetchone()[0] or 0.0

            gelir_toplam = satis_rakami + hizmet_gelir

            # 3) Satılan malların maliyeti (FIFO)
            cogs = self._cogs_hesapla(c, fid, bas, bit)

            # 4) Hizmet kartı giderleri (tur='Gider') - net (iade düşülür)
            c.execute("""
                SELECT COALESCE(SUM(fs.borc),0) - COALESCE(SUM(fs.alacak),0)
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

            # ---- Tabloyu doldur ----
            self.tree.insert("", "end", values=("SATIŞ RAKAMI", format_currency(satis_rakami)), tags=('gelir',))
            self.tree.insert("", "end", values=("HİZMET KARTI GELİRLERİ", format_currency(hizmet_gelir)), tags=('gelir',))
            self.tree.insert("", "end", values=("GELİRLER TOPLAMI", format_currency(gelir_toplam)), tags=('toplam',))

            self.tree.insert("", "end", values=("", ""))
            self.tree.insert("", "end", values=("SATILAN MALLARIN MALİYETİ (FIFO)", format_currency(cogs)), tags=('gider',))
            self.tree.insert("", "end", values=("HİZMET KARTI GİDERLERİ", format_currency(hizmet_gider)), tags=('gider',))
            self.tree.insert("", "end", values=("GİDERLER TOPLAMI", format_currency(gider_toplam)), tags=('toplam',))

            self.tree.insert("", "end", values=("", ""))
            if sonuc >= 0:
                sonuc_metni = f"KÂR: {format_currency(sonuc)}"
            else:
                sonuc_metni = f"ZARAR: {format_currency(-sonuc)}"
            self.tree.insert("", "end", values=("SONUÇ (KÂR / ZARAR)", sonuc_metni), tags=('sonuc',))

        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası",
                                 f"Satış raporu yüklenemedi: {e}", parent=self)
        finally:
            if conn:
                conn.close()

    def _cogs_hesapla(self, c, fid, bas, bit):
        """Seçilen ayda satılan stokların FIFO maliyetini hesaplar."""
        c.execute("""
            SELECT f.tarih, fs.hesap_id, fs.miktar, fs.birim_fiyat, fs.borc, fs.alacak
            FROM fis_satirlari fs
            JOIN fisler f ON f.id = fs.fis_id
            WHERE fs.hesap_turu='Stok' AND fs.firma_id=? AND f.tarih <= ?
            ORDER BY f.tarih, f.id
        """, (fid, bit))

        katmanlar = {}  # hesap_id -> [kalan, birim_fiyat] listesi
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
        """FIFO katmanlarından çıkış yapar ve çıkış maliyetini döndürür."""
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
        export_treeview_data(self.tree, f"Satış Raporu - {self.cmb_ay.get()} {self.main_app.aktif_yil}",
                             format_type)

    def yenile(self):
        self.listele()