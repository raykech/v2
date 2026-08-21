import tkinter as tk
from tkinter import ttk

from .stok_durum_raporu_view import StokDurumRaporuView
from .hesap_ekstresi_view import HesapEkstresiView

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

    def yenile(self):
        selected_widget = self.notebook.nametowidget(self.notebook.select())
        if hasattr(selected_widget, 'yenile'):
            selected_widget.yenile()
