/**
 * Graphical Display Component
 *
 * Simplified line indicators for pitch and roll
 * - Pitch: horizontal line moves up/down with vertical reference
 * - Roll: horizontal line rotates
 */

const GraphicalDisplay = {
    name: 'GraphicalDisplay',

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
        <div class="graphical-display simple">
            <div class="simple-gauges">
                <!-- Pitch Indicator -->
                <div class="simple-gauge">
                    <div class="gauge-label-top">Pitch</div>
                    <div class="gauge-box">
                        <div class="pitch-container">
                            <!-- Center reference (vertical line) -->
                            <div class="pitch-reference"></div>
                            <!-- Moving horizon line -->
                            <div class="pitch-line" :style="getPitchStyle()"></div>
                        </div>
                    </div>
                    <div class="gauge-value">{{ formatAngle(sensorData.orientation.beta) }}</div>
                </div>

                <!-- Roll Indicator -->
                <div class="simple-gauge">
                    <div class="gauge-label-top">Roll</div>
                    <div class="gauge-box">
                        <div class="roll-container">
                            <!-- Level tick marks (like a water level meter) -->
                            <div class="roll-tick-left"></div>
                            <div class="roll-tick-right"></div>
                            <!-- Center dot -->
                            <div class="roll-center"></div>
                            <!-- Rotating line -->
                            <div class="roll-line" :style="getRollStyle()"></div>
                        </div>
                    </div>
                    <div class="gauge-value">{{ formatAngle(sensorData.orientation.gamma) }}</div>
                </div>
            </div>
        </div>
    `,

    methods: {
        getPitchStyle() {
            const beta = this.sensorData.orientation.beta || 0;
            const clampedBeta = Math.max(-90, Math.min(90, beta));
            // Map -90..90 to 90%..10% (inverted so nose up = line goes up)
            const top = 50 - (clampedBeta / 90) * 40;
            return { top: `${top}%` };
        },

        getRollStyle() {
            const gamma = this.sensorData.orientation.gamma || 0;
            const clampedGamma = Math.max(-90, Math.min(90, gamma));
            return { transform: `rotate(${clampedGamma}deg)` };
        },

        formatAngle(val) {
            if (val === null || val === undefined || isNaN(val)) return '--';
            const num = Number(val);
            const sign = num >= 0 ? '+' : '';
            return `${sign}${num.toFixed(1)}°`;
        }
    }
};

window.GraphicalDisplay = GraphicalDisplay;
