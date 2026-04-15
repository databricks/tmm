/**
 * ZeroBus Service
 *
 * This service handles sending sensor data to Databricks backend.
 * Sends data immediately without batching.
 */

const ZeroBusService = {
    // Configuration
    config: {
        endpoint: '/api/stream',  // Backend endpoint
        enabled: true
    },

    // Callbacks
    callbacks: {
        onDataSent: null  // Called when data is successfully sent
    },

    // Statistics
    stats: {
        totalSent: 0,
        totalFailed: 0,
        lastSentTime: null
    },

    /**
     * Initialize the ZeroBus connection
     * @param {Object} options - Configuration options
     */
    init(options = {}) {
        this.config = { ...this.config, ...options };
        if (options.onDataSent) {
            this.callbacks.onDataSent = options.onDataSent;
        }
        console.log('[ZeroBus] Initialized - sending to backend');
    },

    /**
     * Send sensor data immediately to backend
     * @param {Object} sensorData - The sensor data to send
     * @returns {Promise<boolean>} - Success status
     */
    async sendData(sensorData) {
        // Add timestamp to data (clientId comes from sensorData)
        const payload = {
            timestamp: new Date().toISOString(),
            ...sensorData
        };

        // Send immediately as single-item array (backend expects array)
        try {
            const response = await fetch(this.config.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify([payload])  // Send as array with single item
            });

            if (response.ok) {
                // Try to parse JSON response, but don't fail if it's empty
                try {
                    await response.json();
                } catch (e) {
                    // Response might be empty or not JSON - that's OK
                }
                this.stats.totalSent++;
                this.stats.lastSentTime = new Date();
                console.log('[ZeroBus] Sent data at', payload.timestamp);
                // Notify callback that data was sent
                if (this.callbacks.onDataSent) {
                    this.callbacks.onDataSent();
                }
                return true;
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('[ZeroBus] Send failed:', error);
            this.stats.totalFailed++;
            return false;
        }
    },

    /**
     * Get current status
     * @returns {Object}
     */
    getStatus() {
        return {
            enabled: this.config.enabled,
            totalSent: this.stats.totalSent,
            totalFailed: this.stats.totalFailed,
            lastSentTime: this.stats.lastSentTime
        };
    },

    /**
     * Flush any pending data (no-op since we send immediately)
     */
    flush() {
        // No-op - data is sent immediately, nothing to flush
        console.log('[ZeroBus] Flush called (no pending data)');
    }
};

// Export for use in other modules
window.ZeroBusService = ZeroBusService;
