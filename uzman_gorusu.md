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
- **Düzeltme (2026-09-03):** `fatura_form.py:884` edit-yükleme artık `ara_toplam` (net) kullanıyor — oluşturma ile aynı semantik. DB taraması: cari karşılıklı 270 faturadan yalnızca test fişi id=7525 etkilenmişti; **geçmiş veri hasarı yok**. (7525 sonradan temizlendi — 05.09 taraması: dengesiz fiş 0.)

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

### C1. ✅ Karara bağlandı: Peşin/nakit fatura satışları cariye gitmeyecek (tasarım gereği)
- `modules/fatura/fatura_form.py:763-785` (cari karşılık sadece Vadeli'de) → `modules/raporlar/cari_bakiye_raporu_view.py:107-110`
- *(2026-09-04 kullanıcı kararı):* Nakit/peşin satışta cari satırı **bilinçli olarak üretilmiyor** — karşı taraf fişte doğrudan Kasa/Banka. Gerekçe: her nakit çalışan müşteri/tedarikçi için cari kart açmak pratik değil. Cari ekstrede görünmemesi eksik değil, tasarım. Kod değişikliği gerekmez (mevcut davranış kararıyla birebir).

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

### C6. ✅ Tüm form düzenleme-yüklemeleri `firma_id` kapsamlı
- `kasa_form.py:830,845`; `banka_form.py:790,805`; `cari_form.py:666,676-679`; `fatura_form.py:839,897,905`; `cek_senet_form.py:1176,1189,1193,1215`; `acilis_form.py:442,452-455`; `kasa_view.py:453`
- Bugün listeler kapsamlı olduğu için ulaşılamaz, ama tek bozuk id ile çapraz-firma fiş okuma kapısı. `fatura_form.py:861-865` ayrıca `stoklar/hizmet_kartlari` JOIN'inde firma filtresiz (id çakışması yanlış firmaya bağlar) ve INNER JOIN, durum=0 (silinmiş) stoğu olan satırları sessiz düşürür → sil-yaz'da kaybolur.
- `core/services.py:111` — satır silme kapsamsız, başlık UPDATE'i (`:105`) firma istiyor: uyumsuzlukta satırlar gider, başlık durur (kısmi düzenleme, `rowcount` kontrolü yok — `services.py:101-111`).
- `services.py:126,129` (`kaynak_fis_id` SELECT/DELETE) ve `:512-533` (çek/senet durum yardımcıları) firma'sız — global tekil id ile zararsız ama savunmasız desen.
- `modules/cek_senet/cek_senet_form.py:1083-1101` — `UPDATE cekler_senetler ... WHERE id=?` firma korumasız.
- **Düzeltme (2026-09-05):** (Dosya satır numaraları bu turdaki değişikliklerle kaydı; bulgu fonksiyon adlarıyla izlenebilir.)
  1. 7 fiş formunun `load_fis_data`/yardımcı okumaları (`SELECT * FROM fisler WHERE id=?` ve `kaynak_fis_id=?` sorguları) `AND firma_id=?` ile kapsamlendi; `kasa_view` kart-filtre sorgusu da kapsamlı.
  2. `core/services.py` `fis_guncelle`: başlık UPDATE'inden sonra `rowcount==0` → `ValueError("Fiş bulunamadı (firma uyumsuzluğu) — güncelleme iptal edildi.")` — hiçbir satıra dokunmadan iptal (kısmi düzenleme kapısı kapandı). Satır DELETE'leri ve `kaynak_fis_id` SELECT/DELETE'leri `firma_id` kapsamlı.
  3. `fatura_form` edit-yükleme kart JOIN'i → `LEFT JOIN {kart} s ON fs.hesap_id = s.id AND s.firma_id = ?`: id çakışması yanlış firmayı bağlamaz; silinmiş (durum=0) kartlı satırlar sessiz düşmez.
  4. `cek_senet_form`: `UPDATE cekler_senetler ... WHERE id=? AND firma_id=?`; çek/senet durum yardımcılarındaki (services) firma'sız okumalar kapsamlı.
- **Doğrulama:** servis smoke testi — yanlış firma id'siyle `fis_guncelle` → ValueError, fiş ve satırlar AYNEN duruyor (regresyon yok). Tüm formlar GUI smoke'unda açılıp kapandı.

### C7. ✅ Fiş no tekilliği DB'de garanti (mevcut bozuk veriye çarpmayan güvenli kurulum)
- `core/services.py:5-26` check-then-act; `db.py:136-153`'te `UNIQUE(fis_no, firma_id, yil)` yok. Bağlantı işlem-başına, lock yok → eşzamanlı iki kayıt aynı no'yu geçirebilir.
- Benzer: `genel_tanimlar`'daki `INSERT OR IGNORE` (`db.py:235`) `Ana Firma (Varsayılan)` adında gerçek bir firma tanımlanırsa UNIQUE'e çarparak startup'ı bozar.
- **Düzeltme (2026-09-05):** `core/db.py` — kısmi UNIQUE index: `uq_fisler_no_tarih ON fisler (fis_no, firma_id, yil, tarih) WHERE fis_no <> ''` (uygulama politikası `fis_no_kontrol` ile aynı granülerlik; boş fiş no'lu 3700+ fiş kapsamdışı). Kurulumdan önce mevcut veride ihlal taranır; ihlal varsa index **atlanır + konsol uyarısı** — startup asla kırılmaz. `INSERT OR IGNORE INTO firmalar` zaten sessiz-ignore ettiğinden startup riski yoktu; mevcut davranış korundu (NOT: `firmalar.firma_adi UNIQUE` olduğu için kullanıcı aynı adda ikinci firma açamaz — mevcut karta dokunulmadı).
- **Doğrulama:** mevcut DB'de ihlal taraması 0 sonuç → index kuruldu; `tablolari_olustur()` iki kez çalıştırıldı (idempotent), compileall temiz.

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

### C17. ✅ Karara bağlandı: Açılış fişleri tek taraflı kalacak — mizan modeli yok (tasarım gereği)
- `modules/acilis/acilis_form.py:17-19` — "karşı satır oluşturulmaz". Küresel mizan bu yüzden hiç dengeleyemez.
- *(2026-09-04 kullanıcı kararı — KAPADI):* Burası **ön muhasebe**; mizan diye bir rapor/kanıt yok, her modül kendi devrini gösterir (kasa açılışı borç 1.000 TL → kasa raporunda tek başına görünür, bu doğrudur). 590 karşıt satır **üretilmeyecek**; K2'nin `_denge_kontrolu` kapsamı (yalnız Cari satırlı fişler) bu kararla tutarlı — açılışlar kontrol dışı kalır.
- **Sonraya not (yıl kapanışı olmadığından geçmiş yıl bakiyeleri devir alamıyor):** her modüle **Kapanış Fişi** yapılacak. Örnek Kasa: tüm kasa kartlarını ters hesap edip kapatır **ve** sonraki yılın açılış fişini otomatik üretir; maksat raporlarda (Kasa/Banka/Cari ekstre) kesintisiz bakiye görünmesi — muhasebe kaydı değil, rapor bütünlüğü. Detay: plan.md 🔵 "Kapanış Fişi".

### C18. ✅ `fis_sil` → `cek_senet_hareketleri` yetim kayıtları temizleniyor
- `core/services.py:154-180` hareket tablosunu temizlemiyor (FK/cascade yok); sadece `cek_senet_fis_sil` (`:588`) siliyor. Çek/senet fişi genel silme yolundan silinirse sarkan `fis_id` → `cek_senet_fis_son_hareket_mi:536` ve durum sorguları bozulur.
- **Düzeltme (2026-09-05):** `fis_sil` artık ana fişin **ve** bağlı (kaynak_fis_id ile türetilmiş peşin/ödeme) fişinin `cek_senet_hareketleri` satırlarını siliyor; `fis_guncelle`'nin eski peşin fişi temizleme adımı da aynı şekilde hareket kayıtlarını siliyor. Çek/Senet modülü kendi yolunu (`cek_senet_fis_sil`) kullanmaya devam eder; bu, genel silme yolunun **güvence katmanı**.
- **Doğrulama:** servis smoke testi — hareket satırı enjekte edilmiş fiş `fis_sil` ile silinince `cek_senet_hareketleri`'nde `fis_id` sarkan kayıt kalmıyor.

### C19. ✅ Şemada sıcak yol index'leri eklendi
- `db.py:136-173, 217-223` — `fis_satirlari(fis_id)` (her silme/güncelleme ve CASCADE bu FK'yı kullanıyor), `fisler(firma_id,yil)`, `fisler(fis_no)`, `fisler(kaynak_fis_id)` index'leri yok; `firma_id`'de FK/CHECK yok. Büyük veritabanında ilk yavaşlık burada çıkar.
- **Düzeltme (2026-09-05):** `core/db.py` `tablolari_olustur()` içine 6 index (`CREATE INDEX IF NOT EXISTS` — mevcut DB'ye sorunsuz migrate olur): `idx_fis_satirlari_fis (fis_id)`, `idx_fisler_kaynak (kaynak_fis_id)`, `idx_csh_fis (fis_id)`, `idx_csh_cek_senet (cek_senet_id, islem_tarihi)`, `idx_genel_tanimlar_grup (grup, firma_id)` + C7'nin `uq_fisler_no_tarih`'i. (`idx_fisler_firma_tarih` zaten vardı, listelerin `(firma_id, yil, tarih)` süzgesi bu index'le destekli.)
- **Doğrulama:** mevcut DB'de `tablolari_olustur()` iki kez çalıştırıldı (idempotent); index'ler `sqlite_master`'da görünüyor. (FK/CHECK ekleme işi bilinçli kapsam dışı — mevcut satırların doğrulanmasını gerektirir, veri migration'ı; şimdilik sadece index'ler.)

### C20. ⬜ `kaydet_kart` dinamik kolon SQL'i
- `core/services.py:257-259, 268-271` — tablo adı whitelist'li ama `SET {columns}` parçaları dict **key**'lerinden f-string ile kuruluyor (değerler parametreli → metin-alan enjeksiyonu değil, ama kırılgan desen).
- `:265` — `stok_adi.lower()` Türkçe İ/I için yanlış slug üretir.

---

## 🟡 UX — Muhasebecinin her gün hissedeceği eksikler

### U1. ✅ "Kaydet ve Yeni Fiş" akışı var
- Her kayıt formları kapatıp listeye döndürüyor (`kasa_form.py:813-815`; `fatura_form.py:827` `self.kapat()`). N fiş = N × (formu yeniden aç + kasa/hesap seç + tarih ayarla). **Günlük kullanımda en yüksek frekanslı sürtünme.**
- **Düzeltme (2026-09-05):** 7 fiş formunun (kasa, banka, cari, açılış, çek/senet, fatura, fire) alt buton çubuğuna mavi **"Kaydet ve Yeni Fiş"** (`bg="#0d6efd"`) eklendi. Kayıt metodu `yeni_fis=False` parametresi aldı: başarıda modal göstermeden formu **yerinde** sıfırlayan `_yeni_fis_sifirla` — tarih ve ana hesap korunur, fiş no/açıklama/satırlar temizlenir, giriş satırı sıfırlanır (miktar 1,00 / KDV 20), `anlik_yenile` ile kirlilik anı sıfırlanır, durum çubuğunda kısa mesaj, liste arka planda yenilenir, odak fiş no'ya gider. Kasa/Banka/Cari/Açılış/Fatura/Fire ortak reset mantığı `ui/dirty_guard.py:yeni_fis_temel_sifirla` + formların kendi `temizle_giris_satiri`/`giris_satirini_temizle` helper'larıyla; Çek/Senet `temizle_giris_satiri()` + `_tahsil_onceki_durum` sıfırlamasıyla.
- **Doğrulama:** 7 form GUI smoke'u — init temiz → fiş no yazınca kirli → `_yeni_fis_sifirla()` sonrası temiz + `fis_id is None`. Tree satır kirliliği + reset sonrası ağaç boşluğu doğrulandı.

### U2. ✅ Kaydedilmemiş değişiklik koruması var
- `ui/main_window.py:319-336` (`_tab_kapat`), `:410-412` (`cikis_onayla` formdan habersiz), `:150-154` (firma/yıl değişimi tüm sekmeleri sessiz kapatır); formlarda `iptal()`/çarpı ile uyarısız diskart (`kasa_form.py:905-910`, 7 formda aynı).
- `ui/widgets/editable_treeview.py:341-343` — geçersiz hücre mesaj vermmeden sessizce geri alınıyor.
- **Düzeltme (2026-09-05) — `ui/dirty_guard.py` (yeni modül):** `form_anlik` = başlık widget'ları (tarih, fiş no, açıklama, ana hesap, fiş türüne özgü alanlar) + satır ağacının tuple anlık görüntüsü. `dirty_kur(form)` form kuruluşunda anı sabitler; `anlik_yenile(form)` her kayıttan/reset'ten sonra yeniden sabitler (kayıt sonrası kapanışta sorma); `kirli_mi(form)` anla karşılaştırır; `iptal_onayla(form, devam)` kirliyse `askyesno("Kaydedilmemiş Değişiklikler", ...)` ile onaylatır — **7 formun `iptal()`/`kapat()`'ı** buna bağlandı. Ana pencerede üç sessiz-diskart kapısı kapatıldı: `_tab_kapat`, `cikis_onayla` ve firma/yıl değişimi, `modul_formu_kirli_mi` + `_kirli_form_var_mi`/`_kirli_onay` ile açık ve kirli formları listeyip soruyor. `SayfaliListeMixin`/view tarafında `yenile()` delegasyonu korundu.
- **EditableTreeview:** geçersiz hücre geri alımında 2 sn'lik sarı bilgi balonu (`_gecici_uyari`) — sessizlik bitti.
- **Not:** `dirty_guard` ağaç adları `("tree_satirlar", "tree")` — kasa/banka/cari/çek/acilis `tree_satirlar`, fatura/fire `tree` kullanıyor; 5 formdaki `("tree_satirlari",)` yazım hatası bu yüzden satırları hiç izlemiyordu, düzeltildi.
- **Doğrulama:** form smoke'ları (yukarı) + tree satır kirliliği testi + tüm modüller GUI'de açılıp kapatıldı.

### U3. ✅ Klavye akışı geldi
- `ui/dialogs.py`, `main_window.py`, `lookup_widget.py`'de `<Return>`=Kaydet / `<Escape>`=İptal binding'i yok; `LookupDialog` (`:61`) yalnız çift-tık/buton ile seçtirir; menülerde accelerator yok (F5 hariç). (Good: `EditableTreeview`'da Enter→sonraki hücre ve CurrencyFormatter zinciri var.)
- **Düzeltme (2026-09-05):**
  1. **`LookupDialog` klavyeyle tamamen kullanılabilir** (`ui/widgets/lookup_widget.py`): arama kutusunda `Return` → tek sonuçsa anında seçer, değilse ağaca geçer/ağaçta seçiliyse kaydeder; `Down` → ağaca geçer (ilk satıra odak); ağaçta `Return` → seç; pencerede `Escape` → kapat; `WM_DELETE_WINDOW` bağlandı.
  2. **Menü kısayolları** (`ui/main_window.py`): `kisayollar` sözlüğü tek yerden — Alt+T Tanımlar, Alt+K Kasa, Alt+C Cari, Alt+F Fatura, Alt+B Banka, Alt+S Çek/Senet, Alt+R Raporlar, Alt+Y Ayarlar; menülerde `accelerator=` etiketi + `bind_all` ile gerçek binding; **Ctrl+Q → çıkış** (onay akışıyla). 
  3. Form-LEVEL `Return`=Kaydet / `Escape`=İptal **bilinçli olarak bağlanmadı**: fiş formlarında çok alan + EditableTreeview hücre düzenleme akışı var; `bind_all("<Escape>")` LookupDialog'un Escape'i ile çakışırdı. İptal akışı zaten `iptal_onayla` ile korunuyor.
- **Doğrulama:** binding'ler `py_compile` + GUI açılış testi; LookupDialog klavye davranışı kullanıcı testine bırakıldı (pencere görünürlüğüne bağlı `event_generate` tuzağı nedeniyle otomatik test edilmedi — bkz. plan.md notu).

### U6. ✅ Rapor sekmeleri artık yenileniyor
- `modules/raporlar/raporlar_view.py:93-94` — `RaporlarModulu.yenile()` gövdesi `pass`; `main_window.py:308-310` yalnız modül-genelini çağırıyor → her alt-görünümün `yenile()`'i (kategori listesi, KDV hesap id'leri, `stok_rapor_tabani.py:50,55`'te widget oluşturmada `aktif_yil`'e sabitlenen tarih varsayılanları) firma/yıl değişince yenilenmez. (Good: filtreler sekmeler arası korunuyor.)
- **Düzeltme (2026-09-05):** `RaporlarModulu.yenile()` ve `StokRaporlariView.yenile()` **tembel-sekme-güvenli** yazıldı: seçili sekmenin başlığı `self._tabs`/`self._sekmeler` kaydıyla eşleştirilir (lazy sekmelerde `nametowidget` placeholder döndürdüğü için sözlükten bakılır), yalnız gerçekten oluşturulmuşsa `view.yenile()`'e delege edilir. Yeni `AltSekmeGrubu` (rapor gruplaması, bkz. aşağıdaki 🔧 günlüğü) aynı deseni taşır. Böylece firma/yıl değişiminde görünen raporun filtre/lookup/varsayılan-tarih verisi tazeleniyor.
- **Doğrulama:** rapor grubu smoke'u — iç sekme tembel üretimi + `yenile()` çağrısı hatasız. (Görsel tazelik kullanıcı testi.)

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

### U9. ✅ Sessiz konsol hataları kullanıcıya gösteriliyor
- `cek_senet_form.py:925, 962` — durum aramaları DB try-bloğu dışında; KeyError konsola basıyor, UI donmuş gibi görünüyor. `kasa_form.py:356-357` benzeri `print()`.
- **Düzeltme (2026-09-05):**
  1. `kasa_form.py`: `_on_hesap_select`'teki `print` → `messagebox.showerror("Hesap Seçim Hatası", ...)`; `satir_sil`'deki `print` → bilinçli `pass` (satır zaten listeden düşmüş — sessiz yoksay, yorumla belgeli).
  2. `cek_senet_form.py`: `verileri_yukle` baştan sona `try/except` — hata `showerror("Veri Yükleme Hatası", ...)` olarak kullanıcıya çıkıyor, `finally` ile bağlantı kapatılıyor. `_durum_kontrol` ve `_tahsil_icin_durum_dogrula`: fiş satırında kart silinmişse (kayıp kart) KeyError yerine `showwarning("Kayıp Kart", ...)` + güvenli dönüş.
  3. Fatura/fire formlarındaki kalan `print` hata yolları da `showerror`'a çevrildi.
- **Doğrulama:** 7 fiş formunda `print(` kalmadı (grep temiz); kalanlar kapsam dışı debug log'ları (`kasa_view` import log'u, `dashboard_view` except, hizmet raporu traceback). compileall + GUI smoke.

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
| Q1 | 🚫 Kararla kapandı | kasa_form ↔ banka_form ~653 birebir satır (similarity 0.72; cari↔acilis 0.50, kasa↔acilis 0.36, fatura↔fire 0.31). C8'deki eksik kontrol tam bu fork'un maliyeti. Ortak taban fiş-form sınıfı (Taslaktaki RefactoringBacklog ile örtüşüyor) bunu ve K3/C14'ün bir sınıfını kalıcı kılar. | `modules/kasa/kasa_form.py`, `modules/banka/banka_form.py` — **Kullanıcı kararı (04.09.2026): işlem formları BİLEREK ayrı tutuluyor, taban sınıf YAPILMAYACAK** (bkz. plan.md 🟠 Kararlar). K3/U1/U2 gibi düzeltmeler bu karara saygıyla form-form + paylaşılan küçük helper (`ui/dirty_guard.py`) ile yapıldı. |
| Q2 | ✅ | 6 import dosyasında `_metin/_sayi/_tarih` helper'ları 6'şar kere kopya; 5 preview dialog `import_preview.py`'da yapısal aynı ~90 satır (K4-banka-NameError bunun semptomu). | `modules/*/*_import.py`, `ui/import_preview.py` — **Düzeltme (2026-09-05):** `utils/import_helpers.py` (yeni): `metin`/`sayi`/`tarih`/`durum_to_int` + `cari_id_bul`/`kasa_id_bul`/`banka_id_bul`/`banka_kurum_id_bul`/`stok_id_bul`/`hizmet_id_bul`. 6 import dosyasındaki kopya tanımlar silinip `as _metin` vb. takma adla içe aktarıldı (dosya içi çağrı noktaları değişmedi); davranış sözleşmesi birebir korundu (None / "ambiguous" / "wrong_type"). `sayi` Türkçe desenleri birleştirilmiş en iyi hâliyle aldı ("1.234,56"→1234.56, "1.000"→1000, "2.50"→2.5). Yerel kalanlar: map-tabanlı `_kasa_id_bul` (kasa_import), `_odeme_hesap_id_bul` (fatura). Doğrulama: bellek-içi sqlite sözleşme testleri + 6 modül import + compileall. (import_preview'daki 5 kopya diyalog bu turda birleştirilmedi — ayrı iş.) |
| Q3 | ⬜ | `kaydet` ~470 satırlık state-machine (çek/senet); formlarda 150+ satırlık `kaydet`/`load_fis_data`. UI dosyalarından doğrudan SQL (lookup ve fiş yükleme `services`'ı baypas ediyor; yazma yolu `fis_kaydet/guncelle`'den geçiyor). | `cek_senet_form.py` vb. |
| Q4 | ⬜ | Kırılgan widget deseni: `kasa_form.py:252-282` (+banka kopyası) `lookup.set` monkey-patch, StringVar trace + `after(50)/after(300)` polling, her `yeni_kart_ekle` çağrısında binding birikiyor. `cek_senet_form.py:785-795, 1104-1107` — hesap_id'yi yer-tutucu-0 hilesiyle, dict/list sırasının eşit varsayıldığı atama. | |
| Q5 | ⬜ | `main_window._modul_aci` 10 dallı if/elif merdiveni (`:166-194`), F5 yolundaki `module_map`'ı (`:377-387`) tekrarlıyor → kayıt tablosuna dönüşmeli. | |
| Q6 | 🔧 Kısmen | ~~Ölü kod: `modules/raporlar/stok_raporu_view.py`~~ **SİLİNDİ (2026-09-05, kullanıcı onaylı backlog maddesi).** Kalan: `services.py:1` kullanılmayan `import sqlite3`; `services.py:412,439` yanıltıcı/etkisiz parametreler; `fis_kaydet` id döner, `fis_guncelle` dönmez. | |
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
| 2 | ✅ **K2** — `fis_kaydet/fis_guncelle`'e borç=alacak assert'i (`services.py:29`) | Veri-katmanı güvencesi eklendi; kapsam="yalnız Cari satırlı fiş" → C17'yi beklemeye gerek kalmadı. Canlı DB'de 346/347 geçti (0 regresyon). **C17 karara bağlandı (04.09): açılışlar tek taraflı kalır, mizan mantığı yok.** |
| 2b | ✅ **K3** — assert aktifleşti, artık 191/391 kartı eksikse net "KDV kartı tanımlı değil" hatası şart | 03.09'da tamamlandı (banka kardeşiyle birlikte). |
| 3 | ✅ **K4** — `export.py` `_parse_numeric_value` (tarih/sayı) + PDF landscape + pandas guard | 18/18 davranış testi; `py_compile` temiz. |
| 4 | ❓ **K5 + C8 fire + C4** — stok bakiye kontrolü / FIFO eksik katman / iade maliyeti | **KARAR GEREKİYOR** (K5 bloğundaki A/B/C seçenekleri) — bu turda uygulanmadı. |
| 5 | ✅ **K6** — çek/senet durumu `MAX(id)` → `(islem_tarihi, id)` | 6 yer düzeltildi, SQL canlı DB'de hatasız; tabloda hareket yok, veri testi kullanıcıda. |
| 6 | ✅ **U1 + U2 + U3** — Kaydet-ve-Yeni + Enter/Esc + dirty-guard | 05.09 tamamlandı (aşağıda 🔧 günlüğü). Form-level Return/Esc bilinçli kapsam dışı (U3 notu). |
| 7 | ✅ **C6 + C7 + C19** (+ C18) — edit yüklemelerine `AND firma_id=?`, UNIQUE constraint, index'ler, yetim hareket temizliği | 05.09 tamamlandı. |
| 8 | ✅ **Q2** — import helper'ları `utils/import_helpers.py`'da toplandı · Q1 → **KARAR: formlar ayrı kalacak** (taban sınıf yapılmayacak) | 05.09; import_preview kopya diyalogları ayrı iş olarak kaldı. |
| 8b | ✅ **Rapor gruplaması** — Ekstre ve Hizmet raporları tek ana sekme altında (`AltSekmeGrubu`) | Stok/Çek-Senet deseni genelleştirildi; "Sonraki adım" (plan.md) uygulandı. |
| 9 | Kalan C'ler (C2-C5, C8-C16, C20 — ❓'lileri karara bağlayarak) ve U'lar (U4, U5, U7, U8, U10) | Tek tek |

