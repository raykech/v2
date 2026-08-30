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
- Kullanıcı deneyimi: Excel benzeri satır girişi (satır içi düzenleme), dinamik formlar, LookupWidget ile hızlı seçim.

---

## 2. Dizin Yapısı

```
__main__.py                 Uygulama giriş noktası (firma/yıl seçimi + ana pencere)
core/
  db.py                     SQLite bağlantısı ve şema kurulumu
  services.py               Ortak fiş/kart servisleri + çek/senet yardımcıları
modules/
  giris/
    dashboard_view.py       Giriş sekmesi: 6 özet kart (Kasa, Banka Vadesiz, POS, Cari Alacak/Borç, Stok FIFO)
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
    fatura_fire_form.py     Fire Fişi formu (stok çıkışı → gider kartı)
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
  raporlar/
    raporlar_view.py        Raporlar ana görünümü (Notebook sekmeleri)
    hesap_ekstresi_view.py  Hesap ekstresi (Stok/Cari/Kasa/Banka/Hizmet — FIFO destekli)
    stok_raporlari_view.py  Stok Raporları ana sekmesi (iç Notebook, tembel sekmeler)
    stok_rapor_tabani.py    Stok raporları ortak taban sınıfı (tarih/kategori/durum/arama/limit)
    stok_durum_raporu_view.py  Stok Durum Raporu
    stok_satis_raporu_view.py  En Çok Satan / Az Satan + Hiç Satış Yapmayan ürünler
    stok_hareket_raporu_view.py  En Çok Hareket Gören Ürünler
    stok_karlik_raporu_view.py   Kârlılık Raporu (ürün bazında alış/satış/kâr, FIFO)
    hizmet_kartlari_raporu_view.py  Hizmet kartları mizan raporu
    kdv_raporu_view.py      KDV Raporu (191 İndirilecek / 391 Hesaplanan)
    cari_bakiye_raporu_view.py  Cari Bakiyeleri raporu
    satis_raporu_view.py    Aylık Satış Raporu (kâr/zarar, FIFO maliyet)
    cek_senet_raporlari_view.py  Çek/Senet raporları ana sekmesi (iç Notebook)
    cek_senet_portfoy_raporu_view.py   Portföy (güncel durum)
    cek_senet_vade_raporu_view.py      Vade Takvimi (vade dilimleri)
    cek_senet_seruven_raporu_view.py   Serüven (seçili çek/senedin hareketleri)
    cek_senet_cari_raporu_view.py      Cari Bazlı Özet
  ayarlar/
    ayarlar_view.py         Ayarlar ana görünümü (Notebook sekmeleri)
    firma_tanimlari_view.py Firma tanımları (ekle/düzenle/listele)
    yil_tanimlari_view.py   Yıl tanımları (genel_tanimlar 'Yillar' grubu)
ui/
  main_window.py            Ana pencere, sekmeler, F5 ile yeniden yükleme
  dialogs.py                Yeni kart ekleme/düzenleme diyalogları + FirmaYilDialog
  import_preview.py         Import önizleme dialog sınıfları (Kasa, Fatura, Banka, Cari, Çek/Senet, Tanım)
  widgets/
    lookup_widget.py        Arama ve seçim bileşeni
    advanced_treeview.py    Gelişmiş filtreli/sıralamalı Treeview bileşeni
    editable_treeview.py    Excel tarzı satır içi düzenleme bileşeni
    pagination.py           Aşağı kaydıkça yükleyen (infinite scroll) liste mixin'i
    tooltip.py              Tooltip bileşeni
utils/
  formatters.py             Para/tarih formatlama, KDV hesabı (Decimal + ROUND_HALF_UP)
  export.py                 Excel / PDF dışa aktarma
docs/laravel/               Gelecekteki Laravel + Vue + Inertia web geçiş planı (bağımsız dokümanlar)
__importlar/                Excel import deneme/örnek dosyaları (çalışma zamanı dışı)
```

> Not: `modules/raporlar/stok_raporu_view.py` eski bir dosyadır ve raporlar
> notebook'una bağlı değildir; yeni rapor yapısı `raporlar_view.py` üzerinden kurulmuştur.
> Silinmesi `plan.md` 🔵 refaktoring backlog'da bekliyor.

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
- **hizmet_kartlari_gruplari**: `id`, `grup_adi`, `tur`, `firma_id`, `durum` — her firma için varsayılan "Diğer" (Gider/Gelir) ve "KDV" grupları şema kurulumunda oluşturulur
- **genel_tanimlar**: `id`, `grup`, `deger`, `firma_id` — stok kategorisi/birimi gibi değerlerin yanında **"Yillar"** grubuyla çalışma yılı tanımlarını da tutar

### 3.2. Fiş Modeli

**fisler**

| Kolon | Açıklama |
|---|---|
| `id` | Birincil anahtar |
| `tarih` | İşlem tarihi |
| `fis_turu` | Fiş türü |
| `fis_no` | Evrak/fiş numarası (aynı firma + yıl + tarih içinde benzersiz olmalıdır) |
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
| `fis_id` | `fisler.id` referansı (ON DELETE CASCADE) |
| `hesap_turu` | `Stok`, `Hizmet`, `Cari`, `Kasa`, `Banka`, `CekSenet` |
| `hesap_id` | İlgili tanım kartının ID'si |
| `aciklama` | Satır açıklaması |
| `miktar` | Miktar |
| `birim_fiyat` | Birim fiyat |
| `borc` / `alacak` | Borç ve alacak tutarları |
| `kdv_oran` | KDV oranı (KDV tutarı satırda tutulmaz; ayrı KDV satırı üretilir) |
| `firma_id` | Firma |

**Performans indeksleri:** `fis_satirlari (hesap_turu, hesap_id, firma_id)` ve `fisler (firma_id, tarih)` üzerinde otomatik oluşturulur.

### 3.3. Çek/Senet Modeli

**cekler_senetler**

- `id`, `seri_no` (benzersiz), `turu` (`Çek`/`Senet`), `banka`, `banka_id`, `vade_tarihi`, `tutar`
- `firma_id`, `created_at`, `updated_at`
- `kesideci`, `ciranta`, `aciklama`

