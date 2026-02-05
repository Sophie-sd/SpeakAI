class AudioVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.canvasCtx = this.canvas.getContext('2d');
        this.audioCtx = null;
        this.analyser = null;
        this.dataArray = null;
        this.source = null;
        this.animationId = null;
    }

    init() {
         if (!this.audioCtx) {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioCtx.createAnalyser();
            this.analyser.fftSize = 2048;
            this.bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(this.bufferLength);
         }
    }

    connectStream(stream) {
        this.init();
        if (this.source) {
            // this.source.disconnect(); // Can cause issues if reusing context
        }
        this.source = this.audioCtx.createMediaStreamSource(stream);
        this.source.connect(this.analyser);
        this.draw();
    }
    
    connectAudioElement(audioElement) {
        this.init();
        // createMediaElementSource can only be called once per element.
        // If we reuse the element, we should check if we already connected it?
        // Actually, we usually create a new source. 
        // But for persistent audio element, we need a map or flag.
        // Assuming we pass a new Audio object or handle this.
        
        try {
            this.source = this.audioCtx.createMediaElementSource(audioElement);
            this.source.connect(this.analyser);
            this.analyser.connect(this.audioCtx.destination);
            this.draw();
        } catch (e) {
            console.log("Audio source already connected or error", e);
        }
    }

    draw() {
        this.animationId = requestAnimationFrame(() => this.draw());
        this.analyser.getByteTimeDomainData(this.dataArray);

        this.canvasCtx.fillStyle = 'rgb(240, 240, 240)';
        this.canvasCtx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.canvasCtx.lineWidth = 2;
        this.canvasCtx.strokeStyle = 'rgb(0, 0, 0)';
        this.canvasCtx.beginPath();

        const sliceWidth = this.canvas.width * 1.0 / this.bufferLength;
        let x = 0;

        for (let i = 0; i < this.bufferLength; i++) {
            const v = this.dataArray[i] / 128.0;
            const y = v * this.canvas.height / 2;

            if (i === 0) {
                this.canvasCtx.moveTo(x, y);
            } else {
                this.canvasCtx.lineTo(x, y);
            }

            x += sliceWidth;
        }

        this.canvasCtx.lineTo(this.canvas.width, this.canvas.height / 2);
        this.canvasCtx.stroke();
    }
}
