"""Pengujian Black Box otomatis - 10 skenario sesuai Tabel 4.4 makalah."""
import os, re, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["HELPDESK_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
import app as A

A.app.config["TESTING"] = True
A.init_db()
hasil = []


def token(c, path="/login"):
    h = c.get(path).get_data(as_text=True)
    return re.search(r'name="_csrf" value="([^"]+)"', h).group(1)


def login(c, u, p):
    return c.post("/login", data={"username": u, "password": p, "_csrf": token(c)}, follow_redirects=True)


def post(c, url, **d):
    d["_csrf"] = token(c, "/dashboard")
    return c.post(url, data=d, follow_redirects=True)


def cek(no, fitur, kondisi):
    hasil.append((no, fitur, "Berhasil" if kondisi else "GAGAL"))


# 1 Login valid
pel = A.app.test_client(); r = login(pel, "pelapor", "pelapor123")
cek(1, "Login", b"Dashboard" in r.data)
# 2 Login tidak valid
x = A.app.test_client(); r = login(x, "pelapor", "salah")
cek(2, "Validasi login", b"salah" in r.data and b"Dashboard" not in r.data)
# 3 Pelaporan lengkap
r = post(pel, "/tiket/baru", judul="Printer macet", kategori_id="4", deskripsi="Kertas tersangkut")
cek(3, "Pelaporan", b"TKT-" in r.data and b"Printer macet" in r.data)
# 4 Validasi formulir
r = post(pel, "/tiket/baru", judul="", kategori_id="", deskripsi="")
cek(4, "Validasi formulir", r.status_code == 400 and b"wajib" in r.data)
# 5 Detail tiket
cek(5, "Pengelolaan tiket", b"Kertas tersangkut" in pel.get("/tiket/1").data)
# 6 Penugasan (admin)
adm = A.app.test_client(); login(adm, "admin", "admin123")
r = post(adm, "/tiket/1/atur", petugas_id="2", kategori_id="4", prioritas="Tinggi")
cek(6, "Penugasan", b"ditugaskan kepada Budi" in r.data)
# 7 Pembaruan status (petugas)
pet = A.app.test_client(); login(pet, "petugas", "petugas123")
r = post(pet, "/tiket/1/status", status="Diproses", catatan="Sedang diperiksa")
cek(7, "Pembaruan status", b"Diproses" in r.data)
# 8 Riwayat
r = post(pet, "/tiket/1/status", status="Selesai", catatan="Kertas dikeluarkan")
cek(8, "Riwayat penanganan", b"Sedang diperiksa" in r.data and b"Kertas dikeluarkan" in r.data)
# 9 Hak akses
bad = [pel.get("/admin/akun").status_code == 403, pel.get("/rekap").status_code == 403,
       A.app.test_client().get("/dashboard").status_code == 302,
       pel.post("/tiket/1/status", data={"status": "Selesai", "catatan": "x"}).status_code == 400]
p2 = A.app.test_client(); post_user = p2.post("/daftar", data={"nama": "B", "username": "b2", "password": "123456",
                                                              "_csrf": token(p2, "/daftar")})
login(p2, "b2", "123456")
bad.append(p2.get("/tiket/1").status_code == 403)
cek(9, "Hak akses", all(bad))
# 10 Rekapitulasi
r = adm.get("/rekap?status=Selesai")
cek(10, "Rekapitulasi", b"TKT-" in r.data and b"Selesai" in r.data)

print(f"{'No':<3} {'Fitur':<22} Hasil")
for n, f, s in hasil:
    print(f"{n:<3} {f:<22} {s}")
ok = sum(1 for *_, s in hasil if s == "Berhasil")
print(f"\n{ok}/{len(hasil)} skenario berhasil ({ok/len(hasil)*100:.0f}%)")
sys.exit(0 if ok == len(hasil) else 1)
