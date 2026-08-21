import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
from core.db import (
    veritabani_baglan
)
from core.services import kaydet_kart
from utils.formatters import parse_currency

def ac_kart_dialog(parent, tablo_adi, item_id=None, firma_id=1, kart_turu=None):
    dialog_map = {
        "cariler": CariDialog,
        "stoklar": StokDialog,
        "kasalar": KasaDialog,
        "banka_kurumlari": BankaKurumDialog,
        "hizmet_kartlari": HizmetDialog,
        "hizmet_kartlari_gruplari": HizmetKartGrupDialog,
        "stok_kategorileri": GenelTanimDialog,
        "stok_birimleri": GenelTanimDialog,
    }
    
    dialog_class = dialog_map.get(tablo_adi)
    
    if dialog_class:
        baslik_prefix = tablo_adi.replace('_', ' ').capitalize()
        title = f"Yeni {baslik_prefix.replace('Stok ', '')} Ekle" if not item_id else f"{baslik_prefix.replace('Stok ', '')} Düzenle"
        
        if tablo_adi in ('hizmet_kartlari', 'hizmet_kartlari_gruplari'):
            dialog = dialog_class(parent, title, item_id=item_id, firma_id=firma_id, kart_turu=kart_turu)
        elif tablo_adi in ["stok_kategorileri", "stok_birimleri"]:
            grup_adi = "Stok Kategorisi" if tablo_adi == "stok_kategorileri" else "Stok Birimi"
            dialog = dialog_class(parent, title, item_id=item_id, firma_id=firma_id, grup_adi=grup_adi)
        else:
            dialog = dialog_class(parent, title, item_id=item_id, firma_id=firma_id)
        return dialog.result
    return None

class BaseDialog(tk.Toplevel):
    def __init__(self, parent, title, item_id=None, firma_id=1):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.firma_id = firma_id
        self.result = None
        self.item_id = item_id

        self.create_widgets()
        if self.item_id:
            self.load_data_for_edit()

        self.wait_window(self)

    def create_widgets(self):
        raise NotImplementedError

    def load_data_for_edit(self):
        raise NotImplementedError

    def on_save(self):
        raise NotImplementedError

class BankaKurumDialog(BaseDialog):
    def create_widgets(self):
        form_frame = tk.Frame(self, padx=15, pady=15)
        form_frame.pack(fill="both", expand=True)

        tk.Label(form_frame, text="Kurum Adı:").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_kurum_adi = tk.Entry(form_frame, width=40)
        self.ent_kurum_adi.grid(row=0, column=1, padx=5, pady=5)
        self.ent_kurum_adi.focus_set()

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack(fill="x", padx=15)

        btn_save = tk.Button(btn_frame, text="Kaydet", command=self.on_save, bg="#198754", fg="white", width=12)
        btn_save.pack(side="right")

        btn_cancel = tk.Button(btn_frame, text="İptal", command=self.destroy, width=12)
        btn_cancel.pack(side="right", padx=10)

    def load_data_for_edit(self):
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT kurum_adi FROM banka_kurumlari WHERE id = ?", (self.item_id,))
        data = cursor.fetchone()
        conn.close()
        if data:
            self.ent_kurum_adi.insert(0, data[0])

    def on_save(self):
        kurum_adi = self.ent_kurum_adi.get().strip()
        if not kurum_adi:
            messagebox.showerror("Hata", "Kurum Adı boş bırakılamaz.", parent=self)
            return

        kurum_data = {
            'id': self.item_id,
            'kurum_adi': kurum_adi,
            'firma_id': self.firma_id
        }
        
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            new_id = kaydet_kart(cursor, "banka_kurumlari", kurum_data)
            conn.commit()
            
            self.result = (new_id, kurum_adi)
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", f"'{kurum_adi}' adında bir banka kurumu zaten mevcut.", parent=self)
            if conn: conn.rollback()
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {e}", parent=self)
            if conn: conn.rollback()
        finally:
            if conn: conn.close()

