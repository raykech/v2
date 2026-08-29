import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from utils.formatters import parse_currency
from utils.export import export_treeview_data
from core.db import veritabani_baglan
from core.services import kart_sil as kart_sil_service, kaydet_kart, is_kart_kullanilmis_mi
from ui.widgets.lookup_widget import LookupWidget
from ui.dialogs import ac_kart_dialog
from ui.widgets.pagination import SayfaliListeMixin

class HizmetTanimView(SayfaliListeMixin, tk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.parent = parent
        self.selected_id = None
        self._original_tur = None  # Düzenlenen kartın DB'deki türü (tür değişikliği tespiti için)
        self.grup_dict = {}
        self.create_widgets()
        self._yukle_gruplari()
        self._varsayilan_grup_sec()
        self.listele()

    def create_widgets(self):
        # Ana çerçeveler
        form_frame = tk.LabelFrame(self, text="Hizmet/Masraf Kartı Bilgileri", bg="#f5f7fb", padx=10, pady=10)
        form_frame.pack(side="left", fill="y", padx=10, pady=10)

        liste_frame = tk.Frame(self, bg="#f5f7fb")
        liste_frame.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)


        # Form Alanları
        form_alanlari = tk.Frame(form_frame, bg="#f5f7fb")
        form_alanlari.pack(fill="x")
        form_alanlari.columnconfigure(1, weight=1)

        tk.Label(form_alanlari, text="Kart Adı:", bg="#f5f7fb").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_kart_adi = tk.Entry(form_alanlari, width=40)
        self.ent_kart_adi.grid(row=0, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Tür:", bg="#f5f7fb").grid(row=1, column=0, sticky="w", pady=2)
        self.cmb_tur = ttk.Combobox(form_alanlari, state="readonly", values=["Gider", "Gelir"])
        self.cmb_tur.set("Gider")
        self.cmb_tur.grid(row=1, column=1, pady=2, sticky="ew")
        self.cmb_tur.bind("<<ComboboxSelected>>", lambda e: self._tur_degisti())

        tk.Label(form_alanlari, text="Grup:", bg="#f5f7fb").grid(row=2, column=0, sticky="w", pady=2)
        self.lookup_grup = LookupWidget(form_alanlari)
        self.lookup_grup.grid(row=2, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Varsayılan KDV Oranı (%):", bg="#f5f7fb").grid(row=3, column=0, sticky="w", pady=2)
        self.ent_kdv_oran = tk.Entry(form_alanlari, width=40)
        self.ent_kdv_oran.grid(row=3, column=1, pady=2, sticky="ew")

        tk.Label(form_alanlari, text="Durum:", bg="#f5f7fb").grid(row=4, column=0, sticky="w", pady=2)
        self.cmb_durum = ttk.Combobox(form_alanlari, state="readonly", values=["Aktif", "Pasif"])
        self.cmb_durum.set("Aktif")
        self.cmb_durum.grid(row=4, column=1, pady=2, sticky="ew")

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
        tk.Label(filter_frame, text="Tür:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_tur_filtre = ttk.Combobox(filter_frame, state="readonly", width=15, values=["Tümü", "Gider", "Gelir"])
        self.cmb_tur_filtre.set("Tümü")
        self.cmb_tur_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_tur_filtre.pack(side="left", padx=(0, 10))
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
        btn_excel = tk.Button(filter_frame, text="Excel'e Aktar", command=lambda: self.disari_aktar('excel'))
        btn_excel.pack(side="left", padx=(10, 0))

        btn_pdf = tk.Button(filter_frame, text="PDF'e Aktar", command=lambda: self.disari_aktar('pdf'))
        btn_pdf.pack(side="left", padx=(5, 0))

        # Liste Alanı
        tree_container = tk.Frame(liste_frame)
        tree_container.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_container, columns=("id", "kart_adi", "tur", "grup", "kdv_oran", "durum"), show="headings")
        self.tree.heading("id", text="ID"); self.tree.heading("kart_adi", text="Kart Adı"); self.tree.heading("tur", text="Tür"); self.tree.heading("grup", text="Grup"); self.tree.heading("kdv_oran", text="KDV %", anchor="e"); self.tree.heading("durum", text="Durum")
        self.tree.column("id", width=50, stretch=False, anchor="center"); self.tree.column("kart_adi", width=220); self.tree.column("tur", width=80, stretch=False); self.tree.column("grup", width=140, stretch=False); self.tree.column("durum", width=80, stretch=False, anchor="center")
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview); hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); vsb.pack(side="right", fill="y"); hsb.pack(side="bottom", fill="x"); self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.kayit_secildi); self.tree.tag_configure('passive', foreground='gray')
        self._init_sayfalama(self.tree)

    def _tur_degisti(self):
        """Kartın türü değişince grubu türe göre yeniden yükle."""
        self._yukle_gruplari()
        self._varsayilan_grup_sec()

    def _yukle_gruplari(self):
        """Seçili türe göre grupları yükler ve lookup'ı yapılandırır."""
        tur = self.cmb_tur.get()
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT grup_adi, id FROM hizmet_kartlari_gruplari WHERE durum=1 AND firma_id=? AND tur=? ORDER BY grup_adi",
            (self.main_app.aktif_firma_id, tur),
        )
        self.grup_dict = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        self.lookup_grup.configure_lookup(
            title=f"{tur} Grubu Seç", data_dict=self.grup_dict,
            on_new=lambda: self.yeni_grup_ekle(tur),
        )

    def yeni_grup_ekle(self, tur):
        """Lookup'tan yeni grup ekler; tür, kartın türünden gelir."""
        yeni_grup = ac_kart_dialog(
            self, "hizmet_kartlari_gruplari",
            firma_id=self.main_app.aktif_firma_id, kart_turu=tur,
        )
        if yeni_grup:
            self._yukle_gruplari()
            self.lookup_grup.set(yeni_grup[0])
        return yeni_grup

    def _varsayilan_grup_sec(self):
        """Grup zorunlu olduğu için varsayılan olarak 'Diğer' grubunu seç."""
        if "Diğer" in self.grup_dict:
            self.lookup_grup.set(self.grup_dict["Diğer"])

    def filtreleri_temizle(self):
        self.cmb_tur_filtre.set("Tümü"); self.cmb_durum_filtre.set("Aktif"); self.ent_arama.delete(0, tk.END); self.listele()

    def disari_aktar(self, format_type):
        self._tum_veriyi_yukle()
        export_treeview_data(self.tree, "Hizmet Kartları", format_type)
        self.listele()

    def formu_temizle(self):
        self.selected_id = None; self._original_tur = None; self.ent_kart_adi.delete(0, tk.END); self.cmb_tur.set("Gider"); self.ent_kdv_oran.delete(0, tk.END); self.ent_kdv_oran.insert(0, "20"); self.cmb_durum.set("Aktif"); self.ent_kart_adi.focus_set()
        self._yukle_gruplari(); self._varsayilan_grup_sec()
        if self.tree.selection(): self.tree.selection_remove(self.tree.selection())

    def listele(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        self._sayfa_yuklenen = 0
        self._sayfa_tukendi = False
        where_clauses = ["firma_id=?"]; params = [self.main_app.aktif_firma_id]
        if self.cmb_tur_filtre.get() != "Tümü": where_clauses.append("tur = ?"); params.append(self.cmb_tur_filtre.get())
        if self.cmb_durum_filtre.get() != "Tümü": where_clauses.append("durum = ?"); params.append(1 if self.cmb_durum_filtre.get() == "Aktif" else 0)
        if self.ent_arama.get().strip(): where_clauses.append("kart_adi LIKE ?"); params.append(f"%{self.ent_arama.get().strip()}%")
        # NOT: WHERE koşulları hizmet_kartlari tablosunu işaret etmeli
        # (grup tablosunda da firma_id/tur/durum sütunları olduğu için belirsizlik olmasın)
        self._sayfa_query = """SELECT h.id, h.kart_adi, h.tur, COALESCE(g.grup_adi, ''), h.durum, h.kdv_oran
                               FROM hizmet_kartlari h
                               LEFT JOIN hizmet_kartlari_gruplari g ON g.id = h.grup_id
                               WHERE h.""" + " AND h.".join(where_clauses) + " ORDER BY h.id DESC"
        self._sayfa_params = params
        self._diger_sayfa_yukle()

    def _satirlari_ekle(self, rows):
        for row in rows:
            durum_str = "Aktif" if row[4] == 1 else "Pasif"; tags = ('passive',) if row[4] == 0 else (); kdv_oran = row[5] or 0
            self.tree.insert("", "end", values=(row[0], row[1], row[2], row[3], f"{kdv_oran:g}", durum_str), tags=tags)

    def kayit_secildi(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items: return
        values = self.tree.item(selected_items[0], "values")
        if not values: return
        self.selected_id, kart_adi, tur, grup_adi, kdv_oran, durum_str = values
        self._original_tur = tur
        self.ent_kart_adi.delete(0, tk.END); self.ent_kart_adi.insert(0, kart_adi)
        self.cmb_tur.set(tur)
        self._yukle_gruplari()
        if grup_adi in self.grup_dict:
            self.lookup_grup.set(self.grup_dict[grup_adi])
        else:
            self._varsayilan_grup_sec()
        self.ent_kdv_oran.delete(0, tk.END); self.ent_kdv_oran.insert(0, kdv_oran); self.cmb_durum.set(durum_str)

    def kaydet_kart(self):
        kart_adi = self.ent_kart_adi.get().strip()
        if not kart_adi: messagebox.showerror("Hata", "Kart Adı boş bırakılamaz.", parent=self); return
        grup_id = self.lookup_grup.get()
        if not grup_id:
            messagebox.showerror("Hata", "Lütfen bir grup seçin (zorunlu).", parent=self)
            return
        kdv_oran = parse_currency(self.ent_kdv_oran.get())

        # Tür değişikliği kilidi: işlem görmüş kartın türü değiştirilemez (mizan dengesi)
        yeni_tur = self.cmb_tur.get()
        if self.selected_id and self._original_tur and self._original_tur != yeni_tur:
            conn_kontrol = None
            try:
                conn_kontrol = veritabani_baglan()
                if is_kart_kullanilmis_mi(conn_kontrol.cursor(), "hizmet_kartlari", self.selected_id, self.main_app.aktif_firma_id):
                    messagebox.showerror(
                        "Tür Değiştirilemez",
                        "Bu kart işlemlerde kullanıldığı için türü değiştirilemez.\n\n"
                        "Hizmet kartları raporu (mizan), gider kartlarını borç, gelir kartlarını "
                        "alacak kabul eder. Tür değişikliği bu dengeyi bozar.\n\n"
                        "İsterseniz aynı isimle yeni bir kart açın; mevcut kayıtlar bu kartta kalsın.",
                        parent=self,
                    )
                    return
            finally:
                if conn_kontrol:
                    conn_kontrol.close()

        hizmet_data = {'id': self.selected_id, 'kart_adi': kart_adi, 'tur': yeni_tur, 'grup_id': grup_id, 'kdv_oran': kdv_oran, 'durum': 1 if self.cmb_durum.get() == "Aktif" else 0, 'firma_id': self.main_app.aktif_firma_id}
        conn = None
        try:
            conn = veritabani_baglan(); cursor = conn.cursor()
            kaydet_kart(cursor, "hizmet_kartlari", hizmet_data); conn.commit()
            messagebox.showinfo("Başarılı", "Hizmet kartı başarıyla kaydedildi.", parent=self)
            self.formu_temizle(); self.listele()
        except sqlite3.IntegrityError: messagebox.showerror("Hata", "Bu kart adı zaten mevcut.", parent=self); conn.rollback()
        except Exception as e: messagebox.showerror("Hata", f"Kayıt hatası: {e}", parent=self); conn.rollback()
        finally:
            if conn: conn.close()

    def sil_kart(self):
        if not self.selected_id: messagebox.showwarning("Uyarı", "Lütfen silmek için bir kart seçin.", parent=self); return
        if not messagebox.askyesno("Onay", f"'{self.ent_kart_adi.get()}' adlı kartı silmek istediğinizden emin misiniz?", parent=self): return
        conn = None
        try:
            conn = veritabani_baglan(); cursor = conn.cursor()
            kart_sil_service(cursor, "hizmet_kartlari", self.selected_id, self.main_app.aktif_firma_id); conn.commit()
            messagebox.showinfo("Başarılı", "Hizmet kartı başarıyla silindi.", parent=self)
            self.formu_temizle(); self.listele()
        except ValueError as e: messagebox.showerror("Silme Hatası", str(e), parent=self); conn.rollback()
        except Exception as e: messagebox.showerror("Hata", f"Silme hatası: {e}", parent=self); conn.rollback()
        finally:
            if conn: conn.close()

    def yenile(self):
        self.listele()