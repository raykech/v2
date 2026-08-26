# Veritabanı Tasarımı

> Bu doküman Laravel migrationlarında kullanılacak tabloları, kolonları ve ilişkileri tanımlar.

## Genel Kurallar
- Tüm tablolarda `id`, `created_at`, `updated_at` bulunur.
- Tüm firma bazlı tablolarda `firma_id` foreign key bulunur.
- Silme işlemlerinde `softDeletes` kullanılır.
- Para ve tutar alanları `decimal(15,2)` olarak tutulur.
- `yil` alanı fişin **tarih yılından** alınır.

## Tablolar

### firmalar
| Kolon | Tip | Açıklama |
|---|---|---|
| id | bigint PK | |
| firma_adi | string | |
| durum | boolean default true | |
| timestamps | | |

### users
Laravel default users tablosu + Spatie role/permission tabloları.
`firma_id` nullable olabilir; kullanıcı birden fazla firmaya bağlanabilir (`firma_user` pivot).

### firma_user
| Kolon | Tip |
|---|---|
| id | bigint PK |
| firma_id | foreignId |
| user_id | foreignId |
| rol | string nullable |

### stoklar
| Kolon | Tip | Açıklama |
|---|---|---|
| stok_kodu | string unique | Boş bırakılırsa otomatik üretilir |
| stok_adi | string | Zorunlu |
| kategori | string nullable | |
| birim | string default 'Adet' | |
| alis_fiyati | decimal(15,2) default 0 | |
| satis_fiyati | decimal(15,2) default 0 | |
| kritik_miktar | decimal(15,2) default 0 | |
| kdv_oran | decimal(5,2) default 20 | |
| firma_id | foreignId | |
| durum | boolean default true | |

### cariler
| Kolon | Tip | Açıklama |
|---|---|---|
| unvan | string | Zorunlu |
| tur | enum: Müşteri, Tedarikçi, Diğer | default Müşteri |
| telefon | string nullable | |
| firma_id | foreignId | |
| durum | boolean default true | |

### banka_kurumlari
| Kolon | Tip | Açıklama |
|---|---|---|
| kurum_adi | string | Unique (firma bazında) |
| firma_id | foreignId | |
| durum | boolean default true | |

### banka_hesaplari
| Kolon | Tip | Açıklama |
|---|---|---|
| hesap_adi | string | |
| kurum_id | foreignId -> banka_kurumlari | |
| hesap_turu | enum: Vadesiz, POS, Kredi Kartı | default Vadesiz |
| iban | string nullable | |
| komisyon_orani | decimal(5,2) default 0 | |
| firma_id | foreignId | |
| durum | boolean default true | |

### kasalar
| Kolon | Tip | Açıklama |
|---|---|---|
| kasa_adi | string | |
| firma_id | foreignId | |
| durum | boolean default true | |

### hizmet_kartlari_gruplari
| Kolon | Tip | Açıklama |
|---|---|---|
| grup_adi | string | |
| tur | enum: Gider, Gelir | |
| firma_id | foreignId | |
| durum | boolean default true | |
| unique | (grup_adi, tur, firma_id) | |

### hizmet_kartlari
| Kolon | Tip | Açıklama |
|---|---|---|
| kart_adi | string | |
| tur | enum: Gider, Gelir | |
| kdv_oran | decimal(5,2) default 20 | |
| grup_id | foreignId -> hizmet_kartlari_gruplari | |
| firma_id | foreignId | |
| durum | boolean default true | |

### genel_tanimlar
| Kolon | Tip | Açıklama |
|---|---|---|
| grup | string | Örn: Stok Kategorisi, Stok Birimi |
| deger | string | |
| firma_id | foreignId | |

### fisler
| Kolon | Tip | Açıklama |
|---|---|---|
| tarih | date | |
| fis_turu | string | Modüle göre değişir |
| fis_no | string nullable | |
| aciklama | text nullable | |
| cari_id | foreignId nullable | |
| kaynak_modul | string nullable | Fatura, Kasa, Banka... |
| kaynak_fis_id | bigint nullable | Bağlı fiş |
| toplam_tutar | decimal(15,2) default 0 | |
| durum | boolean default true | |
| firma_id | foreignId | |
| yil | integer | Tarih yılından alınır |
| timestamps | | |
| softDeletes | | |

### fis_satirlari
| Kolon | Tip | Açıklama |
|---|---|---|
| fis_id | foreignId -> fisler | cascade |
| hesap_turu | enum: Stok, Hizmet, Cari, Kasa, Banka, CekSenet | |
| hesap_id | bigint | İlgili kart ID |
| aciklama | text nullable | |
| miktar | decimal(15,2) default 1 | |
| birim_fiyat | decimal(15,2) default 0 | |
| borc | decimal(15,2) default 0 | |
| alacak | decimal(15,2) default 0 | |
| kdv_oran | decimal(5,2) default 0 | |
| kdv_tutar | decimal(15,2) default 0 | |
| firma_id | foreignId | |
| timestamps | | |

### cekler_senetler
| Kolon | Tip | Açıklama |
|---|---|---|
| seri_no | string unique | |
| turu | enum: Çek, Senet | |
| banka_id | foreignId nullable -> banka_kurumlari | |
| vade_tarihi | date | |
| tutar | decimal(15,2) | |
| kesideci | string nullable | |
| ciranta | string nullable | |
| aciklama | text nullable | |
| firma_id | foreignId | |
| timestamps | | |
| softDeletes | | |

### cek_senet_hareketleri
| Kolon | Tip | Açıklama |
|---|---|---|
| cek_senet_id | foreignId -> cekler_senetler | |
| fis_id | foreignId -> fisler | |
| islem_tarihi | date | |
| durum | enum: Portföyde, Bankada Tahsilde, Cirolu, Tahsil Edildi, İade Edildi | |
| karsi_hesap_tipi | string nullable | |
| karsi_hesap_id | bigint nullable | |
| karsi_hesap_ismi | string nullable | |
| ilgili_hareket_id | bigint nullable | |
| aciklama | text nullable | |
| firma_id | foreignId | |
| timestamps | | |

## İlişkiler
- `fisler` -> `fis_satirlari` (hasMany)
- `fis_satirlari` -> `fisler` (belongsTo)
- `fisler` -> `cariler` (belongsTo nullable)
- `fisler` -> `kaynak_fis_id` (kendine referans)
- `banka_hesaplari` -> `banka_kurumlari`
- `hizmet_kartlari` -> `hizmet_kartlari_gruplari`
- `cekler_senetler` -> `cek_senet_hareketleri`
- `cek_senet_hareketleri` -> `fisler`

## Index'ler
- `fisler`: `firma_id`, `yil`, `tarih`, `fis_turu`
- `fis_satirlari`: `fis_id`, `hesap_turu`, `hesap_id`, `firma_id`
- `cek_senet_hareketleri`: `cek_senet_id`, `fis_id`, `durum`


## Referans
- Mevcut Python projesi `reference/v2/core/db.py` → tablolari_olustur() metodu
- Tüm tabloların SQL şeması için: `reference/v2/core/db.py`