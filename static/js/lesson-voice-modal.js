/**
 * LessonVoiceModal - ПОВНА КОПІЯ voice chat в модалці
 * Обмежено лише темою уроку/roleplay
 */

class LessonVoiceModal {
    constructor() {
        this.modal = document.getElementById('lesson-voice-modal');
        this.sessionId = null;
        this.lessonId = null;
        this.mode = null;
        this.isRecording = false;
        
        // Initialize recorder and visualizer
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
        
        // Record button (hold to speak)
        const recordBtn = document.getElementById('modal-record-btn');
        if (recordBtn) {
            recordBtn.addEventListener('mousedown', (e) => this.startRecording(e));
            recordBtn.addEventListener('mouseup', (e) => this.stopRecording(e));
            recordBtn.addEventListener('mouseleave', (e) => this.stopRecording(e));
            recordBtn.addEventListener('touchstart', (e) => this.startRecording(e));
            recordBtn.addEventListener('touchend', (e) => this.stopRecording(e));
        }
        
        // Text form
        const textForm = document.getElementById('modal-text-form');
        if (textForm) {
            textForm.addEventListener('submit', (e) => this.handleTextSubmit(e));
        }
        
        // Finish button
        const finishBtn = document.getElementById('modal-finish-btn');
        if (finishBtn) {
            finishBtn.addEventListener('click', () => this.finishAndEvaluate());
        }
        
        // Recording finished event
        document.addEventListener('recording-finished', (e) => this.handleRecordingFinished(e));
    }
    
    async open(lessonId, mode) {
        this.lessonId = lessonId;
        this.mode = mode;
        
        const title = mode === 'voice_practice' ? 'Voice Practice' : 'Role-Play';
        document.getElementById('modal-title').textContent = title;
        
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        
        await this.loadSession();
    }
    
    close() {
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
    }
    
