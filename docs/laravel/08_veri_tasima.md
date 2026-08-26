# Veri Taşıma

> Mevcut projede veri bulunmadığı için SQLite → MySQL veri taşıma **ilk aşamada yapılmayacaktır**.

## İleride Gerekirse
- SQLite export scripti yazılır.
- MySQL import scripti yazılır.
- Tablo/kolon eşleme tablosu kullanılır.
- ID'ler korunur veya yeniden üretilir.
- Tarih ve `yil` alanları doğrulanır.
- Firma bazlı veri kontrolü yapılır.

## Migration Stratejisi
- Tüm tablolar `database/migrations` altında sıfırdan oluşturulur.
- Her modül migration'ı kendi başlığında yazılır.
- İlişkiler foreign key olarak tanımlanır.
- `firma_id` ve `yil` indexlenir.
