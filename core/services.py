import sqlite3
from datetime import datetime
import re

def fis_no_kontrol(cursor, fis_no, firma_id, yil, fis_id=None, tarih=None):
    """
    Fiş numarasının aynı firma, yıl ve (verilmişse) tarih içinde benzersiz olup
    olmadığını kontrol eder.
    Aynı fiş numarası farklı tarihlerde kullanılabilir (ör. aynı fatura no farklı
    tarihlerde tekrarlanabilir); yalnızca aynı tarih içinde tekrar engellenir.
    Boş fis_no'ya izin verilir (kontrol yapılmaz).
    Dönüş: benzersiz ise True, kullanımda ise False.
    """
    if not fis_no:
        return True
    query = """
        SELECT COUNT(*) FROM fisler
        WHERE fis_no = ? AND firma_id = ? AND yil = ?
          AND id != COALESCE(?, -1)
    """
    params = [fis_no, firma_id, yil, fis_id]
    if tarih:
        query += " AND tarih = ?"
        params.append(tarih)
    cursor.execute(query, params)
    return cursor.fetchone()[0] == 0


def _denge_kontrolu(fis_satirlari):
    """
    Cari karşılığı olan fişlarda borç=alacak dengesi zorunlu (K2).
    Cari satırı içermeyen fişler (peşin fatura/tahsilat/ödeme, virman, açılış)
    tasarım gereği tek taraflıdır; kontrol dışıdır.
    Tolerans 0,01 TL (float biriktirme payı).
    """
    if not any(s.get('hesap_turu') == 'Cari' for s in fis_satirlari):
        return
    fark = sum(float(s.get('borc') or 0) for s in fis_satirlari) \
         - sum(float(s.get('alacak') or 0) for s in fis_satirlari)
    if abs(fark) > 0.01:
        raise ValueError(
            f"Fiş dengeli değil: borç-alacak farkı {fark:+,.2f} TL. "
            "Lütfen satır tutarlarını kontrol edin."
        )


def fis_kaydet(cursor, fis_baslik, fis_satirlari, pesin_odeme_data=None, kaynak_modul=None):
    """
    Yeni bir fişi (başlık ve satırlar) ve varsa peşin ödeme fişini veritabanına kaydeder.
    Tüm işlemler tek bir transaction içinde yapılır.
    """
    # Dengesiz fiş hiçbir yazım yapılmadan reddedilir (K2)
    _denge_kontrolu(fis_satirlari)

    # Aynı firma, yıl ve tarih içinde fiş numarası tekrarı olmamalı
    fis_no = str(fis_baslik.get('fis_no') or '').strip()
    if fis_no and not fis_no_kontrol(cursor, fis_no, fis_baslik['firma_id'], fis_baslik['yil'], tarih=fis_baslik.get('tarih')):
        raise ValueError(f"'{fis_no}' fiş numarası bu firma, yıl ve tarih için zaten kullanılıyor.")

    # 1. Ana Fiş başlığını 'fisler' tablosuna ekle
    cursor.execute(
        """
        INSERT INTO fisler (tarih, fis_turu, fis_no, aciklama, cari_id, toplam_tutar, firma_id, yil)
        VALUES (:tarih, :fis_turu, :fis_no, :aciklama, :cari_id, :toplam_tutar, :firma_id, :yil)
        """,
        fis_baslik
    )
    yeni_fis_id = cursor.lastrowid

    # Kaynak modülü ana fişe ekle (eğer belirtilmişse)
    if kaynak_modul:
        cursor.execute("UPDATE fisler SET kaynak_modul = ? WHERE id = ?", (kaynak_modul, yeni_fis_id))

    # 2. Ana Fiş satırlarını 'fis_satirlari' tablosuna ekle
    for satir in fis_satirlari:
        satir['fis_id'] = yeni_fis_id
        satir['firma_id'] = fis_baslik['firma_id']
        cursor.execute(
            """
            INSERT INTO fis_satirlari (fis_id, hesap_turu, hesap_id, borc, alacak, aciklama, miktar, birim_fiyat, kdv_oran, firma_id)
            VALUES (:fis_id, :hesap_turu, :hesap_id, :borc, :alacak, :aciklama, :miktar, :birim_fiyat, :kdv_oran, :firma_id)
            """,
            satir
        )
    
    # 3. Varsa Peşin Ödeme Fişini kaydet
    if pesin_odeme_data:
        pesin_odeme_data['kaynak_fis_id'] = yeni_fis_id # Ana faturayı referans göster
        cursor.execute(
            """
            INSERT INTO fisler (tarih, fis_turu, toplam_tutar, firma_id, yil, kaynak_fis_id, kaynak_modul, aciklama)
            VALUES (:tarih, :fis_turu, :toplam_tutar, :firma_id, :yil, :kaynak_fis_id, :kaynak_modul, :aciklama)
            """,
            pesin_odeme_data
        )
        odeme_fis_id = cursor.lastrowid
        for satir in pesin_odeme_data['satirlar']:
            satir['fis_id'] = odeme_fis_id
            satir['firma_id'] = fis_baslik['firma_id']
            cursor.execute(
                """
                INSERT INTO fis_satirlari (fis_id, hesap_turu, hesap_id, borc, alacak, aciklama, firma_id)
                VALUES (:fis_id, :hesap_turu, :hesap_id, :borc, :alacak, :aciklama, :firma_id)
                """,
                satir
            )

    return yeni_fis_id