**Not:** C1 (04.09) ve C17 (04.09) karara bağlandı — peşin satış cariye gitmez; açılışlar tek taraflı kalır (mizan mantığı yok). Mimari ❓ kalmadı.

---

## 📋 Süreç / Değişiklik Günlüğü *(Claude'ın çalışma kaydı — commit/yükleme yapılmadı, hepsi çalışma ağacında)*

> Kurallar: hiçbir commit/push yapılmadı; DB'ye yazılmadı. Her madde = hangi dosyada ne değişti + nasıl doğrulandı. En sonda kullanıcı kendi test edecek.

### K1 — Fatura edit-load brüt→net ✅
- **Dosya:** `modules/fatura/fatura_form.py:884` (edit-yükleme satır tutarı `toplam_tutar` → `ara_toplam`).
- **Ne:** KDV'li faturayı açıp kaydetmenin satırı KDV kadar şişirmesi (sessiz veri yozlaşması) durduruldu; oluşturma ile edit aynı semantik (satır NET, KDV ayrı satır).
- **Doğrulama:** canlı DB taraması — cari-karşılıklı 347 faturadan yalnız id=7525 (bugünkü test fişi) bozuk; geçmiş veri hasarı yok. (7525 05.09'da DB'de artık yok; son tarama temiz.)

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

