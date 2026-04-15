/**
 * ZeroStream Dashboard
 * Real-time visualization of sensor data from Zerobus
 */

// =============================================================================
// Configuration
// =============================================================================

const CONFIG = {
    // Frontend URL is injected by the backend from FRONTEND_URL environment variable
    frontendUrl: window.FRONTEND_URL || 'https://zerostream-2847375137997282.aws.databricksapps.com',
    refreshInterval: 5000, // milliseconds
    activityThreshold: 5 * 60 * 1000, // 5 minutes in milliseconds
    apiEndpoints: {
        count: '/api/count',
        locations: '/api/locations',
        datasource: '/api/datasource'
    }
};

// =============================================================================
// State Management
// =============================================================================

const state = {
    currentPage: 'landing',
    currentCount: 0,
    previousCount: 0,
    locations: [],
    clients: [],
    uniqueClients: 0,
    dataSizeMB: 0,
    lastDataTimestamp: null,
    fullTrace: false,
    map: null,
    vectorSource: null,
    traceSource: null, // Separate source for trace lines (not clustered)
    traceLayer: null,  // Separate layer for trace lines (not clustered)
    tileLayer: null,
    refreshTimer: null,
    clientColors: {},  // Map client_id to color
    markerFeatures: {}, // Track markers by uid for smooth updates
    traceLineFeature: null, // Single LineString feature for trace mode (performance optimization)
    dataSource: null, // 'zerobus' or 'lakebase' - initialized on first screen load
    dataSourceSwitching: false, // Prevent multiple simultaneous switches
    selectedClient: null, // Selected client for trace view
    locationAbortController: null // AbortController for cancelling in-flight location requests
};

// Safe localStorage helpers (handle private browsing mode)
function safeGetItem(key) {
    try {
        return localStorage.getItem(key);
    } catch (e) {
        console.warn('localStorage not available:', e.message);
        return null;
    }
}

function safeSetItem(key, value) {
    try {
        localStorage.setItem(key, value);
    } catch (e) {
        console.warn('localStorage not available:', e.message);
    }
}

// Map layer configurations with max zoom limits per provider
const MAP_LAYERS = {
    light: {
        name: 'Light',
        url: 'https://{a-c}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        maxZoom: 20
    },
    dark: {
        name: 'Dark',
        url: 'https://{a-c}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        maxZoom: 20
    },
    satellite: {
        name: 'Satellite',
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maxZoom: 18
    },
    terrain: {
        name: 'Terrain',
        url: 'https://{a-c}.tile.opentopomap.org/{z}/{x}/{y}.png',
        maxZoom: 17
    }
};

// =============================================================================
// Navigation
// =============================================================================

function navigateTo(page) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));

    // Show target page
    const targetPage = document.getElementById(`${page}-page`);
    if (targetPage) {
        targetPage.classList.add('active');
        state.currentPage = page;

        // Initialize dashboard when navigating to it for the first time
        if (page === 'dashboard' && !state.map) {
            // initializeDashboard() handles starting auto-refresh after setup
            initializeDashboard();
        } else if (page === 'dashboard') {
            // Dashboard already initialized - just restart refresh timer
            startAutoRefresh();
        } else {
            // Leaving dashboard - stop refresh
            stopAutoRefresh();
        }
    }
}

// Settings panel is now controlled by Bootstrap offcanvas via data-bs-toggle attribute

function changeMapLayer() {
    const select = document.getElementById('map-layer-select');
    const layerKey = select.value;
    const layerConfig = MAP_LAYERS[layerKey];

    if (layerConfig && state.tileLayer) {
        state.tileLayer.setSource(new ol.source.XYZ({
            url: layerConfig.url
        }));

        // Update view max zoom based on layer's tile availability
        if (state.map) {
            const view = state.map.getView();
            const newMaxZoom = layerConfig.maxZoom || 20;
            view.setMaxZoom(newMaxZoom);

            // If current zoom exceeds new max, zoom out smoothly
            if (view.getZoom() > newMaxZoom) {
                view.animate({ zoom: newMaxZoom, duration: 300 });
            }
        }

        safeSetItem('mapLayer', layerKey);
    }
}

// =============================================================================
// Data Source Switching
// =============================================================================

/**
 * Switch between Zerobus (SQL Warehouse) and Lakebase (PostgreSQL) data sources.
 * - Zerobus: Full data access via Databricks SQL Warehouse (blue header)
 * - Lakebase: Recent data access via PostgreSQL-compatible interface (green header)
 */
