/**
 * LessonVoiceModal - Voice Practice & Role-Play for Lessons
 * Phase 2.9: Modal interface for Voice Practice and Role-Play modes
 */

class LessonVoiceModal {
    constructor() {
        this.modal = document.getElementById('lesson-voice-modal');
        this.sessionId = null;
        this.lessonId = null;
        this.mode = null; // 'voice_practice' or 'roleplay'
        this.isRecording = false;
        
        // Initialize components
        if (typeof VoiceRecorder !== 'undefined') {
            this.recorder = new VoiceRecorder();
        }
        if (typeof BarsVisualizer !== 'undefined') {
            this.visualizer = new BarsVisualizer('modal-bars-visualizer');
        }
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        // Close button
        const closeBtn = document.getElementById('modal-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
        
        // Finish button
        const finishBtn = document.getElementById('modal-finish-btn');
        if (finishBtn) {
            finishBtn.addEventListener('click', () => this.finishAndEvaluate());
        }
        
        // Record button
        const recordBtn = document.getElementById('modal-record-btn');
        if (recordBtn) {
            recordBtn.addEventListener('mousedown', (e) => this.startRecording(e));
            recordBtn.addEventListener('mouseup', (e) => this.stopRecording(e));
            recordBtn.addEventListener('mouseleave', (e) => this.stopRecording(e));
            
            recordBtn.addEventListener('touchstart', (e) => this.startRecording(e));
            recordBtn.addEventListener('touchend', (e) => this.stopRecording(e));
        }
        
        // Text form submission
        const textForm = document.getElementById('modal-text-form');
        if (textForm) {
            textForm.addEventListener('submit', (e) => this.handleTextSubmit(e));
        }
    }
    
    /**
     * Open modal for Voice Practice or Role-Play
     */
    async open(lessonId, mode) {
        this.lessonId = lessonId;
        this.mode = mode;
        
        // Update title
        const title = mode === 'voice_practice' ? 'Voice Practice' : 'Role-Play';
        document.getElementById('modal-title').textContent = title;
        
        // Show modal
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        
        // Load or create session
        await this.loadSession();
    }
    
    /**
     * Close modal without evaluation
     */
    close() {
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
        // Session remains active for continuation
    }
    
    /**
     * Load existing or create new session
     */
    async loadSession() {
        try {
            const endpoint = this.mode === 'voice_practice'
                ? `/chat/lesson/${this.lessonId}/voice-practice-chat/`
                : `/chat/lesson/${this.lessonId}/roleplay/start/`;
            
            const response = await fetchWithCsrf(endpoint, {
                method: 'POST',
                body: JSON.stringify({})
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to load session');
            }
            
            this.sessionId = data.session_id;
            
            // Clear chat history
            const chatHistory = document.getElementById('modal-chat-history');
            if (chatHistory) {
                chatHistory.innerHTML = '';
            }
            
            if (data.continued && data.messages) {
                // Restore existing conversation
                for (const msg of data.messages) {
                    if (msg.role === 'user') {
                        this.addUserMessage(msg.content);
                    } else {
                        this.addAIMessage(msg);
                    }
                }
            } else if (data.initial_message) {
                // New session - show initial AI message
                this.addAIMessage(data.initial_message);
                
                // Play initial audio if available
                if (data.initial_message.audio_url) {
                    this.playAudio(data.initial_message.audio_url);
                }
            } else if (data.ai_message) {
                // Role-play response format (legacy)
                this.addAIMessage({
                    content: data.ai_message,
                    role: 'model'
                });
            }
        } catch (error) {
            console.error('Error loading session:', error);
            this.showError('Failed to load session. Please try again.');
        }
    }
    
    /**
     * Start recording audio
     */
    async startRecording(e) {
        if (!this.recorder) return;
        
        e.preventDefault();
        try {
            const stream = await this.recorder.start();
            if (stream) {
                this.isRecording = true;
                const recordBtn = document.getElementById('modal-record-btn');
                if (recordBtn) {
                    recordBtn.classList.add('recording');
                }
            }
        } catch (error) {
            console.error('Microphone error:', error);
            this.showError('Unable to access microphone');
        }
    }
    
    /**
     * Stop recording audio
     */
    async stopRecording(e) {
        if (!this.recorder || !this.isRecording) return;
        
        e.preventDefault();
        this.recorder.stop();
        this.isRecording = false;
        
        const recordBtn = document.getElementById('modal-record-btn');
        if (recordBtn) {
            recordBtn.classList.remove('recording');
        }
        
        // Listen for recording-finished event
        document.addEventListener('recording-finished', (evt) => this.handleRecordingFinished(evt), { once: true });
    }
    
    /**
     * Handle finished recording
     */
    async handleRecordingFinished(evt) {
        const audioBlob = evt.detail;
        if (!audioBlob || audioBlob.size < 1000) {
            this.showError('Recording too short. Please try again.');
            return;
        }
        
        await this.processAudio(audioBlob);
    }
    
    /**
     * Process audio: send to server, get AI response
     */
    async processAudio(audioBlob) {
        try {
            const responseText = document.getElementById('modal-response-text');
            if (responseText) {
                responseText.innerText = '🤔 Обробляю...';
            }
            
            const formData = new FormData();
            formData.append('audio', audioBlob);
            
            const endpoint = this.mode === 'voice_practice'
                ? `/chat/lesson/${this.lessonId}/voice-practice/process-audio/`
                : `/chat/roleplay/${this.sessionId}/continue-voice/`;
            
            const csrfToken = this.getCsrfToken();
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Error processing audio');
            }
            
            if (responseText) {
                responseText.innerText = '';
            }
            
            // Add user message
            if (data.transcript) {
                this.addUserMessage(data.transcript);
            }
            
            // Add AI message
            if (data.ai_message || data.message_id) {
                this.addAIMessage({
                    content: data.ai_message,
                    translation: data.translation,
                    corrected_text: data.corrected_text,
                    audio_url: data.audio_url
                });
            }
            
            // Play audio
            if (data.audio_url) {
                this.playAudio(data.audio_url);
            }
            
            // Check if AI suggests finishing
            if (data.should_finish) {
                this.showFinishSuggestion();
            }
        } catch (error) {
            console.error('Error processing audio:', error);
            this.showError('Error processing audio. Please try again.');
        }
    }
    
    /**
     * Handle text input submission
     */
    async handleTextSubmit(e) {
        e.preventDefault();
        
        const input = document.getElementById('modal-text-input');
        if (!input) return;
        
        const text = input.value.trim();
        if (!text) return;
        
        input.value = '';
        
        this.addUserMessage(text);
        
        try {
            const responseText = document.getElementById('modal-response-text');
            if (responseText) {
                responseText.innerText = '🤔 Обробляю...';
            }
            
            let endpoint, formData;
            
            formData = new FormData();
            
            if (this.mode === 'voice_practice') {
                endpoint = `/chat/lesson/${this.lessonId}/voice-practice/process-text/`;
                formData.append('text', text);
            } else {
                // Role-play mode - use 'message' parameter
                endpoint = `/chat/roleplay/${this.sessionId}/continue/`;
                formData.append('message', text);
            }
            
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Error processing text');
            }
            
            if (responseText) {
                responseText.innerText = '';
            }
            
            // Add AI message
            const aiContent = data.ai_message || data.response;
            this.addAIMessage({
                content: aiContent,
                translation: data.translation,
                corrected_text: data.corrected_text,
                audio_url: data.audio_url
            });
            
            // Play audio
            if (data.audio_url) {
                this.playAudio(data.audio_url);
            }
            
            // Check if AI suggests finishing
            if (data.should_finish) {
                this.showFinishSuggestion();
            }
        } catch (error) {
            console.error('Error processing text:', error);
            this.showError('Error processing input. Please try again.');
        }
    }
    
