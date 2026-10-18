"""
Local Real-Time Voice Translator Backend Server
Optimized for 8GB RAM CPU systems.
Services:
1. Speech-to-Text (STT): faster-whisper (tiny int8)
2. Machine Translation (MT): Helsinki-NLP / MarianMT with LRU memory caching & English pivoting
3. Text-to-Speech (TTS): pyttsx3 local Windows SAPI5 audio synthesis
4. OpenAI-compatible /v1/chat/completions endpoint
5. Health and System Resource Monitor (/api/status)
"""

import os
import io
import gc
import wave
import time
import shutil
import asyncio
import logging
import tempfile
import threading
from typing import Optional, Dict, Any, List, Tuple

import psutil
import torch
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LocalTranslatorServer")

# Disable HuggingFace symlinks warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

app = FastAPI(
    title="LinguaSync Local Backend",
    description="All-in-one local STT, Translation, and TTS backend for 8GB RAM systems",
    version="2.0.0"
)

# Enable CORS for all local origins and file://
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═════════════════════════════════════════════════════════════════════
# 1. LOCAL SPEECH-TO-TEXT (faster-whisper)
# ═════════════════════════════════════════════════════════════════════
class STTEngine:
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        self.model_size = os.environ.get("WHISPER_MODEL", model_size)
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._lock = threading.Lock()

        # Script conditioning prompts to ensure Whisper outputs in the native script (e.g. Devanagari for Hindi)
        self.prompts = {
            "hi": "नमस्ते, यह हिंदी में प्रतिलेखन है।",
            "zh": "这是一段普通话对话。",
            "ja": "これは日本語の会話です。",
            "ar": "هذا تسجيل باللغة العربية.",
            "ru": "Это разговор на русском языке.",
        }

    def get_model(self):
        with self._lock:
            if self.model is None:
                from faster_whisper import WhisperModel
                logger.info(f"Loading faster-whisper ({self.model_size}, {self.compute_type})...")
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                logger.info("faster-whisper loaded successfully.")
            return self.model

    def transcribe_bytes(self, audio_bytes: bytes, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe in-memory audio (WAV, WebM, MP3, etc.) using faster-whisper."""
        if not audio_bytes or len(audio_bytes) < 44:
            return {"text": "", "language": language or "en", "duration": 0.0}

        model = self.get_model()
        audio_stream = io.BytesIO(audio_bytes)
        
        # Normalize language code for Whisper
        whisper_lang = language.split("-")[0].lower() if language else None
        if whisper_lang == "auto" or whisper_lang == "":
            whisper_lang = None

        prompt = self.prompts.get(whisper_lang) if whisper_lang else None

        try:
            segments, info = model.transcribe(
                audio_stream,
                language=whisper_lang,
                task="transcribe",
                initial_prompt=prompt,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400)
            )
            text = " ".join([seg.text.strip() for seg in segments]).strip()
            return {
                "text": text,
                "language": info.language if info else whisper_lang,
                "duration": round(info.duration, 2) if info else 0.0
            }
        except Exception as e:
            logger.error(f"STT transcription error: {e}")
            raise e

stt_engine = STTEngine()

# ═════════════════════════════════════════════════════════════════════
# 2. LOCAL MACHINE TRANSLATION (MarianMT with LRU Memory Management)
# ═════════════════════════════════════════════════════════════════════
class LocalTranslator:
    def __init__(self, max_cached_models: int = 2):
        self.max_cached = max_cached_models
        self.models: Dict[tuple, Any] = {}
        self.lru_order: List[tuple] = []
        self._lock = threading.Lock()

        # Popular direct Helsinki-NLP model mappings
        self.supported_pairs = {
            ("en", "hi"): "Helsinki-NLP/opus-mt-en-hi",
            ("hi", "en"): "Helsinki-NLP/opus-mt-hi-en",
            ("en", "es"): "Helsinki-NLP/opus-mt-en-es",
            ("es", "en"): "Helsinki-NLP/opus-mt-es-en",
            ("en", "fr"): "Helsinki-NLP/opus-mt-en-fr",
            ("fr", "en"): "Helsinki-NLP/opus-mt-fr-en",
            ("en", "de"): "Helsinki-NLP/opus-mt-en-de",
            ("de", "en"): "Helsinki-NLP/opus-mt-de-en",
            ("en", "ru"): "Helsinki-NLP/opus-mt-en-ru",
            ("ru", "en"): "Helsinki-NLP/opus-mt-ru-en",
            ("en", "zh"): "Helsinki-NLP/opus-mt-en-zh",
            ("zh", "en"): "Helsinki-NLP/opus-mt-zh-en",
            ("en", "it"): "Helsinki-NLP/opus-mt-en-it",
            ("it", "en"): "Helsinki-NLP/opus-mt-it-en",
            ("en", "nl"): "Helsinki-NLP/opus-mt-en-nl",
            ("nl", "en"): "Helsinki-NLP/opus-mt-nl-en",
            ("en", "ar"): "Helsinki-NLP/opus-mt-en-ar",
            ("ar", "en"): "Helsinki-NLP/opus-mt-ar-en",
            ("en", "ja"): "Helsinki-NLP/opus-mt-en-jap",
            ("ja", "en"): "Helsinki-NLP/opus-mt-jap-en",
        }

    def _get_model(self, src: str, tgt: str):
        key = (src, tgt)
        with self._lock:
            if key in self.models:
                self.lru_order.remove(key)
                self.lru_order.append(key)
                return self.models[key]

            model_name = self.supported_pairs.get(key)
            if not model_name:
                return None

            # Evict oldest model if cache size reached to save RAM
            if len(self.models) >= self.max_cached and self.lru_order:
                oldest_key = self.lru_order.pop(0)
                logger.info(f"Unloading model {oldest_key} to preserve 8GB RAM budget...")
                if oldest_key in self.models:
                    del self.models[oldest_key]
                gc.collect()

            logger.info(f"Loading MarianMT model {model_name}...")
            from transformers import MarianMTModel, MarianTokenizer
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
            model.eval()

            self.models[key] = (tokenizer, model)
            self.lru_order.append(key)
            return self.models[key]

    def _translate_direct(self, text: str, src: str, tgt: str) -> str:
        pair = self._get_model(src, tgt)
        if not pair:
            raise ValueError(f"No direct MarianMT model for {src}->{tgt}")
        tokenizer, model = pair
        with torch.no_grad():
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            outputs = model.generate(**inputs, max_length=512)
            return tokenizer.decode(outputs[0], skip_special_tokens=True)

    def translate(self, text: str, src: str, tgt: str) -> Dict[str, Any]:
        text = text.strip()
        if not text or src == tgt:
            return {"translated_text": text, "source_lang": src, "target_lang": tgt, "method": "identity"}

        # 1. Direct translation if supported
        if (src, tgt) in self.supported_pairs:
            try:
                res = self._translate_direct(text, src, tgt)
                return {
                    "translated_text": res,
                    "source_lang": src,
                    "target_lang": tgt,
                    "method": f"MarianMT ({self.supported_pairs[(src, tgt)]})"
                }
            except Exception as e:
                logger.warning(f"Direct MarianMT translation failed ({e}), trying fallback...")

        # 2. Pivot translation via English (e.g. es -> en -> hi)
        if src != "en" and tgt != "en" and (src, "en") in self.supported_pairs and ("en", tgt) in self.supported_pairs:
            try:
                intermediate = self._translate_direct(text, src, "en")
                final_res = self._translate_direct(intermediate, "en", tgt)
                return {
                    "translated_text": final_res,
                    "source_lang": src,
                    "target_lang": tgt,
                    "method": "MarianMT (Pivot via English)"
                }
            except Exception as e:
                logger.warning(f"Pivot translation failed ({e}), trying fallback...")

        # 3. Fallback to deep_translator (local/hybrid)
        try:
            from deep_translator import GoogleTranslator
            res = GoogleTranslator(source=src, target=tgt).translate(text)
            return {
                "translated_text": res,
                "source_lang": src,
                "target_lang": tgt,
                "method": "Fallback Translator"
            }
        except Exception as e:
            logger.error(f"All translation methods failed for {src}->{tgt}: {e}")
            return {
                "translated_text": text,
                "source_lang": src,
                "target_lang": tgt,
                "method": "error",
                "error": str(e)
            }

local_translator = LocalTranslator(max_cached_models=2)

# ═════════════════════════════════════════════════════════════════════
# 3. LOCAL TEXT-TO-SPEECH (pyttsx3 Windows SAPI5)
# ═════════════════════════════════════════════════════════════════════
class TTSEngine:
    def __init__(self):
        self._lock = threading.Lock()

    def _fetch_google_tts(self, text: str, lang: str = "hi") -> Optional[bytes]:
        """Fetches natural TTS audio stream from Google Translate service."""
        import urllib.parse
        import urllib.request
        try:
            clean_text = text.strip()[:200]
            encoded = urllib.parse.quote(clean_text)
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={encoded}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "audio/mpeg, audio/*, */*"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = resp.read()
                if data and len(data) > 100:
                    return data
        except Exception as e:
            logger.warning(f"Google TTS fetch failed: {e}")
        return None

    def synthesize_audio_bytes(self, text: str, lang: str = "en") -> Tuple[bytes, str]:
        """
        Synthesizes text to audio stream (MP3 or WAV).
        Handles Hindi (hi) and non-Latin scripts cleanly, avoiding Windows SAPI5 charmap errors.
        """
        lang_lower = (lang or "en").lower()
        has_devanagari = any('\u0900' <= char <= '\u097f' for char in text)

        # 1. Hindi or Devanagari script: prioritize natural Hindi audio stream
        if lang_lower == "hi" or has_devanagari:
            audio_data = self._fetch_google_tts(text, "hi")
            if audio_data:
                return audio_data, "audio/mpeg"

        # 2. Local pyttsx3 Windows SAPI5 synthesis for English and other languages
        with self._lock:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                if voices:
                    selected_voice = voices[0].id
                    for v in voices:
                        v_name = (v.name or "").lower()
                        v_id = (v.id or "").lower()
                        if lang_lower in v_name or lang_lower in v_id:
                            selected_voice = v.id
                            break
                    try:
                        engine.setProperty('voice', selected_voice)
                    except Exception:
                        pass

                engine.setProperty('rate', 155)

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    temp_filename = tf.name

                try:
                    engine.save_to_file(text, temp_filename)
                    engine.runAndWait()
                    if os.path.exists(temp_filename) and os.path.getsize(temp_filename) > 44:
                        with open(temp_filename, "rb") as f:
                            wav_data = f.read()
                        return wav_data, "audio/wav"
                finally:
                    if os.path.exists(temp_filename):
                        try:
                            os.remove(temp_filename)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"pyttsx3 synthesis error: {e}")

        # 3. Fallback to Google TTS if pyttsx3 failed (e.g. charmap codec error or missing OS voice)
        audio_data = self._fetch_google_tts(text, lang_lower)
        if audio_data:
            return audio_data, "audio/mpeg"

        # 4. Fallback empty valid WAV
        empty_wav = (
            b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00"
            b"\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        )
        return empty_wav, "audio/wav"

    def synthesize_wav_bytes(self, text: str, lang: str = "en") -> bytes:
        data, _ = self.synthesize_audio_bytes(text, lang)
        return data

tts_engine = TTSEngine()

# ═════════════════════════════════════════════════════════════════════
# 4. API REQUEST SCHEMAS
# ═════════════════════════════════════════════════════════════════════
class TranslationRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "hi"

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "local-marian"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.1
    max_tokens: Optional[int] = 800

# ═════════════════════════════════════════════════════════════════════
# 5. REST & WEBSOCKET ENDPOINTS
# ═════════════════════════════════════════════════════════════════════

@app.get("/api/status")
def get_system_status():
    """Returns memory usage, system health, and loaded local model information."""
    mem = psutil.virtual_memory()
    return {
        "status": "online",
        "device": "cpu",
        "ram": {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent
        },
        "cpu_percent": psutil.cpu_percent(interval=None),
        "stt": {
            "model": f"faster-whisper-{stt_engine.model_size} (int8)",
            "status": "ready" if stt_engine.model is not None else "standby"
        },
        "translation": {
            "loaded_models": [f"{s}->{t}" for s, t in local_translator.models.keys()],
            "cache_limit": local_translator.max_cached
        },
        "tts": {
            "engine": "pyttsx3 (Windows SAPI5)",
            "status": "ready"
        }
    }

@app.post("/api/translate")
def translate_endpoint(req: TranslationRequest):
    """Local translation endpoint."""
    if not req.text.strip():
        return {"translated_text": "", "source_lang": req.source_lang, "target_lang": req.target_lang}
    return local_translator.translate(req.text, req.source_lang, req.target_lang)

@app.post("/v1/chat/completions")
def openai_compat_chat_completions(req: ChatCompletionRequest):
    """
    OpenAI/Groq compatible chat completions endpoint.
    Automatically parses prompt such as 'Translate from English to Hindi:\n\nHello'
    """
    user_prompt = ""
    for msg in req.messages:
        if msg.role == "user":
            user_prompt = msg.content
            break

    # Parse translation prompt
    # Example format: 'Translate from English to Hindi:\n\nHello'
    import re
    match = re.search(r"Translate from ([A-Za-z]+) to ([A-Za-z]+):\s*\n*(.*)", user_prompt, re.DOTALL | re.IGNORECASE)
    
    LANG_MAP = {
        'english': 'en', 'hindi': 'hi', 'spanish': 'es', 'french': 'fr',
        'german': 'de', 'chinese': 'zh', 'japanese': 'ja', 'korean': 'ko',
        'russian': 'ru', 'arabic': 'ar', 'portuguese': 'pt', 'italian': 'it',
        'turkish': 'tr', 'dutch': 'nl', 'polish': 'pl', 'swedish': 'sv',
        'ukrainian': 'uk', 'indonesian': 'id'
    }

    if match:
        src_name = match.group(1).strip().lower()
        tgt_name = match.group(2).strip().lower()
        content_to_tr = match.group(3).strip()
        src_lang = LANG_MAP.get(src_name, src_name[:2])
        tgt_lang = LANG_MAP.get(tgt_name, tgt_name[:2])
        res = local_translator.translate(content_to_tr, src_lang, tgt_lang)
        translated_text = res.get("translated_text", content_to_tr)
    else:
        # Default translation fallback
        res = local_translator.translate(user_prompt, "en", "hi")
        translated_text = res.get("translated_text", user_prompt)

    return {
        "id": f"chatcmpl-local-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "local-translator-marian",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": translated_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(user_prompt.split()),
            "completion_tokens": len(translated_text.split()),
            "total_tokens": len(user_prompt.split()) + len(translated_text.split())
        }
    }

@app.post("/api/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...), lang: Optional[str] = Form("en")):
    """Transcribe uploaded audio file (WebM, WAV, MP3, etc.)."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio content")
    result = stt_engine.transcribe_bytes(content, language=lang)
    return result

