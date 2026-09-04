# -*- coding: utf-8 -*-
"""
U2 — Kaydedilmemiş değişiklik (dirty) koruması.

İşlem formları bilerek ayrı tutuluyor (plan.md Kararlar), bu yüzden taban sınıf
YERİNE bu küçük ortak yardımcılar kullanılır:
  - form anlık durumu = üst alan değerleri + satır listesi (tree) imzası
  - form __init__ sonunda `kirlilik_baslatici(form)` çağrılır (temiz anlık kaydı)
  - iptal()/kapat() girişinde `iptal_onayla(form)` — kirlilik varsa sorar
  - kayıt tamamlandığında `anlik_yenile(form)` — temiz duruma alınır (kapanışta sormasın)
  - main_window, sekmeleri kapatmadan önce `modul_formu_kirli_mi(view)` ile sorar
"""
import tkinter.messagebox as messagebox


def _widget_deger(w):
    """Farklı widget tiplerinden karşılaştırılabilir düz değer alır."""
    if w is None:
        return None
    try:
        get_date = getattr(w, "get_date", None)  # tkcalendar DateEntry
        if get_date is not None and not hasattr(w, "get_value"):
            return str(get_date())
    except Exception:
        pass
    try:
        return str(w.get())
    except Exception:
        return "?"


def form_anlik(form, alan_adlari, agac_adlari=("tree_satirlar", "tree")):
    """Formun şu anki giriş durumunun karşılaştırılabilir imzası."""
    parca = []
    for ad in alan_adlari:
        parca.append((ad, _widget_deger(getattr(form, ad, None))))
    for ad in agac_adlari:
        agac = getattr(form, ad, None)
        if agac is None:
            continue
        try:
            satirlar = tuple(
                tuple(agac.item(iid, "values")) for iid in agac.get_children()
            )
            parca.append((ad, satirlar))
        except Exception:
            pass
    return tuple(parca)


def kirlilik_baslatici(form, alan_adlari, agac_adlari=("tree_satirlar", "tree")):
    """__init__ sonunda çağrılır: temiz anlık durum kaydı."""
    form._temiz_anlik = form_anlik(form, alan_adlari, agac_adlari)


def anlik_yenile(form):
    """Kayıt sonrası: formu 'temiz' işaretle (kapanışta uyarı çıkmasın)."""
    if hasattr(form, "_dirty_widget_adlari"):
        form._temiz_anlik = form_anlik(
            form, form._dirty_widget_adlari, form._dirty_agac_adlari
        )


def kirli_mi(form):
    anlik = getattr(form, "_temiz_anlik", None)
    if anlik is None or not hasattr(form, "_dirty_widget_adlari"):
        return False
    try:
        return form_anlik(
            form, form._dirty_widget_adlari, form._dirty_agac_adlari
        ) != anlik
    except Exception:
        return False


def dirty_kur(form, alan_adlari, agac_adlari=("tree_satirlar", "tree")):
    """Formda dirty takibini başlatır (alan adlarını forma kaydeder + ilk anlık)."""
    form._dirty_widget_adlari = tuple(alan_adlari)
    form._dirty_agac_adlari = tuple(agac_adlari)
    kirlilik_baslatici(form, alan_adlari, agac_adlari)


def iptal_onayla(form, mesaj=None):
    """
    iptal()/kapat() girişinde çağrılır.
    Temizse True (kapatılabilir); kirliyse kullanıcıya sorar, onaylarsa True.
    """
    if not kirli_mi(form):
        return True
    if mesaj is None:
        mesaj = ("Bu fişte kaydedilmemiş değişiklikler var.\n\n"
                 "Vazgeçip kapatmak istediğinize emin misiniz?")
    return messagebox.askyesno("Kaydedilmemiş Değişiklikler", mesaj, parent=form)


def modul_formu_kirli_mi(module_instance):
    """Bir modül görünümünde (view) açık ve kirli bir form var mı?"""
    form = getattr(module_instance, "form_instance", None)
    if form is None:
        return False
    return kirli_mi(form)


def yeni_fis_temel_sifirla(form):
    """
    U1 — "Kaydet ve Yeni Fiş" sonrası ortak sıfırlama:
    fiş kimliği, satır dict'i, satır ağacı, fiş no ve açıklama.
    Tarih ve ana hesap/lkup alanlarına DOKUNMAZ (formun kendi metodunda korunur).
    """
    form.fis_id = None
    satirlar = getattr(form, "satirlar", None)
    if satirlar is not None:
        satirlar.clear()
    for agac_adi in ("tree_satirlar", "tree"):
        agac = getattr(form, agac_adi, None)
        if agac is not None:
            agac.delete(*agac.get_children())
    for ent_adi in ("ent_fis_no", "ent_aciklama"):
        ent = getattr(form, ent_adi, None)
        if ent is not None:
            ent.delete(0, "end")
    form.satir_sayaci = 0