async function switchDataSource(source, forceLoad = false) {
    console.log(`switchDataSource called: source=${source}, forceLoad=${forceLoad}, current=${state.dataSource}, switching=${state.dataSourceSwitching}`);

    // Skip if already switching or already on this source (unless forceLoad is true)
    if (state.dataSourceSwitching) {
        console.log('Skipping: already switching');
        return;
    }
    if (!forceLoad && source === state.dataSource) {
        console.log('Skipping: already on this source');
        return;
    }

    state.dataSourceSwitching = true;
    const statusLabel = document.getElementById('datasource-label');
    const header = document.getElementById('dashboard-header');

    try {
        // Show switching status
        if (statusLabel) {
            statusLabel.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Switching...';
        }

        // Switch backend data source
        const response = await fetch(CONFIG.apiEndpoints.datasource, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ source: source })
        });

        if (!response.ok) {
            let errorMsg = `HTTP ${response.status}: Switch failed`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.detail?.message || errorData.detail?.error || errorData.message || errorMsg;
                if (errorData.detail?.details && errorData.detail.details.length > 0) {
                    errorMsg += ': ' + errorData.detail.details.join(', ');
                }
            } catch (parseError) {
                const text = await response.text().catch(() => '');
                if (text.includes('<!DOCTYPE') || text.includes('<html')) {
                    errorMsg = `HTTP ${response.status}: Server returned HTML error page`;
                }
                console.error('Failed to parse error response:', parseError);
            }
            throw new Error(errorMsg);
        }

        const data = await response.json();

        // Update state
        state.dataSource = source;
        safeSetItem('dataSource', source);

        // Dashboard always uses lakebase - no URL path change needed
        // The /zerobus path now serves the streaming data table (different page)

        // Update header color based on source
        if (header) {
            if (source === 'lakebase') {
                header.classList.add('lakebase');
            } else {
                header.classList.remove('lakebase');
            }
        }

        // Update status label - dashboard always uses Lakebase
        if (statusLabel) {
            statusLabel.innerHTML = '<i class="bi bi-lightning me-1"></i>Lakebase';
        }

        // Handle mode-specific setup - dashboard always uses Lakebase
        const clientSelector = document.getElementById('client-selector-container');
        if (clientSelector) {
            clientSelector.style.display = 'none';
        }

        // Lakebase mode: Show all clients overview with world view
        state.selectedClient = null;
        state.fullTrace = false;
        // Reset to world view
        if (state.map) {
            state.map.getView().animate({
                center: ol.proj.fromLonLat([0, 20]),
                zoom: 2,
                duration: 500
            });
        }

        // Reset clustering based on current zoom level
        updateClusteringForZoom();

        // Clear map markers and trace lines
        if (state.vectorSource) {
            state.vectorSource.clear();
            state.markerFeatures = {};
        }
        if (state.traceSource) {
            state.traceSource.clear();
        }

        // Load all dashboard data (Lakebase mode)
        await loadDashboardData();

        console.log(`Switched to ${source} (backend confirmed: ${data.current})`);

    } catch (error) {
        console.error('Failed to switch data source:', error);

        const errorMsg = error.message || 'Connection failed';
        if (statusLabel) {
            statusLabel.innerHTML = `<i class="bi bi-exclamation-triangle text-danger me-1"></i><span class="text-danger">Error: ${errorMsg}</span>`;
        }
        showDatabaseError(`Data Source Error: ${errorMsg}`);

        // Revert radio button to previous state
        const prevRadio = document.getElementById(`datasource-${state.dataSource}`);
        if (prevRadio) prevRadio.checked = true;

    } finally {
        state.dataSourceSwitching = false;
    }
}

// Clear dashboard UI (stats and client list)
function clearDashboardUI() {
    // Clear stats
    document.getElementById('event-counter').textContent = '0';
    document.getElementById('unique-clients').textContent = '0';
    document.getElementById('data-size').textContent = '0 MB';
}

// Show message prompting user to select a client
function showClientSelectionMessage() {
    const clientListEl = document.getElementById('client-list');
    clientListEl.innerHTML = `
        <div class="client-item" style="flex-direction: column; align-items: flex-start; gap: 0.5rem;">
            <div style="color: #0d6efd; font-weight: 500;">
                <i class="bi bi-info-circle-fill me-2"></i>Select a Client
            </div>
            <div class="client-meta">Choose a client from the dropdown above to view their trace data.</div>
        </div>
    `;
}

// Update cluster distance - 0 disables clustering, >0 enables it
function updateClusterDistance(distance) {
    if (state.clusterSource) {
        state.clusterSource.setDistance(distance);
        console.log(`Cluster distance set to: ${distance}`);
    }
}

// Clustering configuration
const CLUSTERING_CONFIG = {
    lakebase: {
        enabled: true,      // Enable clustering for all-clients overview
        distance: 25,       // Base cluster distance
        disableAtZoom: 19   // Disable clustering at deep zoom levels
    }
};

// Update clustering based on zoom level and view mode
// - Overview mode: clustering ON, disabled at deep zoom (19+)
// - Trace view: clustering always OFF to show full path
function updateClusteringForZoom() {
    if (!state.map) return;

    // Disable clustering in trace mode to show full path as LineString
    if (state.fullTrace && state.selectedClient) {
        updateClusterDistance(0);
        return;
    }

    // Overview mode: zoom-based clustering
    const config = CLUSTERING_CONFIG.lakebase;
    const zoom = state.map.getView().getZoom();
    const distance = zoom >= config.disableAtZoom ? 0 : config.distance;
    updateClusterDistance(distance);
}

// View switch button is now a static link to /zerobus (streaming data view)
// No dynamic updates needed - the button is defined in HTML

// Legacy function for backwards compatibility
async function switchViewMode(mode) {
    // Map old mode names to new data sources
    const source = (mode === 'allclients') ? 'lakebase' : 'zerobus';
    await switchDataSource(source);
}

async function populateClientSelector() {
    const select = document.getElementById('client-trace-select');
    if (!select) return;

    try {
        // Fetch client list
        const response = await fetch('/api/clients');
        if (!response.ok) throw new Error('Failed to load clients');

        const data = await response.json();
        const clients = data.clients || [];

        // Clear existing options
        select.innerHTML = '';

        if (clients.length === 0) {
            select.innerHTML = '<option value="">No clients available</option>';
            return;
        }

        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select a client...';
        select.appendChild(defaultOption);

        // Add client options (already sorted by last_seen DESC from backend)
        clients.forEach(client => {
            const option = document.createElement('option');
            option.value = client.client_id;
            option.textContent = `${client.client_id} (${client.event_count} events)`;
            select.appendChild(option);
        });

    } catch (error) {
        console.error('Failed to populate client selector:', error);
        select.innerHTML = '<option value="">Error loading clients</option>';
    }
}

async function loadClientTrace() {
    const select = document.getElementById('client-trace-select');
    const clientId = select.value;
    const clientListEl = document.getElementById('client-list');

    if (!clientId) {
        // Clear map if no client selected
        if (state.vectorSource) {
            state.vectorSource.clear();
            state.markerFeatures = {};
        }
        // Refresh client list to show selection prompt
        await loadClients();
        return;
    }

    state.selectedClient = clientId;
    state.fullTrace = true; // Always show full trace in trace mode

    // Clear existing markers while loading
    if (state.vectorSource) {
        state.vectorSource.clear();
        state.markerFeatures = {};
    }

    // Load data for this specific client
    await loadDashboardData();
}

