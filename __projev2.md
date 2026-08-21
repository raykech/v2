# Ön Muhasebe v2 - Proje Mimarisi ve Teknik Dokümantasyon

> **ÖNEMLİ NOT:** Artık `v2` klasörü yok. Dosyalar doğrudan ana dizinde (`core/`, `modules/`, `ui/`, `utils/`).
> Tüm importlar `from core...`, `from modules...`, `from ui...`, `from utils...` şeklinde yapılır.
> Uygulama `python __main__.py` ile çalıştırılır.

Bu doküman, projenin v2 mimarisinin mevcut teknik yapısını, modüllerini ve temel iş akışlarını anlatır. Amaç, geliştirilen yeni sistemin nasıl çalıştığını açık ve anlaşılır bir şekilde belgelemektir.

---

## 1. Proje Hakkında

Bu proje, Python, Tkinter ve SQLite kullanılarak geliştirilmiş yerel bir ön muhasebe uygulamasının **v2 mimarisidir**. v1'deki tekil işlem mantığından, modern ve esnek bir "çok satırlı fiş" yapısına geçilmiştir.

**v2 Mimarisi Temel Amaçları:**
- **Fiş/Satır Modeli:** Tüm işlemleri (kasa, fatura vb.) bir başlık ve ona bağlı birden çok detay satırından oluşan fişler olarak yönetmek.
- **Modüler Dosya Yapısı:** Kod bakımını kolaylaştırmak için her modülü kendi klasörü içinde (`view`, `form` vb.) organize etmek.
- **Sorumlulukların Ayrılması (SoC):** Veritabanı (`core/db.py`), iş mantığı (`core/services.py`) ve arayüz (`modules/`, `ui/`) katmanlarını net bir şekilde ayırmak.
- **Sezgisel Kullanıcı Deneyimi:** Excel benzeri satır girişi, dinamik formlar ve gelişmiş filtreleme gibi modern arayüz desenleri kullanmak.

---

## 2. Mimari ve İş Akışı (v2)

### 2.1. Ana Pencere ve Modül Yönetimi (`main_window.py`)

- **Sekmeli Arayüz:** Uygulama, açılan her modülü bir sekme olarak yönetir. Bu, kullanıcının aynı anda birden fazla modülde çalışmasına olanak tanır.
- **Dinamik Sekme Yönetimi:**
  - `_modul_aci`: Bir modül ilk kez açıldığında, ilgili `Frame`'i oluşturur ve sekmeler çubuğuna ekler. Zaten açıksa, o sekmeyi öne getirir.
  - `_tab_ekle`: Sekme çubuğuna modül adını taşıyan bir buton ve bir kapatma ("x") butonu ekler.
  - `_tab_kapat`: İlgili sekmenin arayüzünü ve referanslarını yok ederek sekmeyi kapatır.

---

### 2.2. Fiş/Satır Veritabanı Modeli (`core/db.py`)

v2 mimarisi, iki ana tablo üzerine kuruludur:

1.  **`fisler` Tablosu:** İşlemin genel başlık bilgilerini tutar.
    - **Sütunlar:** `id`, `tarih`, `fis_turu` ('Kasa Gider Fişi' vb.), `fis_no`, `aciklama`, `toplam_tutar`, `kaynak_modul`, `kaynak_fis_id`.

2.  **`fis_satirlari` Tablosu:** Her fişin detay satırlarını (masraf, hizmet, KDV vb.) tutar.
    - **Sütunlar:** `id`, `fis_id` (ilişki), `hesap_turu` ('Hizmet', 'Kasa'), `hesap_id`, `aciklama`, `borc`, `alacak`, `kdv_oran`, `kdv_tutar`.
    - Bu yapı, bir fiş altında birden çok kalemin işlenmesine olanak tanır.

---

### 2.3. Arayüz Mimarisi ve Bileşenler

- **Liste Ekranları (`..._view.py`):**
  - Standart yapı: Filtreler + Liste.
  - Gelişmiş filtreleme: Cari, Tarih Aralığı, Fiş Türü ve genel bir arama kutusu gibi alanlar içerir.

- **Form Ekranları (`..._form.py`):**
  - Standart yapı: Fiş Başlığı + Satır Giriş Alanı + Satır Listesi + Toplamlar + Kaydet/Kapat Butonları.

- **`LookupWidget` (`lookup_widget.py`):**
  - "..." butonuna basıldığında arama ve seçim listesi açan, projede sıkça kullanılan bir bileşendir.
  - "Yeni" butonu ile, bulunduğu yerden ayrılmadan hızlıca yeni bir tanım kartı (stok, cari vb.) eklemeye olanak tanır.

