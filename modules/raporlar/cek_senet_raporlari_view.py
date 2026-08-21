import tkinter as tk
from tkinter import ttk

from .cek_senet_portfoy_raporu_view import CekSenetPortfoyRaporuView
from .cek_senet_vade_raporu_view import CekSenetVadeRaporuView
from .cek_senet_seruven_raporu_view import CekSenetSeruvenRaporuView
from .cek_senet_cari_raporu_view import CekSenetCariRaporuView


class CekSenetRaporlariView(tk.Frame):
    """Çek/Senet raporlarını tek ana sekme altında toplar."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.create_widgets()

    def create_widgets(self):
        self.inner_notebook = ttk.Notebook(self)
        self.inner_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.portfoy_tab = CekSenetPortfoyRaporuView(self.inner_notebook, self.main_app)
        self.inner_notebook.add(self.portfoy_tab, text="Portföy")

        self.vade_tab = CekSenetVadeRaporuView(self.inner_notebook, self.main_app)
        self.inner_notebook.add(self.vade_tab, text="Vade Takvimi")

        self.seruven_tab = CekSenetSeruvenRaporuView(self.inner_notebook, self.main_app)
        self.inner_notebook.add(self.seruven_tab, text="Serüven")

        self.cari_tab = CekSenetCariRaporuView(self.inner_notebook, self.main_app)
        self.inner_notebook.add(self.cari_tab, text="Cari Bazlı Özet")

    def yenile(self):
        selected = self.inner_notebook.nametowidget(self.inner_notebook.select())
        if hasattr(selected, 'yenile'):
            selected.yenile()