    /**
     * Add user message to chat
     */
    addUserMessage(content) {
        const chatHistory = document.getElementById('modal-chat-history');
        if (!chatHistory) return;
        
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper sent';
        
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2, '0') + ':' +
                       now.getMinutes().toString().padStart(2, '0');
        
        wrapper.innerHTML = `
            <div class="avatar">Я</div>
            <div class="message sent">
                <div class="content">${this.escapeHtml(content)}</div>
                <div class="meta">
                    <span class="time">${timeStr}</span>
                </div>
            </div>
        `;
        
        chatHistory.appendChild(wrapper);
        this.scrollToBottom();
    }
    
    /**
     * Add AI message to chat
     */
    addAIMessage(msgData) {
        const chatHistory = document.getElementById('modal-chat-history');
        if (!chatHistory) return;
        
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper received';
        
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2, '0') + ':' +
                       now.getMinutes().toString().padStart(2, '0');
        
        const content = msgData.content || msgData.ai_message || '';
        
        wrapper.innerHTML = `
            <div class="avatar">AI</div>
            <div class="message received">
                <div class="content">${this.escapeHtml(content)}</div>
                <div class="meta">
                    <span class="time">${timeStr}</span>
                </div>
            </div>
        `;
        
        chatHistory.appendChild(wrapper);
        this.scrollToBottom();
    }
    
    /**
     * Play audio with visualizer
     */
    playAudio(audioUrl) {
        try {
            const audio = new Audio(audioUrl);
            
            if (this.visualizer && this.visualizer.connectAudioElement) {
                this.visualizer.connectAudioElement(audio);
            }
            
            audio.play().catch(err => {
                console.warn('Could not play audio:', err);
            });
            
            audio.addEventListener('ended', () => {
                if (this.visualizer && this.visualizer.stop) {
                    this.visualizer.stop();
                }
            });
        } catch (error) {
            console.error('Error playing audio:', error);
        }
    }
    
    /**
     * Finish session and evaluate
     */
    async finishAndEvaluate() {
        try {
            const finishBtn = document.getElementById('modal-finish-btn');
            if (finishBtn) {
                finishBtn.disabled = true;
                finishBtn.textContent = '⏳ Оцінюю...';
            }
            
            const endpoint = this.mode === 'voice_practice'
                ? `/chat/lesson/${this.lessonId}/voice-practice/evaluate/`
                : `/chat/roleplay/${this.sessionId}/evaluate/`;
            
            const response = await fetchWithCsrf(endpoint, {
                method: 'POST',
                body: JSON.stringify({})
            });
            
            const evaluation = await response.json();
            
            if (!response.ok) {
                throw new Error(evaluation.error || 'Failed to evaluate');
            }
            
            this.showEvaluationResults(evaluation);
        } catch (error) {
            console.error('Error evaluating:', error);
            this.showError('Failed to evaluate. Please try again.');
            
            const finishBtn = document.getElementById('modal-finish-btn');
            if (finishBtn) {
                finishBtn.disabled = false;
                finishBtn.textContent = 'Завершити та оцінити';
            }
        }
    }
    
    /**
     * Show evaluation results
     */
    showEvaluationResults(evaluation) {
        // Hide chat
        const chatContainer = document.getElementById('modal-chat-container');
        if (chatContainer) {
            chatContainer.style.display = 'none';
        }
        
        // Show results
        const resultsDiv = document.getElementById('modal-evaluation-results');
        if (!resultsDiv) return;
        
        resultsDiv.style.display = 'block';
        
        const overallScore = evaluation.overall_score ? evaluation.overall_score.toFixed(1) : '—';
        const feedback = evaluation.feedback || '';
        const strengths = evaluation.strengths || [];
        const improvements = evaluation.improvements || [];
        
        resultsDiv.innerHTML = `
            <div class="evaluation-results-content">
                <h3>Результати оцінювання</h3>
                <div class="score-circle">${overallScore}/10</div>
                
                ${feedback ? `<div class="feedback-text">${this.escapeHtml(feedback)}</div>` : ''}
                
                ${strengths.length > 0 ? `
                    <div class="strengths-section">
                        <h4>Ваші сильні сторони:</h4>
                        <ul>
                            ${strengths.map(s => `<li>${this.escapeHtml(s)}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                ${improvements.length > 0 ? `
                    <div class="improvements-section">
                        <h4>Де можна поліпшити:</h4>
                        <ul>
                            ${improvements.map(i => `<li>${this.escapeHtml(i)}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                <button type="button" id="modal-back-to-lesson" class="btn-back">
                    Повернутися до уроку
                </button>
            </div>
        `;
        
        const backBtn = document.getElementById('modal-back-to-lesson');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                this.close();
                location.reload();
            });
        }
    }
    
    /**
     * Show finish suggestion
     */
    showFinishSuggestion() {
        const responseText = document.getElementById('modal-response-text');
        if (responseText) {
            responseText.innerHTML = '<p class="finish-suggestion">AI recommends finishing. Ready to evaluate?</p>';
        }
    }
    
    /**
     * Show error message
     */
    showError(message) {
        const responseText = document.getElementById('modal-response-text');
        if (responseText) {
            responseText.innerHTML = `<p class="error-message">${this.escapeHtml(message)}</p>`;
        }
    }
    
    /**
     * Scroll to bottom of chat
     */
    scrollToBottom() {
        const chatHistory = document.getElementById('modal-chat-history');
        if (chatHistory) {
            setTimeout(() => {
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }, 0);
        }
    }
    
    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
    
    /**
     * Get CSRF token
     */
    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (token) return token;
        
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

/**
 * Helper: Fetch with CSRF token
 */
async function fetchWithCsrf(url, options = {}) {
    // Get CSRF token from form or cookie
    const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
    let csrfToken = tokenElement ? tokenElement.value : null;
    
    if (!csrfToken) {
        const name = 'csrftoken';
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    csrfToken = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
    }
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        credentials: 'same-origin',
    };
    
    if (options.headers) {
        defaultOptions.headers = { ...defaultOptions.headers, ...options.headers };
    }
    
    return fetch(url, { ...defaultOptions, ...options });
}

// Initialize modal on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.lessonVoiceModal = new LessonVoiceModal();
});
