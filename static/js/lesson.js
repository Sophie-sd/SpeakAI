/**
 * Lesson interactions: tabs, homework submission, voice practice
 */

import { fetchWithCsrf } from './utils.js';

document.addEventListener('DOMContentLoaded', function() {
    initTabSystem();
    initHomeworkSubmission();
    initVoicePractice();
    initRolePlay();
});

// ============= TAB SYSTEM =============

function initTabSystem() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            
            // Remove active from all
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active to clicked
            this.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
        });
    });
}

// ============= HOMEWORK SUBMISSION =============

function initHomeworkSubmission() {
    const submitButton = document.querySelector('.btn-submit-homework');
    if (!submitButton) return;
    
    submitButton.addEventListener('click', submitHomework);
}

async function submitHomework() {
    const lessonId = document.querySelector('.btn-submit-homework').dataset.lessonId;
    const homeworkText = document.getElementById('homework-input').value.trim();
    const feedbackDiv = document.getElementById('homework-feedback');
    
    if (!homeworkText) {
        showError(feedbackDiv, 'Please write your homework before submitting.');
        return;
    }
    
    // Show loading state
    showLoading(feedbackDiv, 'Submitting homework for AI review...');
    
    try {
        const response = await fetch(`/chat/lesson/${lessonId}/check-homework/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ homework: homeworkText })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displayHomeworkFeedback(feedbackDiv, result);
        } else {
            showError(feedbackDiv, result.error || 'Failed to evaluate homework.');
        }
    } catch (error) {
        console.error('Error:', error);
        showError(feedbackDiv, 'Network error. Please try again.');
    }
}

function displayHomeworkFeedback(container, result) {
    container.innerHTML = `
        <div class="feedback-card">
            <div class="feedback-score">
                <span class="score-value">${result.score ? result.score.toFixed(1) : '—'}/10</span>
                <span class="score-label">Your Score</span>
            </div>
            
            ${result.feedback ? `
                <div class="feedback-section">
                    <h4>Feedback</h4>
                    <p>${result.feedback}</p>
                </div>
            ` : ''}
            
            ${result.strengths && result.strengths.length > 0 ? `
                <div class="feedback-section strengths">
                    <h4>✓ Strengths</h4>
                    <ul>
                        ${result.strengths.map(s => `<li>${s}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${result.improvements && result.improvements.length > 0 ? `
                <div class="feedback-section improvements">
                    <h4>📝 Areas to Improve</h4>
                    <ul>
                        ${result.improvements.map(i => `<li>${i}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${result.errors && result.errors.length > 0 ? `
                <div class="feedback-section errors">
                    <h4>⚠️ Grammar/Vocabulary Issues</h4>
                    <ul>
                        ${result.errors.map(e => `
                            <li>
                                <strong>"${e.original}"</strong> → <em>"${e.correction}"</em>
                                <br><small>${e.explanation}</small>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${result.next_step ? `
                <div class="feedback-section next-step">
                    <h4>🎯 Next Step</h4>
                    <p>${result.next_step}</p>
                </div>
            ` : ''}
        </div>
    `;
    container.classList.add('visible');
}

// ============= VOICE PRACTICE =============

function initVoicePractice() {
    const startButton = document.querySelector('.btn-start-voice');
    if (!startButton) return;
    
    startButton.addEventListener('click', function() {
        const lessonId = this.dataset.lessonId;
        if (window.lessonVoiceModal) {
            window.lessonVoiceModal.open(lessonId, 'voice_practice');
        } else {
            console.error('lessonVoiceModal not initialized');
        }
    });
}

function initRolePlay() {
    const startButton = document.querySelector('.btn-start-roleplay');
    if (!startButton) return;
    
    startButton.addEventListener('click', function() {
        const lessonId = this.dataset.lessonId;
        if (window.lessonVoiceModal) {
            window.lessonVoiceModal.open(lessonId, 'roleplay');
        } else {
            console.error('lessonVoiceModal not initialized');
        }
    });
}

async function startVoicePractice() {
    const prompts = document.querySelectorAll('#voice-prompts-list li');
    
    if (prompts.length === 0) {
        alert('No voice prompts available for this lesson.');
        return;
    }
    
    const practiceArea = document.getElementById('voice-practice-area');
    let currentPromptIndex = 0;
    const userResponses = [];
    
    renderVoicePracticeInterface(practiceArea, prompts, currentPromptIndex, userResponses);
}

function renderVoicePracticeInterface(container, prompts, currentIndex, responses) {
    const prompt = prompts[currentIndex];
    const isLast = currentIndex === prompts.length - 1;
    
    container.innerHTML = `
        <div class="voice-practice-interface">
            <div class="practice-progress">
                <span class="progress-text">Prompt ${currentIndex + 1} of ${prompts.length}</span>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${((currentIndex) / prompts.length) * 100}%"></div>
                </div>
            </div>
            
            <div class="current-prompt">
                <h4>Practice this:</h4>
                <p class="prompt-text">${prompt.textContent}</p>
            </div>
            
            <div class="recording-section">
                <button class="btn-record" id="recordBtn">🎤 Start Recording</button>
                <button class="btn-stop" id="stopBtn" style="display:none;">⏹️ Stop Recording</button>
                <div id="recorder-visualization"></div>
            </div>
            
            <div class="practice-controls">
                ${currentIndex > 0 ? `
                    <button class="btn-prev" onclick="window.voicePracticeState.previousPrompt()">← Previous</button>
                ` : ''}
                
                ${!isLast ? `
                    <button class="btn-next" onclick="window.voicePracticeState.nextPrompt()" style="opacity:0.5;" disabled>
                        Next →
                    </button>
                ` : `
                    <button class="btn-submit" onclick="window.voicePracticeState.submitResponses()">
                        ✓ Submit Responses
                    </button>
                `}
            </div>
        </div>
    `;
    
    // Store state globally for button handlers
    window.voicePracticeState = {
        container,
        prompts,
        currentIndex,
        responses,
        nextPrompt: function() {
            if (this.currentIndex < this.prompts.length - 1) {
                this.currentIndex++;
                renderVoicePracticeInterface(this.container, this.prompts, this.currentIndex, this.responses);
                setupRecording();
            }
        },
        previousPrompt: function() {
            if (this.currentIndex > 0) {
                this.currentIndex--;
                renderVoicePracticeInterface(this.container, this.prompts, this.currentIndex, this.responses);
                setupRecording();
            }
        },
        submitResponses: async function() {
            await submitVoicePractice(this.responses);
        }
    };
    
    setupRecording();
}

function setupRecording() {
    // Simplified recording setup - actual implementation would use getUserMedia API
    const recordBtn = document.getElementById('recordBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (!recordBtn) return;
    
    recordBtn.addEventListener('click', () => {
        recordBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
        console.log('Recording started...');
        // TODO: Implement actual audio recording
    });
    
    stopBtn.addEventListener('click', () => {
        recordBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
        const response = '[Voice recording placeholder]';
        window.voicePracticeState.responses[window.voicePracticeState.currentIndex] = response;
        
        // Enable next button
        const nextBtn = document.querySelector('.btn-next');
        if (nextBtn) {
            nextBtn.disabled = false;
            nextBtn.style.opacity = '1';
        }
        
        console.log('Recording stopped. Response saved:', response);
    });
}

async function submitVoicePractice(responses) {
    const lessonId = document.querySelector('.btn-start-voice').dataset.lessonId;
    
    if (responses.length === 0) {
        alert('Please record responses for all prompts.');
        return;
    }
    
    try {
        const response = await fetch(`/chat/lesson/${lessonId}/voice-practice/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ responses })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displayVoicePracticeFeedback(result);
        } else {
            alert(result.error || 'Failed to evaluate voice practice.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Network error. Please try again.');
    }
}

function displayVoicePracticeFeedback(result) {
    const container = document.getElementById('voice-practice-area');
    
    container.innerHTML = `
        <div class="voice-feedback-card">
            <div class="overall-score">
                <span class="score-value">${result.overall_score ? result.overall_score.toFixed(1) : '—'}/10</span>
                <span class="score-label">Overall Score</span>
            </div>
            
            ${result.feedback ? `
                <div class="feedback-section">
                    <h4>Feedback</h4>
                    <p>${result.feedback}</p>
                </div>
            ` : ''}
            
            ${result.strengths && result.strengths.length > 0 ? `
                <div class="feedback-section">
                    <h4>✓ Strengths</h4>
                    <ul>
                        ${result.strengths.map(s => `<li>${s}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${result.improvements && result.improvements.length > 0 ? `
                <div class="feedback-section">
                    <h4>📝 Areas to Improve</h4>
                    <ul>
                        ${result.improvements.map(i => `<li>${i}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            <button class="btn-try-again" onclick="window.location.reload()">Try Again</button>
        </div>
    `;
}

// ============= UTILITY FUNCTIONS =============

function showLoading(container, message) {
    container.innerHTML = `<div class="loading"><p>${message}</p></div>`;
    container.classList.add('visible');
}

function showError(container, message) {
    container.innerHTML = `<div class="error"><p>❌ ${message}</p></div>`;
    container.classList.add('visible');
}

function getCookie(name) {
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
