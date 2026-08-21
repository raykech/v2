import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

class AdvancedTreeview(tk.Frame):
    """
    Sıralama ve filtreleme özelliklerine sahip gelişmiş bir Treeview bileşeni.
    - Sütun başlıklarında sıralama okları.
    - Sütunların altında filtreleme için giriş kutuları (Entry, DateEntry, Combobox).
    - Filtre veya sıralama değiştiğinde bir callback fonksiyonunu tetikler.
    """
    def __init__(self, parent, columns, on_filter_sort_change=None):
        super().__init__(parent)
        self.columns_config = columns
        self.on_filter_sort_change = on_filter_sort_change

        self.filter_widgets = {}
        self.sort_indicator_labels = {}
        self.sort_column = None
        self.sort_direction = "ASC"
        
        # Varsayılan sıralama sütununu bul
        for col_name, config in self.columns_config.items():
            if config.get("default_sort", False):
                self.sort_column = col_name
                self.sort_direction = config.get("default_sort_dir", "DESC")
                break

        self._create_widgets()
        self._update_sort_indicators()
        
        # Bileşen oluşturulduktan sonra ilk veri yüklemesini kendisi tetiklesin.
        self.after(10, self._trigger_callback)

    def _create_widgets(self):
        # Hizalamayı garantilemek için ana içerik (başlıklar, liste) ve scrollbar ayrılıyor.
        main_panel = tk.Frame(self)
        main_panel.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(self, orient="vertical")
        vsb.pack(side="right", fill="y")

        # --- Eylem Çubuğu (Filtre Temizle) ---
        action_bar = tk.Frame(main_panel)
        action_bar.pack(fill="x", pady=(0, 5))
        clear_btn = tk.Button(
            action_bar,
            text="🧹 Filtreleri Temizle",
            command=self.clear_filters,
            relief="flat",
            font=("Arial", 8, "italic"),
            cursor="hand2"
        )
        clear_btn.pack(side="right")

        # --- Başlık ve Filtre Alanı ---
        header_filter_frame = tk.Frame(main_panel)
        header_filter_frame.pack(fill="x", pady=(0, 2))

        for i, (col_name, config) in enumerate(self.columns_config.items()):
            # Sütun genişliğini ve esnekliğini ayarla
            header_filter_frame.grid_columnconfigure(i, weight=config.get("weight", 0), minsize=config["width"])

            # --- Başlık ---
            header_frame = tk.Frame(header_filter_frame)
            header_frame.grid(row=0, column=i, sticky="ew")
            
            if config.get("sortable", False):
                header_frame.config(cursor="hand2")
                lbl = tk.Label(header_frame, text=config["text"], font=("Arial", 9, "bold"), cursor="hand2")
                lbl.pack(side="left", padx=(2, 0))
                
                indicator_lbl = tk.Label(header_frame, text="", font=("Arial", 9, "bold"), width=2)
                indicator_lbl.pack(side="right", padx=(0, 2))
                self.sort_indicator_labels[col_name] = indicator_lbl

                header_frame.bind("<Button-1>", lambda e, c=col_name: self._sort_by(c))
                lbl.bind("<Button-1>", lambda e, c=col_name: self._sort_by(c))
                indicator_lbl.bind("<Button-1>", lambda e, c=col_name: self._sort_by(c))
            else:
                lbl = tk.Label(header_frame, text=config["text"], font=("Arial", 9, "bold"))
                lbl.pack(side="left", padx=(2, 0))

            # --- Filtre ---
            filter_type = config.get("filter_type")
            filter_widget = None
            if filter_type == "entry":
                filter_widget = tk.Entry(header_filter_frame, font=("Arial", 9))
                filter_widget.bind("<KeyRelease>", self._on_filter_change)
            elif filter_type == "date":
                filter_widget = DateEntry(header_filter_frame, date_pattern="dd.mm.yyyy", font=("Arial", 9), locale='tr_TR')
                filter_widget.bind("<<DateEntrySelected>>", self._on_filter_change)
                filter_widget.bind("<KeyRelease>", self._on_filter_change) # For manual deletion
                filter_widget.delete(0, 'end') # Start empty
            elif filter_type == "combo":
                filter_widget = ttk.Combobox(header_filter_frame, values=config.get("values", []), state="readonly", font=("Arial", 9))
                filter_widget.set("Tümü")
                filter_widget.bind("<<ComboboxSelected>>", self._on_filter_change)
            
            if filter_widget:
                # Hizalama sorununu çözmek için sütunlar arası yatay padding kaldırıldı.
                filter_widget.grid(row=1, column=i, sticky="ew", pady=1)
                self.filter_widgets[col_name] = filter_widget

        # --- Treeview ---
        self.tree = ttk.Treeview(
            main_panel,
            columns=tuple(self.columns_config.keys()),
            show="", # İkinci, gereksiz başlıkları kaldır
            yscrollcommand=vsb.set
        )
        vsb.config(command=self.tree.yview)
        
        # Sütunların kaymasını önlemek için #0 (ağaç) sütununu gizle
        self.tree.column("#0", width=0, stretch=tk.NO)
        
        for col_name, config in self.columns_config.items():
            # self.tree.heading(col_name, text=config["text"]) # Artık Treeview başlığı yok
            anchor = config.get("anchor", "w")
            self.tree.column(col_name, width=config["width"], anchor=anchor, stretch=config.get("stretch", True))

        self.tree.pack(fill="both", expand=True)

        def _sync_widths(event=None):
            """Grid ve Treeview sütun genişliklerini senkronize eder."""
            for i, col_name in enumerate(self.columns_config.keys()):
                try:
                    self.tree.column(col_name, width=header_filter_frame.grid_bbox(i, 0)[2])
                except (TypeError, IndexError):
                    pass # Widget henüz çizilmemişse hata verme

        header_filter_frame.bind("<Configure>", _sync_widths)

    def _update_sort_indicators(self):
        for col, label in self.sort_indicator_labels.items():
            if col == self.sort_column:
                # Aktif sıralama sütunu için belirgin ve yönlü bir ok (▲/▼)
                label.config(text="▲" if self.sort_direction == "ASC" else "▼", fg="#212529")
            else:
                # Diğer sıralanabilir sütunlar için sıralanabilir olduğunu belirten soluk ve yönsüz bir ok (↕)
                label.config(text="↕", fg="#adb5bd")

    def _sort_by(self, column_name):
        if self.sort_column == column_name:
            self.sort_direction = "ASC" if self.sort_direction == "DESC" else "DESC"
        else:
            self.sort_column = column_name
            self.sort_direction = "ASC"
        self._update_sort_indicators()
        self._trigger_callback()

    def clear_filters(self):
        """Tüm filtre widget'larını varsayılan durumuna sıfırlar."""
        for widget in self.filter_widgets.values():
            if isinstance(widget, DateEntry):
                widget.delete(0, 'end')
                # tkcalendar'ın, boşaltıldıktan sonra odak kaybedince tarihi
                # geri getirmesini önlemek için bu dahili bayrağı ayarlıyoruz.
                widget._is_empty = True
            elif isinstance(widget, ttk.Combobox):
                widget.set("Tümü")
            elif isinstance(widget, tk.Entry):
                widget.delete(0, 'end')
        
        # Filtreleri temizledikten sonra listeyi yenilemek için callback'i tetikle
        self._on_filter_change()

    def _on_filter_change(self, event=None):
        if hasattr(self, "_filter_job"):
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(400, self._trigger_callback)

    def _trigger_callback(self):
        if not self.on_filter_sort_change:
            return

        filters = {}
        for col_name, widget in self.filter_widgets.items():
            value = None
            # Check for most specific types first (DateEntry inherits from Entry)
            if isinstance(widget, DateEntry):
                if widget.get(): # Sadece alan doluysa tarih almayı dene
                    try:
                        value = widget.get_date().strftime("%Y-%m-%d")
                    except (ValueError, AttributeError):
                        value = None
                # Alan boşsa value None olarak kalır
            elif isinstance(widget, ttk.Combobox):
                value = widget.get()
                if value == "Tümü": value = None
            elif isinstance(widget, tk.Entry):
                value = widget.get().strip()
            
            if value:
                filters[col_name] = value
        
        criteria = {
            "filters": filters,
            "sort": {"by": self.sort_column, "dir": self.sort_direction}
        }
        self.on_filter_sort_change(criteria)

    def update_combobox_values(self, column_name, new_values):
        """Bir combobox filtresinin değer listesini günceller."""
        if column_name in self.filter_widgets:
            widget = self.filter_widgets[column_name]
            if isinstance(widget, ttk.Combobox):
                widget['values'] = new_values
                # Mevcut seçimi korumaya çalış, yoksa sıfırla
                if widget.get() not in new_values:
                    widget.set("Tümü")

    # --- Dışarıya Açık Metotlar (Public API) ---
    def delete_all(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def insert(self, *args, **kwargs):
        return self.tree.insert(*args, **kwargs)

    def item(self, *args, **kwargs):
        return self.tree.item(*args, **kwargs)

    def selection(self, *args, **kwargs):
        return self.tree.selection(*args, **kwargs)
    
    def selection_remove(self, *args, **kwargs):
        return self.tree.selection_remove(*args, **kwargs)

    def bind(self, *args, **kwargs):
        self.tree.bind(*args, **kwargs)

    def tag_configure(self, *args, **kwargs):
        self.tree.tag_configure(*args, **kwargs)