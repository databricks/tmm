/**
 * UID Generator Service
 *
 * Generates 12-character readable, technical-themed unique identifiers
 */

const UIDGenerator = {
    // Technical/positive prefixes (4-7 chars)
    prefixes: [
        'cyber', 'quantum', 'pixel', 'neon', 'turbo', 'hyper', 'ultra',
        'nova', 'flux', 'wave', 'spark', 'drift', 'sync', 'mesh', 'grid',
        'byte', 'bit', 'data', 'core', 'node', 'edge', 'cloud', 'stream',
        'pulse', 'beam', 'ray', 'arc', 'volt', 'amp', 'flow', 'link',
        'nexus', 'matrix', 'vector', 'tensor', 'delta', 'sigma', 'omega',
        'alpha', 'beta', 'gamma', 'zeta', 'echo', 'ping', 'loop', 'hash'
    ],

    // Technical/fun suffixes (4-7 chars)
    suffixes: [
        'sync', 'wave', 'rush', 'flow', 'cast', 'net', 'hub', 'lab',
        'core', 'node', 'port', 'gate', 'link', 'mesh', 'grid', 'zone',
        'spark', 'bolt', 'ray', 'beam', 'flux', 'pulse', 'drift', 'ride',
        'storm', 'burst', 'surge', 'flash', 'glow', 'shine', 'blaze', 'fire'
    ],

    /**
     * Generate a unique 12-character identifier
     * Format: prefix + number (to make exactly 12 chars)
     * Examples: quantumray42, pixelflow789, cybernode001
     */
    generate() {
        // Get random prefix and suffix
        const prefix = this.prefixes[Math.floor(Math.random() * this.prefixes.length)];
        const suffix = this.suffixes[Math.floor(Math.random() * this.suffixes.length)];

        // Calculate how many digits we need
        const baseLength = prefix.length + suffix.length;
        const digitsNeeded = 12 - baseLength;

        // If too long, try different combination
        if (digitsNeeded < 1) {
            // Use shorter prefix only with numbers
            const shortPrefix = this.prefixes.filter(p => p.length <= 8)[
                Math.floor(Math.random() * this.prefixes.filter(p => p.length <= 8).length)
            ];
            const num = Math.floor(Math.random() * 10000).toString().padStart(12 - shortPrefix.length, '0');
            return shortPrefix + num;
        }

        // Generate random number with needed digits
        const maxNum = Math.pow(10, digitsNeeded) - 1;
        const num = Math.floor(Math.random() * maxNum).toString().padStart(digitsNeeded, '0');

        return prefix + suffix + num;
    },

    /**
     * Get or create a persistent UID for this client
     */
    getClientUID() {
        let uid = localStorage.getItem('zerostream_uid');
        if (!uid) {
            uid = this.generate();
            localStorage.setItem('zerostream_uid', uid);
            console.log(`[UIDGenerator] Generated new client UID: ${uid}`);
        }
        return uid;
    },

    /**
     * Force regenerate a new client UID
     * Returns the new UID
     */
    regenerateClientUID() {
        const newUid = this.generate();
        localStorage.setItem('zerostream_uid', newUid);
        console.log(`[UIDGenerator] Regenerated client UID: ${newUid}`);
        return newUid;
    },

    /**
     * Generate sample UIDs for testing
     */
    generateSamples(count = 10) {
        const samples = [];
        for (let i = 0; i < count; i++) {
            samples.push(this.generate());
        }
        return samples;
    }
};

// Export for use in other modules
window.UIDGenerator = UIDGenerator;

// Log some examples on load (for verification)
console.log('[UIDGenerator] Example UIDs:', UIDGenerator.generateSamples(5));