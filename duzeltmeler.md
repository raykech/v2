📋 Ön Muhasebe v2 - Güvenlik ve Kod Analiz Raporu
🚨 KRİTİK SORUNLAR
1. SQL Injection Güvenlik Açığı ⚠️
Konum: core/services.py satır 205-219

python
Copy
def kaydet_kart(cursor, tablo_adi, veri_sozlugu):
    # ...
    columns = ", ".join([f"{key} = ?" for key in veri.keys()])
    params = list(veri.values()) + [kart_id]
    cursor.execute(f"UPDATE {tablo_adi} SET {columns} WHERE id = ?", params)  # ⚠️ Kritik
    # ...
    cursor.execute(f"INSERT INTO {tablo_adi} ({columns}) VALUES ({placeholders})", params)  # ⚠️ Kritik
Risk: Tablo adı kullanıcı girişiyle doğrudan SQL sorgusuna eklendi. Kullanıcı tablo_adi parametresine 'cariler; DROP TABLE cariler; --' gibi bir değer girebilir.

Öneri:

python
Copy
def kaydet_kart(cursor, tablo_adi, veri_sozlugu):
    if tablo_adi not in GECERLI_KART_TABLOLARI:
        raise ValueError(f"Geçersiz tablo adı: {tablo_adi}")
    
    # Tablo adı doğrulandı, şimdi güvenli bir şekilde kullan
    cursor.execute(f"UPDATE {tablo_adi} SET ...", params)
2. Floating Point Hatası - KDV Hesaplamaları ⚠️
Konum: Tüm form dosyalarında (kasa_form.py, fatura_form.py, vb.)

python
Copy
# Satır 102-103 (kasa_form.py)
ara_toplam = miktar * birim_fiyat
kdv_tutar = ara_toplam * (kdv_oran / 100)  # ⚠️ Floating point hatası
genel_toplam = ara_toplam + kdv_tutar
Risk:

100 * 0.1 = 10.0 → 10 * 0.1 = 1.0000000000000002 gibi nokta hassasiyeti sorunları
KDV tutarları küçük farklarla bozulabilir
Raporlarda toplam tutarlar tutarsız olabilir
Öneri:

python
Copy
from decimal import Decimal, ROUND_HALF_UP

