# Raporlar

## Rapor Listesi
| Rapor | Açıklama |
|---|---|
| Stok Durum Raporu | Mevcut stok, kritik miktar, maliyet |
| Stok Ekstresi | Stok giriş/çıkış hareketleri |
| Cari Ekstre | Cari bazında borç/alacak hareketleri |
| Kasa Ekstre | Kasa hareketleri |
| Banka Ekstre | Banka hesap hareketleri |
| Hizmet Kartları Raporu | Hizmet kartları listesi |
| Hizmet Kartları Detay | Hizmet kartı bazında hareketler |
| Çek/Senet Portföy Raporu | Eldeki çek/senetler |
| Çek/Senet Vade Raporu | Vade bazlı çek/senetler |
| Çek/Senet Serüven Raporu | Çek/senet durum geçmişi |

## Ortak Filtreler
- Firma
- Yıl
- Tarih aralığı
- Cari / Kasa / Banka / Stok / Hizmet kartı
- Durum (Çek/Senet için)

## Çıktı Formatları
- Ekranda tablo
- Excel (.xlsx)
- PDF

## Rapor Sorgu Mantığı
- `fis_satirlari` üzerinden hesap türü ve hesap ID ile toplamlar alınır.
- Bakiyeler borç-alacak farkından hesaplanır.
- Stok maliyeti FIFO mantığıyla hesaplanır.
- Raporlar `RaporService` içinde toplanır.


## Referans
- Rapor view dosyaları: `reference/v2/modules/raporlar/`
- Rapor sorgu yapıları: ilgili view dosyasındaki listele() metodu
- Export: `reference/v2/utils/export.py`