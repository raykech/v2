# Ön Muhasebe v2 - Proje Mimarisi ve Teknik Dokümantasyon

> Bu doküman, projenin **güncel** durumunu anlatır.
> Uygulama `python __main__.py` ile çalıştırılır.
> Veritabanı dosyası: `on_muhasebe.db`

---

## 1. Proje Hakkında

Python + Tkinter + SQLite ile geliştirilmiş yerel bir ön muhasebe uygulamasıdır.
v2 mimarisinde tüm işlemler **çok satırlı fiş** modeli üzerine kurulmuştur.

**Temel amaçlar:**

- Fiş/Satır modeli: Her işlem bir başlık (`fisler`) ve ona bağlı detay satırlarından (`fis_satirlari`) oluşur.
- Modüler yapı: Her modül `view` (liste) ve `form` (giriş/düzenleme) olarak ayrılır.
- Katman ayrımı: Veritabanı (`core/db.py`), iş mantığı (`core/services.py`), arayüz (`ui/`, `modules/`).
- Kaynak takibi: Bir modülde oluşturulan fiş, başka modülde oluşturulmuş bir fişe bağlanabilir.
- Kullanıcı deneyimi: Excel benzeri satır girişi, dinamik formlar, LookupWidget ile hızlı seçim.

---

## 2. Dizin Yapısı

```
__main__.py                 Uygulama giriş noktası (firma/yıl seçimi + ana pencere)
core/
  db.py                     SQLite bağlantısı ve şema kurulumu
  services.py               Ortak fiş/kart servisleri + çek/senet yardımcıları
modules/
  kasa/                     Kasa modülü (view + form)
  cari/                     Cari modülü
  banka/                    Banka modülü
  fatura/                   Fatura modülü
  cek_senet/                Çek/Senet modülü
  tanimlar/                 Tanımlar (Stok, Cari, Kasa, Hizmet, Banka)
  raporlar/                 Raporlar
ui/
  main_window.py            Ana pencere, sekmeler, F5 ile yeniden yükleme
  dialogs.py                Yeni kart ekleme/düzenleme diyalogları
  widgets/
    lookup_widget.py        Arama ve seçim bileşeni
    advanced_treeview.py    Gelişmiş filtreli/sıralamalı Treeview bileşeni
    tooltip.py              Tooltip bileşeni
utils/
  formatters.py             Para/tarih formatlama
  export.py                 Excel / PDF dışa aktarma
```

---

## 3. Veritabanı Modeli

### 3.1. Tanımlama Tabloları

- **stoklar**: `id`, `stok_kodu`, `stok_adi`, `kategori`, `birim`, `alis_fiyati`, `kritik_miktar`, `satis_fiyati`, `kdv_oran`, `firma_id`, `durum`
- **cariler**: `id`, `unvan`, `tur` (Müşteri/Tedarikçi/Diğer), `telefon`, `firma_id`, `durum`
- **banka_kurumlari**: `id`, `kurum_adi`, `firma_id`, `durum`
- **banka_hesaplari**: `id`, `hesap_adi`, `kurum_id`, `hesap_turu` (Vadesiz/POS/Kredi Kartı), `iban`, `komisyon_orani`, `firma_id`, `durum`
- **kasalar**: `id`, `kasa_adi`, `firma_id`, `durum`
- **hizmet_kartlari**: `id`, `kart_adi`, `tur` (Gider/Gelir), `kdv_oran`, `grup_id`, `firma_id`, `durum`
- **hizmet_kartlari_gruplari**: `id`, `grup_adi`, `tur`, `firma_id`, `durum`
- **genel_tanimlar**: `id`, `grup`, `deger`, `firma_id` (stok kategorisi, stok birimi gibi değerler için)

### 3.2. Fiş Modeli

**fisler**

| Kolon | Açıklama |
|---|---|
| `id` | Birincil anahtar |
| `tarih` | İşlem tarihi |
| `fis_turu` | Fiş türü |
| `fis_no` | Evrak/fiş numarası |
| `aciklama` | Genel açıklama |
| `cari_id` | Faturanın ana carisi gibi opsiyonel başlık carisi |
| `kaynak_modul` | Fişin hangi modülde oluşturulduğu |
| `kaynak_fis_id` | Bağlı olduğu kaynak fişin ID'si |
| `toplam_tutar` | Fiş toplamı |
| `durum` | 1 aktif, 0 pasif/silindi |
| `firma_id` | Firma |
| `yil` | Çalışma yılı |

**fis_satirlari**