// View mode initialization - removed old data source UI functions

// =============================================================================
// Dashboard Initialization
// =============================================================================

async function initializeDashboard() {
    initializeMap();
    setupSettingsListeners();

    // Initialize with Lakebase data source
    // Dashboard always uses Lakebase (PostgreSQL) - shows all clients overview
    // The /zerobus route now serves the streaming data table (separate page)
    const initialSource = 'lakebase';

    // Await data source initialization before starting auto-refresh
    // This prevents race conditions where refresh fires before setup completes
    console.log(`[Dashboard] Initializing with data source: ${initialSource}`);
    await switchDataSource(initialSource, true);

    // Start auto-refresh AFTER data source is fully initialized
    startAutoRefresh();
    console.log('[Dashboard] Initialization complete');
}

function initializeMap() {
    // Create vector source for markers
    state.vectorSource = new ol.source.Vector();

    // Create cluster source for performance with many points
    // Clustering is dynamically adjusted based on zoom level
    state.clusterSource = new ol.source.Cluster({
        distance: 25,  // Default cluster distance (disabled at zoom 19+)
        minDistance: 10,  // Minimum distance between clusters
        source: state.vectorSource
    });

    // Create vector layer with clustering for better performance
    state.vectorLayer = new ol.layer.Vector({
        source: state.clusterSource,
        style: createClusterStyle,
        updateWhileAnimating: true,
        updateWhileInteracting: true
    });

    // Create separate source and layer for trace lines (NOT clustered)
    // Cluster source only handles Point geometries - LineStrings would be dropped
    state.traceSource = new ol.source.Vector();
    state.traceLayer = new ol.layer.Vector({
        source: state.traceSource,
        updateWhileAnimating: true,
        updateWhileInteracting: true
    });

    // Create tile layer - CartoDB Light is lightweight and fast
    state.tileLayer = new ol.layer.Tile({
        source: new ol.source.XYZ({
            url: MAP_LAYERS.light.url,
            crossOrigin: 'anonymous'
        }),
        preload: 4,  // Preload 4 zoom levels for smooth transitions
        useInterimTilesOnError: true
    });

    // Initialize OpenLayers map with optimized smooth interactions
    state.map = new ol.Map({
        target: 'map',
        layers: [
            state.tileLayer,
            state.traceLayer,  // Trace lines layer (below markers)
            state.vectorLayer  // Clustered markers layer (on top)
        ],
        view: new ol.View({
            center: ol.proj.fromLonLat([0, 20]),
            zoom: 2,
            // Allow fractional zoom for smoother pinch-zoom
            constrainResolution: false,
            // Smooth constraints
            smoothExtentConstraint: true,
            smoothResolutionConstraint: true,
            // Max zoom depends on tile provider (default to light layer's max)
            maxZoom: MAP_LAYERS.light.maxZoom,
            minZoom: 2
        }),
        // Disable default controls to prevent overlap with dashboard UI
        controls: ol.control.defaults.defaults({
            attribution: false,
            rotate: false
        }),
        // Optimized smooth interactions
        interactions: ol.interaction.defaults.defaults({
            // Smoother kinetic panning
            kinetic: true
        }).extend([
            new ol.interaction.MouseWheelZoom({
                // Longer duration = smoother zoom animation
                duration: 300,
                useAnchor: true
            }),
            new ol.interaction.PinchZoom({
                // Smooth pinch-zoom on touch devices
                duration: 400
            })
        ]),
        // Reduce pixel ratio for better performance on high-DPI screens
        pixelRatio: 1
    });

    // Listen for zoom changes to update clustering
    // Disable clustering at deep zoom levels (19+) to show individual points
    state.map.getView().on('change:resolution', function() {
        updateClusteringForZoom();
    });

    // Add popup overlay (check if exists to prevent duplicates)
    let popup = document.getElementById('popup');
    if (!popup) {
        popup = document.createElement('div');
        popup.id = 'popup';
        popup.className = 'ol-popup';
        document.body.appendChild(popup);
    }

    const overlay = new ol.Overlay({
        element: popup,
        positioning: 'bottom-center',
        stopEvent: false,
        offset: [0, -10]
    });
    state.map.addOverlay(overlay);

    // Handle click events (cluster-aware)
    // In overview mode: clicking a marker loads the full trace for that client
    state.map.on('click', function(evt) {
        const feature = state.map.forEachFeatureAtPixel(evt.pixel, function(feature) {
            return feature;
        });

        if (feature) {
            const coords = feature.getGeometry().getCoordinates();
            const features = feature.get('features');  // Get clustered features

            if (features && features.length > 1) {
                // Cluster clicked - zoom in to show individual points
                popup.style.display = 'none';

                // Calculate extent of all features in the cluster
                const extent = ol.extent.createEmpty();
                features.forEach(f => {
                    const geom = f.getGeometry();
                    if (geom) {
                        ol.extent.extend(extent, geom.getExtent());
                    }
                });

                // Zoom to fit cluster extent, or zoom in significantly if points overlap
                if (!ol.extent.isEmpty(extent)) {
                    const view = state.map.getView();
                    const currentZoom = view.getZoom();
                    // Zoom in at least 3 levels, or to max zoom
                    const targetZoom = Math.min(currentZoom + 3, view.getMaxZoom());

                    view.animate({
                        center: coords,
                        zoom: targetZoom,
                        duration: 500
                    });
                }
                return;
            } else {
                // Single point clicked
                const originalFeature = features ? features[0] : feature;
                const props = originalFeature.getProperties();
                const clientId = props.uid;

                // In overview mode (not showing a trace), clicking loads the full trace
                if (!state.fullTrace && clientId) {
                    popup.style.display = 'none';
                    selectClient(clientId);
                    return;
                }

                // In trace mode, show popup with details
                popup.innerHTML = `
                    <div class="popup-content">
                        <strong>Device ID:</strong> ${props.uid}<br>
                        <strong>Last Active:</strong> ${formatTimestamp(props.lastTimestamp)}<br>
                        <strong>Status:</strong> ${props.isActive ? '🟢 Active' : '⚪ Inactive'}
                    </div>
                `;
                overlay.setPosition(coords);
                popup.style.display = 'block';
            }
        } else {
            popup.style.display = 'none';
        }
    });

    // Show tooltip on hover (cluster-aware, check if exists to prevent duplicates)
    let tooltip = document.getElementById('map-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'map-tooltip';
        tooltip.className = 'map-tooltip';
        document.body.appendChild(tooltip);
    }

    const tooltipOverlay = new ol.Overlay({
        element: tooltip,
        positioning: 'bottom-center',
        stopEvent: false,
        offset: [0, -15]
    });
    state.map.addOverlay(tooltipOverlay);

    // Throttle pointermove for better performance with many markers
    let hoverTimeout = null;
    state.map.on('pointermove', function(evt) {
        // Cancel pending hover update
        if (hoverTimeout) {
            clearTimeout(hoverTimeout);
        }

        // Throttle to ~60fps for smooth performance
        hoverTimeout = setTimeout(() => {
            const feature = state.map.forEachFeatureAtPixel(evt.pixel, function(f) {
                return f;
            });

            if (feature) {
                state.map.getTargetElement().style.cursor = 'pointer';
                const coords = feature.getGeometry().getCoordinates();
                const features = feature.get('features');

                if (features && features.length > 1) {
                    // Cluster hover - show count
                    tooltip.innerHTML = `<strong>Clustered: ${features.length} Points</strong><br><small>Click to zoom</small>`;
                } else {
                    // Single point hover
                    const originalFeature = features ? features[0] : feature;
                    const props = originalFeature.getProperties();
                    const speed = props.speed != null ? props.speed.toFixed(1) + ' m/s' : 'N/A';
                    const heading = props.heading != null ? props.heading.toFixed(0) + '°' : 'N/A';
                    const pitch = props.pitch != null ? props.pitch.toFixed(1) + '°' : 'N/A';
                    const roll = props.roll != null ? props.roll.toFixed(1) + '°' : 'N/A';
                    tooltip.innerHTML = `
                        <strong>${props.uid}</strong><br>
                        <span class="tooltip-label">Time:</span> ${formatExactTimestamp(props.lastTimestamp)}<br>
                        <span class="tooltip-label">Speed:</span> ${speed} &nbsp; <span class="tooltip-label">Heading:</span> ${heading}<br>
                        <span class="tooltip-label">Pitch:</span> ${pitch} &nbsp; <span class="tooltip-label">Roll:</span> ${roll}
                    `;
                }
                tooltip.style.display = 'block';
                tooltipOverlay.setPosition(coords);
            } else {
                state.map.getTargetElement().style.cursor = '';
                tooltip.style.display = 'none';
                tooltipOverlay.setPosition(undefined);
            }
        }, 16); // ~60fps
    });
}

