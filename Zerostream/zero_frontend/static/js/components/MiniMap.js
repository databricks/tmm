/**
 * Mini Map Component
 *
 * Displays GPS location on an interactive Leaflet map
 * Zoomed to continent level showing ~1/3 of world
 */

const MiniMap = {
    name: 'MiniMap',

    props: {
        latitude: {
            type: Number,
            default: 0
        },
        longitude: {
            type: Number,
            default: 0
        },
        accuracy: {
            type: Number,
            default: 0
        },
        altitude: {
            type: Number,
            default: 0
        }
    },

    data() {
        return {
            map: null,
            marker: null,
            accuracyCircle: null,
            tileLayer: null,
            initialized: false,
            defaultZoom: 4  // Continent level zoom
        };
    },

    template: `
        <div class="mini-map">
            <h3 class="map-header-dynamic">{{ locationHeader }}</h3>
            <div class="map-container" ref="mapContainer">
                <div v-if="!hasLocation" class="map-placeholder">
                    Waiting for GPS signal...
                </div>
            </div>
        </div>
    `,

    computed: {
        hasLocation() {
            return this.latitude !== 0 || this.longitude !== 0;
        },
        locationHeader() {
            if (!this.hasLocation) return 'Location';
            const lat = this.latitude.toFixed(2);
            const lng = this.longitude.toFixed(2);
            const alt = this.altitude ? Math.round(this.altitude) + 'm' : '--';
            const acc = this.accuracy ? Math.round(this.accuracy) + 'm' : '--';
            return `Lat ${lat}, Lon ${lng} | ALT ${alt} | ACC ${acc}`;
        }
    },

    watch: {
        latitude() {
            this.updateMap();
        },
        longitude() {
            this.updateMap();
        },
        accuracy() {
            this.updateAccuracyCircle();
        }
    },

    mounted() {
        this.$nextTick(() => {
            if (this.hasLocation) {
                this.initMap();
            }
        });

        // Watch for theme changes
        this.themeObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    this.updateTileLayer();
                }
            });
        });
        this.themeObserver.observe(document.documentElement, { attributes: true });
    },

    beforeUnmount() {
        if (this.themeObserver) {
            this.themeObserver.disconnect();
            this.themeObserver = null;
        }
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    },

    methods: {
        initMap() {
            if (this.initialized || !this.$refs.mapContainer) return;

            // Create map at continent zoom level
            this.map = L.map(this.$refs.mapContainer, {
                zoomControl: false,
                attributionControl: false
            }).setView([this.latitude, this.longitude], this.defaultZoom);

            // Add tile layer based on current theme
            const isLightMode = document.documentElement.getAttribute('data-theme') === 'light';
            const tileUrl = isLightMode
                ? 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
                : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

            this.tileLayer = L.tileLayer(tileUrl, {
                maxZoom: 19,
                minZoom: 2
            }).addTo(this.map);

            // Create pulsing marker
            const icon = L.divIcon({
                className: 'custom-marker',
                html: `
                    <div style="position:relative;">
                        <div style="
                            width: 20px;
                            height: 20px;
                            background: #FF6F00;
                            border: 3px solid white;
                            border-radius: 50%;
                            box-shadow: 0 2px 8px rgba(255,111,0,0.6);
                            position: relative;
                            z-index: 2;
                        "></div>
                        <div style="
                            position: absolute;
                            top: 50%;
                            left: 50%;
                            transform: translate(-50%, -50%);
                            width: 40px;
                            height: 40px;
                            background: rgba(255,111,0,0.3);
                            border-radius: 50%;
                            animation: markerPulse 2s infinite;
                        "></div>
                    </div>
                    <style>
                        @keyframes markerPulse {
                            0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
                            50% { transform: translate(-50%, -50%) scale(1.5); opacity: 0.5; }
                        }
                    </style>
                `,
                iconSize: [40, 40],
                iconAnchor: [20, 20]
            });

            this.marker = L.marker([this.latitude, this.longitude], { icon }).addTo(this.map);

            // Add accuracy circle if available
            if (this.accuracy > 0) {
                this.accuracyCircle = L.circle([this.latitude, this.longitude], {
                    radius: Math.max(this.accuracy, 1000), // Minimum visible radius
                    color: '#FF6F00',
                    fillColor: '#FF6F00',
                    fillOpacity: 0.1,
                    weight: 2,
                    dashArray: '5, 5'
                }).addTo(this.map);
            }

            this.initialized = true;
        },

        updateMap() {
            if (!this.hasLocation) return;

            if (!this.initialized) {
                this.initMap();
                return;
            }

            if (this.marker && this.map) {
                const newLatLng = [this.latitude, this.longitude];
                this.marker.setLatLng(newLatLng);

                // Smoothly pan to new location
                this.map.panTo(newLatLng, {
                    animate: true,
                    duration: 0.5
                });

                if (this.accuracyCircle) {
                    this.accuracyCircle.setLatLng(newLatLng);
                }
            }
        },

        updateAccuracyCircle() {
            if (!this.initialized) return;

            if (this.accuracy > 0) {
                const radius = Math.max(this.accuracy, 1000);
                if (this.accuracyCircle) {
                    this.accuracyCircle.setRadius(radius);
                } else {
                    this.accuracyCircle = L.circle([this.latitude, this.longitude], {
                        radius: radius,
                        color: '#FF6F00',
                        fillColor: '#FF6F00',
                        fillOpacity: 0.1,
                        weight: 2,
                        dashArray: '5, 5'
                    }).addTo(this.map);
                }
            }
        },

        updateTileLayer() {
            if (!this.initialized || !this.map || !this.tileLayer) return;

            const isLightMode = document.documentElement.getAttribute('data-theme') === 'light';
            const tileUrl = isLightMode
                ? 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
                : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

            // Remove old tile layer and add new one
            this.map.removeLayer(this.tileLayer);
            this.tileLayer = L.tileLayer(tileUrl, {
                maxZoom: 19,
                minZoom: 2
            }).addTo(this.map);
        }
    }
};

// Register component globally
window.MiniMap = MiniMap;