@app.get("/api/tts")
@app.post("/api/tts")
def tts_endpoint(text: str = Query(...), lang: str = Query("en")):
    """Generates audio stream (WAV or MP3) and returns audio stream."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    audio_bytes, media_type = tts_engine.synthesize_audio_bytes(text, lang=lang)
    return Response(content=audio_bytes, media_type=media_type)

# ═════════════════════════════════════════════════════════════════════
# 6. REAL-TIME WEBSOCKET TRANSCRIPTION (Deepgram-compatible protocol)
# ═════════════════════════════════════════════════════════════════════
@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket, lang: str = "en"):
    """
    Real-time streaming transcription WebSocket.
    Emits events conforming to Deepgram Results schema so existing frontends
    can seamlessly consume the real-time interim and final transcripts!
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected for STT (lang={lang})")
    
    audio_buffer = bytearray()
    last_transcribe_time = time.time()
    
    try:
        while True:
            message = await websocket.receive()
            
            # Binary audio chunk from MediaRecorder
            if "bytes" in message and message["bytes"]:
                chunk = message["bytes"]
                audio_buffer.extend(chunk)
                
                # Periodically transcribe interim results every 1.2s if enough data
                now = time.time()
                if now - last_transcribe_time > 1.2 and len(audio_buffer) >= 32000:
                    last_transcribe_time = now
                    try:
                        res = await asyncio.to_thread(stt_engine.transcribe_bytes, bytes(audio_buffer), lang)
                        transcript = res.get("text", "")
                        if transcript:
                            await websocket.send_json({
                                "type": "Results",
                                "channel": {
                                    "alternatives": [{"transcript": transcript}]
                                },
                                "is_final": False
                            })
                    except Exception as e:
                        logger.debug(f"Interim transcribe tick error: {e}")

            # Text control message (e.g. stop/finalize)
            elif "text" in message and message["text"]:
                try:
                    import json
                    data = json.loads(message["text"])
                    if data.get("action") == "finalize":
                        if len(audio_buffer) > 0:
                            res = await asyncio.to_thread(stt_engine.transcribe_bytes, bytes(audio_buffer), lang)
                            transcript = res.get("text", "")
                            await websocket.send_json({
                                "type": "Results",
                                "channel": {
                                    "alternatives": [{"transcript": transcript}]
                                },
                                "is_final": True,
                                "speech_final": True
                            })
                            await websocket.send_json({"type": "UtteranceEnd"})
                            audio_buffer.clear()
                except Exception as e:
                    logger.debug(f"Control message error: {e}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected. Finalizing any remaining audio ({len(audio_buffer)} bytes)...")
    except Exception as e:
        logger.warning(f"WebSocket STT exception: {e}")

# ═════════════════════════════════════════════════════════════════════
# 7. STATIC FILE SERVING
# ═════════════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
def serve_index():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "LinguaSync Backend Server is Running!"}

if __name__ == "__main__":
    logger.info("Starting LinguaSync Local AI Server on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
