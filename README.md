# Trashcoli-live
repo per mostrare un world model di trashcoli

## Dentro Faraona

Dieci luoghi di Faraona ricostruiti in 3D dalle foto dei Trashcoli, cinque fuori e cinque dentro, da esplorare in prima persona sotto una pioggia di cenere. Le foto sono stanze affacciate su un unico corridoio, e si passa dall'una all'altra camminando. L'ultima stanza, *Dentro la cattedrale*, è una chiesa intera ricostruita da due foto scattate ai suoi due capi.

**Gioca online:** https://g95g95.github.io/Trashcoli-live/

<img src="qr.png" alt="QR code che apre Dentro Faraona su g95g95.github.io/Trashcoli-live" width="220">

Versione da stampare, con titolo e indirizzo sotto il codice: [`qr_stampa.png`](qr_stampa.png). Versione vettoriale, che si ingrandisce senza perdere qualità: [`qr.svg`](qr.svg).

## Comandi

| Su PC | Su telefono |
|---|---|
| Clic: cattura il mouse per guardarti intorno | Pollice sinistro: trascina per camminare |
| W A S D o frecce: cammina, Shift: corri | Resto dello schermo: trascina per guardare |
| F: torcia · E: leggi il foglio nella cappella | Pulsanti in alto: cenere, torcia, vento |
| 1–9, 0: salta a un luogo · Esc: libera il mouse | Pulsanti in basso: luoghi |

Ogni porta del corridoio si apre su una foto: entri, ti guardi intorno, esci e prosegui verso la porta successiva. Appena oltre la porta sei nel punto esatto da cui è stata scattata la foto. A metà corridoio una soglia separa i luoghi di fuori da quelli di dentro. In fondo al corridoio, da tutte e due le parti, c'è una porta di brace: entri in una ed esci dall'altra, così il percorso non finisce.

