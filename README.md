# AI English Tutor - PWA Application

Complete Progressive Web Application for English language learning with AI tutor featuring 3 interaction modes: Text Chat, Voice Chat, and Avatar Mode.

## Features

✅ **3 Learning Modes:**
- **Text Chat Mode**: Conversational AI with contextual image support
- **Voice Chat Mode**: Speech-to-Text → AI Response → Text-to-Speech with 3-bar visualizer (ChatGPT style)
- **Avatar Mode**: Real-time video avatar that syncs with audio responses

✅ **Advanced AI Features:**
- Google Gemini API for intelligent responses
- RAG (Retrieval Augmented Generation) with internal knowledge base
- Adaptive learning that remembers student profile per user
- Context-aware responses based on student level

✅ **Built with:**
- Django 6.0
- Vanilla JavaScript (no frameworks)
- HTMX for dynamic interactions
- PostgreSQL with pgvector (production)
- Google Cloud APIs (Speech-to-Text, Text-to-Speech)
- Cloudinary for media storage

✅ **Mobile First & PWA:**
- Fully responsive design
- Installable as native app
- Service Worker for offline assets
- Touch-optimized interface

---

## Quick Start

### 1. Setup Development Environment

```bash
# Clone repository
git clone <your-repo>
cd "AI English"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file:

```env
DEBUG=True
SECRET_KEY=your-secret-key

# Google Gemini API
GEMINI_API_KEY=your_gemini_key_from_ai.google.dev

# Google Cloud (for STT/TTS)
# 1. Create project in Google Cloud Console
# 2. Enable APIs: Cloud Speech-to-Text, Cloud Text-to-Speech
# 3. Create Service Account and download JSON key
# 4. Set environment variable:
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Cloudinary (for media storage)
CLOUDINARY_URL=cloudinary://your_credentials@cloud_name
```

### 3. Setup Database & Load Initial Data

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Populate knowledge base with English grammar & vocabulary
python manage.py populate_knowledge_base

# Generate embeddings for RAG (requires GEMINI_API_KEY)
python manage.py generate_embeddings
```

### 4. Run Development Server

```bash
python manage.py runserver
```

Access at: http://127.0.0.1:8000/users/login/

**Default test account:**
- Username: admin
- Password: admin

---

## Architecture

### 3 Interaction Modes

```
User Entry
    ├─ Text Mode (💬)
    │  ├─ HTMX Chat Interface
    │  ├─ Gemini API Response
    │  └─ RAG: Search Knowledge Base first
    │
    ├─ Voice Mode (🎤)
    │  ├─ MediaRecorder: Capture user audio
    │  ├─ Google Speech-to-Text: Convert to text
    │  ├─ Gemini API: Generate response
    │  ├─ Google Text-to-Speech: Convert to audio
    │  └─ 3-Bar Visualizer: Animate with frequency data
    │
    └─ Avatar Mode (🎭)
       ├─ Same as Voice Mode
       ├─ + Video Player (idle.mp4 / talking.mp4)
       └─ Sync video state with audio playback
```

### Database Models

- **CustomUser**: Extends Django User with level (A1-C2), subscription status
- **ChatSession**: Groups messages per conversation
- **ChatMessage**: Individual messages (user/model)
- **KnowledgeBase**: Lessons, grammar rules, vocab (with embeddings)
- **Memory**: User learning history, mistakes, interests
- **Avatar**: Video URL configuration for avatar mode

### Knowledge Base (RAG) Flow

```
User Query
    ↓
Generate Embedding (Gemini API)
    ↓
Search KnowledgeBase (pgvector, similarity)
    ↓
Inject Top 3 Results into System Prompt
    ↓
Query Gemini with Enhanced Context
    ↓
Return Response
```

---

## Deployment to Render

### Prerequisites

1. **GitHub Repository**: Push code to GitHub
2. **PostgreSQL**: Use Render's managed database or create separately
3. **Environment Variables**: All API keys configured

### Steps

1. **Create Render Account**: https://render.com/
2. **Create PostgreSQL Database**:
   - Type: PostgreSQL
   - Plan: Starter (free tier)
   - Note the DATABASE_URL

