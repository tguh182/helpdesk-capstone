# Sistem Informasi Helpdesk Berbasis Web

Aplikasi Capstone Project: pelaporan dan penanganan gangguan TI dengan sistem tiket.
Dibangun dengan Python (Flask) dan SQLite.

## Menjalankan
```
pip install -r requirements.txt
python app.py
```
Buka http://127.0.0.1:5000. Database dan data awal dibuat otomatis saat pertama dijalankan.

## Akun contoh (ganti sebelum dipakai sungguhan)
| Peran | Username | Kata sandi |
|---|---|---|
| Administrator | admin | admin123 |
| Petugas TI | petugas | petugas123 |
| Pelapor | pelapor | pelapor123 |

Pelapor baru dapat mendaftar sendiri lewat halaman Daftar.

## Fitur (sesuai KF-01 s.d. KF-11 pada makalah)
Login, pengelolaan akun, pelaporan gangguan, nomor tiket otomatis (TKT-TTTTBBHH-001), kategori,
prioritas, penugasan petugas, pembaruan status (Menunggu / Diproses / Selesai), riwayat penanganan,
pemantauan tiket, dan rekapitulasi dengan filter periode, kategori, status, dan petugas.

## Keamanan
Kata sandi di-hash, token CSRF pada semua formulir, query SQL berparameter, escape otomatis
pada template, pembatasan akses berdasarkan peran, dan cookie sesi HttpOnly.

## Pengujian Black Box
```
python tests/test_blackbox.py
```
Menjalankan 10 skenario pada Tabel 4.4 makalah dan mencetak hasilnya.

## Struktur
- `app.py` aplikasi dan basis data (tabel: pengguna, kategori, tiket, riwayat)
- `templates/` halaman, `static/style.css` tampilan
- `screenshots/` tangkapan layar untuk Bab IV
