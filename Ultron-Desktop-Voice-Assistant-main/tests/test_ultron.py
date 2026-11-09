"""
Suite de pruebas unitarias e integración para validar los 6 pilares de Ultrón v3.0:
1. Configuración y personalización para Sebastián Giraldo Acosta.
2. Detección de Wake-Word ("Ultrón" / "Hey Ultrón").
3. Detección inteligente de idioma (Inglés de entrada -> Español de respuesta).
4. Habilidades restauradas (notas JSON, chistes, renombrado, fecha/hora).
5. Telemetría del sistema en tiempo real y detección de procesos pesados por voz.
6. Visión Multimodal de Escritorio integrada en el asistente.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ultron.assistant import UltronAssistant
from ultron.config import UltronConfig
from ultron.strings import detect_language
from ultron.wakeword import WakeWordDetector


class TestUltronAssistant(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        base = Path(self.tmp_dir.name)
        self.config = UltronConfig(
            assistant_name="Ultrón",
            user_name="Sebastián",
            name_file=base / "assistant_name.txt",
            notes_file=base / "notes.json",
            screenshots_dir=base / "screenshots",
        )
        self.assistant = UltronAssistant(
            config=self.config,
            text_mode=True,
            mute=True,
            force_spanish_reply=True,
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_wake_word_detection_and_command_extraction(self) -> None:
        detector = WakeWordDetector(
            wake_words=["ultron", "ultrón", "hey ultron", "oye ultrón"],
            enabled=True,
        )
        m1 = detector.check_transcript("Hey Ultron, what time is it?")
        self.assertTrue(m1.triggered)
        self.assertEqual(m1.wake_word, "hey ultron")
        self.assertEqual(m1.remaining_command, "what time is it?")

        m2 = detector.check_transcript("Ultrón, abre mi portafolio")
        self.assertTrue(m2.triggered)
        self.assertEqual(m2.remaining_command, "abre mi portafolio")

        m3 = detector.check_transcript("what time is it?")
        self.assertFalse(m3.triggered)

    def test_language_detection_no_collision(self) -> None:
        self.assertEqual(detect_language("What time is it right now?"), "en")
        self.assertEqual(detect_language("¿Qué hora es en este momento?"), "es")
        self.assertEqual(detect_language("Quelle heure est-il ?"), "fr")

    def test_english_input_forces_spanish_reply(self) -> None:
        response = self.assistant.process_command("What time is it?")
        self.assertIn("La hora actual es", response)

    def test_notes_save_and_list(self) -> None:
        save_resp = self.assistant.process_command("Take a note: Review NutriCoach Pro PR")
        self.assertIn("Nota guardada correctamente", save_resp)

        list_resp = self.assistant.process_command("Read my notes")
        self.assertIn("Tienes 1 notas registradas", list_resp)
        self.assertIn("review nutricoach pro pr", list_resp)

    def test_assistant_rename_persistence(self) -> None:
        resp = self.assistant.process_command("Change your name to Ultrón Prime")
        self.assertIn("Ultrón Prime", resp)
        self.assertEqual(self.config.load_assistant_name(), "Ultrón Prime")

    def test_tell_joke_restored(self) -> None:
        joke = self.assistant.process_command("Tell me a joke")
        self.assertTrue(len(joke) > 5)

    def test_system_telemetry_voice_routing(self) -> None:
        resp = self.assistant.process_command("How is my PC running?")
        self.assertIn("Diagnóstico de sistemas completado, Sebastián", resp)
        self.assertIn("CPU al", resp)
        self.assertIn("Memoria RAM al", resp)

    def test_top_processes_voice_routing(self) -> None:
        resp = self.assistant.process_command("What is eating my RAM?")
        self.assertIn("procesos con mayor consumo de memoria RAM, Sebastián", resp)

    def test_multimodal_vision_voice_routing(self) -> None:
        resp = self.assistant.process_command("Look at my screen and debug this error")
        self.assertTrue(len(resp) > 20)
        saved_pngs = list(self.config.screenshots_dir.glob("*.png"))
        self.assertGreaterEqual(len(saved_pngs), 1)

    def test_ultron_prefix_strip_and_spotify_launch(self) -> None:
        resp = self.assistant.process_command("ultron abre spotify")
        self.assertIn("Spotify", resp)

    def test_halcon_prefix_strip_and_bare_name(self) -> None:
        resp = self.assistant.process_command("halcón abre spotify")
        self.assertIn("Spotify", resp)
        bare_resp = self.assistant.process_command("halcón")
        self.assertIn("Te escucho fuerte y claro", bare_resp)

    def test_ultron_bare_name_acknowledgement(self) -> None:
        resp = self.assistant.process_command("ultron")
        self.assertIn("Te escucho fuerte y claro", resp)

    def test_compound_youtube_search(self) -> None:
        resp = self.assistant.process_command("abre youtube y busca música")
        self.assertIn("Buscando 'música' en YouTube", resp)

    def test_analiza_mi_sistema_routes_to_telemetry(self) -> None:
        resp = self.assistant.process_command("ultron analiza mi sistema")
        self.assertIn("Diagnóstico de sistemas completado, Sebastián", resp)

    def test_spaced_liofilizados_shortcut(self) -> None:
        resp = self.assistant.process_command("ultrón abrir liofilizados")
        self.assertIn("liofilizados", resp.lower())

    def test_spotify_artist_search_routing(self) -> None:
        resp = self.assistant.process_command("reproduce a ryan castro en spotify")
        self.assertIn("Buscando 'ryan castro' en Spotify", resp)

    def test_identity_question_instant_response(self) -> None:
        resp = self.assistant.process_command("okay qué eres tú")
        self.assertIn("asistente de escritorio con inteligencia artificial", resp)

    def test_phonetic_homophone_wake_word_stripping(self) -> None:
        # 'El trono mejor en texto copiado' should strip 'El trono' and route to clipboard editor
        with patch.object(self.assistant.skills.dictation, "edit_selected_or_clipboard_text") as mock_edit:
            from ultron.jarvis_pro import DictationResult
            mock_edit.return_value = DictationResult(
                original_text="hola",
                processed_text="Hola, ¿cómo estás?",
                mode="edit_selection",
                copied_to_clipboard=True,
                pasted_to_window=False,
                message="Texto transformado",
            )
            resp = self.assistant.process_command("El trono mejor en texto copiado.")
            self.assertIn("Texto transformado", resp)
            mock_edit.assert_called_once()

    def test_a_una_ultron_homophone_opening_spotify(self) -> None:
        resp = self.assistant.process_command("A una ultron abre spotify")
        self.assertIn("Spotify", resp)

    def test_compose_email_shortcut_routing(self) -> None:
        with patch("ultron.skills.wb.open") as mock_wb:
            resp = self.assistant.process_command("Quiero enviar un correo, me puedes ayudar.")
            self.assertIn("Gmail", resp)
            mock_wb.assert_called_once_with("https://mail.google.com/mail/u/0/#inbox?compose=new")

    def test_pid_controller_instant_explanation(self) -> None:
        resp = self.assistant.process_command("qué sabes del pid")
        self.assertIn("Proporcional-Integral-Derivativo", resp)
        self.assertIn("Bola-Viga", resp)

    def test_academic_tasks_voice_routing(self) -> None:
        resp = self.assistant.process_command("Ultrón, ¿cuáles son mis tareas?")
        self.assertIn("prioridades académicas pendientes", resp)
        self.assertIn("Bioinstrumentación 2", resp)
        self.assertIn("Aprendizaje Automático", resp)

    def test_academic_schedule_voice_routing(self) -> None:
        resp = self.assistant.process_command("Ultrón, ¿qué clases tengo hoy?")
        self.assertIn("Sebastián", resp)


    def test_spotify_direct_play_and_resume(self) -> None:
        with patch.object(self.assistant.skills, "_send_multimedia_key") as mock_key:
            resp = self.assistant.process_command("abre spotify y reproduce música")
            self.assertIn("Spotify", resp)
            self.assertIn("iniciando reproducción musical", resp.lower())

            resp2 = self.assistant.process_command("pon música")
            self.assertIn("Spotify", resp2)

    def test_multimedia_controls_pause_next_prev_volume(self) -> None:
        with patch.object(self.assistant.skills, "_send_multimedia_key") as mock_key:
            # Pausa
            resp_pause = self.assistant.process_command("pausa la música")
            self.assertIn("pausada", resp_pause.lower())

            # Siguiente
            resp_next = self.assistant.process_command("siguiente canción")
            self.assertIn("siguiente canción", resp_next.lower())

            # Anterior
            resp_prev = self.assistant.process_command("canción anterior")
            self.assertIn("anterior", resp_prev.lower())

            # Volumen
            resp_vol_up = self.assistant.process_command("sube el volumen")
            self.assertIn("volumen", resp_vol_up.lower())

    def test_deepseek_reasoner_llm_routing(self) -> None:
        self.assistant.config.llm_provider = "deepseek"
        self.assistant.config.deepseek_api_key = "test_sk_fake_key"
        self.assistant.config.gemini_api_key = ""

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Para sintonizar el PID de tu Bola-Viga, incrementa gradualmente Kp hasta ver oscilaciones estables.",
                        }
                    }
                ]
            }
            reply = self.assistant.brain.ask("cómo ajusto mi pid")
            self.assertIn("PID", reply)
            self.assertIn("Bola-Viga", reply)


if __name__ == "__main__":
    unittest.main()
