# CLAUDE.md - Development Context

This file contains technical context for Claude Code to assist with future development on this project.

## Project Overview

Single-file flight visualization POC using OpenSky Network API data rendered with MapLibre GL + deck.gl.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      index.html                              │
├─────────────────────────────────────────────────────────────┤
│  CSS Styles                                                  │
│  ├── Sunrise theme (warm oranges/golds)                     │
│  ├── Glass-morphism panels (backdrop-filter: blur)          │
│  ├── Sun glow effect (CSS radial gradients)                 │
│  └── Responsive controls                                     │
├─────────────────────────────────────────────────────────────┤
│  MapLibre GL JS (v3.6.2)                                    │
│  ├── Base map container                                      │
│  ├── CARTO raster tiles (light/dark)                        │
│  └── 45° pitch, centered on Europe [15, 50]                 │
├─────────────────────────────────────────────────────────────┤
│  deck.gl Overlay (v8.9.33)                                  │
│  ├── ArcLayer (trajectories)                                │
│  ├── ScatterplotLayer (aircraft glow)                       │
│  ├── ScatterplotLayer (aircraft points, pickable)           │
│  └── LineLayer (heading indicators)                         │
├─────────────────────────────────────────────────────────────┤
│  Data Flow                                                   │
│  └── fetch() → OpenSky API → filter/map → render layers     │
└─────────────────────────────────────────────────────────────┘
```

## Key Technical Decisions

### Why MapLibre GL + deck.gl (not pure deck.gl GlobeView)?
- `deck.GlobeView` threw "not a constructor" error in v8.9.33
- MapLibre provides reliable tile-based map rendering
- deck.gl MapboxOverlay integrates seamlessly for data layers
- This combination is production-proven

### Why single HTML file?
- No build tools required
- Easy to share and demo
- All dependencies loaded from CDN
- Suitable for POC/mockup purposes

### Map Style Toggle Implementation
```javascript
// Dynamically update tile source URL
map.getSource('carto').tiles = [MAP_STYLES[style]];
map.style.sourceCaches['carto'].clearTiles();
map.style.sourceCaches['carto'].update(map.transform);
map.triggerRepaint();
```

## API Details

### OpenSky Network Endpoint
```
GET https://opensky-network.org/api/states/all
    ?lamin=35    # min latitude
    &lomin=-15   # min longitude
    &lamax=72    # max latitude
    &lomax=45    # max longitude
```

### Rate Limits
- Anonymous: ~400 API credits/day, 10 requests/day for state vectors
- Registered: Higher limits with API key
- Current implementation: Single fetch on page load

### Data Transformation
```javascript
// Raw API state array → flight object
s => ({
  icao: s[0],
  call: (s[1] || '').trim(),
  country: s[2],
  lon: s[5],
  lat: s[6],
  alt: s[7] || s[13] || 0,  // baro_altitude or geo_altitude
  vel: s[9] || 0,            // m/s
  hdg: s[10] || 0,           // degrees
  vr: s[11] || 0             // m/s vertical rate
})
```

## Styling Constants

### Altitude Color Mapping
```javascript
// Altitude (ft) → RGBA color
< 15,000 ft  → [255, 107, 107, 240]  // Coral red
15-30,000 ft → interpolated          // Gold gradient
> 30,000 ft  → [255, 255, 255, 240]  // White
```

### Trajectory Calculation
```javascript
// Project flight path ahead based on heading and speed
const dist = (velocity / 200) * 1.8;  // degrees
const rad = (90 - heading) * Math.PI / 180;
return [lon + Math.cos(rad) * dist, lat + Math.sin(rad) * dist];
```

## Common Tasks

### Add new map style
1. Add tile URL to `MAP_STYLES` object
2. Add `<option>` to `#mapStyle` select
3. Style will auto-switch via existing event listener

### Change Europe bounding box
Edit the fetch URL parameters:
- `lamin` / `lamax` for latitude range
- `lomin` / `lomax` for longitude range

### Add continuous updates
```javascript
// Add after loadFlights() call:
setInterval(loadFlights, 15000);  // Every 15 seconds
```

### Adjust aircraft size
Modify `radiusMinPixels` / `radiusMaxPixels` in ScatterplotLayer config.

## Dependencies (CDN)

| Library | Version | CDN URL |
|---------|---------|---------|
| MapLibre GL JS | 3.6.2 | unpkg.com/maplibre-gl@3.6.2 |
| MapLibre GL CSS | 3.6.2 | unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css |
| deck.gl | 8.9.33 | unpkg.com/deck.gl@8.9.33 |

## Future Enhancements

- [ ] Add aircraft icons (IconLayer) instead of dots
- [ ] WebSocket connection for real-time updates
- [ ] Flight path history trails
- [ ] Click-to-track individual aircraft
- [ ] Integration with Spark SDP for streaming data
- [ ] Add airport markers
- [ ] Filter by airline/country
