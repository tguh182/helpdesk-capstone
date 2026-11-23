"""Sistem Informasi Helpdesk Berbasis Web - Capstone Project (Flask + SQLite)."""
import os, secrets, sqlite3
from datetime import datetime
from functools import wraps
from flask import (Flask, g, render_template, request, redirect, url_for,
                   session, flash, abort)
from werkzeug.security import generate_password_hash, check_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.config["DATABASE"] = os.environ.get("HELPDESK_DB", os.path.join(BASE, "helpdesk.db"))


def _secret():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    path = os.path.join(BASE, ".secret_key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    return open(path).read().strip()


app.secret_key = _secret()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.environ.get("HTTPS_ONLY") == "1")

STATUS = ["Menunggu", "Diproses", "Selesai"]
PRIORITAS = ["Rendah", "Sedang", "Tinggi"]
ROLES = {"pelapor": "Pelapor", "petugas": "Petugas TI", "admin": "Administrator"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS pengguna(
  id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT NOT NULL,
  username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('pelapor','petugas','admin')),
  aktif INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS kategori(
  id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS tiket(
  id INTEGER PRIMARY KEY AUTOINCREMENT, nomor TEXT NOT NULL UNIQUE,
  judul TEXT NOT NULL, deskripsi TEXT NOT NULL,
  kategori_id INTEGER REFERENCES kategori(id),
  prioritas TEXT NOT NULL DEFAULT 'Sedang',
  status TEXT NOT NULL DEFAULT 'Menunggu',
  pelapor_id INTEGER NOT NULL REFERENCES pengguna(id),
  petugas_id INTEGER REFERENCES pengguna(id),
  dibuat TEXT NOT NULL, diperbarui TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS riwayat(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tiket_id INTEGER NOT NULL REFERENCES tiket(id),
  pengguna_id INTEGER NOT NULL REFERENCES pengguna(id),
  status TEXT NOT NULL, catatan TEXT NOT NULL, waktu TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_tiket_status ON tiket(status);
CREATE INDEX IF NOT EXISTS ix_riwayat_tiket ON riwayat(tiket_id);
"""


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def isi_contoh(c):
    """Contoh laporan (opsional, env CONTOH_DATA=1) agar halaman tidak kosong saat demo/belajar."""
    from datetime import timedelta
    pel, pet, adm = 3, 2, 1
    kat = {r[1]: r[0] for r in c.execute("SELECT id,nama FROM kategori")}
    # (hari lalu, judul, deskripsi, kategori, prioritas, status, petugas, [(pengguna, status, catatan, menit_setelah_dibuat)])
    data = [
        (5, "Printer ruang administrasi tidak bisa mencetak",
         "Printer menampilkan lampu merah berkedip dan dokumen tertahan di antrean cetak sejak pagi.",
         "Printer", "Sedang", "Selesai", pet,
         [(adm, "Diproses", "Ditugaskan ke Budi Petugas.", 20),
          (pet, "Diproses", "Pengecekan awal: kertas macet di jalur belakang.", 60),
          (pet, "Selesai", "Kertas macet dibersihkan, antrean cetak di-reset. Printer normal kembali.", 180)]),
        (3, "Wi-Fi lantai 2 sangat lambat",
         "Koneksi internet di lantai 2 sering terputus, terutama pada jam 10.00 sampai 12.00.",
         "Jaringan Komputer", "Tinggi", "Diproses", pet,
         [(adm, "Diproses", "Ditugaskan ke Budi Petugas, prioritas tinggi.", 15),
          (pet, "Diproses", "Access point lantai 2 dicek; menunggu penggantian kabel jaringan.", 240)]),
        (2, "Aplikasi absensi tidak bisa dibuka",
         "Setelah pembaruan Windows, aplikasi absensi menutup sendiri saat dibuka.",
         "Perangkat Lunak", "Sedang", "Diproses", pet,
         [(adm, "Diproses", "Ditugaskan ke Budi Petugas.", 30),
          (pet, "Diproses", "Aplikasi dipasang ulang pada komputer uji, masih menyelidiki penyebab.", 120)]),
        (1, "Monitor komputer meja resepsionis berkedip",
         "Layar berkedip tiap beberapa detik dan kadang mati sendiri.",
         "Perangkat Keras", "Rendah", "Menunggu", None, []),
        (0, "Permintaan akun email untuk pegawai baru",
         "Mohon dibuatkan akun email kantor untuk pegawai baru atas nama Rina, mulai bekerja Senin depan.",
         "Lainnya", "Rendah", "Menunggu", None, []),
    ]
    nomor_hari = {}
    for hari, judul, desk, kt, pr, st, petugas, rw in data:
        t0 = datetime.now() - timedelta(days=hari, hours=1)
        tgl = t0.strftime("%Y%m%d")
        nomor_hari[tgl] = nomor_hari.get(tgl, 0) + 1
        nomor = f"TKT-{tgl}-{nomor_hari[tgl]:03d}"
        waktu = lambda m: (t0 + timedelta(minutes=m)).strftime("%Y-%m-%d %H:%M:%S")
        akhir = waktu(rw[-1][3]) if rw else waktu(0)
        cur = c.execute("INSERT INTO tiket(nomor,judul,deskripsi,kategori_id,prioritas,status,pelapor_id,petugas_id,dibuat,diperbarui)"
                        " VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (nomor, judul, desk, kat[kt], pr, st, pel, petugas, waktu(0), akhir))
        tid = cur.lastrowid
        c.execute("INSERT INTO riwayat(tiket_id,pengguna_id,status,catatan,waktu) VALUES(?,?,?,?,?)",
                  (tid, pel, "Menunggu", "Tiket dibuat.", waktu(0)))
        for uid, status, cat, m in rw:
            c.execute("INSERT INTO riwayat(tiket_id,pengguna_id,status,catatan,waktu) VALUES(?,?,?,?,?)",
                      (tid, uid, status, cat, waktu(m)))


def init_db(seed=True):
    c = sqlite3.connect(app.config["DATABASE"])
    c.executescript(SCHEMA)
    if seed and not c.execute("SELECT 1 FROM pengguna LIMIT 1").fetchone():
        env = os.environ.get
        for nama, u, p, r in [("Administrator", "admin", env("ADMIN_PASSWORD", "admin123"), "admin"),
                              ("Budi Petugas", "petugas", env("PETUGAS_PASSWORD", "petugas123"), "petugas"),
                              ("Sari Pelapor", "pelapor", env("PELAPOR_PASSWORD", "pelapor123"), "pelapor")]:
            c.execute("INSERT INTO pengguna(nama,username,password_hash,role) VALUES(?,?,?,?)",
                      (nama, u, generate_password_hash(p), r))
        for k in ["Perangkat Keras", "Jaringan Komputer", "Perangkat Lunak", "Printer", "Lainnya"]:
            c.execute("INSERT INTO kategori(nama) VALUES(?)", (k,))
        if os.environ.get("CONTOH_DATA") == "1":
            isi_contoh(c)
    c.commit()
    c.close()


# ---------- keamanan: sesi, peran, CSRF ----------
def current_user():
    if "uid" not in session:
        return None
    if not hasattr(g, "user"):
        g.user = db().execute("SELECT * FROM pengguna WHERE id=? AND aktif=1",
                              (session["uid"],)).fetchone()
    return g.user


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrap(*a, **kw):
            u = current_user()
            if not u:
                return redirect(url_for("login", next=request.path))
            if roles and u["role"] not in roles:
                abort(403)
            return fn(*a, **kw)
        return wrap
    return deco


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


@app.before_request
def check_csrf():
    if request.method == "POST":
        if not secrets.compare_digest(request.form.get("_csrf", ""), session.get("_csrf", "x")):
            abort(400)


@app.context_processor
def inject():
    return dict(user=current_user(), csrf_token=csrf_token, ROLES=ROLES,
                APP_NAME=os.environ.get("APP_NAME", "Helpdesk TI"),
                STATUS=STATUS, PRIORITAS=PRIORITAS)


@app.errorhandler(403)
def e403(_):
    return render_template("error.html", kode=403, pesan="Anda tidak memiliki hak akses ke halaman ini."), 403


@app.errorhandler(404)
def e404(_):
    return render_template("error.html", kode=404, pesan="Halaman tidak ditemukan."), 404


@app.errorhandler(400)
def e400(_):
    return render_template("error.html", kode=400, pesan="Permintaan tidak valid. Muat ulang halaman lalu coba lagi."), 400


# ---------- autentikasi ----------
@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("dashboard" if current_user() else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute("SELECT * FROM pengguna WHERE username=? AND aktif=1",
                         (request.form.get("username", "").strip(),)).fetchone()
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session.clear()
            session["uid"] = u["id"]
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
        flash("Username atau kata sandi salah.", "error")
    return render_template("login.html")


@app.route("/daftar", methods=["GET", "POST"])
def daftar():
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        un = request.form.get("username", "").strip()
        pw = request.form.get("password", "")
        if not nama or not un or len(pw) < 6:
            flash("Nama, username wajib diisi dan kata sandi minimal 6 karakter.", "error")
        elif db().execute("SELECT 1 FROM pengguna WHERE username=?", (un,)).fetchone():
            flash("Username sudah digunakan.", "error")
        else:
            db().execute("INSERT INTO pengguna(nama,username,password_hash,role) VALUES(?,?,?,'pelapor')",
                         (nama, un, generate_password_hash(pw)))
            db().commit()
            flash("Akun berhasil dibuat. Silakan login.", "ok")
            return redirect(url_for("login"))
    return render_template("daftar.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- dashboard ----------
def scope_sql(u):
    if u["role"] == "pelapor":
        return " WHERE t.pelapor_id=?", [u["id"]]
    if u["role"] == "petugas":
        return " WHERE t.petugas_id=?", [u["id"]]
    return "", []


BASE_Q = """SELECT t.*, k.nama AS kategori, p.nama AS pelapor, s.nama AS petugas
 FROM tiket t LEFT JOIN kategori k ON k.id=t.kategori_id
 JOIN pengguna p ON p.id=t.pelapor_id LEFT JOIN pengguna s ON s.id=t.petugas_id"""


@app.route("/dashboard")
@login_required()
def dashboard():
    u = current_user()
    w, a = scope_sql(u)
    counts = {s: 0 for s in STATUS}
    for r in db().execute("SELECT t.status, COUNT(*) n FROM tiket t" + w + " GROUP BY t.status", a):
        counts[r["status"]] = r["n"]
    terbaru = db().execute(BASE_Q + w + " ORDER BY t.id DESC LIMIT 5", a).fetchall()
    belum = 0
    if u["role"] == "admin":
        belum = db().execute("SELECT COUNT(*) FROM tiket WHERE petugas_id IS NULL AND status!='Selesai'").fetchone()[0]
    return render_template("dashboard.html", counts=counts, total=sum(counts.values()),
                           terbaru=terbaru, belum=belum)


# ---------- tiket ----------
def next_nomor():
    prefix = "TKT-" + datetime.now().strftime("%Y%m%d") + "-"
    n = db().execute("SELECT COUNT(*) FROM tiket WHERE nomor LIKE ?", (prefix + "%",)).fetchone()[0] + 1
    return f"{prefix}{n:03d}"


@app.route("/tiket")
@login_required()
def tiket_list():
    u = current_user()
    w, a = scope_sql(u)
    cond = [w.replace(" WHERE ", "")] if w else []
    q = request.args.get("q", "").strip()
    st = request.args.get("status", "")
    if q:
        cond.append("(t.judul LIKE ? OR t.nomor LIKE ?)")
        a += [f"%{q}%", f"%{q}%"]
    if st in STATUS:
        cond.append("t.status=?")
        a.append(st)
    sql = BASE_Q + (" WHERE " + " AND ".join(cond) if cond else "") + " ORDER BY t.id DESC"
    return render_template("tiket_list.html", rows=db().execute(sql, a).fetchall(), q=q, st=st)


@app.route("/tiket/baru", methods=["GET", "POST"])
@login_required("pelapor", "admin")
def tiket_baru():
    kat = db().execute("SELECT * FROM kategori ORDER BY nama").fetchall()
    if request.method == "POST":
        judul = request.form.get("judul", "").strip()
        desk = request.form.get("deskripsi", "").strip()
        kid = request.form.get("kategori_id", type=int)
        if not judul or not desk or not kid or not any(k["id"] == kid for k in kat):
            flash("Judul, deskripsi, dan kategori wajib diisi.", "error")
            return render_template("tiket_baru.html", kat=kat, f=request.form), 400
        nomor = next_nomor()
        cur = db().execute(
            "INSERT INTO tiket(nomor,judul,deskripsi,kategori_id,pelapor_id,dibuat,diperbarui) VALUES(?,?,?,?,?,?,?)",
            (nomor, judul[:150], desk[:3000], kid, current_user()["id"], now(), now()))
        db().execute("INSERT INTO riwayat(tiket_id,pengguna_id,status,catatan,waktu) VALUES(?,?,?,?,?)",
                     (cur.lastrowid, current_user()["id"], "Menunggu", "Laporan dibuat.", now()))
        db().commit()
        flash(f"Laporan tersimpan. Nomor tiket Anda: {nomor}", "ok")
        return redirect(url_for("tiket_detail", tid=cur.lastrowid))
    return render_template("tiket_baru.html", kat=kat, f={})


def get_tiket(tid):
    t = db().execute(BASE_Q + " WHERE t.id=?", (tid,)).fetchone()
    u = current_user()
    if not t:
        abort(404)
    if (u["role"] == "pelapor" and t["pelapor_id"] != u["id"]) or \
       (u["role"] == "petugas" and t["petugas_id"] != u["id"]):
        abort(403)
    return t


@app.route("/tiket/<int:tid>")
@login_required()
def tiket_detail(tid):
    t = get_tiket(tid)
    rw = db().execute("SELECT r.*, p.nama FROM riwayat r JOIN pengguna p ON p.id=r.pengguna_id "
                      "WHERE tiket_id=? ORDER BY r.id", (tid,)).fetchall()
    petugas = db().execute("SELECT id,nama FROM pengguna WHERE role='petugas' AND aktif=1 ORDER BY nama").fetchall()
    kat = db().execute("SELECT * FROM kategori ORDER BY nama").fetchall()
    return render_template("tiket_detail.html", t=t, rw=rw, petugas=petugas, kat=kat)


@app.route("/tiket/<int:tid>/atur", methods=["POST"])
@login_required("admin")
def tiket_atur(tid):
    t = get_tiket(tid)
    pid = request.form.get("petugas_id", type=int)
    kid = request.form.get("kategori_id", type=int)
    pri = request.form.get("prioritas")
    if pri not in PRIORITAS:
        abort(400)
    if pid and not db().execute("SELECT 1 FROM pengguna WHERE id=? AND role='petugas' AND aktif=1", (pid,)).fetchone():
        abort(400)
    if kid and not db().execute("SELECT 1 FROM kategori WHERE id=?", (kid,)).fetchone():
        abort(400)
    status = t["status"]
    if pid and t["petugas_id"] != pid:
        nama = db().execute("SELECT nama FROM pengguna WHERE id=?", (pid,)).fetchone()["nama"]
        db().execute("INSERT INTO riwayat(tiket_id,pengguna_id,status,catatan,waktu) VALUES(?,?,?,?,?)",
                     (tid, current_user()["id"], status, f"Tiket ditugaskan kepada {nama}.", now()))
    db().execute("UPDATE tiket SET petugas_id=?, kategori_id=?, prioritas=?, diperbarui=? WHERE id=?",
                 (pid or None, kid or t["kategori_id"], pri, now(), tid))
    db().commit()
    flash("Pengaturan tiket disimpan.", "ok")
    return redirect(url_for("tiket_detail", tid=tid))


@app.route("/tiket/<int:tid>/status", methods=["POST"])
@login_required("petugas", "admin")
def tiket_status(tid):
    t = get_tiket(tid)
    st = request.form.get("status")
    cat = request.form.get("catatan", "").strip()
    if st not in STATUS or not cat:
        flash("Status dan catatan tindak lanjut wajib diisi.", "error")
        return redirect(url_for("tiket_detail", tid=tid))
    if t["status"] == "Selesai" and current_user()["role"] != "admin":
        flash("Tiket yang sudah selesai tidak dapat diubah.", "error")
        return redirect(url_for("tiket_detail", tid=tid))
    db().execute("UPDATE tiket SET status=?, diperbarui=? WHERE id=?", (st, now(), tid))
    db().execute("INSERT INTO riwayat(tiket_id,pengguna_id,status,catatan,waktu) VALUES(?,?,?,?,?)",
                 (tid, current_user()["id"], st, cat[:2000], now()))
    db().commit()
    flash("Status dan catatan tindak lanjut disimpan.", "ok")
    return redirect(url_for("tiket_detail", tid=tid))


# ---------- admin: akun & kategori ----------
@app.route("/admin/akun", methods=["GET", "POST"])
@login_required("admin")
def admin_akun():
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        un = request.form.get("username", "").strip()
        pw = request.form.get("password", "")
        role = request.form.get("role")
        if not nama or not un or len(pw) < 6 or role not in ROLES:
            flash("Lengkapi semua isian; kata sandi minimal 6 karakter.", "error")
        elif db().execute("SELECT 1 FROM pengguna WHERE username=?", (un,)).fetchone():
            flash("Username sudah digunakan.", "error")
        else:
            db().execute("INSERT INTO pengguna(nama,username,password_hash,role) VALUES(?,?,?,?)",
                         (nama, un, generate_password_hash(pw), role))
            db().commit()
            flash("Akun ditambahkan.", "ok")
        return redirect(url_for("admin_akun"))
    return render_template("admin_akun.html",
                           rows=db().execute("SELECT * FROM pengguna ORDER BY role, nama").fetchall())


@app.route("/admin/akun/<int:uid>/aktif", methods=["POST"])
@login_required("admin")
def admin_akun_aktif(uid):
    if uid == current_user()["id"]:
        flash("Anda tidak dapat menonaktifkan akun sendiri.", "error")
    else:
        db().execute("UPDATE pengguna SET aktif=1-aktif WHERE id=?", (uid,))
        db().commit()
        flash("Status akun diperbarui.", "ok")
    return redirect(url_for("admin_akun"))


@app.route("/admin/kategori", methods=["GET", "POST"])
@login_required("admin")
def admin_kategori():
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        if not nama:
            flash("Nama kategori wajib diisi.", "error")
        elif db().execute("SELECT 1 FROM kategori WHERE nama=?", (nama,)).fetchone():
            flash("Kategori sudah ada.", "error")
        else:
            db().execute("INSERT INTO kategori(nama) VALUES(?)", (nama,))
            db().commit()
            flash("Kategori ditambahkan.", "ok")
        return redirect(url_for("admin_kategori"))
    rows = db().execute("SELECT k.*, (SELECT COUNT(*) FROM tiket WHERE kategori_id=k.id) n "
                        "FROM kategori k ORDER BY nama").fetchall()
    return render_template("admin_kategori.html", rows=rows)


@app.route("/admin/kategori/<int:kid>/hapus", methods=["POST"])
@login_required("admin")
def admin_kategori_hapus(kid):
    if db().execute("SELECT 1 FROM tiket WHERE kategori_id=?", (kid,)).fetchone():
        flash("Kategori sudah dipakai tiket sehingga tidak dapat dihapus.", "error")
    else:
        db().execute("DELETE FROM kategori WHERE id=?", (kid,))
        db().commit()
        flash("Kategori dihapus.", "ok")
    return redirect(url_for("admin_kategori"))


# ---------- rekapitulasi ----------
@app.route("/rekap")
@login_required("admin", "petugas")
def rekap():
    u = current_user()
    cond, a = [], []
    if u["role"] == "petugas":
        cond.append("t.petugas_id=?"); a.append(u["id"])
    f = {k: request.args.get(k, "") for k in ("dari", "sampai", "kategori", "status", "petugas")}
    if f["dari"]:
        cond.append("date(t.dibuat)>=date(?)"); a.append(f["dari"])
    if f["sampai"]:
        cond.append("date(t.dibuat)<=date(?)"); a.append(f["sampai"])
    if f["kategori"].isdigit():
        cond.append("t.kategori_id=?"); a.append(int(f["kategori"]))
    if f["status"] in STATUS:
        cond.append("t.status=?"); a.append(f["status"])
    if f["petugas"].isdigit() and u["role"] == "admin":
        cond.append("t.petugas_id=?"); a.append(int(f["petugas"]))
    w = (" WHERE " + " AND ".join(cond)) if cond else ""
    rows = db().execute(BASE_Q + w + " ORDER BY t.id DESC", a).fetchall()
    per_status = db().execute("SELECT t.status k, COUNT(*) n FROM tiket t" + w + " GROUP BY t.status", a).fetchall()
    per_kat = db().execute("SELECT COALESCE(k.nama,'-') k, COUNT(*) n FROM tiket t LEFT JOIN kategori k ON k.id=t.kategori_id"
                           + w + " GROUP BY k.nama ORDER BY n DESC", a).fetchall()
    kat = db().execute("SELECT * FROM kategori ORDER BY nama").fetchall()
    petugas = db().execute("SELECT id,nama FROM pengguna WHERE role='petugas' ORDER BY nama").fetchall()
    return render_template("rekap.html", rows=rows, f=f, kat=kat, petugas=petugas,
                           per_status=per_status, per_kat=per_kat)


init_db()  # membuat tabel dan data awal bila belum ada (juga saat dijalankan oleh gunicorn)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
