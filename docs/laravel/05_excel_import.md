# Excel İçe Aktarma

## Genel Akış
1. Kullanıcı "Örnek İndir" ile şablonu indirir.
2. Excel doldurulur.
3. "Veri Yükle" ile dosya seçilir.
4. Sistem dosyayı okur, doğrular, önizleme listesi hazırlar.
5. Kullanıcı onaylarsa toplu kayıt yapılır.
6. Hata varsa satır bazlı rapor gösterilir.

## Tanımlar Import (Excel Yükle sekmesi)
- 6 sayfa: Cari Kartlar, Stok Kartları, Hizmet Kartları, Kasa Kartları, Banka Kurumları, Banka Hesapları
- Aynı isimde kart varsa hata verir.
- Stok Kategori/Birim otomatik oluşturulur.
- Hizmet Grubu ve Banka Kurumu otomatik oluşturulur.

### Cari Kartlar
Kolonlar: Unvan, Tür, Telefon, Durum

### Stok Kartları
Kolonlar: Stok Adı, Stok Kodu, Kategori, Birim, Alış Fiyatı, Satış Fiyatı, KDV %, Kritik Miktar, Durum

### Hizmet Kartları
Kolonlar: Kart Adı, Tür, Grup, KDV %, Durum

### Kasa Kartları
Kolonlar: Kasa Adı, Durum

### Banka Kurumları
Kolonlar: Kurum Adı, Durum

### Banka Hesapları
Kolonlar: Hesap Adı, Banka Kurumu, Hesap Türü, IBAN, Komisyon %, Durum

## Kasa Import
Kolonlar: Fiş Türü, Tarih, Fiş No, Genel Açıklama, Kasa / Ana Kasa, Hedef Kasa, Gider/Gelir Kartı, Yön, Satır Açıklaması, Miktar, Birim Fiyat, KDV %, Tutar

- Fiş Türleri: Kasa Gider Fişi, Kasa Gelir Fişi, Kasalar Arası Virman, Kasa Açılış Fişi
- KDV % boşsa 0 kabul edilir.

## Banka Import
Kolonlar: Fiş Türü, Tarih, Fiş No, Açıklama, Ana Banka, Hedef / Karşı Hesap, Gider/Gelir Kartı, Yön, Satır Açıklaması, Miktar, Birim Fiyat, KDV %, Tutar

- Fiş Türleri: Banka Gider/Gelir, Virman, Blokeyi Bankaya Aktar, Bankaya Yatan, Bankadan Çekilen, Gelen/Giden Transfer, Banka Açılış

## Cari Import
Kolonlar: Fiş Türü, Tarih, Fiş No, Açıklama, Ana Kart / Ödeme Hesabı, Ödeme Türü, Cari, Yön, Satır Açıklaması, Tutar

- Fiş Türleri: Alacak Dekontu, Borç Dekontu, Cari Ödeme, Cari Tahsilat, Cari Virman
- Cari Virman'da borç = alacak olmalıdır.

## Fatura Import
Kolonlar: Fiş Türü, Tarih, Fatura No, Açıklama, Cari, Ödeme Tipi, Ödeme Hesabı, Stok/Hizmet Adı, Satır Açıklaması, Miktar, Birim Fiyat, KDV %, Tutar

- Fiş Türleri: Satış, Alış, İade, Hizmet Satış, Hizmet Alış
- Ödeme Tipleri: Vadeli, Nakit, Banka, POS

## Çek/Senet Import
Kolonlar: Fiş Türü, Tarih, Fiş No, Açıklama, Seri No, Tür, Banka Kurumu, Vade, Tutar, Keşideci, Ciranta, Cari / Karşı Hesap, Satır Açıklaması, Kasa / Banka Hesabı, Tahsil Türü, Durum

- Şu an yalnızca Giriş Fişi ve Açılış Fişi desteklenir.
- Seri No benzersiz olmalıdır.

## Doğrulama Kuralları
- Zorunlu alanlar boşsa satır hata olarak işaretlenir.
- Tanımlı olmayan kasa/banka/cari/stok/hizmet adı varsa hata verilir.
- Aynı Fiş No + Tarih + hesap grubu satırları tek fiş olarak gruplanır.
- Fiş No boşsa her satır ayrı fiş olur.


## Referans
- Kasa import: `reference/v2/modules/kasa/kasa_import.py`
- Banka import: `reference/v2/modules/banka/banka_import.py`
- Cari import: `reference/v2/modules/cari/cari_import.py`
- Fatura import: `reference/v2/modules/fatura/fatura_import.py`
- Çek/Senet import: `reference/v2/modules/cek_senet/cek_senet_import.py`
- Tanımlar import: `reference/v2/modules/tanimlar/tanim_import.py`
- Önizleme dialog: `reference/v2/ui/import_preview.py`