// Style for clustered points - shows count when multiple points grouped
function createClusterStyle(feature, resolution) {
    const features = feature.get('features');
    const size = features ? features.length : 1;

    // Calculate zoom level from resolution for size scaling
    // At low zoom (world view), markers are 2x bigger for visibility
    const zoom = resolution ? Math.log2(156543.03392 / resolution) : 10;
    const zoomScale = zoom < 8 ? 2 : (zoom < 12 ? 1.5 : 1);

    // Single feature - check if it's a LineString (trace line)
    if (size === 1) {
        const originalFeature = features ? features[0] : feature;
        const geometry = originalFeature.getGeometry();

        // If it's a LineString, use the feature's own style (set via setStyle)
        if (geometry && geometry.getType() === 'LineString') {
            return originalFeature.getStyle();
        }

        return createMarkerStyle(originalFeature, zoomScale);
    }

    // Cluster - show count with scaled circle
    const baseRadius = Math.min(8 + Math.log2(size) * 4, 25);  // Scale with count, max 25px
    const radius = baseRadius * zoomScale;

    return new ol.style.Style({
        image: new ol.style.Circle({
            radius: radius,
            fill: new ol.style.Fill({ color: 'rgba(59, 130, 246, 0.7)' }),  // Blue
            stroke: new ol.style.Stroke({
                color: '#1d4ed8',
                width: 2
            })
        }),
        text: new ol.style.Text({
            text: size.toString(),
            fill: new ol.style.Fill({ color: '#ffffff' }),
            font: `bold ${Math.round(11 * zoomScale)}px sans-serif`
        })
    });
}

// Style cache for marker styles (reduces GC pressure)
// Cache key includes zoom scale for proper sizing at different zoom levels
const markerStyleCache = new Map();

function createMarkerStyle(feature, zoomScale = 1) {
    const isActive = feature.get('isActive');
    const clientColor = feature.get('clientColor') || '#3b82f6';

    // Include zoom scale in cache key for zoom-dependent styling
    const cacheKey = `${isActive}-${clientColor}-${zoomScale}`;
    if (markerStyleCache.has(cacheKey)) {
        return markerStyleCache.get(cacheKey);
    }

    // Always use client color, slightly smaller/faded if inactive
    // Apply zoom scale for larger markers at world view
    const baseRadius = isActive ? 8 : 6;
    const radius = baseRadius * zoomScale;

    // Parse color and apply opacity for inactive
    const fillColor = isActive ? clientColor : clientColor + '99'; // 60% opacity hex

    const style = new ol.style.Style({
        image: new ol.style.Circle({
            radius: radius,
            fill: new ol.style.Fill({ color: fillColor }),
            stroke: new ol.style.Stroke({
                color: clientColor,
                width: (isActive ? 2 : 1) * zoomScale
            })
        })
    });

    markerStyleCache.set(cacheKey, style);
    return style;
}

