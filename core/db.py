import sqlite3
import os

# GUVENLIK-03: Veritabanı yolunu programın çalıştığı dizine göre değil,
# bu dosyanın bulunduğu konuma göre ayarla.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_YOLU = os.path.join(BASE_DIR, "on_muhasebe.db")


def veritabani_baglan():
    """Veritabanına bağlanır ve bağlantı nesnesini döndürür."""
    conn = sqlite3.connect(DB_YOLU)
    return conn


def tablolari_olustur():
    """
    Uygulamanın v2 mimarisi için gerekli tüm tabloları kurar.
    Eski 'hareketler' ve 'hareket_baglantilari' tabloları yerine
    'fisler' ve 'fis_satirlari' tabloları kullanılır.
    """
    conn = veritabani_baglan()
    cursor = conn.cursor()

    # --- TANIMLAMA TABLOLARI (v1'den taşındı) ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stoklar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stok_kodu TEXT UNIQUE,
            stok_adi TEXT NOT NULL,
            kategori TEXT DEFAULT '',
            birim TEXT DEFAULT 'Adet',
            alis_fiyati REAL DEFAULT 0,
            kritik_miktar REAL DEFAULT 0,
            satis_fiyati REAL DEFAULT 0,
            kdv_oran REAL DEFAULT 20,
            firma_id INTEGER DEFAULT 1,
            durum INTEGER DEFAULT 1
        )
        """
    )
    # kdv_oran sütununu ekle (eğer yoksa)
    cursor.execute("PRAGMA table_info(stoklar)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'kdv_oran' not in columns:
        cursor.execute("ALTER TABLE stoklar ADD COLUMN kdv_oran REAL DEFAULT 20")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cariler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unvan TEXT NOT NULL,
            tur TEXT DEFAULT 'Müşteri',
            telefon TEXT,
            firma_id INTEGER DEFAULT 1,
            durum INTEGER DEFAULT 1
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS banka_kurumlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kurum_adi TEXT NOT NULL UNIQUE,
            firma_id INTEGER DEFAULT 1,
            durum INTEGER DEFAULT 1
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS banka_hesaplari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hesap_adi TEXT NOT NULL,
            kurum_id INTEGER,
            hesap_turu TEXT DEFAULT 'Vadesiz',
            iban TEXT,
            komisyon_orani REAL DEFAULT 0,
            firma_id INTEGER DEFAULT 1,
            durum INTEGER DEFAULT 1,
            FOREIGN KEY (kurum_id) REFERENCES banka_kurumlari (id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS kasalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kasa_adi TEXT NOT NULL,
            firma_id INTEGER DEFAULT 1,
            durum INTEGER DEFAULT 1
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hizmet_kartlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kart_adi TEXT NOT NULL,
            tur TEXT DEFAULT 'Gider',
            kdv_oran REAL DEFAULT 20,
            firma_id INTEGER DEFAULT 1,
            durum INTEGER DEFAULT 1
        )
        """
    )
    # kdv_oran sütununu ekle (eğer yoksa)
    cursor.execute("PRAGMA table_info(hizmet_kartlari)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'kdv_oran' not in columns:
        cursor.execute("ALTER TABLE hizmet_kartlari ADD COLUMN kdv_oran REAL DEFAULT 20")
    # grup_id sütununu ekle (eğer yoksa)
    if 'grup_id' not in columns:
        cursor.execute("ALTER TABLE hizmet_kartlari ADD COLUMN grup_id INTEGER")

    # Hizmet Kartları Grupları tablosu (mizan için ana hesap grubu)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hizmet_kartlari_gruplari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grup_adi TEXT NOT NULL,
            tur TEXT NOT NULL DEFAULT 'Gider',   -- 'Gider' / 'Gelir'
            firma_id INTEGER DEFAULT 1,
            durum INTEGER DEFAULT 1,
            UNIQUE(grup_adi, tur, firma_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS genel_tanimlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grup TEXT,
            deger TEXT,
            firma_id INTEGER DEFAULT 1
        )
        """
    )

    # 1. Fişler Tablosu (Eski 'hareketler' tablosunun sadeleştirilmiş hali)
    # Sadece işlemin başlık bilgilerini tutar.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            fis_turu TEXT NOT NULL,          -- 'Satış Faturası', 'Kasa Gider Fişi', 'Banka Transfer' vb.
            fis_no TEXT DEFAULT '',          -- Evrak No / Fatura No
            aciklama TEXT DEFAULT '',         -- Fiş geneli için kullanıcı açıklaması
            cari_id INTEGER,                 -- Faturanın ana carisi gibi, başlıkta tutulabilir (opsiyonel)
            kaynak_modul TEXT,               -- Fişin hangi modül tarafından oluşturulduğu (örn: 'Kasa', 'Fatura')
            kaynak_fis_id INTEGER,           -- Faturanın peşin ödeme fişini bağlamak için
            toplam_tutar REAL DEFAULT 0,
            durum INTEGER DEFAULT 1,         -- 1: Aktif, 0: İptal/Silinmiş
            firma_id INTEGER NOT NULL,
            yil INTEGER NOT NULL
        )
        """
    )
    # fisler tablosuna kaynak_modul sütununu ekle (eğer yoksa)
    cursor.execute("PRAGMA table_info(fisler)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'kaynak_modul' not in columns:
        cursor.execute("ALTER TABLE fisler ADD COLUMN kaynak_modul TEXT")
    # fisler tablosuna kaynak_fis_id sütununu ekle (eğer yoksa)
    cursor.execute("PRAGMA table_info(fisler)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'kaynak_fis_id' not in columns:
        cursor.execute("ALTER TABLE fisler ADD COLUMN kaynak_fis_id INTEGER")
    

    # 2. Fiş Satırları Tablosu (Eski 'hareket_baglantilari' tablosunun yeni hali)
    # Her fişin altındaki detay satırlarını (stok, masraf vb.) tutar.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fis_satirlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fis_id INTEGER NOT NULL,
            hesap_turu TEXT NOT NULL,
            hesap_id INTEGER NOT NULL,
            aciklama TEXT,
            miktar REAL DEFAULT 1,
            birim_fiyat REAL DEFAULT 0,
            borc REAL DEFAULT 0,
            alacak REAL DEFAULT 0,
            kdv_oran REAL DEFAULT 0,
            kdv_tutar REAL DEFAULT 0,
            firma_id INTEGER NOT NULL,
            FOREIGN KEY (fis_id) REFERENCES fisler(id) ON DELETE CASCADE
        )
        """
    )

    # --- ÇEK/SENET TABLOLARI (Değişiklik yok) ---
    # Bu tablolar v1 ile aynı kalacak.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cekler_senetler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seri_no TEXT UNIQUE NOT NULL,
            turu TEXT NOT NULL,
            banka TEXT,
            vade_tarihi TEXT NOT NULL,
            tutar REAL NOT NULL,
            firma_id INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cek_senet_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cek_senet_id INTEGER NOT NULL,
            islem_tarihi TEXT NOT NULL,
            durum TEXT NOT NULL,
            karsi_hesap_tipi TEXT,
            karsi_hesap_id INTEGER,
            karsi_hesap_ismi TEXT,
            ilgili_hareket_id INTEGER,
            aciklama TEXT,
            firma_id INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cek_senet_id) REFERENCES cekler_senetler(id)
        )
    """
    )

    # cekler_senetler tablosuna yeni alanları ekle (mevcut veritabanı için)
    cursor.execute("PRAGMA table_info(cekler_senetler)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'banka_id' not in columns:
        cursor.execute("ALTER TABLE cekler_senetler ADD COLUMN banka_id INTEGER")
    if 'kesideci' not in columns:
        cursor.execute("ALTER TABLE cekler_senetler ADD COLUMN kesideci TEXT DEFAULT ''")
    if 'ciranta' not in columns:
        cursor.execute("ALTER TABLE cekler_senetler ADD COLUMN ciranta TEXT DEFAULT ''")
    if 'aciklama' not in columns:
        cursor.execute("ALTER TABLE cekler_senetler ADD COLUMN aciklama TEXT DEFAULT ''")

    # cek_senet_hareketleri tablosuna fis_id alanını ekle (mevcut veritabanı için)
    cursor.execute("PRAGMA table_info(cek_senet_hareketleri)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'fis_id' not in columns:
        cursor.execute("ALTER TABLE cek_senet_hareketleri ADD COLUMN fis_id INTEGER")

    # --- PERFORMANS İYİLEŞTİRMESİ ---
    # Yeni yapıya uygun indexler
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fis_satirlari_hesap ON fis_satirlari (hesap_turu, hesap_id, firma_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fisler_firma_tarih ON fisler (firma_id, tarih);
    """)

    # --- FİRMALAR TABLOSU ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS firmalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma_adi TEXT NOT NULL UNIQUE,
            durum INTEGER DEFAULT 1
        )
        """
    )
    cursor.execute("INSERT OR IGNORE INTO firmalar (id, firma_adi, durum) VALUES (1, 'Ana Firma (Varsayılan)', 1)")

    # --- HİZMET KARTI GRUPLARI: her firma için "Diğer" gider/gelir grubu oluştur ---
    cursor.execute("SELECT id FROM firmalar")
    firma_ids = [row[0] for row in cursor.fetchall()]
    for fid in firma_ids:
        for tur in ("Gider", "Gelir"):
            cursor.execute(
                "INSERT OR IGNORE INTO hizmet_kartlari_gruplari (grup_adi, tur, firma_id, durum) VALUES (?, ?, ?, 1)",
                ("Diğer", tur, fid),
            )

    # Grubu atanmamış mevcut kartları kendi türündeki "Diğer" grubuna ata
    cursor.execute(
        """
        UPDATE hizmet_kartlari
        SET grup_id = (
            SELECT g.id FROM hizmet_kartlari_gruplari g
            WHERE g.grup_adi = 'Diğer' AND g.tur = hizmet_kartlari.tur
              AND g.firma_id = hizmet_kartlari.firma_id
        )
        WHERE grup_id IS NULL
        """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Bu dosya doğrudan çalıştırıldığında veritabanını sıfırdan oluşturur.
    print("Veritabanı dosyası siliniyor (varsa)...")
    if os.path.exists(DB_YOLU):
        os.remove(DB_YOLU)
    print("Yeni v2 şemasıyla veritabanı oluşturuluyor...")
    tablolari_olustur()
    print(f"Veritabanı '{DB_YOLU}' konumunda başarıyla oluşturuldu.")