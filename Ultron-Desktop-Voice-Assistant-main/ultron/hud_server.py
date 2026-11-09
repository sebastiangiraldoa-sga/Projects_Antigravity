"""
Servidor Backend del Stark HUD v4.0 para Ultrón (`ultron.hud_server`).
Construido íntegramente sobre la biblioteca estándar de Python (`ThreadingHTTPServer`)
para mantener una huella de memoria < 15 MB de RAM y cero dependencias externas de servidor web.

Expone:
- Archivos estáticos de la interfaz holográfica (`ultron/hud/index.html`, `styles.css`, `app.js`).
- `GET  /api/status`    -> Metadatos del núcleo y estado de los motores de IA.
- `GET  /api/telemetry` -> Métricas de hardware (CPU, RAM, Disco, Batería, Red, Top Procesos) en tiempo real.
- `POST /api/command`   -> Ejecución de comandos de voz/texto con respuesta inmediata y bloqueo thread-safe.
- `GET  /api/tts`       -> Síntesis de voz Neural MP3 en memoria (Edge Neural TTS + Cloud Neural Fallback).
- `POST /api/vision`    -> Captura de pantalla en vivo (Base64 PNG) + Análisis Multimodal (Debug, UX, PID, General).
"""

from __future__ import annotations

import base64
import json
import logging
import shutil
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from ultron.assistant import UltronAssistant
from ultron.strings import detect_language, tr
from ultron.telemetry import collect_system_health
from ultron.vision import VisionEngine

logger = logging.getLogger("ultron.hud_server")

HUD_STATIC_DIR = Path(__file__).resolve().parent / "hud"

STATIC_ROUTES: Dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/favicon.ico": ("favicon.ico", "image/x-icon"),
}