class HizmetKartGrupDialog(BaseDialog):
    def __init__(self, parent, title, item_id=None, kart_turu=None, firma_id=1):
        self.kart_turu = kart_turu
        super().__init__(parent, title, item_id, firma_id)

    def create_widgets(self):
        form_frame = tk.Frame(self, padx=15, pady=15)
        form_frame.pack(fill="both", expand=True)

        tk.Label(form_frame, text="Grup Adı:").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_grup_adi = tk.Entry(form_frame, width=40)
        self.ent_grup_adi.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Tür:").grid(row=1, column=0, sticky="w", pady=5)
        self.cmb_tur = ttk.Combobox(form_frame, values=["Gider", "Gelir"], state="readonly")
        self.cmb_tur.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        if self.kart_turu:
            # Kartın türü biliniyorsa (lookup'tan açıldıysa) türü kilitle
            self.cmb_tur.set(self.kart_turu)
            self.cmb_tur.config(state="disabled")
        else:
            self.cmb_tur.set("Gider")

        self.ent_grup_adi.focus_set()

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack(fill="x", padx=15)

        btn_save = tk.Button(btn_frame, text="Kaydet", command=self.on_save, bg="#198754", fg="white", width=12)
        btn_save.pack(side="right")

        btn_cancel = tk.Button(btn_frame, text="İptal", command=self.destroy, width=12)
        btn_cancel.pack(side="right", padx=10)

    def load_data_for_edit(self):
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT grup_adi, tur FROM hizmet_kartlari_gruplari WHERE id = ?", (self.item_id,))
        data = cursor.fetchone()
        conn.close()
        if data:
            self.ent_grup_adi.insert(0, data[0])
            self.cmb_tur.set(data[1])

    def on_save(self):
        grup_adi = self.ent_grup_adi.get().strip()
        if not grup_adi:
            messagebox.showerror("Hata", "Grup Adı boş bırakılamaz.", parent=self)
            return

        grup_data = {
            'id': self.item_id,
            'grup_adi': grup_adi,
            'tur': self.cmb_tur.get(),
            'firma_id': self.firma_id,
            'durum': 1,
        }

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            new_id = kaydet_kart(cursor, "hizmet_kartlari_gruplari", grup_data)
            conn.commit()

            self.result = (new_id, grup_adi)
            self.destroy()

        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", f"'{grup_adi}' adında bir grup zaten mevcut.", parent=self)
            if conn: conn.rollback()
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {e}", parent=self)
            if conn: conn.rollback()
        finally:
            if conn: conn.close()


class CariDialog(BaseDialog):
    def create_widgets(self):
        form_frame = tk.Frame(self, padx=15, pady=15)
        form_frame.pack(fill="both", expand=True)

        tk.Label(form_frame, text="Unvan:").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_unvan = tk.Entry(form_frame, width=40)
        self.ent_unvan.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Tür:").grid(row=1, column=0, sticky="w", pady=5)
        self.cmb_tur = ttk.Combobox(
            form_frame, values=["Müşteri", "Tedarikçi", "Diğer"], state="readonly"
        )
        self.cmb_tur.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.cmb_tur.set("Müşteri")

        tk.Label(form_frame, text="Telefon:").grid(row=2, column=0, sticky="w", pady=5)
        self.ent_telefon = tk.Entry(form_frame, width=40)
        self.ent_telefon.grid(row=2, column=1, padx=5, pady=5)

        self.ent_unvan.focus_set()

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack(fill="x", padx=15)

        btn_save = tk.Button(
            btn_frame, text="Kaydet", command=self.on_save, bg="#198754", fg="white", width=12
        )
        btn_save.pack(side="right")

        btn_cancel = tk.Button(
            btn_frame, text="İptal", command=self.destroy, width=12
        )
        btn_cancel.pack(side="right", padx=10)

    def load_data_for_edit(self):
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("SELECT unvan, tur, telefon FROM cariler WHERE id = ?", (self.item_id,))
            data = cursor.fetchone()
            if data:
                self.ent_unvan.insert(0, data[0])
                self.cmb_tur.set(data[1])
                self.ent_telefon.insert(0, data[2] or "")
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Kayıt bilgileri yüklenemedi: {e}", parent=self)
            self.destroy()
        finally:
            if conn:
                conn.close()

    def on_save(self):
        unvan = self.ent_unvan.get().strip()
        if not unvan:
            messagebox.showerror("Hata", "Unvan alanı boş bırakılamaz.", parent=self)
            return
            
        cari_data = {
            'id': self.item_id,
            'unvan': unvan,
            'tur': self.cmb_tur.get(),
            'telefon': self.ent_telefon.get().strip(),
            'firma_id': self.firma_id
        }

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            new_id = kaydet_kart(cursor, "cariler", cari_data)
            conn.commit()

            self.result = (new_id, unvan)
            self.destroy()

        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", f"'{unvan}' adında bir cari zaten mevcut.", parent=self)
            if conn: conn.rollback()
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {e}", parent=self)
            if conn: conn.rollback()
        finally:
            if conn: conn.close()

