# v2 - Modül Geliştirme Rehberi ve Planı

Bu doküman, v2 mimarisinde yeni bir modül geliştirirken izlenecek adımları ve dikkat edilmesi gereken noktaları anlatır. Amacım, "Çek/Senet modülünü geliştir" dediğinde, bu dokümandaki şablonu aynen takip ederek hatasız bir modül oluşturabilmendir.

---

## 1. Modül Geliştirme Şablonu (Örnek: Banka ve Cari Modüllerinden Çıkarılan Dersler)

### Adım Adım Yeni Modül Oluşturma

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

---

## 2. Çek/Senet Modülü Geliştirme Planı

### Hedef ve Kapsam

**Amaç:** Çek/Senet (Kıymetli Evrak) takibinin yapılabilmesi. Müşteriden alınan çekler, müşteriye verilen çekler, bankaya tahsile verilen çekler, ciro edilen çekler vb. durumların yönetilmesi.

**Ortak Kavramlar:**
- **Çek ve Senet** aynı modülde yönetilecek.
- **Tür:** "Çek" veya "Senet"
- **Durum Takibi:** 
  - "Portföyde" (elde)
  - "Bankada Tahsilde"
  - "Cirolu" (başka birine devredildi)
  - "Tahsil Edildi"
  - "Karşılıksız" (çek) / "Protestolu" (senet)
  - "İade Edildi"
- **Kart Tanımı:** Her çek/senet için seri_no, tutar, vade_tarihi, banka, keşideci, ciranta bilgileri.
- **Hareket Takibi:** `cek_senet_hareketleri` tablosu zaten mevcut (v1'den). Durum değişiklikleri bu tabloya işlenir.

### Fiş Türleri (Çek/Senet Modülü İçin)

1. **Çek/Senet Giriş Fişi** — Yeni bir çek/senet portföye alınır (müşteriden tahsil edilen çek/senet).
2. **Çek/Senet Çıkış Fişi** — Portföydeki çek/senet başka birine verilir (ciro/tahsilat için bankaya verilir).
3. **Çek/Senet Tahsil Fişi** — Çek/senet tahsil edildiğinde kasa/banka hesabına para girişi yapılır.
4. **Çek/Senet İade Fişi** — Çek/senet sahibine geri verilir (iade).

### Veritabanı Tabloları (Mevcut)

**`cekler_senetler` tablosu:**
- id, seri_no, turu ('Çek'/'Senet'), banka, vade_tarihi, tutar, firma_id, created_at, updated_at

**`cek_senet_hareketleri` tablosu:**
- id, cek_senet_id, islem_tarihi, durum, karsi_hesap_tipi, karsi_hesap_id, karsi_hesap_ismi, ilgili_hareket_id, aciklama, firma_id, created_at

### Form Yapısı (Öneri)

- **Üst Kısım (Başlık):**
  - Fiş Türü (Çek/Senet Giriş, Çıkış, Tahsil, İade)
  - Tarih
  - Fiş No
  - Açıklama
  - (Virman gibi özel alanlar gerekmeyebilir; her fiş türü satır bazlı çalışır)

- **Giriş Satırı:**
  - Seri No (Entry)
  - Tür (Çek/Senet Combobox)
  - Banka (Combobox - banka_kurumlari)
  - Vade Tarihi (DateEntry)
  - Tutar (CurrencyFormatter)
  - Keşideci / Ciranta (Entry)
  - "+" Buton

- **Alt Kısım:**
  - Treeview satır listesi
  - Toplam Tutar
  - Kaydet / İptal Butonları

### Kayıt Mantığı

Fiş kaydedildiğinde:
1. `fisler` tablosuna başlık kaydı (fis_turu, tarih, fis_no, aciklama, toplam_tutar)
2. `fis_satirlari` tablosuna satırlar (hesap_turu='CekSenet' veya benzeri, hesap_id <- cek_senet_id)
3. `cekler_senetler` tablosuna her satır için yeni çek/senet kaydı ya da mevcut kaydın güncellenmesi
4. `cek_senet_hareketleri` tablosuna durum değişikliği eklenmesi

---

## 3. Dikkat Edilmesi Gereken Genel Kurallar

1. **`iptal()` metodu:** `self.destroy()` KULLANMA. `pack_forget()` + `on_close()` + `view_container.pack()` kullan.
2. **Girinti hataları:** `main_window.py`'de değişiklik yaparken `elif` bloklarının girintilerine çok dikkat et. Aynı hata birden fazla kez yaşandı.
3. **`module_map` iki yerde var:** `_yeniden_yukle_aktif_modul` metodu iki kez tanımlanmış durumda (üstte ve altta). İkisine de modül ekle.
4. **`_setup_hesap_lookup()`:** Lookup widget'ları `verileri_yukle()` ve `ayarla_form_yapisi()`'ndan SONRA çağrılmalı.
5. **Dosya boyutu:** Form dosyaları büyük oluyor (~500+ satır). Tek seferde `create_new_file` ile oluşturmaya çalışma — stream limitine takılıyor. Önce `create_new_file` ile gövdeyi oluştur, sonra `single_find_and_replace` ile parça parça ekle.
6. **`ac_kart_dialog`:** Yeni kart ekleme için `ui/dialogs.py` kullan. `tablo_adi` parametresi 'cariler', 'kasalar', 'banka_hesaplari', 'hizmet_kartlari' vb. olabilir.
7. **`LookupWidget`:** `configure_lookup(title, data_dict, on_new)` imzasını kullan. `data_dict` key=display adı, value=id olacak şekilde.
8. **CurrencyFormatter:** `ent_miktar`, `ent_birim_fiyat`, `ent_kdv_oran`, `ent_virman_tutar` gibi alanlara uygula. `on_change_callback` ile anında toplam hesaplama yap.
9. **Kaynak Takibi:** Tüm kayıtlarda `kaynak_modul` ve `kaynak_fis_id` alanlarını doldur. Fatura'dan kasa fişi oluşturulduğunda `kaynak_modul='Fatura'` olmalı.
10. **Virman formları:** Satır listesi gizlenir (`self.liste_frame.pack_forget()`), yerine hedef hesap + tutar alanları gösterilir.