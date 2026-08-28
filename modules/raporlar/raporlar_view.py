import tkinter as tk
from tkinter import ttk

from .stok_durum_raporu_view import StokDurumRaporuView
from .hesap_ekstresi_view import HesapEkstresiView
from .hizmet_kartlari_raporu_view import HizmetKartlariRaporuView
from .cek_senet_raporlari_view import CekSenetRaporlariView
from .kdv_raporu_view import KdvRaporuView
from .cari_bakiye_raporu_view import CariBakiyeRaporuView
from .satis_raporu_view import SatisRaporuView

class RaporlarModulu(tk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.parent = parent
        self.create_widgets()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.stok_durum_raporu_tab = StokDurumRaporuView(self.notebook, self.main_app)
        self.notebook.add(self.stok_durum_raporu_tab, text="Stok Durum Raporu")

        self.stok_ekstre_tab = HesapEkstresiView(self.notebook, self.main_app, hesap_turu="Stok")
        self.notebook.add(self.stok_ekstre_tab, text="Stok Ekstresi")

        self.cari_ekstre_tab = HesapEkstresiView(self.notebook, self.main_app, hesap_turu="Cari")
        self.notebook.add(self.cari_ekstre_tab, text="Cari Ekstre")

        self.kasa_ekstre_tab = HesapEkstresiView(self.notebook, self.main_app, hesap_turu="Kasa")
        self.notebook.add(self.kasa_ekstre_tab, text="Kasa Ekstresi")

        self.banka_ekstre_tab = HesapEkstresiView(self.notebook, self.main_app, hesap_turu="Banka")
        self.notebook.add(self.banka_ekstre_tab, text="Banka Ekstresi")

        self.hizmet_kartlari_raporu_tab = HizmetKartlariRaporuView(self.notebook, self.main_app)
        self.notebook.add(self.hizmet_kartlari_raporu_tab, text="Hizmet Kartları Raporu")

        self.hizmet_kartlari_detay_tab = HesapEkstresiView(self.notebook, self.main_app, hesap_turu="Hizmet")
        self.cek_senet_raporlari_tab = CekSenetRaporlariView(self.notebook, self.main_app)
        self.notebook.add(self.hizmet_kartlari_detay_tab, text="Hizmet Kartları Detay")
        self.notebook.add(self.cek_senet_raporlari_tab, text="Çek/Senet Raporları")

        self.kdv_raporu_tab = KdvRaporuView(self.notebook, self.main_app)
        self.notebook.add(self.kdv_raporu_tab, text="KDV Raporu")

        self.cari_bakiye_raporu_tab = CariBakiyeRaporuView(self.notebook, self.main_app)
        self.notebook.add(self.cari_bakiye_raporu_tab, text="Cari Bakiyeleri")

        self.satis_raporu_tab = SatisRaporuView(self.notebook, self.main_app)
        self.notebook.add(self.satis_raporu_tab, text="Satış Raporu")

    def yenile(self):
        # Raporlar sekmesine geçişte otomatik yükleme YAPILMAZ (kasıntı engeli);
        # her rapor yalnızca kullanıcı "Listele / Raporu Getir" dediğinde yüklenir.
        pass
