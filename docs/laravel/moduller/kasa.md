# Kasa Modülü

## Fiş Türleri
- Kasa Gider Fişi
- Kasa Gelir Fişi
- Kasalar Arası Virman
- Kasa Açılış Fişi

## Listeleme
- Filtreler: Kasa, Tarih Aralığı, Fiş Türü, Arama
- Liste: ID, Tarih, Fiş No, Kaynak, Fiş Türü, Açıklama, Toplam Tutar

## Form Alanları
- Tarih, Fiş No, Açıklama, Ana Kasa
- Gider/Gelir: Hizmet kartı, satır açıklaması, miktar, birim fiyat, KDV %
- Virman: Hedef Kasa, Tutar
- Açılış: Kasa, Yön, Tutar

## Import
- Kasa import şablonu `Kasa İşlemleri` sayfasını kullanır.
- Detay: `docs/laravel/05_excel_import.md`

## Controller / Service
- KasaController
- KasaFisService (veya FisService kullanılır)


## Referans
- View: `reference/v2/modules/kasa/kasa_view.py`
- Form: `reference/v2/modules/kasa/kasa_form.py`
- Import: `reference/v2/modules/kasa/kasa_import.py`