# Ön Muhasebe v2 — Bağımsız İnceleme Raporu (Uzman Görüşü)

> Tarih: 2026-09-03
> Kapsam: Tüm kod tabanı (~20.000 satır) — çekirdek katman, fiş formları, raporlar, widget'lar, import/export.
> Metodoloji: 4 paralel derinlemesine kod incelemesi; kritik bulgular (fatura KDV çarpanması, export bozulması, FIFO) kod tekrar okunarak ve canlı DB kontrolüyle doğrulandı.
> Kullanım: Bulgular aşağıda öncelik sırasındadır; üzerinden tek tek geçildikçe durum işaretlenir.

**Durum işaretleme:** ⬜ Bekliyor · 🔧 Yapılıyor · ✅ Düzeltildi · ❓ Tartışılacak (tasarım tercihi olabilir)

---

## Özet Karar

Uygulamanın **mimari omurgası sağlam**: tek merkezi fiş servisi, tutarlı firma/yıl kapsamlı listeler, ISO tarih formatı, import'ta satır-satır hata raporlama ve all-or-nothing transaction, her yerde export. "Kendi gözümüzden eksiği yok" hissi anlaşılır — günlük happy-path çalışıyor.

**Ama üç gerçek sorun var:**

1. **Veri bozan mantık hataları mevcut** — en önemlisi: KDV'li bir faturayı açıp sadece "Kaydet" demek muhasebeyi sessizce bozuyor. Bu bir UX eksikliği değil, aktif veri kaybı.
2. **Muhasebe güvenliği yanlış katta**: borç=alacak dengesi sadece bir formda, UI'da kontrol ediliyor; veri katmanında hiç kontrol yok.
3. **Excel export'u tarih sütunlarını bozuyor** — dışa aktarılan raporlar Excel'de yanlış görünüyor.

---

## 🔴 KRİTİK — Düzeltmezseniz veri sessizce bozulur

### K1. ✅ Fatura düzenleyip kaydetmek, satırları KDV kadar şişiriyor *(kod okumasıyla doğrulandı; DB taramasıyla teyit edildi)*
- **Konum:** `modules/fatura/fatura_form.py:526-531` (oluşturma: satır **net** `ara_toplam`) ↔ `:883-884` (düzenleme-yükleme: satır **brüt** `toplam_tutar` ile yüklenir)
- Kayıtta satırlar `self.satirlar`'dan olduğu gibi DB'ye gider (satır 743), KDV satırı ayrıca üretilir (748-760).
- **Sonuç:** KDV'li bir faturayı açıp hiç değiştirmeden kaydetmek stok/masraf satırını brütleştirir → fiş bir KDV tutarı kadar dengesizleşir, maliyet raporları KDV kadar şişer. `fis_guncelle` satırları sil-yeniden-yazdığı için (`core/services.py:111`) bozulma **kalıcı**; ikinci düzenlemede katlanabilir.
- **Tüm rapordaki en tehlikeli bulgu.**
- **Düzeltme (2026-09-03):** `fatura_form.py:884` edit-yükleme artık `ara_toplam` (net) kullanıyor — oluşturma ile aynı semantik. DB taraması: cari karşılıklı 270 faturadan yalnızca test fişi id=7525 etkilenmişti; **geçmiş veri hasarı yok**. (id=7525 hâlâ bozuk — silinecek test fişi ya da tek UPDATE ile düzeltilir.)

### K2. ✅ Borç = Alacak kontrolü veri katmanında hiç yok
- **Konum:** `core/services.py:29` (`fis_kaydet`) ve `:89` (`fis_guncelle`)
- Tek kontrol `modules/cari/cari_form.py:594`'te, float toleranslı (±0.005). Kasa/banka/fatura/çek formlarında dengeyi zorlayan her hata (K1, K3) sessizce deftere yazılır → mizan ve bakiyelerde drift, fark edilmez.
- *(İki bağımsız inceleme aynı sonuca ulaştı — güven yüksek.)*
- **Düzeltme (2026-09-03):** `core/services.py:29` `_denge_kontrolu` eklendi; `fis_kaydet:53` ve `fis_guncelle:115`'te **hiçbir yazım/silme yapılmadan önce** çağrılıyor. Kapsam bilinçli: **yalnız `hesap_turu='Cari'` satırı içeren fişler** denetlenir; cari-karşılıksız fişler (peşin tahsilat/ödeme, virman, açılış) tasarım gereği tek taraflı olduğundan dışarıda → **C17 bu assert'in ön koşusu olmaktan çıktı** (bkz. C17 notu). Tolerans 0,01 TL.
- **Canlı DB doğrulaması:** 6686 fişten 347'si Cari satırlı → **346'sı geçiyor (sıfır regresyon)**, 3'ü 0,001–0,01 kuruş farkıyla tolerans sayesinde geçiyor (0,005/sıfır tolerans bunları yanlışlıkla reddederdi). **Tek tetikleyen id=7525** = K1'in bilinen bozuk test fişi (fark +100 TL, tam KDV kadar) → guard bozulmayı doğru yakalıyor. Kalan 6339 tek-taraflı fiş otomatik kontrol dışı.
- **Not:** assert aktifleşince **K3 kullanıcıya jenerik "Fiş dengeli değil" hatası olarak patlar** (191/391 kartı eksikse KDV satırı atlanır → dengesiz). Bu yüzden K3 artık K2'nin doğal devamıdır — eyleme dönük net mesaj şart.