def fis_guncelle(cursor, fis_id, fis_baslik, fis_satirlari, pesin_odeme_data=None, kaynak_modul=None):
    """
    Mevcut bir fişi (başlık ve satırlar) ve varsa peşin ödeme fişini günceller.
    """
    # Dengesiz fiş hiçbir yazım/silme yapılmadan reddedilir (K2)
    _denge_kontrolu(fis_satirlari)

    # Aynı firma, yıl ve tarih içinde fiş numarası tekrarı olmamalı (kendi fişi hariç)
    fis_no = str(fis_baslik.get('fis_no') or '').strip()
    if fis_no and not fis_no_kontrol(cursor, fis_no, fis_baslik['firma_id'], fis_baslik['yil'], fis_id=fis_id, tarih=fis_baslik.get('tarih')):
        raise ValueError(f"'{fis_no}' fiş numarası bu firma, yıl ve tarih için zaten kullanılıyor.")

    # 1. Ana Fiş başlığını güncelle
    fis_baslik['id'] = fis_id
    fis_baslik['kaynak_modul'] = kaynak_modul # Ensure kaynak_modul is in fis_baslik for the UPDATE statement
    cursor.execute(
        """
        UPDATE fisler SET tarih=:tarih, fis_turu=:fis_turu, fis_no=:fis_no, aciklama=:aciklama,
        cari_id=:cari_id, toplam_tutar=:toplam_tutar, kaynak_modul=:kaynak_modul, yil=:yil
        WHERE id=:id AND firma_id=:firma_id
        """,
        fis_baslik
    )
    # C6: başlık firma uyuşmazlığı/uyuşmazsa hiçbir satıra dokunmadan iptal
    # (eskiden başlık dururken satırlar siliniyordu — kısmi düzenleme kapısı)
    if cursor.rowcount == 0:
        raise ValueError("Fiş bulunamadı (firma uyumsuzluğu) — güncelleme iptal edildi.")

    # 2. Ana Fişin eski satırlarını temizle (firma kapsamlı)
    cursor.execute("DELETE FROM fis_satirlari WHERE fis_id = ? AND firma_id = ?", (fis_id, fis_baslik['firma_id']))

    # 3. Yeni/güncel ana fiş satırlarını ekle
    for satir in fis_satirlari:
        satir['fis_id'] = fis_id
        satir['firma_id'] = fis_baslik['firma_id']
        cursor.execute(
            """
            INSERT INTO fis_satirlari (fis_id, hesap_turu, hesap_id, borc, alacak, aciklama, miktar, birim_fiyat, kdv_oran, firma_id)
            VALUES (:fis_id, :hesap_turu, :hesap_id, :borc, :alacak, :aciklama, :miktar, :birim_fiyat, :kdv_oran, :firma_id)
            """,
            satir
        )

    # 4. Eski peşin ödeme fişini sil (önce satırları ve C18 hareket kayıtları)
    cursor.execute("SELECT id FROM fisler WHERE kaynak_fis_id = ? AND firma_id = ?", (fis_id, fis_baslik['firma_id']))
    eski_ids = [r[0] for r in cursor.fetchall()]
    for eski_fis_id in eski_ids:
        cursor.execute("DELETE FROM fis_satirlari WHERE fis_id = ? AND firma_id = ?", (eski_fis_id, fis_baslik['firma_id']))
        cursor.execute("DELETE FROM cek_senet_hareketleri WHERE fis_id = ?", (eski_fis_id,))
    cursor.execute("DELETE FROM fisler WHERE kaynak_fis_id = ? AND firma_id = ?", (fis_id, fis_baslik['firma_id']))

    # 5. Yeni peşin ödeme fişini kaydet (varsa)
    if pesin_odeme_data:
        pesin_odeme_data['kaynak_fis_id'] = fis_id # Ana faturayı referans göster
        cursor.execute(
            """
            INSERT INTO fisler (tarih, fis_turu, toplam_tutar, firma_id, yil, kaynak_fis_id, kaynak_modul, aciklama)
            VALUES (:tarih, :fis_turu, :toplam_tutar, :firma_id, :yil, :kaynak_fis_id, :kaynak_modul, :aciklama)
            """,
            pesin_odeme_data
        )
        odeme_fis_id = cursor.lastrowid
        for satir in pesin_odeme_data['satirlar']:
            satir['fis_id'] = odeme_fis_id
            satir['firma_id'] = pesin_odeme_data['firma_id']
            cursor.execute(
                """
                INSERT INTO fis_satirlari (fis_id, hesap_turu, hesap_id, borc, alacak, aciklama, firma_id)
                VALUES (:fis_id, :hesap_turu, :hesap_id, :borc, :alacak, :aciklama, :firma_id)
                """,
                satir
            )


def fis_sil(cursor, fis_id, firma_id):
    """
    Verilen ID'ye sahip fişi, ona bağlı tüm fiş satırlarını ve
    varsa ona bağlı peşin ödeme fişini siler.
    """
    if not fis_id:
        raise ValueError("Silinecek fiş ID'si belirtilmedi.")

    # Fişe bağlı peşin ödeme/tahsilat fişi var mı kontrol et
    cursor.execute("SELECT id FROM fisler WHERE kaynak_fis_id = ? AND firma_id = ?", (fis_id, firma_id))
    bagli_fis = cursor.fetchone()

    # Satırları önce açıkça sil (PRAGMA foreign_keys kapalı olsa bile yetim satır kalmasın)
    cursor.execute("DELETE FROM fis_satirlari WHERE fis_id = ? AND firma_id = ?", (fis_id, firma_id))
    if bagli_fis:
        cursor.execute(
            "DELETE FROM fis_satirlari WHERE fis_id = ? AND firma_id = ?",
            (bagli_fis[0], firma_id),
        )

    # C18: fişin ürettiği çek/senet hareket kayıtları da silinir — aksi halde
    # fis_id sarkan yetim hareket, durum zincirini (güncel durum / son hareket
    # sorguları) sessizce bozar. Çek/Senet modülü kendi yolunu (cek_senet_fis_sil)
    # kullanır; bu genel silme yolunun güvence katmanıdır.
    silinecek_fis_ids = [fis_id] + ([bagli_fis[0]] if bagli_fis else [])
    cursor.executemany(
        "DELETE FROM cek_senet_hareketleri WHERE fis_id = ?",
        [(fid,) for fid in silinecek_fis_ids],
    )

    # Ana fişi sil
    cursor.execute("DELETE FROM fisler WHERE id = ? AND firma_id = ?", (fis_id, firma_id))

    # Eğer bağlı bir fiş varsa, onu da sil
    if bagli_fis:
        bagli_fis_id = bagli_fis[0]
        cursor.execute("DELETE FROM fisler WHERE id = ? AND firma_id = ?", (bagli_fis_id, firma_id))


