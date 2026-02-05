/**
 * Voice Practice Recording & Processing
 * Handles MediaRecorder API, audio visualization, and uploads
 */

class VoicePracticeRecorder {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.stream = null;
        this.isRecording = false;
    }
    
    async initialize() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);
            
            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };
            
            this.mediaRecorder.onstop = () => {
                this.handleRecordingStop();
            };
            
            this.setupUI();
        } catch (error) {
            console.error('Error accessing microphone:', error);
            alert('Please allow microphone access to use voice practice.');
        }
    }
    
    setupUI() {
        // UI is handled by lesson.js
        // This is for additional recording setup
    }
    
    startRecording() {
        if (this.mediaRecorder && !this.isRecording) {
            this.audioChunks = [];
            this.mediaRecorder.start();
            this.isRecording = true;
            console.log('Recording started');
        }
    }
    
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            console.log('Recording stopped');
        }
    }
    
    handleRecordingStop() {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Make audio playable
        const audio = new Audio(audioUrl);
        console.log('Recording saved. Duration:', audio.duration);
        
        // Store for submission
        this.lastRecording = {
            blob: audioBlob,
            url: audioUrl,
            duration: audio.duration
        };
    }
    
    getLastRecording() {
        return this.lastRecording || null;
    }
}

// Global instance
window.voiceRecorder = null;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize voice recorder if on voice practice page
    if (document.querySelector('.tab-btn[data-tab="voice"]')) {
        window.voiceRecorder = new VoicePracticeRecorder('voice-practice-area');
        window.voiceRecorder.initialize();
    }
});
