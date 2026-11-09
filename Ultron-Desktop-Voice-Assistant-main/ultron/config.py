"""
Configuración centralizada de Ultrón.
Carga variables de entorno y define el perfil personalizado de Sebastián Giraldo Acosta.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"


@dataclass
class UltronConfig:
    """Configuración global del asistente Ultrón."""

    assistant_name: str = field(
        default_factory=lambda: os.getenv("ULTRON_NAME", "HALCÓN")
    )
    user_name: str = field(
        default_factory=lambda: os.getenv("ULTRON_USER_NAME", "Sebastián")
    )
    default_lang: str = field(
        default_factory=lambda: os.getenv("ULTRON_DEFAULT_LANG", "es")
    )

    # Paso 3: STT ("hybrid": Google STT rápido sin consumir RAM + fallback offline a faster-whisper)
    stt_engine: str = field(
        default_factory=lambda: os.getenv("ULTRON_STT_ENGINE", "hybrid").lower()
    )
    whisper_model: str = field(
        default_factory=lambda: os.getenv("ULTRON_WHISPER_MODEL", "base")
    )

    # Paso 2: Wake-Word Detection
    wake_word_enabled: bool = field(
        default_factory=lambda: os.getenv("ULTRON_WAKE_WORD_ENABLED", "true").lower() == "true"
    )
    wake_words: List[str] = field(
        default_factory=lambda: [
            w.strip().lower()
            for w in os.getenv(
                "ULTRON_WAKE_WORDS",
                "halcon,halcón,hey halcon,hey halcón,oye halcon,oye halcón,ultron,ultrón,hey ultron,oye ultron",
            ).split(",")
            if w.strip()
        ]
    )

    # Paso 1: Integración con IA Generativa (Gemini / Ollama)
    llm_provider: str = field(
        default_factory=lambda: os.getenv("ULTRON_LLM_PROVIDER", "gemini").lower()
    )
    gemini_api_key: str = field(
        default_factory=lambda: (
            ""
            if os.getenv("GEMINI_API_KEY", "").strip()
            in ("", "tu_api_key_aqui", "your_api_key_here", "AIzaSyTuClaveAqui...")
            else os.getenv("GEMINI_API_KEY", "").strip()
        )
    )
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    )
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2")
    )
    deepseek_api_key: str = field(
        default_factory=lambda: (
            ""
            if os.getenv("DEEPSEEK_API_KEY", "").strip()
            in ("", "tu_deepseek_api_key", "your_deepseek_key_here")
            else os.getenv("DEEPSEEK_API_KEY", "").strip()
        )
    )
    deepseek_model: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    )
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    )

    # Rutas de datos persistentes
    workspace_root: Path = field(default_factory=lambda: BASE_DIR.parent)
    name_file: Path = field(default_factory=lambda: DATA_DIR / "assistant_name.txt")
    notes_file: Path = field(default_factory=lambda: DATA_DIR / "notes.json")
    screenshots_dir: Path = field(default_factory=lambda: SCREENSHOTS_DIR)

    # Accesos directos personalizados del ecosistema de Sebastián Giraldo Acosta
    personal_shortcuts: Dict[str, str] = field(
        default_factory=lambda: {
            "github": "https://github.com/sebastiangiraldoa-sga",
            "repositorio": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity",
            "proyectos": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity",
            "liofilizados": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/proyectos-externos/liofilizados",
            "liofilizado": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/proyectos-externos/liofilizados",
            "bioinstrumentacion": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/pregrado-biomedica/bioinstrumentacion-2",
            "bioinstrumentación": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/pregrado-biomedica/bioinstrumentacion-2",
            "anestesia": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/pregrado-biomedica/bioinstrumentacion-2",
            "vision": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/especializacion-ia/vision-computacional",
            "visión": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/especializacion-ia/vision-computacional",
            "aprendizaje automatico": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/especializacion-ia/aprendizaje-automatico",
            "aprendizaje automático": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/especializacion-ia/aprendizaje-automatico",
            "clinica": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/pregrado-biomedica/ingenieria-clinica-2",
            "clínica": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/pregrado-biomedica/ingenieria-clinica-2",
            "redes": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/pregrado-biomedica/redes-neuronales",
            "redes neuronales": "https://github.com/sebastiangiraldoa-sga/Projects_Antigravity/tree/main/pregrado-biomedica/redes-neuronales",
            "calendar": "https://calendar.google.com",
            "calendario": "https://calendar.google.com",
            "drive": "https://drive.google.com",
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
        }
    )

    def ensure_dirs(self) -> None:
        """Crea los directorios de datos y capturas si no existen."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def load_assistant_name(self) -> str:
        """Carga el nombre personalizado desde disco o retorna el configurado por defecto."""
        try:
            if self.name_file.exists():
                saved = self.name_file.read_text(encoding="utf-8").strip()
                if saved:
                    return saved
        except OSError:
            pass
        return self.assistant_name

    def save_assistant_name(self, new_name: str) -> None:
        """Persiste un nuevo nombre para el asistente en disco."""
        self.ensure_dirs()
        self.name_file.write_text(new_name.strip(), encoding="utf-8")
        self.assistant_name = new_name.strip()