class StarkHUDServer(ThreadingHTTPServer):
    """Servidor HTTP multihilo con estado compartido para `UltronAssistant`."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        assistant: Optional[UltronAssistant] = None,
        hud_dir: Optional[Path] = None,
    ) -> None:
        self.assistant = assistant or UltronAssistant(text_mode=True, mute=True)
        self.command_lock = threading.Lock()
        self.hud_dir = hud_dir or HUD_STATIC_DIR
        super().__init__(server_address, StarkHUDRequestHandler)


class StarkHUDRequestHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para los endpoints API y recursos estáticos del Stark HUD."""

    server: StarkHUDServer  # type: ignore[assignment]

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Silencia los logs de polling repetitivos de `/api/telemetry` en consola."""
        path = getattr(self, "path", "")
        if path.startswith("/api/telemetry"):
            return
        logger.debug("HUD HTTP: " + format, *args)

    # ------------------------------------------------------------------
    # Utilidades de respuesta HTTP / JSON / CORS
    # ------------------------------------------------------------------

    def _send_cors_and_cache_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self._send_cors_and_cache_headers()
        self.end_headers()
        self.wfile.write(raw)

    def _read_json_body(self) -> Dict[str, Any]:
        length_str = self.headers.get("Content-Length", "0")
        try:
            length = max(0, int(length_str))
        except ValueError:
            length = 0
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Métodos HTTP (OPTIONS, GET, POST)
    # ------------------------------------------------------------------

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._send_cors_and_cache_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path

        if route in STATIC_ROUTES:
            self._handle_static(route)
            return

        if route == "/api/status":
            self._handle_api_status()
            return

        if route == "/api/telemetry":
            self._handle_api_telemetry()
            return

        if route == "/api/tts":
            query_params = urllib.parse.parse_qs(parsed.query)
            text = (query_params.get("text", [""])[0] or "").strip()
            lang = (query_params.get("lang", ["es"])[0] or "es").strip()
            self._handle_api_tts(text=text, lang=lang)
            return

        self._send_json(404, {"ok": False, "error": f"Ruta no encontrada: {route}"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path

        if route == "/api/command":
            self._handle_api_command()
            return

        if route == "/api/vision":
            self._handle_api_vision()
            return

        if route == "/api/dictate":
            self._handle_api_dictate()
            return

        if route == "/api/organize":
            self._handle_api_organize()
            return

        self._send_json(404, {"ok": False, "error": f"Ruta POST no encontrada: {route}"})

    # ------------------------------------------------------------------
    # Handlers específicos de rutas
    # ------------------------------------------------------------------

    def _handle_static(self, route: str) -> None:
        filename, content_type = STATIC_ROUTES[route]
        file_path = self.server.hud_dir / filename
        if not file_path.exists():
            fallback_html = (
                "<!doctype html><html><head><meta charset='utf-8'><title>Stark HUD v5.2</title></head>"
                "<body><h1>Ultrón Stark HUD v5.2</h1></body></html>"
            ).encode("utf-8")
            self.send_response(200 if filename == "index.html" else 404)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(fallback_html)))
            self._send_cors_and_cache_headers()
            self.end_headers()
            self.wfile.write(fallback_html)
            return

        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self._send_cors_and_cache_headers()
        self.end_headers()
        self.wfile.write(data)

    def _handle_api_status(self) -> None:
        assistant = self.server.assistant
        payload = {
            "ok": True,
            "assistant_name": assistant.config.load_assistant_name(),
            "user_name": assistant.config.user_name,
            "version": "5.2.0",
            "architecture": "Stark HUD v5.2 (Spatial UI + Jarvis Pro Dictation & File Organizer)",
            "llm_backends": {
                "gemini_configured": bool(assistant.config.gemini_api_key),
                "cloud_fallback_ready": True,
            },
        }
        self._send_json(200, payload)

    def _handle_api_telemetry(self) -> None:
        assistant = self.server.assistant
        report = collect_system_health(user_name=assistant.config.user_name)
        payload = report.to_dict()
        payload["ok"] = True
        payload["status"] = report.overall_status
        self._send_json(200, payload)

    def _handle_api_command(self) -> None:
        body = self._read_json_body()
        text = str(body.get("text") or "").strip()
        lang_param = str(body.get("lang") or "es").strip().lower()
        speak_on_server = bool(body.get("speak_on_server", False))

        assistant = self.server.assistant
        if not text:
            self._send_json(
                400,
                {
                    "ok": False,
                    "query": "",
                    "detected_lang": lang_param or "es",
                    "reply": "No recibí ningún comando para procesar.",
                    "should_exit": False,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                },
            )
            return

        if lang_param in ("en", "fr"):
            detected_lang = lang_param
        else:
            detected_lang = detect_language(text, default_lang=lang_param or assistant.config.default_lang)

        with self.server.command_lock:
            prev_mute = assistant.tts.mute
            try:
                assistant.tts.mute = not speak_on_server
                result = assistant.process_command(text, detected_lang=detected_lang)
            finally:
                assistant.tts.mute = prev_mute

        should_exit = result == "EXIT"
        if should_exit:
            reply_text = tr("es", "offline", user=assistant.config.user_name)
        else:
            reply_text = result

        self._send_json(
            200,
            {
                "ok": True,
                "query": text,
                "detected_lang": detected_lang,
                "reply": reply_text,
                "should_exit": should_exit,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            },
        )

    def _handle_api_tts(self, text: str, lang: str = "es") -> None:
        if not text:
            self.send_response(204)
            self._send_cors_and_cache_headers()
            self.end_headers()
            return

        mp3_bytes = self.server.assistant.tts.synthesize_neural_mp3(text, lang=lang)
        if mp3_bytes:
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(mp3_bytes)))
            self._send_cors_and_cache_headers()
            self.end_headers()
            self.wfile.write(mp3_bytes)
        else:
            self.send_response(204)
            self._send_cors_and_cache_headers()
            self.end_headers()

    def _handle_api_vision(self) -> None:
        body = self._read_json_body()
        query = str(body.get("query") or "¿Qué hay en mi pantalla?").strip()
        mode_raw = body.get("mode")
        mode = str(mode_raw).strip() if mode_raw else "general"

        assistant = self.server.assistant
        engine = VisionEngine(assistant.config)
        capture = engine.capture_screen()
        b64_png = base64.b64encode(capture.image_bytes).decode("ascii")
        image_data_url = f"data:image/png;base64,{b64_png}"

        res = engine.analyze_screen(
            query=query,
            mode=mode,
            image_path=capture.file_path,
            lang="es",
        )
        self._send_json(
            200,
            {
                "ok": True,
                "mode": res.mode,
                "query": res.query,
                "analysis": res.analysis,
                "provider_used": res.provider_used,
                "latency_ms": res.latency_ms,
                "image_data_url": image_data_url,
            },
        )

    def _handle_api_dictate(self) -> None:
        body = self._read_json_body()
        text = str(body.get("text") or "").strip()
        mode = str(body.get("mode") or "dictate").strip().lower()
        source_text = body.get("source_text")
        auto_paste = bool(body.get("auto_paste", False))

        assistant = self.server.assistant
        if mode == "edit":
            res = assistant.skills.dictation.edit_selected_or_clipboard_text(
                instruction=text or "Mejora la redacción y claridad del texto",
                source_text=str(source_text) if source_text else None,
                auto_paste=auto_paste,
            )
        else:
            res = assistant.skills.dictation.dictate(
                raw_text=text,
                auto_paste=auto_paste,
            )
        self._send_json(200, {"ok": True, **res.to_dict()})

    def _handle_api_organize(self) -> None:
        body = self._read_json_body()
        target = str(body.get("target") or "descargas").strip()
        dry_run = bool(body.get("dry_run", False))

        assistant = self.server.assistant
        res = assistant.skills.file_organizer.organize_directory(target, dry_run=dry_run)
        self._send_json(200, {"ok": True, **res.to_dict()})



def create_hud_server(
    assistant: Optional[UltronAssistant] = None,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> StarkHUDServer:
    """Crea una instancia de `StarkHUDServer` lista para servir."""
    return StarkHUDServer((host, port), assistant=assistant)


def launch_hud_browser(url: str) -> None:
    """
    Abre el Stark HUD en modo aplicación sin bordes (`--app=...`) en Chrome o Edge en Windows,
    o usando el navegador predeterminado como respaldo.
    """
    if sys.platform == "win32":
        for browser_bin in ("chrome", "msedge"):
            if shutil.which(browser_bin):
                try:
                    subprocess.Popen(
                        ["cmd", "/c", "start", "", browser_bin, f"--app={url}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return
                except Exception as exc:
                    logger.debug("No se pudo iniciar %s en modo app: %s", browser_bin, exc)

        # En Windows 10/11, msedge suele estar registrado como App Path aunque no esté en PATH
        try:
            proc = subprocess.run(
                ["cmd", "/c", "start", "", "msedge", f"--app={url}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
            if proc.returncode == 0:
                return
        except Exception as exc:
            logger.debug("Fallback a webbrowser.open tras msedge: %s", exc)

    webbrowser.open(url)


def run_hud_server(
    assistant: UltronAssistant,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    """
    Inicia el servidor local del Stark HUD buscando automáticamente un puerto libre
    en el rango `port..port+10`, imprime el banner interactivo y abre la interfaz gráfica.
    """
    server: Optional[StarkHUDServer] = None
    bound_port = port

    for candidate_port in range(port, port + 11):
        try:
            server = create_hud_server(assistant=assistant, host=host, port=candidate_port)
            bound_port = server.server_address[1]
            break
        except OSError:
            continue

    if server is None:
        server = create_hud_server(assistant=assistant, host=host, port=0)
        bound_port = server.server_address[1]

    url = f"http://{host}:{bound_port}"
    assistant_name = assistant.config.load_assistant_name()
    print("\n" + "═" * 74)
    print(f"⚡ {assistant_name.upper()} v4.0 — STARK HUD HOLOGRÁFICO ACTIVO")
    print(f"👤 Operador : {assistant.config.user_name}")
    print(f"🌐 URL HUD  : {url}")
    print("🎙️ Audio    : Voz Neural (Edge Neural TTS / Cloud Neural) + WebAudio Reactor")
    print("💡 Consejo  : Presiona Ctrl+C en esta terminal para detener el servidor.")
    print("═" * 74 + "\n")

    if open_browser:
        threading.Timer(0.4, launch_hud_browser, args=(url,)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Cerrando servidor Stark HUD v4.0. ¡Hasta pronto!")
    finally:
        server.server_close()
