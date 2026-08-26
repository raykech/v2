# Mimari ve Katmanlar

## Genel Yaklaşım
- **Controller** ince olur; iş mantığı Service katmanındadır.
- **Model** ilişkileri ve scope'ları içerir.
- **FormRequest** doğrulamayı yönetir.
- **Resource** API/Inertia çıktılarını şekillendirir.
- **Service** transaction, iş kuralı ve tekrar kullanılabilir mantığı içerir.
- **Event/Listener** bağımlılıkları gevşetir (stok, cari, kasa/banka güncellemeleri).

## Örnek Dizin Yapısı
```
app/
  Enums/
    FisTuru.php
    HesapTuru.php
    OdemeTipi.php
    CekSenetDurum.php
  Models/
    Firma.php
    User.php
    Stok.php
    Cari.php
    Kasa.php
    BankaKurum.php
    BankaHesap.php
    HizmetKarti.php
    HizmetKartiGrubu.php
    GenelTanim.php
    Fis.php
    FisSatiri.php
    CekSenet.php
    CekSenetHareket.php
  Services/
    FisService.php
    KartService.php
    CekSenetService.php
    ExcelImportService.php
    RaporService.php
  Http/
    Controllers/
      KasaController.php
      BankaController.php
      CariController.php
      FaturaController.php
      CekSenetController.php
      TanimController.php
      RaporController.php
    Requests/
      KasaFisRequest.php
      BankaFisRequest.php
      ...
    Resources/
      FisResource.php
      CariResource.php
      ...
  Imports/
    KasaImport.php
    BankaImport.php
    CariImport.php
    FaturaImport.php
    CekSenetImport.php
    TanimImport.php
  Exports/
    ...
  Events/
    FisKaydedildi.php
  Listeners/
    StokHareketiGuncelle.php
    CariBakiyeGuncelle.php
    KasaBakiyeGuncelle.php
```

## Service Katmanı Sorumlulukları

### FisService
- `kaydet(FisData $data, array $satirlar, ?PesinOdemeData $pesin)`
- `guncelle(Fis $fis, ...)`
- `sil(Fis $fis)`
- İçeride `DB::transaction` kullanılır.
- Peşin ödeme fişi oluşturma/silme burada yapılır.

### CekSenetService
- `girisFisiKaydet`
- `bankayaTahsileVer`
- `ciroEt`
- `tahsilEt`
- `iadeEt`
- Durum geçişlerini kontrol eder.

### KartService
- Tanım kartı ekleme/güncelleme/silme
- Kullanımda olan kart silinmesin kontrolü

### ExcelImportService
- Şablon oluşturma
- Dosya okuma
- Doğrulama
- Önizleme verisi hazırlama
- Toplu kaydetme

## Transaction Kuralları
- Fiş + satırlar + peşin ödeme + çek/senet hareketleri **tek transaction** içinde.
- Hata olursa tamamı geri alınır.
- Import işlemleri de tek transaction ile toplu kaydedilir.

## Event / Listener Örnekleri
- `FisKaydedildi` eventi tetiklenince:
  - Stok satırları varsa stok hareketi düşülür/eklenir.
  - Cari satırları varsa cari bakiye etkilenir.
  - Kasa/Banka satırları varsa kasa/banka bakiyesi etkilenir.

## Enum'lar
- `FisTuru`: Kasa, Banka, Cari, Fatura, CekSenet türleri
- `HesapTuru`: Stok, Hizmet, Cari, Kasa, Banka, CekSenet
- `OdemeTipi`: Vadeli, Nakit, Banka, POS
- `CekSenetDurum`: Portföyde, Bankada Tahsilde, Cirolu, Tahsil Edildi, İade Edildi

## Helper'lar
- `TarihHelper`: tarih formatlama, yıl kontrolü
- `ParaHelper`: para formatlama, parse
- `FiltreHelper`: ortak filtre parametreleri
- `ImportHelper`: excel satırlarını normalize etme


## Referans
- Service katmanı: `reference/v2/core/services.py`
- Fiş kaydetme: `reference/v2/core/services.py` → fis_kaydet()
- Kart kaydetme: `reference/v2/core/services.py` → kaydet_kart()
- Çek/Senet yardımcıları: `reference/v2/core/services.py` başlığı altındaki metodlar
- FormRequest kuralları: ilgili form dosyasındaki `fis_kaydet()` validasyonları