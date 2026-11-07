# Pagina /manifesto/

Obiettivo: il manifesto dei Trashcoli come pergamena che si srotola mentre scorri, sopra una foto sfocata. Indirizzo: `https://g95g95.github.io/Trashcoli-live/manifesto/`.

## Scelte già fatte
- Testo: `tasks/manifesto_testo.md` (trascritto dalle 3 foto della spusticzine n. 2, 08/2022).
- Sfondo: `Downloads/trashcoli/Esposizione/Buffezze/IMG_20200722_004237_A5.jpg` — due esploratori di spalle in un varco di mattoni, oltre il varco un cantiere bianco e una rete arancione.

## File
- `manifesto/index.html` — pagina unica: HTML, CSS e JS inline, nessuna libreria esterna. Font da Google Fonts.
- `manifesto/sfondo.jpg` — la foto ridotta a 1600 px (circa 150 KB). La sfocatura la fa il CSS, quindi non serve alta risoluzione.
- `README.md` — una sezione breve sulla nuova pagina.

## Esperienza
1. **Apertura.** Schermo nero. Il varco di luce della foto appare lentamente, sfocato. Sopra compare il titolo TRASHCOLI · MANIFESTO.
2. **Pergamena.** Due rulli fissi, in alto e in basso nello schermo. Quando scorri, la carta passa tra i rulli e sembra srotolarsi. Tra i rulli la carta resta piatta. Vicino ai rulli si curva con un'ombra.
3. **Carta.** Texture generata con filtri SVG (fibre, macchie, ingiallimento). Bordi strappati e bruciati, con un filo di brace, come le porte di brace del gioco. Nessuna immagine di carta scaricata.
4. **Testo.** Testo vero, selezionabile e leggibile da screen reader. Serif da libro antico, capolettera al primo paragrafo. Ogni paragrafo appare come inchiostro che penetra nella carta quando entra nello schermo. La parola *entraci* ha un effetto suo.
5. **Sfondo vivo.** La foto si muove pochissimo (zoom lento). Con lo scorrimento cambia la sfocatura: alla fine il varco diventa più nitido. Cenere leggera che cade, come nel gioco.
6. **Fine.** Firma "spusticzine n. 2 · 08/2022". La pergamena si chiude sul rullo. Nessun link al gioco.
7. **Accessibilità e telefono.** Funziona a 360 px di larghezza. Con "riduci movimento" attivo, niente animazioni: la pergamena è statica e il testo è tutto visibile.

## QR code
- `manifesto/qr.svg`, `manifesto/qr.png`, `manifesto/qr_stampa.png`, nello stesso stile dei QR del gioco nella radice.
- Puntano a `https://g95g95.github.io/Trashcoli-live/manifesto/`. Sotto il codice della versione stampa: "Trashcoli · Manifesto" e l'indirizzo.

## Regola: il manifesto e il gioco non si parlano
- Nessun link, pulsante o rimando dall'uno all'altro, in nessuna delle due direzioni.
- Nessuna modifica al gioco (`index.html`, `Dentro_Faraone.html`).

## Verifica
1. Server locale (`python -m http.server`) e screenshot in Edge headless a 1440 px e a 390 px.
2. Controllo: niente scroll orizzontale, testo leggibile sopra la carta, animazioni fluide.
3. Confronto parola per parola tra pagina e `tasks/manifesto_testo.md`.
