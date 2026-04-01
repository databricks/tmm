# Avionics 3D - Design Decisions

This document captures the key architectural and design decisions made during development.

## Architecture

### Component Structure

- **Separation of concerns**: Scene rendering (Three.js) is isolated in `src/scene/`, UI components in `src/components/`, and utility functions in `src/lib/`
- **Single state owner**: `App.tsx` owns all application state and passes data down via props - no global state management library needed for this scale

### Rendering Strategy

- **react-three/fiber**: Chosen over raw Three.js for declarative React integration and automatic cleanup
- **@react-three/drei**: Used for `OrbitControls` - well-tested and handles edge cases
- **Points geometry**: Aircraft rendered as a single `THREE.Points` object rather than individual meshes for performance (handles 10,000+ aircraft)

## 3D Globe

### Coordinate System

- **Normalized radius**: Globe has radius of 1.0 for simpler math
- **Altitude scaling**: Real altitude (meters) converted to globe units via `altitude / 6371000 * scale`
- **Default scale 1000x**: Altitude is exaggerated to make aircraft visible above the surface

### Texture

- **NASA Blue Marble**: Loaded from unpkg CDN (`three-globe` package asset)
- **Fallback**: Solid blue sphere shown during texture load via React Suspense

### Atmosphere

- **Simple glow**: Slightly larger sphere (1.02 radius) with transparent blue backside material
- **No shader complexity**: Avoided custom atmosphere shaders for simplicity

### Graticule

- **30-degree grid**: Latitude and longitude lines every 30 degrees
- **Slight offset**: Lines at radius 1.003 to prevent z-fighting with globe surface

## Aircraft Visualization

### Color Scheme

- **HSL rainbow gradient**: Altitude mapped to hue (0-0.75, red to violet)
- **Max altitude 13km**: Aircraft above this show as violet
- **White for grounded**: Aircraft on ground rendered white
- **Green for selected**: Selected aircraft highlighted in bright green

### Airplane Icons

- **Canvas-drawn texture**: Custom airplane silhouette drawn via Canvas 2D API
- **Point sprites**: Applied as texture map to point material
- **Uniform size**: All aircraft same visual size regardless of distance (sizeAttenuation: true)

### Arc Visualizations

**Trajectory Arcs (Cyan)**:
- Projects 5 minutes of flight based on current velocity, heading, and vertical rate
- Uses simple linear interpolation along lat/lon with altitude changes
- Capped at 1500 arcs for performance
- Arrows at arc endpoints indicate direction

**Origin Arcs (Orange)**:
- Great circle arcs from aircraft position to country-of-origin centroid
- Arc height proportional to distance traveled
- Uses `Line2` from Three.js addons for thick lines (3px)
- Capped at 800 arcs for performance

### Selection

- **Tether line**: Green line from selected aircraft to surface point directly below
- **Auto-rotation pause**: Globe stops rotating when aircraft is selected

## API Integration

### OpenSky Network

- **Proxy configuration**: Vite dev server proxies `/api/opensky` to `https://opensky-network.org/api` to avoid CORS
- **State vector parsing**: Response array indices mapped to named fields via `INDEX` constants
- **Null handling**: Aircraft with invalid lat/lon filtered out during parsing

### Rate Limiting

- **Manual refresh**: No auto-polling to respect API limits
- **All aircraft endpoint**: Uses `/states/all` endpoint for global coverage

## Performance Optimizations

- **Instanced rendering**: All aircraft as single Points geometry
- **Arc limiting**: Maximum 1500 trajectory arcs, 800 origin arcs
- **Memoization**: Heavy computations wrapped in `useMemo`
- **Conditional rendering**: Arcs only rendered when mode is active

## UI/UX Decisions

### Control Panel

- **Glass morphism style**: Semi-transparent dark panel with blur
- **Compact layout**: All controls visible without scrolling
- **Color legend**: Visual key for altitude gradient

### Aircraft Info Panel

- **Dual units**: Altitude shown in meters and feet, velocity in m/s and knots
- **DMS coordinates**: Latitude/longitude in degrees-minutes-seconds format
- **Close button**: Clear selection to return to hover mode

### Hover Tooltip

- **Minimal info**: Callsign, country, altitude only
- **Follows cursor**: Positioned near mouse without blocking aircraft

## Future Considerations

- **WebGL2 instancing**: Could use `InstancedMesh` for more detailed aircraft models
- **WebSocket updates**: Real-time streaming instead of polling
- **Clustering**: Group nearby aircraft at low zoom levels
- **Flight paths history**: Show past trajectory from API time series data
- **Airport labels**: Add major airport markers and names
