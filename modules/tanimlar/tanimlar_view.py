import tkinter as tk
from tkinter import ttk

from .stok_view import StokTanimView
from .kasa_view import KasaTanimView
from .cari_view import CariTanimView
from .hizmet_view import HizmetTanimView
from .banka_kurum_view import BankaKurumTanimView
from .banka_hesap_view import BankaHesapTanimView
from .tanim_import import TanimImportView

class TanimlarModulu(tk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.parent = parent

        self.create_widgets()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Stok Kartları Sekmesi
        self.stok_tab = StokTanimView(self.notebook, self.main_app)
        self.notebook.add(self.stok_tab, text="Stok Kartları")

        self.cari_tab = CariTanimView(self.notebook, self.main_app)
        self.notebook.add(self.cari_tab, text="Cari Kartlar")

        self.kasa_tab = KasaTanimView(self.notebook, self.main_app)
        self.notebook.add(self.kasa_tab, text="Kasa Kartları")

        self.hizmet_tab = HizmetTanimView(self.notebook, self.main_app)
        self.notebook.add(self.hizmet_tab, text="Hizmet Kartları")

        self.banka_hesap_tab = BankaHesapTanimView(self.notebook, self.main_app)
        self.notebook.add(self.banka_hesap_tab, text="Banka Hesapları")

        self.banka_kurum_tab = BankaKurumTanimView(self.notebook, self.main_app)
        self.notebook.add(self.banka_kurum_tab, text="Banka Kurumları")

        self.import_tab = TanimImportView(self.notebook, self.main_app)
        self.notebook.add(self.import_tab, text="Veri Yükle")

    def yenile(self):
        """Aktif sekmeyi yeniler."""
        selected_widget = self.notebook.nametowidget(self.notebook.select())
        if hasattr(selected_widget, 'yenile'):
            selected_widget.yenile()

    def _on_tab_changed(self, event):
        """Sekme değiştiğinde, yeni seçilen sekmenin yenile metodunu çağırır."""
        self.yenile()