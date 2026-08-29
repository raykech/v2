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

NOT: Yükleme yalnızca gerçek kaydırma olaylarında tetiklenir (tekerlek,
klavye, scrollbar sürükleme). Kullanıcı aşağı inmedikçe arka planda
zamanlayıcı ile veri çekilmez.
"""
import tkinter as tk
import time
from tkinter import messagebox
from core.db import veritabani_baglan


class SayfaliListeMixin:
    SAYFA_BOYUTU = 50

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
        # Klavye kaydırma tuşları (ok, Page Up/Down, Home/End)
        tree.bind("<KeyRelease>", self._sayfa_keyrelease)
        # Scrollbar sürüklemesi: scrollbar'ın command'ı tree.yview olduğu için
        # yview metodunu sararak "moveto/scroll" çağrılarını yakalarız.
        self._sayfa_yview_original = tree.yview
        tree.yview = self._sayfa_yview_sarili

    def _sayfa_yview_sarili(self, *args):
        """Scrollbar'dan gelen yview('moveto'/'scroll') çağrılarında yükleme kontrolü yapar."""
        sonuc = self._sayfa_yview_original(*args)
        if args and args[0] in ("moveto", "scroll"):
            self._sayfa_kontrol_et()
        return sonuc

    def _sayfa_keyrelease(self, event):
        kaydirma_tuslari = {
            "Down", "Up", "Next", "Prior", "Page_Down", "Page_Up",
            "Home", "End", "KP_Down", "KP_Up", "KP_Next", "KP_Prior",
        }
        if event.keysym in kaydirma_tuslari:
            self._sayfa_kontrol_et()

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

    def _sayfa_kontrol_et(self, event=None):
        if self._sayfa_tukendi or self._sayfa_yukleniyor or not self._sayfa_query:
            return
        try:
            alt = self._sayfa_tree.yview()[1]
        except Exception:
            return
        # Alt %15'e inilince bir sonraki sayfayı yükle
        if alt >= 0.85:
            self._diger_sayfa_yukle()


    def _tum_veriyi_yukle(self):
        """Tüm sayfaları yükleyerek ağacı tamamen doldurur (dışa aktarım için)."""
        while not self._sayfa_tukendi and not self._sayfa_yukleniyor and self._sayfa_query:
            self._diger_sayfa_yukle()
    def _diger_sayfa_yukle(self):
        if self._sayfa_tukendi or self._sayfa_yukleniyor or not self._sayfa_query:
            return
        baslangic = time.perf_counter()
        onceki_yuklenen = self._sayfa_yuklenen
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
            sure_ms = (time.perf_counter() - baslangic) * 1000
            self._yukleme_suresi_goster(sure_ms, onceki_yuklenen)
            self._sayfa_yukleniyor = False

    def _yukleme_suresi_goster(self, sure_ms, onceki_yuklenen):
        """İlk/sayfa yükleme süresini ana pencerenin durum çubuğuna yazar."""
        try:
            main_app = getattr(self, "main_app", None)
            if main_app is None or not hasattr(main_app, "durum_yaz"):
                return
            etiket = "İlk yükleme" if onceki_yuklenen == 0 else "Sayfa yükleme"
            modul = type(self).__name__
            adet = self._sayfa_yuklenen - onceki_yuklenen
            main_app.durum_yaz(
                f"{modul} | {etiket}: {sure_ms:.1f} ms ({adet} kayıt, toplam {self._sayfa_yuklenen})"
            )
        except Exception:
            pass
