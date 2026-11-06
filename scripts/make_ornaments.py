#!/usr/bin/env python3
"""
Draws TestDay's logo and ornament as SVG, from geometry, so nothing is traced from anyone's artwork.

    python scripts/make_ornaments.py                      # writes the files below and updates the mark in index.html
    python scripts/make_ornaments.py --preview sheet.html # also writes a contact sheet to look at them

The ornament follows the tradition of Central Asian textile and tile borders:

  islimi  a scrolling vine: a wave with a curl at each crest and trough, and leaves where it crosses the middle
  girih   the eight-point star of tile work, with a smaller star cut into it, joined by lozenges
  key     the key meander, a stepped line that runs on and on
  arches  a row of pointed (ogee) arches, the silhouette of a gate or a wall top

The logo mark is the sun-medallion of Uzbek embroidery (suzani): four long almond petals, four short ones, a ring
and a dot. It is also the filled bubble of an answer sheet. The four long petals stand for the four papers
(Listening, Reading, Writing, Speaking), which is why the home page lights one when you point at its row.

Writes
  public/img/orn/*.svg        the bands, one tile each, drawn in black: the site uses them as CSS masks, so one file
                              is any colour (public/css/portal.css, "Ornament")
  public/img/logo-mark*.svg   the mark alone, navy and gold
  public/favicon.svg          the mark in gold on a navy tile, simplified so it reads at 16 px
  public/index.html           the mark's <symbol> between the "td-mark" comments (the page draws every copy of the mark
                              from it with <use>, recoloured by CSS variables)
The PNG icons and the share image are drawn from these by scripts/make_og_image.js.
"""

import argparse
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORN = os.path.join(ROOT, "public", "img", "orn")
IMG = os.path.join(ROOT, "public", "img")
INDEX = os.path.join(ROOT, "public", "index.html")

NAVY, STONE, GOLD = "#0f1a30", "#e9e8e2", "#e0a93b"


# ---------------------------------------------------------------------------------------- geometry
def f(x, places=1):
    s = f"{x:.{places}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def smooth_path(points):
    """A closed smooth outline through the midpoints of a polygon (quadratic curves)."""
    n = len(points)
    mids = [((points[i][0] + points[(i + 1) % n][0]) / 2, (points[i][1] + points[(i + 1) % n][1]) / 2) for i in range(n)]
    d = f"M{f(mids[-1][0])},{f(mids[-1][1])}"
    for i in range(n):
        d += f"Q{f(points[i][0])},{f(points[i][1])} {f(mids[i][0])},{f(mids[i][1])}"
    return d + "Z"


def ribbon(center, widths):
    """The outline of a stroke of varying width along a centre line (a list of points), as a polygon."""
    n = len(center)
    left, right = [], []
    for i, (x, y) in enumerate(center):
        x0, y0 = center[max(i - 1, 0)]
        x1, y1 = center[min(i + 1, n - 1)]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length, dx / length
        w = widths[i] / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return left + right[::-1]


def lerp(a, b, t):
    return a + (b - a) * t


