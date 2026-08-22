import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from core.db import veritabani_baglan


class FirmaTanimlariView(tk.Frame):
    """Firma tanımlarının listelendiği, eklendiği ve düzenlendiği görünüm."""

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.selected_id = None
        self.create_widgets()
        self.listele()

    def create_widgets(self):
        form_frame = tk.LabelFrame(self, text="Firma Bilgileri", bg="#f5f7fb", padx=10, pady=10)
        form_frame.pack(side="left", fill="y", padx=10, pady=10)

        form_alanlari = tk.Frame(form_frame, bg="#f5f7fb")
        form_alanlari.pack(fill="x")
        form_alanlari.columnconfigure(1, weight=1)

        tk.Label(form_alanlari, text="Firma Adı:", bg="#f5f7fb").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_firma_adi = tk.Entry(form_alanlari, width=40)
        self.ent_firma_adi.grid(row=0, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Durum:", bg="#f5f7fb").grid(row=1, column=0, sticky="w", pady=2)
        self.cmb_durum = ttk.Combobox(form_alanlari, state="readonly", values=["Aktif", "Pasif"], width=38)
        self.cmb_durum.set("Aktif")
        self.cmb_durum.grid(row=1, column=1, pady=2, sticky="ew")

        buton_frame = tk.Frame(form_frame, bg="#f5f7fb", pady=10)
        buton_frame.pack(fill="x")
        self.btn_kaydet = tk.Button(buton_frame, text="Kaydet", command=self.kaydet, bg="#198754", fg="white")
        self.btn_kaydet.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.btn_temizle = tk.Button(buton_frame, text="Formu Temizle", command=self.formu_temizle)
        self.btn_temizle.pack(side="left", expand=True, fill="x", padx=(5, 0))

        liste_frame = tk.Frame(self, bg="#f5f7fb")
        liste_frame.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)

        filter_frame = tk.Frame(liste_frame, bg="#f5f7fb")
        filter_frame.pack(fill="x", pady=(0, 5))
        tk.Label(filter_frame, text="Ara:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.ent_arama = tk.Entry(filter_frame)
        self.ent_arama.pack(side="left", fill="x", expand=True)
        self.ent_arama.bind("<KeyRelease>", lambda e: self.listele())

        tree_container = tk.Frame(liste_frame)
        tree_container.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_container, columns=("id", "firma_adi", "durum"), show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("firma_adi", text="Firma Adı")
        self.tree.heading("durum", text="Durum")
        self.tree.column("id", width=60, stretch=False, anchor="center")
        self.tree.column("firma_adi", width=250)
        self.tree.column("durum", width=100, stretch=False, anchor="center")
        self.tree.tag_configure('passive', foreground='gray')

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.kayit_secildi)

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            params = []
            where = ""
            arama = self.ent_arama.get().strip()
            if arama:
                where = "WHERE firma_adi LIKE ?"
                params.append(f"%{arama}%")
            cursor.execute(f"SELECT id, firma_adi, durum FROM firmalar {where} ORDER BY firma_adi", params)
            for row in cursor.fetchall():
                durum = "Aktif" if row[2] == 1 else "Pasif"
                tags = ('passive',) if row[2] == 0 else ()
                self.tree.insert("", "end", values=(row[0], row[1], durum), tags=tags)
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Firmalar listelenemedi: {e}", parent=self)
        finally:
            if conn:
                conn.close()

    def kayit_secildi(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        self.selected_id = int(values[0])
        self.ent_firma_adi.delete(0, tk.END)
        self.ent_firma_adi.insert(0, values[1])
        self.cmb_durum.set(values[2])

    def formu_temizle(self):
        self.selected_id = None
        self.ent_firma_adi.delete(0, tk.END)
        self.cmb_durum.set("Aktif")
        self.ent_firma_adi.focus_set()
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def kaydet(self):
        firma_adi = self.ent_firma_adi.get().strip()
        if not firma_adi:
            messagebox.showerror("Hata", "Firma adı boş bırakılamaz.", parent=self)
            return
        durum = 1 if self.cmb_durum.get() == "Aktif" else 0

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            if self.selected_id:
                cursor.execute("UPDATE firmalar SET firma_adi = ?, durum = ? WHERE id = ?", (firma_adi, durum, self.selected_id))
            else:
                cursor.execute("INSERT INTO firmalar (firma_adi, durum) VALUES (?, ?)", (firma_adi, durum))
            conn.commit()
            messagebox.showinfo("Başarılı", "Firma kaydedildi.", parent=self)
            self.formu_temizle()
            self.listele()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Bu firma adı zaten mevcut.", parent=self)
            if conn:
                conn.rollback()
        except Exception as e:
            messagebox.showerror("Hata", f"Firma kaydedilemedi: {e}", parent=self)
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def yenile(self):
        self.listele()
