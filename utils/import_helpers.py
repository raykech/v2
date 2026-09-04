# -*- coding: utf-8 -*-
"""
Q2 — Excel/CSV içe aktarma yardımcılarının ORTAK hali.

Modüllerin her birinde kopyalanmış olan hücre dönüştürücüleri
(metin/sayı/tarih) ve "ada göre tek kayıt ID bulma" fonksiyonları burada
toplandı. Davranış sözleşmesi birebir korunur:
  - id_bul fonksiyonları: bulunamazsa None, birden çok eşleşirse "ambiguous",
    hizmet kartında tür uymazsa "wrong_type" döndürür.
"""
from datetime import date, datetime

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None


# ---------------------------------------------------------------- Hücre dönüştürücüleri
def metin(deger):
    """Excel hücresini temiz metne çevirir. NaN/None ise boş string döner."""
    if deger is None:
        return ""
    if isinstance(deger, float) and pd is not None and pd.isna(deger):
        return ""
    if isinstance(deger, str):
        return deger.strip()
    if isinstance(deger, (datetime, date)):
        return deger.strftime("%d.%m.%Y")
    return str(deger).strip()


def sayi(deger):
    """Excel hücresini float'a çevirmeyi dener. Geçersizse None döner."""
    if deger is None:
        return None
    if isinstance(deger, bool):
        return None
    if isinstance(deger, (int, float)):
        if pd is not None and isinstance(deger, float) and pd.isna(deger):
            return None
        return float(deger)

    s = str(deger).strip().replace(" ", "").replace("TL", "").replace("₺", "").replace("%", "")
    if not s:
        return None

    # "1.234,56" -> "1234.56"
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    # "1234,56" -> "1234.56"
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    # Nokta kullanımı: "1.234" binlik ayracı mı, "1234.56" ondalık mı?
    if s.count(".") > 1:
        s = s.replace(".", "")
    elif s.count(".") == 1 and len(s.split(".")[1]) == 3:
        # Türkçe binlik ayracı varsayımı: "1.000" -> 1000, "1.234" -> 1234
        s = s.replace(".", "")

    try:
        return float(s)
    except ValueError:
        return None


def tarih(deger):
    """Tarihi YYYY-MM-DD string'ine çevirir. Geçersizse None döner."""
    if deger is None:
        return None
    if isinstance(deger, datetime):
        return deger.strftime("%Y-%m-%d")
    if isinstance(deger, date):
        return deger.strftime("%Y-%m-%d")

    s = str(deger).strip()
    if not s:
        return None

    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def durum_to_int(durum_degeri):
    """'Pasif'/'0'/False gibi değerleri 0, diğerlerini 1 yapar (kart durum alanı)."""
    durum_str = metin(durum_degeri)
    if durum_str in ("Pasif", "0", "False"):
        return 0
    return 1


# ---------------------------------------------------------------- ID bulucular
def _tek_kayit_don(kayitlar):
    """Ortak sözleşme: yoksa None, çoksa 'ambiguous', tekse ilk satır (tuple)."""
    if not kayitlar:
        return None
    if len(kayitlar) > 1:
        return "ambiguous"
    return kayitlar[0]


def _id_don(kayitlar):
    """_tek_kayit_don'un tek satırından ID kolonunu alır."""
    kayit = _tek_kayit_don(kayitlar)
    return kayit if isinstance(kayit, str) or kayit is None else kayit[0]


def cari_id_bul(cursor, unvan, firma_id):
    """Cari unvanına göre ID döndürür. Yoksa None, çoklu kayıtta 'ambiguous'."""
    if not unvan:
        return None
    cursor.execute(
        "SELECT id FROM cariler WHERE durum=1 AND firma_id=? AND unvan=?", (firma_id, unvan)
    )
    return _id_don(cursor.fetchall())


def kasa_id_bul(cursor, kasa_adi, firma_id):
    """Kasa adına göre ID döndürür. Yoksa None, çoklu kayıtta 'ambiguous'."""
    if not kasa_adi:
        return None
    cursor.execute(
        "SELECT id FROM kasalar WHERE durum=1 AND firma_id=? AND kasa_adi=?", (firma_id, kasa_adi)
    )
    return _id_don(cursor.fetchall())


def banka_id_bul(cursor, hesap_adi, firma_id, hesap_turu=None):
    """Banka hesabı adına göre ID döndürür. hesap_turu verilirse onunla da süzer."""
    if not hesap_adi:
        return None
    if hesap_turu:
        cursor.execute(
            "SELECT id FROM banka_hesaplari WHERE durum=1 AND firma_id=? AND hesap_adi=? AND hesap_turu=?",
            (firma_id, hesap_adi, hesap_turu),
        )
    else:
        cursor.execute(
            "SELECT id FROM banka_hesaplari WHERE durum=1 AND firma_id=? AND hesap_adi=?",
            (firma_id, hesap_adi),
        )
    return _id_don(cursor.fetchall())


def banka_kurum_id_bul(cursor, kurum_adi, firma_id):
    """Banka kurumu adına göre ID döndürür."""
    if not kurum_adi:
        return None
    cursor.execute(
        "SELECT id FROM banka_kurumlari WHERE durum=1 AND firma_id=? AND kurum_adi=?",
        (firma_id, kurum_adi),
    )
    return _id_don(cursor.fetchall())


def stok_id_bul(cursor, stok_adi, firma_id):
    """Stok adına göre ID döndürür."""
    if not stok_adi:
        return None
    cursor.execute(
        "SELECT id FROM stoklar WHERE durum=1 AND firma_id=? AND stok_adi=?", (firma_id, stok_adi)
    )
    return _id_don(cursor.fetchall())


def hizmet_id_bul(cursor, kart_adi, tur, firma_id):
    """Hizmet kartı adına göre ID döndürür; tür uymazsa 'wrong_type'."""
    if not kart_adi:
        return None
    cursor.execute(
        "SELECT id, tur FROM hizmet_kartlari WHERE durum=1 AND firma_id=? AND kart_adi=?",
        (firma_id, kart_adi),
    )
    kayit = _tek_kayit_don(cursor.fetchall())
    if kayit is None or kayit == "ambiguous":
        return kayit
    if kayit[1] != tur:
        return "wrong_type"
    return kayit[0]
