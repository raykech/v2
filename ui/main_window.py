import tkinter as tk
from tkinter import ttk, messagebox
import importlib
import sys
from datetime import datetime

# Henüz oluşturulmamış modülleri import etmiyoruz
from modules.kasa.kasa_view import KasaModulu
from modules.tanimlar.tanimlar_view import TanimlarModulu
from modules.raporlar.raporlar_view import RaporlarModulu
from modules.fatura.fatura_view import FaturaModulu
from modules.cari.cari_view import CariModulu
from modules.banka.banka_view import BankaModulu
from modules.cek_senet.cek_senet_view import CekSenetModulu
from modules.ayarlar.ayarlar_view import AyarlarModulu
from modules.giris.dashboard_view import GirisDashboardView
from ui.widgets.tooltip import Tooltip
from ui.dialogs import FirmaYilDialog

class AnaPencere(tk.Tk):
    def __init__(self, firma_id, firma_adi, yil):
        super().__init__()
        self.title("Ön Muhasebe v2")
        self.geometry("1360x760")
        self.configure(bg="#f5f7fb")

        self.aktif_firma_id = firma_id
        self.aktif_firma_adi = firma_adi
        self.aktif_yil = yil

        self.open_tabs = {}
        self.active_tab_key = None
        self._drag_baslangic = None

        self._ust_menu_olustur()
        self._modul_butonlari_olustur()
        self._calisma_alani_olustur()
        self._status_bar_olustur()

        # Başlangıçta bir hoşgeldin ekranı gösterelim
        self._modul_aci("giris")

        # Geliştirme için F5 ile yeniden yükleme özelliği
        self.bind("<F5>", self._yeniden_yukle_aktif_modul)

        self.protocol("WM_DELETE_WINDOW", self.cikis_onayla)

    def _ust_menu_olustur(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        dosya_menu = tk.Menu(menubar, tearoff=0)
        dosya_menu.add_command(label="Çıkış", command=self.cikis_onayla)
        menubar.add_cascade(label="Dosya", menu=dosya_menu)

        moduller_menu = tk.Menu(menubar, tearoff=0)
        moduller_menu.add_command(label="Tanımlar", command=lambda: self._modul_aci("tanimlar"))
        moduller_menu.add_command(label="Kasa", command=lambda: self._modul_aci("kasa"))
        moduller_menu.add_command(label="Cari", command=lambda: self._modul_aci("cari"))
        moduller_menu.add_command(label="Raporlar", command=lambda: self._modul_aci("raporlar"))
        moduller_menu.add_command(label="Fatura", command=lambda: self._modul_aci("fatura"))
        moduller_menu.add_command(label="Banka", command=lambda: self._modul_aci("banka"))
        moduller_menu.add_command(label="Çek/Senet", command=lambda: self._modul_aci("cek_senet"))
        moduller_menu.add_command(label="Ayarlar", command=lambda: self._modul_aci("ayarlar"))
        menubar.add_cascade(label="Modüller", menu=moduller_menu)

    def _modul_butonlari_olustur(self):
        panel = tk.Frame(self, bg="#ffffff", padx=16, pady=14)
        panel.pack(fill="x", padx=10, pady=(10, 6))

        self.module_buttons = {
            "tanimlar": "Tanımlar",
            "kasa": "Kasa",
            "cari": "Cari",
            "fatura": "Fatura",
            "banka": "Banka",
            "cek_senet": "Çek/Senet",
            "raporlar": "Raporlar",
            "ayarlar": "Ayarlar",
        }

        for key, label in self.module_buttons.items():
            btn = tk.Button(
                panel,
                text=label,
                width=12,
                height=3,
                bg="#eaf2ff",
                fg="#0d6efd",
                font=("Arial", 10, "bold"),
                command=lambda k=key: self._modul_aci(k),
            )
            btn.pack(side="left", padx=5)

    def _calisma_alani_olustur(self):
        self.workspace = tk.Frame(self, bg="#ffffff", padx=10, pady=10)
        self.workspace.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tab_bar = tk.Frame(self.workspace, bg="#eef2f7")
        self.tab_bar.pack(fill="x", pady=(0, 5))

        self.content_area = tk.Frame(self.workspace, bg="#ffffff")
        self.content_area.pack(fill="both", expand=True)

    def _status_bar_olustur(self):
        status_bar = tk.Frame(self, bg="#4a69bd", height=28)
        status_bar.pack(side="bottom", fill="x")
        
        status_text = f"Firma: {self.aktif_firma_adi}  |  Çalışma Yılı: {self.aktif_yil}"
        self.lbl_status = tk.Label(
            status_bar,
            text=status_text,
            bg="#4a69bd",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2",
        )
        self.lbl_status.bind("<Button-1>", lambda e: self._firma_yil_degistir())
        self.lbl_status.pack(pady=4)

    def _firma_yil_degistir(self):
        """Status bar tıklanınca firma/yıl seçimini değiştirir."""
        dialog = FirmaYilDialog(self, self.aktif_firma_id, self.aktif_yil)
        if not dialog.result:
            return

        yeni_firma_id = dialog.result["firma_id"]
        yeni_firma_adi = dialog.result["firma_adi"]
        yeni_yil = dialog.result["yil"]

        # Aynı firma ve yıl seçildiyse işlem yapma
        if yeni_firma_id == self.aktif_firma_id and yeni_yil == self.aktif_yil:
            return

        self.aktif_firma_id = yeni_firma_id
        self.aktif_firma_adi = yeni_firma_adi
        self.aktif_yil = yeni_yil

        self.lbl_status.config(
            text=f"Firma: {self.aktif_firma_adi}  |  Çalışma Yılı: {self.aktif_yil}  |  (Tıklayarak değiştir)"
        )

        # Tüm açık sekmeleri kapat; yeni firma/yıl ile modüller temiz açılsın
        for key in list(self.open_tabs.keys()):
            if key != "giris":
                self._tab_kapat(key)
        self._tab_sec("giris")

    def _modul_aci(self, modul_key):
        # Şimdilik sadece placeholder olarak çalışacak
        if modul_key in self.open_tabs:
            self._tab_sec(modul_key)
            return

        tab_frame = tk.Frame(self.content_area, bg="#ffffff")
        tab_frame.pack(fill="both", expand=True)

        module_instance = None
        if modul_key == "giris":
            module_instance = GirisDashboardView(tab_frame, self)
            module_instance.pack(fill="both", expand=True)
        elif modul_key == "kasa":
            module_instance = KasaModulu(tab_frame, self)
            module_instance.pack(fill="both", expand=True)
        elif modul_key == "tanimlar":
            module_instance = TanimlarModulu(tab_frame, self)
            module_instance.pack(fill="both", expand=True)
        elif modul_key == "raporlar":
            module_instance = RaporlarModulu(tab_frame, self)
            module_instance.pack(fill="both", expand=True)
        elif modul_key == "fatura":
            module_instance = FaturaModulu(tab_frame, self)
            module_instance.pack(fill="both", expand=True)
        elif modul_key == "cari":
            module_instance = CariModulu(tab_frame, self)
            module_instance.pack(fill="both", expand=True)
        elif modul_key == "banka":
            module_instance = BankaModulu(tab_frame, self)
            module_instance.pack(fill="both", expand=True)
        elif modul_key == "cek_senet":
            module_instance = CekSenetModulu(tab_frame, self)
            module_instance.pack(fill="both", expand=True)
        elif modul_key == "ayarlar":
            module_instance = AyarlarModulu(tab_frame, self)
            module_instance.pack(fill="both", expand=True)
        else:
            tk.Label(tab_frame, text=f"'{self.module_buttons.get(modul_key)}' modülü henüz oluşturulmadı.", font=("Arial", 18), bg="white").pack(expand=True)

        self.open_tabs[modul_key] = {"frame": tab_frame, "module_instance": module_instance}
        self._tab_ekle(modul_key)
        self._tab_sec(modul_key)

    def _tab_ekle(self, modul_key):
        # Sekme için bir çerçeve oluştur, bu buton gibi davranacak
        tab_container = tk.Frame(self.tab_bar, bg="#d7e8ff")
        tab_container.pack(side="left", padx=(0, 4), pady=2, ipady=2)

        tab_text = self.module_buttons.get(modul_key, "Giriş")
        
        tab_label = tk.Label(tab_container, text=tab_text, bg="#d7e8ff", fg="#0d6efd", font=("Arial", 9, "bold"), padx=8, pady=2)
        tab_label.pack(side="left")

        # Seçim + sürükleme olaylarını konteynere ve etikete bağla
        tab_container.bind("<Button-1>", lambda e, k=modul_key: self._tab_tikla_bas(e, k))
        tab_container.bind("<B1-Motion>", lambda e, k=modul_key: self._tab_surukle(e, k))
        tab_container.bind("<ButtonRelease-1>", lambda e, k=modul_key: self._tab_surukle_birak(e, k))
        tab_label.bind("<Button-1>", lambda e, k=modul_key: self._tab_tikla_bas(e, k))
        tab_label.bind("<B1-Motion>", lambda e, k=modul_key: self._tab_surukle(e, k))
        tab_label.bind("<ButtonRelease-1>", lambda e, k=modul_key: self._tab_surukle_birak(e, k))

        self.open_tabs[modul_key]["tab_button"] = tab_container
        self.open_tabs[modul_key]["tab_label"] = tab_label

        # "Giriş" sekmesi hariç diğerlerine kapatma butonu ekle
        if modul_key != "giris":
            close_btn = tk.Label( # Daha şık görünmesi için Label kullanıyoruz
                tab_container, text="x", bg="#d7e8ff", fg="#0d6efd", font=("Arial", 8, "bold"), padx=5, cursor="hand2"
            )
            close_btn.pack(side="right", padx=(4, 4))
            close_btn.bind("<Button-1>", lambda e, k=modul_key: self._tab_kapat(k))
            close_btn.bind("<ButtonRelease-1>", lambda e, k=modul_key: self._tab_surukle_birak(e, k))
            self.open_tabs[modul_key]["close_button"] = close_btn

    def _tab_tikla_bas(self, event, modul_key):
        """Sekmeye basıldığında: sekmeyi aktif yapar ve sürükleme başlangıcını kaydeder."""
        self._tab_sec(modul_key)
        self._drag_baslangic = {"key": modul_key, "x": event.x_root, "surukleniyor": False}

    def _tab_surukle(self, event, modul_key):
        """Sürükleme sırasında sekmeyi fare konumuna göre yeniden sıralar."""
        if modul_key == "giris":
            return  # Giriş sekmesi sabittir, sürüklenemez
        if not self._drag_baslangic or self._drag_baslangic["key"] != modul_key:
            return
        dx = event.x_root - self._drag_baslangic["x"]
        if not self._drag_baslangic["surukleniyor"]:
            if abs(dx) < 8:  # 8px üzeri hareket sürükleme sayılır
                return
            self._drag_baslangic["surukleniyor"] = True

        # Fare konumuna göre hedef sırayı belirle
        hedef_x = event.x_root - self.tab_bar.winfo_rootx()
        mevcut_sira = list(self.open_tabs.keys())
        yeni_sira = [k for k in mevcut_sira if k != modul_key]

        hedef_index = len(yeni_sira)
        for i, k in enumerate(yeni_sira):
            btn = self.open_tabs[k]["tab_button"]
            btn_x = btn.winfo_x()
            if hedef_x < btn_x + btn.winfo_width() // 2:
                hedef_index = i
                break
        # Giriş sekmesi daima en başta kalsın (önüne sekme geçmesin)
        if "giris" in yeni_sira and hedef_index <= 1:
            hedef_index = 1
        yeni_sira.insert(hedef_index, modul_key)
        self._tablari_yeniden_paketle(yeni_sira)

    def _tab_surukle_birak(self, event, modul_key):
        """Sürükleme bittiğinde sürükleme durumunu temizler ve normal görünüme döner."""
        if modul_key not in self.open_tabs:
            return
        if not self._drag_baslangic:
            return
        surukleniyor = self._drag_baslangic.get("surukleniyor", False)
        self._drag_baslangic = None
        if surukleniyor:
            tab_container = self.open_tabs[modul_key]["tab_button"]
            tab_label = self.open_tabs[modul_key].get("tab_label")
            if modul_key == self.active_tab_key:
                tab_container.config(bg="#0d6efd")
                if tab_label: tab_label.config(bg="#0d6efd", fg="white")
            else:
                tab_container.config(bg="#d7e8ff")
                if tab_label: tab_label.config(bg="#d7e8ff", fg="#0d6efd")

    def _tablari_yeniden_paketle(self, sira):
        """Sekmeleri verilen sıraya göre yeniden paketler (sıra değişimi)."""
        for key in self.open_tabs:
            self.open_tabs[key]["tab_button"].pack_forget()
        for key in sira:
            if key in self.open_tabs:
                self.open_tabs[key]["tab_button"].pack(side="left", padx=(0, 4), pady=2, ipady=2)
        self.update_idletasks()

    def _tab_sec(self, modul_key):
        self.active_tab_key = modul_key
        for key, data in self.open_tabs.items():
            tab_container = data["tab_button"]
            tab_label = data.get("tab_label")
            close_btn = data.get("close_button")

            if key == modul_key:
                data["frame"].pack(fill="both", expand=True)
                tab_container.config(bg="#0d6efd")
                if tab_label: tab_label.config(bg="#0d6efd", fg="white")
                if close_btn: close_btn.config(bg="#0d6efd", fg="white")
                # Sekmeye geçildiğinde modül verilerini tazele
                # (başka bir modülde kaydedilen hareketlerin anında görünmesi için)
                module_instance = data.get("module_instance")
                if module_instance is not None and hasattr(module_instance, "yenile"):
                    try:
                        module_instance.yenile()
                    except Exception as e:
                        print(f"Modül yenileme hatası ({key}): {e}")
            else:
                data["frame"].pack_forget()
                tab_container.config(bg="#d7e8ff")
                if tab_label: tab_label.config(bg="#d7e8ff", fg="#0d6efd")
                if close_btn: close_btn.config(bg="#d7e8ff", fg="#0d6efd")

    def _tab_kapat(self, modul_key):
        if modul_key not in self.open_tabs:
            return

        data = self.open_tabs[modul_key]
        data["frame"].destroy()
        data["tab_button"].destroy() # Konteyner çerçevesini yok et
        # İçindeki label ve button'lar da otomatik yok olur
        del self.open_tabs[modul_key]

        # Eğer kapatılan sekme aktif ise, başka bir sekmeyi aktif yap
        if self.active_tab_key == modul_key:
            self.active_tab_key = None
            if self.open_tabs:
                # Kalan sekmelerden ilkini seç
                first_key = next(iter(self.open_tabs))
                self._tab_sec(first_key)

    def _yeniden_yukle_aktif_modul(self, event=None):
        """
        Geliştirme sırasında F5 tuşuna basıldığında aktif modülü yeniden yükler.
        Bu, uygulamayı yeniden başlatmadan kod değişikliklerini görmeyi sağlar.
        """
        if not self.active_tab_key or self.active_tab_key == "giris":
            print("Yeniden yüklenecek aktif bir modül yok.")
            return

        module_map = {
            "kasa": {
                "main_path": "modules.kasa.kasa_view",
                "class_name": "KasaModulu",
                "dependencies": [
                    "modules.kasa.kasa_form",
                    "modules.acilis.acilis_form",
                    "ui.widgets.advanced_treeview",
                    "core.services",
                    "utils.formatters",
                    "ui.widgets.lookup_widget",
                    "ui.dialogs"
                    "ui.widgets.tooltip", # Tooltip için
                    "re" # kasa_view.py'deki kaynak_modul ayrıştırması için
                ]
            },
            "tanimlar": {
                "main_path": "modules.tanimlar.tanimlar_view",
                "class_name": "TanimlarModulu",
                "dependencies": [
                    "modules.tanimlar.stok_view",
                    "modules.tanimlar.kasa_view",
                    "modules.tanimlar.cari_view",
                    "modules.tanimlar.hizmet_view",
                    "modules.tanimlar.banka_kurum_view",
                    "modules.tanimlar.banka_hesap_view",
                    "core.services",
                    "utils.formatters",
                    "ui.widgets.lookup_widget",
                    "ui.dialogs"
                    "ui.widgets.tooltip", # Tooltip için
                    "re" # fatura_view.py'deki kaynak_modul ayrıştırması için
                ]
            },
            "raporlar": {
                "main_path": "modules.raporlar.raporlar_view",
                "class_name": "RaporlarModulu",
                "dependencies": [
                    "modules.raporlar.hesap_ekstresi_view",
                    "modules.raporlar.stok_durum_raporu_view",
                    "modules.raporlar.cek_senet_raporlari_view",
                    "modules.raporlar.cek_senet_portfoy_raporu_view",
                    "modules.raporlar.cek_senet_vade_raporu_view",
                    "modules.raporlar.cek_senet_seruven_raporu_view",
                    "modules.raporlar.cek_senet_cari_raporu_view",
                    "modules.raporlar.kdv_raporu_view",
                    "core.services",
                    "utils.formatters",
                    "ui.widgets.lookup_widget",
                    "ui.dialogs",
                    "ui.widgets.tooltip", # Tooltip için
                    "utils.export",
                    "datetime" # export.py için eklendi
                ]
            },
                                    "fatura": {
                "main_path": "modules.fatura.fatura_view",
                "class_name": "FaturaModulu",
                "dependencies": [
                    "modules.fatura.fatura_form",
                    "core.services",
                    "utils.formatters",
                    "ui.widgets.lookup_widget",
                    "ui.dialogs",
                    "utils.export", # Fatura modülü için
                    "uuid", # Fatura modülü için
                    "ui.widgets.tooltip", # Tooltip için
                    "re" # Fatura modülü için
                ]
            },
                        "cari": {
                "main_path": "modules.cari.cari_view",
                "class_name": "CariModulu",
                "dependencies": [
                    "modules.cari.cari_form",
                    "modules.acilis.acilis_form",
                    "core.services",
                    "utils.formatters",
                    "ui.widgets.lookup_widget",
                    "ui.dialogs", # Cari formu (yeni kart ekleme)
                    "ui.widgets.tooltip",
                    "datetime" # Cari formu için
                ]
            },
            "banka": {
                "main_path": "modules.banka.banka_view",
                "class_name": "BankaModulu",
                "dependencies": [
                    "modules.banka.banka_form",
                    "modules.acilis.acilis_form",
                    "core.services",
                    "utils.formatters",
                    "ui.widgets.lookup_widget",
                    "ui.dialogs", # Banka formu (yeni kart ekleme)
                    "ui.widgets.tooltip",
                    "datetime" # Banka formu için
                ]
            },
            "cek_senet": {
                "main_path": "modules.cek_senet.cek_senet_view",
                "class_name": "CekSenetModulu",
                "dependencies": [
                    "modules.cek_senet.cek_senet_form",
                    "core.services",
                    "utils.formatters",
                    "ui.widgets.lookup_widget",
                    "ui.dialogs",
                    "ui.widgets.tooltip",
                    "datetime"
                ]
            },
            "ayarlar": {
                "main_path": "modules.ayarlar.ayarlar_view",
                "class_name": "AyarlarModulu",
                "dependencies": [
                    "modules.ayarlar.firma_tanimlari_view",
                    "modules.ayarlar.yil_tanimlari_view",
                    "core.db",
                    "core.services",
                    "ui.dialogs",
                    "ui.widgets.lookup_widget",
                    "utils.formatters"
                ]
            },
            # Gelecekte diğer modüller buraya eklenebilir
        }

    def go_to_module_and_select_fis(self, module_key, fis_id):
        # ... (Bu metodun içeriği zaten doğru, sadece _yeniden_yukle_aktif_modul'den ayrıştırıldı)
        """
        Belirtilen modülü açar ve o modüldeki belirli bir fişi seçer/vurgular.
        """
        if module_key not in self.module_buttons:
            messagebox.showerror("Hata", f"'{module_key}' modülü bulunamadı.", parent=self)
            return

        self._modul_aci(module_key) # Modülü açar veya aktif sekmeye getirir
        
        # Modülün instance'ına erişip fişi seçme metodunu çağır
        module_instance = self.open_tabs[module_key]["module_instance"]

        # Hedef modülde açık bir form varsa kapat, böylece liste görünümünde seçim yapılabilsin
        acik_form = getattr(module_instance, "form_instance", None)
        if acik_form is not None:
            if hasattr(acik_form, "iptal"):
                acik_form.iptal()
            elif hasattr(acik_form, "kapat"):
                acik_form.kapat()
            else:
                acik_form.pack_forget()
                module_instance.form_kapatildi()
                module_instance.pack(fill="both", expand=True)

        if hasattr(module_instance, "select_and_highlight_fis"):
            module_instance.select_and_highlight_fis(fis_id)
        else:
            messagebox.showwarning("Uyarı", f"'{module_key}' modülü fiş seçme özelliğini desteklemiyor.", parent=self)

    def _yeniden_yukle_aktif_modul(self, event=None):
        """
        Geliştirme sırasında F5 tuşuna basıldığında aktif modülü yeniden yükler.
        Bu, uygulamayı yeniden başlatmadan kod değişikliklerini görmeyi sağlar.
        """
        if not self.active_tab_key or self.active_tab_key == "giris":
            print("Yeniden yüklenecek aktif bir modül yok.")
            return

        module_map = {
            "kasa": {"main_path": "modules.kasa.kasa_view", "class_name": "KasaModulu", "dependencies": ["modules.kasa.kasa_form", "modules.acilis.acilis_form", "core.services", "utils.formatters", "ui.widgets.lookup_widget", "ui.dialogs", "ui.widgets.tooltip", "re"]},
            "tanimlar": {"main_path": "modules.tanimlar.tanimlar_view", "class_name": "TanimlarModulu", "dependencies": ["modules.tanimlar.stok_view", "modules.tanimlar.kasa_view", "modules.tanimlar.cari_view", "modules.tanimlar.hizmet_view", "modules.tanimlar.banka_kurum_view", "modules.tanimlar.banka_hesap_view", "core.services", "utils.formatters", "ui.widgets.lookup_widget", "ui.dialogs", "ui.widgets.tooltip", "re"]},
            "raporlar": {"main_path": "modules.raporlar.raporlar_view", "class_name": "RaporlarModulu", "dependencies": ["modules.raporlar.hesap_ekstresi_view", "modules.raporlar.stok_durum_raporu_view", "modules.raporlar.hizmet_kartlari_raporu_view", "modules.raporlar.cek_senet_raporlari_view", "modules.raporlar.cek_senet_portfoy_raporu_view", "modules.raporlar.cek_senet_vade_raporu_view", "modules.raporlar.cek_senet_seruven_raporu_view", "modules.raporlar.cek_senet_cari_raporu_view", "modules.raporlar.kdv_raporu_view", "core.services", "utils.formatters", "ui.widgets.lookup_widget", "ui.dialogs", "utils.export", "datetime", "ui.widgets.tooltip"]},
                        "fatura": {"main_path": "modules.fatura.fatura_view", "class_name": "FaturaModulu", "dependencies": ["modules.fatura.fatura_form", "core.services", "utils.formatters", "ui.widgets.lookup_widget", "ui.dialogs", "utils.export", "uuid", "ui.widgets.tooltip", "re"]},
            "cari": {"main_path": "modules.cari.cari_view", "class_name": "CariModulu", "dependencies": ["modules.cari.cari_form", "modules.acilis.acilis_form", "core.services", "utils.formatters", "ui.widgets.lookup_widget", "ui.dialogs"]},
            "banka": {"main_path": "modules.banka.banka_view", "class_name": "BankaModulu", "dependencies": ["modules.banka.banka_form", "modules.acilis.acilis_form", "core.services", "utils.formatters", "ui.widgets.lookup_widget", "ui.dialogs"]},
            "cek_senet": {"main_path": "modules.cek_senet.cek_senet_view", "class_name": "CekSenetModulu", "dependencies": ["modules.cek_senet.cek_senet_form", "core.services", "utils.formatters", "ui.widgets.lookup_widget", "ui.dialogs", "ui.widgets.tooltip", "datetime"]},
            "ayarlar": {"main_path": "modules.ayarlar.ayarlar_view", "class_name": "AyarlarModulu", "dependencies": ["modules.ayarlar.firma_tanimlari_view", "modules.ayarlar.yil_tanimlari_view", "core.db", "core.services", "ui.dialogs", "ui.widgets.lookup_widget", "utils.formatters"]},
            # Gelecekte diğer modüller buraya eklenebilir
        }

        modul_info = module_map.get(self.active_tab_key)
        if not modul_info:
            print(f"'{self.active_tab_key}' modülü için yeniden yükleme bilgisi bulunamadı.")
            return

        print(f"'{self.active_tab_key}' modülü ve bağımlılıkları yeniden yükleniyor...")
        try:
            # Önce bağımlılıkları, sonra ana modülü yeniden yükle (ters sırada)
            # Bu, bağımlılıkların doğru sırayla yeniden yüklenmesini sağlar
            for path in reversed(modul_info["dependencies"] + [modul_info["main_path"]]):
                if path in sys.modules: # Sadece yüklü olanları yeniden yükle
                    importlib.reload(sys.modules[path])
            
            # Aktif modülü kapatıp yeniden açarak arayüzü güncelleyin
            self._tab_kapat(self.active_tab_key) # Mevcut sekmeyi kapat
            self._modul_aci(self.active_tab_key) # Yeniden yüklenen modülü aç
            messagebox.showinfo("Yeniden Yükleme", f"'{self.active_tab_key}' modülü başarıyla yeniden yüklendi!", parent=self)
        except Exception as e:
            messagebox.showerror("Yeniden Yükleme Hatası", f"Modül yeniden yüklenirken bir hata oluştu:\n\n{e}")
            print(f"Hata: {e}")

    def cikis_onayla(self):
        if messagebox.askyesno("Çıkış Onayı", "Uygulamadan çıkmak istediğinize emin misiniz?"):
            self.destroy()

    def yenile_aktif_modul(self):
        """O an aktif olan sekmedeki modülün verilerini yeniler."""
        if self.active_tab_key and self.active_tab_key in self.open_tabs:
            data = self.open_tabs[self.active_tab_key]
            if "module_instance" in data and hasattr(data["module_instance"], "yenile"):
                try:
                    data["module_instance"].yenile()
                except Exception as e:
                    print(f"Aktif modül yenileme hatası ({self.active_tab_key}): {e}")