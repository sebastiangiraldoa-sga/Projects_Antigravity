"""
Sistema de Visión Multimodal e Inteligencia de Pantalla para Ultrón.
Diseñado para Sebastián Giraldo Acosta (Ingeniería Biomédica & Especialización en Inteligencia Artificial).

Características principales:
1. Captura de pantalla multi-backend tolerante a fallos:
   - pyautogui -> PIL.ImageGrab -> CLI del sistema (scrot / import) -> Fallback sintético Headless (1280x720 PNG).
2. Detección automática de modo de visión (`general`, `debug`, `ux_audit`, `biomedical_pid`).
3. Prompts especializados para depuración de código en Python/PyTorch, auditoría visual
   y análisis de señales biomédicas e instrumentación clínica.
4. Motor VLM multimodal con soporte para Google Gemini (`google-genai`), Ollama (`llava`/`llama3.2-vision`)
   y reporte estructurado local de respaldo cuando no hay conexión a un VLM.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import re
import shutil
import struct
import subprocess
import time
import zlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except ImportError:

    class _RequestsResponseShim:
        def __init__(self, status_code: int, body: bytes) -> None:
            self.status_code = status_code
            self._body = body

        def json(self) -> Any:
            return json.loads(self._body.decode("utf-8"))

    class _RequestsShim:
        @staticmethod
        def post(url: str, json: Any = None, timeout: int = 20) -> _RequestsResponseShim:
            data = __import__("json").dumps(json).encode("utf-8") if json is not None else b""
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return _RequestsResponseShim(resp.status, resp.read())

    requests = _RequestsShim()  # type: ignore

from ultron.config import UltronConfig

logger = logging.getLogger("ultron.vision")


class VisionMode(str, Enum):
    """Modos especializados de análisis visual para Ultrón."""

    GENERAL = "general"
    DEBUG = "debug"
    UX_AUDIT = "ux_audit"
    BIOMEDICAL_PID = "biomedical_pid"


VALID_VISION_MODES = {m.value for m in VisionMode}


@dataclass
class VisionCapture:
    """Resultado de una captura de pantalla en memoria y en disco."""

    image_bytes: bytes
    file_path: Path
    width: int
    height: int
    is_synthetic_fallback: bool = False


@dataclass
class VisionAnalysisResult:
    """Resultado estructurado del análisis multimodal de pantalla."""

    mode: str
    query: str
    analysis: str
    provider_used: str
    image_path: Path
    latency_ms: int


# Palabras clave para auto-detección de modo (Español e Inglés)
_MODE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    VisionMode.BIOMEDICAL_PID.value: (
        "pid",
        "gráfica",
        "grafica",
        "graph",
        "plot",
        "señal",
        "senal",
        "signal",
        "osciloscopio",
        "oscilloscope",
        "arduino",
        "overshoot",
        "control",
        "settling",
        "estabilidad",
        "biomédic",
        "biomedic",
        "ecg",
        "ekg",
        "emg",
        "eeg",
        "bola-viga",
    ),
    VisionMode.DEBUG.value: (
        "error",
        "bug",
        "código",
        "codigo",
        "code",
        "consola",
        "console",
        "terminal",
        "exception",
        "traceback",
        "falla",
        "stacktrace",
        "syntax",
        "crash",
        "compil",
    ),
    VisionMode.UX_AUDIT.value: (
        "ux",
        "ui",
        "diseño",
        "diseno",
        "design",
        "interfaz",
        "interface",
        "layout",
        "figma",
        "css",
        "tailwind",
        "flutter",
        "contraste",
        "contrast",
    ),
}


def detect_vision_mode(user_query: str) -> str:
    """
    Detecta automáticamente el modo de análisis visual a partir de la consulta del usuario.
    Soporta consultas en español e inglés.
    """
    if not user_query or not user_query.strip():
        return VisionMode.GENERAL.value

    normalized = user_query.strip().lower()
    scores: Dict[str, int] = {
        VisionMode.BIOMEDICAL_PID.value: 0,
        VisionMode.DEBUG.value: 0,
        VisionMode.UX_AUDIT.value: 0,
    }

    for mode, keywords in _MODE_KEYWORDS.items():
        for kw in keywords:
            if len(kw) <= 3:
                # Coincidencia por palabra completa para siglas cortas como ui, ux, pid, css
                if re.search(rf"\b{re.escape(kw)}\b", normalized):
                    scores[mode] += 2
            else:
                if kw in normalized:
                    scores[mode] += 1

    best_mode, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_mode
    return VisionMode.GENERAL.value


def build_vision_prompt(
    mode: Optional[str] = None,
    user_query: str = "¿Qué hay en mi pantalla?",
    lang: str = "es",
) -> str:
    """
    Construye el prompt multimodal especializado según el modo de visión y la consulta.
    Si `mode` no se especifica o es inválido, se auto-detecta a partir de `user_query`.
    """
    # Soporte flexible si se invoca con un solo argumento posicional como user_query
    if (
        mode is not None
        and str(mode).lower() not in VALID_VISION_MODES
        and str(mode).lower() != "auto"
        and user_query == "¿Qué hay en mi pantalla?"
    ):
        user_query = str(mode)
        resolved_mode = detect_vision_mode(user_query)
    elif not mode or str(mode).lower() == "auto" or str(mode).lower() not in VALID_VISION_MODES:
        resolved_mode = detect_vision_mode(user_query)
    else:
        resolved_mode = str(mode).lower()

    lang_instruction = (
        "Responde SIEMPRE en español claro, conciso y natural (apto para ser leído por voz TTS), "
        "incluyendo los detalles técnicos clave."
        if lang == "es"
        else f"Respond concisely and clearly in '{lang}' (suitable for TTS playback) with key technical details."
    )

    mode_instructions = {
        VisionMode.DEBUG.value: (
            "MODO DEPURACIÓN DE CÓDIGO Y TERMINAL (DEBUG):\n"
            "- Identifica con precisión el archivo, número de línea y mensaje exacto de error o excepción visible.\n"
            "- Explica la causa raíz técnica del problema en 1-2 oraciones.\n"
            "- Proporciona la solución exacta o el fragmento de código corregido para solucionarlo rápidamente."
        ),
        VisionMode.UX_AUDIT.value: (
            "MODO AUDITORÍA UX/UI Y FRONTEND (UX_AUDIT):\n"
            "- Evalúa la jerarquía visual, contraste de color (accesibilidad WCAG), espaciado, alineación y tipografía.\n"
            "- Identifica puntos de fricción en la experiencia de usuario o problemas de layout responsive.\n"
            "- Sugiere mejoras concretas aplicables en CSS, Tailwind CSS, React o Flutter."
        ),
        VisionMode.BIOMEDICAL_PID.value: (
            "MODO ANÁLISIS DE CONTROL PID Y SEÑALES BIOMÉDICAS (BIOMEDICAL_PID):\n"
            "- Analiza las gráficas, curvas de respuesta temporal, osciloscopio o telemetría de sensores en pantalla.\n"
            "- Evalúa parámetros de sistemas de control (sobreimpulso / overshoot, tiempo de establecimiento / settling time, "
            "error en estado estacionario, oscilaciones) o calidad de señal biomédica (relación señal-ruido, artefactos, frecuencia).\n"
            "- Sugiere ajustes específicos de ganancias (Kp, Ki, Kd) o filtrado de señal según corresponda."
        ),
        VisionMode.GENERAL.value: (
            "MODO ANÁLISIS GENERAL DE PANTALLA (GENERAL):\n"
            "- Realiza lectura óptica (OCR) de los elementos más relevantes y describe el contexto activo en pantalla.\n"
            "- Responde directamente a la consulta del usuario con precisión y enfoque práctico."
        ),
    }

    specific_guide = mode_instructions.get(resolved_mode, mode_instructions[VisionMode.GENERAL.value])

    return (
        "Eres Ultrón, el asistente multimodal de escritorio de Sebastián Giraldo Acosta "
        "(Estudiante de Ingeniería Biomédica y de la Especialización en Inteligencia Artificial).\n"
        f"{specific_guide}\n\n"
        f"Consulta del usuario: \"{user_query}\"\n"
        f"Instrucción de salida: {lang_instruction}"
    )


def _generate_minimal_png_bytes(width: int = 1280, height: int = 720) -> bytes:
    """
    Genera un archivo PNG válido de 1280x720 desde cero usando únicamente la librería estándar
    (`struct` + `zlib`) en caso de que `Pillow` (PIL) no esté instalado en el entorno.
    """
    # Color de fondo oscuro estilo panel de telemetría (#121824 -> RGB: 18, 24, 36)
    row_bytes = b"\x00" + (b"\x12\x18\x24" * width)
    raw_data = row_bytes * height
    compressed = zlib.compress(raw_data, level=1)

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    png_signature = b"\x89PNG\r\n\x1a\n"
    # IHDR: width, height, bit_depth=8, color_type=2 (RGB), compression=0, filter=0, interlace=0
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = make_chunk(b"IHDR", ihdr_data)
    idat_chunk = make_chunk(b"IDAT", compressed)
    iend_chunk = make_chunk(b"IEND", b"")

    return png_signature + ihdr_chunk + idat_chunk + iend_chunk


def _generate_synthetic_screenshot(
    file_path: Path,
    width: int = 1280,
    height: int = 720,
    reason: str = "Headless environment (no DISPLAY)",
) -> VisionCapture:
    """
    Genera una imagen PNG de diagnóstico de 1280x720 en memoria y disco cuando el sistema
    se ejecuta en un entorno sin servidor gráfico ($DISPLAY ausente o contenedores CI).
    """
    timestamp_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (width, height), color=(18, 24, 36))
        draw = ImageDraw.Draw(img)

        # Marco decorativo y cuadrícula de telemetría de Ultrón
        draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(0, 210, 255), width=2)
        draw.rectangle([(40, 40), (width - 40, 120)], fill=(28, 38, 56), outline=(0, 210, 255), width=1)

        header_lines = [
            "ULTRON MULTIMODAL VISION - SYNTHETIC DIAGNOSTIC FRAME",
            f"User: Sebastián Giraldo Acosta | Timestamp: {timestamp_iso}",
            f"Resolution: {width}x{height} | Status: {reason}",
            f"DISPLAY={os.environ.get('DISPLAY', '<unset>')} | Platform={os.name}",
        ]
        y_pos = 52
        for line in header_lines:
            draw.text((60, y_pos), line, fill=(220, 240, 255))
            y_pos += 16

        # Simulación visual de curva de respuesta PID amortiguada para pruebas de visión
        draw.rectangle([(60, 160), (width - 60, height - 80)], outline=(70, 90, 120), width=1)
        draw.line([(80, 420), (width - 80, 420)], fill=(100, 130, 160), width=1)  # Setpoint
        draw.text((85, 400), "PID Setpoint Reference (1.0)", fill=(120, 200, 150))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        file_path.write_bytes(image_bytes)
        return VisionCapture(
            image_bytes=image_bytes,
            file_path=file_path,
            width=width,
            height=height,
            is_synthetic_fallback=True,
        )
    except Exception as exc:
        logger.debug("Usando generador PNG binario mínimo (PIL no disponible: %s)", exc)
        image_bytes = _generate_minimal_png_bytes(width=width, height=height)
        file_path.write_bytes(image_bytes)
        return VisionCapture(
            image_bytes=image_bytes,
            file_path=file_path,
            width=width,
            height=height,
            is_synthetic_fallback=True,
        )


def _read_png_dimensions(image_bytes: bytes) -> Tuple[int, int]:
    """Extrae ancho y alto desde la cabecera IHDR de un PNG válido."""
    if len(image_bytes) >= 24 and image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", image_bytes[16:24])
        return int(width), int(height)
    return 1280, 720


def capture_screen(
    config: Optional[UltronConfig] = None,
    output_path: Optional[Path] = None,
) -> VisionCapture:
    """
    Captura la pantalla actual probando múltiples backends en orden de prioridad:
    1. `pyautogui.screenshot()`
    2. `PIL.ImageGrab.grab()`
    3. Herramientas CLI del sistema (`scrot` o `import -window root`)
    4. Fallback sintético Headless (1280x720 PNG) si no hay `$DISPLAY` o todos los métodos fallan.

    Nunca lanza una excepción no controlada: garantiza siempre un PNG válido en disco.
    """
    cfg = config or UltronConfig()
    cfg.ensure_dirs()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target_path = Path(output_path) if output_path else (cfg.screenshots_dir / f"ultron_vision_{timestamp}.png")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or os.name == "nt")

    if has_display:
        # 1. Intentar con pyautogui.screenshot()
        try:
            import pyautogui  # type: ignore

            shot = pyautogui.screenshot()
            buf = io.BytesIO()
            shot.save(buf, format="PNG")
            image_bytes = buf.getvalue()
            target_path.write_bytes(image_bytes)
            width, height = shot.size
            return VisionCapture(
                image_bytes=image_bytes,
                file_path=target_path,
                width=int(width),
                height=int(height),
                is_synthetic_fallback=False,
            )
        except Exception as exc:
            logger.debug("Backend pyautogui no disponible o falló: %s", exc)

        # 2. Intentar con PIL.ImageGrab.grab()
        try:
            from PIL import ImageGrab

            shot = ImageGrab.grab()
            buf = io.BytesIO()
            shot.save(buf, format="PNG")
            image_bytes = buf.getvalue()
            target_path.write_bytes(image_bytes)
            width, height = shot.size
            return VisionCapture(
                image_bytes=image_bytes,
                file_path=target_path,
                width=int(width),
                height=int(height),
                is_synthetic_fallback=False,
            )
        except Exception as exc:
            logger.debug("Backend PIL.ImageGrab no disponible o falló: %s", exc)

        # 3. Intentar con CLI del sistema (scrot o ImageMagick import)
        cli_commands: List[List[str]] = []
        if shutil.which("scrot"):
            cli_commands.append(["scrot", "-o", str(target_path)])
        if shutil.which("import"):
            cli_commands.append(["import", "-window", "root", str(target_path)])

        for cmd in cli_commands:
            try:
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=8,
                    check=False,
                )
                if proc.returncode == 0 and target_path.exists() and target_path.stat().st_size > 0:
                    image_bytes = target_path.read_bytes()
                    width, height = _read_png_dimensions(image_bytes)
                    return VisionCapture(
                        image_bytes=image_bytes,
                        file_path=target_path,
                        width=width,
                        height=height,
                        is_synthetic_fallback=False,
                    )
            except Exception as exc:
                logger.debug("Backend CLI %s falló: %s", cmd[0], exc)

    # 4. Fallback sintético Headless / Servidor (nunca falla)
    reason = "No DISPLAY server detected" if not has_display else "All GUI screen capture backends failed"
    return _generate_synthetic_screenshot(target_path, width=1280, height=720, reason=reason)


def _load_existing_capture(image_path: Path) -> VisionCapture:
    """Carga un archivo de imagen existente en una estructura `VisionCapture`."""
    image_bytes = image_path.read_bytes()
    width, height = _read_png_dimensions(image_bytes)
    try:
        from PIL import Image

        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
    except Exception:
        pass
    return VisionCapture(
        image_bytes=image_bytes,
        file_path=image_path,
        width=int(width),
        height=int(height),
        is_synthetic_fallback=False,
    )


class UltronVision:
    """
    Motor Multimodal VLM para análisis inteligente de pantalla de Ultrón.
    Soporta Google Gemini (`google-genai`), Ollama (`llava`/`llama3.2-vision`)
    y un reporte diagnóstico local de respaldo.
    """

    def __init__(self, config: Optional[UltronConfig] = None) -> None:
        self.config = config or UltronConfig()

    def capture(self, output_path: Optional[Path] = None) -> VisionCapture:
        """Realiza una captura de pantalla utilizando el pipeline configurado."""
        return capture_screen(self.config, output_path=output_path)

    def capture_screen(self, output_path: Optional[Path] = None) -> VisionCapture:
        """Alias compatible para capturar la pantalla actual."""
        return capture_screen(self.config, output_path=output_path)

    def analyze_screen(
        self,
        user_query: str = "¿Qué hay en mi pantalla?",
        mode: Optional[str] = None,
        image_path: Optional[Path] = None,
        lang: str = "es",
        query: Optional[str] = None,
    ) -> VisionAnalysisResult:
        """
        Captura la pantalla (o lee `image_path` si se provee) y ejecuta el análisis multimodal
        utilizando el modo detectado o especificado.
        """
        start_time = time.monotonic()
        effective_query = (query if query is not None else user_query) or "¿Qué hay en mi pantalla?"

        resolved_mode = (
            str(mode).lower()
            if (mode and str(mode).lower() in VALID_VISION_MODES)
            else detect_vision_mode(effective_query)
        )
        prompt = build_vision_prompt(mode=resolved_mode, user_query=effective_query, lang=lang)
        user_query = effective_query

        if image_path is not None and Path(image_path).exists():
            capture = _load_existing_capture(Path(image_path))
        else:
            capture = capture_screen(self.config, output_path=image_path)

        # 1. Intentar con Google Gemini Multimodal si hay API Key disponible
        if self.config.gemini_api_key:
            gemini_answer = self._analyze_with_gemini(capture, prompt)
            if gemini_answer:
                elapsed_ms = max(1, int((time.monotonic() - start_time) * 1000))
                return VisionAnalysisResult(
                    mode=resolved_mode,
                    query=user_query,
                    analysis=gemini_answer,
                    provider_used="gemini",
                    image_path=capture.file_path,
                    latency_ms=elapsed_ms,
                )

        # 2. Intentar con Ollama Multimodal (llava / llama3.2-vision)
        ollama_answer = self._analyze_with_ollama(capture, prompt)
        if ollama_answer:
            elapsed_ms = max(1, int((time.monotonic() - start_time) * 1000))
            return VisionAnalysisResult(
                mode=resolved_mode,
                query=user_query,
                analysis=ollama_answer,
                provider_used="ollama",
                image_path=capture.file_path,
                latency_ms=elapsed_ms,
            )

        # 3. Fallback Inteligente Local (sin API key ni servidor Ollama activo)
        fallback_report = self._build_local_fallback_report(capture, resolved_mode, user_query)
        elapsed_ms = max(1, int((time.monotonic() - start_time) * 1000))
        return VisionAnalysisResult(
            mode=resolved_mode,
            query=user_query,
            analysis=fallback_report,
            provider_used="local_fallback",
            image_path=capture.file_path,
            latency_ms=elapsed_ms,
        )

    def _analyze_with_gemini(self, capture: VisionCapture, prompt: str) -> Optional[str]:
        """Consulta el modelo multimodal de Google Gemini usando `google-genai`."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.config.gemini_api_key)
            image_part = types.Part.from_bytes(
                data=capture.image_bytes,
                mime_type="image/png",
            )
            models_to_try = [self.config.gemini_model, "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
            seen: set[str] = set()
            unique_models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

            for model_name in unique_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[image_part, prompt],
                        config=types.GenerateContentConfig(
                            temperature=0.4,
                            max_output_tokens=500,
                        ),
                    )
                    if response and getattr(response, "text", None):
                        return response.text.strip()
                except Exception as model_err:
                    logger.debug("Gemini vision model '%s' failed: %s", model_name, model_err)
                    continue
        except Exception as exc:
            logger.warning("Error en análisis multimodal con Gemini: %s", exc)
        return None

    def _analyze_with_ollama(self, capture: VisionCapture, prompt: str) -> Optional[str]:
        """Consulta un modelo multimodal local en Ollama (`llava` o `llama3.2-vision`)."""
        try:
            vision_model = os.getenv("OLLAMA_VISION_MODEL", "llava")
            url = f"{self.config.ollama_base_url.rstrip('/')}/api/generate"
            encoded_image = base64.b64encode(capture.image_bytes).decode("ascii")
            payload = {
                "model": vision_model,
                "prompt": prompt,
                "images": [encoded_image],
                "stream": False,
            }
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("response", "").strip()
                if answer:
                    return answer
        except Exception as exc:
            logger.debug("Ollama Vision no accesible (%s).", exc)
        return None

    def _build_local_fallback_report(
        self,
        capture: VisionCapture,
        mode: str,
        user_query: str,
    ) -> str:
        """
        Genera un reporte de inspección local estructurado cuando ni Gemini ni Ollama están disponibles.
        """
        capture_type = (
            "diagnóstico sintético headless"
            if capture.is_synthetic_fallback
            else "captura de pantalla real"
        )
        return (
            f"Captura procesada localmente ({capture_type}) en modo '{mode}'. "
            f"Resolución: {capture.width}x{capture.height} px. "
            f"Archivo guardado en: {capture.file_path.name} ({capture.file_path}). "
            f"Consulta registrada: '{user_query}'. "
            "Para activar el análisis visual profundo con IA, configura la variable de entorno "
            "GEMINI_API_KEY o ejecuta localmente 'ollama run llava'."
        )


VisionEngine = UltronVision
