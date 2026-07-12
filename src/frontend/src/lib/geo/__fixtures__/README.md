# lib/geo test fixtures

`mini-counties.source.geojson.json` — a hand-authored 2x2 grid of unit-square "counties"
(GEOID 00001-00004, laid out below), used to test `mergePolity`/`mergePolityOutline`
without depending on the real (multi-megabyte) `counties.topojson` asset.

```
+--------+--------+
| 00003  | 00004  |   y: [1,2]
| Gamma  | Delta  |
+--------+--------+
| 00001  | 00002  |   y: [0,1]
| Alpha  | Beta   |
+--------+--------+
  x:[0,1]  x:[1,2]
```

Adjacency (shares an edge): 00001-00002, 00001-00003, 00002-00004, 00003-00004.
Diagonal (shares only a corner point, no edge): 00001-00004, 00002-00003.

`mini-counties.topojson.json` is the shared-arc TopoJSON produced by running the real
pipeline tool (`npx mapshaper`) over the source GeoJSON — this guarantees the fixture's
arc-sharing topology matches production output exactly, rather than hand-writing arc
indices (error-prone) or drifting from mapshaper's actual conventions. Regenerate with:

```
npx --yes mapshaper -i mini-counties.source.geojson.json \
  -rename-layers counties \
  -o format=topojson id-field=GEOID mini-counties.topojson.json force
```
