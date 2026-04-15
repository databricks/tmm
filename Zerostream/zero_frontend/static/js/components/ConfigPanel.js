/**
 * Config Panel Component
 *
 * Settings panel for configuring:
 * - Theme (dark/light mode)
 * - Data frequency (1-10 Hz)
 * - Display mode (numerical/graphical)
 */

const ConfigPanel = {
    name: 'ConfigPanel',

    props: {
        show: {
            type: Boolean,
            default: false
        },
        frequency: {
            type: Number,
            default: 3
        },
        displayMode: {
            type: String,
            default: 'numerical'
        },
        theme: {
            type: String,
            default: 'dark'
        }
    },

    emits: ['close', 'update:frequency', 'update:display-mode', 'update:theme', 'regenerate-client-id'],

    data() {
        return {
            localFrequency: this.frequency,
            localDisplayMode: this.displayMode,
            localTheme: this.theme
        };
    },

    computed: {
        isMinuteFrequency() {
            // Handle float comparison for 1/60 (approximately 0.0167)
            return this.localFrequency < 0.02 && this.localFrequency > 0.01;
        },
        isLightMode() {
            return this.localTheme === 'light';
        }
    },

    watch: {
        frequency(newVal) {
            this.localFrequency = newVal;
        },
        displayMode(newVal) {
            this.localDisplayMode = newVal;
        },
        theme(newVal) {
            this.localTheme = newVal;
        },
        show(newVal) {
            if (newVal) {
                this.localFrequency = this.frequency;
                this.localDisplayMode = this.displayMode;
                this.localTheme = this.theme;
            }
        }
    },

    template: `
        <div v-if="show" class="config-overlay" @click.self="close">
            <div class="config-panel">
                <div class="config-header">
                    <h2>Settings</h2>
                    <button class="config-close" @click="close">✕</button>
                </div>

                <div class="config-content">
                    <!-- Theme Toggle -->
                    <div class="config-section">
                        <h3>Appearance</h3>
                        <p class="config-description">
                            Switch between dark and light mode
                        </p>
                        <div class="theme-toggle">
                            <div class="theme-toggle-label">
                                <svg v-if="isLightMode" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="5"></circle>
                                    <line x1="12" y1="1" x2="12" y2="3"></line>
                                    <line x1="12" y1="21" x2="12" y2="23"></line>
                                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                                    <line x1="1" y1="12" x2="3" y2="12"></line>
                                    <line x1="21" y1="12" x2="23" y2="12"></line>
                                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                                </svg>
                                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                                </svg>
                                {{ isLightMode ? 'Light Mode' : 'Dark Mode' }}
                            </div>
                            <div
                                :class="['theme-switch', isLightMode ? 'active' : '']"
                                @click="toggleTheme"
                                role="switch"
                                :aria-checked="isLightMode">
                                <div class="theme-switch-knob"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Display Mode -->
                    <div class="config-section">
                        <h3>Display Mode</h3>
                        <p class="config-description">
                            Choose how sensor data is visualized
                        </p>
                        <div class="display-toggle">
                            <button
                                :class="['toggle-btn', localDisplayMode === 'combined' ? 'active' : '']"
                                @click="setDisplayMode('combined')">
                                Combined
                            </button>
                            <button
                                :class="['toggle-btn', localDisplayMode === 'numerical' ? 'active' : '']"
                                @click="setDisplayMode('numerical')">
                                Numerical
                            </button>
                            <button
                                :class="['toggle-btn', localDisplayMode === 'graphical' ? 'active' : '']"
                                @click="setDisplayMode('graphical')">
                                Graphical
                            </button>
                        </div>
                    </div>

                    <!-- Send Interval -->
                    <div class="config-section">
                        <h3>Data Send Interval</h3>
                        <p class="config-description">
                            How often sensor data is sent to the backend
                        </p>

                        <div class="interval-toggle">
                            <button
                                :class="['toggle-btn', localFrequency === 1 ? 'active' : '']"
                                @click="setFrequency(1)">
                                Every 1 second
                            </button>
                            <button
                                :class="['toggle-btn', localFrequency === 0.1 ? 'active' : '']"
                                @click="setFrequency(0.1)">
                                Every 10 seconds
                            </button>
                            <button
                                :class="['toggle-btn', isMinuteFrequency ? 'active' : '']"
                                @click="setFrequency(1/60)">
                                Every minute
                            </button>
                        </div>

                        <p class="config-hint">
                            Less frequent = lower battery and network usage
                        </p>
                    </div>

                    <!-- Client ID -->
                    <div class="config-section">
                        <h3>Client ID</h3>
                        <p class="config-description">
                            Your unique device identifier for this session
                        </p>
                        <button class="regenerate-btn" @click="regenerateClientId">
                            Create New Client ID
                        </button>
                        <p class="config-hint">
                            Creates a new identity. Previous data will remain under the old ID.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    `,

    methods: {
        toggleTheme() {
            this.localTheme = this.localTheme === 'dark' ? 'light' : 'dark';
            this.$emit('update:theme', this.localTheme);
        },
        setDisplayMode(mode) {
            this.localDisplayMode = mode;
            this.$emit('update:display-mode', mode);
        },
        setFrequency(freq) {
            this.localFrequency = freq;
            this.$emit('update:frequency', freq);
        },
        updateFrequency() {
            this.$emit('update:frequency', this.localFrequency);
        },
        regenerateClientId() {
            const newId = window.UIDGenerator.regenerateClientUID();
            this.$emit('regenerate-client-id', newId);
            this.close();
        },
        close() {
            this.$emit('close');
        }
    }
};

// Register component globally
window.ConfigPanel = ConfigPanel;