    async loadSession() {
        try {
            const endpoint = this.mode === 'voice_practice'
                ? `/chat/lesson/${this.lessonId}/voice-practice-chat/`
                : `/chat/lesson/${this.lessonId}/roleplay/start/`;
            
            const response = await fetchWithCsrf(endpoint, {
                method: 'POST',
                body: JSON.stringify({})
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server error: ${response.status}`);
            }
            
            const data = await response.json();
            
            this.sessionId = data.session_id;
            
            const chatHistory = document.getElementById('modal-chat-history');
            if (chatHistory) {
                chatHistory.innerHTML = '';
            }
            
            if (data.continued && data.messages) {
                // Restore conversation using render-message endpoint
                for (const msg of data.messages) {
                    if (msg.id) {
                        await this.renderMessageFromServer(msg.id);
                    }
                }
            } else if (data.initial_message && data.initial_message.id) {
                // ALWAYS render initial message via server partial (with full UI features)
                await this.renderMessageFromServer(data.initial_message.id);
                
                // Play audio
                if (data.audio_url || (data.initial_message && data.initial_message.audio_url)) {
                    this.playAudio(data.audio_url || data.initial_message.audio_url);
                }
            }
        } catch (error) {
            console.error('Error loading session:', error);
            this.showError('Failed to load session. Please try again.');
        }
    }
    
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
    
    async stopRecording(e) {
        if (!this.recorder || !this.isRecording) return;
        e.preventDefault();
        
        this.recorder.stop();
        this.isRecording = false;
        
        const recordBtn = document.getElementById('modal-record-btn');
        if (recordBtn) {
            recordBtn.classList.remove('recording');
        }
    }
    
    async handleRecordingFinished(evt) {
        const audioBlob = evt.detail;
        if (!audioBlob || audioBlob.size < 1000) {
            this.showError('Recording too short. Please try again.');
            return;
        }
        
        await this.processAudio(audioBlob);
    }
    
    async processAudio(audioBlob) {
        try {
            const responseText = document.getElementById('modal-response-text');
            if (responseText) {
                responseText.innerText = '🤔 Обробляю...';
            }
            
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            
            const endpoint = this.mode === 'voice_practice'
                ? `/chat/lesson/${this.lessonId}/voice-practice/process-audio/`
                : `/chat/roleplay/${this.sessionId}/continue-voice/`;
            
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server error: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (responseText) {
                responseText.innerText = '';
            }
            
            // Add user message
            const userText = data.user_text || data.transcript;
            if (userText) {
                this.addUserMessage(userText);
            }
            
            // Add AI message using server rendering
            if (data.message_id) {
                await this.renderMessageFromServer(data.message_id);
            }
            
            // Play audio
            if (data.audio_url) {
                this.playAudio(data.audio_url);
            }
            
            // Check if should finish
            if (data.should_finish) {
                this.showFinishSuggestion();
            }
        } catch (error) {
            console.error('Error processing audio:', error);
            this.showError('Error processing audio. Please try again.');
        }
    }
    
    async handleTextSubmit(e) {
        e.preventDefault();
        
        const input = document.getElementById('modal-text-input');
        if (!input) return;
        
        const text = input.value.trim();
        if (!text) return;
        
        input.value = '';
        
        // Add user message immediately
        this.addUserMessage(text);
        
        try {
            const responseText = document.getElementById('modal-response-text');
            if (responseText) {
                responseText.innerText = '🤔 Обробляю...';
            }
            
            const formData = new FormData();
            
            let endpoint;
            if (this.mode === 'voice_practice') {
                endpoint = `/chat/lesson/${this.lessonId}/voice-practice/process-text/`;
                formData.append('text', text);
            } else {
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
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server error: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (responseText) {
                responseText.innerText = '';
            }
            
            // ALWAYS use server rendering for AI message (with full UI features)
            if (data.message_id) {
                await this.renderMessageFromServer(data.message_id);
            }
            
            // Play audio
            if (data.audio_url) {
                this.playAudio(data.audio_url);
            }
            
            // Check if should finish
            if (data.should_finish) {
                this.showFinishSuggestion();
            }
        } catch (error) {
            console.error('Error processing text:', error);
            this.showError('Error processing input. Please try again.');
        }
    }
    
    /**
     * Render message using server endpoint (same as voice chat)
     */
    async renderMessageFromServer(messageId) {
        try {
            const response = await fetch(`/voice/render-message/${messageId}/`);
            if (!response.ok) throw new Error('Failed to fetch message');
            
            const html = await response.text();
            const chatHistory = document.getElementById('modal-chat-history');
            if (chatHistory) {
                chatHistory.insertAdjacentHTML('beforeend', html);
                
                // Process HTMX for action buttons
                if (window.htmx) {
                    htmx.process(chatHistory.lastElementChild);
                }
                
                this.scrollToBottom();
            }
        } catch (err) {
            console.error('Error rendering message:', err);
        }
    }
    
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
                    <span class="status">
                        <svg class="status-icon" viewBox="0 0 24 24">
                            <path d="M18 7l-1.41-1.41-6.34 6.34 1.41 1.41L18 7zm4.24-1.41L11.66 16.17 7.48 12l-1.41 1.41L11.66 19l12-12-1.42-1.41zM.41 13.41L6 19l1.41-1.41L1.83 12 .41 13.41z" />
                        </svg>
                    </span>
                </div>
            </div>
        `;
        
        chatHistory.appendChild(wrapper);
        this.scrollToBottom();
    }
    
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
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to evaluate');
            }
            
            this.showEvaluationResults(data);
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
    
    showEvaluationResults(data) {
        const chatContainer = document.getElementById('modal-chat-container');
        if (chatContainer) {
            chatContainer.style.display = 'none';
        }
        
        const resultsDiv = document.getElementById('modal-evaluation-results');
        if (!resultsDiv) return;
        
        resultsDiv.style.display = 'block';
        
        const evaluation = data.evaluation || data;
        const overallScore = evaluation.overall_score ? evaluation.overall_score.toFixed(1) : '—';
        const feedback = evaluation.feedback || '';
        const strengths = evaluation.strengths || [];
        const improvements = evaluation.improvements || [];
        
        const pronunciation = evaluation.pronunciation_score;
        const grammar = evaluation.grammar_score;
        const vocabulary = evaluation.vocabulary_score;
        const fluency = evaluation.fluency_score;
        const taskCompletion = evaluation.task_completion_score;
        
        resultsDiv.innerHTML = `
            <div class="evaluation-results-content">
                <h3>Результати оцінювання</h3>
                <div class="score-circle">${overallScore}/10</div>
                
                ${(pronunciation || grammar || vocabulary || fluency || taskCompletion) ? `
                    <div class="detailed-scores">
                        ${pronunciation ? `<div class="score-item">Pronunciation: ${pronunciation.toFixed(1)}/10</div>` : ''}
                        ${grammar ? `<div class="score-item">Grammar: ${grammar.toFixed(1)}/10</div>` : ''}
                        ${vocabulary ? `<div class="score-item">Vocabulary: ${vocabulary.toFixed(1)}/10</div>` : ''}
                        ${fluency ? `<div class="score-item">Fluency: ${fluency.toFixed(1)}/10</div>` : ''}
                        ${taskCompletion ? `<div class="score-item">Task Completion: ${taskCompletion.toFixed(1)}/10</div>` : ''}
                    </div>
                ` : ''}
                
                ${feedback ? `<div class="feedback-text">${this.escapeHtml(feedback)}</div>` : ''}
                
                ${strengths.length > 0 ? `
                    <div class="strengths-section">
                        <h4>✅ Ваші сильні сторони:</h4>
                        <ul>
                            ${strengths.map(s => `<li>${this.escapeHtml(s)}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                ${improvements.length > 0 ? `
                    <div class="improvements-section">
                        <h4>📝 Де можна поліпшити:</h4>
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
    
    showFinishSuggestion() {
        const responseText = document.getElementById('modal-response-text');
        if (responseText) {
            responseText.innerHTML = '<p class="finish-suggestion">AI recommends finishing. Ready to evaluate?</p>';
        }
    }
    
    showError(message) {
        const responseText = document.getElementById('modal-response-text');
        if (responseText) {
            responseText.innerHTML = `<p class="error-message">${this.escapeHtml(message)}</p>`;
        }
    }
    
    scrollToBottom() {
        const chatHistory = document.getElementById('modal-chat-history');
        if (chatHistory) {
            setTimeout(() => {
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }, 0);
        }
    }
    
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
