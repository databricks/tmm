/**
 * Sensor Display Component
 *
 * Displays all sensor data in a condensed single-row layout
 */

const SensorDisplay = {
    name: 'SensorDisplay',

    props: {
        sensorData: {
            type: Object,
            required: true
        },
        active: {
            type: Boolean,
            default: false
        }
    },

    template: `
        <div :class="['sensor-display', { inactive: !active }]">
            <!-- Device Orientation - PRIMARY -->
            <div class="sensor-section prominent">
                <h3>Orientation</h3>
                <div class="sensor-grid orientation-grid">
                    <div class="sensor-value large">
                        <div class="label">Pitch</div>
                        <div class="value">{{ formatValue(sensorData.orientation.beta, 1) }}°</div>
                    </div>
                    <div class="sensor-value large">
                        <div class="label">Roll</div>
                        <div class="value">{{ formatValue(sensorData.orientation.gamma, 1) }}°</div>
                    </div>
                    <div class="sensor-value large">
                        <div class="label">Heading</div>
                        <div class="value">{{ formatValue(sensorData.orientation.alpha, 0) }}°</div>
                    </div>
                </div>
            </div>

            <!-- Acceleration -->
            <div class="sensor-section">
                <h3>Acceleration (m/s²)</h3>
                <div class="sensor-grid">
                    <div class="sensor-value">
                        <div class="label">X</div>
                        <div class="value">{{ formatValue(sensorData.acceleration.x) }}</div>
                    </div>
                    <div class="sensor-value">
                        <div class="label">Y</div>
                        <div class="value">{{ formatValue(sensorData.acceleration.y) }}</div>
                    </div>
                    <div class="sensor-value">
                        <div class="label">Z</div>
                        <div class="value">{{ formatValue(sensorData.acceleration.z) }}</div>
                    </div>
                </div>
            </div>

            <!-- Rotation Rate (Gyroscope) -->
            <div class="sensor-section">
                <h3>Rotation (°/s)</h3>
                <div class="sensor-grid">
                    <div class="sensor-value">
                        <div class="label">Alpha</div>
                        <div class="value">{{ formatValue(sensorData.rotationRate.alpha) }}</div>
                    </div>
                    <div class="sensor-value">
                        <div class="label">Beta</div>
                        <div class="value">{{ formatValue(sensorData.rotationRate.beta) }}</div>
                    </div>
                    <div class="sensor-value">
                        <div class="label">Gamma</div>
                        <div class="value">{{ formatValue(sensorData.rotationRate.gamma) }}</div>
                    </div>
                </div>
            </div>

            <!-- Location - Condensed single row -->
            <div class="sensor-section">
                <h3>Location</h3>
                <div class="sensor-grid">
                    <div class="sensor-value">
                        <div class="label">Lat/Lng</div>
                        <div class="value compact">{{ formatCoord(sensorData.location.latitude) }}, {{ formatCoord(sensorData.location.longitude) }}</div>
                    </div>
                    <div class="sensor-value">
                        <div class="label">Altitude</div>
                        <div class="value">{{ formatValue(sensorData.location.altitude, 0) }}m</div>
                    </div>
                    <div class="sensor-value">
                        <div class="label">Accuracy</div>
                        <div class="value">{{ formatValue(sensorData.location.accuracy, 0) }}m</div>
                    </div>
                </div>
            </div>
        </div>
    `,

    methods: {
        formatValue(val, decimals = 2) {
            if (val === null || val === undefined || isNaN(val)) return '--';
            return Number(val).toFixed(decimals);
        },

        formatCoord(val) {
            if (val === null || val === undefined || val === 0) return '--';
            return Number(val).toFixed(4);
        }
    }
};

// Register component globally
window.SensorDisplay = SensorDisplay;
