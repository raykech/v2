import tkinter as tk
from tkinter import ttk

from .firma_tanimlari_view import FirmaTanimlariView
from .yil_tanimlari_view import YilTanimlariView


class AyarlarModulu(tk.Frame):
    """Ayarlar modülü: Firma ve Yıl tanımları."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.create_widgets()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.firma_tanimlari_tab = FirmaTanimlariView(self.notebook, self.main_app)
        self.notebook.add(self.firma_tanimlari_tab, text="Firma Tanımları")

        self.yil_tanimlari_tab = YilTanimlariView(self.notebook, self.main_app)
        self.notebook.add(self.yil_tanimlari_tab, text="Yıl Tanımları")

    def yenile(self):
        selected = self.notebook.nametowidget(self.notebook.select())
        if hasattr(selected, 'yenile'):
            selected.yenile()