# Tanım kartı işlemlerinde kullanılmasına izin verilen tablolar (SQL enjeksiyonuna karşı whitelist)
GECERLI_KART_TABLOLARI = {
    "cariler", "stoklar", "kasalar", "banka_hesaplari",
    "hizmet_kartlari", "genel_tanimlar", "banka_kurumlari",
    "hizmet_kartlari_gruplari",
}

def is_kart_kullanilmis_mi(cursor, tablo_adi, kart_id, firma_id):
    """
    Bir tanım kartının herhangi bir fişte, fiş satırında veya yapısal olarak
    başka bir tanımda (alt kategori gibi) kullanılıp kullanılmadığını kontrol eder.
    """
    if tablo_adi not in GECERLI_KART_TABLOLARI:
        raise ValueError(f"Geçersiz veya izin verilmeyen tablo adı: {tablo_adi}")

    # 1. Yapısal Bağımlılık Kontrolü (Parent-child ilişkileri)
    # Bir banka kurumu, altında hesap kartları varken silinemez.
    if tablo_adi == "banka_kurumlari":
        cursor.execute("SELECT 1 FROM banka_hesaplari WHERE kurum_id = ? AND firma_id = ? LIMIT 1", (kart_id, firma_id))
        if cursor.fetchone():
            raise ValueError("Bu banka kurumuna ait hesap kartları bulunmaktadır. Önce ilgili hesap kartlarını silmelisiniz.")

    # 2. Fiş ve Fiş Satırlarında Kullanım Kontrolü
    hesap_turu_map = {
        "stoklar": "Stok",
        "cariler": "Cari",
        "kasalar": "Kasa",
        "hizmet_kartlari": "Hizmet",
        "banka_hesaplari": "Banka"
    }

    # Bir cari, herhangi bir fişin başlığında kullanılmışsa silinemez.
    if tablo_adi == "cariler":
        cursor.execute("SELECT 1 FROM fisler WHERE cari_id = ? AND firma_id = ? LIMIT 1", (kart_id, firma_id))
        if cursor.fetchone():
            return True

    hesap_turu = hesap_turu_map.get(tablo_adi)
    if not hesap_turu:
        return False # Hareket görmeyen kart türleri için (örn: banka_kurumlari bu adıma gelirse)
        
    query = "SELECT 1 FROM fis_satirlari WHERE hesap_turu=? AND hesap_id=? AND firma_id=? LIMIT 1"
    cursor.execute(query, (hesap_turu, kart_id, firma_id))
    return cursor.fetchone() is not None

def kart_sil(cursor, tablo_adi, kart_id, firma_id):
    """
    Verilen ID'ye sahip tanım kartını siler.
    İşlemlerde kullanılıp kullanılmadığını kontrol eder.
    """
    if tablo_adi not in GECERLI_KART_TABLOLARI:
        raise ValueError(f"Geçersiz veya izin verilmeyen tablo adı: {tablo_adi}")

    if is_kart_kullanilmis_mi(cursor, tablo_adi, kart_id, firma_id):
        raise ValueError(f"Bu kart işlemlerde kullanıldığı için silinemez.")

    cursor.execute(f"DELETE FROM {tablo_adi} WHERE id = ? AND firma_id = ?", (kart_id, firma_id))
    if cursor.rowcount == 0:
        raise ValueError("Silinecek kart bulunamadı veya silme yetkiniz yok.")

def kaydet_kart(cursor, tablo_adi, veri_sozlugu):
    """
    Yeni bir tanım kartı ekler veya mevcut olanı günceller.
    'id' anahtarı varsa UPDATE, yoksa INSERT yapar.
    """
    if tablo_adi not in GECERLI_KART_TABLOLARI:
        raise ValueError(f"Geçersiz veya izin verilmeyen tablo adı: {tablo_adi}")

    veri = veri_sozlugu.copy()
    kart_id = veri.pop('id', None)
    
    if kart_id: # UPDATE
        if not veri: # Güncellenecek veri yoksa
            return kart_id
        columns = ", ".join([f"{key} = ?" for key in veri.keys()])
        params = list(veri.values()) + [kart_id]
        cursor.execute(f"UPDATE {tablo_adi} SET {columns} WHERE id = ?", params)
        return kart_id
    else: # INSERT
        # Stok kodu boşsa otomatik oluştur
        if tablo_adi == 'stoklar' and not veri.get('stok_kodu'):
            stok_adi = veri.get('stok_adi', '')
            slug = re.sub(r'[^\w-]', '', stok_adi.lower().replace(' ', '-'))
            veri['stok_kodu'] = slug if slug else 'stok-kodu'

        columns = ", ".join(veri.keys())
        placeholders = ", ".join(["?"] * len(veri))
        params = list(veri.values())
        cursor.execute(f"INSERT INTO {tablo_adi} ({columns}) VALUES ({placeholders})", params)
        return cursor.lastrowid



