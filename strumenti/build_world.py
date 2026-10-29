"""Pipeline: foto -> mondo 2.5D esplorabile ("Dentro Faraona").

Per ogni foto:
  1. stima della profondità relativa (Depth Anything ViT-S, ONNX)
  2. riconoscimento del cielo e conversione in profondità metrica approssimata
  3. orientamento: pavimento (RANSAC) oppure fuga delle verticali, oppure inclinazione nota
  4. griglia di calpestabilità e punto del varco verso la stanza successiva
  5. esporta texture JPEG, profondità 16 bit (PNG, canale blu = cielo) e world.json

Uso: python3 build_world.py <cartella_foto> <cartella_output> <modello.onnx>
"""
import json, math, sys, base64
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

EYE = 1.6
TEX_MAX = 2048
DEPTH_W = 256
CELL = 0.1
SKY_M = 38.0

# percorso: fuori -> dentro. pitch = inclinazione nota della macchina (gradi, + verso l'alto),
# usata se pavimento e verticali non bastano; med = profondità mediana tipica (m) senza pavimento
ROUTE = [
    dict(file="arco.jpg", label="L'arco", group="Fuori", pitch=0, med=7.0),
    dict(file="fontana.jpg", label="La fontana", group="Fuori", pitch=-8, med=2.4),
    dict(file="inferriata.jpg", label="L'inferriata", group="Fuori", pitch=28, med=3.2),
    dict(file="muro.jpg", label="Il muro scritto", group="Fuori", pitch=38, med=4.5),
    dict(file="senzatetto.jpg", label="Senza tetto", group="Fuori", pitch=82, med=5.0),
    dict(file="cappella.jpg", label="La cappella", group="Dentro", pitch=12, med=4.5,
         doc=dict(file="foglio.jpg", label="Il foglio")),
    dict(file="carrozzina.jpg", label="La carrozzina", group="Dentro", pitch=-30, med=3.0),
    dict(file="televisore.jpg", label="Il televisore", group="Dentro", pitch=-12, med=2.2),
    dict(file="brande.jpg", label="Le brande", group="Dentro", pitch=-22, med=3.0),
]


def hfov_default(w, h, f35=27.0):
    diag = 2 * math.atan(43.27 / (2 * f35))
    fpx = (math.hypot(w, h) / 2) / math.tan(diag / 2)
    return math.degrees(2 * math.atan((w / 2) / fpx))


def run_depth(sess, rgb):
    h, w = rgb.shape[:2]
    s = 518 / max(h, w)
    nh, nw = max(14, round(h * s / 14) * 14), max(14, round(w * s / 14) * 14)
    x = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    disp = np.squeeze(sess.run(None, {sess.get_inputs()[0].name: x})[0]).astype(np.float32)
    return cv2.resize(disp, (w, h), interpolation=cv2.INTER_CUBIC)


def unproject(depth, fx, cx, cy):
    h, w = depth.shape
    u, v = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    return np.stack([(u - cx) / fx * depth, -(v - cy) / fx * depth, -depth], -1)


def disp_to_depth(d, k):
    return (1.0 / (1 / k + d * (1 - 1 / k))).astype(np.float32)


def ransac_floor(pts, iters=500, thr=0.04, seed=7):
    rng = np.random.default_rng(seed)
    best, best_n, n = None, 0, len(pts)
    if n < 60:
        return None
    for _ in range(iters):
        a, b, c = pts[rng.choice(n, 3, replace=False)]
        nrm = np.cross(b - a, c - a)
        L = np.linalg.norm(nrm)
        if L < 1e-9:
            continue
        nrm /= L
        if nrm[1] < 0:
            nrm = -nrm
        if nrm[1] < 0.5:
            continue
        inl = np.abs((pts - a) @ nrm) < thr
        if inl.sum() > best_n:
            best_n, best = inl.sum(), inl
    if best is None or best_n < 0.15 * n:
        return None
    P = pts[best]
    c = P.mean(0)
    nrm = np.linalg.svd(P - c)[2][-1]
    if nrm[1] < 0:
        nrm = -nrm
    return nrm, c, best_n / n


