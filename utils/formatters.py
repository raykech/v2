from datetime import datetime
import tkinter as tk

def format_currency(amount):
    """
    Verilen sayısal değeri para formatına (örn: 1.234,56 TL) çevirir.
    None gelirse "0,00 TL" döner.
    """
    if amount is None:
        amount = 0.0
    # Önce İngiliz formatına çevir (1,234.56), sonra , ve . yer değiştir
    formatted_amount = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted_amount} TL"

def parse_currency(text_value):
    """
    Metin formatındaki para değerini (örn: "1.234,56 TL") sayısal (float) değere çevirir.
    Boş veya geçersiz metin için 0.0 döner.
    """
    if not text_value:
        return 0.0
    try:
        # " TL" kısmını ve binlik ayraçlarını (nokta) kaldır, ondalık ayracı (virgül) noktaya çevir
        s = str(text_value).strip().replace(" TL", "").replace(".", "").replace(",", ".")
        return float(s)
    except (ValueError, TypeError):
        return 0.0

class CurrencyFormatter:
    """
    Bir Entry widget'ına bağlanarak kullanıcı yazdıkça para formatlaması yapar.
    """
    def __init__(self, entry_widget, on_change_callback=None):
        self.widget = entry_widget
        self.widget.bind("<KeyRelease>", self._on_key_release)
        self.widget.bind("<FocusOut>", self._on_focus_out)
        self.widget.bind("<FocusIn>", self._on_focus_in)
        self.on_change_callback = on_change_callback
        self._suspend_updates = False

    def set_value(self, value, trigger_callback=False):
        """Programatik değer atamada formatlama ve callback'i pasif hale getirir."""
        self._suspend_updates = True
        try:
            if value is None:
                formatted = ""
            else:
                raw_text = str(value).strip()
                normalized = raw_text.replace(" ", "").replace(" TL", "")
                if "," in normalized and "." in normalized:
                    normalized = normalized.replace(".", "").replace(",", ".")
                elif "," in normalized:
                    normalized = normalized.replace(".", "").replace(",", ".")
                elif normalized.count(".") > 1:
                    normalized = normalized.replace(".", "")

                try:
                    numeric_value = float(normalized)
                except ValueError:
                    numeric_value = parse_currency(raw_text)
                formatted = f"{numeric_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            self.widget.delete(0, tk.END)
            self.widget.insert(0, formatted)
        finally:
            self._suspend_updates = False

        if trigger_callback and self.on_change_callback:
            self.on_change_callback(None)

    def _on_key_release(self, event):
        if self._suspend_updates:
            return

        if event.keysym not in ("BackSpace", "Delete") and len(event.char) > 0 and not event.char.isprintable():
            return

        current_text = self.widget.get()
        cursor_pos = self.widget.index(tk.INSERT)

        parts = current_text.split(',', 1)
        integer_part_str = "".join(filter(str.isdigit, parts[0]))
        decimal_part_str = "".join(filter(str.isdigit, parts[1])) if len(parts) > 1 else ""

        if integer_part_str:
            formatted_integer = f"{int(integer_part_str):,}".replace(",", ".")
        else:
            formatted_integer = "0" if ',' in current_text else ""

        if ',' in current_text:
            decimal_part_str = decimal_part_str[:2]
            new_text = f"{formatted_integer},{decimal_part_str}"
        else:
            new_text = formatted_integer

        self.widget.delete(0, tk.END)
        self.widget.insert(0, new_text)

        cursor_adjustment = len(new_text) - len(current_text)
        self.widget.icursor(cursor_pos + cursor_adjustment)

        if self.on_change_callback:
            self.on_change_callback(event)

    def _on_focus_out(self, event):
        current_value = parse_currency(self.widget.get())
        self.widget.delete(0, tk.END)
        self.widget.insert(0, f"{current_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def _on_focus_in(self, event):
        if self.widget.get() == "0,00":
            self.widget.delete(0, tk.END)

def format_date(db_tarih: str) -> str:
    """
    Veritabanından gelen YYYY-MM-DD formatındaki tarihi GG.AA.YYYY formatına çevirir.
    Hata durumunda orijinal değeri döndürür.
    """
    try:
        return datetime.strptime(db_tarih, "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(db_tarih) if db_tarih else ""