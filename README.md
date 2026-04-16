# Vody Čeladné

Animovaná umělecká mapa říční sítě okolí Čeladné v Beskydech.  
Toky se postupně vykreslují od pramenů k hlavnímu toku Čeladenky — jako by je někdo kreslil perem.

**KGI/VIZUL, Palacký University Olomouc — Petr Mikeska, 2026**

---

## Jak to funguje

Animace prochází 38 topologickými úrovněmi (depth 0–37):

- **depth 0** — 92 pramenů kreslí simultánně
- **depth 1–9** — přítokové soustavy se postupně slévají
- **depth 10–37** — samotná Čeladenka (segment po segmentu) protéká celým územím

Po ~30 sekundách animace zamrzne jako statický poster.

---

## Struktura souborů

```
vizul-05/
│
├── preprocess.py            # Python skript — předzpracování dat
├── index.html               # Webová aplikace (Canvas animace)
├── data.js                  # Vygenerovaná data pro animaci
│
├── toky_processed.geojson   # Výstup preprocessingu (WGS84, atribut depth)
│
├── toky-celadna.geojson     # Vstupní data — říční síť (EPSG:5514)
├── celadna.shp / .dbf / .prj / .shx / .cpg
│                            # Vstupní data — polygon obce Čeladná (EPSG:5514)
│
├── web/                     # Složka pro nahrání na hosting
│   ├── index.html
│   └── data.js
│
└── vizul2026_cv5_mikeska.zip  # Archiv pro odevzdání
```

---

## Lokální spuštění

Soubor `index.html` načítá `data.js` přes `<script src>`, takže funguje i bez serveru.  
Stačí otevřít `index.html` přímo v prohlížeči (dvojklik nebo `file://` URL).

Nebo spusťte jednoduchý lokální server:

```bash
python3 -m http.server 8000
# → http://localhost:8000
```

---

## Nasazení na hosting

Do složky `web/` jsou zkopírovány jen soubory potřebné pro web:

| Soubor       | Velikost | Popis                              |
|--------------|----------|------------------------------------|
| `index.html` | 13 kB    | Stránka s Canvas animací           |
| `data.js`    | 281 kB   | Geodata (toky + obec) pro animaci  |

**Nahrajte obsah složky `web/` na hosting** (oba soubory musí být ve stejném adresáři).  
Žádné závislosti, žádný backend — funguje na jakémkoli statickém hostingu (GitHub Pages, Netlify, vlastní server, ...).

---

## Přegenerování dat (volitelné)

Pokud změníte vstupní geodata, spusťte znovu preprocess:

```bash
pip install geopandas shapely
python3 preprocess.py
```

Skript přepíše `toky_processed.geojson` a `data.js` a pak zkopírujte `data.js` do `web/`.

---

## Technické detaily

| Parametr              | Hodnota                              |
|-----------------------|--------------------------------------|
| Vstupní CRS           | EPSG:5514 (S-JTSK / Krovak East North) |
| Výstupní CRS          | EPSG:4326 (WGS84)                    |
| Počet segmentů        | 186                                  |
| Topologická hloubka   | 0–37 (Čeladenka = 37)               |
| Pramenů (sources)     | 92                                   |
| Bbox                  | 49.4400–49.5591°N, 18.3058–18.3703°E |
| Technologie           | Python 3, geopandas, Vanilla JS, Canvas API |
| Fonty                 | Playfair Display (Google Fonts), fallback serif |