def hesapla_kdv_tutar(miktar, birim_fiyat, kdv_oran):
    """KDV hesaplama için Decimal kullanımı"""
    ara_toplam = Decimal(str(miktar)) * Decimal(str(birim_fiyat))
    kdv_oran_decimal = Decimal(str(kdv_oran)) / Decimal('100')
    kdv_tutar = ara_toplam * kdv_oran_decimal
    # Yuvarlama: 2 ondalık basamak
    return float(kdv_tutar.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
3. Hesap Ekstresi Raporunda Bakiye Hesaplama Hatası 🐛
Konum: modules/raporlar/hesap_ekstresi_view.py satır 111-143

python
Copy
# Satır 111-116: Devir bakiyesi hesaplama
cursor.execute("""
    SELECT SUM(borc) - SUM(alacak) FROM fis_satirlari fs
    JOIN fisler f ON f.id = fs.fis_id
    WHERE fs.hesap_turu = ? AND fs.hesap_id = ? AND f.tarih < ? AND fs.firma_id = ?
""", (self.hesap_turu, hesap_id, bas_tarih, self.main_app.aktif_firma_id))
devir_bakiye = cursor.fetchone()[0] or 0.0

# Satır 140-142: Bakiye güncelleme
bakiye = devir_bakiye
for hareket in hareketler:
    bakiye += borc - alacak  # ⚠️ Mantık hatası!
Sorun:

Devir bakiyesi tüm geçmiş fişleri toplamalı, sadece f.tarih < bas_tarih olanları değil
Bu hesaplama yanlış bir bakiye sunabilir
Örnek: 5 fiş var, 2'si geçmiş, 3'ü yeni - sadece 2'si devir bakiyesine dahil ediliyor
Öneri:

python
Copy
cursor.execute("""
    SELECT SUM(borc) - SUM(alacak) FROM fis_satirlari fs
    JOIN fisler f ON f.id = fs.fis_id
    WHERE fs.hesap_turu = ? AND fs.hesap_id = ? AND fs.firma_id = ?
    ORDER BY f.tarih
""", (self.hesap_turu, hesap_id, self.main_app.aktif_firma_id))
devir_bakiye = cursor.fetchone()[0] or 0.0
4. Transaction Yönetimi Eksikliği ⚠️
Konum: core/services.py - fis_sil fonksiyonu

python
Copy
def fis_sil(cursor, fis_id, firma_id):
    # ...
    cursor.execute("DELETE FROM fisler WHERE id = ? AND firma_id = ?", (fis_id, firma_id))
    
    # ⚠️ Eski peşin ödeme fişini sil
    cursor.execute("DELETE FROM fisler WHERE kaynak_fis_id = ?", (fis_id,))
Sorun:

fis_sil fonksiyonu içinde yeni bir transaction başlatılmıyor
Bu fonksiyon başka bir fonksiyonun içinde çağrılıyorsa transaction yönetimi bozulabilir
fis_sil çağrıldıktan sonra cursor.commit() yapılıyor mu kontrol edilmeli
Öneri:

python
Copy
def fis_sil(cursor, fis_id, firma_id):
    """
    Fişi siler. Transaction yönetimi çağıran fonksiyona bırakılmalı.
    """
    if not fis_id:
        raise ValueError("Silinecek fiş ID'si belirtilmedi.")
    
    # ... (kontrol kodları)
    
    # Sadece silme işlemlerini yap, commit'i çağıran fonksiyona bırak
    cursor.execute("DELETE FROM fisler WHERE id = ? AND firma_id = ?", (fis_id, firma_id))
    
    bagli_fis = cursor.fetchone()
    if bagli_fis:
        bagli_fis_id = bagli_fis[0]
        cursor.execute("DELETE FROM fisler WHERE id = ? AND firma_id = ?", (bagli_fis_id, firma_id))
5. Fiş No Tekrarı Kontrolü Eksik 🐛
Konum: core/services.py - fis_kaydet ve fis_guncelle

Sorun: fis_no alanı UNIQUE değil, aynı fiş numarası birden fazla fişe atanabilir:

python
Copy
# db.py satır 137-138
fis_no TEXT DEFAULT '',
# UNIQUE olmalı!
Öneri:

python
Copy
def fis_no_kontrol(cursor, fis_no, fis_id=None, firma_id=None):
    """Fiş numarasının benzersiz olup olmadığını kontrol eder"""
    cursor.execute("""
        SELECT COUNT(*) FROM fisler 
        WHERE fis_no = ? AND firma_id = ? 
        AND (fis_id != ? OR ? IS NULL)
    """, (fis_no, firma_id, fis_id, fis_id))
    return cursor.fetchone()[0] == 0

def fis_kaydet(cursor, fis_baslik, fis_satirlari, pesin_odeme_data=None, kaynak_modul=None):
    # ...
    fis_no = fis_baslik.get('fis_no', '').strip()
    if fis_no:
        if not fis_no_kontrol(cursor, fis_no, firma_id=fis_baslik['firma_id']):
            raise ValueError(f"'{fis_no}' fiş numarası zaten kullanılıyor.")
    # ...
⚠️ DİĞER SORUNLAR
6. KDV Raporunda Aylık Toplam Hatası 🐛
Konum: modules/raporlar/kdv_raporu_view.py satır 154-168

python
Copy
def _ay_toplam_satiri_yaz():
    if son_ay is not None:
        self.tree.insert("", "end", values=(
            f"{son_ay} AY TOPLAMI", "", "", "", "",
            format_currency(ay_191), format_currency(ay_391)
        ), tags=('ay_toplam',))

for tarih, fis_no, fis_turu, hesap_id, aciklama, borc, alacak in hareketler:
    ay = tarih[:7]  # YYYY-MM
    if ay != son_ay:
        _ay_toplam_satiri_yaz()
        son_ay = ay
        ay_191 = 0.0
        ay_391 = 0.0

    # ...
    if hesap_id == indirilecek_id:
        ay_191 += borc
        toplam_191 += borc
    if hesap_id == hesaplanan_id:
        ay_391 += alacak
        toplam_391 += alacak
Sorun:

Aylık toplamlar sadece KDV satırlarına göre hesaplanıyor
Diğer fiş satırları (Stok, Hizmet, Cari) KDV raporunda görünmüyor ama aylık toplama dahil edilmeli
Bu durum raporun eksik görünmesine neden olabilir
7. Veritabanı Bağlantı Yönetimi 📊
Konum: Tüm dosyalarda (db.py, services.py, form dosyaları)

Sorun:

Bazı yerlerde conn.close() yanlış veya eksik yapılıyor
Exception durumunda bağlantı kapanmıyor
Öneri: Context manager kullanımı

python
Copy
def veritabani_baglan():
    """Veritabanına bağlanır ve bağlantı nesnesini döndürür."""
    conn = sqlite3.connect(DB_YOLU)
    return conn

# Context manager wrapper
@contextmanager
def db_transaction():
    conn = veritabani_baglan()
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
8. Kod Tekrarı ve Benzerlikler 🔁
Bulunan Benzerlikler:

Satır Ekleme Mantığı (Her form dosyasında aynı):

kasa_form.py, banka_form.py, fatura_form.py
Tüm formlarda aynı yapı: if self.duzenlenen_satir_id: ... else: ...
Öneri: Bu mantığı bir helper fonksiyona taşı
KDV Hesaplama (Her yerde):

ara_toplam = miktar * birim_fiyat
kdv_tutar = ara_toplam * (kdv_oran / 100)
Öneri: utils/validators.py veya utils/formatters.py içinde ortak fonksiyon
Toplam Hesaplama (Her yerde):

python
Copy
ara_toplam = sum(s['miktar'] * s['birim_fiyat'] for s in self.satirlar.values())
kdv_toplam = sum(s['kdv_tutar'] for s in self.satirlar.values())
genel_toplam = ara_toplam + kdv_toplam
Öneri: Ortak fonksiyon
9. Hata Yönetimi Eksikliği 🚨
Konum: ui/dialogs.py satır 114-119

python
Copy
except sqlite3.IntegrityError:
    messagebox.showerror("Hata", f"'{kurum_adi}' adında bir banka kurumu zaten mevcut.", parent=self)
    if conn: conn.rollback()
except Exception as e:
    messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {e}", parent=self)
    if conn: conn.rollback()
finally:
    if conn: conn.close()
Sorun:

IntegrityError dışındaki tüm hatalar genelleştiriliyor
Hangi hata olduğunu kullanıcıya bildiriyor ama çözüm yolu göstermiyor
Tüm hatalar Exception ile yakalanıyor, spesifik hata tipleri ayrılmıyor
Öneri:

python
Copy
except sqlite3.IntegrityError as e:
    messagebox.showerror("Hata", f"'{kurum_adi}' adında bir banka kurumu zaten mevcut.", parent=self)
    if conn: conn.rollback()
except sqlite3.OperationalError as e:
    messagebox.showerror("Veritabanı Hatası", f"Veritabanı hatası: {e}", parent=self)
    if conn: conn.rollback()
except Exception as e:
    messagebox.showerror("Bilinmeyen Hata", f"Beklenmedik bir hata oluştu: {e}", parent=self)
    if conn: conn.rollback()
finally:
    if conn: conn.close()
📊 Özet ve Önceliklendirme
Öncelik	Sorun	Konum	Risk Seviyesi
🔴 Kritik	SQL Injection	services.py	Yüksek
🔴 Kritik	Floating Point Hatası	Tüm formlar	Orta-Yüksek
🟠 Yüksek	Bakiye Hesaplama Hatası	hesap_ekstresi_view.py	Orta
🟠 Yüksek	Transaction Yönetimi	services.py	Orta
🟠 Yüksek	Fiş No Tekrarı	db.py + services.py	Orta
🟡 Orta	KDV Raporu Hatası	kdv_raporu_view.py	Orta
🟡 Orta	Kod Tekrarı	Tüm modüller	Düşük
🟡 Orta	Hata Yönetimi	dialogs.py	Düşük
🛠️ Önerilen Düzeltme Öncelik Sırası
SQL Injection → Hemen düzelt (güvenlik açığı)
Floating Point Hatası → Tutar tutarsızlığını önler
Bakiye Hesaplama → Raporlar yanlış sonuç verir
Transaction Yönetimi → Veri bütünlüğü riski
Fiş No Kontrolü → Tekrar fiş numarası sorunu
Diğer sorunlar → Kod kalitesi için
📝 Özet
Projenizde 1 kritik SQL injection güvenlik açığı, floating point hesaplama hataları, bakiye hesaplama mantığı hataları ve transaction yönetimi eksiklikleri bulunmaktadır. Özellikle KDV hesaplamalarında nokta hassasiyeti sorunları nedeniyle tutar tutarsızlıkları oluşabilir.

En acil yapılması gerekenler:

SQL injection açığını kapat
KDV hesaplamalarını Decimal ile düzelt
Hesap ekstresi bakiye hesaplamasını düzelt
Bu sorunlar düzeltilirse uygulama daha güvenli ve tutarlı olacaktır.