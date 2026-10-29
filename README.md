# Trashcoli-live
repo per mostrare un world model di trashcoli

## Dentro Faraona

Nove luoghi di Faraona ricostruiti in 3D dalle foto dei Trashcoli, cinque fuori e quattro dentro, da esplorare in prima persona sotto una pioggia di cenere. Le foto sono stanze affacciate su un unico corridoio, e si passa dall'una all'altra camminando.

**Gioca online:** https://g95g95.github.io/Trashcoli-live/

<img src="qr.png" alt="QR code che apre Dentro Faraona su g95g95.github.io/Trashcoli-live" width="220">

Versione da stampare, con titolo e indirizzo sotto il codice: [`qr_stampa.png`](qr_stampa.png). Versione vettoriale, che si ingrandisce senza perdere qualità: [`qr.svg`](qr.svg).

## Comandi

| Su PC | Su telefono |
|---|---|
| Clic: cattura il mouse per guardarti intorno | Pollice sinistro: trascina per camminare |
| W A S D o frecce: cammina, Shift: corri | Resto dello schermo: trascina per guardare |
| F: torcia · E: leggi il foglio nella cappella | Pulsanti in alto: cenere, torcia, vento |
| 1–9: salta a un luogo · Esc: libera il mouse | Pulsanti in basso: luoghi |

Ogni porta del corridoio si apre su una foto: entri, ti guardi intorno, esci e prosegui verso la porta successiva. Appena oltre la porta sei nel punto esatto da cui è stata scattata la foto. A metà corridoio una soglia separa i luoghi di fuori da quelli di dentro. In fondo al corridoio, da tutte e due le parti, c'è una porta di brace: entri in una ed esci dall'altra, così il percorso non finisce.

## Altri modi per avviarlo

- **File unico:** `Dentro_Faraona.html` contiene tutto (motore 3D, foto, profondità). Si apre con doppio clic, anche offline, e si può passare su WhatsApp o su una chiavetta.
- **In locale dalla cartella del repo:** `index.html` carica i file di `dati/`, e i browser bloccano questo caricamento se la pagina è aperta come file dal disco. Serve un piccolo server web locale:
  ```
  python3 -m http.server 8000
  ```
  e poi apri `http://localhost:8000`.

## Pubblicazione su GitHub Pages

GitHub Pages è il servizio di GitHub che pubblica come sito i file di un repo. Si attiva una volta sola: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main`, cartella `/ (root)` → Save.** Dopo un paio di minuti il sito risponde all'indirizzo qui sopra, e da lì in poi ogni push su `main` lo aggiorna. Il file `.nojekyll` dice a GitHub di servire i file così come sono, senza passarli dal generatore di siti Jekyll.

## Com'è fatto

- `index.html` — il motore, scritto con three.js, una libreria JavaScript per la grafica 3D nel browser via WebGL. Per ogni foto costruisce una superficie in rilievo e una stanza chiusa attorno. Le pareti della stanza mostrano la foto proiettata dal punto di ripresa: dentro l'inquadratura combaciano con la foto, fuori ne allungano i bordi e poi la sfumano in un muro scuro dei suoi colori. Le stanze si affacciano a destra e a sinistra su un corridoio disegnato dal programma, di pietra fuori e di intonaco e cementine dentro, illuminato dalla luce che esce dalle porte. Poi aggiunge la cenere che cade, quella che si posa col tempo, la nebbia, la torcia e il vento. Il vento è rumore generato al momento, senza file audio.
- `lib/three.module.js` — three.js r160, licenza MIT (`lib/LICENSE-three.txt`).
- `dati/` — per ogni luogo: `sN.jpg` (la foto), `sN_d.png` (profondità in millimetri su 16 bit nei canali rosso e verde, cielo nel canale blu), `world.json` (orientamento, griglia dei punti calpestabili, posizione del varco; il motore attuale non usa più il varco, perché le stanze si raggiungono dal corridoio). Il file `s6_doc.jpg` è il foglio *Le Lampade Viventi* trovato nella cappella.
- `strumenti/build_world.py` — la pipeline che dalle foto genera `dati/`.
- `strumenti/assemble_standalone.py` — impacchetta tutto nel file unico, partendo da `strumenti/pagina_sorgente.html` e `strumenti/three.min.js`.

## Rigenerare con altre foto

La profondità viene stimata con Depth Anything ViT-S, una rete neurale che da una singola foto deduce quanto è lontano ogni punto. Il modello è nel formato ONNX (Open Neural Network Exchange, un formato aperto per modelli di reti neurali) e gira sul processore, senza scheda video.

1. Installa le dipendenze: `pip install onnxruntime opencv-contrib-python pillow numpy`
2. Scarica il modello (circa 100 MB): https://github.com/fabio-sim/Depth-Anything-ONNX/releases/download/v1.0.0/depth_anything_vits14.onnx
3. Metti le foto in una cartella e modifica la lista `ROUTE` in cima a `strumenti/build_world.py`. Per ogni foto indichi nome del file, etichetta, gruppo (`Fuori` o `Dentro`), inclinazione approssimativa della macchina in gradi (positiva verso l'alto) e profondità tipica in metri. Inclinazione e profondità servono solo quando la pipeline non trova né il pavimento né le linee verticali.
4. Lancia `python3 strumenti/build_world.py <cartella_foto> dati <modello.onnx>`. Ci vogliono pochi secondi a foto. Viene creata anche una cartella `diag/` con le mappe di profondità e le griglie calpestabili, per controllare il risultato.
5. Per rifare il file unico: `python3 strumenti/assemble_standalone.py strumenti/pagina_sorgente.html dati strumenti/three.min.js Dentro_Faraona.html`

## Limiti

Ogni luogo è in rilievo solo dove la foto ha visto qualcosa: fuori dall'inquadratura le pareti della stanza ripetono la foto allungata e sfocata, quindi sono macchie di colore e non oggetti. Il corridoio non viene dalle foto, è inventato. Più ti allontani dal punto di ripresa, più il rilievo si deforma: le figure sottili, come la persona nella cappella, viste di lato diventano teli stirati. Nelle foto ravvicinate (televisore, carrozzina, brande) lo spazio calpestabile è di pochi metri quadrati. Le profondità sono stimate, non misurate, quindi le proporzioni sono plausibili ma non esatte.
