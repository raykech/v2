# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox


class ImportPreviewDialog(tk.Toplevel):
    """
    Excel import önizleme penceresi.

    Parametreler:
        parent: tkinter parent widget
        title: pencere başlığı
        fisler: hazir_fisler listesi (her biri dict: fis_turu, tarih, fis_no, kasa_adi, hedef_kasa_adi, toplam_tutar, satir_sayisi, satir_nos)
        hatalar: hata mesajları listesi (string)
        uyarilar: uyarı mesajları listesi (string)
        on_import: callback, çağrıldığında import işlemini yapar. True dönmeli.
    """

    def __init__(self, parent, title, fisler, hatalar, uyarilar, on_import=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.fisler = fisler
        self.hatalar = hatalar
        self.uyarilar = uyarilar
        self.on_import = on_import
        self.create_widgets()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.wait_window()

    def create_widgets(self):
        ana_frame = tk.Frame(self, padx=15, pady=15)
        ana_frame.pack(fill="both", expand=True)

        # Özet
        if self.hatalar:
            ozet_text = f"⚠ {len(self.hatalar)} hata bulundu. Düzeltip tekrar yükleyin."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="red")
            etiket.pack(anchor="w", pady=(0, 10))
        elif self.uyarilar:
            ozet_text = f"✔ {len(self.fisler)} fiş içe aktarılacak. ({len(self.uyarilar)} uyarı var)"
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="#856404")
            etiket.pack(anchor="w", pady=(0, 10))
        else:
            ozet_text = f"✔ {len(self.fisler)} fiş içe aktarılacak."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="green")
            etiket.pack(anchor="w", pady=(0, 10))

        # Fiş listesi
        if self.fisler:
            liste_frame = tk.LabelFrame(ana_frame, text="İçe Aktarılacak Fişler", padx=5, pady=5)
            liste_frame.pack(fill="both", expand=True, pady=(0, 10))

            tree = ttk.Treeview(
                liste_frame,
                columns=("satir_sayisi", "fis_turu", "tarih", "fis_no", "kasa", "toplam_tutar"),
                show="headings",
                height=10,
            )
            tree.heading("satir_sayisi", text="Satır")
            tree.heading("fis_turu", text="Fiş Türü")
            tree.heading("tarih", text="Tarih")
            tree.heading("fis_no", text="Fiş No")
            tree.heading("kasa", text="Kasa")
            tree.heading("toplam_tutar", text="Toplam Tutar", anchor="e")

            tree.column("satir_sayisi", width=60, anchor="center", stretch=False)
            tree.column("fis_turu", width=180)
            tree.column("tarih", width=100, anchor="center")
            tree.column("fis_no", width=80)
            tree.column("kasa", width=180)
            tree.column("toplam_tutar", width=120, anchor="e")

            for fis in self.fisler:
                kasa_goruntule = fis.get("kasa_adi", "")
                if fis.get("hedef_kasa_adi"):
                    kasa_goruntule += " → " + fis["hedef_kasa_adi"]
                tree.insert("", "end", values=(
                    f"{len(fis.get('satir_nos', []))} satır",
                    fis.get("fis_turu", ""),
                    fis.get("tarih", ""),
                    fis.get("fis_no", ""),
                    kasa_goruntule,
                    f"{fis.get('toplam_tutar', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                ))

            vsb = ttk.Scrollbar(liste_frame, orient="vertical", command=tree.yview)
            vsb.pack(side="right", fill="y")
            tree.configure(yscrollcommand=vsb.set)
            tree.pack(side="left", fill="both", expand=True)

        # Hata alanı
        if self.hatalar:
            hata_frame = tk.LabelFrame(ana_frame, text="Hatalar", padx=5, pady=5, fg="red")
            hata_frame.pack(fill="x", pady=(0, 10))
            hata_text = tk.Text(hata_frame, height=6, wrap="word", fg="red", font=("Arial", 9))
            hata_text.pack(fill="x")
            for hata in self.hatalar:
                hata_text.insert("end", hata + "\n")
            hata_text.config(state="disabled")

        # Uyarı alanı
        if self.uyarilar:
            uyari_frame = tk.LabelFrame(ana_frame, text="Uyarılar", padx=5, pady=5, fg="#856404")
            uyari_frame.pack(fill="x", pady=(0, 10))
            uyari_text = tk.Text(uyari_frame, height=4, wrap="word", fg="#856404", font=("Arial", 9))
            uyari_text.pack(fill="x")
            for uyari in self.uyarilar:
                uyari_text.insert("end", uyari + "\n")
            uyari_text.config(state="disabled")

        # Butonlar
        buton_frame = tk.Frame(ana_frame)
        buton_frame.pack(fill="x")

        if not self.hatalar and self.fisler and self.on_import:
            btn_import = tk.Button(
                buton_frame,
                text="İçe Aktar",
                command=self._import,
                bg="#198754",
                fg="white",
                font=("Arial", 10, "bold"),
                padx=20,
                pady=5,
            )
            btn_import.pack(side="right", padx=(10, 0))

        btn_vazgec = tk.Button(
            buton_frame,
            text="Vazgeç",
            command=self.destroy,
            padx=20,
            pady=5,
        )
        btn_vazgec.pack(side="right")

    def _import(self):
        if self.on_import:
            try:
                sonuc = self.on_import()
                if sonuc:
                    self.destroy()
            except Exception as e:
                messagebox.showerror("İçe Aktarma Hatası", str(e), parent=self)


class DefinitionImportPreviewDialog(tk.Toplevel):
    """
    Tanım kartları (Cari, Stok, Hizmet) için önizleme penceresi.
    """

    def __init__(self, parent, title, kartlar, hatalar, uyarilar, on_import=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.kartlar = kartlar
        self.hatalar = hatalar
        self.uyarilar = uyarilar
        self.on_import = on_import
        self.create_widgets()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.wait_window()

    def create_widgets(self):
        ana_frame = tk.Frame(self, padx=15, pady=15)
        ana_frame.pack(fill="both", expand=True)

        if self.hatalar:
            ozet_text = f"⚠ {len(self.hatalar)} hata bulundu. Düzeltip tekrar yükleyin."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="red")
            etiket.pack(anchor="w", pady=(0, 10))
        elif self.uyarilar:
            ozet_text = f"✔ {len(self.kartlar)} kart içe aktarılacak. ({len(self.uyarilar)} uyarı var)"
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="#856404")
            etiket.pack(anchor="w", pady=(0, 10))
        else:
            ozet_text = f"✔ {len(self.kartlar)} kart içe aktarılacak."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="green")
            etiket.pack(anchor="w", pady=(0, 10))

        if self.kartlar:
            liste_frame = tk.LabelFrame(ana_frame, text="İçe Aktarılacak Kartlar", padx=5, pady=5)
            liste_frame.pack(fill="both", expand=True, pady=(0, 10))

            tree = ttk.Treeview(
                liste_frame,
                columns=("tur", "ad", "kod", "detay"),
                show="headings",
                height=10,
            )
            tree.heading("tur", text="Tür")
            tree.heading("ad", text="Ad")
            tree.heading("kod", text="Kod")
            tree.heading("detay", text="Detay")

            tree.column("tur", width=80, anchor="center", stretch=False)
            tree.column("ad", width=250)
            tree.column("kod", width=120, stretch=False)
            tree.column("detay", width=200)

            for kart in self.kartlar:
                tree.insert("", "end", values=(
                    kart.get("tur", ""),
                    kart.get("ad", ""),
                    kart.get("kod", ""),
                    kart.get("detay", ""),
                ))

            vsb = ttk.Scrollbar(liste_frame, orient="vertical", command=tree.yview)
            vsb.pack(side="right", fill="y")
            tree.configure(yscrollcommand=vsb.set)
            tree.pack(side="left", fill="both", expand=True)

        if self.hatalar:
            hata_frame = tk.LabelFrame(ana_frame, text="Hatalar", padx=5, pady=5, fg="red")
            hata_frame.pack(fill="x", pady=(0, 10))
            hata_text = tk.Text(hata_frame, height=6, wrap="word", fg="red", font=("Arial", 9))
            hata_text.pack(fill="x")
            for hata in self.hatalar:
                hata_text.insert("end", hata + "\n")
            hata_text.config(state="disabled")

        if self.uyarilar:
            uyari_frame = tk.LabelFrame(ana_frame, text="Uyarılar", padx=5, pady=5, fg="#856404")
            uyari_frame.pack(fill="x", pady=(0, 10))
            uyari_text = tk.Text(uyari_frame, height=4, wrap="word", fg="#856404", font=("Arial", 9))
            uyari_text.pack(fill="x")
            for uyari in self.uyarilar:
                uyari_text.insert("end", uyari + "\n")
            uyari_text.config(state="disabled")

        buton_frame = tk.Frame(ana_frame)
        buton_frame.pack(fill="x")

        if not self.hatalar and self.kartlar and self.on_import:
            btn_import = tk.Button(
                buton_frame,
                text="İçe Aktar",
                command=self._import,
                bg="#198754",
                fg="white",
                font=("Arial", 10, "bold"),
                padx=20,
                pady=5,
            )
            btn_import.pack(side="right", padx=(10, 0))

        btn_vazgec = tk.Button(
            buton_frame,
            text="Vazgeç",
            command=self.destroy,
            padx=20,
            pady=5,
        )
        btn_vazgec.pack(side="right")

    def _import(self):
        if self.on_import:
            try:
                sonuc = self.on_import()
                if sonuc:
                    self.destroy()
            except Exception as e:
                messagebox.showerror("İçe Aktarma Hatası", str(e), parent=self)


