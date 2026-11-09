"""
Motor de Reconocimiento de Voz (Speech-to-Text) Híbrido Optimizado (v3.2):
1. Ventana de pausa extendida (`pause_threshold = 1.6s` y `phrase_time_limit = 20s`) para capturar
   oraciones largas completas sin cortar al usuario cuando toma aire o hace pausas naturales.
2. `dynamic_energy_threshold = False` con umbral estabilizado para que el micrófono no pierda sensibilidad
   a mitad de una frase larga.
3. Reconocimiento bilingüe enfocado en Español (`es-CO`) e Inglés (`en-US`) sin falsos positivos en francés.
4. Fallback 100% Offline con `faster-whisper` (16kHz).
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from ultron.config import UltronConfig
from ultron.strings import detect_language, tr

logger = logging.getLogger("ultron.stt")

ULTRON_WHISPER_PROMPT = (
    "HALCÓN, Halcón, Hey Halcón, Oye Halcón, Ultrón, Hey Ultrón, Sebastián, Biomédica, IA, Machine Learning, Liofilizados, Bioinstrumentación, GitHub, "
    "¿qué hora es?, ¿qué fecha es hoy?, analiza mi sistema, diagnóstico del sistema, telemetría, "
    "¿cuáles son mis tareas?, ¿qué clases tengo?, mira mi pantalla, analiza mi pantalla, abre YouTube, "
    "What time is it?, How is my PC running?, What are my tasks?, Look at my screen, Open GitHub."
)


@dataclass
class TranscriptionResult:
    """Resultado estructurado de una transcripción de voz o entrada de texto."""

    text: str
    language: str
    engine: str


class UltronSTT:
    """Gestor de entrada de voz y texto optimizado para frases largas y naturales."""

    def __init__(self, config: UltronConfig, text_mode: bool = False) -> None:
        self.config = config
        self.text_mode = text_mode
        self._whisper_model = None
        self._whisper_attempted = False
        self._recognizer = None
        self._calibrated = False

    def _get_recognizer(self) -> object:
        if self._recognizer is None:
            import speech_recognition as sr

            r = sr.Recognizer()
            # Pausa generosa (1.6s) para que Sebastián pueda decir frases largas con pausas naturales sin ser cortado
            r.pause_threshold = 1.6
            r.non_speaking_duration = 0.6
            r.phrase_threshold = 0.25
            # Desactivar ajuste dinámico agresivo que sube el umbral a mitad de la frase y corta el final
            r.dynamic_energy_threshold = False
            r.energy_threshold = 250
            self._recognizer = r
        return self._recognizer

    def _init_whisper(self) -> None:
        """Inicializa faster-whisper de forma perezosa solo cuando se necesita."""
        try:
            from faster_whisper import WhisperModel

            self._whisper_model = WhisperModel(
                self.config.whisper_model,
                device="cpu",
                compute_type="int8",
            )
            logger.info(
                "Modelo faster-whisper ('%s') cargado correctamente en modo offline.",
                self.config.whisper_model,
            )
        except Exception as exc:
            logger.info(
                "faster-whisper no disponible (%s). Se usará SpeechRecognition.",
                exc,
            )
            self._whisper_model = None

    def listen(self, lang_hint: Optional[str] = None) -> Optional[TranscriptionResult]:
        """
        Escucha una orden completa del usuario por micrófono o consola.
        """
        target_lang = lang_hint or self.config.default_lang

        if self.text_mode:
            try:
                raw = input(f"\n🎙️ [{self.config.user_name}]: ").strip()
            except (EOFError, KeyboardInterrupt):
                return TranscriptionResult(text="exit", language=target_lang, engine="text")
            if not raw:
                return None
            detected = detect_language(raw, default_lang=target_lang)
            return TranscriptionResult(text=raw.lower(), language=detected, engine="text")

        try:
            import speech_recognition as sr
        except ImportError:
            logger.warning("SpeechRecognition no instalado; cambiando a modo texto.")
            self.text_mode = True
            return self.listen(lang_hint=target_lang)

        recognizer = self._get_recognizer()

        try:
            with sr.Microphone() as source:
                if not self._calibrated:
                    print("🎛️ Calibrando micrófono para el ruido ambiente (1 segundo)...")
                    recognizer.adjust_for_ambient_noise(source, duration=0.8)  # type: ignore[attr-defined]
                    recognizer.energy_threshold = max(280, min(recognizer.energy_threshold * 1.25, 800))  # type: ignore[attr-defined]
                    self._calibrated = True
                print(f"🎙️ {tr(target_lang, 'listening')} (Habla con naturalidad)")
                audio = recognizer.listen(source, timeout=7, phrase_time_limit=22)  # type: ignore[attr-defined]
        except sr.WaitTimeoutError:
            return None
        except OSError as exc:
            logger.warning("No se detectó micrófono activo (%s). Activando modo texto.", exc)
            self.text_mode = True
            return self.listen(lang_hint=target_lang)

        # Ignorar ruidos cortos de fondo (< 0.45s) para no saturar la consola con "Procesando audio..."
        raw_pcm = getattr(audio, "frame_data", b"")
        sample_rate = getattr(audio, "sample_rate", 16000)
        sample_width = getattr(audio, "sample_width", 2)
        duration_sec = len(raw_pcm) / float(max(1, sample_rate * sample_width))
        if duration_sec < 0.45:
            return None

        print(f"⚙️ {tr(target_lang, 'recognizing')}")

        # Modo 1: Reconocimiento de alta precisión (es-CO / en-US) para frases completas
        if self.config.stt_engine != "whisper_offline":
            result, is_offline = self._transcribe_with_google(recognizer, audio, target_lang)
            if result:
                print(f"🗣️ [{self.config.user_name} | {result.language.upper()}]: {result.text}")
                return result
            if not is_offline:
                return None

        # Modo 2: Offline faster-whisper a 16kHz cuando no hay internet
        if not self._whisper_attempted:
            self._whisper_attempted = True
            self._init_whisper()

        if self._whisper_model is not None:
            result = self._transcribe_with_whisper(audio, target_lang)
            if result:
                print(f"🗣️ [{self.config.user_name} | {result.language.upper()}]: {result.text}")
                return result

        return None

    def _transcribe_with_whisper(
        self, audio: object, default_lang: str
    ) -> Optional[TranscriptionResult]:
        try:
            wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)  # type: ignore[attr-defined]
            wav_stream = io.BytesIO(wav_bytes)
            segments, info = self._whisper_model.transcribe(  # type: ignore[union-attr]
                wav_stream,
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                initial_prompt=ULTRON_WHISPER_PROMPT,
            )
            valid_texts = [
                seg.text.strip()
                for seg in segments
                if getattr(seg, "no_speech_prob", 0.0) < 0.6
            ]
            text = " ".join(valid_texts).strip()

            hallucinations = {
                "we don't know.",
                "we don't know",
                "thank you.",
                "thank you",
                "you",
                "gracias.",
                "subtítulos realizados por la comunidad de amara.org",
            }
            if not text or text.lower() in hallucinations:
                return None

            lang_code = getattr(info, "language", default_lang) or default_lang
            if lang_code not in ("es", "en"):
                lang_code = detect_language(text, default_lang=default_lang)

            return TranscriptionResult(
                text=text.lower(),
                language=lang_code,
                engine="faster-whisper",
            )
        except Exception as exc:
            logger.debug("Fallo en transcripción faster-whisper: %s", exc)
            return None

    def _transcribe_with_google(
        self, recognizer: object, audio: object, default_lang: str
    ) -> Tuple[Optional[TranscriptionResult], bool]:
        """
        Transcribe probando Español (Colombia) e Inglés (US).
        Omite francés en escucha automática para evitar falsos positivos con ruido de fondo ('contrôle').
        """
        import speech_recognition as sr

        lang_BCP47 = {
            "es": "es-CO",
            "en": "en-US",
        }
        ordered_langs = ["es", "en"] if default_lang != "en" else ["en", "es"]

        for code in ordered_langs:
            bcp = lang_BCP47[code]
            try:
                query = recognizer.recognize_google(audio, language=bcp)  # type: ignore[attr-defined]
                if query and len(query.strip()) >= 2:
                    detected = detect_language(query, default_lang=code)
                    return (
                        TranscriptionResult(
                            text=query.lower(),
                            language=detected,
                            engine=f"google ({bcp})",
                        ),
                        False,
                    )
            except sr.UnknownValueError:
                continue
            except sr.RequestError as exc:
                logger.debug("Google Speech API sin conexión: %s", exc)
                return None, True
        return None, False
