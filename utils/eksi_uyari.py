from tkinter import messagebox

from core.services import (
    eksi_dusme_kontrol,
    ayar_oku,
    EKSI_POLITIKA_VARSAYILAN,
    AYAR_EKSI_KASA,
    AYAR_EKSI_BANKA,
    AYAR_EKSI_STOK,
)
from utils.formatters import format_currency, format_miktar


# "Bir kere uyar" politikası için oturum bazlı hatırlanan hesaplar:
# (firma_id, tur, hesap_id) kümesi. Uygulama kapanınca sıfırlanır.
_UYARILAN_BIR_KERE = set()


def _deger_metni(o):
    if o["birim"] == "₺":
        return format_currency(o["deger"])
    return f"{format_miktar(o['deger'])} {o['birim']}"


def _satirlar(offenders):
    return "\n".join(
        f"  • {o['tur']} «{o['hesap_adi']}» → {_deger_metni(o)}" for o in offenders
    )


def eksi_kontrol_ve_onayla(parent, cursor, firma_id, fis_satirlari, guncellenen_fis_id=None):
    """
    Fiş kaydedilmeden ÖNCE çağrılır. Fiş bu hâliyle yazılsa hangi hesapların
    eksiye düşeceğini bulur ve Ayarlar'daki politikaya göre davranır.

    Dönüş: True → kayda devam edil; False → 'izin verme' politikağı nedeniyle
    kayıt engellendi (fiş yazılmamalı).
    """
    offenders = eksi_dusme_kontrol(cursor, firma_id, fis_satirlari, guncellenen_fis_id)
    if not offenders:
        return True

    politikalar = {
        "Kasa": ayar_oku(cursor, firma_id, AYAR_EKSI_KASA, EKSI_POLITIKA_VARSAYILAN),
        "Banka": ayar_oku(cursor, firma_id, AYAR_EKSI_BANKA, EKSI_POLITIKA_VARSAYILAN),
        "Stok": ayar_oku(cursor, firma_id, AYAR_EKSI_STOK, EKSI_POLITIKA_VARSAYILAN),
    }

    engelleyenler = []
    uyarilacaklar = []
    for o in offenders:
        pol = politikalar.get(o["tur"], EKSI_POLITIKA_VARSAYILAN)
        if pol == "izin_verme":
            engelleyenler.append(o)
        elif pol == "her_seferinde_uyar":
            uyarilacaklar.append(o)
        elif pol == "bir_kere_uyar":
            key = (firma_id, o["tur"], o["hesap_id"])
            if key not in _UYARILAN_BIR_KERE:
                _UYARILAN_BIR_KERE.add(key)
                uyarilacaklar.append(o)
        # "hicbir_sey_yapma": sessiz

    # Önce (varsa) uyar; izin verilen kayda devam eder.
    if uyarilacaklar:
        messagebox.showwarning(
            "Eksi Bakiye Uyarısı",
            "Bu fiş şu hesapları eksiye düşürüyor (kaydedilecek):\n\n"
            + _satirlar(uyarilacaklar)
            + "\n\nNot: Eksiler, Raporlar › Düzeltilecekler sekmesinde kırmızı listelenir.",
            parent=parent,
        )

    # Engelleyen varsa kayıt yapılmaz.
    if engelleyenler:
        messagebox.showerror(
            "İzin Verilmedi",
            "Ayarlar › Eksi Çalışma politikası gereği eksiye düşen kayıt engellendi:\n\n"
            + _satirlar(engelleyenler)
            + "\n\nDevam etmek için ayarı gevşetin ya da fişi düzeltin.",
            parent=parent,
        )
        return False

    return True
