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
  kasa/
    kasa_view.py            Kasa modülü liste görünümü
    kasa_form.py            Kasa fiş formu (Gider/Gelir/Virman)
    kasa_import.py          Kasa Excel import yardımcıları
  banka/
    banka_view.py           Banka modülü liste görünümü
    banka_form.py           Banka fiş formu
    banka_import.py         Banka Excel import yardımcıları
  cari/
    cari_view.py            Cari modülü liste görünümü
    cari_form.py            Cari fiş formu
    cari_import.py          Cari Excel import yardımcıları
  fatura/
    fatura_view.py          Fatura modülü liste görünümü
    fatura_form.py          Fatura fiş formu
    fatura_import.py        Fatura Excel import yardımcıları
  cek_senet/
    cek_senet_view.py       Çek/Senet modülü liste görünümü
    cek_senet_form.py       Çek/Senet fiş formu
    cek_senet_import.py     Çek/Senet Excel import yardımcıları
  acilis/
    acilis_form.py          Açılış fişi formu (Kasa/Banka/Cari)
  tanimlar/
    tanimlar_view.py        Tanımlar ana görünümü (Notebook sekmeleri)
    cari_view.py            Cari kart tanımı
    stok_view.py            Stok kart tanımı
    kasa_view.py            Kasa kart tanımı
    hizmet_view.py          Hizmet/Masraf kart tanımı
    banka_kurum_view.py     Banka kurum tanımı
    banka_hesap_view.py     Banka hesap tanımı
    tanim_import.py         Tanım kartları (Cari, Stok, Hizmet, Kasa, Banka) Excel import
  raporlar/                 Raporlar
  ayarlar/                  Ayarlar (firma, yıl)
