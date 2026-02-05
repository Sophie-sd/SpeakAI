# AI English Tutor PWA — Project Specification

## 1. Project Overview
**Goal**: Create a cross-platform Progressive Web Application (PWA) that acts as an AI English Tutor.
**Core Philosophy**: "Framework-less Frontend" (Django + HTML + CSS + JS + HTMX) with advanced AI backend capabilities.
**Target Audience**: English learners who need personalized practice (Text, Voice, Avatar).

## 2. Technical Stack & Rules
*   **Backend**: Django 5.x (Python).
*   **Database**: PostgreSQL (Production) / SQLite (Dev) + `pgvector` for RAG.
*   **Frontend**:
    *   **HTML5/CSS3**: No CSS frameworks (e.g., Bootstrap, Tailwind) unless strictly necessary for utility. Custom BEM/Scoped CSS.
    *   **JS**: Vanilla JavaScript (ES6+). No React/Vue/Angular.
    *   **HTMX**: For dynamic interactions (chat updates, swapping views) without full page reloads.
*   **AI Engine**:
    *   **LLM**: Google Gemini Pro (via `google-generativeai`).
    *   **Embeddings**: Google Gemini Embeddings (for internal Knowledge Base retrieval).
    *   **Voice**: Google Cloud TTS (Text-to-Speech) & Web Speech API / Google STT (Speech-to-Text).
*   **Hosting**: Render (Web Service).
*   **Storage**: Cloudinary (for Avatar videos & lesson images).

### Constraints
1.  **Mobile First**: The UI must be fully responsive and feel like a native app on mobile.
2.  **PWA**: Must be installable (Manifest, Service Worker).
3.  **Permissions**: Graceful handling of Camera/Microphone permissions.
4.  **No Conflicts**: CSS and JS must be modular to avoid conflicts between HTMX swaps and global styles.

## 3. Core Features & Modes

### A. Authentication & Subscription
*   **Custom User Model**: Tracks level (A1-C2), native language, and subscription status.
*   **Subscription Logic**: Middleware checks `user.is_paid`. If false, redirect to payment/subscription page.

### B. Adaptive Learning Engine (The "Brain")
*   **Long-term Memory**: The system remembers:
    *   Vocabulary learned vs. forgotten.
    *   Common grammatical errors.
    *   Personal interests (e.g., "likes football").
*   **Implementation**: A `Memory` model that stores summaries of past sessions. These summaries are injected into the System Prompt for future sessions.

### C. Internal Knowledge Base (RAG)
*   **Priority**: The AI *must* prioritize the internal database over its general training data.
*   **Mechanism**:
    1.  Admin uploads structured lessons/vocabulary to `KnowledgeBase`.
    2.  Content is embedded (vectorized) and stored in DB.
    3.  On user query -> Convert query to vector -> Search DB (Cosine Similarity) -> Inject top 3 matches into context -> Query Gemini.

### D. Interaction Modes (The 3 Ways to Learn)

#### Mode 1: Text Chat + Visuals (Low Bandwidth)
*   **UI**: Standard chat bubbles.
*   **Media**: If the internal DB result has an associated image (e.g., "apple"), the AI response includes a special tag or the backend injects the `<img>` automatically.
*   **Tech**: HTMX `hx-post` for sending messages, `hx-swap="beforeend"` for appending messages.

#### Mode 2: Voice Chat + Visualizer
*   **UI**: Minimalist. Big "Hold to Speak" button.
*   **Visualizer**: A dynamic audio wave animation (using HTML5 Canvas + Web Audio API `AnalyserNode`) that reacts to the AI's voice frequency.
*   **Interaction**:
    *   User holds button -> `MediaRecorder` captures audio.
    *   Release button -> POST audio blob to Django.
    *   Server processes -> Returns JSON (Audio URL + Text).
    *   Frontend plays audio -> Visualizer animates.

#### Mode 3: AI Avatar (Video Loop)
*   **Goal**: Realistic "Video Call" experience without expensive real-time video generation APIs.
*   **Technique (Video Loop Switching)**:
    *   **State A (Idle)**: Loop of the avatar listening/breathing (~3s).
    *   **State B (Talking)**: Loop of the avatar speaking (lip movement).
*   **Logic**:
    *   Default: Play `Idle.mp4` (loop).
    *   When AI Audio starts playing: Seamlessly switch `src` or cross-fade to `Talking.mp4`.
    *   When AI Audio ends: Switch back to `Idle.mp4`.

## 4. Database Schema (Simplified)

```python
class UserProfile(models.Model):
    level = models.CharField(...)
    subscription_active = models.BooleanField(default=False)

class KnowledgeBase(models.Model):
    topic = models.CharField(...)
    content = models.TextField()
    embedding = VectorField() # pgvector
    image = models.ImageField(null=True)

class Memory(models.Model):
    user = models.ForeignKey(User, ...)
    fact = models.TextField() # e.g. "User struggles with Past Perfect"
    created_at = models.DateTimeField(auto_now_add=True)
```

## 5. Implementation Roadmap

### Phase 1: Foundation
1.  Setup Django + PostgreSQL.
2.  Configure Google Gemini API key.
3.  Implement User Auth & Basic Models.

### Phase 2: Core Logic (RAG & Chat)
1.  Implement `GeminiService` (Prompt engineering + Context injection).
2.  Build the Text Chat interface (HTML/CSS/HTMX).
3.  Test Image injection from DB.

### Phase 3: Voice & Avatar
1.  Build frontend Audio Recorder (JS).
2.  Implement `VoiceView` (STT -> Gemini -> TTS).
3.  Build the Avatar Player (Video switching logic).
4.  Build the Audio Visualizer (Canvas).

### Phase 4: PWA & Polish
1.  Add `manifest.json` & icons.
2.  Add `service-worker.js` (caching assets).
3.  Testing on real mobile devices.

## 6. Directory Structure (Proposed)
```
/
├── manage.py
├── project/
│   ├── settings/ (base, dev, prod)
│   ├── urls.py
├── apps/
│   ├── core/ (landing, pwa)
│   ├── users/ (auth, profile)
│   ├── chat/ (chat logic, RAG, history)
│   ├── voice/ (audio processing, TTS/STT)
├── static/
│   ├── css/ (main.css, chat.css, avatar.css)
│   ├── js/ (recorder.js, visualizer.js, avatar.js)
│   ├── img/
├── templates/
│   ├── base.html
│   ├── chat/
```
