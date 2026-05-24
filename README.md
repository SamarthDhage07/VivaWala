# ⬡ NeuralHire — AI-Powered Voice Interview Platform

A futuristic, fully local AI interview preparation platform. Speak your answers, get instant evaluation, track your performance — all powered by a local LLM with zero data leaving your machine.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎤 Voice Answering | Speak into your mic — Whisper transcribes in real time |
| 🤖 AI Evaluation | Local llama3 scores every answer with strengths & weaknesses |
| 📊 Analytics | NumPy-powered scoring + Matplotlib performance dashboards |
| 💾 Local Storage | All reports saved as JSON, TXT + PNG graphs |
| 🔒 100% Private | No API keys, no cloud — Ollama runs on your machine |
| 🌐 9 Domains | Python, Java, ML, DSA, HR, System Design, DevOps + Custom |

---

## 🖥 Tech Stack

**Backend**
- Python 3.11+
- Flask 3.x + Flask-CORS
- Ollama (llama3 local LLM)
- OpenAI Whisper (local STT)
- SpeechRecognition (fallback STT)
- NumPy — score analytics
- Matplotlib — graph generation

**Frontend**
- HTML5 / CSS3 / Vanilla JS
- Web Audio API (live waveform)
- MediaRecorder API (voice capture)
- Orbitron + Space Mono fonts

---

## 📁 Project Structure

```
ai_interview_bot/
├── app.py                     # Flask app + all routes
├── config.py                  # Central configuration
├── requirements.txt
├── run.sh                     # One-command setup & launch
├── .env.example               # Environment variable template
│
├── backend/
│   ├── __init__.py
│   ├── ollama_client.py       # Ollama LLM integration
│   ├── speech_module.py       # Whisper / SpeechRecognition STT
│   ├── analytics.py           # NumPy analytics + Matplotlib graphs
│   └── file_handler.py        # Save/load reports & sessions
│
├── frontend/
│   ├── templates/
│   │   ├── index.html         # Domain selection screen
│   │   ├── interview.html     # Live chat + voice interface
│   │   └── results.html       # Analytics dashboard
│   └── static/
│       ├── css/
│       │   ├── main.css       # Global dark futuristic theme
│       │   ├── interview.css  # Interview layout styles
│       │   └── results.css    # Results page styles
│       └── js/
│           ├── particles.js   # Background particle animation
│           ├── index.js       # Domain selection logic
│           ├── interview.js   # Voice recording + chat + eval
│           └── results.js     # Results rendering
│
├── utils/
│   └── helpers.py             # Shared utility functions
│
├── reports/                   # Auto-created: session JSON + TXT
└── graphs/                    # Auto-created: PNG analytics charts
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com/download) installed
- Microphone access in browser

### 1. Install Ollama

**macOS / Linux**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows**
Download from [ollama.com/download](https://ollama.com/download)

### 2. Pull the llama3 Model
```bash
ollama pull llama3
```
> This downloads ~4.7 GB. Only needed once.

### 3. Start Ollama Service
```bash
ollama serve
```
Keep this running in a terminal.

### 4. Clone & Run NeuralHire

**One-command setup (Linux/macOS):**
```bash
git clone <repo-url>
cd ai_interview_bot
bash run.sh
```

**Manual setup:**
```bash
cd ai_interview_bot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env

# Run
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🎤 How to Install Whisper

Whisper is the primary speech-to-text engine (most accurate):

```bash
pip install openai-whisper

# Also needs ffmpeg:
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt install ffmpeg

# Windows:
# Download from https://ffmpeg.org/download.html
```

The browser only records audio. Transcription happens in Python through `/api/transcribe`, so the app does not use Chrome's Web Speech API or any Chrome extension for voice recognition.

If Whisper fails at runtime, the system automatically falls back to Google SpeechRecognition (requires internet).

---

## 🧑‍💻 Interview Workflow

```
1. Open http://localhost:5000
2. Select your domain (Python, ML, HR, etc.)
3. Choose number of questions (3–10)
4. Click "BEGIN INTERVIEW"
5. AI asks questions one at a time in the chat
6. Click the 🎤 microphone button
7. Speak your answer clearly
8. Click ⏹ to stop recording
9. Whisper converts speech → text
10. Click "SUBMIT ANSWER"
11. llama3 evaluates your answer → score + feedback
12. Repeat for all questions
13. View your full analytics dashboard
```

---

## 📊 Scoring System

Each answer is scored **0–10** by llama3:

| Score | Grade | Label |
|---|---|---|
| 9–10 | A+ | Excellent |
| 8 | A | Excellent |
| 7 | B+ | Good |
| 6 | B | Good |
| 5 | C | Average |
| 4 | D | Average |
| 0–3 | F | Poor |

**NumPy Analytics computed:**
- Average, median, std deviation
- Performance trend (improving / stable / declining)
- Consistency rating (CV-based)
- Performance buckets (Excellent / Good / Average / Poor)

---

## 🗂 Output Files

After each interview, files are saved in `reports/<session_id>/`:

| File | Contents |
|---|---|
| `session.json` | Full structured session data |
| `transcript.txt` | Human-readable Q&A transcript |
| `report.txt` | Concise performance report |

Graphs saved in `graphs/`:

| File | Contents |
|---|---|
| `<id>_dashboard.png` | 4-panel analytics dashboard |

---

## ⚙️ Configuration

Edit `.env` to customize:

```env
OLLAMA_MODEL=llama3          # Change to llama3:70b for better quality
WHISPER_MODEL=base           # tiny | base | small | medium | large
DEFAULT_NUM_QUESTIONS=7
PORT=5000
DEBUG=true
```

---

## 🛠 Troubleshooting

**"Cannot connect to Ollama"**
→ Run `ollama serve` in a terminal first.

**"llama3 model not found"**
→ Run `ollama pull llama3`

**"Microphone access denied"**
→ Allow microphone in browser settings (click lock icon in URL bar)

**Whisper is slow**
→ Switch to `WHISPER_MODEL=tiny` in `.env` for faster (less accurate) transcription

**No audio on Linux**
→ `sudo apt install portaudio19-dev python3-pyaudio`

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/status` | Check Ollama + system status |
| POST | `/api/start` | Start interview session |
| POST | `/api/transcribe` | Transcribe base64 audio |
| POST | `/api/answer` | Submit + evaluate answer |
| POST | `/api/finish` | Generate final report |
| GET | `/api/session/<id>` | Get session data |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/graph/<id>/<type>` | Serve graph PNG |
| GET | `/api/report/<id>/<type>` | Download report file |

---

## 🙏 Credits

- [Ollama](https://ollama.com) — Local LLM runtime
- [OpenAI Whisper](https://github.com/openai/whisper) — Speech recognition
- [Meta llama3](https://llama.meta.com) — Language model
- Fonts: Orbitron, Space Mono (Google Fonts)
