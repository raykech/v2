# -*- coding: utf-8 -*-
"""
Aşağı kaydıkça yükleyen (infinite scroll) Treeview sayfalama yardımcısı.

Kullanım:
  - Sınıf bu mixin'i miras alır:  class XModulu(SayfaliListeMixin, tk.Frame)
  - create_widgets içinde Treeview + scrollbar kurulduktan sonra:
        self._init_sayfalama(self.tree)
  - listele içinde sorguyu/parametreleri kurup kaydedin, sonra ilk sayfayı çekin:
        self._sayfa_query = query        # LIMIT/OFFSET EKLEMEYİN
        self._sayfa_params = params
        self._diger_sayfa_yukle()        # ilk sayfa (LIMIT SAYFA_BOYUTU)
  - Satır ekleme mantığı _satirlari_ekle(rows) metodunda olmalıdır.
  - Filtre değişince listele() yeniden çağrılır; listele başında:
        for i in self.tree.get_children(): self.tree.delete(i)
        self._sayfa_yuklenen = 0
        self._sayfa_tukendi = False
"""
import tkinter as tk
from tkinter import messagebox
from core.db import veritabani_baglan


class SayfaliListeMixin:
    SAYFA_BOYUTU = 200

    def _init_sayfalama(self, tree):
        self._sayfa_tree = tree
        self._sayfa_yuklenen = 0
        self._sayfa_tukendi = False
        self._sayfa_yukleniyor = False
        self._sayfa_query = None
        self._sayfa_params = []
        # Windows / macOS tekerlek + Linux buton 4/5
        tree.bind("<MouseWheel>", self._sayfa_mousewheel)
        tree.bind("<Button-4>", self._sayfa_mousewheel)
        tree.bind("<Button-5>", self._sayfa_mousewheel)

    def _sayfa_mousewheel(self, event):
        if event.num == 4:
            delta = 1
        elif event.num == 5:
            delta = -1
        else:
            delta = int(-1 * (event.delta / 120))
        try:
            self._sayfa_tree.yview_scroll(delta, "units")
        except Exception:
            pass
        self._sayfa_kontrol_et()
        return "break"

    def _sayfa_kontrol_et(self):
        if self._sayfa_tukendi or self._sayfa_yukleniyor or not self._sayfa_query:
            return
        try:
            alt = self._sayfa_tree.yview()[1]
        except Exception:
            return
        # Alt %15'e inilince bir sonraki sayfayı yükle
        if alt >= 0.85:
            self._diger_sayfa_yukle()

    def _diger_sayfa_yukle(self):
        if self._sayfa_tukendi or self._sayfa_yukleniyor or not self._sayfa_query:
            return
        self._sayfa_yukleniyor = True
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            query = self._sayfa_query + " LIMIT ? OFFSET ?"
            cursor.execute(query, self._sayfa_params + [self.SAYFA_BOYUTU, self._sayfa_yuklenen])
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                self._sayfa_tukendi = True
                return
            self._satirlari_ekle(rows)
            self._sayfa_yuklenen += len(rows)
            if len(rows) < self.SAYFA_BOYUTU:
                self._sayfa_tukendi = True
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası",
                                 f"Liste yüklenemedi: {e}",
                                 parent=self._sayfa_tree if self._sayfa_tree else None)
        finally:
            self._sayfa_yukleniyor = False
