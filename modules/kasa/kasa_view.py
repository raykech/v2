import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime
import re # Kaynak modül ayrıştırması için eklendi
from modules.kasa.kasa_form import KasaFisiFormu
from modules.acilis.acilis_form import AcilisFisiFormu
from modules.kasa.kasa_import import (
    kasa_ornek_excel_olustur,
    kasa_excel_oku,
    kasa_import_dogrula,
    kasa_fislerini_kaydet,
)
from core.db import veritabani_baglan
from ui.import_preview import ImportPreviewDialog
from ui.widgets.tooltip import Tooltip
from utils.formatters import format_date, format_currency, parse_currency
from core.services import fis_sil as fis_sil_service

class KasaModulu(tk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, bg="#f5f7fb")
        self.main_app = main_app
        self.parent = parent
        self.form_instance = None # Açık olan formu takip etmek için
        self.selected_fis_kaynak_modul = None # Seçili fişin kaynak modülü
        self.selected_fis_kaynak_fis_id = None # Seçili fişin kaynak fiş ID'si
        self.selected_fis_id = None # Seçili fişin kendi ID'si (kaynağa git için)
        self.kasa_dict = {} # Kasa filtresi için

        self.create_widgets()
        self._load_filter_data()
        self.listele()

    def create_widgets(self):
        # Üst Buton Alanı
        ust_frame = tk.Frame(self, bg="#f5f7fb")
        ust_frame.pack(fill="x", pady=10, padx=10)

        # "Yeni Fiş Ekle" butonu artık bir Menubutton
        self.btn_yeni = tk.Menubutton(
            ust_frame,
            text="Yeni ▼",
            font=("Arial", 9, "bold"),
            padx=10,
            pady=4,
        )
        self.btn_yeni.pack(side="left", padx=(0, 10))

        # Menubutton için menü oluşturma
        self.yeni_fis_menu = tk.Menu(self.btn_yeni, tearoff=0)
        self.btn_yeni["menu"] = self.yeni_fis_menu
        self.yeni_fis_menu.add_command(label="Kasa Açılış Fişi", command=lambda: self._ac_yeni_fis_formu("Kasa Açılış Fişi"))
        self.yeni_fis_menu.add_command(label="Kasa Gider Fişi", command=lambda: self._ac_yeni_fis_formu("Kasa Gider Fişi"))
        self.yeni_fis_menu.add_command(label="Kasa Gelir Fişi", command=lambda: self._ac_yeni_fis_formu("Kasa Gelir Fişi"))
        self.yeni_fis_menu.add_command(label="Kasalar Arası Virman", command=lambda: self._ac_yeni_fis_formu("Kasalar Arası Virman"))


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
        self.btn_kaynaga_git.pack(side="left", padx=(0, 10))

        self.btn_ornek_indir = tk.Button(
            ust_frame,
            text="Örnek İndir",
            command=self.ornek_indir,
            font=("Arial", 9, "bold"),
            padx=10,
            pady=4,
        )
        self.btn_ornek_indir.pack(side="left", padx=(0, 10))

        self.btn_veri_yukle = tk.Button(
            ust_frame,
            text="Veri Yükle",
            command=self.veri_yukle,
            font=("Arial", 9, "bold"),
            padx=10,
            pady=4,
        )
        self.btn_veri_yukle.pack(side="left", padx=(0, 10))

        # Filtre Alanı
        filter_frame = tk.LabelFrame(self, text="Filtrele", bg="#f5f7fb", padx=10, pady=5)
        filter_frame.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(filter_frame, text="Kasa:", bg="#f5f7fb").pack(side="left", padx=(0, 2))
        self.cmb_kasa_filtre = ttk.Combobox(filter_frame, state="readonly", width=20)
        self.cmb_kasa_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_kasa_filtre.pack(side="left", padx=(0, 5))

        tk.Label(filter_frame, text="Baş. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(5, 2))
        self.ent_bas_tarih_filtre = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bas_tarih_filtre.bind("<<DateEntrySelected>>", lambda e: self.listele())
        self.ent_bas_tarih_filtre.set_date(datetime(self.main_app.aktif_yil, 1, 1))
        self.ent_bas_tarih_filtre.pack(side="left", padx=(0, 5))

        tk.Label(filter_frame, text="Bit. Tarihi:", bg="#f5f7fb").pack(side="left", padx=(5, 2))
        self.ent_bit_tarih_filtre = DateEntry(filter_frame, date_pattern="dd.mm.yyyy", width=10)
        self.ent_bit_tarih_filtre.bind("<<DateEntrySelected>>", lambda e: self.listele())
        self.ent_bit_tarih_filtre.pack(side="left", padx=(0, 5))

        tk.Label(filter_frame, text="Fiş Türü:", bg="#f5f7fb").pack(side="left", padx=(5, 2))
        self.cmb_fis_turu_filtre = ttk.Combobox(filter_frame, state="readonly", width=25, values=["Tümü", "Kasa Gider Fişi", "Kasa Gelir Fişi", "Kasalar Arası Virman", "Kasa Açılış Fişi"])
        self.cmb_fis_turu_filtre.set("Tümü")
        self.cmb_fis_turu_filtre.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.cmb_fis_turu_filtre.pack(side="left", padx=(0, 5))

        tk.Label(filter_frame, text="Ara:", bg="#f5f7fb").pack(side="left", padx=(5, 2))
        self.ent_arama = tk.Entry(filter_frame)
        self.ent_arama.pack(side="left", fill="x", expand=True)
        self.ent_arama.bind("<KeyRelease>", lambda e: self.listele())

        btn_filtre_temizle = tk.Button(filter_frame, text="Filtreleri Temizle", command=self.filtreleri_temizle)
        btn_filtre_temizle.pack(side="left", padx=(10, 0))

        # Liste Alanı
        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(tree_container, columns=("id", "tarih", "fis_no", "kaynak", "fis_turu", "aciklama", "toplam_tutar"), show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("tarih", text="Tarih")
        self.tree.heading("fis_no", text="Fiş No")
        self.tree.heading("kaynak", text="Kaynak")
        self.tree.heading("fis_turu", text="Fiş Türü")
        self.tree.heading("aciklama", text="Açıklama")
        self.tree.heading("toplam_tutar", text="Toplam Tutar", anchor="e")

        self.tree.column("id", width=60, stretch=False, anchor="center")
        self.tree.column("tarih", width=100, stretch=False, anchor="center")
        self.tree.column("fis_no", width=80, stretch=False)
        self.tree.column("kaynak", width=120, stretch=False)
        self.tree.column("fis_turu", width=180, stretch=False)
        self.tree.column("aciklama", width=250)
        self.tree.column("toplam_tutar", width=120, stretch=False, anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._update_action_buttons_state() # Başlangıçta buton durumlarını ayarla

    def _load_filter_data(self):
        """Filtreler için kasa listesini yükler."""
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("SELECT id, kasa_adi FROM kasalar WHERE durum=1 AND firma_id=?", (self.main_app.aktif_firma_id,))
            self.kasa_dict = {row[1]: row[0] for row in cursor.fetchall()}
            conn.close()
            self.cmb_kasa_filtre['values'] = ["Tüm Kasalar"] + list(self.kasa_dict.keys())
            self.cmb_kasa_filtre.set("Tüm Kasalar")
        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Kasa listesi yüklenemedi: {e}", parent=self)

    def _on_tree_select(self, event):
        self._get_selected_fis_kaynak_info()
        self._update_action_buttons_state()

    def listele(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        # Base WHERE clauses for fisler table (aliased as f)
        where_clauses = ["f.firma_id=? AND f.yil=?"]
        params = [self.main_app.aktif_firma_id, self.main_app.aktif_yil]
        
        # Date range filter
        bas_tarih = self.ent_bas_tarih_filtre.get_date().strftime("%Y-%m-%d")
        bit_tarih = self.ent_bit_tarih_filtre.get_date().strftime("%Y-%m-%d")
        # Tarih aralığını aktif yılın sınırlarına göre kısıtla
        yil_bas = f"{self.main_app.aktif_yil}-01-01"
        yil_bit = f"{self.main_app.aktif_yil}-12-31"
        if bas_tarih < yil_bas: bas_tarih = yil_bas
        if bit_tarih > yil_bit: bit_tarih = yil_bit
        where_clauses.append("f.tarih BETWEEN ? AND ?")
        params.extend([bas_tarih, bit_tarih])

        secili_kasa = self.cmb_kasa_filtre.get()
        if secili_kasa != "Tüm Kasalar":
            kasa_id = self.kasa_dict.get(secili_kasa)
            if kasa_id:
                where_clauses.append("fs.hesap_id = ?")
                params.append(kasa_id)
        
        # Always filter for transactions that involve a 'Kasa' account in fis_satirlari (aliased as fs)
        join_clauses = ["JOIN fis_satirlari fs ON f.id = fs.fis_id"]
        where_clauses.append("fs.hesap_turu = 'Kasa'")

        secili_fis_turu = self.cmb_fis_turu_filtre.get()
        if secili_fis_turu != "Tümü":
            where_clauses.append("f.fis_turu = ?")
            params.append(secili_fis_turu)

        arama_metni = self.ent_arama.get().strip()
        if arama_metni:
            where_clauses.append("(f.fis_no LIKE ? OR f.aciklama LIKE ?)")
            params.extend([f"%{arama_metni}%", f"%{arama_metni}%"])

        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            
            query = f"""
                SELECT DISTINCT f.id, f.tarih, f.fis_no, f.kaynak_modul, f.kaynak_fis_id, f.fis_turu, f.aciklama, f.toplam_tutar
                FROM fisler f
                {' '.join(join_clauses)}
            """
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += " ORDER BY f.id DESC"

            cursor.execute(query, params)
            fisler = cursor.fetchall()
            conn.close()

            for fis in fisler:
                fis_id, tarih, fis_no, kaynak_modul_db, kaynak_fis_id_db, fis_turu, aciklama, toplam_tutar = fis
                # Sadece kaynak modülün adını göster
                kaynak_str = kaynak_modul_db or ""
                
                self.tree.insert("", "end", values=(
                    fis_id, format_date(tarih), fis_no or '', kaynak_str,
                    fis_turu, aciklama or '', format_currency(toplam_tutar)
                ))

        except Exception as e:
            messagebox.showerror("Veri Yükleme Hatası", f"Kasa fişleri yüklenemedi: {e}", parent=self)

    def filtreleri_temizle(self):
        self.cmb_kasa_filtre.set("Tüm Kasalar")
        self.ent_bas_tarih_filtre.set_date(datetime(self.main_app.aktif_yil, 1, 1))
        self.ent_bit_tarih_filtre.set_date(datetime.now())
        self.cmb_fis_turu_filtre.set("Tümü")
        self.ent_arama.delete(0, tk.END)
        self.listele()

    def ornek_indir(self):
        """Örnek Excel import şablonunu indirir."""
        dosya_yolu = filedialog.asksaveasfilename(
            title="Örnek Excel Şablonunu Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")],
            initialfile="kasa_import_ornek.xlsx",
            parent=self,
        )
        if not dosya_yolu:
            return

        try:
            kasa_ornek_excel_olustur(dosya_yolu)
            messagebox.showinfo("Başarılı", "Örnek Excel dosyası oluşturuldu.\nDoldurup tekrar Veri Yükle ile içe aktarabilirsiniz.", parent=self)
        except Exception as e:
            messagebox.showerror("Excel Oluşturma Hatası", f"Örnek dosya oluşturulamadı:\n{e}", parent=self)

    def veri_yukle(self):
        """Excel dosyasını okur, doğrular ve önizleme sonrası içe aktarır."""
        try:
            self._veri_yukle_impl()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Veri Yükleme Hatası", f"Beklenmeyen bir hata oluştu:\n{e}", parent=self)

    def _veri_yukle_impl(self):
        """Excel dosyasını okur, doğrular ve önizleme sonrası içe aktarır."""
        dosya_yolu = filedialog.askopenfilename(
            title="Kasa Excel Dosyası Seç",
            filetypes=[("Excel Dosyası", "*.xlsx *.xls")],
            parent=self,
        )
        if not dosya_yolu:
            return

        try:
            satirlar = kasa_excel_oku(dosya_yolu)
            print(f"[Kasa Import] Excel okundu, satır sayısı: {len(satirlar)}")
            hazir_fisler, hatalar, uyarilar = kasa_import_dogrula(
                satirlar,
                self.main_app.aktif_firma_id,
                self.main_app.aktif_yil,
            )
            print(f"[Kasa Import] Hazır fiş: {len(hazir_fisler)}, hata: {len(hatalar)}, uyarı: {len(uyarilar)}")
        except Exception as e:
            messagebox.showerror("Excel Okuma Hatası", f"Dosya okunurken bir hata oluştu:\n{e}", parent=self)
            return

        if not hazir_fisler and not hatalar:
            messagebox.showinfo("Bilgi", "Aktarılacak veri bulunamadı.\nExcel dosyası boş olabilir veya satırlar silinmiş olabilir.", parent=self)
            return

        import_basarili = False

        def import_callback():
            nonlocal import_basarili
            conn = None
            try:
                conn = veritabani_baglan()
                cursor = conn.cursor()
                eklenen_ids = kasa_fislerini_kaydet(cursor, hazir_fisler, self.main_app.aktif_firma_id, self.main_app.aktif_yil)
                conn.commit()
                import_basarili = True
                messagebox.showinfo("Başarılı", f"{len(eklenen_ids)} fiş başarıyla içe aktarıldı.", parent=self)
                return True
            except Exception as e:
                if conn:
                    conn.rollback()
                messagebox.showerror("İçe Aktarma Hatası", f"Fişler kaydedilirken bir hata oluştu:\n{e}", parent=self)
                return False
            finally:
                if conn:
                    conn.close()

        try:
            ImportPreviewDialog(
                self,
                "Kasa İçe Aktarma Önizleme",
                hazir_fisler,
                hatalar,
                uyarilar,
                on_import=import_callback,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Önizleme Hatası", f"Önizleme ekranı açılırken bir hata oluştu:\n{e}", parent=self)

        if import_basarili:
            self.filtreleri_temizle()
        else:
            self.yenile()

    def _ac_yeni_fis_formu(self, fis_turu):
        """Belirtilen fiş türü için yeni fiş formunu açar."""
        # Mevcut liste görünümünü gizle
        self.pack_forget()
        if fis_turu == "Kasa Açılış Fişi":
            self.form_instance = AcilisFisiFormu(self.parent, self.main_app, self, fis_turu=fis_turu, on_close=self.form_kapatildi)
        else:
            self.form_instance = KasaFisiFormu(self.parent, self.main_app, self, fis_turu=fis_turu, on_close=self.form_kapatildi)
        self.form_instance.pack(fill="both", expand=True)

    def fis_duzenle(self):
        if self.btn_duzenle['state'] == 'disabled':
            return # Buton pasifse işlem yapma

        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen düzenlemek için bir fiş seçin.", parent=self)
            return

        selected_item = selected_items[0]
        fis_id = self.tree.item(selected_item, "values")[0]
        fis_turu = self.tree.item(selected_item, "values")[4]

        self.pack_forget()
        if fis_turu == "Kasa Açılış Fişi":
            self.form_instance = AcilisFisiFormu(self.parent, self.main_app, self, fis_id=fis_id, fis_turu=fis_turu, on_close=self.form_kapatildi)
        else:
            self.form_instance = KasaFisiFormu(self.parent, self.main_app, self, fis_id=fis_id, fis_turu=fis_turu, on_close=self.form_kapatildi)
        self.form_instance.pack(fill="both", expand=True)

    def fis_sil(self):
        if self.btn_sil['state'] == 'disabled':
            return # Buton pasifse işlem yapma

        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silmek için bir fiş seçin.", parent=self)
            return

        selected_item = selected_items[0]
        fis_id = self.tree.item(selected_item, "values")[0] # fis_id'yi al

        if not messagebox.askyesno("Silme Onayı", f"ID: {fis_id} olan fişi ve tüm satırlarını silmek istediğinizden emin misiniz?\nBu işlem geri alınamaz!", parent=self):
            return

        conn = None
        try:
            conn = veritabani_baglan()
            cursor = conn.cursor()
            fis_sil_service(cursor, fis_id, self.main_app.aktif_firma_id)
            conn.commit()
            messagebox.showinfo("Başarılı", "Fiş başarıyla silindi.", parent=self)
            self.listele() # Listeyi yenile
        except Exception as e:
            if conn: conn.rollback()
            messagebox.showerror("Veritabanı Hatası", f"Silme işlemi sırasında bir hata oluştu:\n{e}", parent=self)
        finally:
            if conn: conn.close()

    def _get_selected_fis_kaynak_info(self):
        """Seçili fişin kaynak modül ve fiş ID bilgilerini günceller."""
        selected_items = self.tree.selection()
        if not selected_items:
            self.selected_fis_kaynak_modul = None
            self.selected_fis_kaynak_fis_id = None
            self.selected_fis_id = None
            return

        selected_item = selected_items[0]
        values = self.tree.item(selected_item, "values")
        
        fis_id = values[0]
        self.selected_fis_id = int(fis_id) # Fişin kendi ID'sini de sakla
        
        # Arayüzdeki metne güvenmek yerine, DB'den kesin bilgiyi al
        conn = veritabani_baglan()
        cursor = conn.cursor()
        cursor.execute("SELECT kaynak_modul, kaynak_fis_id FROM fisler WHERE id=?", (fis_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            self.selected_fis_kaynak_modul, self.selected_fis_kaynak_fis_id = result
        else:
            self.selected_fis_kaynak_modul, self.selected_fis_kaynak_fis_id = None, None

    def _update_action_buttons_state(self):
        """Seçili fişin kaynak modülüne göre butonların durumunu günceller."""
        if self.selected_fis_kaynak_modul and self.selected_fis_kaynak_modul != "Kasa":
            # Başka bir modülden geliyorsa düzenleme/silme pasif, kaynağa git aktif
            self.btn_duzenle.config(state="disabled")
            self.btn_sil.config(state="disabled")
            self.btn_kaynaga_git.config(state="normal")
            
            # Tooltip ekle
            tooltip_text = f"Bu fiş '{self.selected_fis_kaynak_modul}' modülünden oluşturulmuştur. Değişiklik yapmak için kaynak belgeye gidin."
            if not hasattr(self.btn_duzenle, '_tooltip'):
                self.btn_duzenle._tooltip = Tooltip(self.btn_duzenle, tooltip_text)
                self.btn_sil._tooltip = Tooltip(self.btn_sil, tooltip_text)
            else:
                self.btn_duzenle._tooltip.update_text(tooltip_text)
                self.btn_sil._tooltip.update_text(tooltip_text)

        else:
            # Kendi modülünden geliyorsa veya seçili fiş yoksa normal
            self.btn_duzenle.config(state="normal")
            self.btn_sil.config(state="normal")
            self.btn_kaynaga_git.config(state="disabled")
            if hasattr(self.btn_duzenle, '_tooltip'): # Tooltip'i gizle/kaldır
                self.btn_duzenle._tooltip.hide_tooltip()
                self.btn_sil._tooltip.hide_tooltip()

    def _kaynaga_git(self):
        """Kaynağa Git butonuna basıldığında ilgili modüle yönlendirir."""
        if not self.selected_fis_kaynak_modul:
            return
        hedef_fis_id = self.selected_fis_kaynak_fis_id
        if hedef_fis_id is None:
            # Bu fiş başka bir modüle ait ama türetilmiş değil (örn: Kasa listesinde görünen Cari Ödeme).
            # Kaynak modülde bu fişin kendisini seç.
            hedef_fis_id = self.selected_fis_id
        if hedef_fis_id is not None:
            self.main_app.go_to_module_and_select_fis(self.selected_fis_kaynak_modul.lower(), hedef_fis_id)

    def form_kapatildi(self):
        """Form kapatıldığında bu callback çağrılır."""
        self.form_instance = None

    def yenile(self):
        if self.form_instance:
            self.form_instance.yenile()
        else:
            if hasattr(self, "_load_filter_data"):
                self._load_filter_data()
            self.listele()

    def select_and_highlight_fis(self, fis_id):
        """Belirtilen fişi Treeview'de seçer ve görünür hale getirir."""
        self.filtreleri_temizle() # Önce filtreleri temizle
        secilen = None
        for item in self.tree.get_children():
            # fis_id'ler int olabilir, values[0] string olabilir, karşılaştırma için dönüştür
            if int(self.tree.item(item, "values")[0]) == int(fis_id):
                secilen = item
                break
        if secilen is None:
            # Tarih aralığı hedef fişi kapsamıyorsa aralığı genişletip tekrar ara
            self.ent_bas_tarih_filtre.set_date(datetime(self.main_app.aktif_yil - 1, 1, 1))
            self.ent_bit_tarih_filtre.set_date(datetime(self.main_app.aktif_yil + 1, 12, 31))
            self.listele()
            for item in self.tree.get_children():
                if int(self.tree.item(item, "values")[0]) == int(fis_id):
                    secilen = item
                    break
        if secilen is not None:
            self.tree.selection_set(secilen)
            self.tree.see(secilen)
            self._on_tree_select(None) # Buton durumlarını da güncelle
