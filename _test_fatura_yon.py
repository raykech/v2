# -*- coding: utf-8 -*-
"""Fatura satır ve cari yönü mantığını doğrular."""
fis_turleri = [
    "Satış Faturası",
    "Alış Faturası",
    "Satış İade Faturası",
    "Alış İade Faturası",
    "Hizmet Satış Faturası",
    "Hizmet Alış Faturası",
]

beklenen = {
    "Satış Faturası": (False, True),        # satır alacak, cari borç
    "Alış Faturası": (True, False),         # satır borç, cari alacak
    "Satış İade Faturası": (True, False),   # satır borç, cari alacak
    "Alış İade Faturası": (False, True),    # satır alacak, cari borç
    "Hizmet Satış Faturası": (False, True), # satır alacak, cari borç
    "Hizmet Alış Faturası": (True, False),  # satır borç, cari alacak
}

print(f"{'Fiş Türü':<25} {'satir_borclu':<14} {'cari_borclu':<14} {'OK'}")
print("-" * 60)
ok = True
for ft in fis_turleri:
    is_satis = "Satış" in ft
    is_iade = "İade" in ft
    satir_borclu = (is_satis and is_iade) or (not is_satis and not is_iade)
    cari_borclu = (is_satis and not is_iade) or (not is_satis and is_iade)
    bek_satir, bek_cari = beklenen[ft]
    durum = "OK" if (satir_borclu == bek_satir and cari_borclu == bek_cari) else "HATA"
    if durum == "HATA":
        ok = False
    print(f"{ft:<25} {str(satir_borclu):<14} {str(cari_borclu):<14} {durum}")

print("-" * 60)
print("SONUÇ:", "BAŞARILI" if ok else "HATA VAR")
