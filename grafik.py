"""Pembuat grafik SVG sederhana (tanpa pustaka luar) untuk halaman rekapitulasi."""
import math
from datetime import date, timedelta
from markupsafe import Markup, escape

WARNA_STATUS = {"Menunggu": "#F59E0B", "Diproses": "#3B82F6", "Selesai": "#16A34A"}
WARNA_PRIORITAS = {"Rendah": "#98A2B3", "Sedang": "#F59E0B", "Tinggi": "#DC2626"}
PALET = ["#4F46E5", "#0EA5E9", "#14B8A6", "#F59E0B", "#EC4899", "#8B5CF6", "#64748B"]


def potongan(data, warna):
    """data: [(label, n)] -> [{label, n, persen, warna}] dengan nol tetap dicantumkan."""
    total = sum(n for _, n in data) or 0
    out = []
    for i, (lab, n) in enumerate(data):
        out.append({"label": lab, "n": n, "persen": round(n * 100 / total) if total else 0,
                    "warna": warna.get(lab) if isinstance(warna, dict) else warna[i % len(warna)]})
    return out


def donat(items, tengah="tiket"):
    total = sum(i["n"] for i in items)
    r, c = 70, 2 * math.pi * 70
    s = ['<svg viewBox="0 0 200 200" role="img" aria-label="Diagram donat">',
         '<circle cx="100" cy="100" r="70" fill="none" stroke="#EEF0F6" stroke-width="28"/>']
    cum = 0
    if total:
        for i in items:
            if not i["n"]:
                continue
            ln = c * i["n"] / total
            s.append(f'<circle cx="100" cy="100" r="70" fill="none" stroke="{i["warna"]}" stroke-width="28" '
                     f'stroke-dasharray="{ln:.2f} {c - ln:.2f}" stroke-dashoffset="{-cum:.2f}" transform="rotate(-90 100 100)"/>')
            cum += ln
    s.append(f'<text x="100" y="104" text-anchor="middle" font-size="34" font-weight="800" fill="#1F2437">{total}</text>')
    s.append(f'<text x="100" y="126" text-anchor="middle" font-size="13" fill="#667085">{escape(tengah)}</text></svg>')
    return Markup("".join(s))


def tren(per_hari, akhir=None, hari=14):
    """per_hari: {'YYYY-MM-DD': n}. Grafik kolom untuk `hari` hari terakhir sampai `akhir`."""
    akhir = akhir or date.today()
    ds = [akhir - timedelta(days=hari - 1 - i) for i in range(hari)]
    vals = [per_hari.get(d.isoformat(), 0) for d in ds]
    mx = max(vals + [1]); top = 4 if mx <= 4 else int(math.ceil(mx / 4) * 4)
    W, H, L, B, T = 640, 250, 36, 34, 14
    pw, ph = W - L - 8, H - B - T
    bw = pw / hari
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Grafik jumlah laporan per hari">']
    for k in range(5):
        v = top * k / 4; y = T + ph - ph * v / top
        s.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W - 8}" y2="{y:.1f}" stroke="#EEF0F6"/>'
                 f'<text x="{L - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="#98A2B3">{v:g}</text>')
    for i, (d, v) in enumerate(zip(ds, vals)):
        h = ph * v / top; x = L + i * bw + bw * 0.18; w = bw * 0.64; y = T + ph - h
        if v:
            s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="5" fill="#6366F1"/>'
                     f'<text x="{x + w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="#3730A3">{v}</text>')
        else:
            s.append(f'<rect x="{x:.1f}" y="{T + ph - 3}" width="{w:.1f}" height="3" rx="1.5" fill="#E5E7EF"/>')
        if i % 2 == 0 or hari <= 8:
            s.append(f'<text x="{x + w / 2:.1f}" y="{H - 12}" text-anchor="middle" font-size="11" fill="#667085">{d.day:02d}/{d.month:02d}</text>')
    s.append('</svg>')
    return Markup("".join(s))


def format_durasi(menit):
    if menit is None:
        return "-"
    menit = int(round(menit))
    if menit < 60:
        return f"{menit} menit"
    jam = menit / 60
    if jam < 24:
        return f"{jam:.1f} jam".replace(".0", "")
    return f"{jam / 24:.1f} hari".replace(".0", "")