class HizmetDialog(BaseDialog):
    def __init__(self, parent, title, item_id=None, kart_turu=None, firma_id=1):
        self.kart_turu = kart_turu
        super().__init__(parent, title, item_id, firma_id)

    def create_widgets(self):
        form_frame = tk.Frame(self, padx=15, pady=15)
        form_frame.pack(fill="both", expand=True)

        tk.Label(form_frame, text="Kart Adı:").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_kart_adi = tk.Entry(form_frame, width=40)
        self.ent_kart_adi.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Tür:").grid(row=1, column=0, sticky="w", pady=5)
        self.cmb_tur = ttk.Combobox(
            form_frame, values=["Gelir", "Gider"], state="readonly"
        )
        self.cmb_tur.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        tk.Label(form_frame, text="Varsayılan KDV Oranı (%):").grid(row=2, column=0, sticky="w", pady=5)
        self.ent_kdv_oran = tk.Entry(form_frame, width=40)
        self.ent_kdv_oran.grid(row=2, column=1, padx=5, pady=5)

        if self.kart_turu:
            self.cmb_tur.set(self.kart_turu)
            self.cmb_tur.config(state="disabled")
        else:
            self.cmb_tur.set("Gider")

        self.ent_kart_adi.focus_set()

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack(fill="x", padx=15)

        btn_save = tk.Button(
            btn_frame, text="Kaydet", command=self.on_save, bg="#198754", fg="white", width=12
        )
        btn_save.pack(side="right")

        btn_cancel = tk.Button(
            btn_frame, text="İptal", command=self.destroy, width=12
        )
        btn_cancel.pack(side="right", padx=10)

    def load_data_for_edit(self):
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("SELECT kart_adi, tur, kdv_oran FROM hizmet_kartlari WHERE id = ?", (self.item_id,))
            data = cursor.fetchone()
            if data:
                self.ent_kart_adi.insert(0, data[0])
                self.cmb_tur.set(data[1])
                self.ent_kdv_oran.insert(0, str(data[2] or 20))
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Kayıt bilgileri yüklenemedi: {e}", parent=self)
            self.destroy()
        finally:
            if conn: conn.close()

    def on_save(self):
        kart_adi = self.ent_kart_adi.get().strip()
        if not kart_adi:
            messagebox.showerror("Hata", "Kart Adı alanı boş bırakılamaz.", parent=self)
            return

        hizmet_data = {
            'id': self.item_id,
            'kart_adi': kart_adi,
            'tur': self.cmb_tur.get(),
            'kdv_oran': parse_currency(self.ent_kdv_oran.get()),
            'firma_id': self.firma_id
        }

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            new_id = kaydet_kart(cursor, "hizmet_kartlari", hizmet_data)
            conn.commit()

            self.result = (new_id, kart_adi)
            self.destroy()

        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", f"'{kart_adi}' adında bir kart zaten mevcut.", parent=self)
            if conn: conn.rollback()
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {e}", parent=self)
            if conn: conn.rollback()
        finally:
            if conn: conn.close()