# ---------------------------------------------------------------- Stok yardımcıları
def stok_bakiye_ve_maliyet(cursor, firma_id):
    """
    Firmanın stok kartları için mevcut miktar (bakiye) ve FIFO kalan maliyet
    değerlerini hesaplar.

    Dönüş: (bakiyeler, maliyetler) — her ikisi de {stok_id: değer} sözlüğü.

    NOT: fis_satirlari üzerinde tam tarama + Python'da FIFO döngüsü gerektirir.
    Bu yüzden yalnızca bu verilere gerçekten ihtiyaç duyan raporlarda
    kullanılmalı; tanım listelerinde (stok kartları) çalıştırılmamalıdır.
    """
    # 1. Bakiyeler: borç stok giriş, alacak stok çıkış sayılır
    cursor.execute("""
        SELECT hesap_id,
               SUM(CASE WHEN borc > 0 THEN miktar WHEN alacak > 0 THEN -miktar ELSE 0 END)
        FROM fis_satirlari
        WHERE hesap_turu = 'Stok' AND firma_id = ?
        GROUP BY hesap_id
    """, (firma_id,))
    bakiyeler = {row[0]: row[1] or 0.0 for row in cursor.fetchall()}

    # 2. FIFO kalan maliyet: en yeni alışlardan başlayarak kalan miktarı doldur
    cursor.execute("""
        SELECT fs.hesap_id, fs.miktar, fs.birim_fiyat
        FROM fis_satirlari fs
        JOIN fisler f ON f.id = fs.fis_id
        WHERE fs.hesap_turu = 'Stok' AND fs.borc > 0 AND fs.firma_id = ?
        ORDER BY f.tarih DESC, f.id DESC
    """, (firma_id,))
    maliyetler = {stok_id: 0.0 for stok_id in bakiyeler}
    kalan_miktarlar = bakiyeler.copy()
    for stok_id, miktar, birim_fiyat in cursor.fetchall():
        if kalan_miktarlar.get(stok_id, 0) > 0:
            kullanilacak = min(kalan_miktarlar[stok_id], miktar)
            maliyetler[stok_id] += kullanilacak * (birim_fiyat or 0)
            kalan_miktarlar[stok_id] -= kullanilacak

    return bakiyeler, maliyetler


# ------------------------------------------------- Stok rapor yardımcıları
# Fiş türü sabitleri: stok hareketlerinin sınıflandırmasında kullanılır.
STOK_SATIS_TURU = "Satış Faturası"
STOK_SATIS_IADE_TURU = "Satış İade Faturası"
STOK_ALIS_TURU = "Alış Faturası"
STOK_ALIS_IADE_TURU = "Alış İade Faturası"
STOK_FIRE_TURU = "Fire Fişi"

# stok_donem_ozeti dönüş sözlüğündeki anahtarlar (varsayılan 0.0 için kullanılır)
STOK_OZET_ALANLARI = (
    "hareket_sayisi", "son_hareket_tarihi",
    "alis_miktar", "alis_tutar",
    "satis_miktar", "satis_tutar",
    "satis_iade_miktar", "satis_iade_tutar",
    "alis_iade_miktar", "alis_iade_tutar",
    "fire_miktar", "diger_giris_miktar", "diger_cikis_miktar",
    "giris_miktar", "cikis_miktar", "islem_tutar",
)


def stok_donem_ozeti(cursor, firma_id, bas_tarih=None, bit_tarih=None):
    """
    Stok kartlarının dönem bazlı hareket özeti (raporlar için ortak sorgu).

    Dönüş: {stok_id: {alan: değer}} — alanlar STOK_OZET_ALANLARI içindedir.
    bas_tarih veya bit_tarih None verilirse o uçtan filtre uygulanmaz (tüm dönem).

    Tutarlar KDV hariç, miktar × birim_fiyat üzerinden hesaplanır
    (miktar elle düzeltildiğinde raporun da güncel kalması için).
    """
    sartlar = ["fs.hesap_turu = 'Stok'", "fs.firma_id = ?"]
    params = [firma_id]
    if bas_tarih:
        sartlar.append("f.tarih >= ?")
        params.append(bas_tarih)
    if bit_tarih:
        sartlar.append("f.tarih <= ?")
        params.append(bit_tarih)

    cursor.execute(f"""
        SELECT fs.hesap_id,
               COUNT(*),
               MAX(f.tarih),
               SUM(CASE WHEN f.fis_turu = '{STOK_ALIS_TURU}' THEN fs.miktar * fs.birim_fiyat ELSE 0 END),
               SUM(CASE WHEN f.fis_turu = '{STOK_SATIS_TURU}' THEN fs.miktar ELSE 0 END),
               SUM(CASE WHEN f.fis_turu = '{STOK_SATIS_TURU}' THEN fs.miktar * fs.birim_fiyat ELSE 0 END),
               SUM(CASE WHEN f.fis_turu = '{STOK_SATIS_IADE_TURU}' THEN fs.miktar ELSE 0 END),
               SUM(CASE WHEN f.fis_turu = '{STOK_SATIS_IADE_TURU}' THEN fs.miktar * fs.birim_fiyat ELSE 0 END),
               SUM(CASE WHEN f.fis_turu = '{STOK_ALIS_IADE_TURU}' THEN fs.miktar ELSE 0 END),
               SUM(CASE WHEN f.fis_turu = '{STOK_FIRE_TURU}' THEN fs.miktar ELSE 0 END),
               SUM(CASE WHEN fs.borc > 0 AND f.fis_turu NOT IN ('{STOK_ALIS_TURU}', '{STOK_SATIS_IADE_TURU}')
                        THEN fs.miktar ELSE 0 END),
               SUM(CASE WHEN fs.alacak > 0 AND f.fis_turu NOT IN ('{STOK_SATIS_TURU}', '{STOK_ALIS_IADE_TURU}', '{STOK_FIRE_TURU}')
                        THEN fs.miktar ELSE 0 END),
               SUM(CASE WHEN fs.borc > 0 THEN fs.miktar ELSE 0 END),
               SUM(CASE WHEN fs.alacak > 0 THEN fs.miktar ELSE 0 END),
               SUM(fs.miktar * fs.birim_fiyat),
               SUM(CASE WHEN f.fis_turu = '{STOK_ALIS_TURU}' THEN fs.miktar ELSE 0 END)
        FROM fis_satirlari fs
        JOIN fisler f ON f.id = fs.fis_id
        WHERE {' AND '.join(sartlar)}
        GROUP BY fs.hesap_id
    """, params)

    ozet = {}
    for satir in cursor.fetchall():
        hesap_id = satir[0]
        ozet[hesap_id] = {
            "hareket_sayisi": satir[1] or 0,
            "son_hareket_tarihi": satir[2] or "",
            "alis_tutar": satir[3] or 0.0,
            "satis_miktar": satir[4] or 0.0,
            "satis_tutar": satir[5] or 0.0,
            "satis_iade_miktar": satir[6] or 0.0,
            "satis_iade_tutar": satir[7] or 0.0,
            "alis_iade_miktar": satir[8] or 0.0,
            "fire_miktar": satir[9] or 0.0,
            "diger_giris_miktar": satir[10] or 0.0,
            "diger_cikis_miktar": satir[11] or 0.0,
            "giris_miktar": satir[12] or 0.0,
            "cikis_miktar": satir[13] or 0.0,
            "islem_tutar": satir[14] or 0.0,
            "alis_miktar": satir[15] or 0.0,
        }
    return ozet


