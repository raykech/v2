import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from core.db import veritabani_baglan
from core.services import (
    fis_kaydet,
    fis_guncelle,
    cek_senet_hareket_ekle,
)
from ui.dialogs import ac_kart_dialog
from ui.widgets.lookup_widget import LookupWidget
from utils.formatters import CurrencyFormatter, parse_currency


class CekSenetFisiFormu(tk.Frame):
    """Çek/Senet fiş formu.

    Fiş Türleri:
    - Çek/Senet Giriş Fişi
    - Çek/Senet Bankaya Tahsile Verme
    - Çek/Senet Ciro Etme
    - Çek/Senet Tahsil Fişi
    - Çek/Senet İade Fişi
    """

    FIS_TURLERI = [
        "Çek/Senet Giriş Fişi",
        "Çek/Senet Bankaya Tahsile Verme",
        "Çek/Senet Ciro Etme",
        "Çek/Senet Tahsil Fişi",
        "Çek/Senet İade Fişi",
    ]

    GIRIS_FISI = "Çek/Senet Giriş Fişi"
    BANKA_TAHSIL_FISI = "Çek/Senet Bankaya Tahsile Verme"
    CIRO_FISI = "Çek/Senet Ciro Etme"
    TAHSIL_FISI = "Çek/Senet Tahsil Fişi"
    IADE_FISI = "Çek/Senet İade Fişi"

    def __init__(self, parent, main_app, view_container, fis_turu, fis_id=None, on_close=None):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.view_container = view_container
        self.fis_id = fis_id
        self.fis_turu = fis_turu
        self.on_close = on_close
        self.duzenlenen_satir_id = None
        self.satir_sayaci = 0
        self.tahsil_onceki_durum = None
        self._tahsil_guncel_durum = None

        self.satirlar = {}
        self.cari_dict = {}
        self.banka_kurum_dict = {}
        self.banka_hesap_dict = {}
        self.kasa_dict = {}
        self.cek_senet_data = {}
        self.cek_senet_dict = {}

        self.create_widgets()
        self.verileri_yukle()
        self.ayarla_form_yapisi()

        if self.fis_id:
            self.load_fis_data()

    # ---------------------------------------------------------------- UI
    def create_widgets(self):
        ust_frame = tk.Frame(self, bg="#f5f7fb")
        ust_frame.pack(fill="x", pady=10, padx=10)

        baslik_frame = tk.LabelFrame(ust_frame, text="Fiş Başlık Bilgileri", padx=10, pady=10, font=("Arial", 10, "bold"))
        baslik_frame.pack(fill="x")

        baslik_frame.grid_columnconfigure(1, weight=1)
        baslik_frame.grid_columnconfigure(3, weight=1)

        tk.Label(baslik_frame, text="Fiş Türü:").grid(row=0, column=0, sticky="w", pady=2)
        self.lbl_fis_turu = tk.Label(
            baslik_frame, text=self.fis_turu, font=("Arial", 10, "bold"),
            anchor="w", bg="white", relief="sunken", padx=5,
        )
        self.lbl_fis_turu.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Tarih:").grid(row=0, column=2, sticky="w", padx=(10, 0), pady=2)
        self.ent_tarih = DateEntry(baslik_frame, date_pattern="dd.mm.yyyy")
        self.ent_tarih.grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Fiş No:").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_fis_no = tk.Entry(baslik_frame)
        self.ent_fis_no.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        tk.Label(baslik_frame, text="Açıklama:").grid(row=1, column=2, sticky="w", padx=(10, 0), pady=2)
        self.ent_aciklama = tk.Entry(baslik_frame)
        self.ent_aciklama.grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        # Dinamik başlık alanları (fiş türüne göre)
        self.baslik_dinamik_frame = tk.LabelFrame(ust_frame, text="İşlem Bilgileri", padx=10, pady=10, font=("Arial", 10, "bold"))
        self.baslik_dinamik_frame.pack(fill="x", pady=(10, 0))

        self.liste_frame = tk.LabelFrame(self, text="Fiş Satırları", padx=10, pady=10, font=("Arial", 10, "bold"))
        self.liste_frame.pack(fill="both", expand=True, padx=10, pady=10)

        alt_buton_frame = tk.Frame(self, bg="#f5f7fb")
        alt_buton_frame.pack(fill="x", pady=(0, 10), padx=10, side="bottom")

        self.btn_kaydet = tk.Button(
            alt_buton_frame, text="Fişi Kaydet", command=self.fis_kaydet,
            bg="#198754", fg="white", font=("Arial", 11, "bold"), height=2, width=20,
        )
        self.btn_kaydet.pack(side="right")

        self.btn_iptal = tk.Button(
            alt_buton_frame, text="İptal ve Geri Dön", command=self.iptal,
            bg="#6c757d", fg="white", font=("Arial", 11, "bold"), height=2, width=20,
        )
        self.btn_iptal.pack(side="right", padx=10)

        # --- Giriş satırı alanı ---
        self.entry_row_frame = tk.Frame(self.liste_frame)
        self.entry_row_frame.pack(fill="x", pady=(0, 10))

        # Yeni çek/senet girişi için alanlar
        self.giris_frame = tk.Frame(self.entry_row_frame)

        self.ent_seri_no = tk.Entry(self.giris_frame, width=20)
        self.cmb_tur = ttk.Combobox(self.giris_frame, state="readonly", width=8, values=["Çek", "Senet"])
        self.cmb_tur.set("Çek")
        self.lookup_banka_kurum = LookupWidget(self.giris_frame)
        self.ent_vade = DateEntry(self.giris_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_tutar = tk.Entry(self.giris_frame, width=12, justify="right")
        CurrencyFormatter(self.ent_tutar)
        self.ent_kesideci = tk.Entry(self.giris_frame, width=16)
        self.ent_ciranta = tk.Entry(self.giris_frame, width=16)
        self.ent_satir_aciklama_giris = tk.Entry(self.giris_frame, width=20)

        tk.Label(self.giris_frame, text="Seri No", font=("Arial", 8, "bold")).grid(row=0, column=0)
        tk.Label(self.giris_frame, text="Tür", font=("Arial", 8, "bold")).grid(row=0, column=1)
        tk.Label(self.giris_frame, text="Banka", font=("Arial", 8, "bold")).grid(row=0, column=2)
        tk.Label(self.giris_frame, text="Vade", font=("Arial", 8, "bold")).grid(row=0, column=3)
        tk.Label(self.giris_frame, text="Tutar", font=("Arial", 8, "bold")).grid(row=0, column=4)
        tk.Label(self.giris_frame, text="Keşideci", font=("Arial", 8, "bold")).grid(row=0, column=5)
        tk.Label(self.giris_frame, text="Ciranta", font=("Arial", 8, "bold")).grid(row=0, column=6)
        tk.Label(self.giris_frame, text="Açıklama", font=("Arial", 8, "bold")).grid(row=0, column=7)

        self.ent_seri_no.grid(row=1, column=0, padx=2, pady=(2, 0), sticky="ew")
        self.cmb_tur.grid(row=1, column=1, padx=2, pady=(2, 0), sticky="ew")
        self.lookup_banka_kurum.grid(row=1, column=2, padx=2, pady=(2, 0), sticky="ew")
        self.ent_vade.grid(row=1, column=3, padx=2, pady=(2, 0), sticky="ew")
        self.ent_tutar.grid(row=1, column=4, padx=2, pady=(2, 0), sticky="ew")
        self.ent_kesideci.grid(row=1, column=5, padx=2, pady=(2, 0), sticky="ew")
        self.ent_ciranta.grid(row=1, column=6, padx=2, pady=(2, 0), sticky="ew")
        self.ent_satir_aciklama_giris.grid(row=1, column=7, padx=2, pady=(2, 0), sticky="ew")
        self.btn_ekle_giris = tk.Button(self.giris_frame, text="+", command=self.satir_ekle, width=3)
        self.btn_ekle_giris.grid(row=1, column=8, padx=2, pady=(2, 0), sticky="ew")

        # Mevcut çek/senet seçimi için alanlar
        self.secim_frame = tk.Frame(self.entry_row_frame)

        self.lookup_cek_senet = LookupWidget(self.secim_frame)
        self.ent_satir_aciklama = tk.Entry(self.secim_frame, width=40)
        self.btn_ekle_secim = tk.Button(self.secim_frame, text="+", command=self.satir_ekle, width=3)

        tk.Label(self.secim_frame, text="Çek/Senet", font=("Arial", 8, "bold")).grid(row=0, column=0, sticky="ew")
        tk.Label(self.secim_frame, text="Satır Açıklaması", font=("Arial", 8, "bold")).grid(row=0, column=1, sticky="ew")
        self.lookup_cek_senet.grid(row=1, column=0, padx=2, pady=(2, 0), sticky="ew")
        self.ent_satir_aciklama.grid(row=1, column=1, padx=2, pady=(2, 0), sticky="ew")
        self.btn_ekle_secim.grid(row=1, column=2, padx=2, pady=(2, 0), sticky="ew")
        self.secim_frame.grid_columnconfigure(0, weight=3)
        self.secim_frame.grid_columnconfigure(1, weight=2)

        # Satır listesi
        self.tree_satirlar = ttk.Treeview(
            self.liste_frame,
            columns=("cek_senet", "tutar", "aciklama", "sil"),
            show="headings",
        )
        self.tree_satirlar.heading("cek_senet", text="Çek/Senet")
        self.tree_satirlar.heading("tutar", text="Tutar", anchor="e")
        self.tree_satirlar.heading("aciklama", text="Açıklama")
        self.tree_satirlar.heading("sil", text="", anchor="center")

        self.tree_satirlar.column("cek_senet", width=400)
        self.tree_satirlar.column("tutar", width=120, anchor="e")
        self.tree_satirlar.column("aciklama", width=250)
        self.tree_satirlar.column("sil", width=30, anchor="center", stretch=False)

        vsb = ttk.Scrollbar(self.liste_frame, orient="vertical", command=self.tree_satirlar.yview)
        vsb.pack(side="right", fill="y")
        self.tree_satirlar.configure(yscrollcommand=vsb.set)
        self.tree_satirlar.pack(fill="both", expand=True)

        self.tree_satirlar.bind("<Double-1>", self.satir_duzenle_icin_yukle)
        self.tree_satirlar.bind("<ButtonRelease-1>", self.on_tree_click)

        # Toplam
        toplamlar_frame = tk.Frame(self.liste_frame, bg="#e9ecef")
        toplamlar_frame.pack(fill="x", pady=(5, 0))
        toplamlar_frame.grid_columnconfigure(3, weight=1)

        tk.Label(toplamlar_frame, text="Toplam Tutar:", font=("Arial", 10, "bold"), bg="#e9ecef").grid(row=0, column=3, sticky="e", padx=5)
        self.lbl_toplam_tutar = tk.Label(toplamlar_frame, text="0,00", font=("Arial", 10, "bold"), bg="#e9ecef", width=15, anchor="e")
        self.lbl_toplam_tutar.grid(row=0, column=4, sticky="e")

        # Enter navigasyonu
        self.ent_seri_no.bind("<Return>", lambda e: self.cmb_tur.focus_set())
        self.cmb_tur.bind("<<ComboboxSelected>>", lambda e: self.lookup_banka_kurum.ent_display.focus_set())
        self.ent_tutar.bind("<Return>", lambda e: self.satir_ekle())
        self.lookup_cek_senet.ent_display.bind("<Return>", lambda e: self.ent_satir_aciklama.focus_set())
        self.ent_satir_aciklama.bind("<Return>", lambda e: self.satir_ekle())

    # ---------------------------------------------------------------- Veriler
    def verileri_yukle(self):
        firma_id = self.main_app.aktif_firma_id
        conn = veritabani_baglan()
        cursor = conn.cursor()

        cursor.execute("SELECT id, unvan FROM cariler WHERE durum=1 AND firma_id=?", (firma_id,))
        self.cari_dict = {row[1]: row[0] for row in cursor.fetchall()}

        cursor.execute("SELECT id, kurum_adi FROM banka_kurumlari WHERE durum=1 AND firma_id=?", (firma_id,))
        self.banka_kurum_dict = {row[1]: row[0] for row in cursor.fetchall()}

        cursor.execute("SELECT id, hesap_adi FROM banka_hesaplari WHERE durum=1 AND firma_id=?", (firma_id,))
        self.banka_hesap_dict = {row[1]: row[0] for row in cursor.fetchall()}

        cursor.execute("SELECT id, kasa_adi FROM kasalar WHERE durum=1 AND firma_id=?", (firma_id,))
        self.kasa_dict = {row[1]: row[0] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT c.id, c.seri_no, c.turu, c.tutar, c.vade_tarihi,
                   COALESCE(k.kurum_adi, c.banka, '') AS banka_adi,
                   (SELECT h.durum FROM cek_senet_hareketleri h
                    WHERE h.cek_senet_id = c.id
                    ORDER BY h.id DESC LIMIT 1) AS durum
            FROM cekler_senetler c
            LEFT JOIN banka_kurumlari k ON c.banka_id = k.id
            WHERE c.firma_id = ?
            """,
            (firma_id,),
        )
        self.cek_senet_data = {}
        for row in cursor.fetchall():
            cek_id, seri_no, turu, tutar, vade, banka_adi, durum = row
            self.cek_senet_data[cek_id] = {
                "id": cek_id,
                "seri_no": seri_no,
                "turu": turu,
                "tutar": tutar,
                "vade": vade,
                "banka_adi": banka_adi or "",
                "durum": durum or "Portföyde",
                "kaynak_banka_id": None,
                "kaynak_banka_adi": "",
            }

        # Bankada Tahsilde olan çek/senetler için son banka takas hesabını da yükle
        cursor.execute(
            """
            SELECT h.cek_senet_id, h.karsi_hesap_id, h.karsi_hesap_ismi
            FROM cek_senet_hareketleri h
            WHERE h.durum = 'Bankada Tahsilde'
              AND h.id = (
                  SELECT MAX(h2.id) FROM cek_senet_hareketleri h2
                  WHERE h2.cek_senet_id = h.cek_senet_id
                    AND h2.durum = 'Bankada Tahsilde'
              )
            """
        )
        for cek_id, banka_id, banka_adi in cursor.fetchall():
            if cek_id in self.cek_senet_data:
                self.cek_senet_data[cek_id]["kaynak_banka_id"] = banka_id
                self.cek_senet_data[cek_id]["kaynak_banka_adi"] = banka_adi or ""

        conn.close()

    # ---------------------------------------------------------------- Dinamik form
    def ayarla_form_yapisi(self):
        for child in self.baslik_dinamik_frame.winfo_children():
            child.destroy()

        self.lookup_cari = None
        self.lookup_banka_hesap = None
        self.cmb_tahsil_turu = None
        self.lookup_tahsil_hesap = None
        self.lbl_tahsil_hesap = None

        self.baslik_dinamik_frame.grid_columnconfigure(1, weight=1)

        if self.fis_turu == self.GIRIS_FISI:
            self.giris_frame.pack(fill="x")
            self.secim_frame.pack_forget()
            self.lookup_banka_kurum.configure_lookup(
                title="Banka Kurumu Seç",
                data_dict=self.banka_kurum_dict,
                on_new=lambda: self.yeni_kart_ekle("banka_kurumlari"),
            )
            tk.Label(self.baslik_dinamik_frame, text="Müşteri / Cari:").grid(row=0, column=0, sticky="w", pady=2)
            self.lookup_cari = LookupWidget(self.baslik_dinamik_frame)
            self.lookup_cari.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            self.lookup_cari.configure_lookup(
                title="Cari Seç",
                data_dict=self.cari_dict,
                on_new=lambda: self.yeni_kart_ekle("cariler"),
            )
        elif self.fis_turu == self.BANKA_TAHSIL_FISI:
            self.giris_frame.pack_forget()
            self.secim_frame.pack(fill="x")
            self._configure_cek_senet_lookup()
            tk.Label(self.baslik_dinamik_frame, text="Banka Hesabı:").grid(row=0, column=0, sticky="w", pady=2)
            self.lookup_banka_hesap = LookupWidget(self.baslik_dinamik_frame)
            self.lookup_banka_hesap.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            self.lookup_banka_hesap.configure_lookup(
                title="Banka Hesabı Seç",
                data_dict=self.banka_hesap_dict,
                on_new=None,
            )
        elif self.fis_turu == self.CIRO_FISI:
            self.giris_frame.pack_forget()
            self.secim_frame.pack(fill="x")
            self._configure_cek_senet_lookup()
            tk.Label(self.baslik_dinamik_frame, text="Ciro Edilen Cari:").grid(row=0, column=0, sticky="w", pady=2)
            self.lookup_cari = LookupWidget(self.baslik_dinamik_frame)
            self.lookup_cari.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            self.lookup_cari.configure_lookup(
                title="Cari Seç",
                data_dict=self.cari_dict,
                on_new=lambda: self.yeni_kart_ekle("cariler"),
            )
        elif self.fis_turu == self.TAHSIL_FISI:
            self.giris_frame.pack_forget()
            self.secim_frame.pack(fill="x")
            self._configure_cek_senet_lookup()
            self.baslik_dinamik_frame.grid_columnconfigure(3, weight=1)
            tk.Label(self.baslik_dinamik_frame, text="Tahsil Türü:").grid(row=0, column=0, sticky="w", pady=2)
            self.cmb_tahsil_turu = ttk.Combobox(
                self.baslik_dinamik_frame, state="readonly", width=10, values=["Kasa", "Banka"]
            )
            self.cmb_tahsil_turu.set("Kasa")
            self.cmb_tahsil_turu.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            self.cmb_tahsil_turu.bind("<<ComboboxSelected>>", lambda e: self._tahsil_turu_degisti())

            self.lbl_tahsil_hesap = tk.Label(self.baslik_dinamik_frame, text="Kasa Hesabı:")
            self.lbl_tahsil_hesap.grid(row=0, column=2, sticky="w", padx=(10, 0), pady=2)
            self.lookup_tahsil_hesap = LookupWidget(self.baslik_dinamik_frame)
            self.lookup_tahsil_hesap.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
            self._tahsil_turu_degisti()
        elif self.fis_turu == self.IADE_FISI:
            self.giris_frame.pack_forget()
            self.secim_frame.pack(fill="x")
            self._configure_cek_senet_lookup()
            tk.Label(self.baslik_dinamik_frame, text="Müşteri / Cari:").grid(row=0, column=0, sticky="w", pady=2)
            self.lookup_cari = LookupWidget(self.baslik_dinamik_frame)
            self.lookup_cari.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            self.lookup_cari.configure_lookup(
                title="Cari Seç",
                data_dict=self.cari_dict,
                on_new=lambda: self.yeni_kart_ekle("cariler"),
            )

        self._setup_enter_navigation()
        self.guncelle_toplamlari()

    def _configure_cek_senet_lookup(self):
        self.cek_senet_dict = {}
        for cek_id, data in self.cek_senet_data.items():
            durum = data["durum"]
            if self.fis_turu == self.BANKA_TAHSIL_FISI and durum != "Portföyde":
                continue
            if self.fis_turu == self.CIRO_FISI and durum != "Portföyde":
                continue
            if self.fis_turu == self.TAHSIL_FISI and durum not in ("Portföyde", "Bankada Tahsilde"):
                continue
            if self.fis_turu == self.IADE_FISI and durum != "Portföyde":
                continue
            display = (
                f"{data['seri_no']} - {data['turu']} - {data['tutar']:,.2f} TL "
                f"- {durum} - {data['banka_adi']}"
            )
            self.cek_senet_dict[display] = cek_id
        self.lookup_cek_senet.configure_lookup(
            title="Çek/Senet Seç",
            data_dict=self.cek_senet_dict,
            on_new=None,
        )

    def _tahsil_turu_degisti(self, event=None):
        if not self.cmb_tahsil_turu or not self.lookup_tahsil_hesap:
            return
        tur = self.cmb_tahsil_turu.get()
        if tur == "Kasa":
            self.lbl_tahsil_hesap.config(text="Kasa Hesabı:")
            self.lookup_tahsil_hesap.configure_lookup(
                title="Kasa Seç", data_dict=self.kasa_dict, on_new=lambda: self.yeni_kart_ekle("kasalar")
            )
        else:
            self.lbl_tahsil_hesap.config(text="Banka Hesabı:")
            self.lookup_tahsil_hesap.configure_lookup(
                title="Banka Hesabı Seç", data_dict=self.banka_hesap_dict, on_new=None
            )

    def _tahsil_ayarlari_guncelle(self):
        """Satırlardaki çek/senetlerin durumuna göre tahsil alanlarını ayarlar."""
        if self.fis_turu != self.TAHSIL_FISI:
            return
        if self.fis_id and self.tahsil_onceki_durum:
            durumlar = [self.tahsil_onceki_durum] * len(self.satirlar)
        else:
            durumlar = [self.cek_senet_data[s["cek_senet_id"]]["durum"] for s in self.satirlar.values()]
        if not durumlar:
            self.cmb_tahsil_turu.grid()
            self.lbl_tahsil_hesap.grid()
            self._tahsil_turu_degisti()
            self._tahsil_guncel_durum = None
            return

        ilk_durum = durumlar[0]
        hepsi_ayni = all(d == ilk_durum for d in durumlar)
        if not hepsi_ayni:
            self.cmb_tahsil_turu.grid()
            self.lbl_tahsil_hesap.grid()
            self._tahsil_turu_degisti()
            self._tahsil_guncel_durum = None
            return

        # Durum değiştiğinde eski seçimi temizle
        if self._tahsil_guncel_durum != ilk_durum:
            self.lookup_tahsil_hesap.clear()
            self._tahsil_guncel_durum = ilk_durum

        if ilk_durum == "Portföyde":
            self.cmb_tahsil_turu.grid()
            self.lbl_tahsil_hesap.grid()
            self._tahsil_turu_degisti()
        elif ilk_durum == "Bankada Tahsilde":
            self.cmb_tahsil_turu.grid_remove()
            self.lbl_tahsil_hesap.config(text="Tahsil Edilecek Banka Hesabı:")
            self.lbl_tahsil_hesap.grid()
            self.lookup_tahsil_hesap.configure_lookup(
                title="Tahsil Edilecek Banka Hesabı Seç",
                data_dict=self.banka_hesap_dict,
                on_new=None,
            )

    def _setup_enter_navigation(self):
        if self.fis_turu == self.GIRIS_FISI:
            self.ent_seri_no.bind("<Return>", lambda e: self.cmb_tur.focus_set())
            self.cmb_tur.bind("<<ComboboxSelected>>", lambda e: self.lookup_banka_kurum.ent_display.focus_set())
            self.ent_tutar.bind("<Return>", lambda e: self.satir_ekle())
        else:
            self.lookup_cek_senet.ent_display.bind("<Return>", lambda e: self.ent_satir_aciklama.focus_set())
            self.ent_satir_aciklama.bind("<Return>", lambda e: self.satir_ekle())

    def yeni_kart_ekle(self, tablo_adi, kart_turu=None):
        ac_kart_dialog(self, tablo_adi, firma_id=self.main_app.aktif_firma_id, kart_turu=kart_turu)
        self.verileri_yukle()
        self.ayarla_form_yapisi()

    # ---------------------------------------------------------------- Satır işlemleri
    def _fmt(self, fiyat):
        return f"{fiyat:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def satir_ekle(self):
        if self.fis_turu == self.GIRIS_FISI:
            self._satir_ekle_giris()
        else:
            self._satir_ekle_mevcut()
        self.guncelle_toplamlari()

    def _satir_ekle_giris(self):
        seri_no = self.ent_seri_no.get().strip()
        turu = self.cmb_tur.get()
        banka_id = self.lookup_banka_kurum.get()
        banka_adi = self.lookup_banka_kurum.get_value()
        vade = self.ent_vade.get_date().strftime("%Y-%m-%d")
        tutar = parse_currency(self.ent_tutar.get())
        kesideci = self.ent_kesideci.get().strip()
        ciranta = self.ent_ciranta.get().strip()
        aciklama = self.ent_satir_aciklama_giris.get().strip()

        if not seri_no:
            messagebox.showwarning("Eksik Bilgi", "Lütfen seri no girin.", parent=self)
            return
        if not turu:
            messagebox.showwarning("Eksik Bilgi", "Lütfen çek/senet türü seçin.", parent=self)
            return
        if tutar <= 0:
            messagebox.showwarning("Geçersiz Tutar", "Lütfen 0'dan büyük bir tutar girin.", parent=self)
            return

        yeni_satir = {
            "tip": "yeni",
            "seri_no": seri_no,
            "turu": turu,
            "banka_id": banka_id,
            "banka_adi": banka_adi,
            "vade": vade,
            "tutar": tutar,
            "kesideci": kesideci,
            "ciranta": ciranta,
            "aciklama": aciklama,
        }

        if self.duzenlenen_satir_id:
            try:
                self.satirlar[self.duzenlenen_satir_id] = yeni_satir
                self.tree_satirlar.item(
                    self.duzenlenen_satir_id,
                    values=(f"{seri_no} - {turu} - {banka_adi}", self._fmt(tutar), aciklama, "❌"),
                )
            except Exception:
                self.satir_sayaci += 1
                item_id = f"satir_{self.satir_sayaci}"
                self.tree_satirlar.insert(
                    "", "end", iid=item_id,
                    values=(f"{seri_no} - {turu} - {banka_adi}", self._fmt(tutar), aciklama, "❌"),
                )
                self.satirlar[item_id] = yeni_satir
            self.duzenlenen_satir_id = None
        else:
            self.satir_sayaci += 1
            item_id = f"satir_{self.satir_sayaci}"
            self.tree_satirlar.insert(
                "", "end", iid=item_id,
                values=(f"{seri_no} - {turu} - {banka_adi}", self._fmt(tutar), aciklama, "❌"),
            )
            self.satirlar[item_id] = yeni_satir

        self.temizle_giris_satiri()

    def _satir_ekle_mevcut(self):
        raw_id = self.lookup_cek_senet.get()
        if not raw_id:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir çek/senet seçin.", parent=self)
            return

        try:
            cek_senet_id = int(raw_id)
        except (TypeError, ValueError):
            messagebox.showerror("Hata", "Seçilen çek/senet ID'si geçersiz.", parent=self)
            return

        data = self.cek_senet_data.get(cek_senet_id)
        if not data:
            messagebox.showwarning("Hata", "Seçilen çek/senet bulunamadı.", parent=self)
            return

        aciklama = self.ent_satir_aciklama.get().strip()
        yeni_satir = {
            "tip": "mevcut",
            "cek_senet_id": cek_senet_id,
            "seri_no": data["seri_no"],
            "turu": data["turu"],
            "tutar": data["tutar"],
            "aciklama": aciklama,
        }
        display = f"{data['seri_no']} - {data['turu']} - {data['durum']}"

        if self.duzenlenen_satir_id:
            try:
                self.satirlar[self.duzenlenen_satir_id] = yeni_satir
                self.tree_satirlar.item(
                    self.duzenlenen_satir_id,
                    values=(display, self._fmt(data["tutar"]), aciklama, "❌"),
                )
            except Exception:
                self.satir_sayaci += 1
                item_id = f"satir_{self.satir_sayaci}"
                self.tree_satirlar.insert(
                    "", "end", iid=item_id,
                    values=(display, self._fmt(data["tutar"]), aciklama, "❌"),
                )
                self.satirlar[item_id] = yeni_satir
            self.duzenlenen_satir_id = None
        else:
            self.satir_sayaci += 1
            item_id = f"satir_{self.satir_sayaci}"
            self.tree_satirlar.insert(
                "", "end", iid=item_id,
                values=(display, self._fmt(data["tutar"]), aciklama, "❌"),
            )
            self.satirlar[item_id] = yeni_satir

        self.temizle_giris_satiri()
        self._tahsil_ayarlari_guncelle()

    def temizle_giris_satiri(self):
        self.duzenlenen_satir_id = None
        if self.fis_turu == self.GIRIS_FISI:
            self.ent_seri_no.delete(0, tk.END)
            self.cmb_tur.set("Çek")
            self.lookup_banka_kurum.clear()
            self.ent_tutar.delete(0, tk.END)
            self.ent_kesideci.delete(0, tk.END)
            self.ent_ciranta.delete(0, tk.END)
            self.ent_satir_aciklama_giris.delete(0, tk.END)
            self.ent_seri_no.focus_set()
        else:
            self.lookup_cek_senet.clear()
            self.ent_satir_aciklama.delete(0, tk.END)
            self.lookup_cek_senet.ent_display.focus_set()
        self.guncelle_toplamlari()

    def satir_sil(self, item_id_to_delete):
        if not item_id_to_delete:
            return
        try:
            self.tree_satirlar.delete(item_id_to_delete)
            del self.satirlar[item_id_to_delete]
        except KeyError:
            print(f"Satır {item_id_to_delete} bulunamadı.")
        self.guncelle_toplamlari()
        self._tahsil_ayarlari_guncelle()
        if self.duzenlenen_satir_id == item_id_to_delete:
            self.temizle_giris_satiri()

    def on_tree_click(self, event):
        region = self.tree_satirlar.identify("region", event.x, event.y)
        if region == "cell" and self.tree_satirlar.identify_column(event.x) == "#4":
            self.satir_sil(self.tree_satirlar.identify_row(event.y))

    def satir_duzenle_icin_yukle(self, event=None):
        selected_items = self.tree_satirlar.selection()
        if not selected_items:
            return
        selected_item = selected_items[0]
        try:
            self.duzenlenen_satir_id = selected_item
            satir = self.satirlar[selected_item]
            if satir["tip"] == "yeni":
                self.ent_seri_no.delete(0, tk.END)
                self.ent_seri_no.insert(0, satir["seri_no"])
                self.cmb_tur.set(satir["turu"])
                if satir.get("banka_id"):
                    self.lookup_banka_kurum.set(satir["banka_id"])
                self.ent_vade.set_date(datetime.strptime(satir["vade"], "%Y-%m-%d").date())
                self.ent_tutar.delete(0, tk.END)
                self.ent_tutar.insert(0, self._fmt(satir["tutar"]))
                self.ent_kesideci.delete(0, tk.END)
                self.ent_kesideci.insert(0, satir.get("kesideci", ""))
                self.ent_ciranta.delete(0, tk.END)
                self.ent_ciranta.insert(0, satir.get("ciranta", ""))
                self.ent_satir_aciklama_giris.delete(0, tk.END)
                self.ent_satir_aciklama_giris.insert(0, satir.get("aciklama", ""))
            else:
                self.lookup_cek_senet.set(satir["cek_senet_id"])
                self.ent_satir_aciklama.delete(0, tk.END)
                self.ent_satir_aciklama.insert(0, satir.get("aciklama", ""))
        except (IndexError, KeyError, ValueError) as e:
            print(f"Satır yükleme hatası: {e}")
            self.duzenlenen_satir_id = None

    def guncelle_toplamlari(self):
        toplam = sum(s["tutar"] for s in self.satirlar.values())
        self.lbl_toplam_tutar.config(text=self._fmt(toplam))

    # ---------------------------------------------------------------- Kaydet
    def _durum_kontrol(self, cek_id, sonuc_durumu):
        """Yeni fişte ön durumu, düzenlemede sonuç durumunu kontrol eder."""
        mevcut = self.cek_senet_data[cek_id]["durum"]
        if self.fis_id:
            return mevcut == sonuc_durumu

        if self.fis_turu == self.TAHSIL_FISI:
            return mevcut in ("Portföyde", "Bankada Tahsilde")
        if self.fis_turu == self.BANKA_TAHSIL_FISI:
            return mevcut == "Portföyde"
        if self.fis_turu == self.CIRO_FISI:
            return mevcut == "Portföyde"
        if self.fis_turu == self.IADE_FISI:
            return mevcut == "Portföyde"
        return True

    def _tahsil_icin_durum_dogrula(self):
        """Tahsil fişinde tüm satırların aynı durumda olmasını sağlar."""
        if not self.satirlar:
            return None

        if self.fis_id and self.tahsil_onceki_durum:
            return self.tahsil_onceki_durum

        durumlar = [self.cek_senet_data[s["cek_senet_id"]]["durum"] for s in self.satirlar.values()]
        ilk = durumlar[0]
        if not all(d == ilk for d in durumlar):
            messagebox.showwarning(
                "Uyarı",
                "Aynı tahsil fişinde farklı durumdaki çek/senetler işlenemez. "
                "Lütfen aynı durumdaki çek/senetleri seçin.",
                parent=self,
            )
            return None
        return ilk

    def fis_kaydet(self):
        if not self.satirlar:
            messagebox.showwarning("Eksik Bilgi", "Fişe en az bir satır eklemelisiniz.", parent=self)
            return

        tarih = self.ent_tarih.get_date().strftime("%Y-%m-%d")
        firma_id = self.main_app.aktif_firma_id

        fis_baslik = {
            "tarih": tarih,
            "fis_turu": self.fis_turu,
            "fis_no": self.ent_fis_no.get().strip(),
            "aciklama": self.ent_aciklama.get().strip(),
            "toplam_tutar": 0.0,
            "cari_id": None,
            "firma_id": firma_id,
            "yil": self.main_app.aktif_yil,
        }

        fis_satirlari = []
        hareketler = []

        if self.fis_turu == self.GIRIS_FISI:
            if not self.lookup_cari or not self.lookup_cari.get():
                messagebox.showwarning("Eksik Bilgi", "Lütfen müşteri/cari seçin.", parent=self)
                return
            cari_id = self.lookup_cari.get()
            cari_adi = self.lookup_cari.get_value()
            fis_baslik["cari_id"] = cari_id
            toplam = 0.0
            for satir in self.satirlar.values():
                if satir.get("cek_senet_id"):
                    # Düzenleme sırasında mevcut kayıt güncellenir
                    satir_id = satir["cek_senet_id"]
                    cursor_guncelle = None  # Aşağıda açılacak cursor ile işlenecek
                else:
                    satir_id = None
                toplam += satir["tutar"]
                fis_satirlari.append({
                    "hesap_turu": "CekSenet",
                    "hesap_id": 0,  # Gerçek ID kaydetme sırasında doldurulacak
                    "borc": satir["tutar"],
                    "alacak": 0,
                    "aciklama": satir.get("aciklama", ""),
                    "miktar": 1,
                    "birim_fiyat": satir["tutar"],
                    "kdv_oran": 0,
                    "kdv_tutar": 0,
                })
                fis_satirlari.append({
                    "hesap_turu": "Cari",
                    "hesap_id": cari_id,
                    "borc": 0,
                    "alacak": satir["tutar"],
                    "aciklama": satir.get("aciklama", ""),
                    "miktar": 1,
                    "birim_fiyat": satir["tutar"],
                    "kdv_oran": 0,
                    "kdv_tutar": 0,
                })
                hareketler.append({
                    "cek_senet_id": satir_id,
                    "durum": "Portföyde",
                    "karsi_hesap_tipi": "Cari",
                    "karsi_hesap_id": cari_id,
                    "karsi_hesap_ismi": cari_adi,
                    "aciklama": satir.get("aciklama", ""),
                })
            fis_baslik["toplam_tutar"] = toplam

        elif self.fis_turu == self.BANKA_TAHSIL_FISI:
            if not self.lookup_banka_hesap or not self.lookup_banka_hesap.get():
                messagebox.showwarning("Eksik Bilgi", "Lütfen banka hesabı seçin.", parent=self)
                return
            banka_id = self.lookup_banka_hesap.get()
            banka_adi = self.lookup_banka_hesap.get_value()
            toplam = 0.0
            for satir in self.satirlar.values():
                cek_id = satir["cek_senet_id"]
                if not self._durum_kontrol(cek_id, "Bankada Tahsilde"):
                    messagebox.showwarning("Uyarı", "Bu çek/senet bankaya tahsile verilemez.", parent=self)
                    return
                tutar = satir["tutar"]
                toplam += tutar
                fis_satirlari.append({
                    "hesap_turu": "CekSenet",
                    "hesap_id": cek_id,
                    "borc": 0,
                    "alacak": tutar,
                    "aciklama": satir.get("aciklama", ""),
                    "miktar": 1,
                    "birim_fiyat": tutar,
                    "kdv_oran": 0,
                    "kdv_tutar": 0,
                })
                fis_satirlari.append({
                    "hesap_turu": "Banka",
                    "hesap_id": banka_id,
                    "borc": tutar,
                    "alacak": 0,
                    "aciklama": satir.get("aciklama", ""),
                    "miktar": 1,
                    "birim_fiyat": tutar,
                    "kdv_oran": 0,
                    "kdv_tutar": 0,
                })
                hareketler.append({
                    "cek_senet_id": cek_id,
                    "durum": "Bankada Tahsilde",
                    "karsi_hesap_tipi": "Banka",
                    "karsi_hesap_id": banka_id,
                    "karsi_hesap_ismi": banka_adi,
                    "aciklama": satir.get("aciklama", ""),
                })
            fis_baslik["toplam_tutar"] = toplam

        elif self.fis_turu == self.CIRO_FISI:
            if not self.lookup_cari or not self.lookup_cari.get():
                messagebox.showwarning("Eksik Bilgi", "Lütfen ciro edilen cariyi seçin.", parent=self)
                return
            cari_id = self.lookup_cari.get()
            cari_adi = self.lookup_cari.get_value()
            toplam = 0.0
            for satir in self.satirlar.values():
                cek_id = satir["cek_senet_id"]
                if not self._durum_kontrol(cek_id, "Cirolu"):
                    messagebox.showwarning("Uyarı", "Bu çek/senet ciro edilemez.", parent=self)
                    return
                tutar = satir["tutar"]
                toplam += tutar
                fis_satirlari.append({
                    "hesap_turu": "CekSenet",
                    "hesap_id": cek_id,
                    "borc": 0,
                    "alacak": tutar,
                    "aciklama": satir.get("aciklama", ""),
                    "miktar": 1,
                    "birim_fiyat": tutar,
                    "kdv_oran": 0,
                    "kdv_tutar": 0,
                })
                fis_satirlari.append({
                    "hesap_turu": "Cari",
                    "hesap_id": cari_id,
                    "borc": tutar,
                    "alacak": 0,
                    "aciklama": satir.get("aciklama", ""),
                    "miktar": 1,
                    "birim_fiyat": tutar,
                    "kdv_oran": 0,
                    "kdv_tutar": 0,
                })
                hareketler.append({
                    "cek_senet_id": cek_id,
                    "durum": "Cirolu",
                    "karsi_hesap_tipi": "Cari",
                    "karsi_hesap_id": cari_id,
                    "karsi_hesap_ismi": cari_adi,
                    "aciklama": satir.get("aciklama", ""),
                })
            fis_baslik["toplam_tutar"] = toplam

        elif self.fis_turu == self.TAHSIL_FISI:
            if not self.lookup_tahsil_hesap or not self.lookup_tahsil_hesap.get():
                messagebox.showwarning("Eksik Bilgi", "Lütfen tahsil hesabını seçin.", parent=self)
                return
            durum = self._tahsil_icin_durum_dogrula()
            if not durum:
                return
            tahsil_hesap_id = self.lookup_tahsil_hesap.get()
            tahsil_hesap_adi = self.lookup_tahsil_hesap.get_value()
            toplam = 0.0
            if durum == "Portföyde":
                tahsil_turu = self.cmb_tahsil_turu.get() if self.cmb_tahsil_turu else "Kasa"
                hesap_turu = "Kasa" if tahsil_turu == "Kasa" else "Banka"
                for satir in self.satirlar.values():
                    cek_id = satir["cek_senet_id"]
                    tutar = satir["tutar"]
                    toplam += tutar
                    fis_satirlari.append({
                        "hesap_turu": "CekSenet",
                        "hesap_id": cek_id,
                        "borc": 0,
                        "alacak": tutar,
                        "aciklama": satir.get("aciklama", ""),
                        "miktar": 1,
                        "birim_fiyat": tutar,
                        "kdv_oran": 0,
                        "kdv_tutar": 0,
                    })
                    fis_satirlari.append({
                        "hesap_turu": hesap_turu,
                        "hesap_id": tahsil_hesap_id,
                        "borc": tutar,
                        "alacak": 0,
                        "aciklama": satir.get("aciklama", ""),
                        "miktar": 1,
                        "birim_fiyat": tutar,
                        "kdv_oran": 0,
                        "kdv_tutar": 0,
                    })
                    hareketler.append({
                        "cek_senet_id": cek_id,
                        "durum": "Tahsil Edildi",
                        "karsi_hesap_tipi": hesap_turu,
                        "karsi_hesap_id": tahsil_hesap_id,
                        "karsi_hesap_ismi": tahsil_hesap_adi,
                        "aciklama": satir.get("aciklama", ""),
                    })
            else:  # Bankada Tahsilde
                for satir in self.satirlar.values():
                    cek_id = satir["cek_senet_id"]
                    tutar = satir["tutar"]
                    toplam += tutar
                    data = self.cek_senet_data[cek_id]
                    kaynak_id = data.get("kaynak_banka_id")
                    kaynak_adi = data.get("kaynak_banka_adi") or ""
                    if not kaynak_id:
                        messagebox.showwarning(
                            "Uyarı",
                            "Bu çek/senedin Bankada Tahsilde olduğu banka hesabı bulunamadı.",
                            parent=self,
                        )
                        return
                    fis_satirlari.append({
                        "hesap_turu": "Banka",
                        "hesap_id": tahsil_hesap_id,
                        "borc": tutar,
                        "alacak": 0,
                        "aciklama": f"Tahsil - Kaynak Banka ID:{kaynak_id}",
                        "miktar": 1,
                        "birim_fiyat": tutar,
                        "kdv_oran": 0,
                        "kdv_tutar": 0,
                    })
                    fis_satirlari.append({
                        "hesap_turu": "Banka",
                        "hesap_id": kaynak_id,
                        "borc": 0,
                        "alacak": tutar,
                        "aciklama": f"Tahsil - Hedef Banka ID:{tahsil_hesap_id}",
                        "miktar": 1,
                        "birim_fiyat": tutar,
                        "kdv_oran": 0,
                        "kdv_tutar": 0,
                    })
                    hareketler.append({
                        "cek_senet_id": cek_id,
                        "durum": "Tahsil Edildi",
                        "karsi_hesap_tipi": "Banka",
                        "karsi_hesap_id": tahsil_hesap_id,
                        "karsi_hesap_ismi": tahsil_hesap_adi,
                        "aciklama": satir.get("aciklama", ""),
                    })
            fis_baslik["toplam_tutar"] = toplam

        elif self.fis_turu == self.IADE_FISI:
            if not self.lookup_cari or not self.lookup_cari.get():
                messagebox.showwarning("Eksik Bilgi", "Lütfen müşteri/cari seçin.", parent=self)
                return
            cari_id = self.lookup_cari.get()
            cari_adi = self.lookup_cari.get_value()
            toplam = 0.0
            for satir in self.satirlar.values():
                cek_id = satir["cek_senet_id"]
                if not self._durum_kontrol(cek_id, "İade Edildi"):
                    messagebox.showwarning("Uyarı", "Bu çek/senet iade edilemez.", parent=self)
                    return
                tutar = satir["tutar"]
                toplam += tutar
                fis_satirlari.append({
                    "hesap_turu": "CekSenet",
                    "hesap_id": cek_id,
                    "borc": 0,
                    "alacak": tutar,
                    "aciklama": satir.get("aciklama", ""),
                    "miktar": 1,
                    "birim_fiyat": tutar,
                    "kdv_oran": 0,
                    "kdv_tutar": 0,
                })
                fis_satirlari.append({
                    "hesap_turu": "Cari",
                    "hesap_id": cari_id,
                    "borc": tutar,
                    "alacak": 0,
                    "aciklama": satir.get("aciklama", ""),
                    "miktar": 1,
                    "birim_fiyat": tutar,
                    "kdv_oran": 0,
                    "kdv_tutar": 0,
                })
                hareketler.append({
                    "cek_senet_id": cek_id,
                    "durum": "İade Edildi",
                    "karsi_hesap_tipi": "Cari",
                    "karsi_hesap_id": cari_id,
                    "karsi_hesap_ismi": cari_adi,
                    "aciklama": satir.get("aciklama", ""),
                })
            fis_baslik["toplam_tutar"] = toplam

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            # Yeni çek/senet kayıtlarını ve ID'leri belirle
            if self.fis_turu == self.GIRIS_FISI:
                yeni_cek_ids = []
                for satir_index, satir in enumerate(self.satirlar.values()):
                    cek_id = satir.get("cek_senet_id")
                    if not cek_id:
                        cursor.execute(
                            """
                            INSERT INTO cekler_senetler
                                (seri_no, turu, banka_id, vade_tarihi, tutar,
                                 kesideci, ciranta, aciklama, firma_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                satir["seri_no"],
                                satir["turu"],
                                satir.get("banka_id"),
                                satir["vade"],
                                satir["tutar"],
                                satir.get("kesideci", ""),
                                satir.get("ciranta", ""),
                                satir.get("aciklama", ""),
                                firma_id,
                            ),
                        )
                        cek_id = cursor.lastrowid
                        satir["cek_senet_id"] = cek_id
                    else:
                        cursor.execute(
                            """
                            UPDATE cekler_senetler
                            SET seri_no=?, turu=?, banka_id=?, vade_tarihi=?, tutar=?,
                                kesideci=?, ciranta=?, aciklama=?
                            WHERE id=?
                            """,
                            (
                                satir["seri_no"],
                                satir["turu"],
                                satir.get("banka_id"),
                                satir["vade"],
                                satir["tutar"],
                                satir.get("kesideci", ""),
                                satir.get("ciranta", ""),
                                satir.get("aciklama", ""),
                                cek_id,
                            ),
                        )
                    yeni_cek_ids.append(cek_id)
                    # fis_satirlari içindeki CekSenet satırının hesap_id'sini güncelle
                    for fs in fis_satirlari:
                        if fs["hesap_turu"] == "CekSenet" and fs["hesap_id"] == 0:
                            fs["hesap_id"] = cek_id
                            break
                    # Aynı sıradaki hareketin çek/senet ID'sini güncelle
                    if satir_index < len(hareketler):
                        hareketler[satir_index]["cek_senet_id"] = cek_id

                # Eski Giriş fişinde silinen satırları tespit et (temizlik sonra yapılır)
                eski_cek_ids = []
                if self.fis_id:
                    cursor.execute(
                        "SELECT hesap_id FROM fis_satirlari WHERE fis_id=? AND hesap_turu='CekSenet'",
                        (self.fis_id,),
                    )
                    eski_cek_ids = [row[0] for row in cursor.fetchall()]

            if self.fis_id:
                # Eski hareketleri temizle
                cursor.execute("DELETE FROM cek_senet_hareketleri WHERE fis_id=?", (self.fis_id,))
                fis_guncelle(cursor, self.fis_id, fis_baslik, fis_satirlari, kaynak_modul="CekSenet")
                fis_id = self.fis_id
                mesaj = "Çek/Senet fişi başarıyla güncellendi."

                # Giriş fişinde silinen çek/senet kartlarını, başka hareketleri yoksa temizle
                if self.fis_turu == self.GIRIS_FISI and eski_cek_ids:
                    for eski_id in eski_cek_ids:
                        if eski_id not in yeni_cek_ids:
                            cursor.execute(
                                "SELECT COUNT(*) FROM cek_senet_hareketleri WHERE cek_senet_id=?",
                                (eski_id,),
                            )
                            if cursor.fetchone()[0] == 0:
                                cursor.execute("DELETE FROM cekler_senetler WHERE id=?", (eski_id,))
            else:
                fis_id = fis_kaydet(cursor, fis_baslik, fis_satirlari, kaynak_modul="CekSenet")
                mesaj = "Çek/Senet fişi başarıyla kaydedildi."

            # Hareketleri ekle
            for hareket in hareketler:
                cek_senet_hareket_ekle(
                    cursor,
                    cek_senet_id=hareket["cek_senet_id"],
                    fis_id=fis_id,
                    islem_tarihi=tarih,
                    durum=hareket["durum"],
                    karsi_hesap_tipi=hareket.get("karsi_hesap_tipi"),
                    karsi_hesap_id=hareket.get("karsi_hesap_id"),
                    karsi_hesap_ismi=hareket.get("karsi_hesap_ismi"),
                    aciklama=hareket.get("aciklama", ""),
                    firma_id=firma_id,
                )

            conn.commit()
            messagebox.showinfo("Başarılı", mesaj, parent=self)
            self.iptal()
            if self.view_container:
                self.view_container.yenile()
        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu:\n{e}", parent=self)
        finally:
            if conn:
                conn.close()

    # ---------------------------------------------------------------- Düzenleme
    def load_fis_data(self):
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM fisler WHERE id=?", (self.fis_id,))
            baslik = cursor.fetchone()
            if not baslik:
                messagebox.showerror("Hata", "Fiş bulunamadı.", parent=self)
                self.iptal()
                return
            baslik_cols = [desc[0] for desc in cursor.description]
            baslik_data = dict(zip(baslik_cols, baslik))

            self.ent_tarih.set_date(datetime.strptime(baslik_data["tarih"], "%Y-%m-%d").date())
            self.ent_fis_no.insert(0, baslik_data["fis_no"] or "")
            self.ent_aciklama.insert(0, baslik_data["aciklama"] or "")

            cursor.execute("SELECT * FROM fis_satirlari WHERE fis_id=?", (self.fis_id,))
            satirlar = cursor.fetchall()
            satir_cols = [desc[0] for desc in cursor.description]

            cursor.execute("SELECT * FROM cek_senet_hareketleri WHERE fis_id=?", (self.fis_id,))
            hareketler = cursor.fetchall()
            hareket_cols = [desc[0] for desc in cursor.description]

            if self.fis_turu == self.GIRIS_FISI:
                for satir in satirlar:
                    sd = dict(zip(satir_cols, satir))
                    if sd["hesap_turu"] == "Cari" and sd["alacak"] > 0 and self.lookup_cari:
                        self.lookup_cari.set(sd["hesap_id"])
                        break

                for satir in satirlar:
                    sd = dict(zip(satir_cols, satir))
                    if sd["hesap_turu"] != "CekSenet":
                        continue
                    cursor.execute(
                        """
                        SELECT id, seri_no, turu, banka_id, vade_tarihi, tutar,
                               kesideci, ciranta, aciklama
                        FROM cekler_senetler WHERE id=?
                        """,
                        (sd["hesap_id"],),
                    )
                    row = cursor.fetchone()
                    if not row:
                        continue
                    cek_id, seri_no, turu, banka_id, vade, tutar, kesideci, ciranta, aciklama = row
                    banka_adi = next((name for name, i in self.banka_kurum_dict.items() if str(i) == str(banka_id)), "")
                    yeni_satir = {
                        "tip": "yeni",
                        "cek_senet_id": cek_id,
                        "seri_no": seri_no,
                        "turu": turu,
                        "banka_id": banka_id,
                        "banka_adi": banka_adi,
                        "vade": vade,
                        "tutar": tutar,
                        "kesideci": kesideci or "",
                        "ciranta": ciranta or "",
                        "aciklama": aciklama or "",
                    }
                    self.satir_sayaci += 1
                    item_id = f"satir_{self.satir_sayaci}"
                    self.tree_satirlar.insert(
                        "", "end", iid=item_id,
                        values=(f"{seri_no} - {turu} - {banka_adi}", self._fmt(tutar), aciklama or "", "❌"),
                    )
                    self.satirlar[item_id] = yeni_satir

            else:
                # Diğer fişlerde hareketlerden çek/senetleri yükle
                for hareket in hareketler:
                    hd = dict(zip(hareket_cols, hareket))
                    cek_id = hd["cek_senet_id"]
                    data = self.cek_senet_data.get(cek_id)
                    if not data:
                        continue
                    yeni_satir = {
                        "tip": "mevcut",
                        "cek_senet_id": cek_id,
                        "seri_no": data["seri_no"],
                        "turu": data["turu"],
                        "tutar": data["tutar"],
                        "aciklama": hd.get("aciklama") or "",
                    }
                    self.satir_sayaci += 1
                    item_id = f"satir_{self.satir_sayaci}"
                    self.tree_satirlar.insert(
                        "", "end", iid=item_id,
                        values=(
                            f"{data['seri_no']} - {data['turu']} - {data['durum']}",
                            self._fmt(data["tutar"]),
                            hd.get("aciklama") or "",
                            "❌",
                        ),
                    )
                    self.satirlar[item_id] = yeni_satir

                # Başlık alanlarını doldur
                if hareketler:
                    ilk_hareket = dict(zip(hareket_cols, hareketler[0]))
                    if self.fis_turu == self.BANKA_TAHSIL_FISI:
                        if self.lookup_banka_hesap and ilk_hareket.get("karsi_hesap_id"):
                            self.lookup_banka_hesap.set(ilk_hareket["karsi_hesap_id"])
                    elif self.fis_turu == self.CIRO_FISI:
                        if self.lookup_cari and ilk_hareket.get("karsi_hesap_id"):
                            self.lookup_cari.set(ilk_hareket["karsi_hesap_id"])
                    elif self.fis_turu == self.IADE_FISI:
                        if self.lookup_cari and ilk_hareket.get("karsi_hesap_id"):
                            self.lookup_cari.set(ilk_hareket["karsi_hesap_id"])
                    elif self.fis_turu == self.TAHSIL_FISI:
                        # Direkt tahsilde CekSenet alacak satırı vardır; bankadan tahsilde yoktur.
                        cek_senet_alis_satiri = any(
                            dict(zip(satir_cols, s))["hesap_turu"] == "CekSenet"
                            and dict(zip(satir_cols, s))["alacak"] > 0
                            for s in satirlar
                        )
                        self.tahsil_onceki_durum = "Portföyde" if cek_senet_alis_satiri else "Bankada Tahsilde"
                        self._tahsil_guncel_durum = self.tahsil_onceki_durum
                        if self.lookup_tahsil_hesap:
                            if cek_senet_alis_satiri:
                                karsi_tip = ilk_hareket.get("karsi_hesap_tipi") or "Kasa"
                                if self.cmb_tahsil_turu:
                                    self.cmb_tahsil_turu.set(karsi_tip)
                                self._tahsil_turu_degisti()
                                if ilk_hareket.get("karsi_hesap_id"):
                                    self.lookup_tahsil_hesap.set(ilk_hareket["karsi_hesap_id"])
                            else:
                                # Bankadan tahsil: başlık Banka hesabı seçimi olarak kullanılır
                                if self.cmb_tahsil_turu:
                                    self.cmb_tahsil_turu.set("Banka")
                                self._tahsil_turu_degisti()
                                if ilk_hareket.get("karsi_hesap_id"):
                                    self.lookup_tahsil_hesap.set(ilk_hareket["karsi_hesap_id"])

            self.guncelle_toplamlari()
            self._tahsil_ayarlari_guncelle()
            conn.close()
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Fiş bilgileri yüklenemedi: {e}", parent=self)
            self.iptal()

    def iptal(self):
        self.pack_forget()
        if self.on_close:
            self.on_close()
        if self.view_container:
            self.view_container.pack(fill="both", expand=True)

    def yenile(self):
        if self.view_container:
            self.view_container.listele()
