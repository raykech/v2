# -*- coding: utf-8 -*-
"""
Kârlılık Raporu: ürün bazında alış / satış / kâr.

Satış tutarı KDV hariç (miktar × birim_fiyat) net değerdir.
Maliyet, fiş hareketlerinden FIFO yöntemiyle hesaplanan "satılan malın
maliyeti"dir (karttaki güncel alış fiyatı ile ilgisi yoktur).
"""
from core.db import veritabani_baglan
from core.services import (stok_donem_cogs, stok_donem_ozeti, stok_ozet_getir,
                           STOK_SATIS_TURU)
from utils.formatters import format_currency, format_miktar

from .stok_rapor_tabani import StokRaporTabani


class StokKarlikRaporuView(StokRaporTabani):
    """Ürün bazında kârlılık listesi (kâr tutarına göre sıralı)."""

    RAPOR_ADI = "Kârlılık Raporu"

    KOLONLAR = (
        ("stok_kodu", "Stok Kodu", 110, "w"),
        ("stok_adi", "Stok Adı", 240, "w"),
        ("kategori", "Kategori", 110, "w"),
        ("alis_miktar", "Alış Miktarı", 100, "e"),
        ("alis_tutar", "Alış Tutarı", 130, "e"),
        ("satis_miktar", "Satış Miktarı", 100, "e"),
        ("satis_tutar", "Satış Tutarı", 130, "e"),
        ("maliyet", "Maliyet (FIFO)", 130, "e"),
        ("kar", "Kâr", 130, "e"),
        ("marj", "Kâr Marjı %", 90, "e"),
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
            # Yalnızca satış faturası çıkışlarının maliyeti (fire/iade hariç)
            cogs = stok_donem_cogs(cursor, fid, bas, bit, fis_turleri=(STOK_SATIS_TURU,))

            satirlar = []
            for stok_id, stok_kodu, stok_adi, kategori, birim in kartlar:
                o = stok_ozet_getir(ozet, stok_id)
                satis_miktar = o["satis_miktar"] - o["satis_iade_miktar"]
                satis_tutar = o["satis_tutar"] - o["satis_iade_tutar"]
                if satis_miktar <= 0 or satis_tutar <= 0:
                    continue  # döneminde satışı olmayan ürün kâr analizi dışındadır
                maliyet = cogs.get(stok_id, 0.0)
                kar = satis_tutar - maliyet
                marj = (kar / satis_tutar * 100) if satis_tutar else 0.0
                satirlar.append({
                    "kod": stok_kodu, "ad": stok_adi, "kategori": kategori or "",
                    "alis_miktar": o["alis_miktar"], "alis_tutar": o["alis_tutar"],
                    "satis_miktar": satis_miktar, "satis_tutar": satis_tutar,
                    "maliyet": maliyet, "kar": kar, "marj": marj,
                })

            satirlar.sort(key=lambda r: (-r["kar"], r["ad"]))
            adet = self.limit()
            if adet:
                satirlar = satirlar[:adet]

            t = {"alis_tutar": 0.0, "satis_miktar": 0.0, "satis_tutar": 0.0,
                 "maliyet": 0.0, "kar": 0.0}
            for r in satirlar:
                self.tree.insert("", "end", values=(
                    r["kod"], r["ad"], r["kategori"],
                    format_miktar(r["alis_miktar"]),
                    format_currency(r["alis_tutar"]),
                    format_miktar(r["satis_miktar"]),
                    format_currency(r["satis_tutar"]),
                    format_currency(r["maliyet"]),
                    format_currency(r["kar"]),
                    f"{r['marj']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                ), tags=('pozitif',) if r["kar"] >= 0 else ('negatif',))

                t["alis_tutar"] += r["alis_tutar"]
                t["satis_miktar"] += r["satis_miktar"]
                t["satis_tutar"] += r["satis_tutar"]
                t["maliyet"] += r["maliyet"]
                t["kar"] += r["kar"]

            genel_marj = (t["kar"] / t["satis_tutar"] * 100) if t["satis_tutar"] else 0.0
            self.tree.insert("", "end", values=(
                "", "TOPLAM", "",
                "", format_currency(t["alis_tutar"]),
                format_miktar(t["satis_miktar"]),
                format_currency(t["satis_tutar"]),
                format_currency(t["maliyet"]),
                format_currency(t["kar"]),
                f"{genel_marj:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            ), tags=('toplam',))

            self.donem_bilgisi(len(satirlar),
                               "Kâr = net satış tutarı − FIFO maliyet.")
        except Exception as e:
            self.hata_goster(e)
        finally:
            if conn:
                conn.close()