def stok_ozet_getir(ozet, stok_id):
    """Özet sözlüğünden kart verisini döndürür; hareket yoksa tüm alanlar 0."""
    veri = ozet.get(stok_id)
    if veri:
        return veri
    return {alan: ("" if alan == "son_hareket_tarihi" else 0.0) for alan in STOK_OZET_ALANLARI}


def stok_donem_cogs(cursor, firma_id, bas_tarih, bit_tarih, fis_turleri=(STOK_SATIS_TURU,)):
    """
    Dönem içindeki stok çıkışlarının FIFO maliyetini kart bazında hesaplar.

    Katmanlar dönem başından önceki hareketleri de içerir (tüm geçmiş yeniden
    oynatılır); yalnızca [bas_tarih, bit_tarih] aralığında ve fis_turleri ile
    eşleşen çıkışların maliyeti toplama eklenir.

    Dönüş: {stok_id: maliyet_toplamı}
    """
    cursor.execute("""
        SELECT f.tarih, f.fis_turu, fs.hesap_id, fs.miktar, fs.birim_fiyat, fs.borc, fs.alacak
        FROM fis_satirlari fs
        JOIN fisler f ON f.id = fs.fis_id
        WHERE fs.hesap_turu = 'Stok' AND fs.firma_id = ? AND f.tarih <= ?
        ORDER BY f.tarih, f.id
    """, (firma_id, bit_tarih))

    katmanlar = {}
    cogs = {}
    for tarih, fis_turu, hesap_id, miktar, birim_fiyat, borc, alacak in cursor.fetchall():
        katman = katmanlar.setdefault(hesap_id, [])
        if borc and borc > 0:
            katman.append([miktar or 0.0, birim_fiyat or 0.0])
        elif alacak and alacak > 0:
            maliyet = _fifo_tuket(katman, miktar or 0.0)
            if fis_turleri is None or fis_turu in fis_turleri:
                if not bas_tarih or tarih >= bas_tarih:
                    cogs[hesap_id] = cogs.get(hesap_id, 0.0) + maliyet
    return cogs


def _fifo_tuket(katmanlar, miktar):
    """FIFO kuyruğundan miktar kadar tüketir ve tüketilen maliyeti döndürür."""
    kalan = miktar
    toplam = 0.0
    while kalan > 0 and katmanlar:
        katman = katmanlar[0]
        kullanilacak = min(kalan, katman[0])
        toplam += kullanilacak * katman[1]
        katman[0] -= kullanilacak
        kalan -= kullanilacak
        if katman[0] <= 0:
            katmanlar.pop(0)
    return toplam


# ---------------------------------------------------------------- KDV yardımcılar
def aktif_yil_kontrolu(tarih_nesnesi, aktif_yil):
    """
    Fiş tarihinin yılının, seçili çalışma yılı ile aynı olup olmadığını kontrol eder.
    Uygun değilse açıklayıcı hata mesajı döndürür; uygunsa None döndürür.
    Amaç: 2025 yılında çalışırken yanlışlıkla 2026 tarihli fiş girilmesini engellemek
    (aksi halde fiş, 2025 kayıtlarından silinip dönem dışına taşınmış olur).
    """
    if tarih_nesnesi is None:
        return "Tarih seçilmedi."
    if tarih_nesnesi.year != aktif_yil:
        return (
            f"Girilen tarih ({tarih_nesnesi.strftime('%d.%m.%Y')}), seçili çalışma yılından "
            f"({aktif_yil}) farklı. Fiş, {aktif_yil} yılı kayıtlarından çıkar ve dönem dışında görünür. "
            f"Lütfen tarihi {aktif_yil} yılı içinden seçin."
        )
    return None


def kdv_hesap_idleri(cursor, firma_id):
    """
    Firma için tanımlı KDV hesaplarının ID'lerini döndürür.
    Dönüş: (indirilecek_kdv_id, hesaplanan_kdv_id)
    Bulunamazsa ilgili değer None olur.
    """
    cursor.execute(
        "SELECT kart_adi, id FROM hizmet_kartlari WHERE tur='KDV' AND durum=1 AND firma_id=?",
        (firma_id,),
    )
    kdv_hesaplar = {kart_adi: kart_id for kart_adi, kart_id in cursor.fetchall()}
    return kdv_hesaplar.get("191 İndirilecek KDV"), kdv_hesaplar.get("391 Hesaplanan KDV")


def kdv_satiri_olustur(kdv_hesap_id, kdv_tutar, yon, aciklama=""):
    """
    KDV için ayrı bir fiş satırı üretir.
    yon: 'borc' (İndirilecek KDV) veya 'alacak' (Hesaplanan KDV)
    """
    if not kdv_hesap_id or not kdv_tutar:
        return None
    return {
        "hesap_turu": "Hizmet",
        "hesap_id": kdv_hesap_id,
        "borc": kdv_tutar if yon == "borc" else 0,
        "alacak": 0 if yon == "borc" else kdv_tutar,
        "aciklama": aciklama or "KDV",
        "miktar": 1,
        "birim_fiyat": kdv_tutar,
        "kdv_oran": 0,
    }


