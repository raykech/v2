import tkinter as tk
from core.db import veritabani_baglan
from utils.formatters import format_currency


class GirisDashboardView(tk.Frame):
    """Giriş sekmesi: 6 özet kart (Kasa, Banka Vadesiz, POS, Cari Alacak/Borç, Stok FIFO)."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.kartlar = {}
        self.create_widgets()
        self.yenile()

    def create_widgets(self):
        baslik = tk.Label(self, text="GENEL DURUM", font=("Arial", 15, "bold"), bg="#f5f7fb", fg="#333333")
        baslik.pack(anchor="w", padx=24, pady=(22, 8))

        kart_alani = tk.Frame(self, bg="#f5f7fb")
        kart_alani.pack(fill="both", expand=True, padx=16, pady=(0, 20))

        kartlar = [
            ("kasa",    "KASA TOPLAM BAKİYE",            "#198754"),
            ("banka",   "BANKA TOPLAM BAKİYE (Vadesiz)", "#0d6efd"),
            ("pos",     "POS TOPLAM ALACAK",             "#6f42c1"),
            ("alacak",  "TOPLAM ALACAK",                 "#fd7e14"),
            ("borc",    "TOPLAM BORÇ",                   "#dc3545"),
            ("stok",    "ELDEKİ STOK MALİYET (FIFO)",    "#20c997"),
        ]

        # 3 sütun × 2 satır
        for i, (anahtar, baslik_metni, renk) in enumerate(kartlar):
            satir, sutun = divmod(i, 3)
            kart = self._kart_olustur(kart_alani, baslik_metni, renk)
            kart["cerceve"].grid(row=satir, column=sutun, padx=8, pady=8, sticky="nsew")
            self.kartlar[anahtar] = kart

        for col in range(3):
            kart_alani.grid_columnconfigure(col, weight=1, uniform="kart")
        for row in range(2):
            kart_alani.grid_rowconfigure(row, weight=1)

    def _kart_olustur(self, parent, baslik_metni, renk):
        cerceve = tk.Frame(parent, bg="white", highlightbackground="#e0e0e0", highlightthickness=1)

        ust = tk.Frame(cerceve, bg=renk)
        ust.pack(fill="x")
        tk.Label(ust, text=baslik_metni, bg=renk, fg="white",
                 font=("Arial", 9, "bold"), padx=12, pady=6).pack(side="left")

        deger = tk.Label(cerceve, text="0,00 TL", bg="white", fg="#333333",
                         font=("Arial", 20, "bold"), pady=20)
        deger.pack(fill="x")

        return {"cerceve": cerceve, "deger": deger}

    def yenile(self):
        """Sekmeye geçişte verileri tazeler (main_window _tab_sec çağırır)."""
        veriler = self._hesapla()
        for anahtar, deger in veriler.items():
            kart = self.kartlar.get(anahtar)
            if kart:
                kart["deger"].config(text=format_currency(deger))

    def _hesapla(self):
        veriler = {"kasa": 0.0, "banka": 0.0, "pos": 0.0, "alacak": 0.0, "borc": 0.0, "stok": 0.0}
        conn = None
        try:
            conn = veritabani_baglan()
            c = conn.cursor()
            fid = self.main_app.aktif_firma_id

            # 1. Kasa toplam bakiye (tüm kasalar)
            c.execute(
                "SELECT COALESCE(SUM(borc),0) - COALESCE(SUM(alacak),0) "
                "FROM fis_satirlari WHERE hesap_turu='Kasa' AND firma_id=?", (fid,)
            )
            veriler["kasa"] = c.fetchone()[0] or 0.0

            # 2. Banka toplam bakiye (yalnız Vadesiz türü)
            c.execute(
                """SELECT COALESCE(SUM(fs.borc),0) - COALESCE(SUM(fs.alacak),0)
                   FROM fis_satirlari fs
                   JOIN banka_hesaplari b ON b.id = fs.hesap_id
                   WHERE fs.hesap_turu='Banka' AND b.hesap_turu='Vadesiz' AND fs.firma_id=?""", (fid,)
            )
            veriler["banka"] = c.fetchone()[0] or 0.0

            # 3. POS toplam (POS türü banka hesaplarının bakiyesi)
            c.execute(
                """SELECT COALESCE(SUM(fs.borc),0) - COALESCE(SUM(fs.alacak),0)
                   FROM fis_satirlari fs
                   JOIN banka_hesaplari b ON b.id = fs.hesap_id
                   WHERE fs.hesap_turu='Banka' AND b.hesap_turu='POS' AND fs.firma_id=?""", (fid,)
            )
            veriler["pos"] = c.fetchone()[0] or 0.0

            # 4-5. Cari: TOPLAM ALACAK (bize borçlu olanlar) / TOPLAM BORÇ (bizim borcumuz)
            c.execute(
                """SELECT COALESCE(SUM(fs.borc),0) - COALESCE(SUM(fs.alacak),0)
                   FROM cariler cari
                   LEFT JOIN fis_satirlari fs
                     ON fs.hesap_turu='Cari' AND fs.hesap_id = cari.id AND fs.firma_id = ?
                   WHERE cari.firma_id = ?
                   GROUP BY cari.id""", (fid, fid)
            )
            for (bakiye,) in c.fetchall():
                bakiye = bakiye or 0.0
                if bakiye > 0:
                    veriler["alacak"] += bakiye      # cari bize borçlu → bizim alacağımız
                else:
                    veriler["borc"] += -bakiye       # biz cariye borçlu → borcumuz

            # 6. Eldeki stok maliyet değeri (FIFO) — stok raporundaki mantıkla aynı
            c.execute(
                """SELECT hesap_id, SUM(CASE WHEN borc>0 THEN miktar WHEN alacak>0 THEN -miktar ELSE 0 END)
                   FROM fis_satirlari WHERE hesap_turu='Stok' AND firma_id=? GROUP BY hesap_id""", (fid,)
            )
            stok_bakiyeleri = {r[0]: r[1] for r in c.fetchall()}

            c.execute(
                """SELECT fs.hesap_id, fs.miktar, fs.birim_fiyat
                   FROM fis_satirlari fs
                   JOIN fisler f ON f.id = fs.fis_id
                   WHERE fs.hesap_turu='Stok' AND fs.borc > 0 AND fs.firma_id=?
                   ORDER BY f.tarih DESC, f.id DESC""", (fid,)
            )
            kalanlar = stok_bakiyeleri.copy()
            for stok_id, miktar, birim_fiyat in c.fetchall():
                if stok_id in kalanlar and kalanlar[stok_id] > 0:
                    kullanilacak = min(kalanlar[stok_id], miktar or 0)
                    veriler["stok"] += kullanilacak * (birim_fiyat or 0)
                    kalanlar[stok_id] -= kullanilacak

        except Exception as e:
            print(f"Dashboard hesaplama hatası: {e}")
        finally:
            if conn:
                conn.close()
        return veriler
