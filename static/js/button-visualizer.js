/**
 * Button Equalizer Visualizer
 * Animates button scale based on microphone input frequency
 * Used when user is speaking
 */
class ButtonVisualizer {
    constructor(buttonElement) {
        this.button = buttonElement;
        this.audioCtx = null;
        this.analyser = null;
        this.dataArray = null;
        this.source = null;
        this.animationId = null;
        this.baseScale = 1;
        this.currentScale = 1;
        this.targetScale = 1;
    }

    init() {
        if (!this.audioCtx) {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioCtx.createAnalyser();
            this.analyser.fftSize = 256;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        }
    }

    connectStream(stream) {
        this.init();
        
        if (this.source) {
            try {
                this.source.disconnect();
            } catch (e) {
                // Already disconnected
            }
        }
        
        this.source = this.audioCtx.createMediaStreamSource(stream);
        this.source.connect(this.analyser);
        this.draw();
    }

    draw() {
        this.animationId = requestAnimationFrame(() => this.draw());
        
        this.analyser.getByteFrequencyData(this.dataArray);

        // Calculate average frequency
        let sum = 0;
        for (let i = 0; i < this.dataArray.length; i++) {
            sum += this.dataArray[i];
        }
        const average = sum / this.dataArray.length;

        // Scale button: 1.0 (min) to 1.3 (max)
        this.targetScale = 1 + (average / 255) * 0.3;

        // Smooth animation
        this.currentScale += (this.targetScale - this.currentScale) * 0.15;

        // Apply scale to button
        this.button.style.transform = `scale(${this.currentScale})`;
    }

    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        // Smooth return to normal size
        const resetInterval = setInterval(() => {
            this.currentScale += (1 - this.currentScale) * 0.2;
            this.button.style.transform = `scale(${this.currentScale})`;
            
            if (Math.abs(this.currentScale - 1) < 0.01) {
                this.currentScale = 1;
                this.button.style.transform = 'scale(1)';
                clearInterval(resetInterval);
            }
        }, 16);
        
        // Disconnect audio source
        if (this.source) {
            try {
                this.source.disconnect();
            } catch (e) {
                // Already disconnected
            }
        }
    }
}
