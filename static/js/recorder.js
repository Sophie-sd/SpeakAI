class VoiceRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
    }

    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);
            
            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' }); // webm is safer for browsers
                this.audioChunks = [];
                // Dispatch event with blob
                const event = new CustomEvent('recording-finished', { detail: audioBlob });
                document.dispatchEvent(event);
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            return this.stream;
        } catch (err) {
            console.error("Error accessing microphone:", err);
            alert("Could not access microphone. Please allow permissions.");
        }
    }

    stop() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            // Stop tracks
            this.stream.getTracks().forEach(track => track.stop());
        }
    }
}
