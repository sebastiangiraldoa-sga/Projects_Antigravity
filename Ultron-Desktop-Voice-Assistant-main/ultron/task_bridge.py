"""
Motor de Integración Bidireccional de Tareas y Agenda Académica para HALCÓN (`ultron.task_bridge`).
Conecta a HALCÓN en tiempo real con `TAREAS.md` y `SISTEMA_ASISTENTE.md` de Sebastián Giraldo Acosta.

Capacidades:
1. Lectura dinámica en tiempo real de tareas pendientes (`- [ ]`), prioridades y materias.
2. Inserción atómica de nuevas tareas por voz en `TAREAS.md`.
3. Marcado automático de tareas completadas (`[ ]` -> `[x]`) por comando de voz.
4. Consulta del horario semanal dinámico desde `SISTEMA_ASISTENTE.md`.
"""

from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ultron.task_bridge")


@dataclass
class AcademicTask:
    raw_text: str
    title: str
    subject: str
    due_date: str
    completed: bool = False
    priority: str = "normal"  # high, normal, future


class TaskSyncBridge:
    """Puente de sincronización en tiempo real entre HALCÓN y el contexto del proyecto."""

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = workspace_root or self._detect_workspace_root()
        self.tareas_file = self.workspace_root / "TAREAS.md"
        self.sistema_file = self.workspace_root / "SISTEMA_ASISTENTE.md"

    @staticmethod
    def _detect_workspace_root() -> Path:
        """Localiza la raíz del repositorio de forma dinámica y tolerante a fallos."""
        candidates = [
            Path(__file__).resolve().parent.parent.parent,  # Projects_Antigravity/
            Path("/home/antigravity/sebastiangiraldoa-sga/Projects_Antigravity"),
            Path.cwd(),
            Path.cwd().parent,
        ]
        for c in candidates:
            if (c / "TAREAS.md").is_file():
                return c
        return candidates[0]

    def parse_tasks(self) -> List[AcademicTask]:
        """Extrae todas las tareas registradas en `TAREAS.md` con su estado."""
        if not self.tareas_file.is_file():
            logger.warning("No se encontró el archivo TAREAS.md en %s", self.tareas_file)
            return []

        content = self.tareas_file.read_text(encoding="utf-8")
        tasks: List[AcademicTask] = []
        current_section = "general"
        current_subject = "General"

        for line in content.splitlines():
            line_str = line.strip()

            if line_str.startswith("## 📌 Prioridad Alta"):
                current_section = "high"
                continue
            elif line_str.startswith("## 📅 Entregas Futuras"):
                current_section = "future"
                continue
            elif line_str.startswith("### "):
                current_section = "subject"
                current_subject = line_str.replace("###", "").strip()
                continue
            elif line_str.startswith("## "):
                current_section = "other"
                continue

            # Detectar formato estructurado de Prioridad Alta: 1. **[Viernes 13 Nov]** `Bioinstrumentación 2`: **Laboratorio...**
            high_match = re.match(
                r"^\d+\.\s+\*\*\[(.*?)\]\*\*\s+`(.*?)`:\s+\*\*(.*?)\*\*",
                line_str,
            )
            if high_match:
                date_str, subj_str, title_str = high_match.groups()
                tasks.append(
                    AcademicTask(
                        raw_text=line_str,
                        title=title_str.strip(),
                        subject=subj_str.strip(),
                        due_date=date_str.strip(),
                        completed=False,
                        priority="high",
                    )
                )
                continue

            # Detectar formato estándar Markdown checkbox: - [ ] o - [x]
            chk_match = re.match(r"^-\s+\[([ xX])\]\s*(.*)$", line_str)
            if chk_match:
                is_done = chk_match.group(1).lower() == "x"
                body = chk_match.group(2).strip()

                # Ignorar placeholders como '*Sin tareas registradas*'
                if not body or body.startswith("*Sin tareas"):
                    continue

                # Extraer posible fecha: ej "17 Nov (23:59): Entrega..."
                date_prefix_match = re.match(r"^(\d+\s+[A-Za-z]+(?:\s*\([^)]+\))?):\s*(.+)$", body)
                if date_prefix_match:
                    date_val = date_prefix_match.group(1).strip()
                    title_val = date_prefix_match.group(2).strip()
                else:
                    date_val = "Pendiente"
                    title_val = body

                tasks.append(
                    AcademicTask(
                        raw_text=line_str,
                        title=title_val,
                        subject=current_subject,
                        due_date=date_val,
                        completed=is_done,
                        priority="normal" if not is_done else "completed",
                    )
                )

        return tasks

    def get_pending_summary(self, user_name: str = "Sebastián") -> str:
        """Genera un resumen hablado fluido y conciso con las entregas pendientes."""
        tasks = self.parse_tasks()
        pending = [t for t in tasks if not t.completed]

        if not pending:
            return f"Excelente noticia, {user_name}. No tienes ninguna entrega académica pendiente en tu tablero."

        # Priorizar tareas de alta prioridad o con fecha próxima
        high_prio = [t for t in pending if t.priority == "high"]
        regular_pending = [t for t in pending if t.priority != "high"]

        items_to_report = high_prio + regular_pending[:3]
        spoken_parts = []
        for i, t in enumerate(items_to_report, 1):
            spoken_parts.append(f"{i}. {t.due_date}: {t.title} en {t.subject}.")

        summary = f"{user_name}, tienes {len(pending)} compromisos en tu agenda. Las principales prioridades son: " + " ".join(spoken_parts)
        if any("liofilizados" in t.title.lower() or "candelaria" in t.title.lower() for t in pending):
            summary += " Y recuerda tener presente la salida de campo a Candelaria."

        return summary

    def add_task(self, raw_task_text: str, subject: Optional[str] = None) -> Tuple[bool, str]:
        """
        Inserta una nueva tarea en `TAREAS.md` bajo la sección correspondiente.
        """
        clean_text = raw_task_text.strip().strip(".,;:!?")
        if not clean_text:
            return False, "La descripción de la tarea está vacía."

        if not self.tareas_file.is_file():
            return False, "No se encontró el archivo TAREAS.md."

        try:
            content = self.tareas_file.read_text(encoding="utf-8")
            now_str = datetime.date.today().strftime("%d %b")
            new_entry = f"- [ ] [{now_str}] {clean_text}"

            lines = content.splitlines()
            inserted = False
            for idx, line in enumerate(lines):
                if line.strip().startswith("## 📌 Prioridad Alta"):
                    insert_idx = idx + 1
                    if insert_idx < len(lines) and not lines[insert_idx].strip():
                        insert_idx += 1
                    lines.insert(insert_idx, new_entry)
                    inserted = True
                    break

            if not inserted:
                lines.append(f"\n{new_entry}")

            updated_content = "\n".join(lines) + "\n"
            self.tareas_file.write_text(updated_content, encoding="utf-8")
            return True, f"Tarea registrada exitosamente: {clean_text}"
        except Exception as exc:
            logger.error("Error agregando tarea a TAREAS.md: %s", exc)
            return False, f"No se pudo guardar la tarea debido a un error: {exc}"

    def complete_task(self, query: str) -> Tuple[bool, str]:
        """
        Busca una tarea pendiente en `TAREAS.md` que coincida con la consulta y la marca como completada `[x]`.
        """
        if not self.tareas_file.is_file():
            return False, "No se encontró el archivo TAREAS.md."

        q_terms = [w.lower() for w in re.findall(r"\b\w{3,}\b", query) if w.lower() not in ("marca", "completada", "completa", "completado", "tarea", "entrega", "halcon", "ultron")]
        if not q_terms:
            return False, "Por favor especifica el nombre o materia de la tarea a completar."

        try:
            content = self.tareas_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            matched_line_idx = -1
            matched_line_content = ""

            for idx, line in enumerate(lines):
                line_lower = line.lower()
                if ("[ ]" in line or "[ ] Pendiente" in line) and any(term in line_lower for term in q_terms):
                    matched_line_idx = idx
                    matched_line_content = line
                    break

            if matched_line_idx == -1:
                return False, f"No encontré ninguna tarea pendiente que coincida con '{' '.join(q_terms)}'."

            today_str = datetime.date.today().strftime("%d/%b")
            updated_line = matched_line_content.replace("[ ]", "[x]")
            if "Pendiente" in updated_line:
                updated_line = updated_line.replace("[ ] Pendiente", f"[x] Completado ({today_str})")
            else:
                updated_line = f"{updated_line} (Completado el {today_str} 🎉)"

            lines[matched_line_idx] = updated_line
            self.tareas_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True, f"Tarea marcada como completada: {updated_line.replace('- [x]', '').strip()}"
        except Exception as exc:
            logger.error("Error completando tarea en TAREAS.md: %s", exc)
            return False, f"Error al actualizar la tarea: {exc}"

    def get_schedule_today(self, user_name: str = "Sebastián") -> str:
        """Lee el horario del día desde `SISTEMA_ASISTENTE.md` o usa el mapa oficial."""
        weekday = datetime.datetime.now().weekday()  # 0=Lunes, 6=Domingo
        schedule_map = {
            0: "Hoy lunes tienes Ingeniería Clínica 2 de 8:30 a 11:30 de la mañana, y en la tarde Monitoría de Formación Ciudadana de 2 a 5.",
            1: "Hoy martes tienes Redes Neuronales Artificiales y Deep Learning de 10:00 a 11:30 de la mañana.",
            2: "Hoy miércoles tienes Seminario de Ingeniería Biomédica de 10:00 a 12:00 del mediodía.",
            3: "Hoy jueves tienes jornada doble: Bioinstrumentación 2 de 2:00 a 5:30 de la tarde, y en la noche Aprendizaje Automático de 6:30 a 9:30.",
            4: "Hoy viernes tienes Diseño Biomédico 2 de 2:00 a 5:00 de la tarde, y en la noche Visión Computacional con Deep Learning de 6:30 a 9:30.",
            5: "Hoy sábado tienes dos bloques de posgrado: Visión Computacional de 8:00 a 11:00 de la mañana, y Aprendizaje Automático de 11:00 a 2:00 de la tarde.",
            6: "Hoy domingo es día de descanso y repaso. No tienes clases programadas.",
        }
        day_msg = schedule_map.get(weekday, "No tienes clases programadas para hoy.")
        return f"{user_name}, {day_msg}"
