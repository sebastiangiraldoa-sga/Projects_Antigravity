"""
Suite de pruebas unitarias e integración para el Stark HUD v4.0 (`ultron/hud_server.py` y `ultron/tts.py`).
Valida contra un `ThreadingHTTPServer` en vivo (puerto efímero `port=0`):
1. `GET  /api/status`    -> Metadatos del núcleo, versión 4.0.0 y estado de backends IA.
2. `GET  /api/telemetry` -> Métricas de CPU, RAM, Disco, Batería, Red y `status` general.
3. `POST /api/command`   -> Procesamiento de órdenes en tiempo real, respuestas en español y señal de salida (`EXIT`).
4. `POST /api/vision`    -> Captura de pantalla en Base64 (`data:image/png;base64,...`) y análisis multimodal.
5. `GET  /api/tts`       -> Síntesis de audio Neural MP3 (`audio/mpeg`) y fallback 204 offline.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch

from ultron.assistant import UltronAssistant
from ultron.config import UltronConfig
from ultron.hud_server import create_hud_server
from ultron.tts import UltronTTS


class TestStarkHUDServer(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        base = Path(self.tmp_dir.name)
        self.config = UltronConfig(
            assistant_name="Ultrón",
            user_name="Sebastián",
            gemini_api_key="",
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
        self.server = create_hud_server(assistant=self.assistant, host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2)
        self.tmp_dir.cleanup()

    def _get_json(self, path: str) -> dict:
        req = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            return json.loads(resp.read().decode("utf-8"))

    def _post_json(self, path: str, payload: dict) -> dict:
        raw = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=raw,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            self.assertEqual(resp.status, 200)
            return json.loads(resp.read().decode("utf-8"))

    def test_static_hud_assets_served(self) -> None:
        for route, expected_mime, expected_token in (
            ("/", "text/html", "ULTRÓN"),
            ("/styles.css", "text/css", "--bg-obsidian"),
            ("/app.js", "application/javascript", "SILENCE_DEBOUNCE_MS"),
        ):
            req = urllib.request.Request(f"{self.base_url}{route}", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn(expected_mime, resp.headers.get("Content-Type", ""))
                body = resp.read().decode("utf-8")
                self.assertIn(expected_token, body)

    def test_api_status_returns_v4_metadata(self) -> None:
        data = self._get_json("/api/status")
        self.assertTrue(data["ok"])
        self.assertEqual(data["assistant_name"], "Ultrón")
        self.assertEqual(data["user_name"], "Sebastián")
        self.assertEqual(data["version"], "5.2.0")
        self.assertIn("Stark HUD", data["architecture"])
        self.assertTrue(data["llm_backends"]["cloud_fallback_ready"])

    def test_api_telemetry_returns_live_metrics(self) -> None:
        data = self._get_json("/api/telemetry")
        self.assertTrue(data["ok"])
        self.assertIn(data["status"], ("OPTIMAL", "ELEVATED", "CRITICAL"))
        self.assertIn("cpu", data)
        self.assertIn("memory", data)
        self.assertIn("disk", data)
        self.assertIn("top_processes", data)
        self.assertGreaterEqual(data["cpu"]["core_count_logical"], 1)

    def test_api_command_processes_queries_and_exit(self) -> None:
        res1 = self._post_json("/api/command", {"text": "What time is it?", "lang": "es", "speak_on_server": False})
        self.assertTrue(res1["ok"])
        self.assertEqual(res1["detected_lang"], "en")
        self.assertIn("La hora actual es", res1["reply"])
        self.assertFalse(res1["should_exit"])

        res_exit = self._post_json("/api/command", {"text": "salir", "lang": "es", "speak_on_server": False})
        self.assertTrue(res_exit["ok"])
        self.assertTrue(res_exit["should_exit"])
        self.assertIn("Sebastián", res_exit["reply"])

    def test_api_vision_captures_png_and_analyzes(self) -> None:
        with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}, clear=False), patch(
            "ultron.vision.requests.post", side_effect=Exception("Offline")
        ):
            res = self._post_json("/api/vision", {"query": "Analiza la gráfica del control PID", "mode": "biomedical_pid"})
        self.assertTrue(res["ok"])
        self.assertEqual(res["mode"], "biomedical_pid")
        self.assertTrue(res["image_data_url"].startswith("data:image/png;base64,"))
        self.assertTrue(len(res["analysis"]) > 20)
        self.assertGreaterEqual(res["latency_ms"], 1)

    def test_api_tts_returns_mp3_or_204(self) -> None:
        fake_mp3 = b"ID3\x04\x00\x00\x00\x00\x00\x00FAKE_NEURAL_MP3_STREAM"
        with patch.object(self.assistant.tts, "synthesize_neural_mp3", return_value=fake_mp3):
            url = f"{self.base_url}/api/tts?text={urllib.parse.quote('Hola Sebastián')}&lang=es"
            with urllib.request.urlopen(url, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.headers.get("Content-Type"), "audio/mpeg")
                self.assertEqual(resp.read(), fake_mp3)

        with patch.object(self.assistant.tts, "synthesize_neural_mp3", return_value=None):
            url = f"{self.base_url}/api/tts?text={urllib.parse.quote('Sin conexion')}&lang=es"
            with urllib.request.urlopen(url, timeout=5) as resp:
                self.assertEqual(resp.status, 204)

    def test_neural_tts_chunk_splitting_and_markdown_cleanup(self) -> None:
        tts = UltronTTS(mute=True)
        long_text = (
            "**Diagnóstico completado**, `Sebastián`. "
            "El procesador opera con total estabilidad térmica y las señales del osciloscopio están limpias. "
            "Todos los subsistemas responden dentro de los parámetros nominales de diseño."
        )
        chunks = tts._split_tts_chunks(long_text, max_len=100)
        self.assertGreaterEqual(len(chunks), 2)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 100)

    def test_jarvis_pro_smart_dictation_and_api_dictate(self) -> None:
        res = self._post_json(
            "/api/dictate",
            {
                "text": "eh revisa el archivo readme punto md a las 4pm no perdón a las 3pm",
                "mode": "dictate",
                "auto_paste": False,
            },
        )
        self.assertTrue(res["ok"])
        self.assertIn("readme.md", res["output_text"])
        self.assertIn("3pm", res["output_text"])
        self.assertNotIn("4pm", res["output_text"])

    def test_jarvis_pro_file_organizer_and_api_organize(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "informe.pdf").write_text("PDF dummy", encoding="utf-8")
            (tmp_path / "diagrama.png").write_bytes(b"\x89PNG\r\n")
            (tmp_path / "control_pid.py").write_text("print('pid')", encoding="utf-8")
            (tmp_path / "setup.zip").write_bytes(b"PK\x03\x04")

            res = self._post_json("/api/organize", {"target": str(tmp_path), "dry_run": False})
            self.assertTrue(res["ok"])
            self.assertEqual(res["total_moved"], 4)
            self.assertTrue((tmp_path / "Documentos" / "informe.pdf").exists())
            self.assertTrue((tmp_path / "Imagenes" / "diagrama.png").exists())
            self.assertTrue((tmp_path / "Codigo_Scripts" / "control_pid.py").exists())
            self.assertTrue((tmp_path / "Instaladores_Zip" / "setup.zip").exists())


if __name__ == "__main__":
    unittest.main()

