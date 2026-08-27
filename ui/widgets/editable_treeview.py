# -*- coding: utf-8 -*-
"""
Satır içi (Excel tarzı) düzenlenebilir Treeview bileşeni.

Bir hücreye çift tıklandığında:
  - 'text' / 'number' hücreleri için hücre üzerinde Entry editörü açılır.
  - 'lookup' hücreleri için içinde '...' butonu olan bir editör açılır; diyalog
    sadece '...' tıklanınca (veya Enter'a basınca) açılır.

Enter: değeri onaylar ve aynı satırda bir sonraki düzenlenebilir hücreye geçer.
Satır sonunda durur (alt satıra geçmez). Esc: iptal eder. Odak kaybı: onaylar.
Düzenlenen satır hafif bir renkle vurgulanır (tam satır seçimi yoktur).

Diğer modüllerde (banka, fatura, çek/senet) aynı bileşen, kendi column_config
ve on_edit'i ile kullanılabilir.
"""
import tkinter as tk
from tkinter import ttk

from utils.formatters import parse_currency


class EditableTreeview(ttk.Treeview):
    """
    column_config: {kolon_id: {
                        'type': 'text' | 'number' | 'lookup' | 'combobox',
                        'open_dialog': callable(iid) -> secilen_metin | None  (lookup),
                        'values': liste | callable  (combobox için)
                    }}
    on_edit(iid, kolon_id, deger) -> bool
        Düzenleme onaylandığında çağrılır.
        'number' için deger float, 'lookup' için seçilen metin, 'text' için str.
        True dönerse düzenleme kabul edilir; False dönerse hücre eski değerine döner.
    get_edit_value(iid, kolon_id) -> str  (opsiyonel)
        Editöre ön doldurulacak metni döndürür; verilmezse hücrenin mevcut metni kullanılır.
    """
    def __init__(self, master, column_config, on_edit, get_edit_value=None, **kwargs):
        kwargs.setdefault('selectmode', 'none')
        super().__init__(master, **kwargs)
        self._column_config = column_config or {}
        self._on_edit = on_edit
        self._get_edit_value = get_edit_value

        self._editor = None
        self._editor_is_lookup = False
        self._editor_advance = False
        self._editor_value = None
        self._edit_iid = None
        self._edit_col = None
        self._prev_value = None
        self._dialog_open = False

        self.tag_configure('editing', background='#fff3cd')

        self.bind("<Double-1>", self._on_double_click)

    # ------------------------------------------------------------- yardımcılar
    def _editable_columns(self):
        """Ağaç sırasına göre düzenlenebilir kolonlar."""
        return [c for c in self["columns"] if c in self._column_config]

    def _next_editable_cell(self, iid, col):
        """Aynı satırda bir sonraki düzenlenebilir hücre; satır sonunda durur (alt satıra geçmez)."""
        editable = self._editable_columns()
        try:
            idx = editable.index(col)
        except ValueError:
            return None
        if idx + 1 < len(editable):
            return (iid, editable[idx + 1])
        return None

    def _row_editing_vurgu(self, iid, aktif):
        """Düzenlenen satıra hafif vurgu tag'i ekler/kaldırır (tam satır seçimi yok)."""
        if not self.exists(iid):
            return
        mevcut = list(self.item(iid, 'tags'))
        if aktif:
            if 'editing' not in mevcut:
                mevcut.append('editing')
        else:
            if 'editing' in mevcut:
                mevcut.remove('editing')
        self.item(iid, tags=tuple(mevcut))

    # ------------------------------------------------------------- açma
    def _on_double_click(self, event):
        # Önce açık bir editör varsa onu onayla (başka satıra geçişte sessiz kayıp olmasın)
        self._commit_and_close()

        region = self.identify("region", event.x, event.y)
        if region not in ("cell", "tree"):
            return

        col_id = self.identify_column(event.x)
        if not col_id or col_id == '#0':
            return

        try:
            index = int(col_id.lstrip('#')) - 1
            column = self["columns"][index]
        except (ValueError, IndexError):
            return

        cfg = self._column_config.get(column)
        if not cfg:
            return  # Düzenlenemez kolon (ör. sil / hesaplanan tutarlar)

        row_id = self.identify_row(event.y)
        if not row_id:
            return

        self._open_cell(row_id, column, advance=False)

    def _open_cell(self, iid, col, advance=False):
        """Hücreyi düzenlemeye açar. advance=True ise onay sonrası zincir devam eder."""
        cfg = self._column_config.get(col)
        if not cfg:
            return
        if not self.exists(iid):
            return

        etype = cfg.get('type', 'text')
        if etype == 'lookup' and cfg.get('open_dialog'):
            self._open_lookup_editor(iid, col, cfg, advance)
            return
        if etype == 'combobox':
            self._open_combobox_editor(iid, col, cfg, advance)
            return

        bbox = self.bbox(iid, col)
        if not bbox:
            return
        x, y, w, h = bbox

        self._edit_iid = iid
        self._edit_col = col
        self._editor_is_lookup = False
        self._editor_advance = advance
        if self._get_edit_value is not None:
            self._prev_value = self._get_edit_value(iid, col) or ""
        else:
            self._prev_value = self.set(iid, col)

        self._row_editing_vurgu(iid, True)

        ed = tk.Entry(self, justify='right' if etype == 'number' else 'left')
        ed.insert(0, self._prev_value)
        ed.select_range(0, 'end')
        ed.bind("<Return>", self._on_enter)
        ed.bind("<Escape>", self._on_escape)
        ed.bind("<FocusOut>", self._on_focus_out)

        self._editor = ed
        ed.place(x=x, y=y, width=max(w, 40), height=max(h, 20))
        ed.focus_set()

    def _open_lookup_editor(self, iid, col, cfg, advance):
        """Lookup hücresi için readonly Entry + '...' butonu editörü açar."""
        bbox = self.bbox(iid, col)
        if not bbox:
            return
        x, y, w, h = bbox

        self._edit_iid = iid
        self._edit_col = col
        self._editor_is_lookup = True
        self._editor_advance = advance
        if self._get_edit_value is not None:
            self._prev_value = self._get_edit_value(iid, col) or ""
        else:
            self._prev_value = self.set(iid, col)
        self._editor_value = self._prev_value

        self._row_editing_vurgu(iid, True)

        frame = tk.Frame(self, bd=1, relief="solid")
        # Değeri ÖNCE yaz, SONRA readonly yap (readonly Entry'ye sonradan insert işlemez)
        entry = tk.Entry(frame, readonlybackground="white")
        entry.insert(0, self._prev_value)
        entry.config(state="readonly")
        entry.pack(side="left", fill="x", expand=True)
        btn = tk.Button(frame, text="...", width=3, command=self._lookup_pick)
        btn.pack(side="right")

        entry.bind("<Return>", self._on_enter)
        entry.bind("<Escape>", self._on_escape)
        frame.bind("<Return>", self._on_enter)
        frame.bind("<Escape>", self._on_escape)
        frame.bind("<FocusOut>", self._on_focus_out)

        self._editor = frame
        self._editor_entry = entry
        frame.place(x=x, y=y, width=max(w, 80), height=max(h, 22))
        btn.focus_set()

    def _open_combobox_editor(self, iid, col, cfg, advance):
        """Sabit seçenekli kolon (ör. Yön: Borç/Alacak) için Combobox editörü."""
        bbox = self.bbox(iid, col)
        if not bbox:
            return
        x, y, w, h = bbox

        self._edit_iid = iid
        self._edit_col = col
        self._editor_is_lookup = False
        self._editor_advance = advance
        if self._get_edit_value is not None:
            self._prev_value = self._get_edit_value(iid, col) or ""
        else:
            self._prev_value = self.set(iid, col)

        self._row_editing_vurgu(iid, True)

        values = cfg['values']() if callable(cfg.get('values')) else cfg.get('values', [])
        ed = ttk.Combobox(self, values=list(values), state='readonly')
        if self._prev_value in values:
            ed.set(self._prev_value)
        ed.bind("<<ComboboxSelected>>", self._on_combobox_selected)
        ed.bind("<Return>", self._on_enter)
        ed.bind("<Escape>", self._on_escape)
        ed.bind("<FocusOut>", self._on_focus_out)

        self._editor = ed
        ed.place(x=x, y=y, width=max(w, 40), height=max(h, 20))
        ed.focus_set()

    def _lookup_pick(self):
        """Lookup editöründeki '...' butonu / Enter: diyaloğu açar, seçimi uygular."""
        if self._editor is None:
            return
        iid, col = self._edit_iid, self._edit_col
        advance = self._editor_advance

        self._dialog_open = True
        try:
            selected = self._column_config.get(col, {}).get('open_dialog')(iid)
        finally:
            self._dialog_open = False

        if selected is not None:
            self._editor_value = selected
            entry = getattr(self, '_editor_entry', None)
            if entry is not None:
                entry.config(state="normal")
                entry.delete(0, "end")
                entry.insert(0, selected)
                entry.config(state="readonly")
            self._commit_and_close()
            # Kart seçildikten sonra her zaman bir sonraki alana geç (pratik akış)
            self._advance(iid, col)
        elif advance:
            # Zincirdeyken diyalog iptal edilirse mevcut değeri onaylayıp devam et
            self._commit_and_close()
            self._advance(iid, col)

    def _advance(self, iid, col):
        """Aynı satırda bir sonraki düzenlenebilir hücreye geçer (yoksa kapanır)."""
        nxt = self._next_editable_cell(iid, col)
        if nxt:
            self._open_cell(nxt[0], nxt[1], advance=True)

    # ------------------------------------------------------------- olaylar
    def _on_enter(self, event):
        iid, col = self._edit_iid, self._edit_col
        if self._editor_is_lookup:
            self._lookup_pick()  # Lookup'ta Enter, '...' ile aynı: diyaloğu açar
            return "break"
        accepted = self._commit_and_close()
        if accepted:
            self._advance(iid, col)
        return "break"

    def _on_escape(self, event):
        self._commit_and_close(cancel=True)
        return "break"

    def _on_combobox_selected(self, event):
        iid, col = self._edit_iid, self._edit_col
        accepted = self._commit_and_close()
        if accepted:
            self._advance(iid, col)
        return "break"

    def _on_escape(self, event):
        self._commit_and_close(cancel=True)
        return "break"

    def _on_focus_out(self, event):
        if self._editor is None or self._dialog_open:
            return
        etype = self._column_config.get(self._edit_col, {}).get('type', 'text')
        # Lookup/Combobox'ta açılır listeye tıklamak odak kaybına yol açabilir;
        # onay sadece açık seçimle (buton / ComboboxSelected) olur.
        if etype in ('lookup', 'combobox'):
            self._commit_and_close(cancel=True)
        else:
            self._commit_and_close()

    # ------------------------------------------------------------- kapatma
    def _commit_and_close(self, cancel=False):
        """Editörü kapatır. Onaylandıysa True, iptal/reddedildiyse False döner."""
        if self._editor is None:
            return False

        ed = self._editor
        iid, col = self._edit_iid, self._edit_col
        etype = self._column_config.get(col, {}).get('type', 'text')
        is_lookup = self._editor_is_lookup
        if is_lookup:
            raw = self._editor_value or ""
        else:
            raw = ed.get().strip()
        prev = self._prev_value  # Geri almak için temizlemeden önce sakla

        self._editor = None
        self._editor_is_lookup = False
        self._editor_advance = False
        self._editor_value = None
        self._edit_iid = None
        self._edit_col = None
        self._prev_value = None
        ed.destroy()
        self._row_editing_vurgu(iid, False)

        if cancel:
            return False  # Hücre olduğu gibi kalır.

        accepted = False
        if etype == 'number':
            try:
                val = parse_currency(raw)
                accepted = self._on_edit(iid, col, val)
            except (ValueError, TypeError):
                accepted = False
        elif etype == 'lookup':
            accepted = self._on_edit(iid, col, raw)
        else:
            accepted = self._on_edit(iid, col, raw)

        if not accepted and self.exists(iid):
            # Geçersiz değer: hücreyi eski metnine geri al
            self.set(iid, col, prev if prev is not None else "")
        return accepted

    def cancel_active_edit(self):
        """Formdan çağrılabilir: açık editörü kaydetmeden kapatır."""
        self._commit_and_close(cancel=True)