| Kolon | Açıklama |
|---|---|
| `id` | Birincil anahtar |
| `fis_id` | `fisler.id` referansı |
| `hesap_turu` | `Stok`, `Hizmet`, `Cari`, `Kasa`, `Banka`, `CekSenet` |
| `hesap_id` | İlgili tanım kartının ID'si |
| `aciklama` | Satır açıklaması |
| `miktar` | Miktar |
| `birim_fiyat` | Birim fiyat |
| `borc` / `alacak` | Borç ve alacak tutarları |
| `kdv_oran` / `kdv_tutar` | KDV bilgileri |
| `firma_id` | Firma |

### 3.3. Çek/Senet Modeli

**cekler_senetler**

- `id`, `seri_no`, `turu` (`Çek`/`Senet`), `banka`, `banka_id`, `vade_tarihi`, `tutar`
- `firma_id`, `created_at`, `updated_at`
- `kesideci`, `ciranta`, `aciklama`

**cek_senet_hareketleri**

- `id`, `cek_senet_id`, `fis_id`, `islem_tarihi`, `durum`
- `karsi_hesap_tipi`, `karsi_hesap_id`, `karsi_hesap_ismi`
- `ilgili_hareket_id`, `aciklama`, `firma_id`, `created_at`

### 3.4. Firma

- **firmalar**: `id`, `firma_adi`, `durum`

---

## 4. Ortak İş Mantığı (`core/services.py`)

- `fis_kaydet(...)` – Yeni fiş + satırlar + opsiyonel peşin ödeme fişi kaydeder.
- `fis_guncelle(...)` – Fişi ve satırlarını günceller, eski peşin ödeme fişini siler.
- `fis_sil(...)` – Fişi ve bağlı satırları siler.
- `kaydet_kart(...)` / `kart_sil(...)` – Tanım kartlarını ekler/günceller/siler.
- `is_kart_kullanilmis_mi(...)` – Kartın fişlerde kullanılıp kullanılmadığını kontrol eder.
- Çek/Senet yardımcıları:
  - `cek_senet_guncel_durum`
  - `cek_senet_son_banka_takas`
  - `cek_senet_fis_son_hareket_mi`
  - `cek_senet_hareket_ekle`
  - `cek_senet_fis_sil`

---

## 5. Modüller ve Özellikler

### 5.1. Kasa

Fiş türleri:
- Kasa Gider Fişi
- Kasa Gelir Fişi
- Kasalar Arası Virman

Özellikler:
- Gider/Gelir fişlerinde Hizmet kartı satırları + Kasa karşı satırı
- Virman fişinde satır listesi gizlenir; kaynak kasa, hedef kasa ve tutar alanları kullanılır
- KDV otomatik dolum ve anında satır toplamı hesabı

### 5.2. Banka

Fiş türleri:
- Banka Gider Fişi
- Banka Gelir Fişi
- Bankalar Arası Virman
- Blokeyi Bankaya Aktar
- Bankaya Yatan
- Bankadan Çekilen
- Gelen Banka Transferi
- Giden Banka Transferi

Özellikler:
- Gider/Gelir fişlerinde Hizmet kartı satırları + Banka karşı satırı
- Virman ve transfer türlerinde tek tutarlı özel form
- POS hesapları ile normal banka hesapları ayrıştırılır
- Bankaya Yatan / Bankadan Çekilen işlemlerinde karşı hesap Kasa'dır
- Gelen/Giden Transfer işlemlerinde karşı hesap Cari'dir

### 5.3. Cari

Fiş türleri:
- Alacak Dekontu
- Borç Dekontu
- Cari Ödeme
- Cari Tahsilat
- Cari Virman

Özellikler:
- Alacak/Borç Dekontu: üstte tek Gider/Gelir kartı, satırlarda Cariler
- Cari Ödeme/Tahsilat: ödeme türü Kasa veya Banka
- Cari Virman: satır bazlı borç/alacak, toplam borç = toplam alacak zorunluluğu

### 5.4. Fatura

Fiş türleri:
- Satış Faturası
- Alış Faturası
- Satış İade Faturası
- Alış İade Faturası
- Hizmet Satış Faturası
- Hizmet Alış Faturası

Ödeme tipleri:
- Vadeli
- Nakit (Kasa)
- Banka
- POS

Özellikler:
- Stoklu ve hizmetli fatura desteği
- İade faturalarında borç/alacak yönü otomatik ters çevrilir
- Peşin ödemelerde `kaynak_modul='Fatura'` ve `kaynak_fis_id=<fatura_id>` ile bağlı Kasa/Banka fişi oluşturulur
- KDV otomatik dolum ve satır toplamı hesabı

### 5.5. Çek/Senet

Fiş türleri:
- Çek/Senet Giriş Fişi
- Çek/Senet Bankaya Tahsile Verme
- Çek/Senet Ciro Etme
- Çek/Senet Tahsil Fişi
- Çek/Senet İade Fişi

