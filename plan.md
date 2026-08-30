# Plan ve Rehber — Ön Muhasebe v2

Bu dosya: tamamlanan işler, kararlar, ileride yapılacaklar ve **modül geliştirme şablonu**.
(30.08.2026 itibarıyla `planv2.md` bu dosyada birleştirildi; ayrı dosya kaldırıldı.)

Bölümler: 🟢 Tamamlandı · 🟠 Kararlar · 🔵 İleride Yapılacaklar · 📘 Modül Geliştirme Şablonu

---

## 🟢 Tamamlandı

### Raporlar — Stok Raporları grubu ve 4 yeni stok raporu (30.08.2026)
- **Stok Raporları ana sekmesi** (`modules/raporlar/stok_raporlari_view.py`): Raporlar
  notebook'undaki *Stok Durum Raporu* ve *Stok Ekstresi* sekmeleri iç notebook altına
  toplandı (Çek/Senet Raporları deseni). Alt sekmeler tembel (lazy) oluşturulur;
  `event.widget` süzmesiyle iç/üst notebook olayları birbirine karışmaz.
- **Yeni raporlar** (aynı ana sekmede): **En Çok Satan**, **Az Satan**,
  **Hiç Satış Yapmayan** (kullanıcı isteğiyle "az satan" ve "hiç satmayan" iki ayrı rapor),
  **En Çok Hareket Gören**, **Kârlılık**.
- **Ortak taban sınıf** `stok_rapor_tabani.StokRaporTabani`: tarih aralığı (varsayılan aktif
  yılı), kategori, durum (Aktif/Pasif/Tümü) ve limit (İlk 20/50/100/Tümü) filtreleri +
  Treeview kurulumu + Excel/PDF aktarımı tek yerden. Alt sınıf sadece `RAPOR_ADI`,
  `KOLONLAR`, `listele()` yazıyor.
- **Kart arama/lookup alanı KALDIRILDI (karar):** önce "Ara (kod/ad)" düz metin alanı
  LookupWidget'a çevrildi, sonra kullanıcı kararıyla tamamen kaldırıldı — bu raporların
  çıktısı zaten sıralı liste olduğu için listede tekrar kart aramanın gereği yok;
  tek ürün istenirse **Stok Ekstresi** sekmesine bakılır. Stok Durum Raporu'ndaki
  arama alanı da aynı gerekçeyle söküldü (kategori + durum filtresi kaldı).
  Not: lookup denemesinde `event_generate("<<LookupSelected>>")` olayının pencere görünür
  değilken teslim edilmediği görüldü — ileride gereken yerde `on_change` callback deseni kullanılır.