### K3. ✅ 191/391 kartları eksikse KDV'li fiş dengesiz kaydediliyor
- **Konum:** `modules/kasa/kasa_form.py:772-798` (kartlar `:373-381`'den yüklenir, `durum=0`/yoksa None)
- KDV karşılık satırı sadece `if kdv_hesap_id:` ile ekleniyor; kasa satırı brüt yazılıyor, KDV satırı yok → borç ≠ alacak, uyarısız. `fatura_form.py:758`'de de aynı atlama (`kdv_satiri_olustur` None dönerse).
- **Düzeltme (2026-09-03):** Üç fiş formunda kart eksikse artık **sessiz atlamak yerine net hata + kayıt engeli** (messagebox + return): `fatura_form.py` (KDV satırı üretiminde), `kasa_form.py` (gider/gelir KDV satırında), ve aşağıdaki banka kardeşi.
- **Yeni bulunan kardeş hata — `banka_form.py`:** Banka Gider/Gelir fişlerinde KDV karşılık satırı **hiç üretilmiyordu** (hizmet NET, banka GROSS) → satırda KDV varsa fiş daima dengesizdi; Cari satırı olmadığı için K2 assert'i de bunu yakalamıyordu. Kasa'daki KDV-satırı deseni + KDV kart-id yüklemesi banka'ya eklendi; kart eksikse net hata. (Q1 "kasa↔banka kopya" borcunun canlı bir örneği — kalıcı çözüm taban sınıfta, bkz. Q1.)

### K4. ✅ Excel export tarih ve noktalı sayıları bozuyor *(kod okumasıyla doğrulandı)*
- **Konum:** `utils/export.py:102-115` (`_parse_numeric_value`)
- Her `.` binlik ayraç sayılıyor: `"03.09.2026"` → `3092026.0`, `"2.50"` → `250.0`. Tarih sütunu olan her Excel export'u bozuk veri üretir.
- **PDF:** tablo hep A4 **portre** (`export.py:52` — landscape import edilmiş ama kullanılmıyor), 11 sütunlu raporlar okunaksız.
- **Ek:** pandas yoksa `export.py:149`'daki `pd.DataFrame` guard'dan önce AttributeError atıyor.
- **Düzeltme (2026-09-03) — üç iş birlikte:**
  1. `_parse_numeric_value` yeniden yazıldı: tarih biçimli diziler (`gg.aa.yyyy`, `yyyy-mm-dd`, `gg/aa/yyyy`) artık **metin** kalıyor; noktayı-binlik varsayımı yalnızca Türkçe para/miktar desenine (`^\d{1,3}(\.\d{3})*(,\d+)?$`, ondalık `,`) uygulanıyor; düz ondalık (`2.50`) doğru çevriliyor; sayı olmayan her şey metin olarak korunuyor. Format kaynakları `utils/formatters.py`'dan teyit edildi (para `1.234,56`, miktar `1.234,5`, tarih `format_date`→`gg.aa.yyyy`).
  2. PDF orientasyonu: sütun sayısı > 6 ise **landscape(A4)**, değilse portre; sayfa genişliği hesabı seçilen orientasyona bağlandı (`page[0]-60`).
  3. `export_treeview_data` girişine `if not pd` guard'ı eklendi → AttributeError yerine net "pandas gerekli" uyarısı.
- **Doğrulama:** `_parse_numeric_value` saf fonksiyon — 18 girdilik davranış testi (tarihler, `2.50`, `1.234,56`, `23.456.789`, miktar, TL soneki, `%20`/boş/metin) **18/18 geçti**; `py_compile` temiz. (PDF/görsel çıktı kullanıcı testine bırakıldı.)

### K5. ❓ FIFO: stoktan fazla çıkışta maliyet = 0 TL — **KARAR GEREKİYOR (bu turda uygulanmadı)**
- **Konum:** `core/services.py:444-456` (`_fifo_tuket`) + aynı mantık `modules/raporlar/hesap_ekstresi_view.py:366-378`, `modules/raporlar/satis_raporu_view.py:425-437`
- Girişten önce satış serbest (kayıt yolunda bakiye kontrolü yok); katmanı yetmeyen kısım **0 maliyetle** geçiyor.
- **Örnek:** 10@200 satış (giriş yok), sonra 10@50 alış → Kârlılık 2.000 TL kâr gösterir (gerçeği 1.500 TL, marj %100'e şişer); ekstrede miktar-fiyat kalıcı senkron bozulur (Kalan Miktar 0, Kalan Maliyet 500 TL).
- **Neden bu turda bırakıldı:** Üç ayrı FIFO motoru (C5) tek gerçeğe indirgemeyi, aşırı-çıkış politikasını (engelle/uyar/son-maliyetle-fiyatla) ve iade katmanının maliyetle-dönüşünü (C4) içeriyor; hepsi muhasebe politikası kararı + rapor rakamlarında geniş regresyon yüzeyi. Yanlış tahmin, mevcut bilinen hatadan daha kötü görünmez bir hataya yol açar. Kullanıcı kararıyla ele alınacak (aşağıda seçenekler).
- **Karar seçenekleri:** (A) kayıtta **negatif stok engeli** (satış/fire, girişi geçemez) — en güvenli ama önceki serbest akışı bozar; (B) **uyar + izin ver**, eksik katmanı **son bilinen alış maliyetiyle** fiyatla (0 yerine) — esnek, tahmini maliyet; (C) sadece **uyar**, maliyet 0 kalsın ama kullanıcı görsün. Öneri: stok takibi yapan firma için A + raporlarda B yedeği.

### K6. ✅ Çek/Senet "güncel durum" fiş ID'siyle (`MAX(id)`) takip ediliyor, tarihle değil
- **Konum:** `modules/raporlar/cek_senet_portfoy_raporu_view.py:104-111`, `cek_senet_vade_raporu_view.py:81-88`, `cek_senet_seruven_raporu_view.py:98`
- Eski tarihli bir fişi düzenleyip kaydetmek hareketi yeni (büyük) id ile yeniden yazıyor (`modules/cek_senet/cek_senet_form.py:1121-1123, 1143-1155`) → tahsil edilmiş çek, eski giriş fişini düzenleyince portfoyde tekrar "Portföyde" görünür; Serüven tarihi sırasız basar.
- **Düzeltme (2026-09-03):** "son/güncel hareket" seçimi **işlem tarihine** göre yapıldı — 6 yer: `services.py` `cek_senet_guncel_durum` ve `cek_senet_son_banka_takas` (`ORDER BY islem_tarihi DESC, id DESC`), `cek_senet_fis_son_hareket_mi` (alt-sorgu `MAX(id)` → tarih+id LIMIT 1); portfoy ve vade raporlarındaki satır-içi `MAX(h2.id)` alt-sorguları → `ORDER BY h2.islem_tarihi DESC, h2.id DESC LIMIT 1`; serüven `ORDER BY h.id` → `ORDER BY h.islem_tarihi, h.id`. (`islem_tarihi` fiş tarihinden yazılıyor — `cek_senet_form.py:1148` — bu yüzden sıralama doğru çalışır.)
- **Doğrulama:** 4 dosya `py_compile` temiz; canlı DB'de eski-vs-yeni durum seçimini karşılaştıran sorgu hatasız çalıştı. **Ancak tabloda hareket kaydı yok (0)** → etki veri üzerinde gözlenemedi; bir çek/senet girişiyle test edilmeli.

---

## 🟠 CİDDİ — Mantık tutarsızlıkları

### C1. ❓ Peşin/nakit fatura satışları cari bakiyeye hiç yansımıyor
- `modules/fatura/fatura_form.py:763-785` (cari karşılık sadece Vadeli'de) → `modules/raporlar/cari_bakiye_raporu_view.py:107-110`
- Raporlar sadece `hesap_turu='Cari'` satırlardan türetiyor; nakit/Banka/POS satışında Cari satırı yok → cari ekstrede görünmez. Tasarım tercihi olabilir ama kullanıcı "ekstresi eksik" olarak yaşar.

### C2. ⬜ Alış iadeleri Satış Raporu'nda COGS'a giriyor
- `modules/raporlar/satis_raporu_view.py:417-422` (`_cogs_hesapla` ay içindeki **tüm** `alacak>0` stok satırlarını maliyetliyor)
- Tedarikçiye iade "maliyet" yazılır: 10@10 al, 4 iade et, hiçbir satış yok → "Maliyet 40 TL". Aynı ayın Kârlılık raporu (`services.py:412` — sadece STOK_SATIS_TURU) farklı rakam verir → iki rapor çelişir.

### C3. ⬜ İade faturalarında KDV yanlış hesapta
- `modules/fatura/fatura_form.py:751-756` → `modules/raporlar/kdv_raporu_view.py:171-176`
- Kural "KDV satır yönünü takip eder (borç→191, alacak→391)": Satış İade **191'e borç** yazıyor (391'den düşmeli), Alış İade **391'e alacak**. "Ödenecek (391−191)" net doğru çıkar ama KDV2 mantığındaki 191/391 dağılımı yanlış.

### C4. ⬜ Satış iadesi FIFO'ya yeni katman gibi SATIŞ fiyatıyla giriyor
- `core/services.py:303, 434`; `modules/raporlar/hesap_ekstresi_view.py:291-294, 319-326`
- Her maliyet rutini borç stok satırını alış katmanı sayıyor. 80'e alınan mal 120'ye satılıp iade edilirse stok 120 ile değerlenir (+40TL hayalet), sonraki satış 120 katmanını tüketir → marj 40TL/adi eksik hesaplanır.

### C5. ⬜ Üç ayrı FIFO implementasyonu birbirinden sapıyor
- `core/services.py:298-312` (`stok_bakiye_ve_maliyet`, "en yeni alışlarla refill"), `core/services.py:412-441` (`stok_donem_cogs`, kronolojik replay), `modules/raporlar/hesap_ekstresi_view.py:282-333` (replay kopyası)
- Oversell ve iade yoksa anlaşıyorlar; varsa Stok Durum ≠ Stok Ekstresi ≠ Kârlılık (aynı DB'de). K5 üçünden ikisini etkiliyor.

### C6. ⬜ Tüm form düzenleme-yüklemeleri ham id ile, `firma_id` filtresiz
- `kasa_form.py:830,845`; `banka_form.py:790,805`; `cari_form.py:666,676-679`; `fatura_form.py:839,897,905`; `cek_senet_form.py:1176,1189,1193,1215`; `acilis_form.py:442,452-455`; `kasa_view.py:453`
- Bugün listeler kapsamlı olduğu için ulaşılamaz, ama tek bozuk id ile çapraz-firma fiş okuma kapısı. `fatura_form.py:861-865` ayrıca `stoklar/hizmet_kartlari` JOIN'inde firma filtresiz (id çakışması yanlış firmaya bağlar) ve INNER JOIN, durum=0 (silinmiş) stoğu olan satırları sessiz düşürür → sil-yaz'da kaybolur.
- `core/services.py:111` — satır silme kapsamsız, başlık UPDATE'i (`:105`) firma istiyor: uyumsuzlukta satırlar gider, başlık durur (kısmi düzenleme, `rowcount` kontrolü yok — `services.py:101-111`).
- `services.py:126,129` (`kaynak_fis_id` SELECT/DELETE) ve `:512-533` (çek/senet durum yardımcıları) firma'sız — global tekil id ile zararsız ama savunmasız desen.
- `modules/cek_senet/cek_senet_form.py:1083-1101` — `UPDATE cekler_senetler ... WHERE id=?` firma korumasız.

### C7. ⬜ Fiş no tekilliği DB'de garanti değil
- `core/services.py:5-26` check-then-act; `db.py:136-153`'te `UNIQUE(fis_no, firma_id, yil)` yok. Bağlantı işlem-başına, lock yok → eşzamanlı iki kayıt aynı no'yu geçirebilir.
- Benzer: `genel_tanimlar`'daki `INSERT OR IGNORE` (`db.py:235`) `Ana Firma (Varsayılan)` adında gerçek bir firma tanımlanırsa UNIQUE'e çarparak startup'ı bozar.

### C8. ⬜ Kasa Virman aynı-kasa kontrolü yok
- `modules/kasa/kasa_form.py:711-757` — `banka_form.py:632-634` bloke ediyor, kasa'da yok (kopyadan düşmüş). Kasa X→X virmanı kayıt olur, giriş/çıkış toplamlarını şişirir.
- **Fire fişi:** `modules/fatura/fatura_fire_form.py:235, 393` — stok düşüm/bakiye kontrolü yok, negatif stoğa düşürür; toplamlar ham float `miktar*birim_fiyat` (kdv_hesapla rounding'i atlıyor).

### C9. ⬜ `seri_no` global UNIQUE, firma-bazlı değil
- `core/db.py:180` + `cek_senet_form.py:1061-1078` — ikinci firma aynı çek seri no'sunu kullanınca ham IntegrityError, jenerik "Veritabanı Hatası" (`:1165`) olarak kullanıcıya çıkıyor; önden kontrol yok.

### C10. ⬜ Çek/Senet cari raporu ters yönleri topluyor
- `modules/raporlar/cek_senet_cari_raporu_view.py:66-68, 106` — cari bazlı özet tüm hareketleri topluyor (güncel durum değil) ve Toplam sütunu Giriş+Çıkış gibi zıt yönleri artırıyor: 1.000 TL çek al + iade et → "Toplam 2.000 TL" net-sıfır pozisyon.

### C11. ⬜ Vade raporu durum filtresiz gelirse tahsil edilmiş çek "Vadesi Geçmiş"e giriyor
- `modules/raporlar/cek_senet_vade_raporu_view.py:24-27, 104-121` — varsayılan Durum=Tümü; nakit planlama rakamı filtre keşfedilene kadar yanlış, tabloda uyarı yok.

### C12. ⬜ Çek/Senet edit state-machine boşlukları
- `modules/cek_senet/cek_senet_form.py:701-715, 722-723, 827, 873, 1013` — yeni "Portföyde" çek mevcut Ciro/Banka-tahsil fişine eklenemiyor (doğru) ama Tahsil editi `tahsil_onceki_durum`'u sessiz devralıyor; `_satir_ekle_mevcut` mükerrer satır engeli yok (aynı çek iki kez eklenir → çift hareket); vade tarihi geçmiş olabilir, kontrol yok.

### C13. ⬜ `parse_currency` her `.`'i binlik ayraç sayıyor
- `utils/formatters.py:36-48` — "12.5" → 125.0. Odak-çıkışı (`:160`) ve inline hücre (`editable_treeview.py:332`) üzerinden noktalı ondalık yazan kullanıcı 10×/100× kayıt yapar, sessizce. Geçersiz metin → 0.0, mesaj yok.
- `:66` biçimindeki kodlama miktarları `int(float(...))` ile kesiyor (ondalıklı miktar kaybolur).

### C14. ⬜ Ölü validasyon + kırılgan geri-yükleme (cari/fatura)
- `modules/cari/cari_form.py:638-643` — ödemenin nakit-kaynağıyla çakışma kontrolü `s['hesap_turu']`'nun hep "Cari" olduğu döngüde "Kasa/Banka"ya bakıyor → asla tetiklenmez; yazar korunduğunu sanıyor.
- `modules/fatura/fatura_form.py:901-906` — ödeme tipi etiketteki "(Nakit)" string-split ile geri alınıyor (etiket değişirse edit bozulur); `:906` `fetchone()[0]` satırsız fişte TypeError. `:493` — alışta `int()` ondalıklı KDV oranını kesiyor (edit-yükleme float tutuyor → bir daha sapma). `:508` — `stok_dict[...]['birim']` KeyError riski (fire formu `.get()` kullanıyor).
- `modules/kasa/kasa_form.py:863-864` (+banka ikizi) — edit-yükleme `hesap_id`'si KDV kartıyla eşleşen elle eklenmiş satırları düşürüyor → kaybolur.

### C15. ⬜ Para baştan sona REAL/float
- Şema: `db.py:147,167-168,185,37-39,78,103`; hesaplama: `formatters.py:23,46,89-93`; toplama: `services.py:296,306,311,373,435,446-456`
- `kdv_hesapla` Decimal/ROUND_HALF_UP ile hesaplayıp `float()` dönüyor. Satır bazında yuvarlama iyi; binlerce float satır toplamı kuruş sürüklenmesi üretebilir → "Decimal + ROUND_HALF_UP" hedefinden sapma. (Import'taki `float(deger)` de aynı zincire giriyor; `Decimal(str(...))` çoğunu maskeliyor.)
- Import Excel **serial-date** (ör. `45000.0`) dönüşümü yok (`*_import.py` `_tarih` fonksiyonları) → sayısal tarihli hücreler "Tarih geçersiz" hatasıyla reddedilir (tarih-formatlı hücreler sorunsuz).

### C16. ⬜ Yıl kutusu firma-süzgücsüz
- `__main__.py:79` — `SELECT DISTINCT yil FROM fisler` `firma_id` filtresiz → B firmasının yılları A'nın listesinde. `:92-93` `except Exception: pass` hata halinde listeyi sessizce eksik bırakıyor.

### C17. ⬜ Açılış fişleri karşıt satırsız (tek taraflı)
- `modules/acilis/acilis_form.py:17-19` — "karşı satır oluşturulmaz". Küresel mizan bu yüzden hiç dengeleyemez.
- *(2026-09-03) K2 bağlamında:* `_denge_kontrolu` yalnız **Cari satırlı** fişleri denetlediği için açılış fişleri (590/karşılıksız, Cari satırı yok) **otomatik kontrol dışı** → assert'i bloklamıyor. **Ancak C17'nin kendisi çözülmedi**: küresel mizan hâlâ açılış yüzünden dengeleyemez. Bu, ayrı bir muhasebe-modeli kararı olarak duruyor (590 karşıt satır modeli mi, yoksa açılışları Mizan'dan hariç mi).

### C18. ⬜ `fis_sil` → `cek_senet_hareketleri` yetim kayıtları
- `core/services.py:154-180` hareket tablosunu temizlemiyor (FK/cascade yok); sadece `cek_senet_fis_sil` (`:588`) siliyor. Çek/senet fişi genel silme yolundan silinirse sarkan `fis_id` → `cek_senet_fis_son_hareket_mi:536` ve durum sorguları bozulur.

### C19. ⬜ Şemada sıcak yollarda index yok
- `db.py:136-173, 217-223` — `fis_satirlari(fis_id)` (her silme/güncelleme ve CASCADE bu FK'yı kullanıyor), `fisler(firma_id,yil)`, `fisler(fis_no)`, `fisler(kaynak_fis_id)` index'leri yok; `firma_id`'de FK/CHECK yok. Büyük veritabanında ilk yavaşlık burada çıkar.

### C20. ⬜ `kaydet_kart` dinamik kolon SQL'i
- `core/services.py:257-259, 268-271` — tablo adı whitelist'li ama `SET {columns}` parçaları dict **key**'lerinden f-string ile kuruluyor (değerler parametreli → metin-alan enjeksiyonu değil, ama kırılgan desen).
- `:265` — `stok_adi.lower()` Türkçe İ/I için yanlış slug üretir.

---

## 🟡 UX — Muhasebecinin her gün hissedeceği eksikler

### U1. ⬜ "Kaydet ve Yeni Fiş" akışı yok
- Her kayıt formları kapatıp listeye döndürüyor (`kasa_form.py:813-815`; `fatura_form.py:827` `self.kapat()`). N fiş = N × (formu yeniden aç + kasa/hesap seç + tarih ayarla). **Günlük kullanımda en yüksek frekanslı sürtünme.**

### U2. ⬜ Kaydedilmemiş değişiklik koruması yok
- `ui/main_window.py:319-336` (`_tab_kapat`), `:410-412` (`cikis_onayla` formdan habersiz), `:150-154` (firma/yıl değişimi tüm sekmeleri sessiz kapatır); formlarda `iptal()`/çarpı ile uyarısız diskart (`kasa_form.py:905-910`, 7 formda aynı).
- `ui/widgets/editable_treeview.py:341-343` — geçersiz hücre mesaj vermmeden sessizce geri alınıyor.

### U3. ⬜ Klavye akışı yok
- `ui/dialogs.py`, `main_window.py`, `lookup_widget.py`'de `<Return>`=Kaydet / `<Escape>`=İptal binding'i yok; `LookupDialog` (`:61`) yalnız çift-tık/buton ile seçtirir; menülerde accelerator yok (F5 hariç). (Good: `EditableTreeview`'da Enter→sonraki hücre ve CurrencyFormatter zinciri var.)

### U4. ⬜ Büyük import/export'ta pencere donuyor, ilerleme göstergesi yok
- Import baştan sona senkron ana thread'de (`kasa_view.py:308-375`); `ui/widgets/pagination.py:143-146` export için tüm sayfaları tek tek dolaşıyor. Kod tabanında `Progressbar` hiç yok (grep doğrulandı).

### U5. ⬜ Lookup arama her tuşta komple yeniden kuruyor
- `ui/widgets/lookup_widget.py:41, 106-116` — binlerce caride gecikir. `advanced_treeview.py:168-171`'deki 400 ms debounce deseni buraya uygulanmalı.

### U6. ⬜ Rapor sekmeleri bayat yenileme (kırık zincir)
- `modules/raporlar/raporlar_view.py:93-94` — `RaporlarModulu.yenile()` gövdesi `pass`; `main_window.py:308-310` yalnız modül-genelini çağırıyor → her alt-görünümün `yenile()`'i (kategori listesi, KDV hesap id'leri, `stok_rapor_tabani.py:50,55`'te widget oluşturmada `aktif_yil`'e sabitlenen tarih varsayılanları) firma/yıl değişince yenilenmez. (Good: filtreler sekmeler arası korunuyor.)

### U7. ⬜ Üretim uygulamasında F5 hot-reload
- `ui/main_window.py:44, 368-408` — `importlib.reload` ile modül yeniden yükleme; yanlış F5 gelişmekte olan fişi/sekme durumunu bozabilir. Dev aracı, pakette kapatılmalı.

### U8. ⬜ Performans — tuş başına tam yeniden sorgu
- `modules/kasa/kasa_view.py:139` (arama her KeyRelease'te SQLite), `cek_senet_portfoy_raporu_view.py:37`, `cek_senet_cari_raporu_view.py:23` (tuş başına tam sorgu + treeview rebuild).
- `modules/raporlar/satis_raporu_view.py:357-374, 404-423` — Yıllık görünüm 12 ardışık `_cogs_hesapla`, her biri o ay-sonuna kadar **tüm** stok hareketlerini baştan replay (~78× gereksiz iş; sekmeye her dönüşte önbelleksiz tekrar).

### U9. ⬜ Çek/Senet edit'te konsola düşen sessiz hatalar
- `cek_senet_form.py:925, 962` — durum aramaları DB try-bloğu dışında; KeyError konsola basıyor, UI donmuş gibi görünüyor. `kasa_form.py:356-357` benzeri `print()`.

### U10. ⬜ Küçük UX
- Sütun genişlikleri hatırlanmıyor (her açılışta reset).
- Boş raporlarda "kayıt yok" ipucu yok (Portföy/Vade/Serüven/Hiç-Satan boş ağaç basıyor).
- `cari_form.py:486-494` — normal fişte borç=alacak=toplam gösterimi yanıltıcı.
- `ui/widgets/tooltip.py:9-12` — tooltip gecikmesiz, her `<Enter>`'da anında patlıyor.
- Banka import hata verirse üzerine ikinci hata: `ui/import_preview.py:527-539` — except bloğu bağlanmamış `sonuc`'a bakıyor (NameError). (Kopya-yapıştıktan doğan somut bug.)
- `ui/dialogs.py:753-757` — StokDialog otomatik kategori/birim oluşturmanın `except`'i hatayı yutuyor, kayıt ayrı transaction'da devam ediyor (yarı-atomik, sessiz kayıp).
- `ui/dialogs.py:12,43` — `ac_kart_dialog`/`BaseDialog` varsayılanı `firma_id=1` (çok firmalı tuzak).

---

## 🔵 Kod Kalitesi (yapısal)

| # | Durum | Bulgu | Konum |
|---|-------|-------|-------|
| Q1 | ⬜ | kasa_form ↔ banka_form ~653 birebir satır (similarity 0.72; cari↔acilis 0.50, kasa↔acilis 0.36, fatura↔fire 0.31). C8'deki eksik kontrol tam bu fork'un maliyeti. Ortak taban fiş-form sınıfı (Taslaktaki RefactoringBacklog ile örtüşüyor) bunu ve K3/C14'ün bir sınıfını kalıcı kılar. | `modules/kasa/kasa_form.py`, `modules/banka/banka_form.py` |
| Q2 | ⬜ | 6 import dosyasında `_metin/_sayi/_tarih` helper'ları 6'şar kere kopya; 5 preview dialog `import_preview.py`'da yapısal aynı ~90 satır (K4-banka-NameError bunun semptomu). | `modules/*/*_import.py`, `ui/import_preview.py` |
| Q3 | ⬜ | `kaydet` ~470 satırlık state-machine (çek/senet); formlarda 150+ satırlık `kaydet`/`load_fis_data`. UI dosyalarından doğrudan SQL (lookup ve fiş yükleme `services`'ı baypas ediyor; yazma yolu `fis_kaydet/guncelle`'den geçiyor). | `cek_senet_form.py` vb. |
| Q4 | ⬜ | Kırılgan widget deseni: `kasa_form.py:252-282` (+banka kopyası) `lookup.set` monkey-patch, StringVar trace + `after(50)/after(300)` polling, her `yeni_kart_ekle` çağrısında binding birikiyor. `cek_senet_form.py:785-795, 1104-1107` — hesap_id'yi yer-tutucu-0 hilesiyle, dict/list sırasının eşit varsayıldığı atama. | |
| Q5 | ⬜ | `main_window._modul_aci` 10 dallı if/elif merdiveni (`:166-194`), F5 yolundaki `module_map`'ı (`:377-387`) tekrarlıyor → kayıt tablosuna dönüşmeli. | |
| Q6 | ⬜ | Ölü kod: `modules/raporlar/stok_raporu_view.py` (hiçbir yerden referans yok — düzeltmelerin yanlış kopyaya düşmesini engellemek için sil); `services.py:1` kullanılmayan `import sqlite3`; `services.py:412,439` yanıltıcı/etkisiz parametreler; `fis_kaydet` id döner, `fis_guncelle` dönmez. | |
| Q7 | ⬜ | `ui/widgets/editable_treeview.py:274-276, 285-287` — `_on_escape` iki kez tanımlı (ikinci gölgeleme). `lookup_widget.py:113` — iid olarak ham id (yer yer `str(i_id)` ile tutarsız). | |
| Q8 | ⬜ | Bağlantı deseni: `sqlite3.connect(DB_YOLU)` işlem-başına (`core/db.py:11`), WAL/`timeout` yok — tek-thread GUI'de sorun değil ama arka plan işi + eşzamanlı yazıcı eklenirse "created in another thread" / "database is locked" ile ilk çarpan yer olur. | |
| Q9 | ⬜ | `yenile()` sözleşmesi formlar arası farklı (kasa/banka sözlükleri yeniden yükler; cari `:766-769`, çek/senet `:1335-1337`, acilis `:494-496` `view_container.listele()` çağırır) → yeni kart bir forma giriyor, diğerine girmiyor. | |

---

## ✅ Doğru Olan Şeyler (raporun şeffaf kısmı — bunları bozmayın)

- **Tarihler her yerde sıfır dolgulu ISO `YYYY-MM-DD`** → rapor sorgularında sözlüksel karşılaştırma tuzağı **yok** (canlı DB'de tüm satırlar length=10 olarak doğrulandı).
- **Silme = hard delete + FK cascade gerçekten aktif** (`PRAGMA foreign_keys=ON`, `db.py:15`) → raporlarda silinmiş fiş hayaleti yok; `fis_sil/fis_guncelle`'de satırlar açıkça da siliniyor (belt-and-braces).
- **Import'lar sınıftan iyi:** satır-satır `Satır N:` hatalı kırmızı panel, hata varken buton kilitli (all-or-nothing), tek commit/rollback, firma_id sızdırmasız, yıl satırın fiş tarihinden türetilip uyarı veriliyor.
- **Maliyet/satış tabanları KDV hariç** (net satır + ayrı 191/391 satırı, `fatura_form.py:525-531, 745-760`) — doğru model (KDV2 hesabı hariç, o C3).
- **SQL tamamen parametreli** — enjeksiyon bulgusu yok; `STOK_*` sabitlerinin f-string'i module constant (zararsız).
- **Listeler firma+yıl kapsamlı** ve yıl-klempli tarih aralıklarıyla (`kasa_view.py:210-220` ve ikizleri); kayıtlar aktif firma/yıl'ı basıyor.
- Doğru yönlendirme: kasa/banka/cari/fatura'da 4 satış/alış/iade kombinasyonunun borç/alacak yönleri doğrulandı; virman satır eşleştirmesi tutarlı; negatif/sıfır tutar girişte engelli.
- Silme-onay'ları her yerde var; dış `kaynak_modul` fişleri düzenlemeye kapalı "Kaynağa Git" affordance'ı iyi fikir; çek/senet silmede "son hareket değilse silinemez" kuralı var.
- `pagination.py` ve `advanced_treeview.py`'da sıralama SQL-tarafında — sayı/tarih "10 < 9" metin-sıralama tuzağı yok; `stok_rapor_tabani.py` ortak taban + tembel sekmeler iyi desen.
- `acilis_form.py` gerçekten iyi parametreze paylaşımlı form.

---

## Önerilen Öncelik Sırası (tek-tek geçiş planı)

| Önce | Madde | Neden bu sırada |
|-------|-------|-----------------|
| 1 | ✅ **K1** — fatura edit-load'u `ara_toplam`'a (`fatura_form.py:884`) | Tek satırlık düzeltme; aktif veri yozlaşmasını durdurdu. Geçmiş tarama: yalnız id=7525 bozuk (test fişi). |
| 2 | ✅ **K2** — `fis_kaydet/fis_guncelle`'e borç=alacak assert'i (`services.py:29`) | Veri-katmanı güvencesi eklendi; kapsam="yalnız Cari satırlı fiş" → C17'yi beklemeye gerek kalmadı. Canlı DB'de 346/347 geçti (0 regresyon). **C17 (açılış 590 modeli) ayrı karar olarak duruyor.** |
| 2b | ⬜ **K3** — assert aktifleşti, artık 191/391 kartı eksikse net "KDV kartı tanımlı değil" hatası şart | K2'nin doğal devamı (aşağıda kenetli). |
| 3 | ✅ **K4** — `export.py` `_parse_numeric_value` (tarih/sayı) + PDF landscape + pandas guard | 18/18 davranış testi; `py_compile` temiz. |
| 4 | ❓ **K5 + C8 fire + C4** — stok bakiye kontrolü / FIFO eksik katman / iade maliyeti | **KARAR GEREKİYOR** (K5 bloğundaki A/B/C seçenekleri) — bu turda uygulanmadı. |
| 5 | ✅ **K6** — çek/senet durumu `MAX(id)` → `(islem_tarihi, id)` | 6 yer düzeltildi, SQL canlı DB'de hatasız; tabloda hareket yok, veri testi kullanıcıda. |
| 6 | **U1 + U2 + U3** — Kaydet-ve-Yeni + Enter/Esc + dirty-guard | Günlük UX'te en büyük kazanç |
| 7 | **C6 + C7 + C19** — edit yüklemelerine `AND firma_id=?` / `AND yil=?`, UNIQUE constraint, index'ler | Sağlamlık (ulaşılamaz kapıları kapatır) |
| 8 | **Q1 + Q2** — form taban sınıfı + import dedup refactor | Sonraki bug'ların üretim hattını kapatır (Taslak backlog ile örtüşüyor) |
| 9 | Kalan C'ler (C1-C20, ❓'lileri karara bağlayarak) ve U'lar | Tek tek |

**Not:** C1 (nakit satışın caride görünmemesi) ve C17 (açılış karşıt satırı) mimari tasarım kararlarıdır — "bug mı, tercih mi" önce karar verilmeli; K2'nin assert'i bu kararlara bağlanır.

---

## 📋 Süreç / Değişiklik Günlüğü *(Claude'ın çalışma kaydı — commit/yükleme yapılmadı, hepsi çalışma ağacında)*

> Kurallar: hiçbir commit/push yapılmadı; DB'ye yazılmadı. Her madde = hangi dosyada ne değişti + nasıl doğrulandı. En sonda kullanıcı kendi test edecek.

### K1 — Fatura edit-load brüt→net ✅
- **Dosya:** `modules/fatura/fatura_form.py:884` (edit-yükleme satır tutarı `toplam_tutar` → `ara_toplam`).
- **Ne:** KDV'li faturayı açıp kaydetmenin satırı KDV kadar şişirmesi (sessiz veri yozlaşması) durduruldu; oluşturma ile edit aynı semantik (satır NET, KDV ayrı satır).
- **Doğrulama:** canlı DB taraması — cari-karşılıklı 347 faturadan yalnız id=7525 (bugünkü test fişi) bozuk; geçmiş veri hasarı yok. (7525 hâlâ DB'de — kullanıcı onayıyla silinecek/düzelecek.)

### K2 — Veri katmanı borç=alacak assert'i ✅
- **Dosya:** `core/services.py` — yeni `_denge_kontrolu` (satır 29); `fis_kaydet` (53) ve `fis_guncelle` (115) yazımdan **önce** çağrıyor.
- **Ne:** yalnız `hesap_turu='Cari'` satırı olan fişlerde |borç−alacak| ≤ 0,01 assert. Cari-karşılıksız fişler (peşin/virman/açılış) dışarıda → C17 assert'i bloklamıyor (C17'nin kendisi ayrı karar).
- **Doğrulama:** canlı DB — 346/347 Cari fiş geçti (0 regresyon); 3 kuruş-farklı fiş toleransla geçti; tek tetikleyen = bilinen bozuk id=7525. `py_compile` temiz.

### K3 — KDV kartı eksikse net hata + banka kardeşi ✅
- **Dosyalar:** `modules/fatura/fatura_form.py` (KDV satırı üretiminde kart-id yoksa `messagebox + return`), `modules/kasa/kasa_form.py:772-793` (gider/gelir KDV satırı, aynı koruma), `modules/banka/banka_form.py` (verileri_yukle'ye KDV kart-id yüklemesi + gider/gelir fişinde **eksik olan** KDV karşılık satırı eklendi + kart yoksa net hata).
- **Ne:** kart eksikken dengesiz fişin sessiz yazılması yerine kullanıcı "KDV kartı tanımlı değil" uyarısı alıp kayıt engelleniyor. Banka Gider/Gelir'de KDV satırı hiç üretilmemesi (fişi daima dengesizleştiren, K2'nin de yakalamadığı hata) kapatıldı.
- **Doğrulama:** `py_compile` üç dosyada temiz. (GUI akışı kullanıcı tarafından test edilecek.)

### K4 — Excel export tarih/sayı + PDF landscape + pandas guard ✅
- **Dosya:** `utils/export.py` — `_parse_numeric_value` yeniden yazıldı; `_export_to_pdf`'de sütun>6 → landscape(A4) ve `page[0]-60`; `export_treeview_data` girişine `if not pd` guard.
- **Ne:** dışa aktarılan tarihler artık metin kalıyor (bozulmuyor), Türkçe para/miktar doğru sayıya çevriliyor, ham ondalık (`2.50`) korunuyor; çok sütunlu PDF yatay; pandas yoksa çökme yerine net uyarı.
- **Doğrulama:** `_parse_numeric_value` 18 girdilik davranış testi 18/18; `py_compile` temiz.

### K6 — Çek/Senet güncel durumu tarih+id ile ✅
- **Dosyalar:** `core/services.py` (`cek_senet_guncel_durum`, `cek_senet_son_banka_takas`, `cek_senet_fis_son_hareket_mi`), `modules/raporlar/cek_senet_portfoy_raporu_view.py`, `.../cek_senet_vade_raporu_view.py`, `.../cek_senet_seruven_raporu_view.py`.
- **Ne:** "son hareket" seçimi `MAX(id)` → `ORDER BY islem_tarihi DESC, id DESC LIMIT 1` (6 yer); serüven sıralaması tarihe göre. Eski tarihli fişi düzenleyince tahsil edilmiş çek'in "Portföyde"ye dönmesi kapatıldı.
- **Doğrulama:** 4 dosya `py_compile`; canlı DB'de karşılaştırma sorgusu hatasız çalıştı; hareket tablosu boş olduğundan veri-üstü etki gözlenemedi (kullanıcı testi gerekli).

### K5 — STOK/FIFO — ⏸ KARAR → Yeni özellik olarak tasarlandı
- Kullanıcı politikası kararı gerektirdiği için ertelenmişti. Karar verildi: muhasebe akışı **kırılmaz**; eksi kasa/banka/stok için **Ayarlar**'da politika + raporlarda kırmızı satır + **"Düzeltilecekler"** sekmesi. 4 adımda kodlanıyor (aşağıda). Import'a müdahale yok.

---
## 🔧 Eksi Çalışma özelliği — adım adım

### Adım 1 — Ayarlar "Eksi Çalışma" sekmesi ✅
- **Dosyalar:** `core/services.py` (yeni: `ayar_oku`/`ayar_yaz` + `EKSI_POLITIKA_SECENEKLERI`, `STOK_MALIYET_SECENEKLERI`, anahtar sabitleri; firma bazlı `genel_tanimlar` grubu üzerinden), `modules/ayarlar/eksi_calisma_view.py` (yeni görünüm), `modules/ayarlar/ayarlar_view.py` (sekme bağlandı).
- **Ne:** Kasa/Banka/Stok için 4 politika (İzin verme / Her seferinde uyar / Bir kere uyar / Hiçbir şey yapma; **varsayılan: Bir kere uyar**). Stok satırının altında örnek metin; stok "izin verme" seçilince anlamsız olan "Maliyetsiz çıkışın maliyeti (0 / son alış tahmini)" alt-seçeneği otomatik gizleniyor. Ayarlar **firma bazlı** saklanıyor.
- **Doğrulama:** 3 dosya `py_compile` temiz; `ayar_oku`/`ayar_yaz` gidiş-dönüş testi (varsayılan, yaz, firma izolasyonu, güncelleme-tek-satır) 5/5 geçti. GUI akışı kullanıcı testi.

### Adım 2 — Fiş kaydında ayara göre "eksiye düşme" uyarısı ✅
- **Dosyalar:** `core/services.py` (yeni: `_hesap_adi`, `eksi_dusme_kontrol` — fiş yazılmadan önce kartın bu fiş sonrası bakiye/miktarını hesaplar), `utils/eksi_uyari.py` (yeni: `eksi_kontrol_ve_onayla` — politika okur, `messagebox` gösterir, "bir kere uyar" oturum hafızası), bağlandığı formlar: `kasa_form`, `banka_form`, `fatura_form` (stok), `fatura_fire_form` (stok), `cari_form` (kasa/banka).
- **Ne:** Fiş kaydedilmeden ÖNCE, bu fiş hangi kartı eksiye düşürüyor bulunur; ayardaki politikaya göre: izin verme → kayıt **engellenir** (error), her seferinde uyar → `showwarning` + devam, bir kere uyar → hesap başına oturumda bir kez uyar, hiçbiri → sessiz. Import'a dokunulmadı. Çek/Senet fişleri henüz kapsam dışı (bkz. aşağıdaki açık sorular).
- **Doğrulama:** `eksi_dusme_kontrol` bellek-içi test (Kasa/Banka/Stok aşırı kullanım + "none" + düzenle-hariç) doğru; `eksi_kontrol_ve_onayla` 4 politika + "bir kere" 2. çağrı + no-offender → 6/6 (messagebox taklit). 7 dosya `py_compile` + import temiz.

### Adım 3 — Raporlarda eksi satırları kırmızı ✅
- **Dosya:** `modules/raporlar/hesap_ekstresi_view.py` — yeni `tag_configure('eksi', kırmızı)`; cari/kasa/banka ekstre dalında `bakiye<0` (yalnız Kasa/Banka) ve stok ekstre dalında `kalan_miktar<0` VEYA çıkışın maliyeti 0 (maliyetsiz çıkış) satırları kırmızı.
- **Doğrulama:** `py_compile` + import temiz. (Görsel doğrulama kullanıcı testi.)

### Adım 4 — Raporlar › "Düzeltilecekler" sekmesi ✅
- **Dosyalar:** `core/services.py` (yeni: `_para_sorunlari`, `_stok_sorunlari`, `eksi_duzeltilecekler` — kronolojik replay), `modules/raporlar/duzeltilecekler_view.py` (yeni: dönem filtresi + iç içe Özet/Kasa/Banka/Stok sekmeleri + çift tık → fişe gitme), `modules/raporlar/raporlar_view.py` (sekme en sona eklendi).
- **Ne:** Ayar "sessiz" olsa bile çalışan kontrol panosu. Özet sekmesi modül başına sorunlu hesap/kart sayısı (temiz yeşil / var kırmızı); sekmelerde satıra çift tık `go_to_module_and_select_fis` ile sorunun başladığı fişe gider (farklı yıl uyarısıyla).
- **Doğrulama:** `py_compile` + import temiz; `go_to_module_and_select_fis` modül anahtarları (kasa/banka/fatura/cek_senet) doğrulandı.

### Adım 4 REVİZYONU — "71 kayıt" karışıklığı giderildi (kart/hesap başına özet + maliyetsiz satış) ✅
- **Sorun:** İlk hâlinde liste *hareket satırı* bazlıydı ("bu satırda eksiye değdi") → 2026'da **71 satır** gösteriyordu; bu, hem yıl sonunda hâlâ eksi olan gerçek açığı hem de sonradan düzelmiş zamanlama eksilerini birbirine karıştırıyordu. Kullanıcı "bu doğru mu?" diye haklı olarak sorguladı.
- **Karar:** Kullanıcı seçimi → **matematiğe (FIFO/Kar-Zarar maliyet motoruna) DOKUNMA**; yalnızca raporu doğru göster.
- **Yapılan (yalnızca rapor metrikleri değişti, maliyet hesabı aynı):**
  - `eksi_duzeltilecekler` artık **hesap/kart başına TEK özet satırı** döndürür. Alanlar: `hesap_adi, ilk_tarih, eksi_satir, donem_sonu, maliyetsiz, birim, ilk_fis_id`.
  - **Kasa/Banka:** yalnız **dönem sonu bakiyesi eksi** olan hesaplar (ara/düzelmiş eksiler sayılmaz). 2026: **KASA 1** (TL KASA, dönem sonu **−30.686 ₺**), **BANKA 0**.
  - **Stok:** iki nedenden biriyle girer → (a) dönem sonu miktar eksi (gerçek açık) VEYA (b) **maliyetsiz satış** (satış, alıştan önce girildiği için maliyeti 0 hesaplanmış — miktar sonradan düzeltilse bile Kar/Zarar'da maliyet eksik kalır). Gelişmiş FIFO: devir dahil tüm çıkışlar katman tüketir, yalnız dönem içi karşılıksız çıkış "maliyetsiz" sayılır. 2026: **STOK 20 kart** (9'u dönem sonu hâlâ eksi `EKSI`, 11'i yalnız maliyetsiz `+MAL`). En büyük maliyetsiz miktarlar: Kuruyemiş 19.28, Biber Salçası 11.5, Domates Salçası 10.48, Propolis 6.0, Japon Lif 5.0.
  - **Gürültü filtresi:** float artık-değerleri (`son=-0.0`, `maliyetsiz≈0`) için eşik **0.01**'e çekildi (miktar epsilon'u ile tutarlı); önceki `0.001` onlarca sahte satırı işaretliyordu.
  - **Sekme tasarımı:** Kasa/Banka sütunları (Hesap, İlk eksi tarihi, Eksi hareket, Dönem sonu, Açıklama). Stok sütunları (Kart, İlk sorun tarihi, **Maliyetsiz satış**, Dönem sonu, Açıklama). Stok'ta dönem-sonu-eksi satırları kırmızı, yalnız-maliyetsiz satırları sarı (koyu-sarı) boyanır. Çift tık `ilk_fis_id`'ye gider; fişin `fis_turu`'ndan Çek/Senet→`cek_senet`, Stok→`fatura`, Kasa→`kasa`, Banka→`banka` seçilir.
- **Önemli bulgu (maliyet matematiği hakkında, DEĞİŞTİRİLMEDİ):** Tüm FIFO maliyet motorları (`stok_bakiye_ve_maliyet`, `stok_donem_cogs`, Kar/Zarar `_cogs_hesapla`) **kronolojiktir**. Satış, alıştan ÖNCE girildiyse o çıkışa katman yetişmez → maliyet **0** hesaplanır (COGS eksik, brüt kâr şişer); sonradan giren alış **geriye dönük** o satışın maliyetini doldurmaz. Miktar yıl sonunda toparlansa bile maliyet yanlış kalır. Kullanıcı kararı gereği bu düzeltilmedi; yalnızca "maliyetsiz satış" sütunuyla **görünür** kılındı. Ekstre (Adım 3) zaten maliyetsiz çıkışı kırmızı boyuyor; Düzeltilecekler artık bu kartları liste deliyor.
- **Doğrulama:** Gerçek DB üzerinde salt-okunur test: KASA=1, BANKA=0, STOK=20 (9 EKSI + 11 +MAL); `_stok_sorunlari`/`_para_sorunlari` doğru. `py_compile` + 4 modül import temiz; eski `_para_eksi_listesi`/`_stok_eksi_listesi` kaldırıldı (yalnız bu dokümanda isim geçiyordu).

### Kullanıcı kararları (sonra uygulandı) ✅
- **Stok maliyet alt-seçeneği KALDIRILDI:** `stok_maliyet_yontemi` ayarı ve `STOK_MALIYET_*`/`AYAR_STOK_MALIYET` sabitleri silindi; `eksi_calisma_view` sadeleştirildi. Maliyetsiz çıkış fiyatlama olarak **0** kalır, kırmızı işaretlenir. (FIFO'ya "tahmini fiyat" bağlanmadı.)
- **Çek/Senet eksi kontrolüne DAHİL EDİLDİ:** `modules/cek_senet/cek_senet_form.py` fiş kaydına `eksi_kontrol_ve_onayla` eklendi (kasa/banka tahsilat/ödeme satırları).
- **"Bir kere uyar" oturum bazlı KALDI** (değişiklik yok).
- **Doğrulama:** `core.services`, `eksi_calisma_view`, `cek_senet_form` `py_compile` + import temiz; sabitler gerçekten kaldırıldı; politika dağıtımı + `eksi_duzeltilecekler` tekrar test edildi (izin_verme→engelle; stok S1 −5 yakalandı).

### Hâlâ açık (kullanıcıya kalmış)
- id=7525 bozuk test fişi DB'de dokunulmadan duruyor (sil/düzelt kararı bekliyor).