// Create LineString style for trace view
function createTraceLineStyle(clientColor) {
    return [
        // Main trace line
        new ol.style.Style({
            stroke: new ol.style.Stroke({
                color: clientColor,
                width: 3,
                lineCap: 'round',
                lineJoin: 'round'
            })
        }),
        // Semi-transparent wider line for visibility
        new ol.style.Style({
            stroke: new ol.style.Stroke({
                color: clientColor + '40', // 25% opacity
                width: 8,
                lineCap: 'round',
                lineJoin: 'round'
            })
        })
    ];
}

// =============================================================================
// Data Loading
// =============================================================================

async function loadDashboardData() {
    // Show loading state on stats
    const eventCounter = document.getElementById('event-counter');
    const wasLoading = eventCounter?.classList.contains('loading-pulse');
    if (eventCounter && !wasLoading) {
        eventCounter.classList.add('loading-pulse');
    }

    // Start timing
    const startTime = performance.now();

    try {
        const results = await Promise.allSettled([
            loadEventCount(),
            loadLocations(),
            loadClients(),
            loadStatus()
        ]);

        // Log any failures for debugging
        const labels = ['EventCount', 'Locations', 'Clients', 'Status'];
        results.forEach((result, index) => {
            if (result.status === 'rejected') {
                console.error(`[LoadData] ${labels[index]} failed:`, result.reason);
            }
        });
    } finally {
        // Access time is only shown when loading a single client trace
        // In overview mode, show "--" since we're loading multiple things in parallel
        const accessTimeEl = document.getElementById('access-time');
        if (accessTimeEl && !state.selectedClient) {
            accessTimeEl.textContent = '-- ms';
        }

        // Remove loading state
        if (eventCounter) {
            eventCounter.classList.remove('loading-pulse');
        }
    }
}

async function loadEventCount() {
    try {
        const response = await fetch(CONFIG.apiEndpoints.count);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();

        state.previousCount = state.currentCount;
        state.currentCount = data.count || 0;

        animateCounter(state.previousCount, state.currentCount);
        updateLastUpdateTime();

    } catch (error) {
        console.error('Failed to load event count:', error);
        document.getElementById('event-counter').textContent = 'Error';

        // Show error message if database not connected
        if (error.message.includes('503') || error.message.includes('Service not ready')) {
            showDatabaseError(error.message);
        }
    }
}

