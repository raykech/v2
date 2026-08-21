import tkinter as tk
from tkinter import messagebox, ttk


class LookupDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        title,
        data_dict,
        on_new_item,
        on_edit_item,
        on_delete_item,
        on_refresh=None,
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        self.data_dict = data_dict
        self.on_new_item = on_new_item
        self.on_edit_item = on_edit_item
        self.on_delete_item = on_delete_item
        self.on_refresh = on_refresh
        self.result = None

        self.create_widgets()
        self.populate_tree()

        self.ent_search.focus_set()

    def create_widgets(self):
        top_frame = tk.Frame(self, pady=5)
        top_frame.pack(fill="x", padx=10)

        tk.Label(top_frame, text="Ara:").pack(side="left")
        self.ent_search = tk.Entry(top_frame)
        self.ent_search.pack(side="left", fill="x", expand=True, padx=5)
        self.ent_search.bind("<KeyRelease>", self.search)

        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(
            tree_frame, columns=("id", "name"), show="headings"
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Ad / Unvan")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("name", width=450)
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self.on_select)

        bottom_frame = tk.Frame(self, pady=10)
        bottom_frame.pack(fill="x", padx=10)

        self.btn_select = tk.Button(
            bottom_frame,
            text="Seç",
            command=self.on_select,
            bg="#0d6efd",
            fg="white",
            width=12,
        )
        self.btn_select.pack(side="right", padx=5)

        self.btn_new = tk.Button(
            bottom_frame,
            text="Yeni Ekle",
            command=self.on_new,
            bg="#198754",
            fg="white",
            width=12,
        )
        self.btn_new.pack(side="left", padx=5)

        self.btn_edit = tk.Button(
            bottom_frame,
            text="Düzenle",
            command=self.on_edit,
            bg="#ffc107",
            fg="black",
            width=12,
        )
        self.btn_edit.pack(side="left", padx=5)

        self.btn_delete = tk.Button(
            bottom_frame,
            text="Sil",
            command=self.on_delete,
            bg="#dc3545",
            fg="white",
            width=12,
        )
        self.btn_delete.pack(side="left", padx=5)

    def populate_tree(self, filter_text=""):
        for row in self.tree.get_children():
            self.tree.delete(row)

        filter_text = filter_text.lower()
        for name, item_id in self.data_dict.items():
            if filter_text in name.lower():
                self.tree.insert("", "end", iid=item_id, values=(item_id, name))

    def search(self, event=None):
        self.populate_tree(self.ent_search.get())

    def on_select(self, event=None):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Uyarı", "Lütfen listeden bir kayıt seçin.")
            return

        item_id = selected_item
        item_name = self.tree.item(selected_item)["values"][1]
        self.result = (item_id, item_name)
        self.destroy()

    def on_new(self):
        if self.on_new_item:
            new_item_result = self.on_new_item()
            if new_item_result:
                new_id, new_name = new_item_result
                self.data_dict[new_name] = new_id
                self.populate_tree(self.ent_search.get())
                if self.on_refresh:
                    self.on_refresh()

    def on_edit(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Uyarı", "Lütfen düzenlemek için bir kayıt seçin.")
            return
        
        if not self.on_edit_item:
            return

        edited_item_result = self.on_edit_item(selected_item)
        if edited_item_result:
            edited_id, edited_name = edited_item_result
            old_name = next((name for name, i_id in self.data_dict.items() if str(i_id) == str(edited_id)), None)
            if old_name:
                del self.data_dict[old_name]
            self.data_dict[edited_name] = edited_id
            self.populate_tree(self.ent_search.get())

    def on_delete(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Uyarı", "Lütfen silmek için bir kayıt seçin.")
            return
        if self.on_delete_item and self.on_delete_item(selected_item):
            old_name = self.tree.item(selected_item)['values'][1]
            if old_name in self.data_dict:
                del self.data_dict[old_name]
            self.tree.delete(selected_item)

    def yenile(self, yeni_data_dict):
        """Diyalog açıkken listeyi yeni veriyle günceller."""
        self.data_dict = yeni_data_dict
        self.populate_tree(self.ent_search.get())

class LookupWidget(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent.winfo_toplevel()
        self.selected_id = None
        self.selected_name = None

        self.dialog_title = "Seçim"
        self.data_dict = {}
        self.on_new_item_callback = None
        self.on_edit_item_callback = None
        self.on_delete_item_callback = None
        self.main_module_yenile_callback = None

        self.create_widgets()

    def create_widgets(self):
        self.ent_display = tk.Entry(self, state="readonly", readonlybackground="white")
        self.ent_display.pack(side="left", fill="x", expand=True)

        self.btn_lookup = tk.Button(
            self, text="...", command=self.open_lookup, width=3
        )
        self.btn_lookup.pack(side="right")

    def configure_lookup(
        self,
        title,
        data_dict,
        on_new=None,
        on_edit=None,
        on_delete=None,
    ):
        self.dialog_title = title
        self.data_dict = data_dict
        self.on_new_item_callback = on_new
        self.on_edit_item_callback = on_edit
        self.on_delete_item_callback = on_delete
        
        self.main_module_yenile_callback = None
        main_app = self.parent_window.winfo_toplevel()
        if hasattr(main_app, "yenile_aktif_modul"):
            self.main_module_yenile_callback = main_app.yenile_aktif_modul

    def open_lookup(self):
        dialog = LookupDialog(
            self.parent_window,
            self.dialog_title,
            self.data_dict,
            self.on_new_item_callback,
            self.on_edit_item_callback,
            self.on_delete_item_callback,
            on_refresh=self.main_module_yenile_callback,
        )
        self.active_dialog = dialog # Açık olan diyaloğun referansını tut
        self.parent_window.wait_window(dialog)

        if dialog.result:
            self.selected_id, self.selected_name = dialog.result
            self.update_display()
            self.event_generate("<<LookupSelected>>")
        
        self.active_dialog = None # Diyalog kapandığında referansı temizle

    def get(self):
        return self.selected_id

    def get_value(self):
        return self.selected_name

    def set(self, item_id):
        self.selected_id = item_id
        self.selected_name = next(
            (name for name, i_id in self.data_dict.items() if str(i_id) == str(item_id)),
            "",
        )
        self.update_display()
        self.event_generate("<<LookupSelected>>")

    def clear(self):
        self.selected_id = None
        self.selected_name = None
        self.update_display()
        self.event_generate("<<LookupSelected>>")

    def update_display(self):
        self.ent_display.config(state="normal")
        self.ent_display.delete(0, tk.END)
        if self.selected_name:
            self.ent_display.insert(0, self.selected_name)
        self.ent_display.config(state="readonly")

    def disable(self):
        self.ent_display.config(state="disabled")
        self.btn_lookup.config(state="disabled")

    def enable(self):
        self.ent_display.config(state="readonly")
        self.btn_lookup.config(state="normal")