### 05.09 turu — Sağlamlık + UX + Kalite (C6, C7, C18, C19 · U1, U2, U3, U6, U9 · Q2 · rapor gruplaması · ölü dosya) ✅
- **Kapsam:** bu turda raporun ⬜ maddelerinden 10'u kapandı; hiçbir commit yapılmadı, hepsi çalışma ağacında.
- **Sağlamlık:** C6 edit-yükleme firma kapsamları + `fis_guncelle` rowcount muhafızı + fatura LEFT JOIN firma süzgesi (`services.py`, 7 form, `kasa_view.py`); C7 kısmi UNIQUE index `uq_fisler_no_tarih` (ihlal taramalı, startup-güvenli); C18 `fis_sil`/`fis_guncelle` → `cek_senet_hareketleri` yetim temizliği; C19 5 yeni index (`db.py`).
- **UX:** `ui/dirty_guard.py` (yeni) + 7 forma `dirty_kur`/`anlik_yenile`/`iptal_onayla` entegrasyonu (U2); "Kaydet ve Yeni Fiş" butonu + `yeni_fis` akışı 7 formda (U1); `LookupDialog` tam klavye + Alt+harf/Ctrl+Q menü kısayolları (U3); `RaporlarModulu`/`StokRaporlariView`/`AltSekmeGrubu` tembel-sekme-güvenli `yenile()` (U6); sessiz `print` hataları → `showerror`/`showwarning` (U9).
- **Kalite:** Q2 → `utils/import_helpers.py` (yeni) + 6 import dosyasından kopya helper'ların silinmesi; ölü `stok_raporu_view.py` silindi; rapor gruplaması `modules/raporlar/alt_sekme_grubu.py` (yeni) — Ekstre (Cari/Kasa/Banka) ve Hizmet (Kartlar+Detay) tek ana sekme altında.
- **Doğrulama (tur sonu):** `compileall` temiz; servis smoke'ları (rowcount muhafızı, yetim temizliği, import helper sözleşmeleri); GUI smoke'ları — 8 modül açılışı, 7 form kirlilik/reset/tree döngüsü, rapor grupları tembel üretim + `yenile()`.
- **Bu turda BİLEREK yapılmayanlar:** form-level Return/Esc (LookupDialog çakışması — U3 notu); `import_preview.py` 5 kopya diyalog birleştirmesi; `FisListeMixin` (plan.md backlog'da duruyor); `firmalar`/schema FK-CHECK dönüşümü (veri migration'ı gerektirir).

### Hâlâ açık (kullanıcıya kalmış)
- ~~id=7525 bozuk test fişi~~ **KAPANDI (05.09.2026):** fiş DB'de artık yok (kullanıcı temizlemiş); genel tarama — tolerans üstü dengesiz Cari'li fiş **0**, geçmiş veri hasarı tamamen temiz.