async function loadLocations() {
    // PERFORMANCE OPTIMIZATION: Cancel any in-flight location requests
    // This prevents race conditions when rapidly switching between clients
    if (state.locationAbortController) {
        state.locationAbortController.abort();
    }
    state.locationAbortController = new AbortController();

    try {
        let url;

        // Full trace mode: Get all points for selected client (works for both data sources)
        if (state.fullTrace && state.selectedClient) {
            // Pass client_id to backend for efficient server-side filtering
            url = `${CONFIG.apiEndpoints.locations}?full_trace=true&client_id=${encodeURIComponent(state.selectedClient)}`;
        } else {
            // Overview mode: Get latest positions for all clients
            url = CONFIG.apiEndpoints.locations;
        }

        const response = await fetch(url, {
            signal: state.locationAbortController.signal
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        // Locations are now filtered server-side when client_id is passed
        // No need for client-side filtering
        state.locations = data.locations || [];
        state.lastSqlTimeMs = data.sql_time_ms;  // Store SQL execution time
        updateMap();
        updateActiveDevicesCount();

        // Zoom to trace when a client is selected (works for both data sources)
        if (state.fullTrace && state.selectedClient && state.locations.length > 0) {
            zoomToLocations(state.locations, true);
        }

    } catch (error) {
        // Silently ignore aborted requests (user switched to different client)
        if (error.name === 'AbortError') {
            console.log('[LoadLocations] Request cancelled (user switched clients)');
            return;
        }
        console.error('Failed to load locations:', error);
    }
}

async function loadClients() {
    try {
        const response = await fetch('/api/clients');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        state.clients = data.clients || [];
        updateClientList(state.clients);

    } catch (error) {
        console.error('Failed to load clients:', error);
        document.getElementById('client-list').innerHTML = `
            <div class="client-item loading">
                <i class="bi bi-exclamation-circle me-2"></i>
                Failed to load clients: ${error.message}
            </div>`;
    }
}

async function loadStatus() {
    try {
        const response = await fetch('/api/status');

        if (!response.ok) {
            return; // Silent fail for status endpoint
        }

        const data = await response.json();
        state.uniqueClients = data.data?.unique_devices || 0;
        state.dataSizeMB = data.data?.estimated_size_mb || 0;
        state.lastDataTimestamp = data.data?.latest_record?.timestamp || null;

        // Update display
        document.getElementById('unique-clients').textContent = state.uniqueClients;
        document.getElementById('data-size').textContent =
            `${state.dataSizeMB.toFixed(2)} MB`;

        // Update last data timestamp
        if (state.lastDataTimestamp) {
            const lastDataTime = new Date(state.lastDataTimestamp);
            document.getElementById('last-data').textContent =
                lastDataTime.toLocaleTimeString();
        }

    } catch (error) {
        console.error('Failed to load status:', error);
    }
}

// =============================================================================
// UI Updates
// =============================================================================

function animateCounter(from, to) {
    const duration = 1000; // 1 second
    const startTime = performance.now();
    const counterEl = document.getElementById('event-counter');

    function step(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease-out for smoother animation
        const easedProgress = 1 - Math.pow(1 - progress, 3);
        const current = from + (to - from) * easedProgress;

        counterEl.textContent = Math.floor(current).toLocaleString();

        if (progress < 1) {
            requestAnimationFrame(step);
        }
    }

    requestAnimationFrame(step);
}

function getClientColor(clientId) {
    if (!state.clientColors[clientId]) {
        // Generate consistent color for this client
        const colors = [
            '#3b82f6', // blue
            '#10b981', // green
            '#f59e0b', // amber
            '#ef4444', // red
            '#8b5cf6', // purple
            '#ec4899', // pink
            '#14b8a6', // teal
            '#f97316', // orange
        ];
        const index = Object.keys(state.clientColors).length % colors.length;
        state.clientColors[clientId] = colors[index];
    }
    return state.clientColors[clientId];
}

function zoomToLocations(locations, zoomToLast = false) {
    if (!state.map || !locations || locations.length === 0) return;

    if (zoomToLast) {
        // Find the most recent location by timestamp
        let lastLoc = locations[0];
        locations.forEach(loc => {
            if (loc.last_timestamp > lastLoc.last_timestamp) {
                lastLoc = loc;
            }
        });

        if (lastLoc.longitude && lastLoc.latitude) {
            const coord = ol.proj.fromLonLat([lastLoc.longitude, lastLoc.latitude]);
            state.map.getView().animate({
                center: coord,
                zoom: 17,
                duration: 1000
            });
        }
        return;
    }

    // Create extent from all location points
    const extent = ol.extent.createEmpty();
    locations.forEach(loc => {
        if (loc.longitude && loc.latitude) {
            const coord = ol.proj.fromLonLat([loc.longitude, loc.latitude]);
            ol.extent.extend(extent, coord);
        }
    });

    // If extent is valid, fit map to it with padding
    if (!ol.extent.isEmpty(extent)) {
        state.map.getView().fit(extent, {
            padding: [50, 50, 50, 50], // Top, right, bottom, left padding
            maxZoom: 16, // Don't zoom in too much for single points
            duration: 1000 // Smooth animation
        });
    }
}

function updateMap() {
    if (!state.vectorSource) return;

    const now = Date.now();
    const activityThreshold = parseInt(
        document.getElementById('activity-threshold')?.value || 5
    ) * 60 * 1000;

    // PERFORMANCE OPTIMIZATION: Use LineString for trace mode instead of individual points
    // This reduces thousands of Feature objects to just one, dramatically improving render performance
    // Works for BOTH Zerobus and Lakebase when viewing a client trace
    if (state.fullTrace && state.selectedClient && state.locations.length > 0) {
        updateMapWithLineString(now, activityThreshold);
        return;
    }

    // For normal mode (overview): one marker per client showing latest position
    const seenKeys = new Set();

    // Update or add markers for each location
    state.locations.forEach((loc, index) => {
        const lastTimestamp = new Date(loc.last_timestamp).getTime();
        const isActive = (now - lastTimestamp) < activityThreshold;

        // Use client_id as key (one marker per client)
        const markerKey = loc.uid;

        seenKeys.add(markerKey);
        const newCoords = ol.proj.fromLonLat([loc.longitude, loc.latitude]);

        // Check if marker already exists
        if (state.markerFeatures[markerKey]) {
            // Update existing marker (smooth - no flicker)
            const marker = state.markerFeatures[markerKey];
            marker.getGeometry().setCoordinates(newCoords);
            marker.set('lastTimestamp', loc.last_timestamp);
            const wasActive = marker.get('isActive');
            marker.set('isActive', isActive);
            marker.set('speed', loc.speed);
            marker.set('heading', loc.heading);
            marker.set('pitch', loc.orientation_beta);
            marker.set('roll', loc.orientation_gamma);
            // Only trigger style refresh when active status actually changes
            if (wasActive !== isActive) {
                marker.changed();
            }
        } else {
            // Create new marker
            const marker = new ol.Feature({
                geometry: new ol.geom.Point(newCoords),
                uid: loc.uid,
                lastTimestamp: loc.last_timestamp,
                isActive: isActive,
                clientColor: getClientColor(loc.uid),
                speed: loc.speed,
                heading: loc.heading,
                pitch: loc.orientation_beta,
                roll: loc.orientation_gamma
            });
            state.vectorSource.addFeature(marker);
            state.markerFeatures[markerKey] = marker;
        }
    });

    // Remove markers for locations no longer present
    Object.keys(state.markerFeatures).forEach(key => {
        if (!seenKeys.has(key)) {
            state.vectorSource.removeFeature(state.markerFeatures[key]);
            delete state.markerFeatures[key];
        }
    });
}

/**
 * Render trace as individual data points (no connecting line).
 * Shows all location points for the selected client with start/end markers highlighted.
 */
function updateMapWithLineString(now, activityThreshold) {
    // Sort locations by timestamp (oldest first)
    const sortedLocations = [...state.locations].sort((a, b) =>
        new Date(a.last_timestamp) - new Date(b.last_timestamp)
    );

    // Filter valid locations
    const validLocations = sortedLocations.filter(loc => loc.longitude && loc.latitude);

    if (validLocations.length === 0) return;

    const clientColor = getClientColor(state.selectedClient);

    // Clear the trace layer (not used for points-only view)
    state.traceSource.clear();
    state.traceLineFeature = null;

    // Clear old point markers
    Object.keys(state.markerFeatures).forEach(key => {
        state.vectorSource.removeFeature(state.markerFeatures[key]);
    });
    state.markerFeatures = {};

    // Add all points as individual markers
    validLocations.forEach((loc, index) => {
        const coord = ol.proj.fromLonLat([loc.longitude, loc.latitude]);
        const locTimestamp = new Date(loc.last_timestamp).getTime();
        const isActive = (now - locTimestamp) < activityThreshold;

        // Determine marker type for styling
        const isStart = index === 0;
        const isEnd = index === validLocations.length - 1;

        // Use green for start, client color for end, faded for middle points
        let markerColor = clientColor;
        if (isStart) {
            markerColor = '#10b981'; // Green for start
        }

        const marker = new ol.Feature({
            geometry: new ol.geom.Point(coord),
            uid: loc.uid,
            lastTimestamp: loc.last_timestamp,
            isActive: isEnd ? isActive : false, // Only end point shows active status
            clientColor: markerColor,
            speed: loc.speed,
            heading: loc.heading,
            pitch: loc.orientation_beta,
            roll: loc.orientation_gamma,
            markerType: isStart ? 'start' : (isEnd ? 'end' : 'trace')
        });

        state.vectorSource.addFeature(marker);
        state.markerFeatures[`trace_${index}`] = marker;
    });

    console.log(`[Map] Rendered trace with ${validLocations.length} individual points`);
}

function updateClientList(clients) {
    const clientListEl = document.getElementById('client-list');
    const selectPrompt = document.getElementById('client-select-prompt');

    // Always hide the top prompt - we show selection inline now
    if (selectPrompt) {
        selectPrompt.style.display = 'none';
    }

    if (!clients || clients.length === 0) {
        clientListEl.innerHTML = `
            <div class="client-item loading">
                <i class="bi bi-person-x me-2"></i>No clients connected yet
            </div>`;
        return;
    }

    const html = clients.map(client => {
        const statusClass = client.is_active ? 'active' : 'inactive';
        const statusText = client.is_active ? 'Active' : 'Inactive';
        const lastSeen = client.last_seen ? formatTimestamp(client.last_seen) : 'Never';
        const isSelected = state.selectedClient === client.client_id;
        const clientColor = getClientColor(client.client_id);

        // If this client is selected, show the trace indicator instead of normal button
        if (isSelected) {
            return `
                <div class="client-item selected-trace" data-client-id="${client.client_id}" style="border-left: 4px solid ${clientColor};">
                    <div class="trace-indicator">
                        <span class="client-color-dot" style="background-color: ${clientColor};"></span>
                        <span>Showing trace for <strong>${client.client_id}</strong></span>
                    </div>
                </div>
            `;
        }

        // Use button element for proper accessibility and click handling
        return `
            <button type="button"
                    class="client-item selectable"
                    data-client-id="${client.client_id}"
                    aria-pressed="false"
                    style="border-left: 4px solid ${clientColor};">
                <div class="client-info">
                    <div class="client-id-row">
                        <span class="client-color-dot" style="background-color: ${clientColor};"></span>
                        <span class="client-id">${client.client_id}</span>
                    </div>
                    <span class="client-meta">${client.event_count} events • Last: ${lastSeen}</span>
                </div>
                <span class="client-status ${statusClass}">${statusText}</span>
            </button>
        `;
    }).join('');

    clientListEl.innerHTML = html;

    // Add click handlers using event delegation for reliable click handling
    clientListEl.querySelectorAll('.client-item.selectable').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const clientId = this.dataset.clientId;
            if (clientId) {
                selectClient(clientId);
            }
        });
    });
}

