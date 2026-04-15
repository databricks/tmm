/**
 * ZeroStream Main Application
 *
 * Vue 3 app for mobile sensor data collection and streaming
 */

const { createApp } = Vue;

const app = createApp({
    data() {
        return {
            // Client ID
            clientId: UIDGenerator.getClientUID(),

            // Permissions state
            permissionsGranted: false,

            // Sensor state
            sensorsActive: false,

            // Config
            showConfig: false,
            frequency: 1,              // Default: 1 Hz (once per second)
            displayMode: 'combined',   // Default display mode
            alternateDisplaysEnabled: true,   // Show mode toggle button
            theme: 'dark',             // Default theme (dark/light)

            // Data transmission indicator
            dataSent: false,

            // Page navigation (0 = sensors, 1 = stats)
            currentPage: 0,

            // Event counter (updated from ZeroBusService)
            eventCount: 0,
            eventCountInterval: null,

            // Sensor data
            sensorData: {
                acceleration: { x: 0, y: 0, z: 0 },
                accelerationIncludingGravity: { x: 0, y: 0, z: 0 },
                rotationRate: { alpha: 0, beta: 0, gamma: 0 },
                orientation: { alpha: 0, beta: 0, gamma: 0 },
                location: {
                    latitude: 0,
                    longitude: 0,
                    altitude: 0,
                    accuracy: 0,
                    altitudeAccuracy: 0,
                    speed: 0,
                    heading: 0
                },
                magnetometer: { x: 0, y: 0, z: 0 },
                timestamp: null
            }
        };
    },

    created() {
        console.log('[App] Vue app created, initializing...');

        // Load saved theme first (apply immediately to prevent flash)
        const savedTheme = localStorage.getItem('zerostream_theme');
        if (savedTheme && ['dark', 'light'].includes(savedTheme)) {
            this.theme = savedTheme;
        }
        this.applyTheme(this.theme);

        // Load saved settings
        const savedFrequency = localStorage.getItem('zerostream_frequency');
        if (savedFrequency) {
            this.frequency = parseInt(savedFrequency, 10);
        }

        const savedAlternateDisplays = localStorage.getItem('zerostream_alternate_displays');
        if (savedAlternateDisplays) {
            this.alternateDisplaysEnabled = savedAlternateDisplays === 'true';
        }

        // Only load display mode if alternate displays are enabled
        if (this.alternateDisplaysEnabled) {
            const savedDisplayMode = localStorage.getItem('zerostream_display_mode');
            if (savedDisplayMode && ['combined', 'numerical', 'graphical'].includes(savedDisplayMode)) {
                this.displayMode = savedDisplayMode;
            } else {
                this.displayMode = 'combined';  // Default if invalid
            }
        } else {
            this.displayMode = 'combined';  // Force combined mode
        }

        console.log('[App] State:', {
            displayMode: this.displayMode,
            currentPage: this.currentPage,
            alternateDisplaysEnabled: this.alternateDisplaysEnabled
        });

        // Initialize ZeroBus service with data sent callback
        ZeroBusService.init({
            batchSize: 10,
            enabled: true,
            onDataSent: () => {
                this.flashDataIndicator();
            }
        });

        // Set initial frequency in sensor service
        SensorService.setFrequency(this.frequency);

        // Check if permissions are already granted (from previous session)
        this.checkExistingPermissions();

        // Start polling event count for stats display
        this.eventCountInterval = setInterval(() => {
            this.eventCount = ZeroBusService.stats.totalSent;
        }, 100);  // Update every 100ms for smooth animation
    },

    methods: {
        async checkExistingPermissions() {
            // Check if we already have permissions from a previous session
            //
            // IMPORTANT: On iOS 13+, DeviceMotionEvent.requestPermission() MUST be called
            // from a user gesture (click/tap) on EVERY page load. localStorage cannot
            // be used to skip this - the browser requires fresh user interaction each session.

            let hasMotion = false;
            let hasLocation = false;
            let requiresUserGesture = false;

            // Check motion permission (iOS 13+ has a permission API)
            if (typeof DeviceMotionEvent !== 'undefined') {
                if (typeof DeviceMotionEvent.requestPermission === 'function') {
                    // iOS 13+ - ALWAYS requires user gesture to request permission
                    // Cannot auto-grant based on localStorage - must show permission dialog
                    requiresUserGesture = true;
                    hasMotion = false;  // Force showing permission dialog
                    console.log('[App] iOS detected - motion permission requires user gesture each session');
                } else {
                    // Non-iOS or older browsers - motion is always available
                    hasMotion = true;
                }
            }

            // Check location permission by trying to get position
            if ('geolocation' in navigator && 'permissions' in navigator) {
                try {
                    const result = await navigator.permissions.query({ name: 'geolocation' });
                    hasLocation = result.state === 'granted';
                } catch (e) {
                    // Permissions API not supported, check localStorage
                    hasLocation = localStorage.getItem('zerostream_location_granted') === 'true';
                }
            }

            // On iOS, always show permission dialog (motion requires user gesture)
            // On other platforms, auto-start if we have at least one permission
            if (requiresUserGesture) {
                console.log('[App] Showing permission dialog (iOS requires user gesture for motion sensors)');
                this.permissionsGranted = false;
            } else if (hasMotion || hasLocation) {
                console.log('[App] Existing permissions detected, auto-starting sensors');
                this.permissionsGranted = true;
                this.$nextTick(() => {
                    this.startSensors();
                });
            } else {
                console.log('[App] No existing permissions, waiting for user to grant access');
            }
        },

        onPermissionsGranted(results) {
            console.log('[App] Permissions granted:', results);
            this.permissionsGranted = true;

            // Save permission state for next session
            if (results.motion) {
                localStorage.setItem('zerostream_motion_granted', 'true');
            }
            if (results.location) {
                localStorage.setItem('zerostream_location_granted', 'true');
            }

            // Auto-start sensors after permission granted
            this.$nextTick(() => {
                this.startSensors();
            });
        },

        toggleSensors() {
            if (this.sensorsActive) {
                this.stopSensors();
            } else {
                this.startSensors();
            }
        },

        startSensors() {
            SensorService.start(
                // onData callback (display updates at 10Hz)
                (data) => {
                    this.sensorData = data;
                },
                // onError callback
                (type, error) => {
                    console.error(`[App] Sensor error (${type}):`, error);
                }
            );
            this.sensorsActive = true;
        },

        flashDataIndicator() {
            this.dataSent = true;
            setTimeout(() => {
                this.dataSent = false;
            }, 150);  // Longer flash for better visibility at 1 Hz
        },

        stopSensors() {
            SensorService.stop();
            this.sensorsActive = false;

            // Flush any remaining data
            ZeroBusService.flush();
        },

        updateFrequency(newFrequency) {
            this.frequency = newFrequency;
            SensorService.setFrequency(newFrequency);
            localStorage.setItem('zerostream_frequency', newFrequency.toString());
            console.log(`[App] Frequency updated to ${newFrequency} Hz`);
        },

        updateDisplayMode(mode) {
            this.displayMode = mode;
            localStorage.setItem('zerostream_display_mode', mode);
            console.log(`[App] Display mode updated to ${mode}`);
        },

        updateTheme(newTheme) {
            this.theme = newTheme;
            this.applyTheme(newTheme);
            localStorage.setItem('zerostream_theme', newTheme);
            console.log(`[App] Theme updated to ${newTheme}`);
        },

        applyTheme(theme) {
            // Apply theme to document root for CSS variable switching
            if (theme === 'light') {
                document.documentElement.setAttribute('data-theme', 'light');
            } else {
                document.documentElement.removeAttribute('data-theme');
            }
        },

        toggleDisplayMode() {
            console.log('[App] toggleDisplayMode called, current:', this.displayMode);
            const modes = ['combined', 'numerical', 'graphical'];
            const currentIndex = modes.indexOf(this.displayMode);
            const newMode = modes[(currentIndex + 1) % modes.length];
            this.updateDisplayMode(newMode);
        },

        // Page navigation
        setPage(pageIndex) {
            console.log('[App] setPage called:', pageIndex);
            this.currentPage = pageIndex;
        },

        nextPage() {
            console.log('[App] nextPage called, current:', this.currentPage);
            this.currentPage = (this.currentPage + 1) % 2;
            console.log('[App] nextPage new page:', this.currentPage);
        },

        prevPage() {
            this.currentPage = (this.currentPage - 1 + 2) % 2;
        },

        onRegenerateClientId(newId) {
            console.log(`[App] Client ID regenerated: ${newId}`);
            this.clientId = newId;
            // Update the sensor service with new client ID
            SensorService.setClientId(newId);
        }
    },

    beforeUnmount() {
        // Cleanup
        if (this.sensorsActive) {
            SensorService.stop();
        }
        if (this.eventCountInterval) {
            clearInterval(this.eventCountInterval);
        }
    }
});

// Register components
app.component('permission-request', PermissionRequest);
app.component('sensor-display', SensorDisplay);
app.component('graphical-display', GraphicalDisplay);
app.component('combined-display', CombinedDisplay);
app.component('mini-map', MiniMap);
app.component('config-panel', ConfigPanel);
app.component('stats-display', StatsDisplay);

// Mount app
app.mount('#app');
