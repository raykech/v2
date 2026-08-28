import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime
from modules.cek_senet.cek_senet_form import CekSenetFisiFormu
from modules.cek_senet.cek_senet_import import (
    cek_senet_ornek_excel_olustur,
    cek_senet_excel_oku,
    cek_senet_import_dogrula,
    cek_senet_fislerini_kaydet,
)
from ui.import_preview import CekSenetImportPreviewDialog
from core.db import veritabani_baglan
from core.services import (
    cek_senet_fis_sil as cek_senet_fis_sil_service,
    cek_senet_fis_son_hareket_mi,
)
from ui.widgets.tooltip import Tooltip
from utils.formatters import format_date, format_currency
from ui.widgets.pagination import SayfaliListeMixin


class CekSenetModulu(SayfaliListeMixin, tk.Frame):
    """Çek/Senet modülünün liste görünümü."""

    FIS_TURLERI = [
        "Çek/Senet Giriş Fişi",
        "Çek/Senet Bankaya Tahsile Verme",
        "Çek/Senet Ciro Etme",
        "Çek/Senet Tahsil Fişi",
        "Çek/Senet İade Fişi",
        "Çek/Senet Açılış Fişi",
    ]

    DURUMLAR = [
        "Portföyde",
        "Bankada Tahsilde",
        "Cirolu",
        "Tahsil Edildi",
        "İade Edildi",
    ]

    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.parent = parent
        self.form_instance = None
        self.selected_fis_kaynak_modul = None
        self.selected_fis_kaynak_fis_id = None
        self.selected_fis_id = None
        self.selected_fis_son_hareket = False

        self.create_widgets()
        self.listele()

    def create_widgets(self):
        ust_frame = tk.Frame(self, bg="#f5f7fb")
        ust_frame.pack(fill="x", pady=10, padx=10)

        self.btn_yeni = tk.Menubutton(
            ust_frame,
            text="Yeni ▼",
            font=("Arial", 9, "bold"),
            padx=10,
            pady=4,
        )
        self.btn_yeni.pack(side="left", padx=(0, 10))

        self.btn_ornek_indir = tk.Button(
            ust_frame, text="Örnek İndir", command=self.ornek_indir,
            font=("Arial", 9, "bold"), padx=10, pady=4,
        )
        self.btn_ornek_indir.pack(side="left", padx=(0, 10))

        self.btn_veri_yukle = tk.Button(
            ust_frame, text="Veri Yükle", command=self.veri_yukle,
            font=("Arial", 9, "bold"), padx=10, pady=4,
        )
        self.btn_veri_yukle.pack(side="left", padx=(0, 10))

        self.yeni_fis_menu = tk.Menu(self.btn_yeni, tearoff=0)
        self.btn_yeni["menu"] = self.yeni_fis_menu
        for fis_turu in self.FIS_TURLERI:
            self.yeni_fis_menu.add_command(
                label=fis_turu,
                command=lambda t=fis_turu: self._ac_yeni_fis_formu(t),
            )

        self.btn_duzenle = tk.Button(
            ust_frame,
            text="Düzenle",
            command=self.fis_duzenle,
            font=("Arial", 9, "bold"),
            padx=10,
            pady=4,
        )
        self.btn_duzenle.pack(side="left", padx=(0, 10))

        self.btn_sil = tk.Button(
            ust_frame,
            text="Sil",
            command=self.fis_sil,
            font=("Arial", 9, "bold"),
            padx=10,
            pady=4,
        )
        self.btn_sil.pack(side="left")

        self.btn_kaynaga_git = tk.Button(
            ust_frame,
            text="Kaynağa Git",
            command=self._kaynaga_git,
            font=("Arial", 9, "bold"),
            padx=10,
            pady=4,
        )
        self.btn_kaynaga_git.pack(side="left", padx=(10, 0))

        filter_frame = tk.LabelFrame(self, text="Filtrele", bg="#f5f7fb", padx=10, pady=5)
        filter_frame.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(filter_frame, text="Çek/Senet Türü:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_cek_senet_turu_filtre = ttk.Combobox(
            filter_frame, state="readonly", width=12, values=["Tümü", "Çek", "Senet"]
        )
        self.cmb_cek_senet_turu_filtre.set("Tümü")
        self.cmb_cek_senet_turu_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_cek_senet_turu_filtre.pack(side="left", padx=(0, 5))

        tk.Label(filter_frame, text="Durum:", bg="#f5f7fb").pack(side="left", padx=(5, 2))
        self.cmb_durum_filtre = ttk.Combobox(
            filter_frame, state="readonly", width=16, values=["Tümü"] + self.DURUMLAR
        )
        self.cmb_durum_filtre.set("Tümü")
        self.cmb_durum_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_durum_filtre.pack(side="left", padx=(0, 5))

        tk.Label(filter_frame, text="Baş. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(5, 2))
        self.ent_bas_tarih_filtre = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bas_tarih_filtre.bind("<<DateEntrySelected>>", lambda e: self.listele())
        self.ent_bas_tarih_filtre.set_date(datetime(self.main_app.aktif_yil, 1, 1))
        self.ent_bas_tarih_filtre.pack(side="left", padx=(0, 5))

        tk.Label(filter_frame, text="Bit. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(5, 2))
        self.ent_bit_tarih_filtre = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bit_tarih_filtre.bind("<<DateEntrySelected>>", lambda e: self.listele())
        self.ent_bit_tarih_filtre.set_date(datetime.now())
        self.ent_bit_tarih_filtre.pack(side="left", padx=(0, 5))

        tk.Label(filter_frame, text="Fiş Türü:", bg="#f5f7fb").pack(side="left", padx=(5, 2))
        self.cmb_fis_turu_filtre = ttk.Combobox(
            filter_frame, state="readonly", width=22, values=["Tümü"] + self.FIS_TURLERI
        )
        self.cmb_fis_turu_filtre.set("Tümü")
        self.cmb_fis_turu_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_fis_turu_filtre.pack(side="left", padx=(0, 5))

        tk.Label(filter_frame, text="Ara:", bg="#f5f7fb").pack(side="left", padx=(5, 2))
        self.ent_arama = tk.Entry(filter_frame)
        self.ent_arama.pack(side="left", fill="x", expand=True)
        self.ent_arama.bind("<KeyRelease>", lambda e: self.listele())

        btn_filtre_temizle = tk.Button(filter_frame, text="Filtreleri Temizle", command=self.filtreleri_temizle)
        btn_filtre_temizle.pack(side="left", padx=(10, 0))

        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            tree_container,
            columns=("id", "tarih", "fis_no", "kaynak", "fis_turu", "seri_no", "aciklama", "toplam_tutar"),
            show="headings",
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("tarih", text="Tarih")
        self.tree.heading("fis_no", text="Fiş No")
        self.tree.heading("kaynak", text="Kaynak")
        self.tree.heading("fis_turu", text="Fiş Türü")
        self.tree.heading("seri_no", text="Seri No")
        self.tree.heading("aciklama", text="Açıklama")
        self.tree.heading("toplam_tutar", text="Toplam Tutar", anchor="e")

        self.tree.column("id", width=60, stretch=False, anchor="center")
        self.tree.column("tarih", width=100, stretch=False, anchor="center")
        self.tree.column("fis_no", width=80, stretch=False)
        self.tree.column("kaynak", width=100, stretch=False)
        self.tree.column("fis_turu", width=200, stretch=False)
        self.tree.column("seri_no", width=140, stretch=False)
        self.tree.column("aciklama", width=220)
        self.tree.column("toplam_tutar", width=120, stretch=False, anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._init_sayfalama(self.tree)
        self._update_action_buttons_state()

    def _on_tree_select(self, event):
        self._get_selected_fis_kaynak_info()
        self._update_action_buttons_state()

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._sayfa_yuklenen = 0
        self._sayfa_tukendi = False

        where_clauses = ["f.firma_id=? AND f.yil=?"]
        params = [self.main_app.aktif_firma_id, self.main_app.aktif_yil]

        bas_tarih = self.ent_bas_tarih_filtre.get_date().strftime("%Y-%m-%d")
        bit_tarih = self.ent_bit_tarih_filtre.get_date().strftime("%Y-%m-%d")
        # Tarih aralığını aktif yılın sınırlarına göre kısıtla
        yil_bas = f"{self.main_app.aktif_yil}-01-01"
        yil_bit = f"{self.main_app.aktif_yil}-12-31"
        if bas_tarih < yil_bas: bas_tarih = yil_bas
        if bit_tarih > yil_bit: bit_tarih = yil_bit
        where_clauses.append("f.tarih BETWEEN ? AND ?")
        params.extend([bas_tarih, bit_tarih])

        secili_tur = self.cmb_cek_senet_turu_filtre.get()
        if secili_tur != "Tümü":
            where_clauses.append("cs.turu = ?")
            params.append(secili_tur)

        secili_durum = self.cmb_durum_filtre.get()
        if secili_durum != "Tümü":
            where_clauses.append("h.durum = ?")
            params.append(secili_durum)

        secili_fis_turu = self.cmb_fis_turu_filtre.get()
        if secili_fis_turu != "Tümü":
            where_clauses.append("f.fis_turu = ?")
            params.append(secili_fis_turu)

        arama_metni = self.ent_arama.get().strip()
        if arama_metni:
            where_clauses.append("(f.fis_no LIKE ? OR f.aciklama LIKE ? OR cs.seri_no LIKE ?)")
            params.extend([f"%{arama_metni}%", f"%{arama_metni}%", f"%{arama_metni}%"])

        query = f"""
            SELECT DISTINCT f.id, f.tarih, f.fis_no, f.kaynak_modul, f.kaynak_fis_id,
                   f.fis_turu, f.aciklama, f.toplam_tutar,
                   GROUP_CONCAT(cs.seri_no, ', ') AS seri_nolar
            FROM fisler f
            JOIN cek_senet_hareketleri h ON f.id = h.fis_id
            JOIN cekler_senetler cs ON h.cek_senet_id = cs.id
            WHERE {" AND ".join(where_clauses)}
            GROUP BY f.id
            ORDER BY f.id DESC
        """
        self._sayfa_query = query
        self._sayfa_params = params
        self._diger_sayfa_yukle()

    def _satirlari_ekle(self, rows):
        for fis in rows:
            fis_id, tarih, fis_no, kaynak_modul_db, _, fis_turu, aciklama, toplam_tutar, seri_nolar = fis
            self.tree.insert("", "end", values=(
                fis_id,
                format_date(tarih),
                fis_no or "",
                kaynak_modul_db or "",
                fis_turu,
                seri_nolar or "",
                aciklama or "",
                format_currency(toplam_tutar),
            ))

    def filtreleri_temizle(self):
        self.cmb_cek_senet_turu_filtre.set("Tümü")
        self.cmb_durum_filtre.set("Tümü")
        self.ent_bas_tarih_filtre.set_date(datetime(self.main_app.aktif_yil, 1, 1))
        self.ent_bit_tarih_filtre.set_date(datetime.now())
        self.cmb_fis_turu_filtre.set("Tümü")
        self.ent_arama.delete(0, tk.END)
        self.listele()

    def ornek_indir(self):
        dosya_yolu = filedialog.asksaveasfilename(
            title="Örnek Excel Şablonunu Kaydet", defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")], initialfile="cek_senet_import_ornek.xlsx", parent=self,
        )
        if not dosya_yolu: return
        try:
            cek_senet_ornek_excel_olustur(dosya_yolu)
            messagebox.showinfo("Başarılı", "Örnek Excel dosyası oluşturuldu.", parent=self)
        except Exception as e:
            messagebox.showerror("Excel Oluşturma Hatası", f"Örnek dosya oluşturulamadı:\n{e}", parent=self)

    def veri_yukle(self):
        try:
            self._veri_yukle_impl()
        except Exception as e:
            import traceback; traceback.print_exc()
            messagebox.showerror("Veri Yükleme Hatası", f"Beklenmeyen bir hata oluştu:\n{e}", parent=self)

    def _veri_yukle_impl(self):
        dosya_yolu = filedialog.askopenfilename(
            title="Çek/Senet Excel Dosyası Seç", filetypes=[("Excel Dosyası", "*.xlsx *.xls")], parent=self,
        )
        if not dosya_yolu: return
        try:
            satirlar = cek_senet_excel_oku(dosya_yolu)
            hazir_fisler, hatalar, uyarilar = cek_senet_import_dogrula(satirlar, self.main_app.aktif_firma_id, self.main_app.aktif_yil)
        except Exception as e:
            messagebox.showerror("Excel Okuma Hatası", f"Dosya okunurken bir hata oluştu:\n{e}", parent=self)
            return
        if not hazir_fisler and not hatalar:
            messagebox.showinfo("Bilgi", "Aktarılacak veri bulunamadı.", parent=self)
            return
        import_basarili = False
        def import_callback():
            nonlocal import_basarili
            conn = None
            try:
                conn = veritabani_baglan(); cursor = conn.cursor()
                eklenen_ids = cek_senet_fislerini_kaydet(cursor, hazir_fisler, self.main_app.aktif_firma_id, self.main_app.aktif_yil)
                conn.commit(); import_basarili = True
                messagebox.showinfo("Başarılı", f"{len(eklenen_ids)} fiş başarıyla içe aktarıldı.", parent=self)
                return True
            except Exception as e:
                if conn: conn.rollback()
                messagebox.showerror("İçe Aktarma Hatası", str(e), parent=self)
                return False
            finally:
                if conn: conn.close()
        try:
            CekSenetImportPreviewDialog(self, "Çek/Senet İçe Aktarma Önizleme", hazir_fisler, hatalar, uyarilar, on_import=import_callback)
        except Exception as e:
            import traceback; traceback.print_exc()
            messagebox.showerror("Önizleme Hatası", str(e), parent=self)
        if import_basarili:
            self.listele()
        else:
            self.listele()

    def _ac_yeni_fis_formu(self, fis_turu):
        self.pack_forget()
        self.form_instance = CekSenetFisiFormu(
            self.parent, self.main_app, self, fis_turu=fis_turu, on_close=self.form_kapatildi,
        )
        self.form_instance.pack(fill="both", expand=True)

    def fis_duzenle(self):
        if self.btn_duzenle['state'] == 'disabled':
            return
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen düzenlemek için bir fiş seçin.", parent=self)
            return

        selected_item = selected_items[0]
        fis_id = self.tree.item(selected_item, "values")[0]
        fis_turu = self.tree.item(selected_item, "values")[4]

        self.pack_forget()
        self.form_instance = CekSenetFisiFormu(
            self.parent, self.main_app, self, fis_id=fis_id, fis_turu=fis_turu, on_close=self.form_kapatildi,
        )
        self.form_instance.pack(fill="both", expand=True)

    def fis_sil(self):
        if self.btn_sil['state'] == 'disabled':
            return
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silmek için bir fiş seçin.", parent=self)
            return

        selected_item = selected_items[0]
        fis_id = self.tree.item(selected_item, "values")[0]

        if not messagebox.askyesno(
            "Silme Onayı",
            f"ID: {fis_id} olan fişi ve tüm hareketlerini silmek istediğinizden emin misiniz?\nBu işlem geri alınamaz!",
            parent=self,
        ):
            return

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cek_senet_fis_sil_service(cursor, fis_id, self.main_app.aktif_firma_id)
            conn.commit()
            messagebox.showinfo("Başarılı", "Fiş başarıyla silindi.", parent=self)
            self.listele()
        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Veritabanı Hatası", f"Silme işlemi sırasında bir hata oluştu:\n{e}", parent=self)
        finally:
            if conn:
                conn.close()

    def _get_selected_fis_kaynak_info(self):
        selected_items = self.tree.selection()
        if not selected_items:
            self.selected_fis_kaynak_modul = None
            self.selected_fis_kaynak_fis_id = None
            self.selected_fis_id = None
            self.selected_fis_son_hareket = False
            return

        values = self.tree.item(selected_items[0], "values")
        fis_id = values[0]
        self.selected_fis_id = int(fis_id)

        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT kaynak_modul, kaynak_fis_id FROM fisler WHERE id=?", (fis_id,))
        result = cursor.fetchone()
        self.selected_fis_son_hareket = cek_senet_fis_son_hareket_mi(cursor, fis_id)
        conn.close()

        if result:
            self.selected_fis_kaynak_modul, self.selected_fis_kaynak_fis_id = result
        else:
            self.selected_fis_kaynak_modul, self.selected_fis_kaynak_fis_id = None, None

    def _update_action_buttons_state(self):
        if self.selected_fis_kaynak_modul and self.selected_fis_kaynak_modul != "CekSenet":
            self.btn_duzenle.config(state="disabled")
            self.btn_sil.config(state="disabled")
            self.btn_kaynaga_git.config(state="normal")
            tooltip_text = f"Bu fiş '{self.selected_fis_kaynak_modul}' modülünden oluşturulmuştur."
            if not hasattr(self.btn_duzenle, '_tooltip'):
                self.btn_duzenle._tooltip = Tooltip(self.btn_duzenle, tooltip_text)
                self.btn_sil._tooltip = Tooltip(self.btn_sil, tooltip_text)
            else:
                self.btn_duzenle._tooltip.update_text(tooltip_text)
                self.btn_sil._tooltip.update_text(tooltip_text)
        elif not self.selected_fis_son_hareket:
            self.btn_duzenle.config(state="disabled")
            self.btn_sil.config(state="disabled")
            self.btn_kaynaga_git.config(state="disabled")
            tooltip_text = "Bu fiş, çek/senedin son hareketi değil. Önce sonraki hareketleri silin/düzenleyin."
            if not hasattr(self.btn_duzenle, '_tooltip'):
                self.btn_duzenle._tooltip = Tooltip(self.btn_duzenle, tooltip_text)
                self.btn_sil._tooltip = Tooltip(self.btn_sil, tooltip_text)
            else:
                self.btn_duzenle._tooltip.update_text(tooltip_text)
                self.btn_sil._tooltip.update_text(tooltip_text)
        else:
            self.btn_duzenle.config(state="normal")
            self.btn_sil.config(state="normal")
            self.btn_kaynaga_git.config(state="disabled")
            if hasattr(self.btn_duzenle, '_tooltip'):
                self.btn_duzenle._tooltip.hide_tooltip()
                self.btn_sil._tooltip.hide_tooltip()

    def _kaynaga_git(self):
        if not self.selected_fis_kaynak_modul:
            return
        hedef_fis_id = self.selected_fis_kaynak_fis_id
        if hedef_fis_id is None:
            hedef_fis_id = self.selected_fis_id
        if hedef_fis_id is not None:
            self.main_app.go_to_module_and_select_fis(self.selected_fis_kaynak_modul.lower(), hedef_fis_id)

    def form_kapatildi(self):
        self.form_instance = None

    def yenile(self):
        if self.form_instance:
            self.form_instance.yenile()
        else:
            if hasattr(self, "_load_filter_data"):
                self._load_filter_data()
            self.listele()

    def select_and_highlight_fis(self, fis_id):
        self.filtreleri_temizle()
        secilen = self._tree_de_fis_ara(fis_id)
        if secilen is None:
            self.ent_bas_tarih_filtre.set_date(datetime(self.main_app.aktif_yil - 1, 1, 1))
            self.ent_bit_tarih_filtre.set_date(datetime(self.main_app.aktif_yil + 1, 12, 31))
            self.listele()
            secilen = self._tree_de_fis_ara(fis_id)
        if secilen is None:
            # Sayfalama: hedef fiş ilk yüklenen sayfada yoksa tüm kayıtları yükle
            self._sayfa_tukendi = False
            while not self._sayfa_tukendi:
                onceki = self._sayfa_yuklenen
                self._diger_sayfa_yukle()
                if self._sayfa_yuklenen == onceki and not self._sayfa_tukendi:
                    self._sayfa_tukendi = True  # ilerleme yoksa durdur
            secilen = self._tree_de_fis_ara(fis_id)
        if secilen is not None:
            self.tree.selection_set(secilen)
            self.tree.see(secilen)
            self._on_tree_select(None)

    def _tree_de_fis_ara(self, fis_id):
        for item in self.tree.get_children():
            try:
                if int(self.tree.item(item, "values")[0]) == int(fis_id):
                    return item
            except (TypeError, ValueError):
                continue
        return None
