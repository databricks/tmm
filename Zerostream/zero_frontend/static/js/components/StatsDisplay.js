/**
 * Stats Display Component
 *
 * Shows total events sent and data transmitted with animated counters
 */

const StatsDisplay = {
    name: 'StatsDisplay',

    props: {
        eventCount: {
            type: Number,
            default: 0
        },
        active: {
            type: Boolean,
            default: false
        }
    },

    data() {
        return {
            // Animated display values (for smooth transitions)
            displayEventCount: 0,
            displayDataSize: 0,
            // Estimated bytes per event (based on typical JSON payload)
            bytesPerEvent: 550,
            // Animation frame ID
            animationFrame: null
        };
    },

    computed: {
        // Calculate total data size in bytes
        totalDataBytes() {
            return this.eventCount * this.bytesPerEvent;
        },

        // Format data size for display
        formattedDataSize() {
            const bytes = this.displayDataSize;
            if (bytes < 1024) {
                return { value: bytes.toFixed(0), unit: 'B' };
            } else if (bytes < 1024 * 1024) {
                return { value: (bytes / 1024).toFixed(1), unit: 'KB' };
            } else if (bytes < 1024 * 1024 * 1024) {
                return { value: (bytes / (1024 * 1024)).toFixed(2), unit: 'MB' };
            } else {
                return { value: (bytes / (1024 * 1024 * 1024)).toFixed(2), unit: 'GB' };
            }
        },

        // Format event count with commas
        formattedEventCount() {
            return Math.floor(this.displayEventCount).toLocaleString();
        }
    },

    watch: {
        eventCount: {
            handler(newVal) {
                this.animateToValue(newVal);
            },
            immediate: true
        }
    },

    methods: {
        animateToValue(targetEvents) {
            const targetData = targetEvents * this.bytesPerEvent;
            const startEvents = this.displayEventCount;
            const startData = this.displayDataSize;
            const duration = 300; // ms
            const startTime = performance.now();

            const animate = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Ease-out curve for smooth deceleration
                const easeOut = 1 - Math.pow(1 - progress, 3);

                this.displayEventCount = startEvents + (targetEvents - startEvents) * easeOut;
                this.displayDataSize = startData + (targetData - startData) * easeOut;

                if (progress < 1) {
                    this.animationFrame = requestAnimationFrame(animate);
                }
            };

            if (this.animationFrame) {
                cancelAnimationFrame(this.animationFrame);
            }
            this.animationFrame = requestAnimationFrame(animate);
        }
    },

    beforeUnmount() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    },

    template: `
        <div :class="['stats-display', { inactive: !active }]">
            <div class="stats-container">
                <!-- Events Counter -->
                <div class="stat-card">
                    <div class="stat-label">Events Sent</div>
                    <div class="stat-value-container">
                        <span class="stat-value">{{ formattedEventCount }}</span>
                    </div>
                    <div class="stat-sublabel">sensor readings</div>
                </div>

                <!-- Data Size Counter -->
                <div class="stat-card">
                    <div class="stat-label">Data Transmitted</div>
                    <div class="stat-value-container">
                        <span class="stat-value">{{ formattedDataSize.value }}</span>
                        <span class="stat-unit">{{ formattedDataSize.unit }}</span>
                    </div>
                    <div class="stat-sublabel">~{{ bytesPerEvent }} bytes/event</div>
                </div>
            </div>

            <!-- Status indicator -->
            <div class="stats-status">
                <span :class="['status-dot', { active: active }]"></span>
                <span class="status-text">{{ active ? 'Streaming' : 'Paused' }}</span>
            </div>
        </div>
    `
};

// Register component globally
window.StatsDisplay = StatsDisplay;