# ---------------------------------------------------------------- Çek/Senet özel yardımcılar
def cek_senet_guncel_durum(cursor, cek_senet_id):
    """Bir çek/senedin en son hareketine göre güncel durumunu döndürür."""
    cursor.execute(
        "SELECT durum FROM cek_senet_hareketleri WHERE cek_senet_id = ? ORDER BY islem_tarihi DESC, id DESC LIMIT 1",
        (cek_senet_id,),
    )
    row = cursor.fetchone()
    return row[0] if row else "Portföyde"


def cek_senet_son_banka_takas(cursor, cek_senet_id):
    """Son 'Bankada Tahsilde' hareketindeki karşı banka hesap bilgisini döndürür."""
    cursor.execute(
        """
        SELECT karsi_hesap_id, karsi_hesap_ismi
        FROM cek_senet_hareketleri
        WHERE cek_senet_id = ? AND durum = 'Bankada Tahsilde'
        ORDER BY islem_tarihi DESC, id DESC LIMIT 1
        """,
        (cek_senet_id,),
    )
    return cursor.fetchone()


def cek_senet_fis_son_hareket_mi(cursor, fis_id):
    """
    Bir fişteki tüm çek/senet hareketlerinin, ilgili çek/senetlerin son hareketi
    olup olmadığını kontrol eder. Son hareket ise True döner.
    """
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM cek_senet_hareketleri h
        WHERE h.fis_id = ?
          AND h.id <> (SELECT h2.id FROM cek_senet_hareketleri h2 WHERE h2.cek_senet_id = h.cek_senet_id ORDER BY h2.islem_tarihi DESC, h2.id DESC LIMIT 1)
        """,
        (fis_id,),
    )
    row = cursor.fetchone()
    return row[0] == 0


def cek_senet_hareket_ekle(
    cursor,
    cek_senet_id,
    fis_id,
    islem_tarihi,
    durum,
    karsi_hesap_tipi=None,
    karsi_hesap_id=None,
    karsi_hesap_ismi=None,
    aciklama="",
    firma_id=1,
):
    """cek_senet_hareketleri tablosuna tek hareket ekler."""
    cursor.execute(
        """
        INSERT INTO cek_senet_hareketleri
            (cek_senet_id, fis_id, islem_tarihi, durum,
             karsi_hesap_tipi, karsi_hesap_id, karsi_hesap_ismi, aciklama, firma_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cek_senet_id,
            fis_id,
            islem_tarihi,
            durum,
            karsi_hesap_tipi,
            karsi_hesap_id,
            karsi_hesap_ismi,
            aciklama,
            firma_id,
        ),
    )