def spiral(cx, cy, r0, r1, theta0, turns, n, direction):
    """Points of a spiral about (cx, cy) from radius r0 to r1 (angles in degrees, screen space, y down)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        r = r0 * (r1 / r0) ** t
        th = math.radians(theta0) + direction * 2 * math.pi * turns * t
        pts.append((cx + r * math.cos(th), cy + r * math.sin(th)))
    return pts


def leaf(x0, y0, ang, length, width, n=10):
    """A pointed leaf growing from (x0, y0) in direction `ang` degrees."""
    a = math.radians(ang)
    pts, ws = [], []
    for i in range(n + 1):
        t = i / n
        pts.append((x0 + length * t * math.cos(a), y0 + length * t * math.sin(a)))
        ws.append(width * (math.sin(math.pi * min(1, t * 0.96 + 0.02)) ** 0.85))
    return ribbon(pts, ws)


def poly_path(points):
    return "M" + "L".join(f"{f(x)},{f(y)}" for x, y in points) + "Z"


def tile_svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" width="{f(w)}" height="{f(h)}">'
            f'{body.replace("FILL", "#000")}</svg>\n')


# ---------------------------------------------------------------------------------------- the mark
LONG_B, LONG_W = 0.31, 0.215       # long petals: start radius, half width (the unit is the tip radius)
SHORT_B, SHORT_L, SHORT_W = 0.35, 0.84, 0.12
RING_R, RING_W, DOT_R = 0.215, 0.055, 0.08
BOX = 1.12                         # the mark is drawn in a -BOX..BOX square; the long tips reach 1.0


def petal(b=0.31, L=1.0, w=0.2, tip=0.12, base=0.22):
    """An almond petal pointing up from radius b to L, symmetrical about its axis, with smooth joins."""
    h = L - b
    p = lambda x, y: f"{x:.3f},{y:.3f}"
    s1 = ((base * w, -(b + 0.02 * h)), (w, -(b + 0.22 * h)), (w, -(b + 0.50 * h)))
    s2 = ((w, -(b + 0.80 * h)), (tip * w, -(b + 0.88 * h)), (0.0, -L))
    d = f"M0,{-b:.3f} C{p(*s1[0])} {p(*s1[1])} {p(*s1[2])} C{p(*s2[0])} {p(*s2[1])} {p(*s2[2])} "
    d += f"C{p(-tip * w, s2[1][1])} {p(-w, s2[0][1])} {p(-w, s1[2][1])} C{p(-w, s1[1][1])} {p(-base * w, s1[0][1])} 0,{-b:.3f}Z"
    return d


def long_petal(w=LONG_W, inlaid=True):
    """A long petal with a small almond cut out of it (drawn with fill-rule evenodd)."""
    h = 1.0 - LONG_B
    d = petal(b=LONG_B, L=1.0, w=w)
    if inlaid:
        d += petal(b=LONG_B + 0.16 * h, L=1.0 - 0.2 * h, w=w * 0.42, tip=0.15)
    return d


def short_petal(w=SHORT_W):
    return petal(b=SHORT_B, L=SHORT_L, w=w)


def mark_body(fill, inlaid=True, heavy=False):
    """The mark in a -BOX..BOX square, in one colour."""
    lw, sw = (0.24, 0.14) if heavy else (LONG_W, SHORT_W)
    out = []
    for a in range(0, 360, 90):
        out.append(f'<path transform="rotate({a})" fill="{fill}" fill-rule="evenodd" d="{long_petal(lw, inlaid)}"/>')
    for a in range(45, 360, 90):
        out.append(f'<path transform="rotate({a})" fill="{fill}" d="{short_petal(sw)}"/>')
    rw, dr = (0.07, 0.085) if heavy else (RING_W, DOT_R)
    out.append(f'<circle r="{RING_R}" fill="none" stroke="{fill}" stroke-width="{rw}"/><circle r="{dr}" fill="{fill}"/>')
    return "".join(out)


def mark_svg(fill, size=64):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-BOX} {-BOX} {BOX * 2} {BOX * 2}" width="{size}" height="{size}">'
            f'{mark_body(fill)}</svg>\n')


def mark_symbol():
    """The mark as a <symbol>, coloured by CSS variables (see "The mark" in portal.css)."""
    parts = []
    for name, a in zip("abcd", range(0, 360, 90)):
        parts.append(f'<path class="pl pl-{name}" fill-rule="evenodd" transform="rotate({a})" d="{long_petal()}"/>')
    for a in range(45, 360, 90):
        parts.append(f'<path class="pl pl-s" transform="rotate({a})" d="{short_petal()}"/>')
    parts.append(f'<circle class="rg" r="{RING_R}"/><circle class="dt" r="{DOT_R}"/>')
    return f'<symbol id="td-mark" viewBox="{-BOX} {-BOX} {BOX * 2} {BOX * 2}">{"".join(parts)}</symbol>'


def favicon_svg():
    """A rounded navy tile with the gold mark, heavier and without the inlays so it reads at 16 px."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1.3 -1.3 2.6 2.6" width="64" height="64">'
            f'<rect x="-1.3" y="-1.3" width="2.6" height="2.6" rx="0.52" fill="{NAVY}"/>'
            f'<g transform="scale(0.96)">{mark_body(GOLD, inlaid=False, heavy=True)}</g></svg>\n')


