# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk


class RaporlarModulu(tk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.parent = parent
        self._tabs = {}  # tab text -> [olustu_mu, widget, tab_key]
        self.create_widgets()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tablar = [
            ("Stok Raporları", "stok_raporlari"),
            ("Cari Ekstre", "ekstre_Cari"),
            ("Kasa Ekstresi", "ekstre_Kasa"),
            ("Banka Ekstresi", "ekstre_Banka"),
            ("Hizmet Kartları Raporu", "hizmet_kartlari"),
            ("Hizmet Kartları Detay", "ekstre_Hizmet"),
            ("Çek/Senet Raporları", "cek_senet"),
            ("KDV Raporu", "kdv"),
            ("Cari Bakiyeleri", "cari_bakiye"),
            ("Kar/Zarar Raporu", "satis"),
        ]

        # İlk sekme hemen oluşturulur; gerisi lazy placeholder frame içinde.
        for i, (tab_text, tab_key) in enumerate(tablar):
            if i == 0:
                view = self._tab_olustur(tab_key, self.notebook)
                self.notebook.add(view, text=tab_text)
                self._tabs[tab_text] = [True, view, tab_key]
            else:
                placeholder = tk.Frame(self.notebook, bg="#f5f7fb")
                self.notebook.add(placeholder, text=tab_text)
                self._tabs[tab_text] = [False, placeholder, tab_key]

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event):
        # İç içe notebook'larda (ör. Stok/Çek-Senet raporları) alt sekme
        # olaylarını değil, yalnızca kendi sekme değişimini işle.
        if event.widget is not self.notebook:
            return
        try:
            secili_sekme = self.notebook.tab(self.notebook.select(), "text")
        except Exception:
            return
        tab_info = self._tabs.get(secili_sekme)
        if tab_info is None:
            return
        olustu, widget, tab_key = tab_info
        if olustu:
            return

        # Placeholder frame'in içini temizle ve gerçek view'ı içine koy
        for child in widget.winfo_children():
            child.destroy()
        view = self._tab_olustur(tab_key, widget)
        if view is not None:
            view.pack(fill='both', expand=True)
            self._tabs[secili_sekme] = [True, view, tab_key]

    def _tab_olustur(self, tab_key, parent):
        if tab_key == "stok_raporlari":
            from .stok_raporlari_view import StokRaporlariView
            return StokRaporlariView(parent, self.main_app)
        elif tab_key.startswith("ekstre_"):
            from .hesap_ekstresi_view import HesapEkstresiView
            hesap_turu = tab_key.split("_", 1)[1]
            return HesapEkstresiView(parent, self.main_app, hesap_turu=hesap_turu)
        elif tab_key == "hizmet_kartlari":
            from .hizmet_kartlari_raporu_view import HizmetKartlariRaporuView
            return HizmetKartlariRaporuView(parent, self.main_app)
        elif tab_key == "cek_senet":
            from .cek_senet_raporlari_view import CekSenetRaporlariView
            return CekSenetRaporlariView(parent, self.main_app)
        elif tab_key == "kdv":
            from .kdv_raporu_view import KdvRaporuView
            return KdvRaporuView(parent, self.main_app)
        elif tab_key == "cari_bakiye":
            from .cari_bakiye_raporu_view import CariBakiyeRaporuView
            return CariBakiyeRaporuView(parent, self.main_app)
        elif tab_key == "satis":
            from .satis_raporu_view import SatisRaporuView
            return SatisRaporuView(parent, self.main_app)
        return None

    def yenile(self):
        pass
