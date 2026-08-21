import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from core.db import veritabani_baglan
from utils.formatters import format_currency, format_date
from utils.export import export_treeview_data

class HesapEkstresiView(tk.Frame):
    def __init__(self, parent, main_app, hesap_turu):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.hesap_turu = hesap_turu
        self.hesap_dict = {}
        self.create_widgets()
        self._load_filter_data()

    def create_widgets(self):
        # Filtre Alanı
        filter_frame = tk.LabelFrame(self, text="Filtrele", bg="#f5f7fb", padx=10, pady=10)
        filter_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(filter_frame, text=f"{self.hesap_turu} Seç:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_hesap_filtre = ttk.Combobox(filter_frame, state="readonly", width=30)
        self.cmb_hesap_filtre.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Baş. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(10, 2))
        self.ent_bas_tarih = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bas_tarih.set_date(datetime(self.main_app.aktif_yil, 1, 1))
        self.ent_bas_tarih.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Bit. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(10, 2))
        self.ent_bit_tarih = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
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

        self.tree = ttk.Treeview(tree_container, columns=("tarih", "fis_no", "fis_turu", "aciklama", "borc", "alacak", "bakiye"), show="headings")
        self.tree.heading("tarih", text="Tarih")
        self.tree.heading("fis_no", text="Fiş No")
        self.tree.heading("fis_turu", text="Fiş Türü")
        self.tree.heading("aciklama", text="Açıklama")
        self.tree.heading("borc", text="Borç", anchor="e")
        self.tree.heading("alacak", text="Alacak", anchor="e")
        self.tree.heading("bakiye", text="Bakiye", anchor="e")

        self.tree.column("tarih", width=100, stretch=False, anchor="center")
        self.tree.column("fis_no", width=100, stretch=False)
        self.tree.column("fis_turu", width=180, stretch=False)
        self.tree.column("aciklama", width=300)
        self.tree.column("borc", width=120, stretch=False, anchor="e")
        self.tree.column("alacak", width=120, stretch=False, anchor="e")
        self.tree.column("bakiye", width=120, stretch=False, anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure('devir', background='#f0f0f0', font=('Arial', 9, 'bold'))
        self.tree.tag_configure('toplam', font=('Arial', 9, 'bold'))
        self.tree.tag_configure('bakiye', font=('Arial', 10, 'bold'), background='#d1e7dd')
        self.tree.tag_configure('separator', background='#cccccc')

    def _load_filter_data(self):
        tablo_map = {"Cari": "cariler", "Kasa": "kasalar", "Banka": "banka_hesaplari", "Stok": "stoklar"}
        ad_kolon_map = {"Cari": "unvan", "Kasa": "kasa_adi", "Banka": "hesap_adi", "Stok": "stok_adi"}
        tablo_adi = tablo_map.get(self.hesap_turu)
        ad_kolonu = ad_kolon_map.get(self.hesap_turu)
        if not tablo_adi: return

        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, {ad_kolonu} FROM {tablo_adi} WHERE durum=1 AND firma_id=?", (self.main_app.aktif_firma_id,))
        self.hesap_dict = {row[1]: row[0] for row in cursor.fetchall()}
        conn.close()
        self.cmb_hesap_filtre['values'] = list(self.hesap_dict.keys())
        if self.cmb_hesap_filtre['values']:
            self.cmb_hesap_filtre.set(self.cmb_hesap_filtre['values'][0])

    def listele(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        secili_hesap_adi = self.cmb_hesap_filtre.get()
        if not secili_hesap_adi:
            messagebox.showwarning("Uyarı", f"Lütfen bir {self.hesap_turu} seçin.", parent=self)
            return

        hesap_id = self.hesap_dict.get(secili_hesap_adi)
        bas_tarih = self.ent_bas_tarih.get_date().strftime("%Y-%m-%d")
        bit_tarih = self.ent_bit_tarih.get_date().strftime("%Y-%m-%d")

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            # 1. Devir Bakiyesini Hesapla
            cursor.execute("""
                SELECT SUM(borc) - SUM(alacak) FROM fis_satirlari fs
                JOIN fisler f ON f.id = fs.fis_id
                WHERE fs.hesap_turu = ? AND fs.hesap_id = ? AND f.tarih < ? AND fs.firma_id = ?
            """, (self.hesap_turu, hesap_id, bas_tarih, self.main_app.aktif_firma_id))
            devir_bakiye = cursor.fetchone()[0] or 0.0

            self.tree.insert("", "end", values=(
                "", "", "DEVİR", "",
                format_currency(devir_bakiye) if devir_bakiye > 0 else "",
                format_currency(-devir_bakiye) if devir_bakiye < 0 else "",
                format_currency(devir_bakiye)
            ), tags=('devir',))

            # 2. Tarih Aralığındaki Hareketleri Çek
            cursor.execute("""
                SELECT f.tarih, f.fis_no, f.fis_turu, fs.aciklama, fs.borc, fs.alacak
                FROM fis_satirlari fs
                JOIN fisler f ON f.id = fs.fis_id
                WHERE fs.hesap_turu = ? AND fs.hesap_id = ? AND f.tarih BETWEEN ? AND ? AND fs.firma_id = ?
                ORDER BY f.tarih, f.id
            """, (self.hesap_turu, hesap_id, bas_tarih, bit_tarih, self.main_app.aktif_firma_id))
            
            hareketler = cursor.fetchall()
            
            toplam_borc = 0.0
            toplam_alacak = 0.0

            bakiye = devir_bakiye
            for hareket in hareketler:
                tarih, fis_no, fis_turu, aciklama, borc, alacak = hareket
                bakiye += borc - alacak
                self.tree.insert("", "end", values=(
                    format_date(tarih),
                    fis_no,
                    fis_turu,
                    aciklama,
                    format_currency(borc),
                    format_currency(alacak),
                    format_currency(bakiye)
                ))
                toplam_borc += borc
                toplam_alacak += alacak

            # Alt Toplamlar
            self.tree.insert("", "end", values=("", "", "", "", "", "", ""), tags=('separator',))
            self.tree.insert("", "end", values=(
                "", "", "ARA TOPLAM", "",
                format_currency(toplam_borc),
                format_currency(toplam_alacak), ""
            ), tags=('toplam',))
            self.tree.insert("", "end", values=(
                "", "", "GENEL BAKİYE", "",
                format_currency(bakiye) if bakiye > 0 else "",
                format_currency(-bakiye) if bakiye < 0 else "",
                format_currency(bakiye)
            ), tags=('bakiye',))

        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Ekstre yüklenemedi: {e}", parent=self)
        finally:
            if conn: conn.close()

    def disari_aktar(self, format_type):
        secili_hesap_adi = self.cmb_hesap_filtre.get()
        report_title = f"{secili_hesap_adi} - {self.hesap_turu} Ekstresi"
        export_treeview_data(self.tree, report_title, format_type)

    def yenile(self):
        self._load_filter_data()
        self.listele()