- **Ortak servisler** (`core/services.py`): `stok_donem_ozeti(cursor, firma_id, bas, bit)`
  → fiş türü bazında kart özetleri (hareket sayısı, alış/satış/satış iade/alış iade/fire
  miktar ve tutarları, giriş/çıkış toplamları, işlem hacmi, son hareket tarihi;
  `bas/bit=None` → tüm dönem) ve `stok_donem_cogs(...)` → kart bazında FIFO maliyet
  (fiş türü filtrelenebilir; Kârlılık'ta yalnızca `Satış Faturası` çıkışları).
  `stok_ozet_getir()` hareket görmemiş kart için sıfır sözlük döndürür.
- **Hesaplamalar:** Satış net = Satış Faturası − Satış İade Faturası (miktar ve tutar,
  KDV hariç = miktar × birim_fiyat). Kâr = net satış tutarı − FIFO maliyet; marj % ve
  TOPLAM satırı Kârlılık raporunda. Hiç Satış Yapmayan listesinde "Tüm Dönem Satış"
  sütunu turuncu ile **ölü stok** ayrımını gösterir; liste bağlı sermayeye göre sıralıdır.
- `ui/main_window.py` F5 yeniden yükleme bağımlılıklarına yeni rapor modülleri eklendi.
- **Doğrulama:** Servis toplamları ham SQL ile birebir (2025 satış tutarı 314.910,66 TL);
  FIFO maliyet satış çıkışları 191.494,77 TL, tüm çıkışlar 201.131,19 TL (fire/iade farkı).
  Tüm alt sekmeler Tkinter duman testinde üretildi ve `listele()` hatasız çalıştı.
- **Sonraki adım (kullanıcı planı):** aynı gruplama diğer raporlara (Cari, Kasa/Banka
  ekstreleri, Hizmet, Çek/Senet zaten grup) da aynı desenle uygulanacak.

### Performans — Stok listesi ve ortak stok servisi (30.08.2026)
- **Tanımlar → Stok Kartları listesi sadeleştirildi:** "Mevcut Miktar" ve "Maliyet Değeri"
  sütunları kaldırıldı. Liste artık yalnızca `stoklar` tablosunu çekiyor; önceden her
  açılış/filtre/aramada `fis_satirlari` üzerinde iki tam tarama (bakiye + tüm alışlar)
  ve Python'da FIFO döngüsü çalışıyordu. `low_stock` kırmızı boyaması da kalktı
  (miktar hesabına bağlıydı); pasif (gri) boyama korundu. Kritik stok uyarısı
  Stok Durum Raporu'nda görünmeye devam ediyor.
- **`core/services.py` → `stok_bakiye_ve_maliyet(cursor, firma_id)`** ortak servisi eklendi:
  bakiye + FIFO kalan maliyeti tek yerden hesaplıyor. Kullanıcıları: Stok Durum Raporu
  ve Giriş dashboard'u (ikisinin de kopya blokları silindi). Tanım listelerinde
  çalıştırılmaması gerektiği docstring'de not.

### Güvenlik & Veri bütünlüğü
- **Kart silme/sorgulamada SQL enjeksiyon whitelist'i** (`core/services.py`)
  - `kart_sil`, `is_kart_kullanilmis_mi` → `GECERLI_KART_TABLOLARI` doğrulaması eklendi.
- **Fiş no tekrarı kontrolü** (`core/services.py`)
  - `fis_no_kontrol()`; `fis_kaydet` / `fis_guncelle` aynı firma+yıl içinde mükerrer numarayı reddeder.
- **KDV hesabında 2 ondalık ticari yuvarlama** (`utils/formatters.py` → `kdv_hesapla`)
  - Kasa/Banka/Fatura formları ve import'lar artık Decimal + ROUND_HALF_UP ile hesaplıyor;
    kuruş farkları ve float artıkları (örn. 0.18000000000000002) ortadan kalktı.

### Kullanıcı Deneyimi — Satır bazlı düzenleme
- **`ui/widgets/editable_treeview.py`** — Excel tarzı, yeniden kullanılabilir satır içi düzenleme bileşeni.
  - Hücreye çift tık → yerinde düzenleme (metin / sayı / lookup `...` butonu).
  - Enter → aynı satır içinde sağa ilerler (alt satıra geçmez). Esc → iptal.
  - Düzenlenen satır hafif vurgu; tam satır mavi seçimi yok (`selectmode="none"`).
  - Lookup: hesap hücresinde readonly alan + `...` butonu; diyalog sadece buton/Enter ile açılır.
  - Kart seçiminden sonra otomatik olarak sonraki alana (Satır Açıklaması) geçer.
- **Kasa modülü** bu bileşene taşındı (üst alan sadece yeni satır ekler).
  - KDV % kolonu satıra eklendi; hesap değişince kartın KDV'si otomatik uygulanır.
  - "Toplam (KDV Dahil)" hücresi düzenlenince birim fiyat geri hesaplanır.
- **Açılış (Kasa/Banka/Cari), Banka, Fatura, Cari, Çek/Senet modülleri** de aynı bileşene taşındı:
  - Banka: KDV'siz; hesap/açıklama/miktar/birim fiyat satır içi düzenlenebilir.
  - Açılış & Cari: hesap (lookup) + yön (Borç/Alacak combobox) + açıklama + tutar.
  - Fatura: stok/hizmet lookup + açıklama + miktar + birim fiyat + KDV % + toplam (ters hesap).
  - Çek/Senet: "Çek/Senet" kolonu bileşik görüntü olduğundan satır içi **sadece tutar (yeni tip) ve açıklama** düzenlenebilir; çek/senet seçimi sil + üstten yeniden ekleme ile değiştirilir.

### Performans optimizasyonları
- **Fiş listesi sorgu optimizasyonu:** Kasa/Banka/Cari listelerinde `JOIN fis_satirlari + SELECT DISTINCT` yerine `f.id IN (SELECT fis_id FROM fis_satirlari ...)` alt sorgusu kullanıldı. Kasa açılışı ~1.8sn → ~280ms, sayfa yüklemesi ~1.6sn → ~30-60ms.
- **Sayfalama (infinite scroll) iyileştirmeleri:** Sayfa boyutu 200→50; yükleme yalnızca gerçek kaydırma olaylarında (tekerlek/klavye/scrollbar) tetiklenir; periyodik zamanlayıcı yok.
- **Yükleme süresi göstergesi:** Durum çubuğunda ilk/sayfa yükleme ms ve kayıt sayısı gösterilir.
- **Raporlar lazy yükleme:** Raporlar sekmesi açılırken tüm raporlar birden kurulmaz; yalnızca tıklanan sekme oluşturulur. Açılış ~1.5sn → ~620ms.
- **Kar/Zarar Raporu (Aylık/Yıllık):** Satış Raporu yeniden adlandırıldı; Aylık (mevcut) + Yıllık (12 ay 6×6 grid, her ayın tüm kalemleri, altta genel toplam) sekmeleri eklendi.
- **Enter ile giriş düzeltmesi:** Giriş ekranına pencere genelinde `<Return>` ve `<KP_Enter>` bağlandı (odak nerede olursa olsun çalışır).

### Kullanıcı Deneyimi — Liste sütun sıralama (fiş listeleri)
- **`ui/widgets/pagination.py`** — `SayfaliListeMixin`'e SQL tarafı sütun sıralama eklendi:
  - `_enable_sortable_headers(tree, sort_map)` → başlıklarda tıklanabilir oklar (▲/▼/↕).
  - `_order_by_sql()` → whitelist'ten ORDER BY üretir; sayfalama (LIMIT/OFFSET) bozulmaz.
  - `sort_map` sütun→SQL ifadesi eşlemesidir; kullanıcı girdisi SQL'e girmez (enjeksiyon koruması).
- **Kasa, Banka, Cari, Fatura, Çek/Senet fiş listeleri** bu özelliğe bağlandı.
  - Varsayılan sıralama `f.id DESC`; tarih/tutar/metin sütunlarına tıklayarak ASC↔DESC geçişi.
  - Fatura'da Cari Unvan (`c.unvan`), Çek/Senet'te Seri No (`seri_nolar` alias) de sıralanabilir.

---

## 🟠 Kararlar (kullanıcı onaylı)

### İşlem formları BİLEREK ayrı tutuluyor
- `kasa_form` / `banka_form` / `cari_form` / `fatura_form` / `cek_senet_form` arasındaki
  benzerlik (~%71) **bilinçli bir tasarım tercihidir**; ortak bir form taban sınıfına
  taşınmayacak. Her modülün fiş giriş davranışı kendine özgü evrilebilir.
  Tekrar taramalarında bu dosyalar "birleştirme adayı" olarak önerilmez.

### Hizmet kartı türü kilidi (uygulandı — `hizmet_view.py`)
- **İşlem görmüş bir hizmet kartının Tür'ü (Gider/Gelir) değiştirilemez.**
  - Gerekçe: Hizmet kartları raporu bir mizandır; gider kartı borç, gelir kartı alacak
    çalışır. Tür değişikliği geçmiş kayıtları mizanda yanlış bölüme taşır ve kartı
    hem borç hem alacak çalışmış "kirli" bir hesaba çevirir.
  - Kullanıcı yanlış kart açtıysa: yeni kart açması veya ileride "Hesap Taşı" kullanması önerilir.

---

## 🔵 İleride Yapılacaklar

### Refaktoring backlog — tekrar eden kod taraması (30.08.2026)
Tekrar taramasında bulunan kopya bloklar (işlem formları kapsam dışı — bkz. Kararlar):

1. **Excel import yardımcıları — yüksek kazanç / düşük risk**
   - `_metin`, `_sayi`, `_tarih` (~60'ar satır) **5-6 dosyada birebir kopya**:
     `kasa_import`, `banka_import`, `cari_import`, `fatura_import`, `cek_senet_import`, `tanim_import`.
   - Kart arama fonksiyonları da kopya: `_cari_id_bul` ×4, `_hizmet_id_bul` ×3,
     `_kasa_id_bul` ×2, `_banka_id_bul` ×2.
   - İnce farklar parametreyle birleştirilmeli: banka'nın `_banka_id_bul`'ında fazladan
     `hesap_turu` parametresi; `kasa_import` cursor yerine önceden kurulmuş map kullanıyor.
   - **Öneri:** `utils/import_helpers.py` altında topla (~300 satır erir).
2. **İşlem liste ekranları — yüksek kazanç / orta risk**
   - `modules/{kasa,banka,cari,fatura,cek_senet}/*_view.py` arası benzerlik:
     kasa↔banka ~%95 (356/377 benzersiz satır ortak), diğer ikililer %62–67.
   - Tekrar eden bloklar: fiş listeleme sorgusu (aynı `SELECT f.id, ... FROM fisler f` +
     WHERE kurulumu), `_satirlari_ekle`, `filtreleri_temizle`, `ornek_indir`, `veri_yukle` sarmalayıcısı.
   - **Öneri:** `FisListeMixin` taban sınıfı; kart filtresi ve `satir_filtreleri` hook olarak kalır.
     UI refactor — elle test gerektirir, import helper'larından sonra sıraya alınmalı.
3. **Ölü dosya temizliği**
   - `modules/raporlar/stok_raporu_view.py` hiçbir yerden import edilmiyor
     (canlı rapor: `stok_durum_raporu_view.py`; `__projev2.md` §2 notunda da geçiyor).
   - Kullanıcı onayıyla silinecek.
4. **Cüceler — düşük öncelik**
   - `SELECT deger FROM genel_tanimlar WHERE grup='Yillar' ORDER BY deger DESC` ×3
     (`__main__.py:83`, `ui/dialogs.py:969`, `yil_tanimlari_view.py:63`) → `yil_listesi_getir(cursor)` yardımcısı.
   - Stok kategori/birim lookup'ı (`SELECT deger, id FROM genel_tanimlar WHERE grup=?`) ×4
     (`tanimlar/stok_view.py` ×2 + `stok_durum_raporu_view.py`) → `genel_tanim_sozlugu(cursor, grup, firma_id)`.
   - `tanimlar/*_view.py` ailesi ~%50 yapısal benzerlik (form + liste + kaydet/sil iskeleti) —
     taban sınıf adayı ama işlem view'larına göre daha az kopya içeriyor; en sona bırakılabilir.

### Hesap Taşı (Hizmet Kartları) — bekleyen özellik
- **Amaç:** İşlem görmüş bir kartın türü kilitli olduğu için, kayıtları başka bir karta
  taşıma ihtiyacı doğabilir. (Ayrıca yanlış açılmış kart düzeltmek için de kullanılabilir.)
- **Girdi:** Hizmet Kartları listesinde ilgili satıra **sağ tık → "Hesap Taşı"**.
- **İşleyiş:**
  - Kullanıcı **Kaynak Hesap** (sağ tıklanan, sabit) ve **Hedef Hesap** seçer.
  - **Hedef hesap aynı türde olmalı** (Gider → Gider, Gelir → Gelir) — mizan dengesi korunur.
  - Opsiyonel **tarih aralığı**: "şu-şu tarihler arasındaki tüm hareketler şu hesaba taşınsın".
  - Onay sonrası `fis_satirlari.hesap_id` güncellenir (transaction içinde, tek seferde).
- **Dikkat:** Taşıma sonrası KDV otomatik satırları ve rapor tutarları yeniden gözden geçirilmeli;
  taşıma öncesi onay diyaloğunda taşınacak satır sayısı gösterilmeli.
- **Kapsam:** Önce hizmet kartları; istenirse stok/cari için de benzer mekanizma.

### Diğer
- İsteğe bağlı: "Kayıt Et" tıklanırken açık satır düzenlemesi varsa otomatik onayla
  (EditableTreeview odak kaybı bunu zaten sağlıyor — görsel teyit edilecek).
- İsteğe bağlı: Çek/Senet "Çek/Senet" kolonu için satır içi seçim (şu an sil + üstten ekle).

---

## 📘 Modül Geliştirme Şablonu (eski planv2.md)

Bu bölüm, v2 mimarisinde yeni bir modül geliştirirken izlenecek adımları ve dikkat
edilmesi gereken noktaları anlatır. "X modülünü geliştir" denildiğinde bu şablon
olduğu gibi takip edilmelidir.

### 1. Modül Geliştirme Şablonu (Örnek: Banka ve Cari Modüllerinden Çıkarılan Dersler)

#### Adım Adım Yeni Modül Oluşturma

1. **Klasör ve `__init__.py` Oluştur:**
   - `modules/[modul_adi]/__init__.py` (boş dosya)

2. **`[modul_adi]_view.py` Oluştur (Liste Ekranı):**
   - Sınıf: `[Modul]Modulu(tk.Frame)`
   - Yapı: Üst Butonlar + Filtre Alanı + Treeview Listesi + Durum Çubuğu
   - Sabit: `FIS_TURLERI = [...]` (modüle özel fiş türleri)
   - Metotlar:
     - `__init__(self, parent, main_app)` — `create_widgets()`, `_load_filter_data()`, `listele()` çağırır
     - `create_widgets()` — Yeni menüsü, Düzenle, Sil, Kaynağa Git butonları + filtre alanları + treeview
     - `_load_filter_data()` — Filtre combobox'ları için veritabanından verileri yükle
     - `listele()` — `fisler` JOIN `fis_satirlari` WHERE `hesap_turu='[Modul]'` sorgusu
     - `filtreleri_temizle()` — Filtreleri sıfırla, `listele()` çağır
     - `_ac_yeni_fis_formu(fis_turu)` — `self.pack_forget()` + form oluştur + `pack()`
     - `fis_duzenle()` — Seçili fişi form ile aç
     - `fis_sil()` — `fis_sil_service` ile sil, onay iste
     - `_get_selected_fis_kaynak_info()` — Seçili fişin `kaynak_modul` ve `kaynak_fis_id` bilgisini al
     - `_update_action_buttons_state()` — Kaynak modülü farklıysa Düzenle/Sil'i disable et, Kaynağa Git'i enable et
     - `_kaynaga_git()` — `main_app.go_to_module_and_select_fis()` çağır
     - `form_kapatildi()` — `form_instance = None` yap
     - `yenile()` — form açıksa formu yenile, değilse listele
     - `select_and_highlight_fis(fis_id)` — Filtreleri temizle, fişi treeview'de seç ve görünür yap

3. **`[modul_adi]_form.py` Oluştur (Fiş Formu) — EN KRİTİK DOSYA:**
   - Sınıf: `[Modul]FisiFormu(tk.Frame)`
   - `__init__(self, parent, main_app, view_container, fis_turu, fis_id=None, on_close=None)`:
     ```python
     self.create_widgets()
     self.verileri_yukle()
     self.ayarla_form_yapisi()
     # EN SON: self._setup_hesap_lookup()  (kasa_form.py'deki pattern)
     if self.fis_id:
         self.load_fis_data()
     ```
   - **create_widgets() içinde:**
     - Üst başlık alanı (Fiş Türü, Ana Hesap LookupWidget, Tarih, Fiş No, Açıklama)
     - Virman gibi özel fiş türleri için gizli alanlar (`lbl_hedef_...`, `lookup_hedef_...`, `lbl_virman_tutar`, `ent_virman_tutar`)
     - Excel tarzı giriş satırı (LookupWidget hesap, açıklama, miktar, birim_fiyat, kdv_oran, satır toplamı, "+" buton)
     - Treeview satır listesi (çift tık = düzenle, son sütun ❌ = sil)
     - Toplamlar alanı (Ara Toplam, Toplam KDV, Genel Toplam)
     - Alt butonlar (Kaydet, İptal ve Geri Dön)
   - **Kritik Metotlar:**
     - `_setup_hesap_lookup()` — StringVar trace + set patch + fokus davranışı (kasa_form.py'den birebir kopyala)
     - `_on_hesap_select()` — Hizmet kartı seçilince KDV'yi otomatik doldur
     - `verileri_yukle()` — hizmet kartları, kasa, banka, cari sözlüklerini yükle
     - `ayarla_form_yapisi()` — fis_turu'ne göre formu şekillendir (Gider/Tahsil/Virman dalları)
     - `toggle_hedef_alani(goster)` — Virman alanlarını göster/gizle
     - `yeni_kart_ekle()` — `ac_kart_dialog` çağır + verileri yenile + lookup'ları yeniden yapılandır
     - `hesapla_satir_toplami()`, `satir_ekle()`, `temizle_giris_satiri()`, `satir_sil()`, `satir_duzenle_icin_yukle()`, `guncelle_toplamlari()` — kasa_form.py'deki birebir aynısı
     - `fis_kaydet()` — `fis_kaydet`/`fis_guncelle` servislerini kullan, `kaynak_modul='[Modul]'`
     - `_olustur_fis_satirlari()` — modüle özel satır üretimi (borç/alacak yönleri)
     - `load_fis_data()` — Düzenleme modunda fişi forma yükle
     - `iptal()` — `self.pack_forget()` + `on_close()` + `view_container.pack()` (destroy DEĞİL!)
     - `yenile()` — `view_container.yenile()` çağır

4. **`main_window.py`'ye Bağla:**
   - Import: `from modules.[modul_adi].[modul_adi]_view import [Modul]Modulu`
   - Üst menüye ekle: `moduller_menu.add_command(label="[Modul]", command=lambda: self._modul_aci("[modul_key]"))`
   - `_modul_aci()` içine ekle:
     ```python
     elif modul_key == "[modul_key]":
         module_instance = [Modul]Modulu(tab_frame, self)
         module_instance.pack(fill="both", expand=True)
     ```
   - İkinci `_yeniden_yukle_aktif_modul` methodundaki `module_map` sözlüğüne ekle:
     ```python
     "[modul_key]": {
         "main_path": "modules.[modul_adi].[modul_adi]_view",
         "class_name": "[Modul]Modulu",
         "dependencies": [
             "modules.[modul_adi].[modul_adi]_form",
             "core.services",
             "utils.formatters",
             "ui.widgets.lookup_widget",
             "ui.dialogs",
             "ui.widgets.tooltip",
             "datetime"
         ]
     },
     ```
   - **Kritik:** main_window.py'de iki tane `_yeniden_yukle_aktif_modul` metodu var ve her ikisinde de `module_map` var. İkisine de eklemek gerekiyor.

5. **Doğrulama:**
   - `python -m py_compile modules/[modul_adi]/__init__.py modules/[modul_adi]/[modul_adi]_view.py modules/[modul_adi]/[modul_adi]_form.py ui/main_window.py`
   - Import testi: `python -c "from modules.[modul_adi].[modul_adi]_view import [Modul]Modulu; from modules.[modul_adi].[modul_adi]_form import [Modul]FisiFormu; print('OK')"`

### 2. Dikkat Edilmesi Gereken Genel Kurallar

1. **`iptal()` metodu:** `self.destroy()` KULLANMA. `pack_forget()` + `on_close()` + `view_container.pack()` kullan.
2. **Girinti hataları:** `main_window.py`'de değişiklik yaparken `elif` bloklarının girintilerine çok dikkat et. Aynı hata birden fazla kez yaşandı.
3. **`module_map` iki yerde var:** `_yeniden_yukle_aktif_modul` metodu iki kez tanımlanmış durumda (üstte ve altta). İkisine de modül ekle.
4. **`_setup_hesap_lookup()`:** Lookup widget'ları `verileri_yukle()` ve `ayarla_form_yapisi()`'ndan SONRA çağrılmalı.
5. **Dosya boyutu:** Form dosyaları büyük oluyor (~500+ satır). Tek seferde dosya oluşturmaya çalışma — önce gövdeyi oluştur, sonra parça parça düzenleme ile ekle.
6. **`ac_kart_dialog`:** Yeni kart ekleme için `ui/dialogs.py` kullan. `tablo_adi` parametresi 'cariler', 'stoklar', 'kasalar', 'banka_hesaplari', 'hizmet_kartlari' vb. olabilir.
7. **`LookupWidget`:** `configure_lookup(title, data_dict, on_new)` imzasını kullan. `data_dict` key=display adı, value=id olacak şekilde.
8. **CurrencyFormatter:** `ent_miktar`, `ent_birim_fiyat`, `ent_kdv_oran`, `ent_virman_tutar` gibi alanlara uygula. `on_change_callback` ile anında toplam hesaplama yap.
9. **Kaynak Takibi:** Tüm kayıtlarda `kaynak_modul` ve `kaynak_fis_id` alanlarını doldur. Fatura'dan kasa fişi oluşturulduğunda `kaynak_modul='Fatura'` olmalı.
10. **Virman formları:** Satır listesi gizlenir (`self.liste_frame.pack_forget()`), yerine hedef hesap + tutar alanları gösterilir.
