# -*- coding: utf-8 -*-
"""
Stok Raporları: tüm stok raporlarını tek ana sekme altında toplar.

İç sekmeler tembel (lazy) oluşturulur; sekme ilk kez seçildiğinde yüklenir.
"""
import tkinter as tk
from tkinter import ttk


class StokRaporlariView(tk.Frame):
    """Stok raporlarının ana taşıyıcısı (iç sekme grubu)."""

    # (sekme başlığı, iç sekme anahtarı)
    ALTK_SEKMELER = [
        ("Stok Durum", "stok_durum"),
        ("Stok Ekstresi", "stok_ekstresi"),
        ("En Çok Satan", "satis_cok"),
        ("Az Satan", "satis_az"),
        ("Hiç Satış Yapmayan", "satis_yok"),
        ("En Çok Hareket Gören", "hareket"),
        ("Kârlılık", "karlik"),
    ]

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self._sekmeler = {}  # başlık -> [oluştu_mu, widget, anahtar]
        self.create_widgets()

    def create_widgets(self):
        self.inner_notebook = ttk.Notebook(self)
        self.inner_notebook.pack(fill="both", expand=True, padx=6, pady=6)

        # İlk iç sekme hemen oluşturulur; gerisi placeholder içinde bekler.
        for i, (baslik, anahtar) in enumerate(self.ALTK_SEKMELER):
            if i == 0:
                view = self._alt_sekme_olustur(anahtar, self.inner_notebook)
                self.inner_notebook.add(view, text=baslik)
                self._sekmeler[baslik] = [True, view, anahtar]
            else:
                placeholder = tk.Frame(self.inner_notebook, bg="#f5f7fb")
                self.inner_notebook.add(placeholder, text=baslik)
                self._sekmeler[baslik] = [False, placeholder, anahtar]

        self.inner_notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event):
        # Yalnızca bu notebook'un kendi olayını işle (iç içe sekmelerde karışmasın)
        if event.widget is not self.inner_notebook:
            return
        try:
            baslik = self.inner_notebook.tab(self.inner_notebook.select(), "text")
        except Exception:
            return
        bilgi = self._sekmeler.get(baslik)
        if bilgi is None:
            return
        olustu, widget, anahtar = bilgi
        if olustu:
            return

        for child in widget.winfo_children():
            child.destroy()
        view = self._alt_sekme_olustur(anahtar, widget)
        if view is not None:
            view.pack(fill="both", expand=True)
            self._sekmeler[baslik] = [True, view, anahtar]

    def _alt_sekme_olustur(self, anahtar, parent):
        if anahtar == "stok_durum":
            from .stok_durum_raporu_view import StokDurumRaporuView
            return StokDurumRaporuView(parent, self.main_app)
        if anahtar == "stok_ekstresi":
            from .hesap_ekstresi_view import HesapEkstresiView
            return HesapEkstresiView(parent, self.main_app, hesap_turu="Stok")
        if anahtar in ("satis_cok", "satis_az"):
            from .stok_satis_raporu_view import StokSatisRaporuView
            return StokSatisRaporuView(parent, self.main_app,
                                       mod="cok" if anahtar == "satis_cok" else "az")
        if anahtar == "satis_yok":
            from .stok_satis_raporu_view import StokHicSatisRaporuView
            return StokHicSatisRaporuView(parent, self.main_app)
        if anahtar == "hareket":
            from .stok_hareket_raporu_view import StokHareketRaporuView
            return StokHareketRaporuView(parent, self.main_app)
        if anahtar == "karlik":
            from .stok_karlik_raporu_view import StokKarlikRaporuView
            return StokKarlikRaporuView(parent, self.main_app)
        return None

    def yenile(self):
        try:
            secili = self.inner_notebook.nametowidget(self.inner_notebook.select())
        except Exception:
            return
        if hasattr(secili, 'yenile'):
            secili.yenile()