# ---------------------------------------------------------------------------------------- the bands
def islimi(P=104.0, H=92.0, A=8.0, stem_w=4.0, R=17.0, leaf_len=22.0, leaf_w=10.0):
    """A scrolling vine: a wave with a curl at each crest and trough and leaves where it crosses the middle."""
    yM = H / 2
    step = 4.0
    xs = [-12 + i * step for i in range(int((P + 24) / step) + 1)]
    stem = [(x, yM - A * math.sin(2 * math.pi * x / P)) for x in xs]

    def curl(xc, up):
        yc = yM - A if up else yM + A
        cy = yc - R if up else yc + R
        pts = spiral(xc, cy, R, 3.4, 90 if up else -90, 2.0, 30, direction=-1 if up else 1)
        ws = [lerp(stem_w * 1.2, 1.1, (i / (len(pts) - 1)) ** 0.85) for i in range(len(pts))]
        return ribbon(pts, ws)

    shapes = [ribbon(stem, [stem_w] * len(stem)), curl(P / 4, True), curl(3 * P / 4, False)]
    for x0, sgn in ((0.0, 1), (P / 2, -1)):
        pair = [leaf(x0, yM, -sgn * 52, leaf_len, leaf_w), leaf(x0, yM, sgn * 128, leaf_len * 0.8, leaf_w * 0.8)]
        shapes += pair
        if x0 == 0.0:
            # These leaves grow past the tile's edge: draw them again one tile over so the part that spills
            # over arrives on the other edge and the repeat has no join.
            shapes += [[(x + dx, y) for x, y in pts] for pts in pair for dx in (-P, P)]
    return P, H, f'<path fill="FILL" d="{"".join(smooth_path(s) for s in shapes)}"/>'


def star_points(cx, cy, R, rot=0.0, inner=0.7654):
    pts = []
    for k in range(16):
        ang = math.radians(-90 + rot + k * 22.5)
        rad = R if k % 2 == 0 else R * inner
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def girih_row(W=56.0, H=44.0):
    """A row of eight-point stars of tile work, each with a smaller star cut into it, joined by lozenges."""
    cx, cy = W / 2, H / 2
    star = poly_path(star_points(cx, cy, 19.5))
    hole = poly_path(star_points(cx, cy, 10.0, rot=22.5))
    dot = f'<circle cx="{f(cx)}" cy="{f(cy)}" r="3"/>'
    loz = "".join(f'<path d="M{f(x)},{f(cy - 7)}L{f(x + 4)},{f(cy)}L{f(x)},{f(cy + 7)}L{f(x - 4)},{f(cy)}Z"/>' for x in (0.0, W))
    return W, H, f'<path fill="FILL" fill-rule="evenodd" d="{star}{hole}"/><g fill="FILL">{dot}{loz}</g>'


def key_row(W=48.0, H=30.0, sw=3.4):
    """A key meander (a stepped line that runs on and on)."""
    d = f"M-4,{H - 4} H4 V4 H{W - 4} V{H - 12} H14 V12 H{W - 14} V{H - 4} H{W + 4}"
    return W, H, f'<path d="{d}" fill="none" stroke="FILL" stroke-width="{sw}" stroke-linejoin="miter" stroke-linecap="butt"/>'