---

### 2.4. Temel İş Akışları

#### Fiş Oluşturma ve Düzenleme

- **Dinamik Form Yapısı:** Formlar, `__init__` içinde aldığı `fis_turu` bilgisine göre `ayarla_form_yapisi` metodunu çalıştırır. Örneğin, `fis_turu` "Kasalar Arası Virman" ise, satır listesi gizlenir ve yerine "Hedef Kasa", "Virman Tutarı" gibi özel alanlar gösterilir.

- **Excel-Benzeri Satır Yönetimi:**
  - **Giriş Satırı:** Satır listesinin hemen üzerinde, veri girişi için ayrılmış sabit bir satır bulunur.
  - **Ekleme:** Kullanıcı bu satıra bilgileri girip "+" butonuna bastığında, `satir_ekle` metodu çalışır. Bu metot, satırı hem `Treeview` listesine görsel olarak ekler hem de `self.satirlar` sözlüğüne kaydeder.
  - **Düzenleme (Çift Tıklama):** Kullanıcı listedeki bir satıra çift tıkladığında, o satırın verileri yukarıdaki giriş satırına yüklenir. Değişiklik yapılıp tekrar "+" butonuna basıldığında, yeni bir satır eklemek yerine mevcut satır güncellenir.
  - **Silme ("X" İkonu):** Her satırın en sağındaki "❌" ikonuna tıklandığında ilgili satır silinir.

- **Anında KDV Güncelleme ve Otomatik Odaklanma:**
  - `LookupWidget`'tan bir stok/hizmet kartı seçildiği anda, o karta tanımlı KDV oranı **hemen** güncellenir.
  - Bu işlem için `LookupWidget`'ın `set` metodu "patch"lenerek ve `StringVar`'ın `trace` metodu kullanılarak, değerdeki her değişiklik anında yakalanır.
  - KDV güncellendikten sonra imleç, veri girişini hızlandırmak için otomatik olarak bir sonraki alan olan "Satır Açıklaması"na geçer.

#### Kaynak Takibi ve "Kaynağa Git" Özelliği

- **Amaç:** Veri bütünlüğünü korumak ve işlemlerin kökenini takip edebilmek.
- **Mekanizma:** `fisler` tablosundaki `kaynak_modul` ve `kaynak_fis_id` sütunları, bir fişin hangi modül tarafından ve hangi ana fişe bağlı olarak oluşturulduğunu kaydeder. Örneğin, bir faturanın peşin ödemesi, `kaynak_modul='Fatura'` ve `kaynak_fis_id=<fatura_id>` olarak işaretlenmiş bir Kasa fişidir.
- **Kural:** Bir fiş, yalnızca kendi oluşturulduğu modülden düzenlenebilir ve silinebilir.
- **Arayüz Davranışı:**
  - Liste ekranında, başka bir modülden oluşturulmuş bir fiş seçildiğinde "Düzenle" ve "Sil" butonları pasif hale gelir.
  - "Kaynağa Git" butonu aktifleşir. Bu butona tıklandığında, uygulama kullanıcıyı otomatik olarak kaynak modüle yönlendirir ve ilgili kaynak fişi seçili hale getirir.

#### Tanımlar Arası Senkronizasyon

- Tanımlar modülünde, sekmeler arası geçiş yapıldığında, yeni açılan sekmenin verileri `_on_tab_changed` metodu sayesinde otomatik olarak yenilenir.
- Bu, bir sekmede eklenen yeni bir tanımın (örn: Banka Kurumu), diğer sekmelerde (örn: Banka Hesapları) anında görünür olmasını sağlar.

---

## 3. Mevcut Modüller (v2 Mimarisi)

- **`core/`**:
  - `db.py`: Veritabanı bağlantısı ve `tablolari_olustur` ile şema yönetimi.
  - `services.py`: Merkezi iş mantığı. `fis_kaydet`, `fis_guncelle`, `fis_sil` gibi tüm modüllerin kullanabileceği fonksiyonları barındırır.

- **`modules/kasa/`**:
  - `kasa_view.py`: Kasa modülünün ana liste ekranı.
  - `kasa_form.py`: Kasa fişi ekleme ve düzenleme formu.

- **`modules/fatura/`**:
  - `fatura_view.py`: Fatura modülünün ana liste ekranı.
  - `fatura_form.py`: Fatura ekleme ve düzenleme formu.

