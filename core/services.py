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


def fis_kaydet(cursor, fis_baslik, fis_satirlari, pesin_odeme_data=None, kaynak_modul=None):
    """
    Yeni bir fişi (başlık ve satırlar) ve varsa peşin ödeme fişini veritabanına kaydeder.
    Tüm işlemler tek bir transaction içinde yapılır.
    """
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

    # 2. Ana Fişin eski satırlarını temizle
    cursor.execute("DELETE FROM fis_satirlari WHERE fis_id = ?", (fis_id,))

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

    # 4. Eski peşin ödeme fişini sil (önce satırlarını açıkça temizle)
    cursor.execute("SELECT id FROM fisler WHERE kaynak_fis_id = ?", (fis_id,))
    for eski_fis_id in [r[0] for r in cursor.fetchall()]:
        cursor.execute("DELETE FROM fis_satirlari WHERE fis_id = ?", (eski_fis_id,))
    cursor.execute("DELETE FROM fisler WHERE kaynak_fis_id = ?", (fis_id,))

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
        "SELECT durum FROM cek_senet_hareketleri WHERE cek_senet_id = ? ORDER BY id DESC LIMIT 1",
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
        ORDER BY id DESC LIMIT 1
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
          AND h.id < (SELECT MAX(id) FROM cek_senet_hareketleri WHERE cek_senet_id = h.cek_senet_id)
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