// Select a client for trace view (works for both Zerobus and Lakebase)
// PERFORMANCE OPTIMIZATION: Only load locations, not full dashboard data
// This reduces API calls from 4 to 1 when switching clients
async function selectClient(clientId) {
    // Works for both data sources now

    state.selectedClient = clientId;
    state.fullTrace = true;

    // Update client list to show inline selection indicator
    // Find the clicked button and replace it with the trace indicator
    const clickedBtn = document.querySelector(`.client-item.selectable[data-client-id="${clientId}"]`);
    const clientColor = getClientColor(clientId);
    if (clickedBtn) {
        // Replace with loading state first
        clickedBtn.outerHTML = `
            <div class="client-item selected-trace" data-client-id="${clientId}" style="border-left: 4px solid ${clientColor};">
                <div class="trace-indicator">
                    <span class="client-color-dot" style="background-color: ${clientColor};"></span>
                    <span><span class="spinner-border spinner-border-sm me-1"></span>Loading trace for <strong>${clientId}</strong>...</span>
                </div>
            </div>
        `;
    }

    // Show the "Show all traces" button in header
    const showAllBtn = document.getElementById('show-all-traces-btn');
    if (showAllBtn) {
        showAllBtn.style.display = 'inline-block';
    }

    // Clear existing markers and trace line
    if (state.vectorSource) {
        state.vectorSource.clear();
        state.markerFeatures = {};
    }
    if (state.traceSource) {
        state.traceSource.clear();
        state.traceLineFeature = null;
    }

    // Ensure clustering is configured for trace view (disabled)
    updateClusteringForZoom();

    // SELECTIVE LOADING: Only fetch locations for the selected client
    // Don't reload clients list, event count, or status - they don't change
    try {
        await loadLocations();

        // Update access time display (SQL execution time only)
        const accessTimeEl = document.getElementById('access-time');
        if (accessTimeEl) {
            const sqlTime = state.lastSqlTimeMs;
            if (sqlTime !== undefined && sqlTime !== null) {
                accessTimeEl.textContent = `${sqlTime} ms`;
            } else {
                accessTimeEl.textContent = '-- ms';
            }
        }

        // Update the inline indicator to show success (remove spinner)
        const traceItem = document.querySelector(`.client-item.selected-trace[data-client-id="${clientId}"]`);
        if (traceItem) {
            const indicator = traceItem.querySelector('.trace-indicator span');
            if (indicator) {
                indicator.innerHTML = `Showing trace for <strong>${clientId}</strong>`;
            }
        }
    } catch (error) {
        console.error('[SelectClient] Failed to load locations:', error);
        // Show error in the inline indicator
        const traceItem = document.querySelector(`.client-item.selected-trace[data-client-id="${clientId}"]`);
        if (traceItem) {
            const indicator = traceItem.querySelector('.trace-indicator span');
            if (indicator) {
                indicator.innerHTML = `<span class="text-danger">Error loading trace</span>`;
            }
        }
    }
}

// Clear client selection and return to overview mode
async function clearClientSelection() {
    state.selectedClient = null;
    state.fullTrace = false;

    // Clear map (both clustered markers and trace lines)
    if (state.vectorSource) {
        state.vectorSource.clear();
        state.markerFeatures = {};
    }
    if (state.traceSource) {
        state.traceSource.clear();
        state.traceLineFeature = null;
    }

    // Update clustering for overview mode
    updateClusteringForZoom();

    // Hide the "Show all traces" button in header
    const showAllBtn = document.getElementById('show-all-traces-btn');
    if (showAllBtn) {
        showAllBtn.style.display = 'none';
    }

    // Refresh the client list to restore normal buttons
    updateClientList(state.clients);

    // Reload overview data
    await loadLocations();

    // Reset access time in overview mode (only show time for single client trace)
    const accessTimeEl = document.getElementById('access-time');
    if (accessTimeEl) {
        accessTimeEl.textContent = '-- ms';
    }

    // Reset to world view for Lakebase
    if (state.dataSource === 'lakebase' && state.map) {
        state.map.getView().animate({
            center: ol.proj.fromLonLat([0, 20]),
            zoom: 2,
            duration: 500
        });
    }

    console.log('[ClearSelection] Returned to overview mode');
}

