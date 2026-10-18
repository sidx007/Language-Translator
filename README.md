# 🌐 LinguaSync: 100% Local AI Voice Translator

<div align="center">

![LinguaSync Banner](https://img.shields.io/badge/LinguaSync-100%25%20Local%20Voice%20Translator-7c3aed?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Faster--Whisper](https://img.shields.io/badge/Faster--Whisper-STT%20(int8)-00d4aa?style=for-the-badge)
![MarianMT](https://img.shields.io/badge/MarianMT-Neural%20Translation-6c63ff?style=for-the-badge)
![pyttsx3](https://img.shields.io/badge/pyttsx3-Local%20TTS-f43f5e?style=for-the-badge)
![RAM](https://img.shields.io/badge/RAM-8GB%20Optimized-success?style=for-the-badge)

<p align="center">
  A state-of-the-art, <b>100% local, bidirectional voice translator</b> with a futuristic glassmorphic UI. Runs completely on your local machine with <b>zero external API keys or cloud dependencies</b>, specifically optimized to operate smoothly on <b>8GB RAM</b> CPU systems.
</p>

</div>

---

## ✨ Key Capabilities & Dual Engine Modes

LinguaSync features a seamless **Mode Switcher** directly in the UI header, letting you toggle with a single click between **100% Local AI** and **High-Performance Cloud APIs**:

### 💻 1. Local AI Mode (Offline & Private)
- **Zero External Dependencies**: Operates 100% on CPU without API keys, subscriptions, or external network requests.
- **Speech-to-Text**: `faster-whisper-small` (int8) powered by CTranslate2. Transcribes Hindi in native Devanagari script and English with low latency.
- **Neural Machine Translation**: `Helsinki-NLP / MarianMT` offline models with an intelligent LRU memory cache (<600MB footprint) and English pivot translation for cross-lingual pairs.
- **Text-to-Speech**: Local Windows SAPI5 engine via `pyttsx3` with client-side Web Speech API OS voice fallback.
- **8GB RAM Budget**: Hardware telemetry actively monitors memory usage to keep total consumption well within 8GB RAM.

### ☁️ 2. Online APIs Mode (Cloud Power)
- **Deepgram nova-2 STT**: Real-time streaming WebSocket speech recognition with intelligent endpointing and VAD.
- **Groq LLM (openai/gpt-oss-120b)**: Instantaneous neural translations powered by `openai/gpt-oss-120b` on Groq's high-speed inference engine.
- **Deepgram Aura + Google TTS**: High-fidelity natural voice synthesis (Deepgram Aura models for English/European languages and Google TTS audio stream for Hindi).
- **Persistent Key Storage**: Securely stores API keys locally in browser `localStorage`.

### 🔄 Shared Features Across Both Modes
- **Dual-Channel Live Waveforms**: Real-time microphone level animation on both speaker channels.
- **Auto-Turn Conversation**: Automatically switches the microphone between speakers after voice playback finishes for hands-free chatting.
- **Tagged Conversation History**: Logs every utterance with clickable replay and `[💻 Local]` / `[☁️ Cloud]` mode indicators.

---

## 🏗️ System Architecture

```text
Speaker A speaks into Microphone
    │
    ▼
MediaRecorder (Audio chunks / Opus / WebM)
    │
    ▼
Local Backend Server (FastAPI on http://127.0.0.1:8000)
    ├─► /ws/transcribe & /api/transcribe
    │    └─► Faster-Whisper (Tiny int8 on CPU) ➔ Transcribed Text
    │
    ├─► /api/translate
    │    └─► MarianMT Neural MT (LRU Cached, <600MB footprint) ➔ Translated Text
    │
    └─► /api/tts
         └─► pyttsx3 / Windows SAPI5 ➔ Local WAV Audio Stream
    │
    ▼
Browser plays translated voice audio
    │
    ▼
Auto-Turn Handler: Automatically activates Speaker B's microphone!
```

---

## 🚀 Getting Started

### 1. Requirements
- Windows, macOS, or Linux.
- Python 3.10+ (tested on Python 3.12).
- 8GB RAM or more.

### 2. Set Up a Virtual Environment (`venv`)
> [!IMPORTANT]
> A dedicated Python virtual environment (`venv`) is required to isolate dependencies (`faster-whisper`, `ctranslate2`, `torch`, `transformers`) and prevent package version collisions.

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell blocks script execution, first enable remote signed scripts: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Ensure your virtual environment is active (you will see `(venv)` in your terminal prompt), then run:
```bash
pip install -r requirements.txt
```

### 4. Start the Backend Server
With your virtual environment active:

- **Using the One-Click Launcher**:
  - Double click **`start_server.bat`** (Command Prompt), or run `./start_server.ps1` (PowerShell).
  - The script automatically detects and activates your `venv`, starts the server, and opens your browser.

- **Or start manually**:
  ```bash
  python server.py
  ```
  The server will initialize on `http://127.0.0.1:8000`.

### 5. Open the Application
Navigate to:
```text
http://127.0.0.1:8000/
```
*(Always open via `http://127.0.0.1:8000/` instead of `file:///` so your browser can grant microphone access in a secure context).*

---

## 📡 Backend API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/status` | `GET` | Health check, CPU/RAM usage, and loaded model status |
| `/api/transcribe` | `POST` | Transcribes uploaded audio file (`file: UploadFile`, `lang: str`) |
| `/ws/transcribe` | `WebSocket` | Real-time audio streaming transcription |
| `/api/translate` | `POST` | Neural translation (`{ text, source_lang, target_lang }`) |
| `/v1/chat/completions` | `POST` | OpenAI-compatible translation completion endpoint |
| `/api/tts` | `GET` / `POST` | Synthesizes text to local WAV audio stream |
| `/` | `GET` | Serves the LinguaSync frontend web application |

---

## 🛡️ License
MIT License. Open source and free for personal and commercial use.
