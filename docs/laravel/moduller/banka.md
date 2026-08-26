# Banka Modülü

## Fiş Türleri
- Banka Gider Fişi
- Banka Gelir Fişi
- Bankalar Arası Virman
- Blokeyi Bankaya Aktar
- Bankaya Yatan
- Bankadan Çekilen
- Gelen Banka Transferi
- Giden Banka Transferi
- Banka Açılış Fişi

## Listeleme
- Filtreler: Banka, Tarih Aralığı, Fiş Türü, Arama

## Form Alanları
- Ana Banka, Tarih, Fiş No, Açıklama
- Gider/Gelir: Hizmet kartı + satırlar
- Virman/Transfer: Hedef / Karşı Hesap + Tutar

## Import
- Banka import şablonu `Banka İşlemleri` sayfasını kullanır.
- Detay: `docs/laravel/05_excel_import.md`


## Referans
- View: `reference/v2/modules/banka/banka_view.py`
- Form: `reference/v2/modules/banka/banka_form.py`
- Import: `reference/v2/modules/banka/banka_import.py`