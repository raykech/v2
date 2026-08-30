# Ön Muhasebe v2 — Proje Kılavuzu (Otomatik Yüklenir)

Bu dosya her oturumda bağlama enjekte edilir. Projenin **detaylı** durumu
`__projev2.md` ve `plan.md` dosyalarındadır.

## Proje
- Python + Tkinter + SQLite ile yerel ön muhasebe uygulaması.
- Çalıştırma: `python __main__.py` (veritabanı: `on_muhasebe.db`).
- Tüm işlemler çok satırlı fiş modeli: `fisler` + `fis_satirlari`.

## Kanonik Dokümanlar
- `__projev2.md` — güncel mimari, veritabanı modeli, modüller, geliştirme kuralları (madde 1–19), **§9 Güncel Durum**
- `plan.md` — tamamlanan işler, kararlar, bekleyen özellikler (Hesap Taşı, refaktoring backlog vb.)
  ve **yeni modül geliştirme şablonu** (eski `planv2.md` buraya taşındı, dosya artık yok)

## Devam Protokolü
Kullanıcı "devam edelim", "kaldığımız yerden", "continue", "projeyi hatırlıyor musun"
gibi bir şey söylediğinde:

1. `__projev2.md` §9 Güncel Durum ve `plan.md`'yi oku.
2. Çalışılacak konu belli ise sadece ilgili modül dosyasını oku — tüm repoyu asla baştan okuma.
3. Bekleyen özellikler `plan.md`'deki 🔵 bölümündedir (ör. Hesap Taşı, EditableTreeview iyileştirmeleri).
4. Aktif goal varsa `update_goal resume` ile yeniden etkinleştir.

## Çalışma Kuralları (özet)
- Yanıtlar **Türkçe** olur. Kod yorumları da Türkçe olabilir.
- **Sadece ilgili dosyayı/modülü oku** — tüm modülleri yeniden okuma, gereksiz token harcama.
- Normalize veritabanı yapısı korunur (başlık + detay tabloları, `firma_id` + `yil`).
- Kısa ve öz ol; gereksiz uzun açıklama yazma.
- Tüm kayıtlarda `firma_id` ve `yil` korunur; fiş no tekrarı kontrol edilir.
- KDV: 191 İndirilecek / 391 Hesaplanan ayrı satır modeli, Decimal + ROUND_HALF_UP.
- Detaylı kurallar `__projev2.md` §8 (madde 1–19).