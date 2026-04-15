/**
 * Combined Display Component
 *
 * Default view combining graphical gauges (pitch, roll, compass)
 * with numerical readouts (acceleration, rotation)
 */

const CombinedDisplay = {
    name: 'CombinedDisplay',

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

    data() {
        return {
            continuousHeading: 0,
            lastRawHeading: null,
            displayedNumbers: {
                acceleration: { x: 0, y: 0, z: 0 },
                rotationRate: { alpha: 0, beta: 0, gamma: 0 },
                orientation: { beta: 0, gamma: 0 }
            }
        };
    },

    watch: {
        'sensorData.orientation.alpha'(newHeading) {
            if (!this.active) return;
            this.updateContinuousHeading(newHeading);
        },
        sensorData: {
            deep: true,
            handler(newData) {
                if (!this.active) return;
                // Update displayed numbers at 5 Hz (when updateNumbers flag is true)
                if (newData.updateNumbers) {
                    this.displayedNumbers = {
                        acceleration: { ...newData.acceleration },
                        rotationRate: { ...newData.rotationRate },
                        orientation: {
                            beta: newData.orientation.beta,
                            gamma: newData.orientation.gamma
                        }
                    };
                }
            }
        }
    },

    template: `
        <div :class="['combined-display', { inactive: !active }]">
            <!-- Row 1: Gauges — pitch/roll stacked left, heading right -->
            <div class="combined-gauges">
                <div class="gauges-left">
                    <!-- Pitch -->
                    <div class="combined-gauge stacked">
                        <div class="gauge-label-top">Pitch</div>
                        <div class="gauge-box">
                            <div class="pitch-container">
                                <div class="pitch-reference"></div>
                                <div class="pitch-line" :style="getPitchStyle()"></div>
                                <!-- Pitch markers on vertical center line -->
                                <div class="pitch-markers">
                                    <div class="pitch-marker pitch-up">↑</div>
                                    <div class="pitch-marker pitch-center">—</div>
                                    <div class="pitch-marker pitch-down">↓</div>
                                </div>
                            </div>
                            <div class="gauge-value-overlay">{{ formatAngle(displayedNumbers.orientation.beta) }}</div>
                        </div>
                    </div>
                    <!-- Roll -->
                    <div class="combined-gauge stacked">
                        <div class="gauge-label-top">Roll</div>
                        <div class="gauge-box">
                            <div class="roll-container">
                                <!-- Level tick marks (like a water level meter) -->
                                <div class="roll-tick-left"></div>
                                <div class="roll-tick-right"></div>
                                <div class="roll-center"></div>
                                <div class="roll-line" :style="getRollStyle()"></div>
                            </div>
                            <div class="gauge-value-overlay">{{ formatAngle(displayedNumbers.orientation.gamma) }}</div>
                        </div>
                    </div>
                </div>

                <!-- Heading (right side, full height) -->
                <div class="gauge-right">
                    <div class="gauge-label-top">Heading</div>
                    <div class="gauge-box heading-box">
                        <!-- Rotating compass rose -->
                        <div class="compass-rose-rotating" :style="getCompassRoseStyle()">
                            <!-- Tick marks every 10° -->
                            <div class="compass-ticks">
                                <div v-for="tick in compassTicks" :key="tick.deg"
                                     :class="['compass-tick', { major: tick.major }]"
                                     :style="{ transform: 'rotate(' + tick.deg + 'deg)' }">
                                </div>
                            </div>
                            <!-- Cardinal directions -->
                            <span class="cardinal cardinal-n">N</span>
                            <span class="cardinal cardinal-e">E</span>
                            <span class="cardinal cardinal-s">S</span>
                            <span class="cardinal cardinal-w">W</span>
                        </div>
                        <!-- Fixed indicator pointing up -->
                        <div class="compass-fixed-indicator">
                            <svg viewBox="0 0 24 32" fill="none">
                                <path d="M 12,4 L 8,12 L 12,10 L 16,12 Z" fill="var(--primary-color)" stroke="white" stroke-width="1"/>
                            </svg>
                        </div>
                        <div class="compass-center-dot"></div>
                    </div>
                    <div class="gauge-value">{{ formatHeading(sensorData.orientation.alpha) }}</div>
                </div>
            </div>

            <!-- Row 2: Numerical Readouts -->
            <div class="combined-numerics">
                <div class="sensor-section">
                    <h3>Acceleration (m/s²)</h3>
                    <div class="sensor-grid">
                        <div class="sensor-value">
                            <div class="label">X</div>
                            <div class="value">{{ formatValue(displayedNumbers.acceleration.x) }}</div>
                        </div>
                        <div class="sensor-value">
                            <div class="label">Y</div>
                            <div class="value">{{ formatValue(displayedNumbers.acceleration.y) }}</div>
                        </div>
                        <div class="sensor-value">
                            <div class="label">Z</div>
                            <div class="value">{{ formatValue(displayedNumbers.acceleration.z) }}</div>
                        </div>
                    </div>
                </div>
                <div class="sensor-section">
                    <h3>Rotation (°/s)</h3>
                    <div class="sensor-grid">
                        <div class="sensor-value">
                            <div class="label">Alpha</div>
                            <div class="value">{{ formatValue(displayedNumbers.rotationRate.alpha) }}</div>
                        </div>
                        <div class="sensor-value">
                            <div class="label">Beta</div>
                            <div class="value">{{ formatValue(displayedNumbers.rotationRate.beta) }}</div>
                        </div>
                        <div class="sensor-value">
                            <div class="label">Gamma</div>
                            <div class="value">{{ formatValue(displayedNumbers.rotationRate.gamma) }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,

    computed: {
        compassTicks() {
            const ticks = [];
            for (let deg = 0; deg < 360; deg += 10) {
                // Skip cardinal directions (0, 90, 180, 270) — those have labels
                if (deg % 90 === 0) continue;
                ticks.push({ deg, major: deg % 30 === 0 });
            }
            return ticks;
        }
    },

    methods: {
        /**
         * Update continuous heading - tracks rotation beyond 360° to prevent CSS transition jumps
         * This allows CSS to smoothly animate from 350° to 370° instead of jumping to 10°
         */
        updateContinuousHeading(newHeading) {
            if (newHeading === null || newHeading === undefined || isNaN(newHeading)) {
                return;
            }

            // Initialize on first value
            if (this.lastRawHeading === null) {
                this.continuousHeading = newHeading;
                this.lastRawHeading = newHeading;
                return;
            }

            // Calculate the difference
            let diff = newHeading - this.lastRawHeading;

            // Detect wraparound and adjust continuous heading accordingly
            if (diff > 180) {
                // Wrapped backward (e.g., 350° -> 10°), actually went -340°
                diff -= 360;
            } else if (diff < -180) {
                // Wrapped forward (e.g., 10° -> 350°), actually went +340°
                diff += 360;
            }

            // Update continuous heading (can be > 360 or < 0)
            this.continuousHeading += diff;
            this.lastRawHeading = newHeading;
        },

        getPitchStyle() {
            const beta = this.sensorData.orientation.beta || 0;
            const clampedBeta = Math.max(-90, Math.min(90, beta));
            const top = 50 - (clampedBeta / 90) * 40;
            return { top: `${top}%` };
        },

        getRollStyle() {
            const gamma = this.sensorData.orientation.gamma || 0;
            // Clamp to ±90 degrees and negate for correct visual representation
            // Negative gamma (device tilted left) should rotate line counter-clockwise
            const clampedGamma = Math.max(-90, Math.min(90, gamma));
            return { transform: `rotate(${-clampedGamma}deg)` };
        },

        getCompassRoseStyle() {
            // Use continuous heading (can be > 360°) to prevent CSS transition jumps
            // Rotate rose counter-clockwise so North points to actual north
            return { transform: `rotate(${-this.continuousHeading}deg)` };
        },

        formatValue(val, decimals = 2) {
            if (val === null || val === undefined || isNaN(val)) return '--';
            return Number(val).toFixed(decimals);
        },

        formatAngle(val) {
            if (val === null || val === undefined || isNaN(val)) return '--';
            const num = Number(val);
            const sign = num >= 0 ? '+' : '';
            return `${sign}${num.toFixed(1)}°`;
        },

        formatHeading(val) {
            if (val === null || val === undefined || isNaN(val)) return '--';
            return `${Number(val).toFixed(0)}°`;
        }
    }
};

window.CombinedDisplay = CombinedDisplay;
