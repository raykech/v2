import tkinter as tk
from tkinter import ttk, messagebox

from core.db import veritabani_baglan
from core.services import (
    ayar_oku,
    ayar_yaz,
    EKSI_POLITIKA_SECENEKLERI,
    EKSI_POLITIKA_VARSAYILAN,
    AYAR_EKSI_KASA,
    AYAR_EKSI_BANKA,
    AYAR_EKSI_STOK,
)


class EksiCalismaView(tk.Frame):
    """Kasa / Banka / Stok için 'eksi çalışma' politikaları.

    Gerçek hayatta muhasebe akışını durdurmak istemeyiz: kullanıcı tüm
    satışları girip alışları sonra girebilir. Bu yüzden eksiye düşme
    durumunda ne olacağına kullanıcı karar verir. Rapor tarafında eksiler
    her halükârda kırmızı gösterilir; bu ayar yalnızca fiş kaydındaki
    davranışı (engelle/uyar/sessiz) belirler.
    """

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.secenekler = [etiket for etiket, _ in EKSI_POLITIKA_SECENEKLERI]
        self._politika_etiket_from_deger = {
            deger: etiket for etiket, deger in EKSI_POLITIKA_SECENEKLERI
        }
        self.create_widgets()
        self.yukle()

    def create_widgets(self):
        form = tk.LabelFrame(
            self, text="Eksiye düşüldüğünde ne yapılsın?", bg="#f5f7fb", padx=12, pady=12
        )
        form.pack(fill="x", padx=10, pady=10)

        self.cmb_kasa = self._politika_satiri(form, "Kasa:", 0)
        self.cmb_banka = self._politika_satiri(form, "Banka:", 1)
        self.cmb_stok = self._politika_satiri(form, "Stok:", 2)

        tk.Label(
            form,
            text=(
                "  Örnek: Stok 10 adet görünüp 12 adet satılırsa stok eksiye düşer.\n"
                "  İzin verme: 12'yi satmana engel olur. Uyar seçenekleri: kaydeder ama seni uyarır."
            ),
            bg="#f5f7fb",
            fg="#6c757d",
            justify="left",
            anchor="w",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 4))

        btn_frame = tk.Frame(self, bg="#f5f7fb")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(
            btn_frame, text="Kaydet", command=self.kaydet, bg="#198754", fg="white", width=12
        ).pack(side="left")

        tk.Label(
            self,
            text="Not: Eksiler, Raporlar › Düzeltilecekler sekmesinde ve raporlarda her halükârda kırmızı gösterilir.",
            bg="#f5f7fb",
            fg="#6c757d",
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def _politika_satiri(self, parent, etiket, satir):
        tk.Label(parent, text=etiket, bg="#f5f7fb").grid(
            row=satir, column=0, sticky="w", padx=(0, 8), pady=3
        )
        cmb = ttk.Combobox(parent, state="readonly", width=36, values=self.secenekler)
        cmb.grid(row=satir, column=1, sticky="w", pady=3)
        return cmb

    @staticmethod
    def _politika_deger_from_etiket(etiket):
        for et, deger in EKSI_POLITIKA_SECENEKLERI:
            if et == etiket:
                return deger
        return EKSI_POLITIKA_VARSAYILAN

    def yukle(self):
        conn = veritabani_baglan()
        cursor = conn.cursor()
        try:
            kasa = ayar_oku(cursor, self.main_app.aktif_firma_id, AYAR_EKSI_KASA, EKSI_POLITIKA_VARSAYILAN)
            banka = ayar_oku(cursor, self.main_app.aktif_firma_id, AYAR_EKSI_BANKA, EKSI_POLITIKA_VARSAYILAN)
            stok = ayar_oku(cursor, self.main_app.aktif_firma_id, AYAR_EKSI_STOK, EKSI_POLITIKA_VARSAYILAN)
        finally:
            conn.close()

        self.cmb_kasa.set(self._politika_etiket_from_deger.get(kasa, self.secenekler[2]))
        self.cmb_banka.set(self._politika_etiket_from_deger.get(banka, self.secenekler[2]))
        self.cmb_stok.set(self._politika_etiket_from_deger.get(stok, self.secenekler[2]))

    def kaydet(self):
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            ayar_yaz(cursor, self.main_app.aktif_firma_id, AYAR_EKSI_KASA,
                     self._politika_deger_from_etiket(self.cmb_kasa.get()))
            ayar_yaz(cursor, self.main_app.aktif_firma_id, AYAR_EKSI_BANKA,
                     self._politika_deger_from_etiket(self.cmb_banka.get()))
            ayar_yaz(cursor, self.main_app.aktif_firma_id, AYAR_EKSI_STOK,
                     self._politika_deger_from_etiket(self.cmb_stok.get()))
            conn.commit()
            messagebox.showinfo("Kaydedildi", "Eksi çalışma ayarları kaydedildi.", parent=self)
        except Exception as e:
            messagebox.showerror("Hata", f"Ayarlar kaydedilemedi: {e}", parent=self)
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def yenile(self):
        self.yukle()