class GenelTanimDialog(BaseDialog):
    def __init__(self, parent, title, item_id=None, firma_id=1, grup_adi=None):
        self.grup_adi = grup_adi
        self.label_text = grup_adi.replace("Stok ", "") + " Adı:"
        super().__init__(parent, title, item_id, firma_id)

    def create_widgets(self):
        form_frame = tk.Frame(self, padx=15, pady=15)
        form_frame.pack(fill="both", expand=True)

        tk.Label(form_frame, text=self.label_text).grid(row=0, column=0, sticky="w", pady=5)
        self.ent_deger = tk.Entry(form_frame, width=40)
        self.ent_deger.grid(row=0, column=1, padx=5, pady=5)
        self.ent_deger.focus_set()

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack(fill="x", padx=15)

        btn_save = tk.Button(btn_frame, text="Kaydet", command=self.on_save, bg="#198754", fg="white", width=12)
        btn_save.pack(side="right")

        btn_cancel = tk.Button(btn_frame, text="İptal", command=self.destroy, width=12)
        btn_cancel.pack(side="right", padx=10)

    def load_data_for_edit(self):
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT deger FROM genel_tanimlar WHERE id = ? AND grup = ?", (self.item_id, self.grup_adi))
        data = cursor.fetchone()
        conn.close()
        if data:
            self.ent_deger.insert(0, data[0])

    def on_save(self):
        deger = self.ent_deger.get().strip()
        if not deger:
            messagebox.showerror("Hata", f"{self.label_text.replace(':', '')} boş bırakılamaz.", parent=self)
            return

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            
            query = "SELECT id FROM genel_tanimlar WHERE grup = ? AND deger = ? AND firma_id = ?"
            params = [self.grup_adi, deger, self.firma_id]
            if self.item_id:
                query += " AND id != ?"
                params.append(self.item_id)
            cursor.execute(query, params)
            if cursor.fetchone():
                raise sqlite3.IntegrityError

            if self.item_id:
                cursor.execute("UPDATE genel_tanimlar SET deger = ? WHERE id = ?", (deger, self.item_id))
                new_id = self.item_id
            else:
                cursor.execute(
                    "INSERT INTO genel_tanimlar (grup, deger, firma_id) VALUES (?, ?, ?)",
                    (self.grup_adi, deger, self.firma_id)
                )
                new_id = cursor.lastrowid
            
            conn.commit()
            self.result = (new_id, deger)
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", f"'{deger}' adında bir kayıt zaten mevcut.", parent=self)
            if conn: conn.rollback()
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {e}", parent=self)
            if conn: conn.rollback()
        finally:
            if conn: conn.close()

class KasaDialog(BaseDialog):
    def create_widgets(self):
        form_frame = tk.Frame(self, padx=15, pady=15)
        form_frame.pack(fill="both", expand=True)

        tk.Label(form_frame, text="Kasa Adı:").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_kasa_adi = tk.Entry(form_frame, width=40)
        self.ent_kasa_adi.grid(row=0, column=1, padx=5, pady=5)
        self.ent_kasa_adi.focus_set()

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack(fill="x", padx=15)

        btn_save = tk.Button(btn_frame, text="Kaydet", command=self.on_save, bg="#198754", fg="white", width=12)
        btn_save.pack(side="right")

        btn_cancel = tk.Button(btn_frame, text="İptal", command=self.destroy, width=12)
        btn_cancel.pack(side="right", padx=10)

    def load_data_for_edit(self):
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT kasa_adi FROM kasalar WHERE id = ?", (self.item_id,))
        data = cursor.fetchone()
        conn.close()
        if data:
            self.ent_kasa_adi.insert(0, data[0])

    def on_save(self):
        kasa_adi = self.ent_kasa_adi.get().strip()
        if not kasa_adi:
            messagebox.showerror("Hata", "Kasa Adı boş bırakılamaz.", parent=self)
            return

        kasa_data = {
            'id': self.item_id,
            'kasa_adi': kasa_adi,
            'firma_id': self.firma_id
        }
        
        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            new_id = kaydet_kart(cursor, "kasalar", kasa_data)
            conn.commit()
            
            self.result = (new_id, kasa_adi)
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", f"'{kasa_adi}' adında bir kasa zaten mevcut.", parent=self)
            if conn: conn.rollback()
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {e}", parent=self)
            if conn: conn.rollback()
        finally:
            if conn: conn.close()

