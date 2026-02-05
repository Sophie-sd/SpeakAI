class AvatarController {
    constructor(idleVideoId, talkingVideoId) {
        this.idleVideo = document.getElementById(idleVideoId);
        this.talkingVideo = document.getElementById(talkingVideoId);
        
        if (!this.idleVideo || !this.talkingVideo) return;

        // Initial state
        this.talkingVideo.style.display = 'none';
        this.idleVideo.style.display = 'block';
        this.idleVideo.loop = true;
        this.talkingVideo.loop = true;
        
        // Try to play idle (might be blocked by autoplay policy until interaction)
        this.idleVideo.play().catch(e => console.log("Autoplay prevented", e));
    }

    startTalking() {
        this.idleVideo.style.display = 'none';
        this.talkingVideo.style.display = 'block';
        this.talkingVideo.currentTime = 0;
        this.talkingVideo.play();
        this.idleVideo.pause();
    }

    stopTalking() {
        this.talkingVideo.pause();
        this.talkingVideo.style.display = 'none';
        this.idleVideo.style.display = 'block';
        this.idleVideo.play();
    }
}