- **`modules/cari/`**:
  - `cari_view.py`: Cari modülünün ana liste ekranı.
  - `cari_form.py`: Cari fişi ekleme ve düzenleme formu.
  - Fiş Türleri:
    - Alacak Dekontu (ana cari alacaklı, alt satırlar Gider hizmet kartları borçlu)
    - Borç Dekontu (ana cari borçlu, alt satırlar Gelir hizmet kartları alacaklı)
    - Cari Ödeme (cariler borçlu, karşı taraf kasa/banka alacaklı)
    - Cari Tahsilat (cariler alacaklı, karşı taraf kasa/banka borçlu)
    - Cari Virman (satır bazlı borç/alacak, toplam borç == toplam alacak)

- **`modules/banka/`**:
  - `banka_view.py`: Banka modülünün ana liste ekranı.
  - `banka_form.py`: Banka fişi ekleme ve düzenleme formu.
  - Fiş Türleri:
    - Banka Gider Fişi (Hizmet Gider kartları borçlu, banka hesabı alacaklı)
    - Banka Tahsil Fişi (Hizmet Gelir kartları alacaklı, banka hesabı borçlu)
    - Bankalar Arası Virman (ana banka alacaklı, hedef banka borçlu)

- **`modules/tanimlar/`**:
  - `tanimlar_view.py`: Stok, Hizmet, Kasa, Banka, Cari, Banka Kurumları ve Banka Hesapları tanım kartlarının yönetildiği sekmeli ana pencere.

- **`modules/raporlar/`**:
  - `raporlar_view.py`: Raporlar modülünün ana liste ekranı.
  - `stok_raporu_view.py`, `stok_durum_raporu_view.py`, `hesap_ekstresi_view.py`: Stok ve hesap ekstresi raporları.

- **`modules/cek_senet/`**: (Planlanıyor)
  - `cek_senet_view.py`, `cek_senet_form.py`: Çek/Senet modülü (bkz. `planv2.md`).

- **`ui/`**:
  - `main_window.py`: Ana uygulama penceresi, menüler ve sekme yönetimi.
  - `dialogs.py`: "Yeni Kart Ekle" gibi işlemler için kullanılan diyalog pencereleri.
  - `widgets/`: `lookup_widget.py` gibi yeniden kullanılabilir arayüz bileşenleri.

- **`utils/`**:
  - `formatters.py`: `format_currency`, `parse_currency` gibi yardımcı formatlama fonksiyonları.

---

## 4. Veritabanı ve Geliştirme Yaklaşımı

- **Veritabanı:** Proje, tek bir `on_muhasebe_v2.db` SQLite dosyası kullanır.
- **Şema Yönetimi:** Geliştirme aşamasında, veritabanı şeması değiştiğinde eski veritabanı dosyası manuel olarak silinir ve `db.py`'nin `tablolari_olustur` fonksiyonu ile yeniden oluşturulur. Bu, geliştirme sürecini hızlandırır.
- **Veri Bütünlüğü:** İşlemler (kaydetme, silme, güncelleme) `try...except...finally` blokları içinde ve `transaction` (commit/rollback) mantığıyla yönetilir.

---

## 5. Son Durum

Sistem şu anda v2 mimarisinin temel özelliklerini içeren, çalışan **Kasa, Cari, Banka ve Fatura** modüllerine sahiptir:
- Firma ve yıl seçimi ile giriş.
- Sekmeli modül arayüzü ve sekmeleri kapatma.
- **Kasa ve Banka Modülleri:**
  - Gelişmiş filtreleme (kasa/banka, tarih aralığı, fiş türü, arama).
  - Fiş türüne göre (Gider, Tahsil, Virman) dinamik olarak değişen fiş formları.
  - Excel benzeri arayüz ile çoklu satır ekleme, düzenleme ve silme.
  - Anında KDV güncelleme ve otomatik odaklanma.
  - Kaynak takibi ve “Kaynağa Git” özelliği.
- **Cari Modülü:**
  - Alacak/Borç Dekontu, Cari Ödeme/Tahsilat, Cari Virman fiş türleri.
  - Ödeme türüne göre (Kasa/Banka) otomatik karşıt hesap seçimi.
  - Satır bazlı borç/alacak yönetimi ve virman denge kontrolü.
  - Kaynak takibi ve “Kaynağa Git” özelliği.
- **Fatura Modülü:** Satış ve Alış faturaları, peşin/tahsilatlı ödeme yönetimi.
- **Tanımlar Modülü:**
  - Stok, Hizmet, Kasa, Banka, Cari kart tanımları.
  - Sekmeler arası otomatik veri yenileme.

Bu yapı, Çek/Senet modülünün de aynı sağlam temeller üzerinde hızla geliştirilmesi için bir şablon oluşturmaktadır.