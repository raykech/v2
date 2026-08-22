import tkinter as tk
from tkinter import ttk, messagebox
from core.db import veritabani_baglan


class YilTanimlariView(tk.Frame):
    """Yıl tanımlarının yönetildiği görünüm.

    Yıllar 'genel_tanimlar' tablosunda 'Yillar' grubu altında tutulur.
    Firma/Yıl seçim ekranı bu yılları da listeye ekler.
    """

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.create_widgets()
        self.listele()

    def create_widgets(self):
        form_frame = tk.LabelFrame(self, text="Yıl Ekle", bg="#f5f7fb", padx=10, pady=10)
        form_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(form_frame, text="Yıl:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.ent_yil = tk.Entry(form_frame, width=10)
        self.ent_yil.pack(side="left", padx=(0, 10))
        self.ent_yil.bind("<Return>", lambda e: self.yil_ekle())

        btn_ekle = tk.Button(form_frame, text="Yıl Ekle", command=self.yil_ekle, bg="#198754", fg="white")
        btn_ekle.pack(side="left", padx=(0, 10))

        btn_kaldir = tk.Button(form_frame, text="Seçili Yılı Kaldır", command=self.yil_kaldir, bg="#dc3545", fg="white")
        btn_kaldir.pack(side="left")

        tk.Label(
            form_frame,
            text="  Not: Yıl seçimi, alt taraftaki Firma/Yıl değiştir ekranında elle de yazılabilir.",
            bg="#f5f7fb",
            fg="#6c757d",
        ).pack(side="left", padx=(10, 0))

        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(tree_container, columns=("yil", "kaynak"), show="headings")
        self.tree.heading("yil", text="Yıl")
        self.tree.heading("kaynak", text="Kaynak")
        self.tree.column("yil", width=120, stretch=False, anchor="center")
        self.tree.column("kaynak", width=250)

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        conn = veritabani_baglan()
        cursor = conn.cursor()

        # Tanımlı yıllar
        cursor.execute("SELECT deger FROM genel_tanimlar WHERE grup = 'Yillar' ORDER BY deger DESC")
        tanimli = [int(row[0]) for row in cursor.fetchall() if str(row[0]).strip().isdigit()]

        # Verilerde geçen yıllar
        cursor.execute("SELECT DISTINCT yil FROM fisler ORDER BY yil DESC")
        veri_yillari = [row[0] for row in cursor.fetchall() if row[0]]

        conn.close()

        seen = set()
        for yil in tanimli:
            self.tree.insert("", "end", values=(yil, "Tanımlı"))
            seen.add(yil)
        for yil in veri_yillari:
            if yil not in seen:
                self.tree.insert("", "end", values=(yil, "Verilerde Mevcut"))
                seen.add(yil)

    def yil_ekle(self):
        yil_text = self.ent_yil.get().strip()
        if not yil_text:
            messagebox.showwarning("Uyarı", "Lütfen bir yıl girin.", parent=self)
            return
        try:
            yil = int(yil_text)
        except ValueError:
            messagebox.showerror("Hata", "Yıl sayısal olmalıdır.", parent=self)
            return

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM genel_tanimlar WHERE grup = 'Yillar' AND deger = ?",
                (str(yil),),
            )
            if cursor.fetchone()[0] > 0:
                messagebox.showinfo("Bilgi", "Bu yıl zaten tanımlı.", parent=self)
                return
            cursor.execute("INSERT INTO genel_tanimlar (grup, deger) VALUES ('Yillar', ?)", (str(yil),))
            conn.commit()
            self.ent_yil.delete(0, tk.END)
            self.listele()
        except Exception as e:
            messagebox.showerror("Hata", f"Yıl eklenemedi: {e}", parent=self)
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def yil_kaldir(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen listeden bir yıl seçin.", parent=self)
            return
        values = self.tree.item(selected[0], "values")
        yil = values[0]
        kaynak = values[1]
        if kaynak == "Verilerde Mevcut":
            messagebox.showwarning("Uyarı", "Bu yıl verilerde kullanıldığı için tanımlı listeden kaldırılamaz. Yalnızca 'Tanımlı' yıllar kaldırılabilir.", parent=self)
            return
        if not messagebox.askyesno("Onay", f"{yil} yılını tanımlı listeden kaldırmak istediğinize emin misiniz?", parent=self):
            return

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM genel_tanimlar WHERE grup = 'Yillar' AND deger = ?", (str(yil),))
            conn.commit()
            self.listele()
        except Exception as e:
            messagebox.showerror("Hata", f"Yıl kaldırılamadı: {e}", parent=self)
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def yenile(self):
        self.listele()
