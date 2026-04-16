#!/usr/bin/env python3
"""
preprocess.py — Předprocesing říční sítě Čeladné
KGI/VIZUL, Palacký University Olomouc, 2026

Načte toky-celadna.geojson + celadna.shp, ořízne toky na polygon obce,
sestaví topologii ze UTOKJ_ID/UTOKJN_ID, přiřadí každému toku atribut
depth (0 = pramen, max = hlavní tok), exportuje toky_processed.geojson
a data.js pro animaci v index.html.
"""

import geopandas as gpd
import json
import sys
from collections import defaultdict, deque


def build_topology_depths(gdf):
    """
    Vypočítá atribut 'depth' pro každý segment v GeoDataFrame.
    depth=0 pro prameny (listy stromu), depth=max pro hlavní tok (kořen).
    Využívá atributy UTOKJ_ID a UTOKJN_ID.
    """
    gdf = gdf.copy()

    # Zaokrouhlení na celá čísla — floating-point nepřesnosti v ID
    gdf['_uid'] = gdf['UTOKJ_ID'].round(0).astype('int64')
    gdf['_puid'] = gdf['UTOKJN_ID'].round(0).astype('int64')

    all_ids = set(gdf['_uid'].tolist())

    # upstream[B] = [A, ...] → A ústí do B (A je přítok B)
    upstream = defaultdict(list)
    # downstream[A] = B → A ústí do B
    downstream = {}

    for _, row in gdf.iterrows():
        uid = row['_uid']
        puid = row['_puid']
        downstream[uid] = puid
        if puid in all_ids:
            upstream[puid].append(uid)

    # Prameny (leaves) = uzly, do nichž nic neústí
    leaves = [uid for uid in all_ids if not upstream.get(uid)]
    print(f"  Prameny (sources): {len(leaves)}")

    # BFS od pramenů směrem dolů — počítáme nejdelší cestu od pramene ke každému uzlu
    # To zaručuje, že hlavní tok dostane maximální depth
    depth = {uid: -1 for uid in all_ids}
    for leaf in leaves:
        depth[leaf] = 0

    queue = deque([(leaf, 0) for leaf in leaves])
    while queue:
        uid, d = queue.popleft()
        puid = downstream.get(uid)
        if puid in all_ids:
            new_d = d + 1
            if new_d > depth[puid]:
                depth[puid] = new_d
                queue.append((puid, new_d))

    # Izolované segmenty (bez topologického propojení) = depth 0
    for uid in all_ids:
        if depth[uid] < 0:
            depth[uid] = 0

    gdf['depth'] = gdf['_uid'].map(depth).fillna(0).astype(int)
    return gdf.drop(columns=['_uid', '_puid'])


def main():
    print("=" * 50)
    print("Říční síť Čeladné — předprocesing")
    print("=" * 50)

    # 1. Načtení dat
    print("\n[1/6] Načítání vstupních dat...")
    try:
        rivers = gpd.read_file('toky-celadna.geojson')
        print(f"  Toky:  {len(rivers)} segmentů, CRS: {rivers.crs}")
    except Exception as e:
        print(f"CHYBA: nelze načíst toky-celadna.geojson\n  {e}", file=sys.stderr)
        sys.exit(1)

    try:
        commune = gpd.read_file('celadna.shp')
        print(f"  Obec:  {len(commune)} feature, CRS: {commune.crs}")
    except Exception as e:
        print(f"CHYBA: nelze načíst celadna.shp\n  {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Sjednocení souřadnicového systému
    print("\n[2/6] Sjednocení CRS...")
    if commune.crs != rivers.crs:
        commune = commune.to_crs(rivers.crs)
        print(f"  Obec přeprojectována na {rivers.crs}")
    else:
        print(f"  CRS shodné: {rivers.crs}")

    # 3. Ořez toků na hranici obce
    print("\n[3/6] Ořez toků na polygon obce...")
    rivers_clipped = gpd.clip(rivers, commune)
    rivers_clipped = rivers_clipped[~rivers_clipped.geometry.is_empty].copy()
    rivers_clipped = rivers_clipped.reset_index(drop=True)
    print(f"  Segmenty po ořezu: {len(rivers_clipped)}")

    if len(rivers_clipped) == 0:
        print("VAROVÁNÍ: V oblasti obce nebyly nalezeny žádné toky!", file=sys.stderr)
        sys.exit(1)

    # 4. Topologie a výpočet depth
    print("\n[4/6] Sestavení topologie, výpočet depth...")
    rivers_clipped = build_topology_depths(rivers_clipped)
    max_depth = int(rivers_clipped['depth'].max())
    print(f"  Maximální depth: {max_depth}")
    dist = rivers_clipped['depth'].value_counts().sort_index()
    print("  Distribuce (depth: počet):")
    for d, n in dist.items():
        bar = '█' * min(n, 30)
        print(f"    {d:3d}: {bar} ({n})")

    # 5. Reprojekce do WGS84
    print("\n[5/6] Reprojekce do WGS84 (EPSG:4326)...")
    rivers_wgs84 = rivers_clipped.to_crs('EPSG:4326')
    commune_wgs84 = commune.to_crs('EPSG:4326')

    bounds = rivers_wgs84.total_bounds  # minx(lon), miny(lat), maxx(lon), maxy(lat)
    bbox_str = (f"{bounds[1]:.4f}°N\u2013{bounds[3]:.4f}°N, "
                f"{bounds[0]:.4f}°E\u2013{bounds[2]:.4f}°E")
    print(f"  Bbox WGS84: {bbox_str}")

    # 6a. Export toky_processed.geojson
    print("\n[6/6] Export výstupních souborů...")
    rivers_wgs84.to_file('toky_processed.geojson', driver='GeoJSON')
    print("  toky_processed.geojson  ✓")

    # 6b. Export data.js (embedovaná data pro index.html)
    rivers_json = json.loads(rivers_wgs84.to_json())
    commune_json = json.loads(commune_wgs84.to_json())

    # Zjistíme hlavní tok (největší depth)
    main_river_row = rivers_clipped.loc[rivers_clipped['depth'].idxmax()]
    main_river_name = main_river_row.get('NAZ_TOK', '') or 'Čeladenka'

    with open('data.js', 'w', encoding='utf-8') as f:
        f.write('// Automaticky generováno skriptem preprocess.py\n')
        f.write('// Říční síť Čeladné — předzpracovaná data pro animaci v index.html\n\n')
        f.write(f'const MAX_DEPTH = {max_depth};\n\n')
        f.write(f'const BBOX_STR = {json.dumps(bbox_str)};\n\n')
        f.write('const RIVERS_DATA = ')
        json.dump(rivers_json, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n\n')
        f.write('const COMMUNE_DATA = ')
        json.dump(commune_json, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')

    print("  data.js                 ✓")

    print("\n" + "=" * 50)
    print("Hotovo!")
    print(f"  Segmentů: {len(rivers_clipped)},  depth 0–{max_depth}")
    print(f"  Hlavní tok: {main_river_name}")
    print(f"  Bbox: {bbox_str}")
    print("=" * 50)


if __name__ == '__main__':
    main()
