"""Dentro la cattedrale: dalle due foto della chiesa ricava la navata e i due punti di ripresa.

Uso: python strumenti/build_cattedrale.py <foto_altare.jpg> <foto_cantoria.jpg> dati

Le due foto guardano la stessa navata dai due capi: la prima dal presbiterio verso la cantoria,
la seconda dalla cantoria verso l'altare. La larghezza della navata (7 m) fissa la scala.
I punti qui sotto sono stati presi a mano sulle foto (pixel su 1280 x 960): spigoli della cantoria,
della porta e del muro di fondo, punti di fuga, una persona in piedi sotto la cantoria, le panche.
Il risultato è dati/cattedrale.json: misure della navata, posa delle due macchine, panche e macerie.
Coordinate: x a destra guardando l'altare, y in alto dal pavimento della navata,
z verso la facciata, con z = 0 sulla faccia interna della facciata.
"""
import json, shutil, sys
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares

W, DL, HF = 7.0, 2.6, 67.0          # larghezza navata, profondità cantoria, campo orizzontale delle foto
F = 640 / np.tan(np.radians(HF) / 2)


def rotm(yaw, pitch, roll):
    cy, sy, cp, sp, cr, sr = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch), np.cos(roll), np.sin(roll)
    return (np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
            @ np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]]))   # come una camera three.js con ordine YXZ


def proj(cam, P, direction=False):
    c = rotm(*cam[3:6]).T @ (np.asarray(P, float) - (0 if direction else np.asarray(cam[:3])))
    return np.array([640 + F * c[0] / -c[2], 480 - F * c[1] / -c[2]])


def ray(cam, uv, axis, val):
    d = rotm(*cam[3:6]) @ np.array([(uv[0] - 640) / F, -(uv[1] - 480) / F, -1.0])
    o = np.asarray(cam[:3]); return o + (val - o[axis]) / d[axis] * d


def obs(r, cam, uv, P, w=1.0):
    r.extend(w * (proj(cam, P) - np.array(uv)))


# foto dall'altare: x y z yaw pitch roll, parapetto, trave della cantoria, porta, cornice, volta
def res_a(p):
    A = p[:6]; Hr, Hl, dw, dh, Hc, rise = p[6:]; zl, r = -DL, []
    obs(r, A, (510, 400), (W / 2, Hr, zl)); obs(r, A, (970, 400), (-W / 2, Hr, zl))
    obs(r, A, (510, 478), (W / 2, Hl, zl)); obs(r, A, (970, 478), (-W / 2, Hl, zl))
    obs(r, A, (686, 505), (dw / 2, dh, 0)); obs(r, A, (786, 505), (-dw / 2, dh, 0))
    obs(r, A, (545, 300), (W / 2, Hc, 0), 0.5); obs(r, A, (945, 300), (-W / 2, Hc, 0), 0.5)
    obs(r, A, (740, 145), (0, Hc + rise, 0), 0.5)
    r.extend(proj(A, (0, 0, 1), True) - np.array([727, 564]))          # punto di fuga della navata
    obs(r, A, (560, 683), (2.0, 0, zl + 0.3)); obs(r, A, (560, 570), (2.0, 1.7, zl + 0.3))   # persona di 1,70 m
    return np.array(r + [3000 * p[5]])


pa = least_squares(res_a, [0, 2.2, -15, np.pi + 0.1, 0.08, 0, 4.2, 3.0, 1.6, 2.6, 6.0, 3.0]).x
A, (Hr, Hl, dw, dh, Hc, rise) = list(pa[:6]), pa[6:]
B_Y, B_Z = Hl + 0.2 + 1.55, -DL + 0.45       # in piedi sulla cantoria, appoggiato al parapetto


# foto dalla cantoria: x yaw pitch roll, lunghezza della navata, zoccolo
def res_b(p):
    B = [p[0], B_Y, B_Z, *p[1:4]]; Lt, Hd = p[4:]; r = []
    obs(r, B, (440, 152), (-W / 2, Hc, -Lt)); obs(r, B, (885, 152), (W / 2, Hc, -Lt))
    obs(r, B, (440, 435), (-W / 2, Hd, -Lt)); obs(r, B, (885, 435), (W / 2, Hd, -Lt))
    return np.array(r + [400 * (p[2] - np.radians(-16.4)), 300 * p[3]])   # le verticali convergono a -16°


pb = least_squares(res_b, [0, 0, -0.28, 0, 15, 1.2]).x
B, (Lt, Hd) = [pb[0], B_Y, B_Z, *pb[1:4]], pb[4:]


def bench(cam, uv0, uv1, h):
    """Panca dagli estremi dello schienale: centro, lunghezza, angolo sul piano."""
    p0, p1 = ray(cam, uv0, 1, h), ray(cam, uv1, 1, h)
    if p1[0] < p0[0]: p0, p1 = p1, p0
    c, d = (p0 + p1) / 2, p1 - p0
    return [round(c[0], 2), round(c[2] + 0.15, 2), round(float(np.hypot(d[0], d[2])), 2), round(float(np.arctan2(d[2], d[0])), 3)]


za = -Lt
shot = lambda tex, cam, gain: {"tex": tex, "hfov": HF, "pos": [round(v, 3) for v in cam[:3]],
                               "rot": [round(v, 4) for v in cam[3:6]], "gain": gain}
out = {
    "id": 10, "slug": "cattedrale", "label": "Dentro la cattedrale", "group": "Dentro", "kind": "cattedrale",
    "nave": {"w": W, "len": round(Lt, 2), "cornice": round(Hc, 2), "volta": round(rise, 2), "zoccolo": round(Hd, 2),
             "presbiterio": [3.2, round(A[1] - 1.6, 2)],
             "cantoria": {"prof": DL, "piano": round(B_Y - 1.6, 2), "spess": 0.2, "parapetto": round(Hr, 2), "colonne": 1.1}},
    # panche: centro x, z, lunghezza, angolo; le prime due viste dall'alto, le altre solo dall'altare
    "panche": [bench(B, (350, 688), (787, 718), 0.88), bench(B, (425, 632), (757, 652), 0.88),
               bench(A, (705, 680), (858, 682), 0.88), bench(A, (645, 648), (830, 650), 0.88)],
    # cumuli di macerie sul presbiterio: centro x, z, raggio, altezza
    "macerie": [[0.1, round(za + 2.2, 2), 1.3, 0.95], [-2.2, round(za + 1.4, 2), 1.0, 0.45],
                [2.3, round(za + 1.6, 2), 1.1, 0.4], [-1.8, round(za + 4.5, 2), 0.8, 0.18]],
    "foto": [shot("c1.jpg", A, 2.3), shot("c2.jpg", B, 1.0)],
}

if __name__ == "__main__":
    fa, fb, dst = map(Path, sys.argv[1:4])
    shutil.copyfile(fa, dst / "c1.jpg"); shutil.copyfile(fb, dst / "c2.jpg")
    (dst / "cattedrale.json").write_text(json.dumps(out, indent=1))
    print(f"navata {W} x {Lt:.2f} m, cornice {Hc:.2f}, volta +{rise:.2f}; "
          f"altare: occhio a {A[1]:.2f} m, {A[2] + Lt:.2f} m dal muro; cantoria: occhio a {B_Y:.2f} m")
