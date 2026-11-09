"""
Motor de Síntesis de Voz (Text-to-Speech) con soporte multilingüe (ES/EN/FR).
En Windows utiliza `SAPI.SpVoice` nativo por llamada para evitar bloqueos de audio
cuando se alterna con el micrófono (`PyAudio`), y `pyttsx3` como motor multiplataforma.
"""

from __future__ import annotations

import logging
import re
import sys
import threading
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

logger = logging.getLogger("ultron.tts")

NEURAL_VOICE_MAP: Dict[str, str] = {
    "es": "es-CO-GonzaloNeural",
    "en": "en-US-ChristopherNeural",
    "fr": "fr-FR-HenriNeural",
}


class UltronTTS:
    """Envoltura segura y multilingüe para síntesis de voz en Windows, Linux y macOS."""

    def __init__(self, rate: int = 175, volume: float = 1.0, mute: bool = False) -> None:
        self.mute = mute
        self.rate = rate
        self.volume = volume
        self._lock = threading.Lock()
        self.engine = None
        self.voice_map: Dict[str, Optional[str]] = {"es": None, "en": None, "fr": None}

        if not self.mute and sys.platform != "win32":
            self._init_engine(rate, volume)

    def _init_engine(self, rate: int, volume: float) -> None:
        try:
            import pyttsx3

            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", rate)
            self.engine.setProperty("volume", volume)

            voices = self.engine.getProperty("voices") or []
            for voice in voices:
                v_meta = f"{getattr(voice, 'languages', '')} {getattr(voice, 'name', '')} {getattr(voice, 'id', '')}".lower()
                if any(k in v_meta for k in ("es", "spanish", "español", "mexico", "colombia", "latam")):
                    self.voice_map["es"] = voice.id
                if any(k in v_meta for k in ("en-us", "en_us", "english")):
                    self.voice_map["en"] = voice.id
                if any(k in v_meta for k in ("fr-fr", "fr_fr", "french", "français")):
                    self.voice_map["fr"] = voice.id
        except Exception as exc:
            logger.warning("TTS local no disponible (%s). Usando salida por consola.", exc)
            self.engine = None

    def speak(self, text: str, lang: str = "es") -> None:
        """Imprime y pronuncia el texto en el idioma indicado sin bloquear el micrófono."""
        print(f"🤖 [Ultrón | {lang.upper()}]: {text}")
        if self.mute:
            return

        with self._lock:
            if sys.platform == "win32":
                if self._speak_windows_sapi(text, lang):
                    return

            if self.engine is None:
                self._init_engine(self.rate, self.volume)

            if self.engine is not None:
                try:
                    voice_id = self.voice_map.get(lang)
                    if voice_id:
                        self.engine.setProperty("voice", voice_id)
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as exc:
                    logger.debug("Error al sintetizar voz con pyttsx3: %s", exc)

    def synthesize_neural_mp3(self, text: str, lang: str = "es") -> Optional[bytes]:
        """
        Sintetiza audio neural en formato MP3 en memoria para el Stark HUD v4.0.
        - Nivel 1: Microsoft Edge Neural TTS (`edge_tts`, ej. `es-CO-GonzaloNeural`).
        - Nivel 2: Cloud Neural TTS Zero-Install (fragmentación inteligente <= 180 caracteres).
        Retorna `bytes` MP3 o `None` si no hay conectividad.
        """
        clean_text = re.sub(r"[*_`#]+", "", text or "")
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if not clean_text:
            return None

        lang_key = (lang or "es").strip().lower()[:2]
        if lang_key not in ("es", "en", "fr"):
            lang_key = "es"

        # Nivel 1: edge_tts (Neural Voice de alta fidelidad)
        try:
            import asyncio
            import edge_tts  # type: ignore[import-not-found]

            voice = NEURAL_VOICE_MAP.get(lang_key, "es-CO-GonzaloNeural")

            async def _edge_stream() -> bytes:
                communicate = edge_tts.Communicate(clean_text, voice)
                audio_buf = bytearray()
                async for chunk in communicate.stream():
                    if chunk.get("type") == "audio" and chunk.get("data"):
                        audio_buf.extend(chunk["data"])
                return bytes(audio_buf)

            mp3_bytes = asyncio.run(_edge_stream())
            if mp3_bytes:
                return mp3_bytes
        except Exception as exc:
            logger.debug("Fallback de edge_tts a Cloud Neural TTS: %s", exc)

        # Nivel 2: Zero-Install Cloud Neural MP3 Fallback
        try:
            chunks = self._split_tts_chunks(clean_text, max_len=180)
            combined = bytearray()
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            }
            for chunk in chunks:
                url = (
                    "https://translate.googleapis.com/translate_tts"
                    f"?ie=UTF-8&client=tw-ob&tl={lang_key}&q={urllib.parse.quote(chunk)}"
                )
                req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = resp.read()
                    if data:
                        combined.extend(data)
            if combined:
                return bytes(combined)
        except Exception as exc:
            logger.debug("Cloud Neural TTS no disponible (modo offline): %s", exc)

        return None

    @staticmethod
    def _split_tts_chunks(text: str, max_len: int = 180) -> List[str]:
        """Divide un texto largo en fragmentos <= max_len respetando oraciones y palabras."""
        sentences = re.split(r"(?<=[.!?;:])\s+", text.strip())
        chunks: List[str] = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= max_len:
                candidate = f"{current} {sentence}".strip() if current else sentence
                if len(candidate) <= max_len:
                    current = candidate
                else:
                    if current:
                        chunks.append(current)
                    current = sentence
            else:
                if current:
                    chunks.append(current)
                    current = ""
                words = sentence.split()
                for word in words:
                    if len(word) > max_len:
                        if current:
                            chunks.append(current)
                            current = ""
                        for i in range(0, len(word), max_len):
                            chunks.append(word[i : i + max_len])
                        continue
                    candidate = f"{current} {word}".strip() if current else word
                    if len(candidate) <= max_len:
                        current = candidate
                    else:
                        if current:
                            chunks.append(current)
                        current = word

        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def _speak_windows_sapi(text: str, lang: str = "es") -> bool:
        """Usa el motor COM SAPI.SpVoice nativo de Windows para evitar conflictos con PyAudio."""
        try:
            import pythoncom  # type: ignore[import-not-found]
            import win32com.client  # type: ignore[import-not-found]

            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Rate = 1
            speaker.Volume = 100

            lang_keywords = {
                "es": ("spanish", "español", "es-", "sabina", "helena", "pablo", "raul", "dalia"),
                "en": ("english", "en-", "david", "zira", "mark"),
                "fr": ("french", "français", "fr-", "hortense", "paul"),
            }.get(lang, ("spanish", "español", "es-"))

            for v in speaker.GetVoices():
                desc = v.GetDescription().lower()
                if any(k in desc for k in lang_keywords):
                    speaker.Voice = v
                    break

            speaker.Speak(text)
            return True
        except Exception as exc:
            logger.debug("Fallback de SAPI.SpVoice a pyttsx3: %s", exc)
            return False

