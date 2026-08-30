# -*- coding: utf-8 -*-
"""
Satış performansına göre stok raporları.

- StokSatisRaporuView : En Çok Satan / Az Satan ürünler (mod: "cok" | "az")
- StokHicSatisRaporuView : Dönemde hiç satış yapmayan ürünler
"""
from core.db import veritabani_baglan
from core.services import stok_bakiye_ve_maliyet, stok_donem_ozeti, stok_ozet_getir
from utils.formatters import format_currency, format_date, format_miktar

from .stok_rapor_tabani import StokRaporTabani


MOD_BILGILERI = {
    "cok": {"baslik": "En Çok Satan Ürünler", "ters": True},
    "az": {"baslik": "Az Satan Ürünler", "ters": False},
}


class StokSatisRaporuView(StokRaporTabani):
    """Satış miktarına göre sıralı ürün listesi (en çok / az)."""

    KOLONLAR = (
        ("sira", "Sıra", 55, "center"),
        ("stok_kodu", "Stok Kodu", 110, "w"),
        ("stok_adi", "Stok Adı", 240, "w"),
        ("kategori", "Kategori", 110, "w"),
        ("satis_miktar", "Satış Miktarı", 110, "e"),
        ("satis_tutar", "Satış Tutarı", 130, "e"),
        ("iade_miktar", "İade Miktarı", 100, "e"),
        ("fis_sayisi", "Hareket Sayısı", 100, "e"),
        ("mevcut", "Mevcut Miktar", 110, "e"),
    )

    def __init__(self, parent, main_app, mod="cok"):
        self.mod = mod if mod in MOD_BILGILERI else "cok"
        self.RAPOR_ADI = MOD_BILGILERI[self.mod]["baslik"]
        super().__init__(parent, main_app)
        self.durum_yaz("Filtreyi ayarlayıp Listele butonuna basın.")

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
            bakiyeler, _ = stok_bakiye_ve_maliyet(cursor, fid)

            satirlar = []
            for stok_id, stok_kodu, stok_adi, kategori, birim in kartlar:
                o = stok_ozet_getir(ozet, stok_id)
                # Net satış = satış faturası - satış iadesi
                net_miktar = o["satis_miktar"] - o["satis_iade_miktar"]
                net_tutar = o["satis_tutar"] - o["satis_iade_tutar"]
                if net_miktar <= 0:
                    continue  # bu listede yalnızca satışı olan ürünler var
                satirlar.append({
                    "id": stok_id, "kod": stok_kodu, "ad": stok_adi,
                    "kategori": kategori or "", "net_miktar": net_miktar,
                    "net_tutar": net_tutar,
                    "iade": o["satis_iade_miktar"],
                    "hareket": o["hareket_sayisi"],
                    "mevcut": bakiyeler.get(stok_id, 0.0),
                })

            ters = MOD_BILGILERI[self.mod]["ters"]
            satirlar.sort(key=lambda r: (-r["net_miktar"] if ters else r["net_miktar"],
                                         r["ad"]))
            adet = self.limit()
            if adet:
                satirlar = satirlar[:adet]

            for i, r in enumerate(satirlar, start=1):
                tags = ('uyari',) if r["mevcut"] <= 0 else ()
                self.tree.insert("", "end", values=(
                    i, r["kod"], r["ad"], r["kategori"],
                    format_miktar(r["net_miktar"]),
                    format_currency(r["net_tutar"]),
                    format_miktar(r["iade"]),
                    r["hareket"],
                    format_miktar(r["mevcut"]),
                ), tags=tags)

            self.donem_bilgisi(len(satirlar),
                               "Satış miktarına (net) göre sıralıdır.")
        except Exception as e:
            self.hata_goster(e)
        finally:
            if conn:
                conn.close()


class StokHicSatisRaporuView(StokRaporTabani):
    """Seçili dönemde hiç satış yapmayan (net satış = 0) ürünler."""

    RAPOR_ADI = "Hiç Satış Yapmayan Ürünler"

    KOLONLAR = (
        ("sira", "Sıra", 55, "center"),
        ("stok_kodu", "Stok Kodu", 110, "w"),
        ("stok_adi", "Stok Adı", 240, "w"),
        ("kategori", "Kategori", 110, "w"),
        ("birim", "Birim", 70, "center"),
        ("mevcut", "Mevcut Miktar", 110, "e"),
        ("maliyet", "Maliyet Değeri", 130, "e"),
        ("gecmis_satis", "Tüm Dönem Satış", 120, "e"),
        ("son_hareket", "Son Hareket", 100, "center"),
        ("hareket_sayisi", "Hareket Sayısı", 100, "e"),
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
            donem_ozet = stok_donem_ozeti(cursor, fid, bas, bit)
            gecmis_ozet = stok_donem_ozeti(cursor, fid)  # tüm dönem
            bakiyeler, maliyetler = stok_bakiye_ve_maliyet(cursor, fid)

            satirlar = []
            for stok_id, stok_kodu, stok_adi, kategori, birim in kartlar:
                o = stok_ozet_getir(donem_ozet, stok_id)
                g = stok_ozet_getir(gecmis_ozet, stok_id)
                net_miktar = o["satis_miktar"] - o["satis_iade_miktar"]
                if net_miktar > 0:
                    continue  # dönemde satışı olan ürün listeye girmez
                gecmis_net = g["satis_miktar"] - g["satis_iade_miktar"]
                satirlar.append({
                    "kod": stok_kodu, "ad": stok_adi, "kategori": kategori or "",
                    "birim": birim or "",
                    "mevcut": bakiyeler.get(stok_id, 0.0),
                    "maliyet": maliyetler.get(stok_id, 0.0),
                    "gecmis_satis": gecmis_net,
                    "son_hareket": o["son_hareket_tarihi"] or g["son_hareket_tarihi"],
                    "hareket": o["hareket_sayisi"],
                })

            # Bağlı sermayesi en yüksek (maliyet değeri büyük) olan üstte
            satirlar.sort(key=lambda r: (-r["maliyet"], r["ad"]))
            adet = self.limit()
            if adet:
                satirlar = satirlar[:adet]

            for i, r in enumerate(satirlar, start=1):
                tags = ('uyari',) if r["gecmis_satis"] <= 0 else ()
                self.tree.insert("", "end", values=(
                    i, r["kod"], r["ad"], r["kategori"], r["birim"],
                    format_miktar(r["mevcut"]),
                    format_currency(r["maliyet"]),
                    format_miktar(r["gecmis_satis"]),
                    format_date(r["son_hareket"]),
                    r["hareket"],
                ), tags=tags)

            self.donem_bilgisi(
                len(satirlar),
                "Turuncu satır: hiçbir dönemde satışı olmayan ürün (ölü stok).")
        except Exception as e:
            self.hata_goster(e)
        finally:
            if conn:
                conn.close()
