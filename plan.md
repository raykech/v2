# Plan — Ön Muhasebe v2 (Gelecek / Yapılacaklar)

Bu dosya: tamamlanan işler, kararlar ve ileride yapılacak özelliklerin notudur.

---

## 🟢 Tamamlandı

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

---

## 🟠 Kararlar (kullanıcı onaylı)

### Hizmet kartı türü kilidi (uygulandı — `hizmet_view.py`)
- **İşlem görmüş bir hizmet kartının Tür'ü (Gider/Gelir) değiştirilemez.**
  - Gerekçe: Hizmet kartları raporu bir mizandır; gider kartı borç, gelir kartı alacak
    çalışır. Tür değişikliği geçmiş kayıtları mizanda yanlış bölüme taşır ve kartı
    hem borç hem alacak çalışmış "kirli" bir hesaba çevirir.
  - Kullanıcı yanlış kart açtıysa: yeni kart açması veya ileride "Hesap Taşı" kullanması önerilir.

---

## 🔵 İleride Yapılacaklar

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
