/**
 * DOM-based 3-bar audio visualizer
 * Displays 3 vertical bars that animate based on audio frequency
 */
class BarsVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.bars = Array.from(this.container.querySelectorAll('.visualizer-bar'));
        this.audioCtx = null;
        this.analyser = null;
        this.dataArray = null;
        this.source = null;
        this.animationId = null;
        this.isActive = false;

        // Set static collapsed state by default
        this.setCollapsedState();
    }

    init() {
        if (!this.audioCtx) {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioCtx.createAnalyser();
            this.analyser.fftSize = 128; // Increased for better resolution
            this.bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(this.bufferLength);
        }
    }

    /**
     * Sets the bars to a static, collapsed state (idle)
     */
    setCollapsedState() {
        this.isActive = false;
        this.bars.forEach((bar) => {
            bar.style.transition = 'height 0.4s ease-in-out';
            bar.style.height = '15px'; // Static small height
        });
    }

    connectAudioElement(audioElement) {
        this.init();
        this.isActive = true;

        try {
            if (this.source) {
                try {
                    this.source.disconnect();
                } catch (e) {}
            }
            this.source = this.audioCtx.createMediaElementSource(audioElement);
            this.source.connect(this.analyser);
            this.analyser.connect(this.audioCtx.destination);
            this.draw();
        } catch (e) {
            console.log("Audio source error", e);
            this.setCollapsedState();
        }
    }

    draw() {
        if (!this.isActive) return;
        
        this.animationId = requestAnimationFrame(() => this.draw());
        this.analyser.getByteFrequencyData(this.dataArray);

        // Multipliers to make the center bar most prominent
        // index 0: left, 1: center, 2: right
        const multipliers = [0.6, 1.3, 0.6]; 
        
        const step = Math.floor(this.bufferLength / this.bars.length);
        this.bars.forEach((bar, i) => {
            let sum = 0;
            // Focus on vocal range frequencies (lower to mid)
            const rangeStart = Math.floor(i * step * 0.5);
            const rangeEnd = rangeStart + step;
            
            for (let j = rangeStart; j < rangeEnd; j++) {
                sum += this.dataArray[j];
            }
            const avg = (sum / step) * multipliers[i];
            
            // Map to visual height
            // Base height 15px + dynamic height up to ~65px
            const dynamicHeight = (avg / 255) * 80;
            const finalHeight = Math.min(Math.max(15, 15 + dynamicHeight), 75);
            
            bar.style.transition = 'height 0.1s ease-out';
            bar.style.height = finalHeight + 'px';
        });
    }

    stop() {
        this.isActive = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        this.setCollapsedState();
    }
}