ui/
  main_window.py            Ana pencere, sekmeler, F5 ile yeniden yükleme
  dialogs.py                Yeni kart ekleme/düzenleme diyalogları
  import_preview.py         Import önizleme dialog sınıfları (Kasa, Fatura, Banka, Cari, Çek/Senet, Tanım)
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
- **hizmet_kartlari**: `id`, `kart_adi`, `tur` (Gider/Gelir/**KDV**), `kdv_oran`, `grup_id`, `firma_id`, `durum`
  - `tur='KDV'` olan kartlar KDV hesaplarıdır: **191 İndirilecek KDV**, **391 Hesaplanan KDV**
  - Bu kartlar "KDV" grubu altında (`hizmet_kartlari_gruplari.grup_adi='KDV'`) otomatik oluşturulur
  - KDV kartları fiş satırlarında kullanılır ancak normal hizmet kartı lookuplarında gösterilmez (tür filtresi nedeniyle)
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
- Kasa Açılış Fişi (Açılış formu ile)

Özellikler:
- Gider/Gelir fişlerinde Hizmet kartı satırları + Kasa karşı satırı
- Virman fişinde satır listesi gizlenir; kaynak kasa, hedef kasa ve tutar alanları kullanılır
- KDV otomatik dolum ve anında satır toplamı hesabı

**Excel İçe Aktarma (`kasa_import.py`)**
- Template sayfası: "Kasa İşlemleri" + "Açıklama"
- Sütunlar: Fiş Türü, Tarih, Fiş No, Genel Açıklama, Kasa / Ana Kasa, Hedef Kasa, Gider/Gelir Kartı, Yön, Satır Açıklaması, Miktar, Birim Fiyat, KDV %, Tutar
- Gruplama: Aynı Fiş No + Tarih + Kasa satırları tek fişte toplanır. Fiş No boşsa her satır ayrı fiş.
- KDV % boş bırakılırsa 0 kabul edilir.

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
- Banka Açılış Fişi (Açılış formu ile)

Özellikler:
- Gider/Gelir fişlerinde Hizmet kartı satırları + Banka karşı satırı
- Virman ve transfer türlerinde tek tutarlı özel form
- POS hesapları ile normal banka hesapları ayrıştırılır
- Bankaya Yatan / Bankadan Çekilen işlemlerinde karşı hesap Kasa'dır
- Gelen/Giden Transfer işlemlerinde karşı hesap Cari'dir

**Excel İçe Aktarma (`banka_import.py`)**
- Template sayfası: "Banka İşlemleri" + "Açıklama"
- Sütunlar: Fiş Türü, Tarih, Fiş No, Açıklama, Ana Banka, Hedef / Karşı Hesap, Gider/Gelir Kartı, Yön, Satır Açıklaması, Miktar, Birim Fiyat, KDV %, Tutar
- Blokeyi Bankaya Aktar: Ana Banka POS, Hedef normal banka hesabı olmalıdır.
- Bankaya Yatan / Bankadan Çekilen: Ana Banka normal (Vadesiz), karşı hesap Kasa.
- Gelen/Giden Transfer: Ana Banka normal (Vadesiz), karşı hesap Cari.

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

**Excel İçe Aktarma (`cari_import.py`)**
- Template sayfası: "Cari İşlemleri" + "Açıklama"
- Sütunlar: Fiş Türü, Tarih, Fiş No, Açıklama, Ana Kart / Ödeme Hesabı, Ödeme Türü, Cari, Yön, Satır Açıklaması, Tutar
- Alacak Dekontu: Ana Kart / Ödeme Hesabı'na Gider kartı yazılır, satırlara Cariler.
- Borç Dekontu: Ana Kart / Ödeme Hesabı'na Gelir kartı yazılır, satırlara Cariler.
- Cari Ödeme/Tahsilat: Ödeme Türü (Kasa/Banka) ve Ödeme Hesabı (kasa/banka adı) girilir, satırlara Cariler.
- Cari Virman: Yön (Borç/Alacak) ile Cariler girilir, borç toplam = alacak toplam.

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

**Excel İçe Aktarma (`fatura_import.py`)**
- Template sayfası: "Fatura İşlemleri" + "Açıklama"
- Sütunlar: Fiş Türü, Tarih, Fatura No, Açıklama, Cari, Ödeme Tipi, Ödeme Hesabı, Stok/Hizmet Adı, Satır Açıklaması, Miktar, Birim Fiyat, KDV %, Tutar
- Vadeli faturalarda Cari zorunludur; Nakit/Banka/POS faturalarında Ödeme Hesabı zorunludur.
- Hizmet faturalarında Miktar kullanılmaz (otomatik 1).

### 5.5. Çek/Senet

Fiş türleri:
- Çek/Senet Giriş Fişi
- Çek/Senet Bankaya Tahsile Verme
- Çek/Senet Ciro Etme
- Çek/Senet Tahsil Fişi
- Çek/Senet İade Fişi
- Çek/Senet Açılış Fişi

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

**Excel İçe Aktarma (`cek_senet_import.py`)**
- Şu an yalnızca **Çek/Senet Giriş Fişi** ve **Çek/Senet Açılış Fişi** desteklenir.
- Template sayfası: "Çek/Senet İşlemleri" + "Açıklama"
- Sütunlar: Fiş Türü, Tarih, Fiş No, Açıklama, Seri No, Tür, Banka Kurumu, Vade, Tutar, Keşideci, Ciranta, Cari / Karşı Hesap, Satır Açıklaması, Kasa / Banka Hesabı, Tahsil Türü, Durum
- Seri No benzersiz olmalıdır; aynı seri no daha önce kullanılmışsa hata verilir.
- Giriş fişinde Cari zorunludur; Açılış fişinde Cari istenmez.

### 5.6. Tanımlar

Tanımlar notebook'u şu sekmelerden oluşur:
- Stok Kartları
- Cari Kartları
- Kasa Kartları
- Hizmet Kartları (Gider/Gelir + Grup)
- Banka Hesapları
- Banka Kurumları
- **Excel Yükle** (en son sekme) – Tanım kartlarını Excel'den toplu içe aktarır.

Tanımlar sekmeler arası geçişte otomatik yenilenir.

**Excel İçe Aktarma (`tanim_import.py`)**
- "Excel Yükle" sekmesinden erişilir.
- Tek Excel dosyasında 6 sayfa: Cari Kartlar, Stok Kartları, Hizmet Kartları, Kasa Kartları, Banka Kurumları, Banka Hesapları
- Aynı isimde kart tanımlıysa hata verir (güncelleme yapılmaz, manuel olarak düzenlenmesi gerekir).
- Stok Kategori/Birim otomatik oluşturulur.
- Hizmet Grubu ve Banka Kurumu eksikse otomatik oluşturulur.

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
- Kasa (manuel + Excel import)
- Banka (manuel + Excel import)
- Cari (manuel + Excel import)
- Fatura (manuel + Excel import)
- Çek/Senet (manuel + Excel import – Giriş ve Açılış)
- Tanımlar (manuel + Excel import – Cari, Stok, Hizmet, Kasa, Banka)
- Raporlar

Uygulama, tek kullanıcılı yerel ön muhasebe işlemlerini fiş bazlı olarak yönetebilecek durumdadır.
Tüm modüller Excel import desteğine sahiptir.