def normals(P, step=3):
    Q = P[::step, ::step]
    n = np.cross(np.gradient(Q, axis=1), np.gradient(Q, axis=0))
    return (n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)).reshape(-1, 3)


def vertical_vp(gray, fx, cx, cy, scale):
    """Direzione 'su' in coordinate camera dalla fuga delle linee quasi verticali."""
    lsd = cv2.createLineSegmentDetector()
    segs = lsd.detect(gray)[0]
    if segs is None:
        return None, 0
    segs = segs.reshape(-1, 4) * scale
    H = gray.shape[0] * scale
    N, W = [], []
    for x1, y1, x2, y2 in segs:
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 0.05 * H:
            continue
        ang = abs(math.degrees(math.atan2(x2 - x1, y2 - y1)))
        ang = min(ang, 180 - ang)
        if ang > 28:
            continue
        r1 = np.array([(x1 - cx) / fx, -(y1 - cy) / fx, -1.0])
        r2 = np.array([(x2 - cx) / fx, -(y2 - cy) / fx, -1.0])
        n = np.cross(r1, r2)
        N.append(n / np.linalg.norm(n)); W.append(L)
    if len(N) < 6:
        return None, len(N)
    N, W = np.array(N), np.array(W)
    rng = np.random.default_rng(3)
    best, best_s = None, -1
    for _ in range(400):
        i, j = rng.choice(len(N), 2, replace=False)
        v = np.cross(N[i], N[j])
        if np.linalg.norm(v) < 1e-6:
            continue
        v /= np.linalg.norm(v)
        inl = np.abs(N @ v) < 0.03
        s = W[inl].sum()
        if s > best_s:
            best_s, best = s, inl
    A = (N[best] * W[best, None]).T @ N[best]
    v = np.linalg.eigh(A)[1][:, 0]
    if v[1] < 0:
        v = -v
    return v, int(best.sum())


def rot_to_up(nrm):
    up = np.array([0, 1.0, 0])
    nrm = nrm / np.linalg.norm(nrm)
    v, c = np.cross(nrm, up), nrm @ up
    s = np.linalg.norm(v)
    if s < 1e-8:
        return np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)


def pitch_of(up_c):
    return math.degrees(math.asin(np.clip(-up_c[2], -1, 1)))


