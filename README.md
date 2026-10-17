# 🌐 LinguaSync: Real-Time AI Voice Translator

<div align="center">

![LinguaSync Banner](https://img.shields.io/badge/LinguaSync-Real--Time%20Voice%20Translator-7c3aed?style=for-the-badge)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Deepgram](https://img.shields.io/badge/Deepgram-STT%20%26%20TTS-13EF93?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-gpt--oss--120b-F55036?style=for-the-badge)

<p align="center">
  A sleek, real-time, bidirectional voice translator with a futuristic glassmorphic UI. Speak in one language, see live streaming transcriptions, translate via ultra-fast LLMs, and listen to spoken translations with automated turn-taking.
</p>

</div>

---

## ✨ Features

- **🎙️ Real-Time Streaming STT (Deepgram Nova-2)**:
  - Streams microphone audio chunk-by-chunk via WebSockets (`wss://api.deepgram.com/v1/listen`).
  - Live interim transcriptions as you speak, with smart formatting and VAD endpointing.
- **🧠 Ultra-Fast Neural Translation (Groq)**:
  - Powered by `openai/gpt-oss-120b` for instant, context-aware translation.
  - Zero fluff or meta-commentary—pure, accurate interpretation.
- **🔊 Hybrid High-Fidelity TTS**:
  - **Deepgram Aura**: Natural, lifelike speech synthesis (`aura-asteria-en`, `aura-2-aquila-es`, etc.).
  - **Native Hindi Engine**: Dedicated native speech synthesis (`hi-IN`) for authentic, flawless Devanagari Hindi pronunciation.
  - Automatic fallback to browser `speechSynthesis` ensures voice playback never fails.
- **🔄 Auto-Turn Conversation Mode**:
  - Automatically alternates the active microphone between Speaker A and Speaker B once translation playback finishes.
  - Enables hands-free, seamless two-way dialogue without manual button clicks.
- **🛡️ Persistent Microphone Stream**:
  - Solves browser permission fatigue on `file://` and local origins by retaining an active audio stream across the session.
- **🎨 Glassmorphic Aesthetic**:
  - Modern dark mode with floating ambient orbs, responsive glass cards, animated real-time audio waveforms, and full conversation history.

---

## 🛠️ Architecture & Pipeline

```text
Speaker A speaks (e.g. English)
    │
    ▼
MediaRecorder (WebM/Opus Chunks)
    │
    ▼
Deepgram WebSocket (Nova-2 STT)
    │  └─► Live interim text displayed
    ▼
Speech Final / Utterance End
    │
    ▼
Groq API (openai/gpt-oss-120b)
    │  └─► Translates English ➔ Hindi
    ▼
TTS Engine (Native Hindi / Deepgram Aura)
    │  └─► Speaks translation aloud through speaker
    ▼
Auto-Turn Trigger
    │
    ▼
Microphone switches to Speaker B (Hindi) automatically!
```

---

## 🚀 Quick Start

### 1. Requirements
- A modern web browser (Google Chrome, Microsoft Edge, Brave, etc.).
- API Keys:
  - **[Deepgram API Key](https://console.deepgram.com/)** (Used for Nova-2 STT and Aura TTS).
  - **[Groq API Key](https://console.groq.com/)** (Used for `openai/gpt-oss-120b` translation).

### 2. Running the App

You can run LinguaSync directly without any build step:

#### Option A: Direct File Open
Double-click `index.html` or open it directly in your browser:
```text
file:///path/to/real-time-voice-translator/index.html
```

#### Option B: Local Static Server (Recommended)
Using Python or Node static server:
```bash
# Using Python
python -m http.server 3000

# OR using npx serve
npx serve .
```
Then navigate to `http://localhost:3000` in your browser.

---

## 🔑 Configuration

1. Open `index.html`.
2. Enter your **Deepgram API Key** and **Groq API Key** in the top configuration card.
3. Click **Connect** (keys are saved securely in your browser's `localStorage` for future visits).
4. Select the desired languages for **Speaker A** and **Speaker B** (default: English ↔ Hindi).

---

## 🗣️ Supported Languages

LinguaSync supports bidirectional translation across major global languages, including:
- 🇬🇧 English (`en`)
- 🇮🇳 Hindi (`hi`)
- 🇪🇸 Spanish (`es`)
- 🇫🇷 French (`fr`)
- 🇩🇪 German (`de`)
- 🇨🇳 Chinese (`zh`)
- 🇯🇵 Japanese (`ja`)
- 🇰🇷 Korean (`ko`)
- 🇷🇺 Russian (`ru`)
- 🇸🇦 Arabic (`ar`)
- 🇧🇷 Portuguese (`pt`)
- 🇮🇹 Italian (`it`)
- 🇹🇷 Turkish (`tr`)
- 🇳🇱 Dutch (`nl`)
- 🇵🇱 Polish (`pl`)
- 🇸🇪 Swedish (`sv`)
- 🇺🇦 Ukrainian (`uk`)
- 🇮🇩 Indonesian (`id`)

---

## 💡 Controls

| Control | Function |
|---|---|
| **🎤 Record / ⬛ Stop** | Start or stop listening on that speaker's channel. |
| **🔄 Auto-Turn** | Toggle automatic switching of turns between Speaker A and Speaker B. |
| **⇄ Swap** | Instantly swap the languages of Speaker A and Speaker B. |
| **🔊 Replay** | Replay the latest spoken translation. |
| **🗑️ Clear** | Clear speech and translation text from the panel. |

---

## 📄 License

This project is licensed under the MIT License.
