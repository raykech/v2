# -*- coding: utf-8 -*-
"""
Rapor sekme grubu: birden çok rapor görünümünü tek ana sekme altında iç
sekmelerle toplar (rapor gruplaması). İç sekmeler tembel (lazy) oluşturulur;
sekme ilk kez seçildiğinde yüklenir. StokRaporlariView deseni genelleştirildi.
"""
import tkinter as tk
from tkinter import ttk


class AltSekmeGrubu(tk.Frame):
    """(başlık, factory) listesi verilen iç sekme taşıyıcısı."""

    def __init__(self, parent, main_app, sekmeler):
        """sekmeler: [(baslik, factory), ...]; factory(parent, main_app) -> view"""
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self._sekmeler = {}  # baslik -> [olustu_mu, widget, factory]
        self.create_widgets(sekmeler)

    def create_widgets(self, sekmeler):
        self.inner_notebook = ttk.Notebook(self)
        self.inner_notebook.pack(fill="both", expand=True, padx=6, pady=6)

        for i, (baslik, factory) in enumerate(sekmeler):
            if i == 0:
                view = factory(self.inner_notebook, self.main_app)
                self.inner_notebook.add(view, text=baslik)
                self._sekmeler[baslik] = [True, view, factory]
            else:
                placeholder = tk.Frame(self.inner_notebook, bg="#f5f7fb")
                self.inner_notebook.add(placeholder, text=baslik)
                self._sekmeler[baslik] = [False, placeholder, factory]

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
        olustu, widget, factory = bilgi
        if olustu:
            return

        for child in widget.winfo_children():
            child.destroy()
        view = factory(widget, self.main_app)
        if view is not None:
            view.pack(fill="both", expand=True)
            self._sekmeler[baslik] = [True, view, factory]

    def yenile(self):
        """U6: görünen iç sekmenin yenile()'sını çağır (tembel sekmelerde lookup)."""
        try:
            baslik = self.inner_notebook.tab(self.inner_notebook.select(), "text")
        except Exception:
            return
        bilgi = self._sekmeler.get(baslik)
        if bilgi and bilgi[0] and hasattr(bilgi[1], "yenile"):
            bilgi[1].yenile()