def arches_row(W=36.0, H=16.0):
    """A row of pointed (ogee) arches along the top, solid below: the silhouette of a gate or a wall top."""
    d = (f"M0,{H} L0,{H - 3} C0,{H - 7.8} 9,{H - 8.6} 12.2,{H - 12} C14.6,{H - 14.5} 16.6,{H - 15.4} {W / 2},{H - 16} "
         f"C{W - 16.6},{H - 15.4} {W - 14.6},{H - 14.5} {W - 12.2},{H - 12} C{W - 9},{H - 8.6} {W},{H - 7.8} {W},{H - 3} L{W},{H}Z")
    return W, H, f'<path fill="FILL" d="{d}"/>'


BANDS = {"islimi": islimi, "girih": girih_row, "key": key_row, "arches": arches_row}


# ---------------------------------------------------------------------------------------- writing
def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


SPRITE_RE = re.compile(r"(<!-- td-mark:start[^>]*-->\n)(.*?)(\s*<!-- td-mark:end -->)", re.S)


def sprite_block():
    return ('  <svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">'
            f'{mark_symbol()}</svg>')


def update_index():
    """Put the current mark into index.html (between the td-mark comments). Returns False if it was already current."""
    with open(INDEX, encoding="utf-8") as fh:
        page = fh.read()
    if not SPRITE_RE.search(page):
        raise SystemExit("public/index.html has no <!-- td-mark:start --> ... <!-- td-mark:end --> block to update")
    updated = SPRITE_RE.sub(lambda m: m.group(1) + sprite_block() + "\n  <!-- td-mark:end -->", page)
    if updated == page:
        return False
    write(INDEX, updated)
    return True


def contact_sheet(tiles):
    rows = []
    for name, (w, h, body) in tiles.items():
        gold, navy = body.replace("FILL", GOLD), body.replace("FILL", NAVY)
        count = int(900 / w) + 2
        reps = lambda b: "".join(f'<g transform="translate({k * w},0)">{b}</g>' for k in range(count))
        rows.append(f'<div style="background:{NAVY};margin:14px 0"><svg xmlns="http://www.w3.org/2000/svg" width="900" height="{f(h)}" viewBox="0 0 900 {f(h)}">{reps(gold)}</svg></div>'
                    f'<div style="background:{STONE};margin:14px 0"><svg xmlns="http://www.w3.org/2000/svg" width="900" height="{f(h * 0.45)}" viewBox="0 0 900 {f(h)}">{reps(navy)}</svg></div>')
    sizes = (160, 96, 48, 32, 24)
    marks = "".join(mark_svg(NAVY, s).replace("<svg ", '<svg style="margin-right:22px" ', 1) for s in sizes)
    icons = "".join(favicon_svg().replace('width="64" height="64"', f'width="{s}" height="{s}" style="margin-right:22px"') for s in (96, 48, 32, 16))
    return (f'<!doctype html><body style="margin:20px;background:#888;width:900px">{"".join(rows)}'
            f'<div style="background:{STONE};padding:20px;display:flex;align-items:end">{marks}</div>'
            f'<div style="background:{STONE};padding:20px;display:flex;align-items:end">{icons}</div></body>')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="also write a contact sheet (an HTML file) to look at the result")
    args = parser.parse_args()
    tiles = {}
    for name, fn in BANDS.items():
        w, h, body = fn()
        tiles[name] = (w, h, body)
        write(os.path.join(ORN, f"{name}.svg"), tile_svg(w, h, body))
    write(os.path.join(IMG, "logo-mark.svg"), mark_svg(NAVY))
    write(os.path.join(IMG, "logo-mark-gold.svg"), mark_svg(GOLD))
    write(os.path.join(ROOT, "public", "favicon.svg"), favicon_svg())
    changed = update_index()
    if args.preview:
        write(args.preview, contact_sheet(tiles))
    sizes = ", ".join(f"{n} {os.path.getsize(os.path.join(ORN, n + '.svg'))} B" for n in BANDS)
    print(f"wrote {sizes}; index.html mark {'updated' if changed else 'already current'}")


if __name__ == "__main__":
    sys.exit(main())
