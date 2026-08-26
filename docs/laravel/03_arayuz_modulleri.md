# Arayüz ve Modül Yapısı

## Genel Tasarım
- Uygulama **Inertia + Vue 3** ile SPA benzeri çalışır.
- Sol tarafta veya üstte modül menüsü bulunur.
- Modüller sekmeler halinde açılır.
- Her sekmede liste + filtre + form/aksiyon alanları bulunur.

## Ana Modüller
| Modül | Açıklama |
|---|---|
| Tanımlar | Stok, Cari, Kasa, Hizmet, Banka tanımları + Excel Yükle |
| Kasa | Kasa fişleri, liste, import |
| Banka | Banka fişleri, liste, import |
| Cari | Cari fişleri, liste, import |
| Fatura | Satış/Alış faturaları, liste, import |
| Çek/Senet | Çek/Senet fişleri, durum takibi, import |
| Raporlar | Ekstreler ve durum raporları |
| Ayarlar | Firma, yıl, kullanıcı ayarları |

## Liste Ekranları
Her liste ekranında:
- Filtre alanları (tarih aralığı, hesap/kasa/cari, fiş türü, arama)
- Sıralama ve sayfalama
- Yeni, Düzenle, Sil, Kaynağa Git butonları
- Import butonları (modüle göre)

## Filtre Kuralları
- Tarih aralığı **aktif yılın sınırlarına kısıtlanır**.
- Aktif yıl seçimi genel üst bardadır.
- Liste sorgularında `firma_id` ve `yil` zorunlu filtredir.

## Form Ekranları
- Fiş başlık bilgileri: Tarih, Fiş No, Açıklama, modüle özel alanlar
- Satır girişi: Excel benzeri tablo + satır ekleme
- Toplamlar: Ara Toplam, KDV, Genel Toplam
- Kaydet / İptal

## Lookup / Seçim Bileşeni
- Cari, Kasa, Banka, Stok, Hizmet seçimlerinde açılır arama modalı
- Yeni kart ekleme modalı
- Seçim sonrası KDV otomatik dolgu (opsiyonel)

## Excel Yükle
- Tanımlar modülünde "Excel Yükle" sekmesi
- Modül listelerinde "Örnek İndir" ve "Veri Yükle" butonları
- Önizleme ekranı: hata/uyarı listesi, içe aktar onayı

## Kullanıcı Deneyimi Kuralları
- İşlemlerde geri bildirim (başarı/hata mesajı)
- Kayıt silmede onay
- Import hatalarında satır bazlı hata listesi
- Formlar klavye ile gezilebilir (Enter/Tab)
- Sayfa yenilenince aktif modül korunur


## Referans
- Ana pencere yapısı: `reference/v2/ui/main_window.py`
- Sekme/buton yapısı: `reference/v2/ui/main_window.py` → _modul_aci(), _tab_ekle()
- Lookup widget: `reference/v2/ui/widgets/lookup_widget.py`
- Import preview dialog: `reference/v2/ui/import_preview.py`
- Her modülün view yapısı: `reference/v2/modules/<modul>/<modul>_view.py`