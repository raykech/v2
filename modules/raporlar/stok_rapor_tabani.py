# -*- coding: utf-8 -*-
"""
Stok raporları için ortak altyapı.

Tüm stok raporları aynı filtre satırını (tarih aralığı, kategori, durum, limit)
ve aynı liste/aktarım davranışını paylaşır; alt sınıflar yalnızca KOLONLAR'ı ve
listele() mantığını tanımlar.

Bu raporlar toplu liste üretir; tek bir ürünün hareketi istenirse
Stok Ekstresi alt sekmesi kullanılır — burada kart arama/lookup alanı YOKTUR.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from tkcalendar import DateEntry

from core.db import veritabani_baglan
from utils.formatters import format_date
from utils.export import export_treeview_data


# Limit seçeneği: (görünen metin, adet) — 0 = sınırsız
LIMIT_SECENEKLERI = [("İlk 20", 20), ("İlk 50", 50), ("İlk 100", 100), ("Tümü", 0)]


class StokRaporTabani(tk.Frame):
    """Stok raporlarının ortak taban sınıfı."""

    RAPOR_ADI = "Stok Raporu"
    # (anahtar, başlık, genişlik, anchor)
    KOLONLAR = ()
    # Limit seçici görünsün mü (sıralı listeler için True)
    LIMIT_VAR = True

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.kategori_listesi = []
        self.create_widgets()
        self._load_filter_data()

    # ---------------------------------------------------------------- arayüz
    def create_widgets(self):
        filter_frame = tk.LabelFrame(self, text="Filtrele", bg="#f5f7fb", padx=10, pady=8)
        filter_frame.pack(fill="x", padx=10, pady=(10, 6))

        tk.Label(filter_frame, text="Baş. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.ent_bas_tarih = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bas_tarih.set_date(datetime(self.main_app.aktif_yil, 1, 1))
        self.ent_bas_tarih.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Bit. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.ent_bit_tarih = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bit_tarih.set_date(datetime(self.main_app.aktif_yil, 12, 31))
        self.ent_bit_tarih.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Kategori:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_kategori_filtre = ttk.Combobox(filter_frame, state="readonly", width=18)
        self.cmb_kategori_filtre.pack(side="left", padx=(0, 10))

        tk.Label(filter_frame, text="Durum:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_durum_filtre = ttk.Combobox(
            filter_frame, state="readonly", width=8, values=["Aktif", "Tümü", "Pasif"])
        self.cmb_durum_filtre.set("Aktif")
        self.cmb_durum_filtre.pack(side="left", padx=(0, 10))

        if self.LIMIT_VAR:
            tk.Label(filter_frame, text="Limit:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
            self.cmb_limit = ttk.Combobox(
                filter_frame, state="readonly", width=8,
                values=[metin for metin, _ in LIMIT_SECENEKLERI])
            self.cmb_limit.set("İlk 20")
            self.cmb_limit.pack(side="left", padx=(0, 10))

        tk.Button(filter_frame, text="Listele", command=self.listele).pack(side="left", padx=(0, 5))
        tk.Button(filter_frame, text="Excel'e Aktar",
                  command=lambda: self.disari_aktar('excel')).pack(side="left", padx=(0, 5))
        tk.Button(filter_frame, text="PDF'e Aktar",
                  command=lambda: self.disari_aktar('pdf')).pack(side="left")

        # Liste Alanı
        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        kolon_ids = tuple(k[0] for k in self.KOLONLAR)
        self.tree = ttk.Treeview(tree_container, columns=kolon_ids, show="headings")
        for anahtar, baslik, genislik, anchor in self.KOLONLAR:
            self.tree.heading(anahtar, text=baslik, anchor=anchor)
            # Metin sütunları esner, sayısal sütunlar sabit kalır
            self.tree.column(anahtar, width=genislik, anchor=anchor,
                             stretch=(anchor == "w"))

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.tag_configure('toplam', font=('Arial', 10, 'bold'),
                                background='#d1e7dd')
        self.tree.tag_configure('pozitif', foreground='#198754')
        self.tree.tag_configure('negatif', foreground='#dc3545')
        self.tree.tag_configure('uyari', foreground='#fd7e14')
        self.taglar()

        self.lbl_durum = tk.Label(self, text="", bg="#f5f7fb", anchor="w",
                                  font=("Arial", 9))
        self.lbl_durum.pack(fill="x", padx=12, pady=(0, 8))

    def taglar(self):
        """Alt sınıflar özel treeview etiketlerini burada tanımlar."""
        pass

    # ---------------------------------------------------------------- filtre
    def _load_filter_data(self):
        secili = self.cmb_kategori_filtre.get()

        conn = veritabani_baglan()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT deger FROM genel_tanimlar WHERE grup=? AND firma_id=? ORDER BY deger",
                ("Stok Kategorisi", self.main_app.aktif_firma_id),
            )
            self.kategori_listesi = [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()

        degerler = ["Tümü"] + self.kategori_listesi
        self.cmb_kategori_filtre['values'] = degerler
        self.cmb_kategori_filtre.set(secili if secili in degerler else "Tümü")

    def tarih_araligi(self):
        """Filtredeki başlangıç/bitiş tarihlerini ISO (YYYY-MM-DD) döndürür."""
        return (self.ent_bas_tarih.get_date().strftime("%Y-%m-%d"),
                self.ent_bit_tarih.get_date().strftime("%Y-%m-%d"))

    def limit(self):
        if not self.LIMIT_VAR:
            return 0
        secili = self.cmb_limit.get()
        for metin, adet in LIMIT_SECENEKLERI:
            if metin == secili:
                return adet
        return 20

    def stok_sartlari(self):
        """stoklar tablosu (takma ad: s) için WHERE parçası ve parametreler."""
        sartlar = ["s.firma_id = ?"]
        params = [self.main_app.aktif_firma_id]

        kategori = self.cmb_kategori_filtre.get()
        if kategori and kategori != "Tümü":
            sartlar.append("s.kategori = ?")
            params.append(kategori)

        durum = self.cmb_durum_filtre.get()
        if durum and durum != "Tümü":
            sartlar.append("s.durum = ?")
            params.append(1 if durum == "Aktif" else 0)

        return " AND ".join(sartlar), params

    def stok_kartlari(self, cursor, alanlar="id, stok_kodu, stok_adi, kategori, birim"):
        """Filtreye uyan stok kartlarını [(id, kod, ad, kategori, birim), ...] olarak döndürür."""
        sart, params = self.stok_sartlari()
        cursor.execute(f"SELECT {alanlar} FROM stoklar s WHERE {sart}", params)
        return cursor.fetchall()

    # ---------------------------------------------------------------- yardımcılar
    def temizle(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def durum_yaz(self, metin):
        self.lbl_durum.config(text=metin)

    def donem_bilgisi(self, kayit_sayisi, ek=""):
        bas, bit = self.tarih_araligi()
        metin = (f"Dönem: {format_date(bas)} – {format_date(bit)}   |   "
                 f"Kart sayısı: {kayit_sayisi}")
        if ek:
            metin = f"{metin}   |   {ek}"
        self.durum_yaz(metin)

    def hata_goster(self, hata):
        messagebox.showerror("Veri Yükleme Hatası",
                             f"{self.RAPOR_ADI} yüklenemedi: {hata}", parent=self)

    def disari_aktar(self, format_type):
        bas, bit = self.tarih_araligi()
        export_treeview_data(self.tree, f"{self.RAPOR_ADI} {bas}_{bit}", format_type)

    def listele(self):
        raise NotImplementedError

    def yenile(self):
        # Sekme geçişinde otomatik listeleme yapılmaz (kasıntı engeli);
        # yalnızca kategori listesi tazelenir, kullanıcı "Listele" ile yükler.
        try:
            self._load_filter_data()
        except Exception as e:
            self.hata_goster(e)
