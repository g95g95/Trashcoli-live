"""Crea Dentro_Faraona.html: un solo file con motore, foto e profondità incorporati (si apre con doppio clic)."""
import base64, json, re, sys
from pathlib import Path

web, data, three, out = map(Path, sys.argv[1:5])

def data_uri(p: Path) -> str:
    mime = {".jpg": "image/jpeg", ".png": "image/png"}[p.suffix]
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()

world = json.loads((data / "world.json").read_text())
for sc in world["scenes"]:
    sc["tex"] = data_uri(data / sc["tex"])
    sc["depth"] = data_uri(data / sc["depth"])
    if "doc" in sc:
        sc["doc"]["tex"] = data_uri(data / sc["doc"]["tex"])

html = web.read_text()
# niente CDN: three.js incorporato come script classico (definisce la variabile globale THREE)
html, n1 = re.subn(r'<script type="importmap">.*?</script>\s*', "", html, flags=re.S)
rep2 = ("<script>\n" + three.read_text() + "\n</script>\n<script>\nconst WORLD = "
        + json.dumps(world, separators=(",", ":")) + ";\n(function () {\n")
html, n2 = re.subn(r'<script type="module">\s*import \* as THREE from "three";', lambda m: rep2, html)
html, n3 = re.subn(r'world = await \(await fetch\("world\.json"\)\)\.json\(\);', "world = WORLD;", html)
html, n4 = re.subn(r"(window\.__faraona = \{[^}]*\};)\s*</script>",
                   lambda m: m.group(1) + "\n})();\n</script>", html)
assert (n1, n2, n3, n4) == (1, 1, 1, 1), (n1, n2, n3, n4)

head = ('<!doctype html>\n<html lang="it">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
        "body{margin:0;font:14px system-ui,-apple-system,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>\n")
# title/meta/link/style del progetto vanno nell'head, il resto nel body
split = html.index("</style>") + len("</style>")
page = head + html[:split] + "\n</head>\n<body>\n" + html[split:] + "\n</body>\n</html>\n"
out.write_text(page)
print(f"{out.name}: {out.stat().st_size / 1e6:.1f} MB")
