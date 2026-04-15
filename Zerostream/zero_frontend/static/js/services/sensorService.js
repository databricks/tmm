/**
 * Sensor Service
 *
 * Handles all device sensor interactions including:
 * - Accelerometer
 * - Gyroscope
 * - Magnetometer
 * - GPS Location
 * - Device Orientation
 */

const SensorService = {
    // Sensor state
    state: {
        active: false,
        permissions: {
            motion: false,
            location: false
        }
    },

    // Configuration
    config: {
        dataFrequency: 1,      // Data sending frequency (1 = every 1s, 0.2 = every 5s)
        displayFrequency: 10,  // Display updates per second (fixed at 10 for smooth compass/roll/pitch)
        numbersFrequency: 2,   // Number updates per second (fixed at 2Hz)
        get dataInterval() {
            return 1000 / this.dataFrequency;
        },
        get displayInterval() {
            return 1000 / this.displayFrequency;
        },
        get numbersInterval() {
            return 1000 / this.numbersFrequency;
        }
    },

    // Callbacks
    callbacks: {
        onData: null,
        onError: null
    },

    // Interval handles
    intervals: {
        accelerometer: null,
        location: null,
        displayUpdate: null,
        numbersUpdate: null,
        dataCollection: null
    },

    // Watch IDs
    watchIds: {
        location: null
    },

    // Current sensor readings
    currentData: {
        acceleration: { x: 0, y: 0, z: 0 },
        accelerationIncludingGravity: { x: 0, y: 0, z: 0 },
        rotationRate: { alpha: 0, beta: 0, gamma: 0 },
        orientation: { alpha: 0, beta: 0, gamma: 0 },
        location: { latitude: 0, longitude: 0, altitude: 0, accuracy: 0, speed: 0, heading: 0 },
        magnetometer: { x: 0, y: 0, z: 0 },
        timestamp: null
    },

    /**
     * Set the data collection frequency
     * @param {number} freq - Frequency in Hz: 1 = every 1s, 0.1 = every 10s, 1/60 = every minute
     */
    setFrequency(freq) {
        // Validate frequency (allow 1Hz, 0.1Hz, or ~1/60Hz)
        const validFrequencies = [1, 0.1];
        const isMinuteFreq = freq < 0.02 && freq > 0.01;  // approximately 1/60

        if (validFrequencies.includes(freq) || isMinuteFreq) {
            this.config.dataFrequency = freq;

            let intervalStr;
            if (freq === 1) intervalStr = '1 second';
            else if (freq === 0.1) intervalStr = '10 seconds';
            else if (isMinuteFreq) intervalStr = '1 minute';
            else intervalStr = `${Math.round(1/freq)} seconds`;

            console.log(`[SensorService] Data sending set to every ${intervalStr}`);

            // Restart data collection if active
            if (this.state.active) {
                this.restartDataCollection();
            }
        } else {
            console.warn(`[SensorService] Invalid frequency: ${freq}. Use 1 (every 1s), 0.1 (every 10s), or 1/60 (every minute)`);
        }
    },

    /**
     * Get current data frequency
     */
    getFrequency() {
        return this.config.dataFrequency;
    },

    /**
     * Set the client ID (used when regenerating)
     * Note: New ID is automatically picked up from UIDGenerator on next data collection
     * @param {string} clientId - New client ID
     */
    setClientId(clientId) {
        console.log(`[SensorService] Client ID updated to: ${clientId}`);
        // The new client ID will be automatically used on next data collection
        // since collectAndSendData() calls UIDGenerator.getClientUID() each time
    },

    /**
     * Request permissions for sensors
     * @returns {Promise<Object>} Permission results
     */
    async requestPermissions() {
        const results = {
            motion: false,
            location: false
        };

        // Request motion permissions (iOS 13+)
        if (typeof DeviceMotionEvent !== 'undefined' &&
            typeof DeviceMotionEvent.requestPermission === 'function') {
            try {
                const permission = await DeviceMotionEvent.requestPermission();
                results.motion = permission === 'granted';
            } catch (error) {
                console.error('[SensorService] Motion permission error:', error);
            }
        } else {
            // Non-iOS or older browsers - assume granted
            results.motion = true;
        }

        // Request location permissions
        if ('geolocation' in navigator) {
            try {
                await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(
                        () => {
                            results.location = true;
                            resolve();
                        },
                        (error) => {
                            console.error('[SensorService] Location permission error:', error);
                            reject(error);
                        },
                        { enableHighAccuracy: true, timeout: 10000 }
                    );
                });
            } catch (error) {
                results.location = false;
            }
        }

        this.state.permissions = results;
        return results;
    },

    /**
     * Start collecting sensor data
     * @param {Function} onData - Callback for sensor data updates
     * @param {Function} onError - Callback for errors
     */
    start(onData, onError) {
        if (this.state.active) return;

        this.callbacks.onData = onData;
        this.callbacks.onError = onError;
        this.state.active = true;

        // Start motion sensors
        this.startMotionSensors();

        // Start location tracking
        this.startLocationTracking();

        // Start display updates (10 Hz for compass, 5 Hz for numbers)
        this.startDisplayUpdates();

        // Start data collection (configurable frequency)
        this.startDataCollection();

        console.log('[SensorService] Started');
    },

    /**
     * Stop collecting sensor data
     */
    stop() {
        if (!this.state.active) return;

        this.state.active = false;

        // Stop motion sensors
        window.removeEventListener('devicemotion', this.handleMotion);
        window.removeEventListener('deviceorientation', this.handleOrientation);

        // Stop location tracking
        if (this.watchIds.location) {
            navigator.geolocation.clearWatch(this.watchIds.location);
            this.watchIds.location = null;
        }

        // Clear intervals
        if (this.intervals.displayUpdate) {
            clearInterval(this.intervals.displayUpdate);
            this.intervals.displayUpdate = null;
        }
        if (this.intervals.numbersUpdate) {
            clearInterval(this.intervals.numbersUpdate);
            this.intervals.numbersUpdate = null;
        }
        if (this.intervals.dataCollection) {
            clearInterval(this.intervals.dataCollection);
            this.intervals.dataCollection = null;
        }

        console.log('[SensorService] Stopped');
    },

    /**
     * Start motion sensors (accelerometer, gyroscope)
     */
    startMotionSensors() {
        // Device Motion (accelerometer + gyroscope)
        this.handleMotion = (event) => {
            if (event.acceleration) {
                this.currentData.acceleration = {
                    x: event.acceleration.x || 0,
                    y: event.acceleration.y || 0,
                    z: event.acceleration.z || 0
                };
            }

            if (event.accelerationIncludingGravity) {
                this.currentData.accelerationIncludingGravity = {
                    x: event.accelerationIncludingGravity.x || 0,
                    y: event.accelerationIncludingGravity.y || 0,
                    z: event.accelerationIncludingGravity.z || 0
                };
            }

            if (event.rotationRate) {
                this.currentData.rotationRate = {
                    alpha: event.rotationRate.alpha || 0,
                    beta: event.rotationRate.beta || 0,
                    gamma: event.rotationRate.gamma || 0
                };
            }
        };

        // Device Orientation (compass/magnetometer direction)
        this.handleOrientation = (event) => {
            this.currentData.orientation = {
                alpha: event.alpha || 0,  // Z-axis rotation (compass)
                beta: event.beta || 0,    // X-axis rotation (front-back tilt)
                gamma: event.gamma || 0   // Y-axis rotation (left-right tilt)
            };

            // Approximate magnetometer from compass heading
            if (event.webkitCompassHeading !== undefined) {
                this.currentData.magnetometer.heading = event.webkitCompassHeading;
            }
        };

        window.addEventListener('devicemotion', this.handleMotion);
        window.addEventListener('deviceorientation', this.handleOrientation);
    },

    /**
     * Start GPS location tracking
     */
    startLocationTracking() {
        if (!('geolocation' in navigator)) {
            console.warn('[SensorService] Geolocation not available');
            return;
        }

        const options = {
            enableHighAccuracy: true,
            maximumAge: 0,
            timeout: 5000
        };

        this.watchIds.location = navigator.geolocation.watchPosition(
            (position) => {
                // GPS heading is null when stationary - use compass heading as fallback
                // Use the same orientation.alpha that's displayed on the compass gauge
                let heading = position.coords.heading;
                if (heading === null || heading === undefined) {
                    // Use compass heading: webkitCompassHeading (iOS) or orientation.alpha
                    // This matches what's displayed in the heading gauge
                    heading = this.currentData.magnetometer?.heading ??
                              this.currentData.orientation?.alpha ?? 0;
                }

                this.currentData.location = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    altitude: position.coords.altitude || 0,
                    accuracy: position.coords.accuracy || 0,
                    altitudeAccuracy: position.coords.altitudeAccuracy || 0,
                    speed: position.coords.speed || 0,
                    heading: heading
                };
            },
            (error) => {
                console.error('[SensorService] Location error:', error);
                if (this.callbacks.onError) {
                    this.callbacks.onError('location', error);
                }
            },
            options
        );
    },

    /**
     * Start display updates (10 Hz for smooth compass/roll/pitch, 2 Hz for numbers)
     */
    startDisplayUpdates() {
        // Counter for number updates (update every 5th frame for 2Hz)
        let frameCount = 0;

        // 10 Hz updates for smooth compass/roll/pitch rotation
        this.intervals.displayUpdate = setInterval(() => {
            if (!this.state.active) return;

            frameCount++;

            // Create deep copy of data to ensure Vue reactivity triggers properly
            // Shallow copies with spread don't trigger Vue watchers reliably
            const dataPacket = {
                acceleration: { ...this.currentData.acceleration },
                accelerationIncludingGravity: { ...this.currentData.accelerationIncludingGravity },
                rotationRate: { ...this.currentData.rotationRate },
                orientation: { ...this.currentData.orientation },
                location: { ...this.currentData.location },
                magnetometer: { ...this.currentData.magnetometer },
                timestamp: this.currentData.timestamp,
                updateNumbers: (frameCount % 5 === 0)  // Update numbers every 5th frame (2 Hz)
            };

            // Update display with current sensor values
            if (this.callbacks.onData) {
                this.callbacks.onData(dataPacket);
            }
        }, this.config.displayInterval);
    },

    /**
     * Start data collection at configured frequency
     */
    startDataCollection() {
        this.intervals.dataCollection = setInterval(() => {
            if (!this.state.active) return;

            // Prepare data packet with proper field names (camelCase for Python API)
            // Always use orientation.alpha - this is exactly what's displayed on the compass gauge
            const compassHeading = this.currentData.orientation?.alpha ?? 0;

            const dataPacket = {
                clientId: window.UIDGenerator ? window.UIDGenerator.getClientUID() : 'unknown',
                timestamp: new Date().toISOString(),
                acceleration: this.currentData.acceleration,
                accelerationIncludingGravity: this.currentData.accelerationIncludingGravity,
                rotationRate: this.currentData.rotationRate,
                orientation: this.currentData.orientation,
                location: {
                    ...this.currentData.location,
                    heading: compassHeading  // Always use compass heading, not GPS heading
                },
                // Ensure magnetometer is either null or proper Vector3D format
                magnetometer: this.currentData.magnetometer &&
                             (this.currentData.magnetometer.x !== undefined ||
                              this.currentData.magnetometer.y !== undefined ||
                              this.currentData.magnetometer.z !== undefined)
                             ? {
                                 x: this.currentData.magnetometer.x || 0,
                                 y: this.currentData.magnetometer.y || 0,
                                 z: this.currentData.magnetometer.z || 0
                               }
                             : null
            };

            // Send to ZeroBus
            if (window.ZeroBusService) {
                ZeroBusService.sendData(dataPacket);
            }
        }, this.config.dataInterval);
    },

    /**
     * Restart data collection (when frequency changes)
     */
    restartDataCollection() {
        if (this.intervals.dataCollection) {
            clearInterval(this.intervals.dataCollection);
        }
        this.startDataCollection();
    },


    /**
     * Check if sensors are available
     * @returns {Object} Availability status
     */
    checkAvailability() {
        return {
            deviceMotion: 'DeviceMotionEvent' in window,
            deviceOrientation: 'DeviceOrientationEvent' in window,
            geolocation: 'geolocation' in navigator,
            accelerometer: 'Accelerometer' in window,
            gyroscope: 'Gyroscope' in window,
            magnetometer: 'Magnetometer' in window
        };
    }
};

// Export for use in other modules
window.SensorService = SensorService;
