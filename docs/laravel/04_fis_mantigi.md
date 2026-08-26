# Fiş Mantığı

## Genel Fiş Modeli
Her işlem bir `Fis` (başlık) ve birden fazla `FisSatiri` (satır) olarak tutulur.
- `fisler.tarih` -> işlem tarihi
- `fisler.yil` -> tarih yılı
- `fisler.fis_turu` -> hangi modülün hangi fiş tipi
- `fisler.toplam_tutar` -> fişin genel toplamı
- `fisler.kaynak_modul` ve `kaynak_fis_id` -> başka fişten türetilme

## Borç / Alacak Yönlendirme
Her modül kendi fiş türüne göre borç/alacak yönünü belirler.

### Kasa
- Kasa Gider: Hizmet satırları borç, Kasa satırı alacak
- Kasa Gelir: Hizmet satırları alacak, Kasa satırı borç
- Kasalar Arası Virman: kaynak kasa alacak, hedef kasa borç
- Kasa Açılış: Kasa satırları borç/alacak

### Banka
- Banka Gider: Hizmet borç, Banka alacak
- Banka Gelir: Hizmet alacak, Banka borç
- Bankalar Arası Virman: kaynak banka alacak, hedef banka borç
- Blokeyi Bankaya Aktar: POS alacak, banka borç
- Bankaya Yatan: banka borç, kasa alacak
- Bankadan Çekilen: kasa borç, banka alacak
- Gelen Banka Transferi: banka borç, cari alacak
- Giden Banka Transferi: cari borç, banka alacak
- Banka Açılış: banka satırları borç/alacak

### Cari
- Alacak Dekontu: Cariler alacak, Gider kartı borç
- Borç Dekontu: Cariler borç, Gelir kartı alacak
- Cari Ödeme: Cariler borç, Kasa/Banka alacak
- Cari Tahsilat: Cariler alacak, Kasa/Banka borç
- Cari Virman: satır bazlı borç/alacak, toplam eşit olmalı

### Fatura
- Satış Faturası: Stok/Hizmet satırları alacak, Cari borç (vadeli) veya Kasa/Banka borç (peşin)
- Alış Faturası: Stok/Hizmet satırları borç, Cari alacak (vadeli) veya Kasa/Banka alacak (peşin)
- Satış İade: Satırlar borç, Cari alacak
- Alış İade: Satırlar alacak, Cari borç

### Çek/Senet
- Giriş Fişi: CekSenet satırı borç, Cari alacak
- Bankaya Tahsile Verme: CekSenet alacak, Banka borç
- Ciro Etme: CekSenet alacak, Cari borç
- Tahsil Fişi: CekSenet alacak, Kasa/Banka borç
- İade Fişi: CekSenet alacak, Cari borç

## Peşin Ödeme Akışı (Fatura)
- Fatura `Nakit`, `Banka` veya `POS` ile kaydedilirse ayrıca `kaynak_modul=Fatura` olan bir Kasa/Banka fişi oluşturulur.
- Bu fiş `kaynak_fis_id` ile ana faturaya bağlanır.
- Ana fatura silinirse bağlı peşin fiş de silinir.

## Kaynak Takibi
- Bir fiş başka modülden türetilmişse düzenleme/silme kilitlenir.
- Kullanıcıya "Kaynağa Git" butonu gösterilir.

## Çek/Senet Durum Makinesi
```
Giriş Fişi
   ↓
Portföyde ──→ Bankaya Tahsile Verme → Bankada Tahsilde → Tahsil Fişi → Tahsil Edildi
   │
   ├──→ Ciro Etme → Cirolu
   └──→ İade Fişi → İade Edildi
```

## Yıl Kuralı
- Fişin `yil` alanı her zaman `tarih` alanının yılıdır.
- Listelerde `firma_id + yil + tarih aralığı` birlikte kullanılır.
- Tarih aralığı aktif yıl dışına taşamaz.


## Referans
- Kasa form kaydetme: `reference/v2/modules/kasa/kasa_form.py` → fis_kaydet()
- Banka form kaydetme: `reference/v2/modules/banka/banka_form.py` → fis_kaydet()
- Cari form kaydetme: `reference/v2/modules/cari/cari_form.py` → fis_kaydet()
- Fatura form kaydetme: `reference/v2/modules/fatura/fatura_form.py` → kaydet()
- Çek/Senet form kaydetme: `reference/v2/modules/cek_senet/cek_senet_form.py` → fis_kaydet()
- Açılış fişi: `reference/v2/modules/acilis/acilis_form.py` → fis_kaydet()