class FaturaImportPreviewDialog(tk.Toplevel):
    """
    Fatura import önizleme penceresi.
    """

    def __init__(self, parent, title, faturalar, hatalar, uyarilar, on_import=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.faturalar = faturalar
        self.hatalar = hatalar
        self.uyarilar = uyarilar
        self.on_import = on_import
        self.create_widgets()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.wait_window()

    def create_widgets(self):
        ana_frame = tk.Frame(self, padx=15, pady=15)
        ana_frame.pack(fill="both", expand=True)

        if self.hatalar:
            ozet_text = f"⚠ {len(self.hatalar)} hata bulundu. Düzeltip tekrar yükleyin."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="red")
            etiket.pack(anchor="w", pady=(0, 10))
        elif self.uyarilar:
            ozet_text = f"✔ {len(self.faturalar)} fatura içe aktarılacak. ({len(self.uyarilar)} uyarı var)"
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="#856404")
            etiket.pack(anchor="w", pady=(0, 10))
        else:
            ozet_text = f"✔ {len(self.faturalar)} fatura içe aktarılacak."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="green")
            etiket.pack(anchor="w", pady=(0, 10))

        if self.faturalar:
            liste_frame = tk.LabelFrame(ana_frame, text="İçe Aktarılacak Faturalar", padx=5, pady=5)
            liste_frame.pack(fill="both", expand=True, pady=(0, 10))

            tree = ttk.Treeview(
                liste_frame,
                columns=("satir_sayisi", "fis_turu", "tarih", "fis_no", "cari", "toplam_tutar"),
                show="headings",
                height=10,
            )
            tree.heading("satir_sayisi", text="Satır")
            tree.heading("fis_turu", text="Fatura Türü")
            tree.heading("tarih", text="Tarih")
            tree.heading("fis_no", text="Fatura No")
            tree.heading("cari", text="Cari / Ödeme")
            tree.heading("toplam_tutar", text="Toplam Tutar", anchor="e")

            tree.column("satir_sayisi", width=60, anchor="center", stretch=False)
            tree.column("fis_turu", width=180)
            tree.column("tarih", width=100, anchor="center")
            tree.column("fis_no", width=90)
            tree.column("cari", width=220)
            tree.column("toplam_tutar", width=120, anchor="e")

            for fatura in self.faturalar:
                cari_goruntule = fatura.get("cari_adi", "")
                if fatura.get("odeme_tipi") != "Vadeli":
                    cari_goruntule = f"{fatura.get('odeme_tipi', '')} / {fatura.get('odeme_hesap_adi', '')}"
                tree.insert("", "end", values=(
                    f"{len(fatura.get('satir_nos', []))} satır",
                    fatura.get("fis_turu", ""),
                    fatura.get("tarih", ""),
                    fatura.get("fis_no", ""),
                    cari_goruntule,
                    f"{fatura.get('toplam_tutar', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                ))

            vsb = ttk.Scrollbar(liste_frame, orient="vertical", command=tree.yview)
            vsb.pack(side="right", fill="y")
            tree.configure(yscrollcommand=vsb.set)
            tree.pack(side="left", fill="both", expand=True)

        if self.hatalar:
            hata_frame = tk.LabelFrame(ana_frame, text="Hatalar", padx=5, pady=5, fg="red")
            hata_frame.pack(fill="x", pady=(0, 10))
            hata_text = tk.Text(hata_frame, height=6, wrap="word", fg="red", font=("Arial", 9))
            hata_text.pack(fill="x")
            for hata in self.hatalar:
                hata_text.insert("end", hata + "\n")
            hata_text.config(state="disabled")

        if self.uyarilar:
            uyari_frame = tk.LabelFrame(ana_frame, text="Uyarılar", padx=5, pady=5, fg="#856404")
            uyari_frame.pack(fill="x", pady=(0, 10))
            uyari_text = tk.Text(uyari_frame, height=4, wrap="word", fg="#856404", font=("Arial", 9))
            uyari_text.pack(fill="x")
            for uyari in self.uyarilar:
                uyari_text.insert("end", uyari + "\n")
            uyari_text.config(state="disabled")

        buton_frame = tk.Frame(ana_frame)
        buton_frame.pack(fill="x")

        if not self.hatalar and self.faturalar and self.on_import:
            btn_import = tk.Button(
                buton_frame,
                text="İçe Aktar",
                command=self._import,
                bg="#198754",
                fg="white",
                font=("Arial", 10, "bold"),
                padx=20,
                pady=5,
            )
            btn_import.pack(side="right", padx=(10, 0))

        btn_vazgec = tk.Button(
            buton_frame,
            text="Vazgeç",
            command=self.destroy,
            padx=20,
            pady=5,
        )
        btn_vazgec.pack(side="right")

    def _import(self):
        if self.on_import:
            try:
                sonuc = self.on_import()
                if sonuc:
                    self.destroy()
            except Exception as e:
                messagebox.showerror("İçe Aktarma Hatası", str(e), parent=self)

class BankaImportPreviewDialog(tk.Toplevel):
    """
    Banka import önizleme penceresi.
    """

    def __init__(self, parent, title, fisler, hatalar, uyarilar, on_import=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.fisler = fisler
        self.hatalar = hatalar
        self.uyarilar = uyarilar
        self.on_import = on_import
        self.create_widgets()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.wait_window()

    def create_widgets(self):
        ana_frame = tk.Frame(self, padx=15, pady=15)
        ana_frame.pack(fill="both", expand=True)

        if self.hatalar:
            ozet_text = f"⚠ {len(self.hatalar)} hata bulundu. Düzeltip tekrar yükleyin."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="red")
            etiket.pack(anchor="w", pady=(0, 10))
        elif self.uyarilar:
            ozet_text = f"✔ {len(self.fisler)} fiş içe aktarılacak. ({len(self.uyarilar)} uyarı var)"
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="#856404")
            etiket.pack(anchor="w", pady=(0, 10))
        else:
            ozet_text = f"✔ {len(self.fisler)} fiş içe aktarılacak."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="green")
            etiket.pack(anchor="w", pady=(0, 10))

        if self.fisler:
            liste_frame = tk.LabelFrame(ana_frame, text="İçe Aktarılacak Fişler", padx=5, pady=5)
            liste_frame.pack(fill="both", expand=True, pady=(0, 10))

            tree = ttk.Treeview(
                liste_frame,
                columns=("satir_sayisi", "fis_turu", "tarih", "fis_no", "banka", "toplam_tutar"),
                show="headings",
                height=10,
            )
            tree.heading("satir_sayisi", text="Satır")
            tree.heading("fis_turu", text="Fiş Türü")
            tree.heading("tarih", text="Tarih")
            tree.heading("fis_no", text="Fiş No")
            tree.heading("banka", text="Banka")
            tree.heading("toplam_tutar", text="Toplam Tutar", anchor="e")

            tree.column("satir_sayisi", width=60, anchor="center", stretch=False)
            tree.column("fis_turu", width=180)
            tree.column("tarih", width=100, anchor="center")
            tree.column("fis_no", width=80)
            tree.column("banka", width=220)
            tree.column("toplam_tutar", width=120, anchor="e")

            for fis in self.fisler:
                banka_goruntule = fis.get("kasa_adi", "")
                if fis.get("hedef_kasa_adi"):
                    banka_goruntule += " → " + fis["hedef_kasa_adi"]
                tree.insert("", "end", values=(
                    f"{len(fis.get('satir_nos', []))} satır",
                    fis.get("fis_turu", ""),
                    fis.get("tarih", ""),
                    fis.get("fis_no", ""),
                    banka_goruntule,
                    f"{fis.get('toplam_tutar', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                ))

            vsb = ttk.Scrollbar(liste_frame, orient="vertical", command=tree.yview)
            vsb.pack(side="right", fill="y")
            tree.configure(yscrollcommand=vsb.set)
            tree.pack(side="left", fill="both", expand=True)

        if self.hatalar:
            hata_frame = tk.LabelFrame(ana_frame, text="Hatalar", padx=5, pady=5, fg="red")
            hata_frame.pack(fill="x", pady=(0, 10))
            hata_text = tk.Text(hata_frame, height=6, wrap="word", fg="red", font=("Arial", 9))
            hata_text.pack(fill="x")
            for hata in self.hatalar:
                hata_text.insert("end", hata + "\n")
            hata_text.config(state="disabled")

        if self.uyarilar:
            uyari_frame = tk.LabelFrame(ana_frame, text="Uyarılar", padx=5, pady=5, fg="#856404")
            uyari_frame.pack(fill="x", pady=(0, 10))
            uyari_text = tk.Text(uyari_frame, height=4, wrap="word", fg="#856404", font=("Arial", 9))
            uyari_text.pack(fill="x")
            for uyari in self.uyarilar:
                uyari_text.insert("end", uyari + "\n")
            uyari_text.config(state="disabled")

        buton_frame = tk.Frame(ana_frame)
        buton_frame.pack(fill="x")

        if not self.hatalar and self.fisler and self.on_import:
            btn_import = tk.Button(
                buton_frame,
                text="İçe Aktar",
                command=self._import,
                bg="#198754",
                fg="white",
                font=("Arial", 10, "bold"),
                padx=20,
                pady=5,
            )
            btn_import.pack(side="right", padx=(10, 0))

        btn_vazgec = tk.Button(
            buton_frame,
            text="Vazgeç",
            command=self.destroy,
            padx=20,
            pady=5,
        )
        btn_vazgec.pack(side="right")

    def _import(self):
        if self.on_import:
            try:
                sonuc = self.on_import()
                if sonuc:
                    self.destroy()
            except Exception as e:
                messagebox.showerror("İçe Aktarma Hatası", str(e), parent=self)

                if sonuc:
                    self.destroy()
            except Exception as e:
                messagebox.showerror("İçe Aktarma Hatası", str(e), parent=self)

class CariImportPreviewDialog(tk.Toplevel):
    """Cari import önizleme penceresi."""

    def __init__(self, parent, title, fisler, hatalar, uyarilar, on_import=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.fisler = fisler
        self.hatalar = hatalar
        self.uyarilar = uyarilar
        self.on_import = on_import
        self.create_widgets()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.wait_window()

    def create_widgets(self):
        ana_frame = tk.Frame(self, padx=15, pady=15)
        ana_frame.pack(fill="both", expand=True)

        if self.hatalar:
            ozet_text = f"\u26a0 {len(self.hatalar)} hata bulundu. D\u00fczeltip tekrar y\u00fckleyin."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="red")
            etiket.pack(anchor="w", pady=(0, 10))
        elif self.uyarilar:
            ozet_text = f"\u2714 {len(self.fisler)} fi\u015f i\u00e7e aktar\u0131lacak. ({len(self.uyarilar)} uyar\u0131 var)"
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="#856404")
            etiket.pack(anchor="w", pady=(0, 10))
        else:
            ozet_text = f"\u2714 {len(self.fisler)} fi\u015f i\u00e7e aktar\u0131lacak."
            etiket = tk.Label(ana_frame, text=ozet_text, font=("Arial", 10, "bold"), fg="green")
            etiket.pack(anchor="w", pady=(0, 10))

        if self.fisler:
            liste_frame = tk.LabelFrame(ana_frame, text="\u0130\u00e7e Aktar\u0131lacak Fi\u015fler", padx=5, pady=5)
            liste_frame.pack(fill="both", expand=True, pady=(0, 10))
            tree = ttk.Treeview(
                liste_frame,
                columns=("satir_sayisi", "fis_turu", "tarih", "fis_no", "detay", "toplam_tutar"),
                show="headings", height=10,
            )
            tree.heading("satir_sayisi", text="Sat\u0131r")
            tree.heading("fis_turu", text="Fi\u015f T\u00fcr\u00fc")
            tree.heading("tarih", text="Tarih")
            tree.heading("fis_no", text="Fi\u015f No")
            tree.heading("detay", text="Detay")
            tree.heading("toplam_tutar", text="Toplam Tutar", anchor="e")
            tree.column("satir_sayisi", width=60, anchor="center", stretch=False)
            tree.column("fis_turu", width=150)
            tree.column("tarih", width=100, anchor="center")
            tree.column("fis_no", width=80)
            tree.column("detay", width=220)
            tree.column("toplam_tutar", width=120, anchor="e")
            for fis in self.fisler:
                detay = fis.get("odeme_turu", "") or fis.get("fis_turu", "")
                tree.insert("", "end", values=(
                    f"{len(fis.get('satir_nos', []))} sat\u0131r",
                    fis.get("fis_turu", ""),
                    fis.get("tarih", ""),
                    fis.get("fis_no", ""),
                    detay,
                    f"{fis.get('toplam_tutar', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                ))
            vsb = ttk.Scrollbar(liste_frame, orient="vertical", command=tree.yview)
            vsb.pack(side="right", fill="y")
            tree.configure(yscrollcommand=vsb.set)
            tree.pack(side="left", fill="both", expand=True)

        if self.hatalar:
            hata_frame = tk.LabelFrame(ana_frame, text="Hatalar", padx=5, pady=5, fg="red")
            hata_frame.pack(fill="x", pady=(0, 10))
            hata_text = tk.Text(hata_frame, height=6, wrap="word", fg="red", font=("Arial", 9))
            hata_text.pack(fill="x")
            for hata in self.hatalar:
                hata_text.insert("end", hata + "\n")
            hata_text.config(state="disabled")

        if self.uyarilar:
            uyari_frame = tk.LabelFrame(ana_frame, text="Uyar\u0131lar", padx=5, pady=5, fg="#856404")
            uyari_frame.pack(fill="x", pady=(0, 10))
            uyari_text = tk.Text(uyari_frame, height=4, wrap="word", fg="#856404", font=("Arial", 9))
            uyari_text.pack(fill="x")
            for uyari in self.uyarilar:
                uyari_text.insert("end", uyari + "\n")
            uyari_text.config(state="disabled")

        buton_frame = tk.Frame(ana_frame)
        buton_frame.pack(fill="x")
        if not self.hatalar and self.fisler and self.on_import:
            btn_import = tk.Button(
                buton_frame, text="\u0130\u00e7e Aktar", command=self._import,
                bg="#198754", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5,
            )
            btn_import.pack(side="right", padx=(10, 0))
        btn_vazgec = tk.Button(buton_frame, text="Vazge\u00e7", command=self.destroy, padx=20, pady=5)
        btn_vazgec.pack(side="right")

    def _import(self):
        if self.on_import:
            try:
                sonuc = self.on_import()
                if sonuc:
                    self.destroy()
            except Exception as e:
                messagebox.showerror("\u0130\u00e7e Aktarma Hatas\u0131", str(e), parent=self)

class CekSenetImportPreviewDialog(tk.Toplevel):
    """Çek/Senet import önizleme penceresi."""

    def __init__(self, parent, title, fisler, hatalar, uyarilar, on_import=None):
        super().__init__(parent)
        self.title(title); self.transient(parent); self.grab_set()
        self.fisler = fisler; self.hatalar = hatalar; self.uyarilar = uyarilar; self.on_import = on_import
        self.create_widgets(); self.lift(); self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False)); self.wait_window()

    def create_widgets(self):
        ana_frame = tk.Frame(self, padx=15, pady=15); ana_frame.pack(fill="both", expand=True)
        if self.hatalar:
            tk.Label(ana_frame, text=f"\u26a0 {len(self.hatalar)} hata bulundu.", font=("Arial", 10, "bold"), fg="red").pack(anchor="w", pady=(0, 10))
        else:
            tk.Label(ana_frame, text=f"\u2714 {len(self.fisler)} fi\u015f i\u00e7e aktar\u0131lacak.", font=("Arial", 10, "bold"), fg="green").pack(anchor="w", pady=(0, 10))
        if self.fisler:
            liste_frame = tk.LabelFrame(ana_frame, text="\u0130\u00e7e Aktar\u0131lacak Fi\u015fler", padx=5, pady=5); liste_frame.pack(fill="both", expand=True, pady=(0, 10))
            tree = ttk.Treeview(liste_frame, columns=("seri", "fis_turu", "tarih", "fis_no", "tutar"), show="headings", height=10)
            tree.heading("seri", text="Seri No"); tree.heading("fis_turu", text="Fi\u015f T\u00fcr\u00fc"); tree.heading("tarih", text="Tarih"); tree.heading("fis_no", text="Fi\u015f No"); tree.heading("tutar", text="Tutar", anchor="e")
            tree.column("seri", width=140); tree.column("fis_turu", width=180); tree.column("tarih", width=100); tree.column("fis_no", width=100); tree.column("tutar", width=120, anchor="e")
            for fis in self.fisler:
                tree.insert("", "end", values=(fis.get("seri_no", ""), fis.get("fis_turu", ""), fis.get("tarih", ""), fis.get("fis_no", ""), f"{fis.get('toplam_tutar', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")))
            vsb = ttk.Scrollbar(liste_frame, orient="vertical", command=tree.yview); vsb.pack(side="right", fill="y"); tree.configure(yscrollcommand=vsb.set); tree.pack(side="left", fill="both", expand=True)
        if self.hatalar:
            hata_frame = tk.LabelFrame(ana_frame, text="Hatalar", padx=5, pady=5, fg="red"); hata_frame.pack(fill="x", pady=(0, 10))
            hata_text = tk.Text(hata_frame, height=6, wrap="word", fg="red", font=("Arial", 9)); hata_text.pack(fill="x")
            for hata in self.hatalar: hata_text.insert("end", hata + "\n")
            hata_text.config(state="disabled")
        buton_frame = tk.Frame(ana_frame); buton_frame.pack(fill="x")
        if not self.hatalar and self.fisler and self.on_import:
            tk.Button(buton_frame, text="\u0130\u00e7e Aktar", command=self._import, bg="#198754", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5).pack(side="right", padx=(10, 0))
        tk.Button(buton_frame, text="Vazge\u00e7", command=self.destroy, padx=20, pady=5).pack(side="right")

    def _import(self):
        if self.on_import:
            try:
                sonuc = self.on_import()
                if sonuc: self.destroy()
            except Exception as e:
                messagebox.showerror("\u0130\u00e7e Aktarma Hatas\u0131", str(e), parent=self)
