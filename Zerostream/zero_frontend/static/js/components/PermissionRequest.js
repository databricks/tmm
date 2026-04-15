/**
 * Permission Request Component
 *
 * Displays sensor permissions needed and handles requesting them
 */

const PermissionRequest = {
    name: 'PermissionRequest',

    emits: ['permissions-granted'],

    data() {
        return {
            loading: false,
            error: null
        };
    },

    template: `
        <div class="permission-request">
            <h2>Sensor Access Required</h2>
            <p>ZeroStream needs access to your device sensors to collect and stream data.</p>

            <div class="permission-list">
                <div class="permission-item">
                    <div class="permission-icon">📍</div>
                    <div class="permission-text">
                        <h4>Location</h4>
                        <p>GPS coordinates, altitude, speed</p>
                    </div>
                </div>

                <div class="permission-item">
                    <div class="permission-icon">📱</div>
                    <div class="permission-text">
                        <h4>Motion Sensors</h4>
                        <p>Accelerometer, gyroscope, orientation</p>
                    </div>
                </div>

                <div class="permission-item">
                    <div class="permission-icon">🧭</div>
                    <div class="permission-text">
                        <h4>Compass</h4>
                        <p>Device heading and magnetic field</p>
                    </div>
                </div>
            </div>

            <div class="privacy-notice">
                <p>When active, this app streams your location and movement data anonymously to Databricks Zerobus. Your device is identified only by a random client ID — no personal information is collected. Sensor data is only transmitted while the app is active. You can stop it at any time or close the page.</p>
            </div>

            <p v-if="error" class="error-message">{{ error }}</p>

            <button
                @click="requestPermissions"
                :disabled="loading"
                class="btn btn-primary">
                {{ loading ? 'Requesting...' : 'Grant Permissions' }}
            </button>
        </div>
    `,

    methods: {
        async requestPermissions() {
            this.loading = true;
            this.error = null;

            try {
                const results = await SensorService.requestPermissions();

                if (results.motion || results.location) {
                    this.$emit('permissions-granted', results);
                } else {
                    this.error = 'Permissions were denied. Please allow access in your device settings.';
                }
            } catch (err) {
                this.error = 'Failed to request permissions: ' + err.message;
            } finally {
                this.loading = false;
            }
        }
    }
};

// Register component globally
window.PermissionRequest = PermissionRequest;