class StokDialog(BaseDialog):
    def create_widgets(self):
        form_frame = tk.Frame(self, padx=15, pady=15)
        form_frame.pack(fill="both", expand=True)

        tk.Label(form_frame, text="Stok Adı:").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_stok_adi = tk.Entry(form_frame, width=40)
        self.ent_stok_adi.grid(row=0, column=1, padx=5, pady=5)
        self.ent_stok_adi.focus_set()
        
        tk.Label(form_frame, text="Stok Kodu:").grid(row=1, column=0, sticky="w", pady=5)
        self.ent_stok_kodu = tk.Entry(form_frame, width=40)
        self.ent_stok_kodu.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(form_frame, text="(Boş bırakılırsa otomatik oluşur)", font=("Arial", 7)).grid(row=2, column=1, sticky="w")

        tk.Label(form_frame, text="Kategori:").grid(row=3, column=0, sticky="w", pady=5)
        self.cmb_kategori = ttk.Combobox(form_frame, width=38)
        self.cmb_kategori.grid(row=3, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Birim:").grid(row=4, column=0, sticky="w", pady=5)
        self.cmb_birim = ttk.Combobox(form_frame, width=38)
        self.cmb_birim.grid(row=4, column=1, padx=5, pady=5)

        conn = veritabani_baglan()
        try:
            cursor = conn.cursor()
            self._load_tanimlar(cursor, "Stok Kategorisi", self.cmb_kategori)
            self._load_tanimlar(cursor, "Stok Birimi", self.cmb_birim)
            if "Adet" in self.cmb_birim['values']:
                self.cmb_birim.set("Adet")
            elif self.cmb_birim['values']:
                self.cmb_birim.set(self.cmb_birim['values'][0])
            if self.cmb_kategori['values']:
                self.cmb_kategori.set(self.cmb_kategori['values'][0])
        finally:
            conn.close()

        tk.Label(form_frame, text="Alış Fiyatı:").grid(row=5, column=0, sticky="w", pady=5)
        self.ent_alis_fiyati = tk.Entry(form_frame, width=40)
        self.ent_alis_fiyati.grid(row=5, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Satış Fiyatı:").grid(row=6, column=0, sticky="w", pady=5)
        self.ent_satis_fiyati = tk.Entry(form_frame, width=40)
        self.ent_satis_fiyati.grid(row=6, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Varsayılan KDV Oranı (%):").grid(row=7, column=0, sticky="w", pady=5)
        self.ent_kdv_oran = tk.Entry(form_frame, width=40)
        self.ent_kdv_oran.grid(row=7, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack(fill="x", padx=15)

        btn_save = tk.Button(btn_frame, text="Kaydet", command=self.on_save, bg="#198754", fg="white", width=12)
        btn_save.pack(side="right")

        btn_cancel = tk.Button(btn_frame, text="İptal", command=self.destroy, width=12)
        btn_cancel.pack(side="right", padx=10)

    def load_data_for_edit(self):
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT stok_adi, stok_kodu, alis_fiyati, satis_fiyati, kategori, birim, kdv_oran FROM stoklar WHERE id = ?", (self.item_id,))
        data = cursor.fetchone()
        
        if data:
            self.ent_stok_adi.insert(0, data[0])
            self.ent_stok_kodu.insert(0, data[1] or "")
            self.ent_alis_fiyati.insert(0, data[2] or "0")
            self.ent_satis_fiyati.insert(0, data[3] or "0")
            self.ent_kdv_oran.insert(0, str(data[6] or 20))
            kategori_deger = data[4] or ""
            birim_deger = data[5] or "Adet"

        self._load_tanimlar(cursor, "Stok Kategorisi", self.cmb_kategori)
        self._load_tanimlar(cursor, "Stok Birimi", self.cmb_birim)
        conn.close()
        if data:
            self.cmb_kategori.set(kategori_deger)
            self.cmb_birim.set(birim_deger)

    def on_save(self):
        stok_adi = self.ent_stok_adi.get().strip()
        if not stok_adi:
            messagebox.showerror("Hata", "Stok Adı boş bırakılamaz.", parent=self)
            return

        kategori = self.cmb_kategori.get().strip()
        birim = self.cmb_birim.get().strip()
        if not kategori:
            kategori = "Genel"
        if not birim:
            birim = "Adet"

        alis_fiyati = parse_currency(self.ent_alis_fiyati.get())
        satis_fiyati = parse_currency(self.ent_satis_fiyati.get())
        kdv_oran = parse_currency(self.ent_kdv_oran.get())

        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM genel_tanimlar WHERE grup = ? AND deger = ? AND firma_id = ?",
                ("Stok Kategorisi", kategori, self.firma_id),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    "INSERT INTO genel_tanimlar (grup, deger, firma_id) VALUES (?, ?, ?)",
                    ("Stok Kategorisi", kategori, self.firma_id),
                )

            cursor.execute(
                "SELECT id FROM genel_tanimlar WHERE grup = ? AND deger = ? AND firma_id = ?",
                ("Stok Birimi", birim, self.firma_id),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    "INSERT INTO genel_tanimlar (grup, deger, firma_id) VALUES (?, ?, ?)",
                    ("Stok Birimi", birim, self.firma_id),
                )
            conn.commit()
            conn.close()
        except Exception:
            if conn:
                conn.rollback()
                conn.close()

        stok_data = {
            'id': self.item_id,
            'stok_adi': stok_adi,
            'stok_kodu': self.ent_stok_kodu.get().strip(),
            'alis_fiyati': alis_fiyati,
            'satis_fiyati': satis_fiyati,
            'kdv_oran': kdv_oran,
            'kategori': kategori,
            'birim': birim,
            'firma_id': self.firma_id
        }

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            
            new_id = kaydet_kart(cursor, "stoklar", stok_data)
            conn.commit()

            self.result = (new_id, stok_adi)
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", f"Bu stok adı veya kodu zaten mevcut.", parent=self)
            if conn: conn.rollback()
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Kayıt sırasında bir hata oluştu: {e}", parent=self)
            if conn: conn.rollback()
        finally:
            if conn: conn.close()

    def _load_tanimlar(self, cursor, grup_adi, combobox):
        cursor.execute("SELECT deger FROM genel_tanimlar WHERE grup = ? AND firma_id = ?", (grup_adi, self.firma_id))
        degerler = [row[0] for row in cursor.fetchall()]
        combobox['values'] = degerler

class YilSecimDialog(tk.Toplevel):
    def __init__(self, parent, yillar, aktif_yil):
        super().__init__(parent)
        self.title("Çalışma Yılını Değiştir")
        self.transient(parent)
        self.grab_set()
        self.result = None

        self.create_widgets(yillar, aktif_yil)
        self.wait_window(self)

    def create_widgets(self, yillar, aktif_yil):
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text="Yeni Çalışma Yılını Seçin:", font=("Arial", 10)).pack(anchor="w")
        
        self.cmb_yil = ttk.Combobox(main_frame, values=yillar, state="readonly", font=("Arial", 10))
        self.cmb_yil.pack(fill="x", pady=(5, 15))
        self.cmb_yil.set(aktif_yil)

        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill="x")

        btn_save = tk.Button(
            btn_frame, text="Yılı Değiştir", command=self.on_select, bg="#0d6efd", fg="white", width=15
        )
        btn_save.pack(side="right")

        btn_cancel = tk.Button(
            btn_frame, text="İptal", command=self.destroy, width=15
        )
        btn_cancel.pack(side="right", padx=10)

    def on_select(self):
        self.result = int(self.cmb_yil.get())
        self.destroy()
