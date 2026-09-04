import sqlite3
import os

# Veritabanı yolunu bu dosyanın bulunduğu konuma göre ayarla
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_YOLU = os.path.join(BASE_DIR, "on_muhasebe.db")


def veritabani_baglan():
    """Veritabanına bağlanır ve bağlantı nesnesini döndürür."""
    conn = sqlite3.connect(DB_YOLU)
    # Foreign key yürütmeyi aç: ON DELETE CASCADE gibi kuralların çalışması için gerekli.
    # SQLite'da varsayılan olarak kapalıdır; kapalıyken ana fiş silindiğinde
    # fis_satirlari satırları yetim (orphan) kalır.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def tablolari_olustur():
    """
    Uygulamanın v2 mimarisi için gerekli tüm tabloları kurar.
    Geliştirme aşaması sonrası temiz şema — ALTER TABLE / migrasyon içermez.
    """
    conn = veritabani_baglan()
    cursor = conn.cursor()

    # --- TANIMLAMA TABLOLARI ---
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
            grup_id INTEGER,
            firma_id INTEGER DEFAULT 1,
            durum INTEGER DEFAULT 1
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hizmet_kartlari_gruplari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grup_adi TEXT NOT NULL,
            tur TEXT NOT NULL DEFAULT 'Gider',
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

    # --- FİŞLER TABLOSU ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            fis_turu TEXT NOT NULL,
            fis_no TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            cari_id INTEGER,
            kaynak_modul TEXT,
            kaynak_fis_id INTEGER,
            toplam_tutar REAL DEFAULT 0,
            durum INTEGER DEFAULT 1,
            firma_id INTEGER NOT NULL,
            yil INTEGER NOT NULL
        )
        """
    )

    # --- FİŞ SATIRLARI TABLOSU ---
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
            firma_id INTEGER NOT NULL,
            FOREIGN KEY (fis_id) REFERENCES fisler(id) ON DELETE CASCADE
        )
        """
    )

    # --- ÇEK/SENET TABLOLARI ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cekler_senetler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seri_no TEXT UNIQUE NOT NULL,
            turu TEXT NOT NULL,
            banka TEXT,
            banka_id INTEGER,
            vade_tarihi TEXT NOT NULL,
            tutar REAL NOT NULL,
            kesideci TEXT DEFAULT '',
            ciranta TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            firma_id INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (banka_id) REFERENCES banka_kurumlari(id)
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
            fis_id INTEGER,
            aciklama TEXT,
            firma_id INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cek_senet_id) REFERENCES cekler_senetler(id)
        )
        """
    )

    # --- PERFORMANS İNDEKSLERİ ---
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fis_satirlari_hesap ON fis_satirlari (hesap_turu, hesap_id, firma_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fisler_firma_tarih ON fisler (firma_id, tarih);
    """)
    # C19: sıcak yollar — fiş→satır silme/güncelleme/cascade, kaynak fiş araması,
    # çek/senet hareket sorguları, genel tanımlar lookup'ları
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fis_satirlari_fis ON fis_satirlari (fis_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fisler_kaynak ON fisler (kaynak_fis_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_csh_fis ON cek_senet_hareketleri (fis_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_csh_cek_senet ON cek_senet_hareketleri (cek_senet_id, islem_tarihi);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_genel_tanimlar_grup ON genel_tanimlar (grup, firma_id);
    """)

    # --- C7: Fiş no tekilliği DB düzeyinde (uygulama politikasıyla aynı granülerlik:
    # aynı no, aynı firma+yıl+tarih içinde tekrar edemez; farklı tarih serbest).
    # Boş fis_no kapsamdışı (3700+ fişte no yok). Mevcut veride ihlal yoksa oluşturulur;
    # varsa (ör. aynı no aynı gün çift kaydedilmişse) uyarı verilir ve atlanır —
    # startup'ı kırmamak için.
    ihlal = cursor.execute(
        """
        SELECT fis_no, firma_id, yil, tarih, COUNT(*) FROM fisler
        WHERE fis_no <> '' GROUP BY fis_no, firma_id, yil, tarih HAVING COUNT(*) > 1 LIMIT 1
        """
    ).fetchone()
    if ihlal:
        print(f"[UYARI] fiş no tekrarı nedeniyle DB UNIQUE atlandı: {ihlal}")
    else:
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_fisler_no_tarih
            ON fisler (fis_no, firma_id, yil, tarih) WHERE fis_no <> '';
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

    # --- HİZMET KARTI GRUPLARI: varsayılan "Diğer" grupları ---
    cursor.execute("SELECT id FROM firmalar")
    firma_ids = [row[0] for row in cursor.fetchall()]
    for fid in firma_ids:
        for tur in ("Gider", "Gelir"):
            cursor.execute(
                "INSERT OR IGNORE INTO hizmet_kartlari_gruplari (grup_adi, tur, firma_id, durum) VALUES (?, ?, ?, 1)",
                ("Diğer", tur, fid),
            )

        # KDV grubu ve varsayılan KDV hesapları (191 İndirilecek KDV, 391 Hesaplanan KDV)
        cursor.execute(
            "INSERT OR IGNORE INTO hizmet_kartlari_gruplari (grup_adi, tur, firma_id, durum) VALUES (?, ?, ?, 1)",
            ("KDV", "KDV", fid),
        )
        # KDV grubunun ID'sini al
        cursor.execute("SELECT id FROM hizmet_kartlari_gruplari WHERE grup_adi='KDV' AND tur='KDV' AND firma_id=?", (fid,))
        kdv_grup = cursor.fetchone()
        kdv_grup_id = kdv_grup[0] if kdv_grup else None
        # 191 İndirilecek KDV
        if kdv_grup_id:
            for kdv_kart in [
                ("191 İndirilecek KDV", "KDV", 0, kdv_grup_id, fid),
                ("391 Hesaplanan KDV", "KDV", 0, kdv_grup_id, fid),
            ]:
                cursor.execute(
                    "SELECT id FROM hizmet_kartlari WHERE firma_id=? AND kart_adi=? AND tur='KDV'",
                    (fid, kdv_kart[0]),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO hizmet_kartlari (kart_adi, tur, kdv_oran, grup_id, firma_id, durum) VALUES (?, ?, ?, ?, ?, 1)",
                        kdv_kart,
                    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("Veritabanı dosyası siliniyor (varsa)...")
    if os.path.exists(DB_YOLU):
        os.remove(DB_YOLU)
    print("Yeni v2 şemasıyla veritabanı oluşturuluyor...")
    tablolari_olustur()
    print(f"Veritabanı '{DB_YOLU}' konumunda başarıyla oluşturuldu.")
