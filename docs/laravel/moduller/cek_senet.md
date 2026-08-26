# Çek/Senet Modülü

## Fiş Türleri
- Çek/Senet Giriş Fişi
- Çek/Senet Bankaya Tahsile Verme
- Çek/Senet Ciro Etme
- Çek/Senet Tahsil Fişi
- Çek/Senet İade Fişi
- Çek/Senet Açılış Fişi

## Durumlar
- Portföyde
- Bankada Tahsilde
- Cirolu
- Tahsil Edildi
- İade Edildi

## State Machine
```
Giriş Fişi -> Portföyde
Portföyde -> Bankaya Tahsile Verme -> Bankada Tahsilde
Bankada Tahsilde -> Tahsil Fişi -> Tahsil Edildi
Portföyde -> Ciro Etme -> Cirolu
Portföyde -> İade Fişi -> İade Edildi
```

## Import
- Şu an yalnızca Giriş ve Açılış fişleri desteklenir.
- Detay: `docs/laravel/05_excel_import.md`


## Referans
- View: `reference/v2/modules/cek_senet/cek_senet_view.py`
- Form: `reference/v2/modules/cek_senet/cek_senet_form.py`
- Import: `reference/v2/modules/cek_senet/cek_senet_import.py`