La porta 10 è il portone di una chiesa: entri sotto la cantoria e hai davanti la navata, fino all'altare. Le foto sono due, e ci si arriva a piedi. La prima è scattata dalla cantoria: sali la scala ripida a sinistra del portone e vai al parapetto. La seconda è scattata dall'altare: attraversa la navata, sali sul presbiterio, scavalca le macerie e girati verso il portone. Il tasto 0 (o il pulsante 10) ti porta direttamente su uno dei due punti; premilo di nuovo per l'altro.

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
- La cattedrale è fatta in un altro modo, perché le foto sono due. Il motore costruisce una navata vera: pareti, volta a botte, presbiterio rialzato, cantoria con la scala, colonne, panche e cumuli di macerie. Poi dipinge ogni punto della navata con le foto: proietta ogni foto dal suo punto di ripresa, come un proiettore di diapositive. Per ogni foto calcola una volta sola la mappa delle distanze, così una foto non colora quello che lei stessa non vede, per esempio il pavimento dietro una panca. Se due foto vedono lo stesso punto, vince quella scattata dalla direzione più vicina alla tua e meno di taglio. Dai due punti di ripresa vedi quindi la foto esatta. Dove nessuna foto arriva, la navata è un intonaco scuro dei colori della chiesa. Il portone verso il corridoio mostra il portone chiuso della foto e si apre quando ti avvicini.
- `lib/three.module.js` — three.js r160, licenza MIT (`lib/LICENSE-three.txt`).
- `dati/` — per ogni luogo: `sN.jpg` (la foto), `sN_d.png` (profondità in millimetri su 16 bit nei canali rosso e verde, cielo nel canale blu), `world.json` (orientamento, griglia dei punti calpestabili, posizione del varco; il motore attuale non usa più il varco, perché le stanze si raggiungono dal corridoio). Il file `s6_doc.jpg` è il foglio *Le Lampade Viventi* trovato nella cappella. Per la cattedrale: `c1.jpg` (dall'altare), `c2.jpg` (dalla cantoria) e `cattedrale.json` (misure della navata, posizione e orientamento delle due macchine fotografiche, panche, macerie). È un file separato da `world.json`, perché `build_world.py` riscrive `world.json` da zero.
- `strumenti/build_world.py` — la pipeline che dalle foto genera `dati/`.
- `strumenti/build_cattedrale.py` — calcola `cattedrale.json` dalle due foto della chiesa: `python3 strumenti/build_cattedrale.py <foto_altare> <foto_cantoria> dati`. Contiene i punti presi a mano sulle foto: gli spigoli della cantoria, della porta e del muro di fondo, i punti di fuga, una persona in piedi sotto la cantoria e le panche. Da questi punti ricava, con i minimi quadrati, dove stava ogni macchina e quanto è grande la navata. La scala viene dalla larghezza della navata, fissata a 7 m.
- `strumenti/assemble_standalone.py` — impacchetta tutto nel file unico, partendo da `strumenti/pagina_sorgente.html` e `strumenti/three.min.js`.
- `manifesto/` — la pagina del manifesto: `index.html` (HTML, CSS e JavaScript in un file, senza librerie; la carta e i bordi bruciati sono generati dal programma), `sfondo.jpg` (la foto dietro la pergamena) e i QR code.

## Rigenerare con altre foto

La profondità viene stimata con Depth Anything ViT-S, una rete neurale che da una singola foto deduce quanto è lontano ogni punto. Il modello è nel formato ONNX (Open Neural Network Exchange, un formato aperto per modelli di reti neurali) e gira sul processore, senza scheda video.

1. Installa le dipendenze: `pip install onnxruntime opencv-contrib-python pillow numpy`
2. Scarica il modello (circa 100 MB): https://github.com/fabio-sim/Depth-Anything-ONNX/releases/download/v1.0.0/depth_anything_vits14.onnx
3. Metti le foto in una cartella e modifica la lista `ROUTE` in cima a `strumenti/build_world.py`. Per ogni foto indichi nome del file, etichetta, gruppo (`Fuori` o `Dentro`), inclinazione approssimativa della macchina in gradi (positiva verso l'alto) e profondità tipica in metri. Inclinazione e profondità servono solo quando la pipeline non trova né il pavimento né le linee verticali.
4. Lancia `python3 strumenti/build_world.py <cartella_foto> dati <modello.onnx>`. Ci vogliono pochi secondi a foto. Viene creata anche una cartella `diag/` con le mappe di profondità e le griglie calpestabili, per controllare il risultato.
5. Per rifare il file unico: `python3 strumenti/assemble_standalone.py strumenti/pagina_sorgente.html dati strumenti/three.min.js Dentro_Faraona.html`

## Limiti

Ogni luogo è in rilievo solo dove la foto ha visto qualcosa: fuori dall'inquadratura le pareti della stanza ripetono la foto allungata e sfocata, quindi sono macchie di colore e non oggetti. Il corridoio non viene dalle foto, è inventato. Più ti allontani dal punto di ripresa, più il rilievo si deforma: le figure sottili, come la persona nella cappella, viste di lato diventano teli stirati. Nelle foto ravvicinate (televisore, carrozzina, brande) lo spazio calpestabile è di pochi metri quadrati. Le profondità sono stimate, non misurate, quindi le proporzioni sono plausibili ma non esatte.

Nella cattedrale le misure vengono da due foto e da una larghezza supposta (7 m), quindi valgono entro qualche decina di centimetri. Le due foto non sono in perfetto accordo, quindi camminando i dettagli delle pareti scivolano un poco quando si passa da una foto all'altra. Le pareti viste di taglio sono sfocate. Nessuna delle due foto vede il centro della volta, il retro della cantoria e il lato delle panche rivolto al portone: lì c'è un intonaco scuro inventato. Anche la scala della cantoria è inventata: le foto non la mostrano.

## Manifesto

Il manifesto dei Trashcoli, dalla spusticzine n. 2 (agosto 2022), su una pergamena che si srotola mentre scorri. È una pagina separata, non collegata al gioco.

**Leggi online:** https://g95g95.github.io/Trashcoli-live/manifesto/

<img src="manifesto/qr.png" alt="QR code che apre il manifesto su g95g95.github.io/Trashcoli-live/manifesto" width="220">

Versione da stampare, con titolo e indirizzo sotto il codice: [`manifesto/qr_stampa.png`](manifesto/qr_stampa.png). Versione vettoriale: [`manifesto/qr.svg`](manifesto/qr.svg).