Durumlar:
- Portföyde
- Bankada Tahsilde
- Cirolu
- Tahsil Edildi
- İade Edildi

Durum akışı:

```
Giriş Fişi
   ↓
Portföyde ──→ Bankaya Tahsile Verme → Bankada Tahsilde → Tahsil Fişi → Tahsil Edildi
   │
   ├──→ Ciro Etme → Cirolu
   └──→ İade Fişi → İade Edildi
```

Kurallar:
- Giriş Fişi yeni çek/senet kartı oluşturur.
- Diğer fişler yalnızca uygun durumdaki çek/senetleri seçebilir.
- Tahsil fişinde tüm satırlar aynı durumda olmalıdır.
- Bir fiş, ilgili çek/senedin son hareketi değilse düzenlenemez/silinemez.

### 5.6. Tanımlar

- Stok Kartları
- Cari Kartları
- Kasa Kartları
- Hizmet Kartları (Gider/Gelir + Grup)
- Banka Hesapları
- Banka Kurumları

Tanımlar sekmeler arası geçişte otomatik yenilenir.

### 5.7. Raporlar

Rapor sekmeleri:
- Stok Durum Raporu
- Stok Ekstresi
- Cari Ekstre
- Kasa Ekstre
- Banka Ekstre
- Hizmet Kartları Raporu
- Hizmet Kartları Detay

Raporlar **Excel (.xlsx)** ve **PDF** olarak dışa aktarılabilir.

---

## 6. Kullanıcı Arayüzü ve Deneyim

### 6.1. Ana Pencere

- Firma ve yıl seçimi ile giriş yapılır.
- Modüller sekmeler hâlinde açılır.
- Sekmeler arası geçişte aktif modül otomatik yenilenir.
- Geliştirme sırasında **F5** ile aktif modül ve bağımlılıkları yeniden yüklenir.

### 6.2. LookupWidget

- `...` butonu ile arama diyaloğu açılır.
- Yeni kart ekleme, düzenleme ve silme işlemleri diyalog içinden yapılabilir.
- Seçim sonrası otomatik KDV dolumu ve odaklanma davranışları tetiklenebilir.

### 6.3. Dinamik Formlar

- Fiş türüne göre form yapısı değişir.
- Virman/transfer türlerinde satır listesi gizlenir, yerine kaynak-hedef-tutar alanları gelir.
- Excel benzeri giriş satırı, çift tıklama ile düzenleme, `X` ile satır silme.
- CurrencyFormatter ile para girişleri otomatik formatlanır.

### 6.4. Kaynak Takibi ve "Kaynağa Git"

- Bir fiş başka modülden oluşturulduysa:
  - Düzenle ve Sil butonları pasif olur.
  - Kaynağa Git butonu aktifleşir.
- Örnek: Fatura peşin tahsilatı, `kaynak_modul='Fatura'` olan bir Kasa/Banka fişi oluşturur. Kasa listesinde bu fiş seçildiğinde kullanıcı "Kaynağa Git" ile faturaya dönebilir.

---

## 7. Kurulum ve Çalıştırma

```bash
pip install tkcalendar pandas openpyxl reportlab
python __main__.py
```

- `tkcalendar`: tarih seçici
- `pandas` + `openpyxl`: Excel dışa aktarma
- `reportlab`: PDF dışa aktarma

Veritabanı `core/db.py` çalıştırıldığında `on_muhasebe.db` olarak otomatik oluşturulur.

---

## 8. Geliştirme Notları / Kurallar

1. `iptal()` metodunda `self.destroy()` kullanılmaz; `pack_forget()` + `on_close()` + `view_container.pack()` kullanılır.
2. `main_window.py` içinde `_yeniden_yukle_aktif_modul` metodu ve `module_map` iki yerde bulunur; yeni modül eklerken ikisine de ekleme yapılmalıdır.
3. Lookup widget'ları `verileri_yukle()` ve `ayarla_form_yapisi()` çağrılarından sonra yapılandırılmalıdır.
4. Yeni kart ekleme işlemlerinde `ui/dialogs.py` içindeki `ac_kart_dialog` kullanılır.
5. Tüm kayıtlarda `firma_id` ve `yil` bilgisi korunmalıdır.
6. Çek/Senet seçimlerinde LookupWidget'tan dönen ID string olabilir; veri sözlüğü anahtarları integer olduğundan `int()` çevrimi yapılmalıdır.

---

## 9. Güncel Durum

Tamamlanan modüller:
- Kasa
- Banka
- Cari
- Fatura
- Çek/Senet
- Tanımlar
- Raporlar

Uygulama, tek kullanıcılı yerel ön muhasebe işlemlerini fiş bazlı olarak yönetebilecek durumdadır.
