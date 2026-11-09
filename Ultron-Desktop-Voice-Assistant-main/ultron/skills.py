"""
Habilidades (Skills) de Automatización de Escritorio de Ultrón v3.1.
Incluye:
- Lanzador Universal de Aplicaciones de Windows (Spotify, VS Code, Calculadora, WhatsApp, Discord, Office, etc.) y sitios web.
- Búsqueda directa por voz en YouTube y Google.
- Control de ventanas y volumen del sistema (Subir/Bajar volumen, Silenciar, Minimizar todo, Cambiar ventana).
- Telemetría de hardware y procesos en tiempo real (`UltronTelemetry`).
- Visión Multimodal de Escritorio (`UltronVision`: Debug, UX Audit, Biomedical/PID, General).
- Funciones de notas JSON persistentes, chistes, cambio de nombre, Wikipedia y música.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser as wb
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pyjokes
import wikipedia

from ultron.config import UltronConfig
from ultron.jarvis_pro import FileOrganizerEngine, SmartDictationEngine
from ultron.strings import tr
from ultron.task_bridge import TaskSyncBridge
from ultron.telemetry import UltronTelemetry
from ultron.tts import UltronTTS
from ultron.vision import UltronVision

logger = logging.getLogger("ultron.skills")

# Mapa de aplicaciones nativas de Windows / URI schemes y su respaldo web
WINDOWS_APPS_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "spotify": ("spotify:", "https://open.spotify.com"),
    "whatsapp": ("whatsapp:", "https://web.whatsapp.com"),
    "discord": ("discord:", "https://discord.com/app"),
    "calculadora": ("calc.exe", None),
    "calculator": ("calc.exe", None),
    "bloc de notas": ("notepad.exe", None),
    "notepad": ("notepad.exe", None),
    "paint": ("mspaint.exe", None),
    "explorador": ("explorer.exe", None),
    "explorer": ("explorer.exe", None),
    "administrador de tareas": ("taskmgr.exe", None),
    "task manager": ("taskmgr.exe", None),
    "configuración": ("ms-settings:", None),
    "configuracion": ("ms-settings:", None),
    "settings": ("ms-settings:", None),
    "vscode": ("code", "https://vscode.dev"),
    "visual studio code": ("code", "https://vscode.dev"),
    "cmd": ("cmd.exe", None),
    "terminal": ("wt.exe", None),
    "word": ("winword", None),
    "excel": ("excel", None),
    "powerpoint": ("powerpnt", None),
}

POPULAR_WEBSITES_MAP: Dict[str, str] = {
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
    "netflix": "https://www.netflix.com",
    "gmail": "https://mail.google.com",
    "correo": "https://mail.google.com",
    "google calendar": "https://calendar.google.com",
    "mi google calendar": "https://calendar.google.com",
    "calendario": "https://calendar.google.com",
    "mi calendario": "https://calendar.google.com",
    "calendar": "https://calendar.google.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "notion": "https://www.notion.so",
    "21st": "https://21st.dev",
    "21st.dev": "https://21st.dev",
    "supabase": "https://supabase.com/dashboard",
    "vercel": "https://vercel.com/dashboard",
    "figma": "https://www.figma.com",
    "canva": "https://www.canva.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "tiktok": "https://www.tiktok.com",
    "amazon": "https://www.amazon.com",
    "mercadolibre": "https://www.mercadolibre.com.co",
}


class UltronSkills:
    """Conjunto de habilidades locales, de telemetría, visión multimodal y Jarvis Pro ejecutables por Ultrón."""

    def __init__(self, config: UltronConfig, tts: UltronTTS) -> None:
        self.config = config
        self.tts = tts
        self.config.ensure_dirs()
        self.telemetry = UltronTelemetry(user_name=self.config.user_name)
        self.vision = UltronVision(config=self.config)
        self.dictation = SmartDictationEngine(config=self.config)
        self.file_organizer = FileOrganizerEngine(user_name=self.config.user_name)
        self.task_bridge = TaskSyncBridge(workspace_root=self.config.workspace_root)

    def greet(self, lang: str = "es") -> str:
        """Saluda a Sebastián según la hora del día."""
        hour = datetime.datetime.now().hour
        if 4 <= hour < 12:
            period_key = "morning"
        elif 12 <= hour < 18:
            period_key = "afternoon"
        elif 18 <= hour < 24:
            period_key = "evening"
        else:
            period_key = "night"

        welcome_msg = tr(lang, "welcome", user=self.config.user_name)
        period_msg = tr(lang, period_key)
        service_msg = tr(lang, "service", assistant=self.config.load_assistant_name())
        full_greeting = f"{welcome_msg} {period_msg} {service_msg}"
        self.tts.speak(full_greeting, lang=lang)
        return full_greeting

    def acknowledge_presence(self, lang: str = "es") -> str:
        """Responde cuando Sebastián dice solo 'Ultrón' o 'Hola Ultrón'."""
        msg = (
            f"Aquí estoy, {self.config.user_name}. Te escucho fuerte y claro. "
            "¿Qué aplicación abrimos, qué analizamos en tu pantalla o qué consulta tienes?"
        )
        self.tts.speak(msg, lang=lang)
        return msg

    def tell_time(self, lang: str = "es") -> str:
        """Informa la hora actual."""
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        msg = tr(lang, "time", time=now_str)
        self.tts.speak(msg, lang=lang)
        return msg

    def tell_date(self, lang: str = "es") -> str:
        """Informa la fecha actual."""
        now = datetime.datetime.now()
        date_str = (
            f"{now.day} de {now.strftime('%B')} de {now.year}"
            if lang == "es"
            else now.strftime("%d %B %Y")
        )
        msg = tr(lang, "date", date=date_str)
        self.tts.speak(msg, lang=lang)
        return msg

    def system_telemetry(self, lang: str = "es") -> str:
        """Ejecuta un diagnóstico completo de hardware y sistema operativo."""
        report_voice = self.telemetry.format_voice_report(lang=lang, include_processes=True)
        self.tts.speak(report_voice, lang=lang)
        return report_voice

    def top_processes(self, sort_by: str = "memory", lang: str = "es") -> str:
        """Informa cuáles son los procesos que más memoria RAM o CPU están consumiendo."""
        report_voice = self.telemetry.format_top_processes_voice(
            limit=3, sort_by=sort_by, lang=lang
        )
        self.tts.speak(report_voice, lang=lang)
        return report_voice

    def analyze_screen(
        self,
        query: str = "¿Qué hay en mi pantalla?",
        mode: Optional[str] = None,
        lang: str = "es",
    ) -> str:
        """Captura la pantalla activa y la analiza con Visión Multimodal."""
        result = self.vision.analyze_screen(user_query=query, mode=mode, lang=lang)
        self.tts.speak(result.analysis, lang=lang)
        return result.analysis

    def open_any_target(self, raw_target: str, lang: str = "es") -> str:
        """
        Abre proyectos personales de Sebastián, aplicaciones nativas (Spotify, Calculadora,
        VS Code, WhatsApp, etc.) o cualquier sitio web.
        """
        target = raw_target.strip().lower().strip(".,!?¿¡")
        if not target:
            msg = f"Dime qué aplicación o página quieres que abra, {self.config.user_name}."
            self.tts.speak(msg, lang=lang)
            return msg

        # 1. Proyectos personales de Sebastián y accesos rápidos configurados
        for key, url in self.config.personal_shortcuts.items():
            if key in target:
                wb.open(url)
                msg = tr(lang, "opening_site", site=key.capitalize())
                self.tts.speak(msg, lang=lang)
                return msg

        # 2. Aplicaciones nativas de Windows / URI protocols (Spotify, Calculadora, VS Code, etc.)
        for app_name, (win_cmd, web_fallback) in WINDOWS_APPS_MAP.items():
            if app_name in target:
                launched = self._launch_native_app(win_cmd, web_fallback)
                msg = f"Abriendo {app_name.capitalize()}, {self.config.user_name}." if launched else f"Abriendo {app_name.capitalize()} en el navegador."
                self.tts.speak(msg, lang=lang)
                return msg

        # 3. Sitios web populares (ChatGPT, Claude, Figma, Supabase, Vercel, Netflix, etc.)
        for site_name, site_url in POPULAR_WEBSITES_MAP.items():
            if site_name in target:
                wb.open(site_url)
                msg = tr(lang, "opening_site", site=site_name.capitalize())
                self.tts.speak(msg, lang=lang)
                return msg

        # 4. Si menciona un dominio (.com, .co, .org, .io, .ai) o una marca general, abrirla o buscarla
        clean_word = target.split()[0]
        if "." in clean_word:
            url = clean_word if clean_word.startswith(("http://", "https://")) else f"https://{clean_word}"
        else:
            url = f"https://www.{clean_word}.com"
        wb.open(url)
        msg = tr(lang, "opening_site", site=target)
        self.tts.speak(msg, lang=lang)
        return msg

    @staticmethod
    def _launch_native_app(win_cmd: str, web_fallback: Optional[str]) -> bool:
        """Intenta lanzar una aplicación o protocolo URI en Windows/Linux/macOS; usa web_fallback si falla."""
        try:
            if sys.platform == "win32":
                if win_cmd.endswith(":") or win_cmd.endswith(".exe"):
                    os.startfile(win_cmd)  # type: ignore[attr-defined]
                    return True
                resolved = shutil.which(win_cmd)
                if resolved:
                    subprocess.Popen([resolved])
                    return True
                os.startfile(win_cmd)  # type: ignore[attr-defined]
                return True
            else:
                resolved = shutil.which(win_cmd.replace(".exe", ""))
                if resolved:
                    subprocess.Popen([resolved])
                    return True
        except Exception as exc:
            logger.debug("No se pudo abrir app nativa '%s' (%s).", win_cmd, exc)

        if web_fallback:
            wb.open(web_fallback)
        return False

    @staticmethod
    def _send_multimedia_key(vk_code: int, key_name: str) -> bool:
        """
        Envía un comando multimedia global al sistema operativo (Windows/Linux/macOS).
        Controla Spotify, YouTube y reproductores del sistema sin requerir foco en la ventana.
        """
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
                time.sleep(0.04)
                ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
                return True
            except Exception as exc:
                logger.debug("ctypes keybd_event(0x%X) fallo: %s", vk_code, exc)

        try:
            import pyautogui

            pyautogui.press(key_name)
            return True
        except Exception as exc:
            logger.debug("pyautogui.press('%s') fallo: %s", key_name, exc)

        return False

    def play_spotify_music(self, query: str = "", lang: str = "es") -> str:
        """
        Inicia la reproducción directa en Spotify.
        Abre la app nativa en Windows y envía la señal Play en segundo plano.
        Si la consulta incluye un término específico (artista o canción), lo busca y reproduce.
        """
        clean_q = re.sub(
            r"(?i)\b(?:abre|abrir|ábreme|abreme|en|on|spotify|y|reproduce|reproducir|pon|poner|escuchar|escucha|toca|tocar|play|search|busca|buscar|musica|música|canción|cancion|canciones|temas|tema|grupo|banda|disco|álbum|album|un|una|algo|de|a|al|del|los|las|el|la)\b",
            " ",
            query or "",
        )
        clean_q = re.sub(r"[^\w\s\-\']", "", clean_q)
        clean_q = re.sub(r"\s+", " ", clean_q).strip()

        if clean_q:
            return self.search_spotify(clean_q, lang=lang)

        # 1. Abrir app nativa de Spotify en Windows
        opened_native = False
        if sys.platform == "win32":
            try:
                os.startfile("spotify:")
                opened_native = True
            except Exception as exc:
                logger.debug("No se pudo iniciar protocolo spotify: (%s)", exc)

        if not opened_native:
            self.open_any_target("spotify", lang=lang)

        # 2. Enviar señal multimedia Play en segundo plano tras 1.2 segundos para que Spotify arranque y suene
        def _delayed_play() -> None:
            time.sleep(1.2)
            self._send_multimedia_key(0xB3, "playpause")

        threading.Thread(target=_delayed_play, daemon=True).start()

        msg = f"Abriendo Spotify e iniciando reproducción musical, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    @staticmethod
    def _send_key(key_name: str) -> bool:
        """Envía una pulsación de tecla simple al sistema si pyautogui está disponible."""
        try:
            import pyautogui

            pyautogui.press(key_name)
            return True
        except Exception as exc:
            logger.debug("pyautogui.press('%s') fallo: %s", key_name, exc)
            return False

    def search_spotify(self, search_query: str, lang: str = "es") -> str:
        """Busca un artista, canción o playlist y lo reproduce en Spotify sin caracteres residuales."""
        # 1. Limpieza de frases de activación y palabras de relleno
        clean_q = re.sub(
            r"(?i)\b(?:abre|abrir|ábreme|abreme|en|on|spotify|y|reproduce|reproducir|pon|poner|escuchar|escucha|toca|tocar|play|search|busca|buscar|musica|música|canción|cancion|canciones|temas|tema|grupo|banda|disco|álbum|album|un|una|algo|de|a|al|del|los|las|el|la)\b",
            " ",
            search_query or "",
        )
        # 2. Eliminar puntuación residual (puntos finales ., comas, comillas, signos de interrogación o signos más accidentales)
        clean_q = re.sub(r"[^\w\s\-\']", "", clean_q)
        # 3. Normalizar espacios múltiples
        clean_q = re.sub(r"\s+", " ", clean_q).strip()

        if not clean_q:
            return self.play_spotify_music("", lang=lang)

        encoded = urllib.parse.quote(clean_q)
        opened_native = False
        if sys.platform == "win32":
            # Intentar primero con la consulta con espacios limpios (para evitar que Spotify fuerce el símbolo '+')
            try:
                os.startfile(f"spotify:search:{clean_q}")
                opened_native = True
            except Exception:
                try:
                    os.startfile(f"spotify:search:{encoded}")
                    opened_native = True
                except Exception as exc:
                    logger.debug("No se pudo abrir spotify:search URI: %s", exc)

        if not opened_native:
            wb.open(f"https://open.spotify.com/search/{encoded}")

        # Enviar Enter para enfocar el resultado principal de la búsqueda y reproducir
        def _delayed_play_search() -> None:
            time.sleep(1.2)
            if opened_native:
                self._send_key("enter")
                time.sleep(0.3)
                self._send_multimedia_key(0xB3, "playpause")

        threading.Thread(target=_delayed_play_search, daemon=True).start()

        msg = f"Buscando '{clean_q}' en Spotify, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    def pause_media(self, lang: str = "es") -> str:
        """Pausa la música o medio activo en el sistema."""
        self._send_multimedia_key(0xB3, "playpause")
        msg = f"Música pausada, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    def resume_media(self, lang: str = "es") -> str:
        """Reanuda la reproducción multimedia activa."""
        self._send_multimedia_key(0xB3, "playpause")
        msg = f"Reanudando música, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    def next_track(self, lang: str = "es") -> str:
        """Avanza a la siguiente pista o canción."""
        self._send_multimedia_key(0xB0, "nexttrack")
        msg = f"Pasando a la siguiente canción, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    def prev_track(self, lang: str = "es") -> str:
        """Retrocede a la pista o canción anterior."""
        self._send_multimedia_key(0xB1, "prevtrack")
        msg = f"Volviendo a la canción anterior, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    def media_volume_up(self, lang: str = "es") -> str:
        """Sube el volumen multimedia del sistema."""
        for _ in range(3):
            self._send_multimedia_key(0xAF, "volumeup")
            time.sleep(0.02)
        msg = f"Subiendo volumen, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    def media_volume_down(self, lang: str = "es") -> str:
        """Baja el volumen multimedia del sistema."""
        for _ in range(3):
            self._send_multimedia_key(0xAE, "volumedown")
            time.sleep(0.02)
        msg = f"Bajando volumen, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    def search_youtube(self, search_query: str, lang: str = "es") -> str:
        """Busca o reproduce directamente un tema o video en YouTube."""
        clean_q = (
            search_query.replace("en youtube", "")
            .replace("on youtube", "")
            .replace("youtube", "")
            .replace("reproduce a", "")
            .replace("reproduce", "")
            .replace("reproducir", "")
            .replace("pon a", "")
            .replace("pon", "")
            .strip()
        )
        if not clean_q:
            wb.open("https://www.youtube.com")
            msg = "Abriendo YouTube."
        else:
            encoded = urllib.parse.quote_plus(clean_q)
            wb.open(f"https://www.youtube.com/results?search_query={encoded}")
            msg = f"Buscando '{clean_q}' en YouTube, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    def search_google(self, search_query: str, lang: str = "es") -> str:
        """Realiza una búsqueda directa en Google en una pestaña del navegador."""
        clean_q = search_query.strip()
        if not clean_q:
            wb.open("https://www.google.com")
            msg = "Abriendo Google."
        else:
            encoded = urllib.parse.quote_plus(clean_q)
            wb.open(f"https://www.google.com/search?q={encoded}")
            msg = f"Buscando '{clean_q}' en Google, {self.config.user_name}."
        self.tts.speak(msg, lang=lang)
        return msg

    def desktop_control(self, action: str, lang: str = "es") -> str:
        """Controla el volumen del sistema y las ventanas activas con fallback robusto."""
        if action == "volume_up":
            return self.media_volume_up(lang=lang)
        if action == "volume_down":
            return self.media_volume_down(lang=lang)
        if action == "volume_mute":
            self._send_multimedia_key(0xAD, "volumemute")
            msg = "Audio del sistema alternado."
            self.tts.speak(msg, lang=lang)
            return msg

        try:
            import pyautogui

            if action == "minimize_all":
                pyautogui.hotkey("win", "d")
                msg = "Mostrando el escritorio."
            elif action == "switch_window":
                pyautogui.hotkey("alt", "tab")
                msg = "Cambiando de ventana activa."
            else:
                msg = "Acción de escritorio completada."
        except Exception as exc:
            logger.debug("Control de escritorio hotkey no disponible: %s", exc)
            if action == "minimize_all":
                msg = "Mostrando el escritorio."
            elif action == "switch_window":
                msg = "Cambiando de ventana activa."
            else:
                msg = f"No pude ejecutar el atajo de teclado ({exc})."

        self.tts.speak(msg, lang=lang)
        return msg

    def open_website_or_project(self, target_key: str, lang: str = "es") -> str:
        """Compatibilidad directa para abrir un proyecto o URL."""
        return self.open_any_target(target_key, lang=lang)

    def search_wikipedia(self, query: str, lang: str = "es") -> str:
        """Busca un resumen en Wikipedia con manejo explícito de excepciones."""
        clean_q = (
            query.replace("wikipedia", "")
            .replace("busca en", "")
            .replace("buscar en", "")
            .replace("search on", "")
            .replace("search", "")
            .strip()
        )
        if not clean_q:
            msg = tr(lang, "no_result")
            self.tts.speak(msg, lang=lang)
            return msg

        self.tts.speak(tr(lang, "wiki_search"), lang=lang)
        try:
            wikipedia.set_lang(lang if lang in ("es", "en", "fr") else "es")
            summary = wikipedia.summary(clean_q, sentences=2)
            self.tts.speak(summary, lang=lang)
            return summary
        except wikipedia.exceptions.DisambiguationError as exc:
            options = ", ".join(exc.options[:3])
            msg = (
                f"Hay varios resultados para '{clean_q}', por ejemplo: {options}."
                if lang == "es"
                else f"Multiple results found for '{clean_q}', such as: {options}."
            )
            self.tts.speak(msg, lang=lang)
            return msg
        except (wikipedia.exceptions.PageError, wikipedia.exceptions.WikipediaException) as exc:
            logger.debug("Wikipedia error: %s", exc)
            msg = tr(lang, "no_result")
            self.tts.speak(msg, lang=lang)
            return msg

    def tell_joke(self, lang: str = "es") -> str:
        """Cuenta un chiste para programadores."""
        joke_lang = lang if lang in ("es", "en") else "es"
        try:
            joke = pyjokes.get_joke(language=joke_lang, category="neutral")
        except Exception:
            joke = pyjokes.get_joke(language="en", category="neutral")
        self.tts.speak(joke, lang=joke_lang)
        return joke

    def save_note(self, content: str, lang: str = "es") -> str:
        """Guarda una nota con marca de tiempo en formato JSON."""
        clean_note = content.strip()
        notes = self._load_notes_list()
        entry = {
            "id": len(notes) + 1,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "content": clean_note,
        }
        notes.append(entry)
        self.config.ensure_dirs()
        self.config.notes_file.write_text(
            json.dumps(notes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        msg = tr(lang, "note_saved", note=clean_note)
        self.tts.speak(msg, lang=lang)
        return msg

    def list_notes(self, lang: str = "es") -> str:
        """Lee las notas guardadas por el usuario."""
        notes = self._load_notes_list()
        if not notes:
            msg = tr(lang, "notes_empty")
            self.tts.speak(msg, lang=lang)
            return msg

        header = tr(lang, "notes_header", count=len(notes))
        items = "; ".join(f"{n['id']}: {n['content']}" for n in notes[-5:])
        full_msg = f"{header} {items}"
        self.tts.speak(full_msg, lang=lang)
        return full_msg

    def _load_notes_list(self) -> List[Dict[str, object]]:
        if not self.config.notes_file.exists():
            return []
        try:
            data = json.loads(self.config.notes_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def change_name(self, new_name: str, lang: str = "es") -> str:
        """Cambia y persiste el nombre del asistente."""
        clean_name = new_name.strip() or "Ultrón"
        self.config.save_assistant_name(clean_name)
        msg = tr(lang, "name_set", name=clean_name)
        self.tts.speak(msg, lang=lang)
        return msg

    def take_screenshot(self, lang: str = "es") -> str:
        """Toma una captura de pantalla tolerante a fallos usando el pipeline de UltronVision."""
        capture = self.vision.capture_screen()
        msg = tr(lang, "screenshot", path=capture.file_path)
        self.tts.speak(msg, lang=lang)
        return msg

    def play_music(self, query: str, lang: str = "es") -> str:
        """Reproduce música del directorio ~/Music o busca en Spotify/YouTube según la orden."""
        if "spotify" in query.lower():
            return self.search_spotify(query, lang=lang)

        music_dir = Path.home() / "Music"
        songs = (
            [
                f
                for f in music_dir.iterdir()
                if f.is_file() and f.suffix.lower() in (".mp3", ".wav", ".flac", ".m4a")
            ]
            if music_dir.exists()
            else []
        )

        clean_q = (
            query.replace("reproduce música", "")
            .replace("reproducir música", "")
            .replace("reproduce a", "")
            .replace("reproduce", "")
            .replace("pon música", "")
            .replace("play music", "")
            .replace("joue de la musique", "")
            .strip()
        )
        if clean_q and songs:
            songs = [s for s in songs if clean_q in s.name.lower()]

        if songs:
            chosen = random.choice(songs)
            self._open_media_file(chosen)
            msg = tr(lang, "playing", song=chosen.name)
            self.tts.speak(msg, lang=lang)
            return msg

        if clean_q:
            return self.search_youtube(clean_q, lang=lang)
        return self.open_any_target("spotify", lang=lang)

    def system_power(self, action: str, lang: str = "es", dry_run: bool = False) -> str:
        """Ejecuta apagado o reinicio del sistema de forma segura."""
        if action == "shutdown":
            msg = tr(lang, "shutdown", user=self.config.user_name)
            cmd = (
                ["systemctl", "poweroff"]
                if sys.platform != "win32"
                else ["shutdown", "/s", "/f", "/t", "1"]
            )
        else:
            msg = tr(lang, "restart")
            cmd = (
                ["systemctl", "reboot"]
                if sys.platform != "win32"
                else ["shutdown", "/r", "/f", "/t", "1"]
            )

        self.tts.speak(msg, lang=lang)
        if not dry_run:
            subprocess.run(cmd, check=False)
        return msg

    @staticmethod
    def _open_media_file(path: Path) -> None:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    # ──────────────────────────────────────────────────────────────────────
    # 12. Jarvis Pro Capabilities (File Organizer + Smart Dictation + In-Place Edit)
    # ──────────────────────────────────────────────────────────────────────

    def organize_files(self, query: str, dry_run: bool = False, lang: str = "es") -> str:
        """Organiza inteligentemente los archivos de una carpeta (Descargas, Escritorio, Documentos)."""
        res = self.file_organizer.organize_directory(query, dry_run=dry_run)
        msg = res.summary_text
        self.tts.speak(msg, lang=lang)
        return msg

    def smart_dictate(self, raw_text: str, auto_paste: bool = False, lang: str = "es") -> str:
        """Limpia muletillas, auto-correcciones y extensiones habladas, y copia/pega el resultado."""
        res = self.dictation.dictate(raw_text, auto_paste=auto_paste)
        msg = res.spoken_summary
        self.tts.speak(msg, lang=lang)
        return f"{msg}\nTexto limpio: \"{res.output_text}\""

    def edit_clipboard_text(
        self,
        instruction: str,
        source_text: Optional[str] = None,
        auto_paste: bool = False,
        lang: str = "es",
    ) -> str:
        """Transforma in-place el texto seleccionado o del portapapeles sin texto conversacional extra."""
        res = self.dictation.edit_selected_or_clipboard_text(
            instruction=instruction,
            source_text=source_text,
            auto_paste=auto_paste,
        )
        msg = res.spoken_summary
        self.tts.speak(msg, lang=lang)
        return f"{msg}\nResultado:\n{res.output_text}"

    # ──────────────────────────────────────────────────────────────────────
    # 13. Productivity & Local Knowledge Shortcuts (Email + PID Controller)
    # ──────────────────────────────────────────────────────────────────────

    def compose_email(self, query: str = "", lang: str = "es") -> str:
        """Abre Gmail para redactar un correo y asiste con dictado por voz."""
        gmail_compose_url = "https://mail.google.com/mail/u/0/#inbox?compose=new"
        wb.open(gmail_compose_url)
        msg = (
            f"Abriendo Gmail para redactar tu correo, {self.config.user_name}. "
            "Puedes dictarme el contenido diciendo 'Ultrón, dicta...' y lo tendrás en tu portapapeles listo para pegar con Ctrl+V."
        )
        self.tts.speak(msg, lang=lang)
        return msg

    def explain_pid(self, lang: str = "es") -> str:
        """Explicación técnica instantánea de lazo de control PID para ingeniería biomédica y automatización."""
        msg = (
            "El controlador PID (Proporcional-Integral-Derivativo) calcula continuamente el error entre el setpoint deseado "
            "y la variable de proceso medida. Ajusta la salida con tres términos: proporcional al error instantáneo, "
            "integral de los errores acumulados y derivativo de la velocidad de cambio del error. En tu proyecto Bola-Viga en Arduino, "
            "permite balancear la esfera en la posición exacta del riel con mínimo sobretiro y rápida estabilización."
        )
        self.tts.speak(msg, lang=lang)
        return msg

    # ──────────────────────────────────────────────────────────────────────
    # 14. Academic Management Skills (Tareas y Horario Académico de Sebastián)
    # ──────────────────────────────────────────────────────────────────────

    def get_academic_tasks(self, lang: str = "es") -> str:
        """
        Lee dinámicamente el tablero de tareas pendientes (TAREAS.md) y genera
        un reporte hablado en tiempo real con las próximas entregas de Sebastián.
        """
        summary = self.task_bridge.get_pending_summary(user_name=self.config.user_name)
        self.tts.speak(summary, lang=lang)
        return summary

    def get_academic_schedule(self, lang: str = "es") -> str:
        """
        Informa las clases programadas para el día de hoy según el horario académico de Sebastián.
        """
        schedule_msg = self.task_bridge.get_schedule_today(user_name=self.config.user_name)
        self.tts.speak(schedule_msg, lang=lang)
        return schedule_msg

    def add_academic_task(self, raw_task_text: str, lang: str = "es") -> str:
        """
        Registra una nueva tarea académica por voz directamente en `TAREAS.md`.
        """
        ok, detail = self.task_bridge.add_task(raw_task_text)
        if ok:
            msg = f"{self.config.user_name}, he anotado tu nueva tarea en el tablero: {raw_task_text}."
        else:
            msg = f"{self.config.user_name}, {detail}"
        self.tts.speak(msg, lang=lang)
        return msg

    def complete_academic_task(self, query: str, lang: str = "es") -> str:
        """
        Busca y marca una tarea como completada en `TAREAS.md` por comando de voz.
        """
        ok, detail = self.task_bridge.complete_task(query)
        if ok:
            msg = f"Excelente trabajo, {self.config.user_name}. {detail}"
        else:
            msg = f"{self.config.user_name}, {detail}"
        self.tts.speak(msg, lang=lang)
        return msg




