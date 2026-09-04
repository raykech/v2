import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from core.db import veritabani_baglan
from core.services import eksi_duzeltilecekler
from utils.formatters import format_currency, format_date, format_miktar


class DuzeltileceklerView(tk.Frame):
    """Raporlar › Düzeltilecekler.

    Seçili dönemde SORUNLU olan Kasa / Banka / Stok hesap-kartlarını,
    her biri için TEK özet satırı olarak listeler:
      • Kasa/Banka → dönem sonu bakiyesi eksi olan hesaplar.
      • Stok       → dönem sonu miktarı eksi VEYA 'maliyetsiz satış'
                     (satış, alıştan önce girildiği için maliyeti 0 hesaplanmış)
                     içeren kartlar.
    Üstte dönem filtresi, altta iç içe sekmeler: Özet + Kasa + Banka + Stok.
    Bir satıra çift tıklayınca sorunun başladığı fişe gider. Ayar "sessiz" olsa
    bile bu rapor her zaman çalışır (fikir: kullanıcıyı kırmadan görünür kılmak).
    """

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self._veri = {"Kasa": [], "Banka": [], "Stok": []}
        self.create_widgets()

    # --------------------------------------------------------------- arayüz
    def create_widgets(self):
        filtre = tk.LabelFrame(self, text="Dönem", bg="#f5f7fb", padx=10, pady=8)
        filtre.pack(fill="x", padx=10, pady=8)

        tk.Label(filtre, text="Baş. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.ent_bas = self._tarih(filtre, datetime(self.main_app.aktif_yil, 1, 1))
        tk.Label(filtre, text="Bit. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(10, 2))
        self.ent_bit = self._tarih(filtre, datetime(self.main_app.aktif_yil, 12, 31))

        tk.Button(filtre, text="Listele", command=self.listele, bg="#0d6efd", fg="white").pack(side="left", padx=(12, 0))
        tk.Label(
            filtre,
            text="   İpucu: bir satıra çift tıklayarak sorunun başladığı fişe gidebilirsiniz.",
            bg="#f5f7fb", fg="#6c757d",
        ).pack(side="left")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tab_ozet = tk.Frame(self.nb, bg="#f5f7fb")
        self.tab_kasa = tk.Frame(self.nb, bg="#f5f7fb")
        self.tab_banka = tk.Frame(self.nb, bg="#f5f7fb")
        self.tab_stok = tk.Frame(self.nb, bg="#f5f7fb")
        self.nb.add(self.tab_ozet, text="Özet")
        self.nb.add(self.tab_kasa, text="Kasa")
        self.nb.add(self.tab_banka, text="Banka")
        self.nb.add(self.tab_stok, text="Stok")

        self._ozet_tree = self._build_ozet(self.tab_ozet)
        self.tree_kasa = self._build_para_tab(self.tab_kasa)
        self.tree_banka = self._build_para_tab(self.tab_banka)
        self.tree_stok = self._build_stok_tab(self.tab_stok)

    def _tarih(self, parent, default):
        from tkcalendar import DateEntry
        de = DateEntry(parent, date_pattern="dd.mm.yyyy", width=12)
        de.set_date(default)
        de.pack(side="left")
        return de

    def _build_ozet(self, parent):
        tree = ttk.Treeview(
            parent, columns=("modul", "adet", "durum"), show="headings", height=6
        )
        tree.heading("modul", text="Modül")
        tree.heading("adet", text="Sorunlu hesap/kart", anchor="e")
        tree.heading("durum", text="Durum")
        tree.column("modul", width=160, anchor="w")
        tree.column("adet", width=180, anchor="e")
        tree.column("durum", width=360, anchor="w")
        tree.tag_configure('temiz', foreground='#198754')
        tree.tag_configure('var', background='#f8d7da', foreground='#842029', font=('Arial', 9, 'bold'))
        tk.Label(
            parent,
            text="Seçili dönemde sorunu olan hesap/kart sayısı. Bir modül sekmesine geçip "
                 "kartları görebilir, çift tıklayarak sorunun başladığı fişe gidebilirsiniz.\n"
                 "Kasa/Banka: dönem sonu bakiyesi eksi.  Stok: dönem sonu eksi veya maliyetsiz satış.",
            bg="#f5f7fb", fg="#6c757d", wraplength=700, justify="left",
        ).pack(anchor="w", padx=8, pady=8)
        tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        return tree

    def _build_para_tab(self, parent):
        container = tk.Frame(parent, bg="#f5f7fb")
        container.pack(fill="both", expand=True)
        kolonlar = ("hesap", "ilk_tarih", "adet", "son", "neden")
        tree = ttk.Treeview(container, columns=kolonlar, show="headings")
        basliklar = {
            "hesap": "Hesap", "ilk_tarih": "İlk eksi tarihi",
            "adet": "Eksi hareket", "son": "Dönem sonu", "neden": "Açıklama",
        }
        for k in kolonlar:
            anchor = "e" if k in ("adet", "son") else ("center" if k == "ilk_tarih" else "w")
            tree.heading(k, text=basliklar[k], anchor=anchor)
        tree.column("hesap", width=200)
        tree.column("ilk_tarih", width=120, anchor="center")
        tree.column("adet", width=100, anchor="e")
        tree.column("son", width=140, anchor="e")
        tree.column("neden", width=320)
        self._attach_scroll(container, tree)
        tree.tag_configure('eksi', background='#f8d7da', foreground='#842029')
        return tree

    def _build_stok_tab(self, parent):
        container = tk.Frame(parent, bg="#f5f7fb")
        container.pack(fill="both", expand=True)
        kolonlar = ("kart", "ilk_tarih", "maliyetsiz", "son", "neden")
        tree = ttk.Treeview(container, columns=kolonlar, show="headings")
        basliklar = {
            "kart": "Stok Kartı", "ilk_tarih": "İlk sorun tarihi",
            "maliyetsiz": "Maliyetsiz satış", "son": "Dönem sonu", "neden": "Açıklama",
        }
        for k in kolonlar:
            anchor = "e" if k in ("maliyetsiz", "son") else ("center" if k == "ilk_tarih" else "w")
            tree.heading(k, text=basliklar[k], anchor=anchor)
        tree.column("kart", width=200)
        tree.column("ilk_tarih", width=120, anchor="center")
        tree.column("maliyetsiz", width=140, anchor="e")
        tree.column("son", width=120, anchor="e")
        tree.column("neden", width=320)
        self._attach_scroll(container, tree)
        tree.tag_configure('eksi', background='#f8d7da', foreground='#842029')
        tree.tag_configure('maliyetsiz', background='#fff3cd', foreground='#7a5b00')
        return tree

    def _attach_scroll(self, container, tree):
        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)

    # --------------------------------------------------------------- veri
    def listele(self):
        bas = self.ent_bas.get_date().strftime("%Y-%m-%d")
        bit = self.ent_bit.get_date().strftime("%Y-%m-%d")
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            self._veri = eksi_duzeltilecekler(cursor, self.main_app.aktif_firma_id, bas, bit)
        except Exception as e:
            messagebox.showerror("Hata", f"Düzeltilecekler yüklenemedi: {e}", parent=self)
            return
        finally:
            if conn:
                conn.close()
        self._draw_ozet()
        self._draw_para(self.tree_kasa, "Kasa")
        self._draw_para(self.tree_banka, "Banka")
        self._draw_stok()

    def _draw_ozet(self):
        for i in self._ozet_tree.get_children():
            self._ozet_tree.delete(i)
        toplam = 0
        aciklama = {
            "Kasa": "bakiyesi eksi hesap",
            "Banka": "bakiyesi eksi hesap",
            "Stok": "eksi/maliyetsiz kart",
        }
        for tur in ("Kasa", "Banka", "Stok"):
            adet = len(self._veri[tur])
            toplam += adet
            durum = "Sorun yok" if adet == 0 else f"{adet} {aciklama[tur]}"
            tag = 'temiz' if adet == 0 else 'var'
            self._ozet_tree.insert("", "end", values=(tur, adet, durum), tags=(tag,))
        self._ozet_tree.insert("", "end", values=("TOPLAM", toplam, ""), tags=('var' if toplam else 'temiz',))

    def _para_neden(self, r):
        return "Dönem sonu bakiye eksi (fazla ödeme/çıkış)"

    def _draw_para(self, tree, tur):
        for i in tree.get_children():
            tree.delete(i)
        harita = {}
        for r in self._veri[tur]:
            iid = tree.insert("", "end", values=(
                r["hesap_adi"],
                format_date(r["ilk_tarih"]) if r["ilk_tarih"] else "-",
                r["eksi_satir"],
                format_currency(r["donem_sonu"]),
                self._para_neden(r),
            ), tags=('eksi',))
            harita[iid] = r
        tree._duzelt_map = harita
        tree.bind("<Double-1>", lambda e, t=tur, tr=tree: self._cift_tikla(e, t, tr), add="+")

    def _stok_neden(self, r):
        eksik = r["donem_sonu"] < -0.01
        mal = (r["maliyetsiz"] or 0) > 0.01
        if eksik and mal:
            return "Dönem sonu stok eksi + maliyetsiz satış"
        if eksik:
            return "Dönem sonu stok eksi"
        return "Maliyetsiz satış (maliyet 0 hesaplandı)"

    def _draw_stok(self):
        tree = self.tree_stok
        for i in tree.get_children():
            tree.delete(i)
        harita = {}
        for r in self._veri["Stok"]:
            eksik = r["donem_sonu"] < -0.01
            tag = 'eksi' if eksik else 'maliyetsiz'
            iid = tree.insert("", "end", values=(
                r["hesap_adi"],
                format_date(r["ilk_tarih"]) if r["ilk_tarih"] else "-",
                f"{format_miktar(r['maliyetsiz'] or 0)} adet",
                f"{format_miktar(r['donem_sonu'])} adet",
                self._stok_neden(r),
            ), tags=(tag,))
            harita[iid] = r
        tree._duzelt_map = harita
        tree.bind("<Double-1>", lambda e, tr=tree: self._cift_tikla(e, "Stok", tr), add="+")

    def _cift_tikla(self, event, tur, tree):
        iid = tree.identify_row(event.y)
        if not iid:
            return
        r = getattr(tree, "_duzelt_map", {}).get(iid)
        if not r:
            return
        fis_id = r.get("ilk_fis_id")
        if not fis_id:
            messagebox.showinfo(
                "Fiş bulunamadı",
                "Bu kartta hareket fişi tarihsiz/eşleşmez görünüyor.",
                parent=self,
            )
            return
        bilgi = self._fis_bilgisi(fis_id)
        if bilgi is None:
            return
        yil, fis_turu = bilgi
        if yil is not None and yil != self.main_app.aktif_yil:
            messagebox.showwarning(
                "Farklı Yıl",
                f"Bu fiş {yil} yılına ait; çalışma yılı {self.main_app.aktif_yil}.\n"
                "Yılı değiştirip tekrar deneyin.",
                parent=self,
            )
            return
        modul = self._modul_adi(tur, fis_turu)
        if hasattr(self.main_app, "go_to_module_and_select_fis"):
            self.main_app.go_to_module_and_select_fis(modul, fis_id)

    def _modul_adi(self, tur, fis_turu):
        ft = fis_turu or ""
        if "Çek" in ft or "Senet" in ft:
            return "cek_senet"
        if tur == "Stok":
            return "fatura"
        if tur == "Kasa":
            return "kasa"
        if tur == "Banka":
            return "banka"
        return "fatura"

    def _fis_bilgisi(self, fis_id):
        """(yil, fis_turu) döndürür; bulunamazsa None."""
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("SELECT yil, fis_turu FROM fisler WHERE id=?", (fis_id,))
            return cursor.fetchone()
        except Exception:
            return None
        finally:
            if conn:
                conn.close()

    def yenile(self):
        # Sekmeye geçişte otomatik listeleme yok; kullanıcı "Listele"ye basar.
        pass
