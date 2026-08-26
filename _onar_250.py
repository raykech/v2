# -*- coding: utf-8 -*-
"""250 numaralı fişteki fazladan Hizmet satırını onarır."""
import sqlite3

conn = sqlite3.connect("on_muhasebe.db")
c = conn.cursor()

c.execute("DELETE FROM fis_satirlari WHERE fis_id=250 AND hesap_turu='Hizmet'")
conn.commit()

print("250 fişi kalan satırlar:")
for r in c.execute(
    "SELECT id, fis_id, hesap_turu, hesap_id, borc, alacak FROM fis_satirlari WHERE fis_id=250"
):
    print(r)

conn.close()