**cek_senet_hareketleri**

- `id`, `cek_senet_id`, `fis_id`, `islem_tarihi`, `durum`
- `karsi_hesap_tipi`, `karsi_hesap_id`, `karsi_hesap_ismi`
- `ilgili_hareket_id`, `aciklama`, `firma_id`, `created_at`

### 3.4. Firma

- **firmalar**: `id`, `firma_adi`, `durum` — varsayılan "Ana Firma (Varsayılan)" şema kurulumunda oluşturulur

---

## 4. Ortak İş Mantığı (`core/services.py`)

- `fis_no_kontrol(...)` – Fiş numarasının aynı firma + yıl içinde benzersizliğini kontrol eder
  (tarih verilirse aynı tarih içinde tekrar da engellenir; boş numaraya izin verilir).
- `fis_kaydet(...)` – Yeni fiş + satırlar + opsiyonel peşin ödeme fişi kaydeder. Kayıttan önce `fis_no_kontrol` yapılır.
- `fis_guncelle(...)` – Fişi ve satırlarını günceller, eski peşin ödeme fişini siler. (`yil` UPDATE'te de set edilir)
- `fis_sil(...)` – Fişi ve bağlı satırları siler.
- `kaydet_kart(...)` / `kart_sil(...)` – Tanım kartlarını ekler/günceller/siler.
- `is_kart_kullanilmis_mi(...)` – Kartın fişlerde kullanılıp kullanılmadığını kontrol eder.
- **Güvenlik (SQL enjeksiyon whitelist):** `GECERLI_KART_TABLOLARI` sözlüğü; `kart_sil`,
  `kaydet_kart` ve `is_kart_kullanilmis_mi` fonksiyonları tablo adını bu whitelist'ten
  geçirmeden çalışmaz — izin verilmeyen tablo adı reddedilir.
- **KDV yardımcıları:**
  - `kdv_hesap_idleri(cursor, firma_id)` – Firmanın 191/391 KDV hesap ID'lerini döndürür `(indirilecek, hesaplanan)`.
  - `kdv_satiri_olustur(kdv_hesap_id, kdv_tutar, yon, aciklama)` – KDV için ayrı fiş satırı üretir (`yon`: `'borc'` → 191, `'alacak'` → 391).
- **Stok yardımcısı:**
  - `stok_bakiye_ve_maliyet(cursor, firma_id)` – Stok bakiyesi (miktar) + FIFO kalan maliyeti
    `{stok_id: değer}` sözlükleri olarak `(bakiyeler, maliyetler)` döndürür. Tek kaynak;
    Stok Durum Raporu ve Giriş dashboard'u kullanır. `fis_satirlari` üzerinde tam tarama
    gerektirdiğinden **tanım listelerinde çalıştırılmaz** (Tanımlar → Stok artık saf kart listesidir).
- **Dönem kontrolü:**
  - `aktif_yil_kontrolu(tarih_nesnesi, aktif_yil)` – Fiş tarihi seçili çalışma yılı dışındaysa açıklayıcı hata mesajı döndürür, uygunsa `None`. Tüm fiş formları kaydetmeden önce bu kontrolü yapar (yanlış yıla fiş taşınmasını engeller).
- Çek/Senet yardımcıları:
  - `cek_senet_guncel_durum`
  - `cek_senet_son_banka_takas`
  - `cek_senet_fis_son_hareket_mi`
  - `cek_senet_hareket_ekle`
  - `cek_senet_fis_sil`

**Para/KDV yuvarlama (`utils/formatters.py`):**
- `kdv_hesapla(...)` Decimal + `ROUND_HALF_UP` ile **2 ondalık ticari yuvarlama** yapar;
  Kasa/Banka/Fatura formları ve import'lar bu fonksiyonu kullanır — kuruş farkları ve
  float artıkları (örn. `0.18000000000000002`) oluşmaz.

---

## 4.1. KDV Modeli (Ayrı Satır / 191-391)

KDV, satır tutarına gömülmez; **ayrı bir fiş satırı** olarak kaydedilir. Bu, her fişin
borç toplamı = alacak toplamı şeklinde dengede kalmasını sağlar.

**Temel kural:**
- Net satır (KDV hariç) → satırın yönünde yazılır (Stok/Hizmet/Gelir/Gider kartı)
- KDV satırı → net satırla **aynı yönde**, `191 İndirilecek KDV` (borç) veya `391 Hesaplanan KDV` (alacak)
- Karşı satır (Cari / Kasa / Banka) → **brüt** (KDV dahil), ters yönde
- Sonuç: `net + KDV = brüt` → borç = alacak

**KDV hesabı seçimi (yöne göre):**
- Satır borçlu ise → 191 İndirilecek KDV (borç)
- Satır alacaklı ise → 391 Hesaplanan KDV (alacak)

| Fatura / Fiş | Satır (net) | KDV satırı | Karşı (brüt) |
|---|---|---|---|
| Satış Faturası (Vadeli) | Stok/Hizmet **alacak** | 391 **alacak** | Cari **borç** |
| Alış Faturası (Vadeli) | Stok/Hizmet **borç** | 191 **borç** | Cari **alacak** |
| Satış İade | Stok/Hizmet **borç** | 191 **borç** | Cari **alacak** |
| Alış İade | Stok/Hizmet **alacak** | 391 **alacak** | Cari **borç** |
| Kasa/Banka Gider | Gider kartı **borç** | 191 **borç** | Kasa/Banka **alacak** |
| Kasa Gelir | Gelir kartı **alacak** | 391 **alacak** | Kasa **borç** |
| Peşin Fatura | Stok/Hizmet (tek yön) + KDV (aynı yön) | — | Ayrı peşin fişinde Kasa/Banka (brüt) |

**Notlar:**
- Peşin faturalarda KDV, ana fatura fişinde üretilir; ödeme fişi brüt tutarı taşır (birlikte denge).
- **Banka gider/gelir fişleri KDV'sizdir** — KDV alanı ve hesaplaması banka formunda yoktur, `KDV %` sütunu importta yok sayılır.
- **Fire Fişi de KDV'sizdir** — satırlarda KDV yoktur; stok çıkışı (alacak) karşılığında Gider kartı borçlanır.
- Excel importta **"Tutar" sütunu her zaman nettir** (KDV hariç); KDV satırı sistem tarafından üretilir.

**Akıllı giriş (Tutar KDV Dahil):**
- Kasa ve Fatura formlarında giriş satırındaki **"Tutar (KDV Dahil)"** alanı doldurulursa
  birim fiyat otomatik hesaplanır: `birim_fiyat = tutar / (miktar × (1 + KDV%/100))`.
- Bu alan doluysa satır eklerken birim fiyat yerine bu tutar esas alınır.
- Ayrıca KDV % kolonu satır bazında düzenlenebilir; hesap değişince kartın KDV'si otomatik uygulanır.

---

## 5. Modüller ve Özellikler

### 5.0. Giriş (Genel Durum Dashboard)

Uygulama açıldığında giriş sekmesi **6 özet kart** gösterir (3 sütun × 2 satır):

| Kart | İçerik |
|---|---|
| Kasa Toplam Bakiye | Tüm kasaların `Σ(borç) − Σ(alacak)` |
| Banka Toplam Bakiye | Yalnız **Vadesiz** türü banka hesapları |
| POS Toplam Alacak | `hesap_turu='POS'` banka hesaplarının bakiyesi |
| Toplam Alacak | Bize borçlu olan carilerin toplamı |
| Toplam Borç | Bizim cariye borcumuzun toplamı |
| Eldeki Stok Maliyet (FIFO) | Ortak servis `stok_bakiye_ve_maliyet` üzerinden (stok raporuyla aynı kaynak) |

Sekmeye her geçişte otomatik yenilenir (`yenile()`).

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
- **KDV ayrı satır**: Gider/Gelir fişlerinde KDV, net satırla aynı yönde 191/391 hesabına ayrı satır olarak yazılır (fiş dengelenir)
- **Akıllı giriş**: "Tutar (KDV Dahil)" alanından birim fiyat otomatik hesaplanır
- **Satır içi düzenleme**: `EditableTreeview` ile hücreye çift tık → yerinde düzenleme (hesap, açıklama, miktar, birim fiyat, KDV %)

**Excel İçe Aktarma (`kasa_import.py`)**
- Template sayfası: "Kasa İşlemleri" + "Açıklama"
- Sütunlar: Fiş Türü, Tarih, Fiş No, Genel Açıklama, Kasa / Ana Kasa, Hedef Kasa, Gider/Gelir Kartı, Yön, Satır Açıklaması, Miktar, Birim Fiyat, KDV %, Tutar
- Gruplama: Aynı Fiş No + Tarih + Kasa satırları tek fişte toplanır. Fiş No boşsa her satır ayrı fiş.
- KDV % boş bırakılırsa 0 kabul edilir.
- **Tutar sütunu nettir** (KDV hariç); KDV ayrı satır olarak otomatik üretilir.

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
- **Banka gider/gelir fişleri KDV'sizdir** (KDV alanı yoktur; importta `KDV %` sütunu yok sayılır)
- **Satır içi düzenleme**: `EditableTreeview` (hesap/açıklama/miktar/birim fiyat)

**Excel İçe Aktarma (`banka_import.py`)**
- Template sayfası: "Banka İşlemleri" + "Açıklama"
- Sütunlar: Fiş Türü, Tarih, Fiş No, Açıklama, Ana Banka, Hedef / Karşı Hesap, Gider/Gelir Kartı, Yön, Satır Açıklaması, Miktar, Birim Fiyat, KDV %, Tutar
- Blokeyi Bankaya Aktar: Ana Banka POS, Hedef normal banka hesabı olmalıdır.
- Bankaya Yatan / Bankadan Çekilen: Ana Banka normal (Vadesiz), karşı hesap Kasa.
- Gelen/Giden Transfer: Ana Banka normal (Vadesiz), karşı hesap Cari.
- Banka işlemleri KDV'sizdir; `KDV %` sütunu dikkate alınmaz.

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
- **Satır içi düzenleme**: `EditableTreeview` (hesap lookup + Borç/Alacak yönü + açıklama + tutar)

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
- **Fire Fişi** (KDV'siz stok fire kaydı)

Ödeme tipleri:
- Vadeli
- Nakit (Kasa)
- Banka
- POS

Özellikler:
- Stoklu ve hizmetli fatura desteği
- İade faturalarında borç/alacak yönü otomatik ters çevrilir (`is_satis`/`is_iade` mantığı — "Hizmet Satış Faturası" gibi türlerde de doğru çalışır)
- Peşin ödemelerde `kaynak_modul='Fatura'` ve `kaynak_fis_id=<fatura_id>` ile bağlı Kasa/Banka fişi oluşturulur
- KDV otomatik dolum ve satır toplamı hesabı
- **KDV ayrı satır**: fatura satırı net, KDV 191/391 hesabına ayrı satır olarak yazılır; cari karşılığı brüt → fiş dengelenir
- **Akıllı giriş**: "Tutar (KDV Dahil)" alanından birim fiyat otomatik hesaplanır
- **Satır içi düzenleme**: `EditableTreeview` (stok/hizmet lookup + açıklama + miktar + birim fiyat + KDV % + toplam ters hesap)
- Peşin ödeme yönü: Satış (iade değil) ve Alış İade → **Tahsilat**; Alış (iade değil) ve Satış İade → **Ödeme**

**Fire Fişi (`fatura_fire_form.py`):**
- Stok satırları **alacak** (stok çıkışı), üstte seçilen **Fire Gider Kartı** (Hizmet, Gider türü) toplam tutar kadar **borç**lanır → fiş dengelenir.
- KDV'sizdir; satırlarda KDV hesaplanmaz.
- `kaynak_modul='Fatura'` ile kaydedilir; Fatura modülünün "Yeni ▼" menüsünden ve tür filtresinden erişilir.
- Düzenleme modunda stok satırları + gider kartı geri yüklenir.

**Excel İçe Aktarma (`fatura_import.py`)**
- Template sayfası: "Fatura İşlemleri" + "Açıklama"
- Sütunlar: Fiş Türü, Tarih, Fatura No, Açıklama, Cari, Ödeme Tipi, Ödeme Hesabı, Stok/Hizmet Adı, Satır Açıklaması, Miktar, Birim Fiyat, KDV %, Tutar
- Vadeli faturalarda Cari zorunludur; Nakit/Banka/POS faturalarında Ödeme Hesabı zorunludur.
- **Miktar × Birim Fiyat, stok ve hizmet faturalarında aynı şekilde uygulanır** (Miktar boşsa 1 kabul edilir; Birim Fiyat boşsa Tutar / Miktar ile hesaplanır).
- **Tutar sütunu nettir** (KDV hariç); KDV ayrı satır olarak otomatik üretilir.

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
- Satır içi düzenleme: "Çek/Senet" kolonu bileşik görüntü olduğundan **sadece tutar (yeni tip) ve açıklama** hücre içinde düzenlenebilir; çek/senet seçimi sil + üstten yeniden ekleme ile değiştirilir.

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
- Hizmet Kartları (Gider/Gelir/KDV + Grup)
- Banka Hesapları
- Banka Kurumları
- **Excel Yükle** (en son sekme) – Tanım kartlarını Excel'den toplu içe aktarır.

Tanımlar sekmeler arası geçişte otomatik yenilenir.

> **Stok Kartları listesi (performans):** Liste yalnızca `stoklar` tablosunu çeker;
> "Mevcut Miktar" ve "Maliyet Değeri" sütunları kaldırıldı (eskiden her aramada
> `fis_satirlari` üzerinde iki tam tarama + FIFO döngüsü çalışıyordu). Miktar/maliyet
> ve kritik stok (kırmızı) boyaması artık yalnızca Stok Durum Raporu'nda gösterilir.
> Listede sadece pasif kartlar gri boyanır.

> Not: `191 İndirilecek KDV` ve `391 Hesaplanan KDV` kartları ile "KDV" grubu, veritabanı
> şeması kurulurken (`core/db.py`) otomatik oluşturulur; elle silinmemeli/düzenlenmemelidir
> (fiş satırlarında kullanıldıkları için kullanımda olan kart silinemez).

**Hizmet kartı türü kilidi:** İşlem görmüş (fişlerde kullanılmış) bir hizmet kartının
**Tür'ü (Gider/Gelir) değiştirilemez** — hizmet kartları raporu bir mizandır; tür değişikliği
geçmiş kayıtları yanlış bölüme taşır. Yanlış kart açıldıysa yeni kart açılması veya ileride
"Hesap Taşı" özelliğinin kullanılması önerilir.

**Excel İçe Aktarma (`tanim_import.py`)**
- "Excel Yükle" sekmesinden erişilir.
- Tek Excel dosyasında 6 sayfa: Cari Kartlar, Stok Kartları, Hizmet Kartları, Kasa Kartları, Banka Kurumları, Banka Hesapları
- Aynı isimde kart tanımlıysa hata verir (güncelleme yapılmaz, manuel olarak düzenlenmesi gerekir).
- Stok Kategori/Birim otomatik oluşturulur.
- Hizmet Grubu ve Banka Kurumu eksikse otomatik oluşturulur.

### 5.7. Raporlar

Raporlar notebook'undaki sekmeler:

| Sekme | Dosya | İçerik |
|---|---|---|
| **Stok Raporları** | `stok_raporlari_view.py` | İç notebook (bkz. aşağıdaki alt sekme tablosu) — tüm stok raporları tek yerde |
| Cari Ekstre | `hesap_ekstresi_view.py` (Cari) | Cari hareketleri + bakiye |
| Kasa Ekstre | `hesap_ekstresi_view.py` (Kasa) | Kasa hareketleri + bakiye |
| Banka Ekstre | `hesap_ekstresi_view.py` (Banka) | Banka hareketleri + bakiye |
| Hizmet Kartları Raporu | `hizmet_kartlari_raporu_view.py` | Mizan: GELİRLER üstte, GİDERLER altta, gruplar altında kartlar; **tarih aralığına uyar** ve tutarlar **miktar × birim fiyat**tan hesaplanır |
| Hizmet Kartları Detay | `hesap_ekstresi_view.py` (Hizmet) | Hizmet kartı hareket detayı; satır tutarları **miktar × birim fiyat**tan hesaplanır |
| Çek/Senet Raporları | `cek_senet_raporlari_view.py` | İç notebook: **Portföy** (güncel durum), **Vade Takvimi** (vade dilimleri), **Serüven** (seçili çek/senedin hareketleri), **Cari Bazlı Özet** |
| KDV Raporu | `kdv_raporu_view.py` | 191 İndirilecek / 391 Hesaplanan hareketleri; tarih aralığı, aylık alt toplamlar, genel toplamlar ve **"Ödenecek/Devreden KDV (391 − 191)"** farkı |
| Cari Bakiyeleri | `cari_bakiye_raporu_view.py` | Tüm carilerin güncel borç/alacak bakiyeleri + **Cari Türü (Müşteri/Tedarikçi/Diğer) filtresi** + toplamlar |
| Kar/Zarar Raporu | `satis_raporu_view.py` | **Aylık** sekme (ay seçimiyle detaylar) + **Yıllık** sekme (12 ay 6+6 grid, her ayın tüm kalemleri, altta tüm yıl toplamları) |

#### Stok Raporları (alt sekmeler)

Yeni stok raporları `stok_rapor_tabani.StokRaporTabani` ortak sınıfını kullanır:
**tarih aralığı** (varsayılan: aktif yılın tamamı), **kategori**, **durum (Aktif/Pasif/Tümü)**
ve **limit (İlk 20 / 50 / 100 / Tümü)** filtreleri + Excel/PDF aktarımı ortaktır.
Bu raporlarda **kart arama/lookup alanı yoktur** (bilinçli karar): çıktı zaten sıralı bir
liste olduğu için listede tekrar kart aramanın anlamı yok — tek bir ürünün hareketi
istendiğinde **Stok Ekstresi** alt sekmesi kullanılır.
Veri kaynağı `core/services.py` → `stok_donem_ozeti()` (fiş türü bazında dönem özeti) ve
`stok_donem_cogs()` (kart bazında FIFO maliyet) servisleridir.

| Alt Sekme | Dosya | İçerik |
|---|---|---|
| Stok Durum | `stok_durum_raporu_view.py` | Stok kartları; kategori/durum filtreli, kalan miktar + maliyet (ortak servis `stok_bakiye_ve_maliyet`) |
| Stok Ekstresi | `hesap_ekstresi_view.py` (hesap_turu='Stok') | FIFO maliyet yöntemiyle giriş/çıkış/kalan miktar + maliyet |
| En Çok Satan | `stok_satis_raporu_view.py` (mod='cok') | Net satış miktarına göre **azalan** sıralı liste (satış − satış iadesi) |
| Az Satan | `stok_satis_raporu_view.py` (mod='az') | Satışı olan ürünlerin **artan** sıralı düşük performanslıları |
| Hiç Satış Yapmayan | `stok_satis_raporu_view.py` → `StokHicSatisRaporuView` | Dönemde net satışı 0 olan kartlar; bağlı sermayeye (maliyet değeri) göre sıralı, "Tüm Dönem Satış" sütunuyla **ölü stok** ayrımı (turuncu) |
| En Çok Hareket Gören | `stok_hareket_raporu_view.py` | Dönemdeki **fiş satırı sayısına** göre sıralı; alış/satış/iade/fire-çıkış miktarları + işlem hacmi + son hareket |
| Kârlılık | `stok_karlik_raporu_view.py` | Ürün bazında alış/satış **miktar + tutarı**, **FIFO maliyet**, **kâr** ve **kâr marjı %** (yeşil/kırmızı), altta TOPLAM satırı |

Tüm raporlar **Excel (.xlsx)** ve **PDF** olarak dışa aktarılabilir (`utils/export.py` → `export_treeview_data`).

**Rapor yükleme davranışı:** Raporlar sekmesine girildiğinde **rapor sekmeleri tembel (lazy) oluşturulur** — yalnızca ilk açılan sekme (Stok Raporları → Stok Durum) başta kurulur; diğer rapor sekmeleri ilk tıklandığında oluşturulur. İç içe notebook'larda (Stok Raporları, Çek/Senet Raporları) alt sekmeler de temeldir; `<<NotebookTabChanged>>` olayında `event.widget` kontrolüyle yalnızca kendi notebook'unun sekme değişimi işlenir. Hiçbir rapor otomatik veri yüklemez (kasıntı engeli); her rapor yalnızca kullanıcı **"Listele" / "Raporu Getir"** butonuna bastığında doldurulur. Ekstre sekmelerinde hesap seçimi **aramalı LookupWidget** ile yapılır (Cari/Stok/Kasa/Banka/Hizmet — listeden yeni kart da eklenebilir).

**Ekstrelerde Fiş ID ve sağ tık → Kaynağa Git:** Tüm ekstre tablolarında (Stok/Cari/Kasa/Banka/Hizmet Detay) her hareket satırının başında **Fiş ID** kolonu bulunur. Gösterilen ID, hareketin geldiği fişin **kaynak fiş** ID'sidir (eğer varsa — örn. peşin ödeme fişi yerine asıl fatura ID'si görünür); kaynak yoksa fişin kendi ID'si yazılır. Bir satıra **sağ tıklanınca → "Kaynağa Git"** menüsü açılır; tıklanırsa ilgili fişin modülüne gidilir ve fiş listede seçilip vurgulanır. Hedef fiş **aktif yıldan farklı bir yıldaysa uyarı verilir** ve gidilmez (önce durum çubuğundan yıl değiştirilmeli).


### 5.8. Ayarlar

Ayarlar notebook'u iki sekmeden oluşur:
- **Firma Tanımları** (`firma_tanimlari_view.py`): Firma ekleme/düzenleme, durum (Aktif/Pasif), arama filtresi.
- **Yıl Tanımları** (`yil_tanimlari_view.py`): `genel_tanimlar` tablosunun **"Yillar"** grubuna yıl ekleme/kaldırma; eklenen yıllar firma/yıl seçim ekranının yıl listesinde görünür.

Ayrıca ana pencerenin durum çubuğuna tıklanınca açılan **FirmaYilDialog** (`ui/dialogs.py`) ile
çalışma sırasında firma ve yıl değiştirilebilir; değişiklikte açık sekmeler kapatılıp modüller
yeni firma/yıl ile tazelenir.

---

## 6. Kullanıcı Arayüzü ve Deneyim

### 6.1. Ana Pencere

- Firma ve yıl seçimi ile giriş yapılır; ardından **Giriş (Genel Durum)** sekmesi açılır.
- Modüller sekmeler hâlinde açılır; sekmeler **sürüklenerek yeniden sıralanabilir** (Giriş sekmesi sabittir, en başta kalır), `x` ile kapatılabilir.
- Sekmeler arası geçişte aktif modül otomatik yenilenir.
- Durum çubuğu firma/yıl bilgisini gösterir; tıklanınca firma/yıl değiştirme diyaloğu açılır.
- Geliştirme sırasında **F5** ile aktif modül ve bağımlılıkları yeniden yüklenir.
- Modüller üst menüden ("Modüller") ve üst buton panelinden açılır.

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
- `main_app.go_to_module_and_select_fis(module_key, fis_id)` hedef modülü açar, açık formu kapatır ve fişi listede seçip vurgular.
- **Ekstre raporlarında sağ tık:** Stok/Cari/Kasa/Banka/Hizmet ekstrelerinde bir harekete sağ tıklanınca `go_to_module_and_select_fis` çağrılır ve o fişin olduğu modüle gidilir.

### 6.5. EditableTreeview (Satır İçi Düzenleme)

`ui/widgets/editable_treeview.py` — Excel tarzı, yeniden kullanılabilir satır içi düzenleme bileşeni:
- `column_config`: her düzenlenebilir kolon için `type` (`text` / `number` / `lookup` / `combobox`) tanımlanır.
- Hücreye çift tık → yerinde düzenleme; lookup hücrelerinde `...` butonu ile diyalog (sadece buton/Enter ile açılır).
- Enter → aynı satır içinde sağa ilerler (alt satıra geçmez); Esc → iptal; odak kaybı → onaylar.
- Düzenlenen satır hafif vurgu (`#fff3cd`); tam satır mavisi seçim yok (`selectmode="none"`).
- `on_edit(iid, kolon_id, deger)` → `True` dönerse düzenleme kabul edilir.
- Kasa, Banka, Cari, Fatura, Çek/Senet ve Açılış formları bu bileşeni kullanır.

### 6.6. Sayfalama (Infinite Scroll)

`ui/widgets/pagination.py` → `SayfaliListeMixin` — Treeview listeleri için **aşağı kaydıkça yükleme**:
- `listele()` yalnızca ilk `SAYFA_BOYUTU` (**50**) kaydı çeker; kullanıcı listenin alt %15'ine
  indikçe bir sonraki sayfa (`LIMIT ... OFFSET ...`) otomatik yüklenir.
- Yükleme **yalnızca gerçek kaydırma olaylarında** tetiklenir:
  - Fare tekerleği (`<MouseWheel>`, `<Button-4/5>`)
  - Klavye kaydırma tuşları (`Down`, `Up`, `Page Down/Up`, `Home`, `End` → `<KeyRelease>`)
  - Scrollbar sürükleme (`tree.yview` sarmalayıcısı ile `moveto`/`scroll` çağrıları)
  - Arka planda zamanlayıcı ile otomatik veri çekme **yoktur**; kullanıcı aşağı inmedikçe yüklenmez.
- Her yükleme sonunda durum çubuğuna süre yazılır: `Modül | İlk yükleme: X ms (50 kayıt, toplam N)`.
- Kullanım: sınıf `SayfaliListeMixin`'i miras alır, `create_widgets` içinde `_init_sayfalama(tree)`
  çağrılır; `listele` sorguyu `_sayfa_query`/`_sayfa_params`'a yazar ve `_diger_sayfa_yukle()` ile
  ilk sayfayı doldurur. Satır ekleme `_satirlari_ekle(rows)` metodundadır.
- **Sorgu optimizasyonu:** Kasa/Banka/Cari fiş listelerinde `JOIN fis_satirlari + SELECT DISTINCT`
  yerine **alt sorgu** kullanılır (`f.id IN (SELECT fis_id FROM fis_satirlari WHERE hesap_turu=... )`).
  Böylece DB, limit uygulanmadan önce on binlerce birleşik satırı tekilleştirmek zorunda kalmaz;
  Kasa açılışı ~1.8sn → ~280ms, sayfa yüklemesi ~1.6sn → ~30-60ms seviyelerine indi.
- **Sütun başlığına tıklayarak SQL tarafı sıralama:** `_enable_sortable_headers(tree, sort_map)` ile
  başlıklarda ▲/▼/↕ okları; `_order_by_sql()` whitelist'ten ORDER BY üretir (enjeksiyon koruması).
  Kasa, Banka, Cari, Fatura, Çek/Senet listelerinde aktif.
- Fiş listeleri (Kasa, Banka, Cari, Fatura, Çek/Senet) ve Tanımlar kart listeleri (Cari, Stok,
  Hizmet, Kasa, Banka Kurum/Hesap) bu bileşeni kullanır → açılış/sekme geçişlerindeki kasıntı giderilir.
- "Kaynağa Git" (`select_and_highlight_fis`): hedef fiş ilk yüklenen sayfada yoksa tüm sayfalar
  otomatik yüklenip fiş bulunur ve seçilir.

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
SQLite bağlantısında `PRAGMA foreign_keys = ON` açıktır (fiş silinince satırlar CASCADE ile temizlenir).

---

## 8. Geliştirme Notları / Kurallar

1. `iptal()` metodunda `self.destroy()` kullanılmaz; `pack_forget()` + `on_close()` + `view_container.pack()` kullanılır.
   (İstisna: `fatura_fire_form.py`'deki `kapat()` kendi listesini yeniden paketler ve `listele()` çağırır.)
2. `main_window.py` içinde `_yeniden_yukle_aktif_modul` metodu ve `module_map` **tek yerde** tanımlıdır
   (eski iki kopya birleştirildi; `go_to_module_and_select_fis` ayrı bir metottur). Yeni modül eklerken
   `module_map`'e hem bağımlılık listesi hem de ana sınıf eklenmelidir.
3. Lookup widget'ları `verileri_yukle()` ve `ayarla_form_yapisi()` çağrılarından sonra yapılandırılmalıdır.
4. Yeni kart ekleme işlemlerinde `ui/dialogs.py` içindeki `ac_kart_dialog` kullanılır.
5. Tüm kayıtlarda `firma_id` ve `yil` bilgisi korunmalıdır.
6. Çek/Senet seçimlerinde LookupWidget'tan dönen ID string olabilir; veri sözlüğü anahtarları integer olduğundan `int()` çevrimi yapılmalıdır.
7. KDV'li fiş üreten her yerde KDV ayrı satırı `kdv_satiri_olustur(...)` ile üretilir; hesap ID'leri `kdv_hesap_idleri(...)` ile alınır. Satır net, karşı satır brüt, KDV aynı yönde yazılır.
8. Düzenleme modunda fiş yüklerken KDV hesap satırları (191/391) normal satır listesine alınmaz; kaydederken yeniden üretilir.
9. KDV kartları (`tur='KDV'`) normal Gider/Gelir lookup'larında gösterilmez (tür filtresi).
10. Fiş tarihi seçili çalışma yılı dışında olamaz; tüm fiş formları kaydetmeden önce `aktif_yil_kontrolu(...)` ile bunu engeller. Importta dönem dışı satırlar uyarı ile kaydedilir.
11. **Fiş no tekrarı:** `fis_kaydet`/`fis_guncelle` aynı firma + yıl (+ tarih) içinde mükerrer numarayı `fis_no_kontrol(...)` ile reddeder.
12. **SQL enjeksiyon whitelist:** `kart_sil`, `kaydet_kart`, `is_kart_kullanilmis_mi` fonksiyonlarına tablo adı yalnızca `GECERLI_KART_TABLOLARI` üzerinden geçer.
13. **KDV yuvarlama:** Tüm KDV hesabı `utils/formatters.py` içindeki `kdv_hesapla` (Decimal + ROUND_HALF_UP) ile yapılır; elle `round()`/float aritmetiği kullanılmaz.
14. **Satır içi düzenleme:** Formlarda yeni satır girişi `EditableTreeview` ile yapılır; üst giriş alanı yalnızca yeni satır ekler. KDV % hücresi düzenlenebilir, hesap değişince kart KDV'si otomatik uygulanır, "Toplam (KDV Dahil)" hücresi düzenlenince birim fiyat geri hesaplanır.
15. **Fire Fişi** KDV'sizdir: stok satırları alacak, üstteki Gider kartı toplam borç — KDV satırı üretilmez.
16. **Hizmet satırı tutarı = miktar × birim fiyat:** Hizmet kartı raporları (mizan, ekstre, satış raporu hizmet bölümü) tutarı `fis_satirlari.borc/alacak` yerine `miktar * birim_fiyat`'tan hesaplar. Böylece veritabanında miktar elle düzeltildiğinde raporlar da güncellenir (fiş formuyla tutarlı). Karşı satırlar (Cari/Kasa/Banka) tutar bazlıdır.
17. **Raporlar otomatik yüklenmez:** Raporlar sekmesine geçişte hiçbir rapor `listele()` çalıştırmaz; yalnızca "Listele / Raporu Getir" butonu veriyi doldurur. `yenile()` yalnızca filtre/lookup verisini tazeler.
18. **Tarih filtresi LEFT JOIN içinde etkisiz olur:** Tarih aralığı koşulu `LEFT JOIN ... ON ... AND f.tarih BETWEEN ? AND ?` şeklinde yazılırsa filtrelenmez (join tarafı boş kalır, satırlar gelir). Tarih filtresi `fs.fis_id IN (SELECT id FROM fisler WHERE tarih BETWEEN ? AND ?)` (veya WHERE) ile uygulanmalıdır.
19. **Sayfalama:** Fiş/tanım listelerinde `listele()` tüm kayıtları çekmez; `SayfaliListeMixin` ile `LIMIT/OFFSET` kullanır. Yeni liste ekranı yazarken `_sayfa_query`/`_sayfa_params` + `_diger_sayfa_yukle()` + `_satirlari_ekle()` deseni uygulanmalıdır. Sayfa boyutu `SAYFA_BOYUTU = 50`'dir; yükleme yalnızca gerçek kaydırma olaylarında tetiklenir (periyodik zamanlayıcı kullanılmaz).
20. **Fiş listesi sorgusu:** Kasa/Banka/Cari gibi `fis_satirlari` ile filtreleyen listelerde `JOIN + DISTINCT` yazılmaz; `f.id IN (SELECT fis_id FROM fis_satirlari WHERE hesap_turu=... )` alt sorgusu tercih edilir (LIMIT öncesi satır şişkinliği/tekilleştirme maliyeti oluşmaz).
21. **Raporlar lazy yüklenir:** `RaporlarModulu` notebook sekmelerini ilk tıklamada oluşturur; rapor verisi yine yalnızca "Listele / Raporu Getir" ile doldurulur.
22. **Rapor grupları tek ana sekme altında:** Aynı konudaki raporlar (Stok, ileride Cari/Kasa/Banka…) `*_raporlari_view.py` dosyasında **iç notebook** altında toplanır; ana notebook'ta tek sekme olarak görünür. İç sekmeler de temeldir ve `<<NotebookTabChanged>>` işleyicisi `if event.widget is not self.notebook: return` ile kendi olayını süzer (iç içe notebook'ta üst notebook'un yanlış tetiklenmesini engeller).
23. **Rapor ortak taban sınıfı:** Bir grubun raporları filtre satırını tekrar yazmaz; `stok_rapor_tabani.StokRaporTabani` deseni gibi tek taban sınıftan türetılır (filtre alanları + `stok_sartlari()`/`tarih_araligi()`/`limit()` + Treeview kurulumu + Excel/PDF). Alt sınıf yalnızca `RAPOR_ADI`, `KOLONLAR` ve `listele()` yazar. Hesaplamalar `core/services.py`'de ortak servis olarak durur (`stok_donem_ozeti`, `stok_donem_cogs`); rapor dosyalarında SQL çoğaltılmaz. **Liste üreten raporlarda kart arama/lookup alanı kullanılmaz** — çıktı zaten sıralı liste olduğundan tek ürün istenirse ekstre sekmesine bakılır (lookup yalnızca ekstre gibi tek hesap seçimi zorunlu ekranlarda).

---

## 9. Güncel Durum

Tamamlanan modüller:
- Giriş (Genel Durum dashboard — 6 özet kart)
- Kasa (manuel + Excel import, satır içi düzenleme)
- Banka (manuel + Excel import – KDV'siz)
- Cari (manuel + Excel import)
- Fatura (manuel + Excel import – KDV ayrı satır) + **Fire Fişi**
- Çek/Senet (manuel + Excel import – Giriş ve Açılış)
- Tanımlar (manuel + Excel import – Cari, Stok, Hizmet, Kasa, Banka)
- Ayarlar (Firma Tanımları, Yıl Tanımları, çalışma sırasında firma/yıl değiştirme)
- Raporlar (**Stok Raporları** ana sekmesi: Stok Durum, Stok Ekstresi, En Çok Satan, Az Satan, Hiç Satış Yapmayan, En Çok Hareket Gören, Kârlılık), Cari/Kasa/Banka Ekstre, Hizmet Kartları + Detay, Çek/Senet Raporları, KDV Raporu, Cari Bakiyeleri, **Kar/Zarar Raporu** — Aylık/Yıllık)

Tamamlanan sistemler:
- **KDV modeli**: 191 İndirilecek / 391 Hesaplanan KDV hesapları otomatik oluşturulur;
  Kasa ve Fatura fişlerinde KDV ayrı satır olarak kaydedilir; Banka ve Fire Fişi KDV'sizdir.
- **Akıllı giriş**: Kasa ve Fatura formlarında "Tutar (KDV Dahil)" girişiyle birim fiyat otomatik hesaplanır.
- **Satır içi düzenleme (EditableTreeview)**: Kasa, Banka, Cari, Fatura, Çek/Senet, Açılış formlarında Excel tarzı hücre düzenleme.
- **Hizmet faturalarında miktar × birim**: Fatura formu + import'ta hizmet satırları da stokla aynı şekilde miktar × birim fiyat ile çalışır (gider + gelir). Raporlar (mizan, hizmet ekstre, satış raporu) hizmet tutarlarını miktar × birimden hesaplar — miktar manuel düzeltildiğinde raporlar da güncellenir.
- **Rapor performansı**: Raporlar sekmesine geçişte otomatik yükleme kaldırıldı (Listele/Raporu Getir ile dolar); ekstre hesap seçimleri aramalı LookupWidget'a çevrildi; Cari Bakiyeleri'ne cari türü filtresi eklendi; Hizmet Kartları Raporu'nun tarih aralığı filtresi düzeltildi.
- **Sayfalama (infinite scroll)**: Kasa/Banka/Cari/Fatura/Çek-Senet fiş listeleri ve Tanımlar kart listeleri aşağı kaydıkça yükleme yapar; sayfa boyutu 50, yükleme yalnızca gerçek kaydırma olaylarında tetiklenir — açılış/sekme geçiş kasıntısı giderildi.
- **Fiş listesi performansı**: Kasa/Banka/Cari listelerinde `JOIN + DISTINCT` yerine alt sorgu kullanıldı; Kasa açılışı ~1.8sn → ~280ms, sayfa başına yükleme ~1.6sn → ~30-60ms oldu.
- **Sütun sıralama (SQL tarafı)**: Fiş listelerinde başlık tıklayınca ▲/▼ sıralama; sayfalama ile birlikte çalışır.
- **Yükleme süresi göstergesi**: Alt durum çubuğunda ilk/sayfa yükleme süresi ve kayıt sayısı görüntülenir.
- **Raporlar lazy yükleme**: Raporlar sekmesi açılırken tüm raporlar değil, yalnızca seçilen sekme oluşturulur; raporlar sekmesi açılışı ~1.5sn → ~620ms.
- **Kar/Zarar Raporu**: Satış Raporu yeniden adlandırıldı; **Aylık** (mevcut detay) ve **Yıllık** (12 ay 6+6 grid + genel toplamlar) sekmeleri eklendi.
- **Veri bütünlüğü**: Fiş no tekrar kontrolü, kart tablosu whitelist (SQL enjeksiyon koruması), KDV'de Decimal + ROUND_HALF_UP ticari yuvarlama, `PRAGMA foreign_keys=ON` + CASCADE silme.
- **KDV Raporu**: 191/391 hareketleri, aylık alt toplamlar ve "Ödenecek/Devreden KDV (391 − 191)" farkı.
- **Stok raporları tek ana sekme altında + 4 yeni stok raporu**: Raporlar notebook'undaki *Stok Durum Raporu* ve *Stok Ekstresi* sekmeleri **Stok Raporları** ana sekmesinin içine (tembel alt sekmeler) alındı; aynı yere **En Çok Satan**, **Az Satan**, **Hiç Satış Yapmayan**, **En Çok Hareket Gören** ve **Kârlılık** raporları eklendi. Ortak altyapı: `stok_rapor_tabani.StokRaporTabani` (tarih aralığı + kategori + durum + limit filtreleri, Excel/PDF; kart arama alanı bilinçli olarak yok). Ortak veri servisi: `core/services.py` → `stok_donem_ozeti()` (fiş türü bazında dönem özeti: hareket sayısı, alış/satış/iade/fire miktar ve tutarları, işlem hacmi, son hareket) ve `stok_donem_cogs()` (kart bazında FIFO maliyet; Kar/Zarar raporundaki FIFO mantığıyla aynı, sadece satış faturası çıkışları). Kâr = net satış tutarı − FIFO maliyet; marj %'si ve TOPLAM satırı raporun altında.
- **Stok listesi performansı + ortak stok servisi**: Tanımlar → Stok Kartları listesi artık yalnızca `stoklar` tablosunu çekiyor (miktar/maliyet sütunleri ve her aramada çalışan iki `fis_satirlari` tam taraması + FIFO döngüsü kaldırıldı). Bakiye + FIFO kalan maliyet hesabı tek kaynakta: `core/services.py` → `stok_bakiye_ve_maliyet()`; Stok Durum Raporu ve Giriş dashboard'u bu servisi kullanıyor (kopya bloklar silindi).

Uygulama, tek kullanıcılı yerel ön muhasebe işlemlerini fiş bazlı olarak yönetebilecek durumdadır.
Tüm modüller Excel import desteğine sahiptir.

**Bekleyen özellikler (detay için `plan.md`):**
- Hesap Taşı (Hizmet Kartları): sağ tık → kayıtları aynı türdeki başka karta taşıma (opsiyonel tarih aralığı).
- **Refaktoring backlog** (tekrar taraması 30.08.2026 — `plan.md` 🔵): Excel import
  yardımcıları (`_metin`/`_sayi`/`_tarih` + kart aramaları) → `utils/import_helpers.py`;
  işlem liste ekranları → `FisListeMixin`; ölü dosya `stok_raporu_view.py` temizliği.
  **İşlem formları (kasa/banka/cari/fatura/çek-senet `_form.py`) bilerek ayrı tutuluyor — birleştirme kapsamı dışı.**
- İsteğe bağlı: "Kayıt Et" tıklanırken açık satır düzenlemesinin otomatik onaylanması; Çek/Senet kolonu için satır içi seçim.
- Web geçişi (Laravel 13 + Inertia + Vue) **`C:\Users\mehme\Herd\onmuhasebe\docs\GECIS_PLANI.md`** dosyasında
  yürüyor (Faz 0 kabuğu kuruldu). Bu dokümanın kapsamı dışında; eski taslak set `docs/laravel/` altında arşivdir.
