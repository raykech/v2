import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# v2 yapısındaki dosyalardan import yapıyoruz
from core.db import veritabani_baglan, tablolari_olustur
from ui.main_window import AnaPencere

class GirisPenceresi(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Firma ve Yıl Seçimi")
        self.geometry("400x250")
        self.resizable(False, False)

        self.secilen_firma_id = None
        self.secilen_yil = None
        self.secilen_firma_adi = None
        self.firma_sozluk = {}

        self.create_widgets()
        self.firmalari_yukle()

    def create_widgets(self):
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text="Muhasebe v2", font=("Arial", 16, "bold"), fg="#0d6efd").pack(pady=(0, 20))

        tk.Label(main_frame, text="Çalışılacak Firma:", font=("Arial", 10)).pack(anchor="w")
        self.cmb_firma = ttk.Combobox(main_frame, state="readonly", font=("Arial", 10))
        self.cmb_firma.pack(fill="x", pady=(5, 10))
        self.cmb_firma.bind("<<ComboboxSelected>>", self.firma_secildi)

        tk.Label(main_frame, text="Çalışma Yılı:", font=("Arial", 10)).pack(anchor="w")
        self.cmb_yil = ttk.Combobox(main_frame, state="readonly", font=("Arial", 10))
        self.cmb_yil.pack(fill="x", pady=5)

        # Şifre alanı ve Enter tuşu bağlama (v1'deki gibi)
        self.ent_sifre = tk.Entry(main_frame, show="*", font=("Arial", 10))
        self.ent_sifre.bind("<Return>", self.giris_yap)

        btn_giris = tk.Button(main_frame, text="Giriş Yap", command=self.giris_yap, bg="#198754", fg="white", font=("Arial", 11, "bold"), height=2)
        btn_giris.pack(fill="x", pady=(20, 0))

    def firmalari_yukle(self):
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("SELECT id, firma_adi FROM firmalar WHERE durum=1 ORDER BY firma_adi")
            firmalar = cursor.fetchall()
            conn.close()

            if not firmalar:
                messagebox.showerror("Kritik Hata", "Veritabanında aktif firma bulunamadı!")
                self.destroy()
                return

            self.firma_sozluk = {firma[1]: firma[0] for firma in firmalar}
            self.cmb_firma['values'] = list(self.firma_sozluk.keys())
            self.cmb_firma.current(0)
            self.firma_secildi()

        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Firmalar yüklenemedi: {e}")
            self.destroy()

    def firma_secildi(self, event=None):
        # Bu fonksiyon şimdilik boş, yıl seçimi mantığı ana uygulamada olacak
        mevcut_yil = datetime.now().year
        self.cmb_yil['values'] = [mevcut_yil, mevcut_yil - 1]
        self.cmb_yil.set(mevcut_yil)

    def giris_yap(self, event=None):
        firma_adi = self.cmb_firma.get()
        yil_str = self.cmb_yil.get()

        if not firma_adi or not yil_str:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir firma ve yıl seçin.")
            return

        self.secilen_firma_id = self.firma_sozluk[firma_adi]
        self.secilen_yil = int(yil_str)
        self.secilen_firma_adi = firma_adi

        self.destroy()

if __name__ == "__main__":
    tablolari_olustur()
    
    giris_app = GirisPenceresi()
    giris_app.mainloop()
    
    if giris_app.secilen_firma_id and giris_app.secilen_yil:
        main_app = AnaPencere(
            firma_id=giris_app.secilen_firma_id,
            firma_adi=giris_app.secilen_firma_adi,
            yil=giris_app.secilen_yil
        )
        main_app.mainloop()