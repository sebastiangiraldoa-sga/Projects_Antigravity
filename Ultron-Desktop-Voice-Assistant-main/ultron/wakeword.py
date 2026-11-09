"""
Módulo de Detección de Palabra de Activación (Wake-Word Detection - Paso 2).
Permite activar a Ultrón mediante "Ultrón", "Hey Ultrón" u "Oye Ultrón",
con soporte tanto para comandos en una sola frase ("Ultrón, abre mi portafolio")
como activación en dos pasos.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable, Optional

logger = logging.getLogger("ultron.wakeword")


@dataclass
class WakeWordMatch:
    """Resultado del análisis de palabra de activación."""

    triggered: bool
    wake_word: Optional[str] = None
    remaining_command: str = ""


class WakeWordDetector:
    """
    Detector híbrido de Wake-Word:
    - Analiza transcripciones para detectar si el usuario invocó a Ultrón.
    - Extrae automáticamente el comando posterior si se dijo en la misma oración.
    - Soporta integración opcional con `openwakeword` para escucha de bajo consumo.
    """

    def __init__(self, wake_words: Iterable[str], enabled: bool = True) -> None:
        self.enabled = enabled
        # Ordenamos de mayor a menor longitud para capturar primero "oye ultrón" antes que "ultrón"
        self.wake_words = sorted(
            {w.strip().lower() for w in wake_words if w.strip()},
            key=len,
            reverse=True,
        )

    def check_transcript(self, text: str) -> WakeWordMatch:
        """
        Verifica si el texto contiene la palabra de activación y separa el comando restante.
        Si `enabled` es False, siempre retorna `triggered=True` con el texto completo.
        """
        cleaned = text.strip()
        if not self.enabled:
            return WakeWordMatch(triggered=True, wake_word=None, remaining_command=cleaned)

        lowered = cleaned.lower()
        for ww in self.wake_words:
            pattern = rf"^\s*(?:{re.escape(ww)})\b[\s,.:;!?-]*(.*)$"
            match = re.match(pattern, lowered, flags=re.IGNORECASE)
            if match:
                remainder = match.group(1).strip()
                return WakeWordMatch(
                    triggered=True,
                    wake_word=ww,
                    remaining_command=remainder,
                )

        return WakeWordMatch(triggered=False, wake_word=None, remaining_command="")