def cek_senet_fis_sil(cursor, fis_id, firma_id):
    """
    Çek/Senet modülündeki bir fişi siler.
    Önce o fişe bağlı çek/senet hareketlerini, ardından fişi ve satırlarını siler.
    Eğer Giriş fişi siliniyorsa ve oluşturulan çek/senet kartları başka hiçbir harekette
    kullanılmamışsa kartları da temizler.
    """
    # Bu fişe bağlı hareketleri bul
    cursor.execute("SELECT id, cek_senet_id FROM cek_senet_hareketleri WHERE fis_id = ?", (fis_id,))
    hareketler = cursor.fetchall()

    # Fişte CekSenet satırı olarak geçen kartları bul (Giriş fişi için)
    cursor.execute(
        "SELECT hesap_id FROM fis_satirlari WHERE fis_id = ? AND hesap_turu = 'CekSenet'",
        (fis_id,),
    )
    cek_senet_ids = [row[0] for row in cursor.fetchall()]

    # Hareketleri sil
    cursor.execute("DELETE FROM cek_senet_hareketleri WHERE fis_id = ?", (fis_id,))

    # Ana fişi ve satırlarını sil
    fis_sil(cursor, fis_id, firma_id)

    # Giriş fişinde oluşturulmuş kartları, başka hareketleri yoksa temizle
    if cek_senet_ids:
        for cek_senet_id in cek_senet_ids:
            cursor.execute(
                "SELECT COUNT(*) FROM cek_senet_hareketleri WHERE cek_senet_id = ?",
                (cek_senet_id,),
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute("DELETE FROM cekler_senetler WHERE id = ?", (cek_senet_id,))


# ---------------------------------------------------------------- Firma bazlı ayar deposu
# Ayarlar 'genel_tanimlar' tablosunda tutulur: grup=anahtar, deger=seçenek,
# firma_id ile firma bazlı ayrılır. Bu, "Eksi Çalışma" gibi anahtar/değer
# niteliğindeki tercihler için ortak bir okuma/yazma arayüzü sağlar.
def ayar_oku(cursor, firma_id, anahtar, varsayilan=None):
    """Firma bazlı bir ayar değeri okur; yoksa varsayilanı döndürür."""
    cursor.execute(
        "SELECT deger FROM genel_tanimlar WHERE grup = ? AND firma_id = ? LIMIT 1",
        (anahtar, firma_id),
    )
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else varsayilan


def ayar_yaz(cursor, firma_id, anahtar, deger):
    """Firma bazlı bir ayar değerini (varsa güncelleyerek) yazar."""
    cursor.execute(
        "SELECT id FROM genel_tanimlar WHERE grup = ? AND firma_id = ? LIMIT 1",
        (anahtar, firma_id),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE genel_tanimlar SET deger = ? WHERE id = ?", (deger, row[0])
        )
    else:
        cursor.execute(
            "INSERT INTO genel_tanimlar (grup, deger, firma_id) VALUES (?, ?, ?)",
            (anahtar, deger, firma_id),
        )


# ---------------------------------------------------------------- "Eksi Çalışma" politikaları
# Kasa/banka/stok bir fiş sonrası eksiye düştüğünde ne olacağını belirler.
# Muhasebe akışını kırmamak için varsayılan "uyar ama izin ver" davranışıdır.
EKSI_POLITIKA_SECENEKLERI = [
    ("İzin verme (kayıtı engelle)", "izin_verme"),
    ("Her seferinde uyar (yine de kaydet)", "her_seferinde_uyar"),
    ("Bir kere uyar (sonra sessiz kaydet)", "bir_kere_uyar"),
    ("Hiçbir şey yapma (sessiz kaydet)", "hicbir_sey_yapma"),
]
EKSI_POLITIKA_VARSAYILAN = "bir_kere_uyar"

# Stok eksiye düştüğünde çıkışın maliyeti fiyatlama olarak 0 kabul edilir
# (karşılıksız çıkış = maliyetsiz). Rapor/Düzeltilecekler bunu kırmızı işaretler.

# Ayar anahtarları
AYAR_EKSI_KASA = "eksi_kasa"
AYAR_EKSI_BANKA = "eksi_banka"
AYAR_EKSI_STOK = "eksi_stok"


# ---------------------------------------------------------------- "Eksiye düşme" tespiti
def _hesap_adi(cursor, hesap_turu, hesap_id):
    """Kasa/Banka/Stok kartının görünen adını döndürür (mesajlar için)."""
    tablo_kolon = {
        "Kasa": ("kasalar", "kasa_adi"),
        "Banka": ("banka_hesaplari", "hesap_adi"),
        "Stok": ("stoklar", "stok_adi"),
    }.get(hesap_turu)
    if not tablo_kolon:
        return f"{hesap_turu} #{hesap_id}"
    tablo, kolon = tablo_kolon
    cursor.execute(f"SELECT {kolon} FROM {tablo} WHERE id = ?", (hesap_id,))
    row = cursor.fetchone()
    return row[0] if row and row[0] else f"{hesap_turu} #{hesap_id}"


def eksi_dusme_kontrol(cursor, firma_id, fis_satirlari, guncellenen_fis_id=None):
    """
    Kaydedilecek/güncellenecek bir fişten sonra hangi hesapların eksiye
    düştüğünü belirler (fiş henüz yazılmamış olarak çağrılır).

    - Kasa / Banka: net bakiye = borç - alacak (₺). Sonuç < 0 → sorun.
    - Stok: net miktar = giriş(borç) - çıkış(alacak) (miktar). Sonuç < 0 → sorun.

    Güncellemede, kartın ESKİ hâli sayılmasın diye `guncellenen_fis_id` hariç
    tutulur. Dönüş: eksiye düşen hesapların listesi; her öğe
    {'tur','hesap_id','hesap_adi','deger','birim'}. Liste boşsa sorun yok.
    """
    para_turleri = {"Kasa", "Banka"}
    hedef_turleri = para_turleri | {"Stok"}

    # Fiş satırlarını (tur, hesap_id) bazında topla
    delta = {}
    for s in fis_satirlari:
        tur = s.get("hesap_turu")
        if tur not in hedef_turleri:
            continue
        hid = s.get("hesap_id")
        if hid is None:
            continue
        d = delta.setdefault((tur, hid), 0.0)
        if tur in para_turleri:
            delta[(tur, hid)] = d + float(s.get("borc") or 0) - float(s.get("alacak") or 0)
        else:  # Stok: miktar, yönlü
            miktar = float(s.get("miktar") or 0)
            if float(s.get("borc") or 0) > 0:
                delta[(tur, hid)] = d + miktar
            elif float(s.get("alacak") or 0) > 0:
                delta[(tur, hid)] = d - miktar

    if not delta:
        return []

    haric = " AND fis_id <> ?" if guncellenen_fis_id else ""
    ex_params = [guncellenen_fis_id] if guncellenen_fis_id else []

    offenders = []
    for (tur, hid), d in delta.items():
        if tur in para_turleri:
            cursor.execute(
                f"""SELECT COALESCE(SUM(borc - alacak), 0) FROM fis_satirlari
                    WHERE hesap_turu = ? AND hesap_id = ? AND firma_id = ?{haric}""",
                [tur, hid, firma_id] + ex_params,
            )
            bakiye = (cursor.fetchone()[0] or 0.0) + d
            deger, birim = bakiye, "₺"
        else:  # Stok
            cursor.execute(
                f"""SELECT COALESCE(SUM(CASE WHEN borc > 0 THEN miktar
                                             WHEN alacak > 0 THEN -miktar
                                             ELSE 0 END), 0)
                    FROM fis_satirlari
                    WHERE hesap_turu = 'Stok' AND hesap_id = ? AND firma_id = ?{haric}""",
                [hid, firma_id] + ex_params,
            )
            deger, birim = (cursor.fetchone()[0] or 0.0) + d, "adet"

        if deger < -0.01:
            offenders.append({
                "tur": tur,
                "hesap_id": hid,
                "hesap_adi": _hesap_adi(cursor, tur, hid),
                "deger": deger,
                "birim": birim,
            })
    return offenders


def _para_sorunlari(cursor, firma_id, hesap_turu, hesaplar, bas_tarih, bit_tarih):
    """Kasa/Banka hesapları için DÖNEM SONU bakiyesi eksi olan hesapları,
    hesap başına tek özet satırı olarak döndürür.
    (Satış/ödeme önce girilip sonra düzelmiş ara eksiler 'düzeltilmesi gereken'
    sayılmaz — kullanıcı kararı: yalnız dönem sonu eksi.)"""
    sonuc = []
    for hid, ad in hesaplar:
        cursor.execute(
            """SELECT f.tarih, f.id, fs.borc, fs.alacak
               FROM fis_satirlari fs JOIN fisler f ON f.id = fs.fis_id
               WHERE fs.hesap_turu=? AND fs.hesap_id=? AND fs.firma_id=?
               ORDER BY f.tarih, f.id""",
            (hesap_turu, hid, firma_id),
        )
        bakiye = 0.0
        eksi_satir = 0
        ilk_tarih = None
        ilk_fis = None
        for tarih, fis_id, borc, alacak in cursor.fetchall():
            delta = (borc or 0) - (alacak or 0)
            if tarih < bas_tarih:
                bakiye += delta
                continue
            if bit_tarih and tarih > bit_tarih:
                break
            bakiye += delta
            if bakiye < -0.01:
                eksi_satir += 1
                if ilk_tarih is None:
                    ilk_tarih, ilk_fis = tarih, fis_id
        if bakiye < -0.01:  # yalnız dönem sonu eksi
            sonuc.append({
                "tur": hesap_turu, "hesap_id": hid, "hesap_adi": ad,
                "ilk_tarih": ilk_tarih, "eksi_satir": eksi_satir,
                "donem_sonu": bakiye, "maliyetsiz": None,
                "birim": "₺", "ilk_fis_id": ilk_fis,
            })
    sonuc.sort(key=lambda r: (r["ilk_tarih"] or "", r["hesap_adi"]))
    return sonuc


def _stok_sorunlari(cursor, firma_id, bas_tarih, bit_tarih):
    """Stok kartları için, kart başına tek özet satırı. Bir kart 'sorunlu' sayılır
    eğer: (a) dönem sonu miktarı eksi (gerçek açık) VEYA (b) dönem içinde
    maliyetsiz satış var (satış, alıştan önce girildiği için 0 maliyetle hesaplandı
    — miktar sonradan düzeltilse bile Kar/Zarar maliyeti eksik kalır)."""
    cursor.execute(
        "SELECT id, stok_adi FROM stoklar WHERE durum=1 AND firma_id=?", (firma_id,)
    )
    kartlar = cursor.fetchall()
    sonuc = []
    for hid, ad in kartlar:
        cursor.execute(
            """SELECT f.tarih, f.id, fs.miktar, fs.borc, fs.alacak, fs.birim_fiyat
               FROM fis_satirlari fs JOIN fisler f ON f.id = fs.fis_id
               WHERE fs.hesap_turu='Stok' AND fs.hesap_id=? AND fs.firma_id=?
               ORDER BY f.tarih, f.id""",
            (hid, firma_id),
        )
        katmanlar = []          # FIFO: [kalan_miktar, birim_fiyat]
        kalan = 0.0             # dönem sonu/şu an net miktar
        eksi_satir = 0
        maliyetsiz = 0.0        # karşılıksız (0 maliyetle) satılan toplam miktar
        ilk_tarih = None
        ilk_fis = None
        for tarih, fis_id, miktar, borc, alacak, bf in cursor.fetchall():
            miktar = miktar or 0.0
            bf = bf or 0.0
            donem_icinde = bas_tarih <= tarih and not (bit_tarih and tarih > bit_tarih)
            if (borc or 0) > 0:
                delta = miktar
                katmanlar.append([miktar, bf])
            elif (alacak or 0) > 0:
                delta = -miktar
                # Her çıkış FIFO katmanlarını tüketir (devir dahil), gerçek COGS
                # motoru gibi. Yalnız dönem İÇİNDEKI karşılıksız çıkışlar
                # 'maliyetsiz' olarak sayılır.
                tuketilen = 0.0
                kalan_istek = miktar
                while kalan_istek > 0 and katmanlar:
                    k = katmanlar[0]
                    ku = min(kalan_istek, k[0])
                    k[0] -= ku
                    kalan_istek -= ku
                    tuketilen += ku
                    if k[0] <= 0:
                        katmanlar.pop(0)
                eksik = miktar - tuketilen
                if donem_icinde and eksik > 0.001:
                    maliyetsiz += eksik
                    if ilk_tarih is None:
                        ilk_tarih, ilk_fis = tarih, fis_id
            else:
                continue

            onceki_kalan = kalan
            kalan += delta
            if tarih < bas_tarih:
                continue
            if bit_tarih and tarih > bit_tarih:
                break
            if kalan < -0.01 and onceki_kalan >= -0.01:
                eksi_satir += 1
                if ilk_tarih is None:
                    ilk_tarih, ilk_fis = tarih, fis_id

        if kalan < -0.01 or maliyetsiz > 0.01:
            sonuc.append({
                "tur": "Stok", "hesap_id": hid, "hesap_adi": ad,
                "ilk_tarih": ilk_tarih, "eksi_satir": eksi_satir,
                "donem_sonu": kalan, "maliyetsiz": maliyetsiz,
                "birim": "adet", "ilk_fis_id": ilk_fis,
            })
    sonuc.sort(key=lambda r: (r["ilk_tarih"] or "", r["hesap_adi"]))
    return sonuc


def eksi_duzeltilecekler(cursor, firma_id, bas_tarih, bit_tarih=None):
    """'Düzeltilecekler' raporu: seçili dönemde sorunlu KASA/BANKA/STOK
    hesap/kartları — her biri için TEK özet satırı.
      • Kasa/Banka: dönem sonu bakiyesi eksi olan hesaplar.
      • Stok: dönem sonu miktarı eksi VEYA maliyetsiz satış içeren kartlar.
    Dönüş: {'Kasa':[...], 'Banka':[...], 'Stok':[...]}."""
    def _hesaplar(tablo, ad_kolon):
        cursor.execute(
            f"SELECT id, {ad_kolon} FROM {tablo} WHERE durum=1 AND firma_id=?",
            (firma_id,),
        )
        return cursor.fetchall()

    kasa = _para_sorunlari(
        cursor, firma_id, "Kasa", _hesaplar("kasalar", "kasa_adi"), bas_tarih, bit_tarih
    )
    banka = _para_sorunlari(
        cursor, firma_id, "Banka", _hesaplar("banka_hesaplari", "hesap_adi"), bas_tarih, bit_tarih
    )
    stok = _stok_sorunlari(cursor, firma_id, bas_tarih, bit_tarih)
    return {"Kasa": kasa, "Banka": banka, "Stok": stok}