function showDatabaseError(message) {
    const errorHtml = `
        <div class="client-item" style="flex-direction: column; align-items: flex-start; gap: 0.25rem;">
            <div style="color: #ef4444; font-weight: 500;">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>Database Connection Error
            </div>
            <div class="client-meta">${message}</div>
            <div class="client-meta">Check backend logs and database configuration.</div>
        </div>
    `;

    document.getElementById('client-list').innerHTML = errorHtml;
}

function updateActiveDevicesCount() {
    // This function is kept for compatibility but the active devices
    // count is now displayed via the unique-clients stat box from /api/status
}

function updateLastUpdateTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
    const displayEl = document.getElementById('display-updated');
    if (displayEl) {
        displayEl.textContent = timeStr;
        // Brief flash to indicate refresh occurred
        displayEl.classList.add('refresh-flash');
        setTimeout(() => displayEl.classList.remove('refresh-flash'), 300);
    }
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;

    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatExactTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

// =============================================================================
// Auto Refresh
// =============================================================================

function startAutoRefresh() {
    stopAutoRefresh(); // Clear any existing timer

    const intervalSeconds = parseInt(
        document.getElementById('refresh-interval')?.value || 5
    );
    const interval = intervalSeconds * 1000;

    console.log(`[AutoRefresh] Starting auto-refresh with ${intervalSeconds}s interval`);

    state.refreshTimer = setInterval(async () => {
        if (state.currentPage === 'dashboard') {
            // Skip refresh if a data source switch is in progress
            if (state.dataSourceSwitching) {
                console.log('[AutoRefresh] Skipping refresh - data source switch in progress');
                return;
            }
            console.log(`[AutoRefresh] Refreshing data (source: ${state.dataSource})`);
            try {
                await loadDashboardData();
                console.log('[AutoRefresh] Refresh completed successfully');
            } catch (error) {
                console.error('[AutoRefresh] Refresh failed:', error);
            }
        }
    }, interval);

    console.log(`[AutoRefresh] Timer started with ID: ${state.refreshTimer}`);
}

function stopAutoRefresh() {
    if (state.refreshTimer) {
        console.log(`[AutoRefresh] Stopping timer ID: ${state.refreshTimer}`);
        clearInterval(state.refreshTimer);
        state.refreshTimer = null;
    }
}

function setupSettingsListeners() {
    const refreshInput = document.getElementById('refresh-interval');
    const activityInput = document.getElementById('activity-threshold');

    refreshInput?.addEventListener('change', () => {
        CONFIG.refreshInterval = parseInt(refreshInput.value) * 1000;
        safeSetItem('refreshInterval', refreshInput.value);
        startAutoRefresh();
    });

    activityInput?.addEventListener('change', () => {
        safeSetItem('activityThreshold', activityInput.value);
        updateMap();
    });

    // Load saved settings
    const savedRefresh = safeGetItem('refreshInterval');
    const savedActivity = safeGetItem('activityThreshold');
    const savedFullTrace = safeGetItem('fullTrace');

    if (savedRefresh) refreshInput.value = savedRefresh;
    if (savedActivity) activityInput.value = savedActivity;

    // Initialize fullTrace state from localStorage
    if (savedFullTrace !== null) {
        state.fullTrace = savedFullTrace === 'true';
    }
    const traceCheckbox = document.getElementById('full-trace-toggle');
    if (traceCheckbox) {
        traceCheckbox.checked = state.fullTrace;
    }
    const traceTextEl = document.getElementById('full-trace-text');
    if (traceTextEl) {
        traceTextEl.textContent = state.fullTrace ? 'Full trace ON' : 'Full trace OFF';
    }

    // Initialize map layer from localStorage
    const savedMapLayer = safeGetItem('mapLayer');
    if (savedMapLayer && MAP_LAYERS[savedMapLayer]) {
        const mapSelect = document.getElementById('map-layer-select');
        if (mapSelect) {
            mapSelect.value = savedMapLayer;
            changeMapLayer();
        }
    }
}

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Set frontend URL on the button
    const frontendLink = document.getElementById('frontend-link');
    if (frontendLink) {
        frontendLink.href = CONFIG.frontendUrl;
    }

    // Check URL path to determine initial page
    const path = window.location.pathname;
    if (path === '/lakebase') {
        // Direct link to dashboard - go straight there
        navigateTo('dashboard');
    } else {
        // Root or unknown path - show landing page
        navigateTo('landing');
    }
});

// Handle browser back/forward buttons
// Dashboard always uses Lakebase, so no data source switching needed
window.addEventListener('popstate', function(event) {
    // Just reload the dashboard if needed
    if (state.currentPage === 'dashboard' && !state.dataSource) {
        switchDataSource('lakebase', true);
    }
});

// Cleanup on page unload - properly dispose map and overlays
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();

    // Properly dispose OpenLayers map to prevent memory leaks
    if (state.map) {
        // Remove all overlays
        state.map.getOverlays().clear();

        // Dispose the map (removes event listeners and cleans up)
        state.map.setTarget(null);
        state.map = null;
    }

    // Clear vector sources
    if (state.vectorSource) {
        state.vectorSource.clear();
        state.vectorSource = null;
    }
    if (state.traceSource) {
        state.traceSource.clear();
        state.traceSource = null;
    }

    // Clear marker tracking
    state.markerFeatures = {};
    state.clientColors = {};

    // Remove dynamically created DOM elements
    const popup = document.getElementById('popup');
    const tooltip = document.getElementById('map-tooltip');
    if (popup) popup.remove();
    if (tooltip) tooltip.remove();
});