3. **Create Web Service**:
   - Connect GitHub repo
   - Build Command: `bash build.sh`
   - Start Command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
   - Environment Variables:
     ```
     DEBUG=False
     DJANGO_SETTINGS_MODULE=config.settings
     SECRET_KEY=<generate-strong-key>
     DATABASE_URL=<from-postgres>
     GEMINI_API_KEY=<your-key>
     GOOGLE_APPLICATION_CREDENTIALS=<path-or-json>
     CLOUDINARY_URL=<your-url>
     ```

4. **Post-Deploy Commands**:
   ```bash
   python manage.py migrate
   python manage.py populate_knowledge_base
   python manage.py generate_embeddings
   ```

---

## API Keys Setup

### Google Gemini API
- Go to: https://ai.google.dev/
- Create API key
- Free tier available

### Google Cloud (Speech-to-Text + Text-to-Speech)
- Go to: https://cloud.google.com/
- Create project
- Enable APIs: Cloud Speech-to-Text, Cloud Text-to-Speech
- Create Service Account
- Download JSON key
- Set `GOOGLE_APPLICATION_CREDENTIALS` to path/JSON

### Cloudinary (Media Storage)
- Go to: https://cloudinary.com/
- Sign up (free plan available)
- Get `CLOUDINARY_URL` from dashboard
- Set in .env

---

## File Structure

```
/
├── manage.py
├── requirements.txt
├── build.sh                    # Render build script
├── render.yaml                # Render config
├── .env                        # Environment variables
├── config/
│  ├── settings.py             # Django settings
│  ├── urls.py
│  └── wsgi.py
├── apps/
│  ├── users/
│  │  ├── models.py            # CustomUser
│  │  ├── views.py
│  │  └── urls.py
│  ├── chat/
│  │  ├── models.py            # Chat, KnowledgeBase, Memory
│  │  ├── views.py             # chat_view, send_message
│  │  ├── services/
│  │  │  └── gemini.py         # GeminiService (RAG, LLM)
│  │  ├── management/commands/
│  │  │  ├── populate_knowledge_base.py
│  │  │  └── generate_embeddings.py
│  │  └── urls.py
│  └── voice/
│     ├── models.py            # Avatar
│     ├── views.py             # voice_mode, avatar_mode, process_audio
│     ├── services/
│     │  └── speech.py         # SpeechService (STT, TTS)
│     └── urls.py
├── static/
│  ├── css/
│  │  ├── style.css            # Base styles
│  │  ├── chat.css             # Chat mode styles
│  │  ├── voice.css            # Voice mode styles
│  │  └── avatar.css           # Avatar mode styles
│  └── js/
│     ├── recorder.js          # Audio recording
│     ├── bars-visualizer.js   # ChatGPT-style 3-bar visualizer
│     ├── avatar.js            # Avatar video control
│     └── main.js              # Global functionality
└── templates/
   ├── base.html               # Layout with navigation
   ├── chat/
   │  ├── index.html           # Chat interface
   │  └── partials/
   │     └── new_messages.html
   ├── voice/
   │  ├── voice-only.html      # Voice-only mode
   │  └── avatar.html          # Avatar mode
   └── users/
      ├── login.html
      └── register.html
```

---

## Troubleshooting

### "pgvector not found" on Render
- Render's PostgreSQL has pgvector pre-installed
- Locally, for testing: Use SQLite (default)
- For local PostgreSQL: Install pgvector extension

### "Google API key not found"
- Ensure `.env` has `GEMINI_API_KEY=your_key`
- For Speech-to-Text: Set `GOOGLE_APPLICATION_CREDENTIALS`
- Generate embeddings will fail silently if key missing

### Avatar videos not loading
- Ensure `Avatar` model has `idle_video` and `talking_video` URLs
- Test URLs are accessible (e.g., from Cloudinary)
- Check CORS settings if using external CDN

### Voice recording not working on production
- HTTPS required for getUserMedia (WebRTC)
- Render provides HTTPS automatically
- Check browser permissions for microphone

---

## Next Steps (Roadmap)

- [ ] Payment integration (Stripe)
- [ ] Multiple avatar personas
- [ ] Pronunciation assessment with Speech Recognition API
- [ ] Offline mode improvements
- [ ] Audio/video caching in Service Worker
- [ ] User progress dashboard
- [ ] Mobile native app wrapper (React Native/Flutter)

---

## Support

For issues or feature requests, please open an issue on GitHub.

---

**Developed with** ❤️ **for English learners worldwide**
