import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from core.db import veritabani_baglan
from core.services import kart_sil as kart_sil_service, kaydet_kart
from utils.formatters import parse_currency, format_currency
from ui.widgets.lookup_widget import LookupWidget
from ui.dialogs import ac_kart_dialog
from ui.widgets.pagination import SayfaliListeMixin

class BankaHesapTanimView(SayfaliListeMixin, tk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.parent = parent
        self.selected_id = None
        self.kurum_dict = {}
        self.create_widgets()
        self._load_and_configure_data()
        self.listele()

    def create_widgets(self):
        # Ana çerçeveler
        form_frame = tk.LabelFrame(self, text="Banka Hesap Bilgileri", bg="#f5f7fb", padx=10, pady=10)
        form_frame.pack(side="left", fill="y", padx=10, pady=10)

        liste_frame = tk.Frame(self, bg="#f5f7fb")
        liste_frame.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)

        # Form Alanları
        form_alanlari = tk.Frame(form_frame, bg="#f5f7fb")
        form_alanlari.pack(fill="x")
        form_alanlari.columnconfigure(1, weight=1)

        tk.Label(form_alanlari, text="Hesap Adı:", bg="#f5f7fb").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_hesap_adi = tk.Entry(form_alanlari, width=40)
        self.ent_hesap_adi.grid(row=0, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Banka Kurumu:", bg="#f5f7fb").grid(row=1, column=0, sticky="w", pady=2)
        self.lookup_kurum = LookupWidget(form_alanlari)
        self.lookup_kurum.grid(row=1, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Hesap Türü:", bg="#f5f7fb").grid(row=2, column=0, sticky="w", pady=2)
        self.cmb_hesap_turu = ttk.Combobox(form_alanlari, state="readonly", values=["Vadesiz", "POS", "Kredi Kartı"])
        self.cmb_hesap_turu.grid(row=2, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="IBAN:", bg="#f5f7fb").grid(row=3, column=0, sticky="w", pady=2)
        self.ent_iban = tk.Entry(form_alanlari, width=40)
        self.ent_iban.grid(row=3, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Komisyon %:", bg="#f5f7fb").grid(row=4, column=0, sticky="w", pady=2)
        self.ent_komisyon = tk.Entry(form_alanlari, width=40, justify="right")
        self.ent_komisyon.grid(row=4, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Durum:", bg="#f5f7fb").grid(row=5, column=0, sticky="w", pady=2)
        self.cmb_durum = ttk.Combobox(form_alanlari, state="readonly", values=["Aktif", "Pasif"])
        self.cmb_durum.set("Aktif")
        self.cmb_durum.grid(row=5, column=1, pady=2, sticky="ew")

        # Form Butonları
        buton_frame = tk.Frame(form_frame, bg="#f5f7fb", pady=10)
        buton_frame.pack(fill="x")
        self.btn_kaydet = tk.Button(buton_frame, text="Kaydet", command=self.kaydet_kart, bg="#198754", fg="white")
        self.btn_kaydet.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.btn_sil = tk.Button(buton_frame, text="Sil", command=self.sil_kart, bg="#dc3545", fg="white")
        self.btn_sil.pack(side="left", expand=True, fill="x")
        self.btn_temizle = tk.Button(buton_frame, text="Formu Temizle", command=self.formu_temizle)
        self.btn_temizle.pack(side="left", expand=True, fill="x", padx=(5, 0))

        # Filtre Alanı
        filter_frame = tk.LabelFrame(liste_frame, text="Filtrele", bg="#f5f7fb", padx=10, pady=5)
        filter_frame.pack(fill="x", pady=(0, 5))
        tk.Label(filter_frame, text="Kurum:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_kurum_filtre = ttk.Combobox(filter_frame, state="readonly", width=20)
        self.cmb_kurum_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_kurum_filtre.pack(side="left", padx=(0, 10))
        tk.Label(filter_frame, text="Durum:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_durum_filtre = ttk.Combobox(filter_frame, state="readonly", width=10, values=["Tümü", "Aktif", "Pasif"])
        self.cmb_durum_filtre.set("Aktif")
        self.cmb_durum_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_durum_filtre.pack(side="left", padx=(0, 10))
        tk.Label(filter_frame, text="Ara:", bg="#f5f7fb").pack(side="left", padx=(10, 2))
        self.ent_arama = tk.Entry(filter_frame)
        self.ent_arama.pack(side="left", fill="x", expand=True)
        self.ent_arama.bind("<KeyRelease>", lambda e: self.listele())
        btn_filtre_temizle = tk.Button(filter_frame, text="Filtreleri Temizle", command=self.filtreleri_temizle)
        btn_filtre_temizle.pack(side="left", padx=(10, 0))

        # Liste Alanı
        tree_container = tk.Frame(liste_frame)
        tree_container.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_container, columns=("id", "hesap_adi", "kurum_adi", "hesap_turu", "iban", "durum"), show="headings")
        self.tree.heading("id", text="ID"); self.tree.heading("hesap_adi", text="Hesap Adı"); self.tree.heading("kurum_adi", text="Banka Kurumu"); self.tree.heading("hesap_turu", text="Hesap Türü"); self.tree.heading("iban", text="IBAN"); self.tree.heading("durum", text="Durum")
        self.tree.column("id", width=50, stretch=False, anchor="center"); self.tree.column("hesap_adi", width=200); self.tree.column("kurum_adi", width=150); self.tree.column("hesap_turu", width=100); self.tree.column("iban", width=200); self.tree.column("durum", width=80, stretch=False, anchor="center")
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview); hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); vsb.pack(side="right", fill="y"); hsb.pack(side="bottom", fill="x"); self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.kayit_secildi); self.tree.tag_configure('passive', foreground='gray')
        self._init_sayfalama(self.tree)

    def _load_and_configure_data(self):
        conn = veritabani_baglan(); cursor = conn.cursor()
        cursor.execute("SELECT kurum_adi, id FROM banka_kurumlari WHERE durum=1 AND firma_id=?", (self.main_app.aktif_firma_id,))
        self.kurum_dict = {row[0]: row[1] for row in cursor.fetchall()}; conn.close()
        self.cmb_kurum_filtre['values'] = ["Tümü"] + list(self.kurum_dict.keys()); self.cmb_kurum_filtre.set("Tümü")
        self.lookup_kurum.configure_lookup(title="Banka Kurumu Seç", data_dict=self.kurum_dict, on_new=self.yeni_kurum_ekle)

    def yeni_kurum_ekle(self):
        yeni_kart = ac_kart_dialog(self, "banka_kurumlari", firma_id=self.main_app.aktif_firma_id)
        if yeni_kart: self._load_and_configure_data()
        return yeni_kart

    def filtreleri_temizle(self):
        self.cmb_kurum_filtre.set("Tümü"); self.cmb_durum_filtre.set("Aktif"); self.ent_arama.delete(0, tk.END); self.listele()

    def formu_temizle(self):
        self.selected_id = None; self.ent_hesap_adi.delete(0, tk.END); self.lookup_kurum.clear(); self.cmb_hesap_turu.set("Vadesiz"); self.ent_iban.delete(0, tk.END); self.ent_komisyon.delete(0, tk.END); self.cmb_durum.set("Aktif"); self.ent_hesap_adi.focus_set()
        if self.tree.selection(): self.tree.selection_remove(self.tree.selection())

    def listele(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        self._sayfa_yuklenen = 0
        self._sayfa_tukendi = False
        where_clauses = ["h.firma_id=?"]; params = [self.main_app.aktif_firma_id]
        if self.cmb_kurum_filtre.get() != "Tümü": where_clauses.append("k.kurum_adi = ?"); params.append(self.cmb_kurum_filtre.get())
        if self.cmb_durum_filtre.get() != "Tümü": where_clauses.append("h.durum = ?"); params.append(1 if self.cmb_durum_filtre.get() == "Aktif" else 0)
        if self.ent_arama.get().strip(): where_clauses.append("(h.hesap_adi LIKE ? OR h.iban LIKE ?)"); params.extend([f"%{self.ent_arama.get().strip()}%", f"%{self.ent_arama.get().strip()}%"])
        self._sayfa_query = "SELECT h.id, h.hesap_adi, k.kurum_adi, h.hesap_turu, h.iban, h.durum FROM banka_hesaplari h LEFT JOIN banka_kurumlari k ON h.kurum_id = k.id WHERE " + " AND ".join(where_clauses) + " ORDER BY h.id DESC"
        self._sayfa_params = params
        self._diger_sayfa_yukle()

    def _satirlari_ekle(self, rows):
        for row in rows:
            durum_str = "Aktif" if row[5] == 1 else "Pasif"; tags = ('passive',) if row[5] == 0 else ()
            self.tree.insert("", "end", values=(row[0], row[1], row[2] or '', row[3], row[4] or '', durum_str), tags=tags)

    def kayit_secildi(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items: return
        item_id = self.tree.item(selected_items[0], "values")[0]
        conn = veritabani_baglan(); cursor = conn.cursor()
        cursor.execute("SELECT * FROM banka_hesaplari WHERE id=?", (item_id,)); data = cursor.fetchone(); conn.close()
        if data:
            cols = [desc[0] for desc in cursor.description]; hesap_data = dict(zip(cols, data))
            self.formu_temizle(); self.selected_id = item_id
            self.ent_hesap_adi.insert(0, hesap_data.get('hesap_adi', '')); self.cmb_hesap_turu.set(hesap_data.get('hesap_turu', 'Vadesiz'))
            self.ent_iban.insert(0, hesap_data.get('iban', '')); self.ent_komisyon.insert(0, format_currency(hesap_data.get('komisyon_orani', 0)))
            self.cmb_durum.set("Aktif" if hesap_data.get('durum', 1) == 1 else "Pasif")
            if hesap_data.get('kurum_id'): self.lookup_kurum.set(hesap_data['kurum_id'])

    def kaydet_kart(self):
        hesap_adi = self.ent_hesap_adi.get().strip()
        if not hesap_adi: messagebox.showerror("Hata", "Hesap Adı boş bırakılamaz.", parent=self); return
        hesap_data = {'id': self.selected_id, 'hesap_adi': hesap_adi, 'kurum_id': self.lookup_kurum.get(), 'hesap_turu': self.cmb_hesap_turu.get(), 'iban': self.ent_iban.get().strip(), 'komisyon_orani': parse_currency(self.ent_komisyon.get()), 'durum': 1 if self.cmb_durum.get() == "Aktif" else 0, 'firma_id': self.main_app.aktif_firma_id}
        conn = None
        try:
            conn = veritabani_baglan(); cursor = conn.cursor()
            kaydet_kart(cursor, "banka_hesaplari", hesap_data); conn.commit()
            messagebox.showinfo("Başarılı", "Banka hesabı başarıyla kaydedildi.", parent=self)
            self.formu_temizle(); self.listele()
        except sqlite3.IntegrityError: messagebox.showerror("Hata", "Bu hesap adı zaten mevcut.", parent=self); conn.rollback()
        except Exception as e: messagebox.showerror("Hata", f"Kayıt hatası: {e}", parent=self); conn.rollback()
        finally:
            if conn: conn.close()

    def sil_kart(self):
        if not self.selected_id: messagebox.showwarning("Uyarı", "Lütfen silmek için bir hesap seçin.", parent=self); return
        if not messagebox.askyesno("Onay", f"'{self.ent_hesap_adi.get()}' adlı hesabı silmek istediğinizden emin misiniz?", parent=self): return
        conn = None
        try:
            conn = veritabani_baglan(); cursor = conn.cursor()
            kart_sil_service(cursor, "banka_hesaplari", self.selected_id, self.main_app.aktif_firma_id); conn.commit()
            messagebox.showinfo("Başarılı", "Banka hesabı başarıyla silindi.", parent=self)
            self.formu_temizle(); self.listele()
        except ValueError as e: messagebox.showerror("Silme Hatası", str(e), parent=self); conn.rollback()
        except Exception as e: messagebox.showerror("Hata", f"Silme hatası: {e}", parent=self); conn.rollback()
        finally:
            if conn: conn.close()

    def yenile(self):
        self._load_and_configure_data(); self.listele()