def build_scene(sess, cfg, src: Path, outdir: Path, idx: int, log):
    path = src / cfg["file"]
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    W0, H0 = img.size
    hfov = hfov_default(W0, H0, 26.0 if W0 * 4 == H0 * 3 else 27.0)

    s = min(1.0, TEX_MAX / max(W0, H0))
    tex = img.resize((round(W0 * s), round(H0 * s)), Image.LANCZOS)
    tex_name = f"s{idx}.jpg"
    tex.save(outdir / tex_name, quality=80, optimize=True, progressive=True)

    ws = 1024 / max(W0, H0)
    work = np.asarray(img.resize((round(W0 * ws), round(H0 * ws)), Image.LANCZOS))
    disp_full = run_depth(sess, work)
    dh = round(DEPTH_W * work.shape[0] / work.shape[1])
    disp = cv2.resize(disp_full, (DEPTH_W, dh), interpolation=cv2.INTER_AREA)

    # cielo: disparità quasi nulla rispetto al resto
    hi = np.percentile(disp, 99.5)
    sky = disp < 0.045 * hi
    sky = cv2.morphologyEx(sky.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    solid = ~sky
    lo = np.percentile(disp[solid], 1) if solid.sum() > 100 else np.percentile(disp, 1)
    d = np.clip((disp - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)
    d = cv2.bilateralFilter(d, 5, 0.08, 3)

    fx = (DEPTH_W / 2) / math.tan(math.radians(hfov) / 2)
    cx, cy = DEPTH_W / 2, dh / 2

    # scelta del rapporto lontano/vicino: superfici o orizzontali o verticali
    best = (None, -1, None)
    rows = slice(int(dh * 0.6), None)
    rng = np.random.default_rng(2)
    c12, s12 = math.cos(math.radians(12)), math.sin(math.radians(12))
    for k in np.geomspace(2.0, 30, 20):
        P = unproject(disp_to_depth(d, k), fx, cx, cy)
        band = P[rows][solid[rows]].reshape(-1, 3)
        if len(band) < 200:
            break
        band = band[rng.choice(len(band), min(4000, len(band)), replace=False)]
        fl = ransac_floor(band, iters=250, thr=0.02 * float(np.median(-band[:, 2])))
        if fl is None:
            continue
        a = np.abs(normals(P)[solid[::3, ::3].reshape(-1)] @ fl[0])
        score = float(np.mean((a > c12) | (a < s12))) * (0.5 + 0.5 * fl[2])
        if score > best[1]:
            best = (k, score, fl)
    k, kscore, fl = best

    # orientamento
    gray = cv2.cvtColor(work, cv2.COLOR_RGB2GRAY)
    up_vp, nvp = vertical_vp(gray, fx * work.shape[1] / DEPTH_W, cx * work.shape[1] / DEPTH_W,
                             cy * work.shape[1] / DEPTH_W, 1.0)
    # le coordinate LSD sono in pixel del lavoro: riporta fx/cx/cy alla stessa scala
    pitch_cfg = cfg.get("pitch", 0)
    has_floor = fl is not None and kscore > 0.42
    vp_ok = up_vp is not None and nvp >= 12 and abs(pitch_of(up_vp) - pitch_cfg) < 25
    if vp_ok:
        method, up = "verticali", up_vp
    elif has_floor and abs(pitch_of(fl[0]) - pitch_cfg) < 25:
        method, up = "pavimento", fl[0]
    else:
        method = "inclinazione nota"
        t = math.radians(pitch_cfg)
        up = np.array([0, math.cos(t), -math.sin(t)])
    if not has_floor:
        k = 8.0 if cfg["group"] == "Dentro" else 10.0

    depth = disp_to_depth(d, k)
    P = unproject(depth, fx, cx, cy)
    R = rot_to_up(up)
    Pr = P.reshape(-1, 3) @ R.T

    if has_floor:
        # distanza camera-pavimento misurata lungo la verticale scelta
        cam_h = abs(fl[1] @ fl[0]) / max(abs(up @ fl[0]), 0.5)
    else:
        # altezza della camera: cerca un pavimento dopo la rotazione, altrimenti usa la profondità tipica
        ys = Pr[solid.reshape(-1), 1]
        cam_h = None
        low = ys[ys < np.percentile(ys, 12)]
        if len(low) > 200 and np.std(low) < 0.08 * np.median(depth[solid]) and pitch_cfg < 5:
            cam_h = -float(np.median(low))
        if not cam_h or cam_h <= 0:
            cam_h = None
    if cam_h:
        scale = EYE / cam_h
    else:
        scale = cfg.get("med", 3.5) / float(np.median(depth[solid]))
    Pw = Pr * scale
    Pw[:, 1] += EYE
    Pw = Pw.reshape(dh, DEPTH_W, 3)

    # profondità metrica in mm + cielo nel canale blu
    dm = np.clip(depth * scale * 1000, 1, 65000).astype(np.uint16)
    dm[sky] = int(SKY_M * 1000)
    rgb = np.zeros((dh, DEPTH_W, 3), np.uint8)
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = dm >> 8, dm & 255, np.where(sky, 255, 0)
    depth_name = f"s{idx}_d.png"
    Image.fromarray(rgb).save(outdir / depth_name, optimize=True)

    # griglia calpestabile
    flat = Pw[solid].reshape(-1, 3)
    xs, ys, zs = flat[:, 0], flat[:, 1], flat[:, 2]
    nw_ = np.cross(np.gradient(Pw, axis=1), np.gradient(Pw, axis=0))
    nw_ = nw_ / np.maximum(np.linalg.norm(nw_, axis=-1, keepdims=True), 1e-9)
    ny = np.abs(nw_[..., 1])[solid].reshape(-1)        # superfici quasi orizzontali = pavimento, anche se in pendenza
    x0, x1 = np.percentile(xs, 1) - 0.6, np.percentile(xs, 99) + 0.6
    z0, z1 = np.percentile(zs, 1) - 0.6, 1.6
    x0, x1 = min(x0, -1.5), max(x1, 1.5)
    z0 = min(z0, -1.5)
    gw, gh = int((x1 - x0) / CELL) + 1, int((z1 - z0) / CELL) + 1
    gi, gj = ((xs - x0) / CELL).astype(int), ((zs - z0) / CELL).astype(int)
    ok = (gi >= 0) & (gi < gw) & (gj >= 0) & (gj < gh)
    floorc = np.zeros((gh, gw), np.int32); obst = np.zeros((gh, gw), np.int32)
    fm, om = ok & (np.abs(ys) < 0.22), ok & (ys > 0.32) & (ys < 1.9) & (ny < 0.6)
    np.add.at(floorc, (gj[fm], gi[fm]), 1); np.add.at(obst, (gj[om], gi[om]), 1)
    floor_m = cv2.morphologyEx((floorc > 0).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    obst_m = cv2.dilate((obst > 2).astype(np.uint8), np.ones((3, 3), np.uint8))

    # spazio visto vuoto: lungo ogni raggio, prima di colpire la superficie, all'altezza del corpo non c'è nulla
    cam = np.array([0, EYE, 0])
    Ps = Pw[::2, ::2][solid[::2, ::2]].reshape(-1, 3)
    freec = np.zeros((gh, gw), np.int32)
    for t in np.linspace(0.04, 0.93, 36):
        q = cam + t * (Ps - cam)
        m = (q[:, 1] > 0.3) & (q[:, 1] < 1.9)
        qi, qj = ((q[m, 0] - x0) / CELL).astype(int), ((q[m, 2] - z0) / CELL).astype(int)
        kk = (qi >= 0) & (qi < gw) & (qj >= 0) & (qj < gh)
        np.add.at(freec, (qj[kk], qi[kk]), 1)
    free_m = cv2.morphologyEx((freec > 1).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    # zona sotto lo sguardo (la foto non la vede ma ci stai sopra): un piccolo ventaglio davanti ai piedi
    yaw_fwd = np.array([(R @ np.array([0, 0, -1.0]))[0], (R @ np.array([0, 0, -1.0]))[2]])
    if np.linalg.norm(yaw_fwd) < 1e-3:
        yaw_fwd = np.array([0, -1.0])
    yaw_fwd /= np.linalg.norm(yaw_fwd)
    ii, jj = np.meshgrid(np.arange(gw), np.arange(gh))
    X, Z = x0 + (ii + .5) * CELL, z0 + (jj + .5) * CELL
    along = X * yaw_fwd[0] + Z * yaw_fwd[1]
    across = np.abs(-X * yaw_fwd[1] + Z * yaw_fwd[0])
    # il ventaglio cieco arriva fin dove la foto comincia a vedere il pavimento
    bot = R @ np.array([0, -(dh - cy) / fx, -1.0])
    hz = math.hypot(bot[0], bot[2])
    reach = min(4.0, EYE * hz / -bot[1] + 0.3) if bot[1] < -0.05 else 2.2
    blind = ((along > -0.9) & (along < reach) & (across < 0.6 + np.maximum(along, 0) * 0.5)).astype(np.uint8)
    walk = ((free_m | floor_m | blind) & (1 - obst_m)).astype(np.uint8)
    sj, si = int((0 - z0) / CELL), int((0 - x0) / CELL)
    walk[max(sj - 2, 0):sj + 3, max(si - 2, 0):si + 3] = 1          # il punto di partenza è sempre libero
    n, lab = cv2.connectedComponents(walk, connectivity=4)
    walk = (lab == lab[sj, si]).astype(np.uint8)

    # varco: cella calpestabile più lontana in avanti
    cand = np.argwhere(walk > 0)
    if len(cand):
        cxw, czw = x0 + (cand[:, 1] + .5) * CELL, z0 + (cand[:, 0] + .5) * CELL
        fwd = cxw * yaw_fwd[0] + czw * yaw_fwd[1]
        # tieni la cella lontana ma non incollata ai bordi: erodi prima
        er = cv2.erode(walk, np.ones((5, 5), np.uint8))
        good = er[cand[:, 0], cand[:, 1]] > 0
        pick = np.argmax(np.where(good, fwd, fwd - 100))
        portal = [round(float(cxw[pick]), 2), round(float(czw[pick]), 2)]
    else:
        portal = [0, -1]

    scene = dict(id=idx, slug=Path(cfg["file"]).stem, label=cfg["label"], group=cfg["group"],
                 tex=tex_name, depth=depth_name, dw=DEPTH_W, dh=dh, hfov=round(hfov, 3),
                 R=np.round(R, 6).tolist(), yoff=EYE, portal=portal,
                 grid=dict(x0=round(float(x0), 3), z0=round(float(z0), 3), cell=CELL, w=gw, h=gh,
                           bits=base64.b64encode(np.packbits(walk.reshape(-1)).tobytes()).decode()))
    if "doc" in cfg:
        dimg = ImageOps.exif_transpose(Image.open(src / cfg["doc"]["file"])).convert("RGB")
        dimg.save(outdir / f"s{idx}_doc.jpg", quality=84, optimize=True, progressive=True)
        scene["doc"] = dict(tex=f"s{idx}_doc.jpg", label=cfg["doc"]["label"], w=dimg.width, h=dimg.height)
    log.append(f"{idx} {cfg['label']:<18} metodo={method:<28} k={k:.1f} ({kscore:.2f}) pitch={pitch_of(up):+.0f}° "
               f"(atteso {pitch_cfg:+d}) vp={nvp} cielo={sky.mean():.0%} scala={scale:.2f} calpestabile={walk.sum()*CELL*CELL:.1f}m² varco={portal}")

    # diagnostica
    dv = np.clip((depth * scale) / np.percentile(depth[solid] * scale, 98), 0, 1)
    vis = cv2.applyColorMap((dv * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    vis[sky] = (120, 60, 0)
    diag = outdir.parent / "diag"
    diag.mkdir(exist_ok=True)
    cv2.imwrite(str(diag / f"s{idx}_depth.png"), vis)
    g = np.dstack([walk * 200, (floor_m | free_m) * 110, obst_m * 255]).astype(np.uint8)
    cv2.circle(g, (si, sj), 2, (255, 255, 255), -1)
    pi_, pj_ = int((portal[0] - x0) / CELL), int((portal[1] - z0) / CELL)
    cv2.circle(g, (pi_, pj_), 2, (0, 200, 255), -1)
    cv2.imwrite(str(diag / f"s{idx}_grid.png"), cv2.resize(g, (gw * 3, gh * 3), interpolation=cv2.INTER_NEAREST))
    return scene


def main():
    src, out, model = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    out.mkdir(parents=True, exist_ok=True)
    sess = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
    log, scenes = [], []
    for i, cfg in enumerate(ROUTE, 1):
        scenes.append(build_scene(sess, cfg, src, out, i, log))
        print(log[-1], flush=True)
    (out / "world.json").write_text(json.dumps(dict(scenes=scenes), separators=(",", ":")))


if __name__ == "__main__":
    main()
