# -*- coding: utf-8 -*-
"""En Çok Hareket Gören Ürünler raporu (fiş satırı sayısına göre)."""
from core.db import veritabani_baglan
from core.services import stok_donem_ozeti, stok_ozet_getir
from utils.formatters import format_currency, format_date, format_miktar

from .stok_rapor_tabani import StokRaporTabani


class StokHareketRaporuView(StokRaporTabani):
    """Dönem içindeki fiş satırı (hareket) sayısına göre sıralı ürün listesi."""

    RAPOR_ADI = "En Çok Hareket Gören Ürünler"

    KOLONLAR = (
        ("sira", "Sıra", 55, "center"),
        ("stok_kodu", "Stok Kodu", 110, "w"),
        ("stok_adi", "Stok Adı", 240, "w"),
        ("kategori", "Kategori", 110, "w"),
        ("hareket_sayisi", "Hareket Sayısı", 100, "e"),
        ("alis_miktar", "Alış Miktarı", 100, "e"),
        ("satis_miktar", "Satış Miktarı", 100, "e"),
        ("iade_miktar", "İade Miktarı", 100, "e"),
        ("diger_cikis", "Fire/Diğer Çıkış", 110, "e"),
        ("islem_tutar", "İşlem Hacmi", 130, "e"),
        ("son_hareket", "Son Hareket", 95, "center"),
    )

    def listele(self):
        self.temizle()
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            fid = self.main_app.aktif_firma_id
            bas, bit = self.tarih_araligi()

            kartlar = self.stok_kartlari(cursor)
            ozet = stok_donem_ozeti(cursor, fid, bas, bit)

            satirlar = []
            for stok_id, stok_kodu, stok_adi, kategori, birim in kartlar:
                o = stok_ozet_getir(ozet, stok_id)
                if o["hareket_sayisi"] <= 0:
                    continue  # dönemde hareketi olmayan ürün listeye girmez
                satirlar.append({
                    "kod": stok_kodu, "ad": stok_adi, "kategori": kategori or "",
                    "hareket": o["hareket_sayisi"],
                    "alis": o["alis_miktar"],
                    "satis": o["satis_miktar"],
                    "iade": o["satis_iade_miktar"] + o["alis_iade_miktar"],
                    "diger": o["fire_miktar"] + o["diger_cikis_miktar"],
                    "tutar": o["islem_tutar"],
                    "son": o["son_hareket_tarihi"],
                })

            satirlar.sort(key=lambda r: (-r["hareket"], -r["tutar"], r["ad"]))
            adet = self.limit()
            if adet:
                satirlar = satirlar[:adet]

            for i, r in enumerate(satirlar, start=1):
                self.tree.insert("", "end", values=(
                    i, r["kod"], r["ad"], r["kategori"],
                    r["hareket"],
                    format_miktar(r["alis"]),
                    format_miktar(r["satis"]),
                    format_miktar(r["iade"]),
                    format_miktar(r["diger"]),
                    format_currency(r["tutar"]),
                    format_date(r["son"]),
                ))

            self.donem_bilgisi(len(satirlar),
                               "Hareket sayısı = dönemdeki stok fiş satırı adedi.")
        except Exception as e:
            self.hata_goster(e)
        finally:
            if conn:
                conn.close()
