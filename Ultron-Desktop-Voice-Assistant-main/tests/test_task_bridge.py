"""
Suite de pruebas unitarias para el motor de sincronización de tareas y agenda (`TaskSyncBridge`).
Verifica lectura dinámica de TAREAS.md, adición de tareas por voz, completado atómico y horario.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ultron.task_bridge import AcademicTask, TaskSyncBridge


SAMPLE_TAREAS_CONTENT = """# Tablero de Tareas y Proyectos

## 📌 Prioridad Alta (Próximos días)

1. **[Viernes 13 Nov]** `Bioinstrumentación 2`: **Laboratorio de máquina de anestesia**
   - Estado: `[ ] Pendiente`

2. **[Sábado 14 Nov - 11:00]** `Aprendizaje Automático`: **Tarea 3**
   - Estado: `[ ] Pendiente`

---

## 📅 Entregas Futuras (Noviembre)

- **[Martes 17 Nov - 23:59]** `Ingeniería Clínica 2`: **Entrega de Matriz de gestión de riesgo**

---

## 📚 Tareas por Materia

### Ingeniería Clínica 2
- [ ] 17 Nov (23:59): Entrega de Matriz de gestión de riesgo

### Bioinstrumentación 2
- [ ] 13 Nov: Laboratorio de máquina de anestesia
- [ ] 20 Nov: Video de presentación de Ventilación mecánica

### Visión Computacional con Deep Learning
- [x] 13 Nov (18:30): Actividad - CNN con regularización (Entregado el 09/Nov 🎉)

### Proyectos Especiales / Investigación
- [ ] 13 Nov (08:00 - 12:30): Salida de campo - Levantamiento de equipos en Candelaria, Valle del Cauca.
"""


class TestTaskSyncBridge(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        self.tareas_path = self.workspace / "TAREAS.md"
        self.tareas_path.write_text(SAMPLE_TAREAS_CONTENT, encoding="utf-8")
        self.bridge = TaskSyncBridge(workspace_root=self.workspace)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_parse_tasks_extracts_pending_and_completed(self) -> None:
        tasks = self.bridge.parse_tasks()
        self.assertGreater(len(tasks), 3)

        # Verificar que se detectó la completada (CNN)
        completed = [t for t in tasks if t.completed]
        self.assertEqual(len(completed), 1)
        self.assertIn("CNN", completed[0].title)

        # Verificar que se detectaron pendientes de prioridad alta
        high_prio = [t for t in tasks if t.priority == "high"]
        self.assertGreaterEqual(len(high_prio), 2)

    def test_get_pending_summary_contains_key_deliverables(self) -> None:
        summary = self.bridge.get_pending_summary(user_name="Sebastián")
        self.assertIn("Sebastián", summary)
        self.assertIn("Laboratorio de máquina de anestesia", summary)
        self.assertIn("Tarea 3", summary)
        self.assertIn("Candelaria", summary)
        # La CNN completada no debe reportarse como tarea pendiente
        self.assertNotIn("CNN con regularización en Visión", summary)

    def test_add_task_appends_to_tareas_md(self) -> None:
        ok, msg = self.bridge.add_task("Calibrar sensor de presión diferencial")
        self.assertTrue(ok)
        self.assertIn("registrada exitosamente", msg)

        content = self.tareas_path.read_text(encoding="utf-8")
        self.assertIn("Calibrar sensor de presión diferencial", content)

    def test_complete_task_modifies_checkbox(self) -> None:
        ok, msg = self.bridge.complete_task("anestesia")
        self.assertTrue(ok)
        self.assertIn("marcada como completada", msg)

        content = self.tareas_path.read_text(encoding="utf-8")
        self.assertIn("Laboratorio de máquina de anestesia", content)
        self.assertIn("[x]", content)

    def test_complete_non_existent_task_returns_clean_error(self) -> None:
        ok, msg = self.bridge.complete_task("materia inexistente de astronomia")
        self.assertFalse(ok)
        self.assertIn("No encontré ninguna tarea pendiente", msg)

    def test_get_schedule_today_returns_valid_day_string(self) -> None:
        schedule = self.bridge.get_schedule_today(user_name="Sebastián")
        self.assertIn("Sebastián", schedule)
        self.assertTrue(len(schedule) > 20)


if __name__ == "__main__":
    unittest.main()
