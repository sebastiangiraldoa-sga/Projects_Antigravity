"""
Módulo Jarvis Pro para Ultrón v5.2 (`ultron.jarvis_pro`).
Inspirado en la arquitectura de `akshayaggarwal99/jarvis-ai-assistant` y adaptado nativamente para Windows 11:

1. `SmartDictationEngine`:
   - Limpieza instantánea de muletillas ("eh", "um", "este"), autocorrecciones al vuelo
     ("a las 4pm no perdón a las 3pm" -> "a las 3pm") y conversión de extensiones de código
     ("readme punto md" -> "readme.md", "main punto py" -> "main.py").
   - Inyección directa en portapapeles y pegado rápido en el cursor activo (`Ctrl+V`).
   - Edición In-Place (`Direct Text Editing`): Toma el texto seleccionado o copiado en el
     portapapeles (VS Code, Word, Gmail, WhatsApp), aplica la transformación pedida por voz
     (traducir, formalizar, resumir, refactorizar) sin preámbulos y lo deja listo/pegado.

2. `FileOrganizerEngine`:
   - Analiza y organiza automáticamente carpetas como `Descargas` (`Downloads`) o `Escritorio` (`Desktop`)
     clasificando archivos en subcarpetas por categoría (`Documentos`, `Imagenes`, `Videos`,
     `Audio`, `Instaladores_Zip`, `Codigo_Scripts`) sin sobrescribir archivos existentes.

3. `AgenticToolRouter`:
   - Enrutador inteligente basado en IA (JSON estructurado) que interpreta intenciones naturales
     cuando una frase no coincide con un patrón fijo.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ultron.config import UltronConfig
from ultron.llm import UltronBrain

logger = logging.getLogger("ultron.jarvis_pro")

# Extensiones de archivo para conversión hablada ("readme punto md" -> "readme.md")
SPOKEN_EXTENSIONS = (
    "md",
    "txt",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "csv",
    "html",
    "css",
    "js",
    "ts",
    "tsx",
    "jsx",
    "py",
    "java",
    "cpp",
    "c",
    "h",
    "cs",
    "go",
    "rs",
    "json",
    "xml",
    "yml",
    "yaml",
    "sql",
    "sh",
    "bat",
    "ps1",
    "env",
    "png",
    "jpg",
    "jpeg",
    "svg",
    "webp",
    "mp4",
    "mp3",
    "wav",
    "zip",
    "exe",
)

FILE_CATEGORIES: Dict[str, Tuple[str, ...]] = {
    "Documentos": (".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".epub"),
    "Imagenes": (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".webp", ".ico", ".heic"),
    "Videos": (".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv", ".m4v", ".3gp"),
    "Audio": (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"),
    "Instaladores_Zip": (".zip", ".rar", ".7z", ".tar", ".gz", ".msi", ".exe", ".dmg", ".pkg", ".deb", ".iso"),
    "Codigo_Scripts": (".js", ".ts", ".tsx", ".jsx", ".py", ".sh", ".bat", ".ps1", ".html", ".css", ".json", ".xml", ".yml", ".yaml", ".sql", ".ino", ".cpp", ".c", ".h"),
}

BLOCKED_SYSTEM_PATHS_WIN = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
    "c:\\system volume information",
)

BLOCKED_SYSTEM_PATHS_UNIX = (
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/var",
    "/boot",
    "/sys",
    "/proc",
    "/root",
    "/dev",
)


@dataclass
class DictationResult:
    """Resultado de un dictado limpio o edición in-place."""

    original_text: str
    processed_text: str
    mode: str  # "dictate" | "edit_selection"
    copied_to_clipboard: bool
    pasted_to_window: bool
    message: str

    @property
    def output_text(self) -> str:
        return self.processed_text

    @property
    def spoken_summary(self) -> str:
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "processed_text": self.processed_text,
            "output_text": self.processed_text,
            "mode": self.mode,
            "copied_to_clipboard": self.copied_to_clipboard,
            "pasted_to_window": self.pasted_to_window,
            "message": self.message,
            "spoken_summary": self.message,
        }


@dataclass
class FileOrganizationResult:
    """Resultado de analizar u organizar un directorio."""

    directory: str
    action: str  # "organize" | "analyze"
    total_files_moved: int
    categories_summary: Dict[str, int]
    message: str

    @property
    def summary_text(self) -> str:
        return self.message

    @property
    def total_moved(self) -> int:
        return self.total_files_moved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "directory": self.directory,
            "action": self.action,
            "total_files_moved": self.total_files_moved,
            "total_moved": self.total_files_moved,
            "categories_summary": self.categories_summary,
            "message": self.message,
            "summary_text": self.message,
        }


class SmartDictationEngine:
    """
    Motor de Dictado Inteligente y Edición de Texto Seleccionado/Portapapeles
    inspirado en `prompts.ts` y `assistant-processor.ts` de Jarvis AI.
    """

    def __init__(self, config: UltronConfig, brain: Optional[UltronBrain] = None) -> None:
        self.config = config
        self.brain = brain or UltronBrain(config)

    @staticmethod
    def clean_dictation(raw_text: str) -> str:
        """
        Transforma palabras habladas en texto limpio y puntuado en < 1ms:
        1. Elimina muletillas ("eh", "ehm", "um", "uh", "este").
        2. Resuelve autocorrecciones habladas ("a las 4pm no perdón a las 3pm" -> "a las 3pm").
        3. Convierte extensiones de archivos ("readme punto md" / "readme dot md" -> "readme.md").
        4. Capitaliza y añade puntuación final limpia.
        """
        text = raw_text.strip()
        if not text:
            return ""

        # 1. Eliminar prefijos de comando de dictado si quedaron presentes
        text = re.sub(
            r"^(?:dicta|dictar|escribe\s+esto|escribe|pega\s+esto|dictate|type\s+this)[\s,:.-]*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        # 2. Eliminar muletillas aisladas al inicio o entre pausas
        text = re.sub(
            r"\b(?:eh+|ehm+|uh+|um+|este+|mmm+)\b[\s,]*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # 3. Autocorrecciones habladas:
        # Ej: "nos vemos a las 4pm no perdón a las 3pm en la oficina" -> "nos vemos a las 3pm en la oficina"
        # Caso A: Horas o cifras corregidas ("a las 4pm no perdón a las 3pm" / "4pm till 3pm" / "el lunes digo el martes")
        text = re.sub(
            r"\b(a\s+las\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s+(?:no\s+perd[oó]n|perd[oó]n|digo|mejor\s+dicho|no\s+espera)\s+(a\s+las\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
            r"\2",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\b(\d{1,2}\s*(?:am|pm))\s+(?:till|no\s+wait|I\s+mean|sorry)\s+(\d{1,2}\s*(?:am|pm))\b",
            r"\2",
            text,
            flags=re.IGNORECASE,
        )
        # Caso B: Días de la semana corregidos ("el lunes no perdón el martes")
        days_pattern = r"(?:el\s+)?(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)"
        text = re.sub(
            rf"\b({days_pattern})\s+(?:no\s+perd[oó]n|perd[oó]n|digo|mejor\s+dicho)\s+({days_pattern})\b",
            r"\2",
            text,
            flags=re.IGNORECASE,
        )

        # 4. Conversión de extensiones de archivos ("readme punto md" / "config dot json")
        ext_Alternation = "|".join(SPOKEN_EXTENSIONS)
        text = re.sub(
            rf"\b([a-zA-Z0-9_-]+)\s+(?:punto|dot)\s+({ext_Alternation})\b",
            lambda m: f"{m.group(1)}.{m.group(2).lower()}",
            text,
            flags=re.IGNORECASE,
        )

        # 5. Comandos básicos de puntuación hablada
        text = re.sub(r"\s+\b(?:punto\s+y\s+aparte|nueva\s+l[ií]nea)\b\s*", ".\n", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+\b(?:punto\s+seguido)\b\s*", ". ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+\b(?:signo\s+de\s+interrogaci[oó]n)\b", "?", text, flags=re.IGNORECASE)

        # Limpiar espacios múltiples
        text = re.sub(r"[ \t]{2,}", " ", text).strip()

        # 6. Capitalizar primera letra y asegurar punto final si es una oración larga sin signo final
        if text:
            text = text[0].upper() + text[1:]
            if len(text.split()) >= 4 and text[-1] not in ".!?:;)\"'":
                text += "."

        return text

    @staticmethod
    def get_clipboard_text() -> str:
        """Obtiene el texto actual del portapapeles de forma segura y multiplataforma."""
        try:
            import pyperclip  # type: ignore[import-not-found]

            content = pyperclip.paste()
            if isinstance(content, str):
                return content
        except Exception:
            pass

        if sys.platform == "win32":
            try:
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                if res.returncode == 0:
                    return res.stdout.strip()
            except Exception:
                pass
        return ""

    @staticmethod
    def set_clipboard_text(text: str) -> bool:
        """Copia el texto indicado al portapapeles del sistema."""
        if not text:
            return False
        try:
            import pyperclip  # type: ignore[import-not-found]

            pyperclip.copy(text)
            return True
        except Exception:
            pass

        if sys.platform == "win32":
            try:
                proc = subprocess.Popen(
                    ["clip"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                proc.communicate(input=text.encode("utf-16le"), timeout=3)
                return proc.returncode == 0
            except Exception:
                pass
        return False

    @staticmethod
    def simulate_paste_in_previous_window(switch_back_first: bool = False) -> bool:
        """
        En Windows/Desktop, pega el contenido del portapapeles con Ctrl+V.
        Si `switch_back_first=True` (cuando se invoca desde un botón del HUD),
        hace Alt+Tab breve hacia la ventana donde estaba trabajando el usuario y pega.
        """
        try:
            import pyautogui  # type: ignore[import-untyped]

            if switch_back_first:
                pyautogui.hotkey("alt", "tab")
                time.sleep(0.28)
            pyautogui.hotkey("ctrl", "v")
            return True
        except Exception as exc:
            logger.debug("No se pudo simular Ctrl+V automático: %s", exc)
            return False

    def dictate(
        self,
        raw_text: str,
        auto_paste: bool = False,
        switch_window: bool = False,
    ) -> DictationResult:
        """Limpia el dictado, lo copia al portapapeles y opcionalmente lo pega."""
        cleaned = self.clean_dictation(raw_text)
        copied = self.set_clipboard_text(cleaned)
        pasted = False
        if auto_paste and copied:
            pasted = self.simulate_paste_in_previous_window(switch_back_first=switch_window)

        action_note = (
            "Texto limpio pegado e insertado en tu portapapeles"
            if pasted
            else "Texto limpio copiado a tu portapapeles (presiona Ctrl+V donde quieras pegarlo)"
        )
        msg = f"{action_note}: «{cleaned}»"
        return DictationResult(
            original_text=raw_text,
            processed_text=cleaned,
            mode="dictate",
            copied_to_clipboard=copied,
            pasted_to_window=pasted,
            message=msg,
        )

    def edit_selected_or_clipboard_text(
        self,
        instruction: str,
        source_text: Optional[str] = None,
        auto_paste: bool = False,
        switch_window: bool = False,
    ) -> DictationResult:
        """
        Edición Directa In-Place (inspirada en `AssistantProcessor` de Jarvis AI):
        Toma el texto seleccionado o del portapapeles, le aplica la orden (traducir,
        corregir gramática, formalizar, resumir, refactorizar código) y devuelve SOLO
        el texto transformado en el portapapeles listo para pegar.
        """
        target_text = (source_text if source_text is not None else self.get_clipboard_text()).strip()
        if not target_text:
            msg = (
                f"No encontré texto copiado en tu portapapeles, {self.config.user_name}. "
                "Primero selecciona y copia con Ctrl+C el texto o código que quieras transformar y vuelve a indicarme la orden."
            )
            return DictationResult(
                original_text="",
                processed_text="",
                mode="edit_selection",
                copied_to_clipboard=False,
                pasted_to_window=False,
                message=msg,
            )

        editor_system_prompt = (
            "You are a precision in-place text and code editor (Jarvis Direct Editing Mode).\n"
            "CRITICAL RULES:\n"
            "1. Return ONLY the modified text or code requested by the command.\n"
            "2. NEVER include introductory phrases ('Claro, aquí tienes...', 'Here is the edited text:'), explanations, or surrounding quotes.\n"
            "3. Preserve original signatures or variable names unless asked to change them."
        )
        user_prompt = (
            f"Command: {instruction}\n\n"
            f"===SELECTED_TEXT_START===\n{target_text}\n===SELECTED_TEXT_END===\n\n"
            "Return ONLY the modified text:"
        )

        edited = self.brain.generate_raw(
            prompt=user_prompt,
            system_prompt=editor_system_prompt,
            temperature=0.15,
            max_tokens=800,
        )
        if not edited:
            # Fallback local si no hay red: aplicar limpieza de dictado sobre el texto
            edited = self.clean_dictation(target_text)

        # Limpiar posibles bloques markdown envolventes si el LLM los puso
        edited_clean = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", edited.strip())
        edited_clean = re.sub(r"\n?```$", "", edited_clean).strip()

        copied = self.set_clipboard_text(edited_clean)
        pasted = False
        if auto_paste and copied:
            pasted = self.simulate_paste_in_previous_window(switch_back_first=switch_window)

        preview = edited_clean if len(edited_clean) <= 180 else edited_clean[:177] + "..."
        msg = (
            f"Texto transformado y copiado a tu portapapeles, {self.config.user_name}: «{preview}»"
        )
        return DictationResult(
            original_text=target_text,
            processed_text=edited_clean,
            mode="edit_selection",
            copied_to_clipboard=copied,
            pasted_to_window=pasted,
            message=msg,
        )


class FileOrganizerEngine:
    """
    Organizador Inteligente de Archivos por Voz (inspirado en `file-organizer-tool.ts`).
    Clasifica archivos de Descargas, Escritorio o cualquier carpeta de usuario en subcarpetas
    por tipo sin sobrescribir nada.
    """

    def __init__(self, user_name: str = "Sebastián") -> None:
        self.user_name = user_name

    @staticmethod
    def resolve_target_directory(query_or_path: str) -> Path:
        """
        Resuelve nombres naturales ('descargas', 'escritorio', 'documentos') o rutas explícitas
        hacia la carpeta real del usuario en Windows 11 / Linux / macOS.
        """
        q = query_or_path.lower().strip()
        home = Path.home()

        if any(w in q for w in ("descarga", "download")):
            return home / "Downloads"

        if any(w in q for w in ("escritorio", "desktop")):
            # En Windows 11 con OneDrive activo, el Escritorio suele estar en OneDrive/Desktop o OneDrive/Escritorio
            for candidate in (
                home / "OneDrive" / "Escritorio",
                home / "OneDrive" / "Desktop",
                home / "Desktop",
                home / "Escritorio",
            ):
                if candidate.exists():
                    return candidate
            return home / "Desktop"

        if any(w in q for w in ("documento", "document")):
            for candidate in (
                home / "OneDrive" / "Documentos",
                home / "OneDrive" / "Documents",
                home / "Documents",
                home / "Documentos",
            ):
                if candidate.exists():
                    return candidate
            return home / "Documents"

        # Si el usuario pasó una ruta con ~ o ruta directa
        expanded = os.path.expanduser(query_or_path.strip())
        candidate_path = Path(expanded)
        if candidate_path.exists() and candidate_path.is_dir():
            return candidate_path

        # Por defecto, organizar Descargas (la carpeta más común)
        return home / "Downloads"

    @staticmethod
    def is_safe_directory(target_dir: Path) -> bool:
        """Impide tocar directorios críticos del sistema operativo."""
        try:
            resolved_str = str(target_dir.resolve()).lower()
        except Exception:
            return False

        if sys.platform == "win32":
            return not any(resolved_str.startswith(b) for b in BLOCKED_SYSTEM_PATHS_WIN)
        return not any(resolved_str.startswith(b) for b in BLOCKED_SYSTEM_PATHS_UNIX)

    @staticmethod
    def categorize_extension(ext: str) -> str:
        ext_low = ext.lower()
        for category, extensions in FILE_CATEGORIES.items():
            if ext_low in extensions:
                return category
        return "Otros"

    @staticmethod
    def get_unique_destination(dest_path: Path) -> Path:
        """Si ya existe un archivo con el mismo nombre, añade `(1)`, `(2)`, etc."""
        if not dest_path.exists():
            return dest_path
        stem = dest_path.stem
        suffix = dest_path.suffix
        parent = dest_path.parent
        counter = 1
        while True:
            candidate = parent / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def organize_directory(self, target_spec: str, dry_run: bool = False) -> FileOrganizationResult:
        """
        Clasifica todos los archivos sueltos de la carpeta indicada en subcarpetas por categoría.
        Ignora archivos ocultos, archivos temporales de descarga (`.crdownload`, `.part`, `.tmp`) y carpetas.
        """
        target_dir = self.resolve_target_directory(target_spec)
        if not self.is_safe_directory(target_dir):
            msg = f"Por seguridad, no está permitido organizar el directorio del sistema {target_dir}."
            return FileOrganizationResult(
                directory=str(target_dir),
                action="analyze" if dry_run else "organize",
                total_files_moved=0,
                categories_summary={},
                message=msg,
            )

        if not target_dir.exists() or not target_dir.is_dir():
            msg = f"No encontré la carpeta {target_dir.name} en tu sistema, {self.user_name}."
            return FileOrganizationResult(
                directory=str(target_dir),
                action="analyze" if dry_run else "organize",
                total_files_moved=0,
                categories_summary={},
                message=msg,
            )

        summary: Dict[str, int] = {}
        moved_count = 0

        for item in sorted(target_dir.iterdir()):
            if item.is_dir() or item.name.startswith("."):
                continue
            # No mover accesos directos del Escritorio (.lnk / .url) ni descargas incompletas
            if item.suffix.lower() in (".lnk", ".url", ".ini", ".crdownload", ".part", ".tmp"):
                continue

            category = self.categorize_extension(item.suffix)
            summary[category] = summary.get(category, 0) + 1

            if not dry_run:
                category_dir = target_dir / category
                category_dir.mkdir(parents=True, exist_ok=True)
                dest_file = self.get_unique_destination(category_dir / item.name)
                try:
                    shutil.move(str(item), str(dest_file))
                    moved_count += 1
                except Exception as exc:
                    logger.warning("No se pudo mover %s: %s", item.name, exc)

        total_detected = sum(summary.values())
        folder_label = target_dir.name

        if total_detected == 0:
            msg = f"Tu carpeta {folder_label} ya está completamente limpia y organizada, {self.user_name}. No hay archivos sueltos para mover."
        elif dry_run:
            breakdown = ", ".join(f"{cnt} en {cat}" for cat, cnt in summary.items())
            msg = f"Análisis de {folder_label} completado: encontré {total_detected} archivos sueltos ({breakdown})."
        else:
            breakdown = ", ".join(f"{cnt} en {cat}" for cat, cnt in summary.items())
            msg = (
                f"Organización de {folder_label} completada, {self.user_name}: "
                f"clasifiqué {moved_count} archivos automáticamente ({breakdown})."
            )

        return FileOrganizationResult(
            directory=str(target_dir),
            action="analyze" if dry_run else "organize",
            total_files_moved=moved_count if not dry_run else total_detected,
            categories_summary=summary,
            message=msg,
        )
