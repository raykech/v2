# Laravel Geçiş Planı

> Bu doküman, mevcut Python/Tkinter ön muhasebe uygulamasının Laravel + Vue + Inertia tabanlı web uygulamasına geçiş planıdır.

## Amaç
- Mevcut masaüstü uygulamasının **birebir aynı iş mantığını** web ortamına taşımak.
- Modüler, kod tekrarı az, performanslı ve kullanıcı deneyimi yüksek bir uygulama kurmak.

## Teknoloji Kararları
| Katman | Teknoloji |
|---|---|
| Backend | Laravel 13 |
| Frontend | Vue 3 + Inertia |
| Veritabanı | MySQL (veya PostgreSQL) |
| Auth | Sanctum + Laravel Starter Kit |
| Yetki | Spatie Laravel Permission |
| Yedekleme | Spatie Laravel Backup |
| Excel | Laravel Excel (maatwebsite/excel) |
| PDF | Laravel DomPDF veya benzeri |

## Öncelik Sırası
1. Veritabanı migrationları ve modeller
2. Auth + rol/yetki + firma/yıl seçimi
3. Tanımlar (Cari, Stok, Hizmet, Kasa, Banka)
4. Fiş çekirdeği (fisler + fis_satirlari)
5. Kasa, Banka, Cari, Fatura modülleri
6. Çek/Senet state machine
7. Raporlar
8. Excel import/export
9. API planı (opsiyonel)
10. Deployment

## Kapsam Dışı (İlk Etap)
- Mevcut SQLite verisini taşıma (veri yok)
- Otomatik test yazımı (ilk aşamada zaman kaybetmemek için)
- Çok dilli destek (sonra eklenebilir)

## Fazlar
- **Faz 1**: Migration + Model + Auth + Firma/Yıl altyapısı
- **Faz 2**: Tanımlar CRUD + Excel import
- **Faz 3**: Fiş çekirdeği + Kasa/Banka/Cari/Fatura
- **Faz 4**: Çek/Senet durum makinesi
- **Faz 5**: Raporlar + Excel/PDF
- **Faz 6**: API + canlıya alma
