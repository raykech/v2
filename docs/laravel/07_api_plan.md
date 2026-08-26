# API Planı (Opsiyonel)

## Auth
- Sanctum ile token bazlı kimlik doğrulama
- Spatie ile rol/permission kontrolü

## Örnek Endpoint Listesi

### Auth
- POST /api/login
- POST /api/logout
- GET /api/user

### Tanımlar
- GET /api/tanimlar/cari
- POST /api/tanimlar/cari
- PUT /api/tanimlar/cari/{id}
- DELETE /api/tanimlar/cari/{id}
- Aynı yapı stok, kasa, banka, hizmet için de geçerli

### Firma / Yıl
- GET /api/firmalar
- POST /api/firma/sec
- GET /api/yillar

### Fişler
- GET /api/{modul}/fisler
- POST /api/{modul}/fisler
- GET /api/{modul}/fisler/{id}
- PUT /api/{modul}/fisler/{id}
- DELETE /api/{modul}/fisler/{id}

### Import
- POST /api/import/{modul}/onizle
- POST /api/import/{modul}/kaydet

### Raporlar
- GET /api/raporlar/{rapor_adi}
- GET /api/raporlar/{rapor_adi}/export

## Resource Katmanı
- `FisResource`
- `FisSatiriResource`
- `CariResource`
- `StokResource`
- `KasaResource`
- `BankaResource`
- `CekSenetResource`

## API Kuralları
- Tüm listelerde sayfalama + filtre parametreleri
- Tüm yazma işlemlerinde FormRequest doğrulaması
- Hatalarda standart JSON formatı
