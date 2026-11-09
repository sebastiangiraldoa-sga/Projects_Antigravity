"""
Pruebas unitarias para el sistema de Visión Multimodal e Inteligencia de Pantalla de Ultrón (`ultron/vision.py`).
Verifica:
1. Auto-detección de modos (`debug`, `ux_audit`, `biomedical_pid`, `general`) en español e inglés.
2. Construcción de prompts especializados (`build_vision_prompt`).
3. Pipeline `capture_screen()` incluyendo el fallback sintético en entornos Linux headless (sin $DISPLAY).
4. `UltronVision.analyze_screen()` con mocks de Gemini Multimodal, Ollama (`llava`) y fallback local sin API Key.
"""

from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ultron.config import UltronConfig
from ultron.vision import (
    UltronVision,
    VisionAnalysisResult,
    VisionCapture,
    VisionMode,
    build_vision_prompt,
    capture_screen,
    detect_vision_mode,
)


class TestUltronVision(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.tmp_dir.name)
        self.config = UltronConfig(
            assistant_name="Ultrón",
            user_name="Sebastián",
            gemini_api_key="",
            gemini_model="gemini-2.0-flash",
            ollama_base_url="http://localhost:11434",
            screenshots_dir=self.base_path / "screenshots",
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_vision_mode_enum_values(self) -> None:
        self.assertEqual(VisionMode.GENERAL.value, "general")
        self.assertEqual(VisionMode.DEBUG.value, "debug")
        self.assertEqual(VisionMode.UX_AUDIT.value, "ux_audit")
        self.assertEqual(VisionMode.BIOMEDICAL_PID.value, "biomedical_pid")

    def test_mode_autodetection_spanish_and_english(self) -> None:
        # Modo debug (Español e Inglés)
        self.assertEqual(
            detect_vision_mode("Mira este error en la consola de mi código"),
            VisionMode.DEBUG.value,
        )
        self.assertEqual(
            detect_vision_mode("Can you help me fix this Python traceback exception in terminal?"),
            VisionMode.DEBUG.value,
        )

        # Modo ux_audit (Español e Inglés)
        self.assertEqual(
            detect_vision_mode("Audita el diseño e interfaz de esta página en Tailwind y CSS"),
            VisionMode.UX_AUDIT.value,
        )
        self.assertEqual(
            detect_vision_mode("Review the UX and UI layout of my Flutter mobile design"),
            VisionMode.UX_AUDIT.value,
        )

        # Modo biomedical_pid (Español e Inglés)
        self.assertEqual(
            detect_vision_mode("Analiza la gráfica del control PID en Arduino y dime el overshoot"),
            VisionMode.BIOMEDICAL_PID.value,
        )
        self.assertEqual(
            detect_vision_mode("Check this oscilloscope signal plot from the sensor"),
            VisionMode.BIOMEDICAL_PID.value,
        )

        # Modo general (Español e Inglés)
        self.assertEqual(
            detect_vision_mode("¿Qué hay en mi pantalla en este momento?"),
            VisionMode.GENERAL.value,
        )
        self.assertEqual(
            detect_vision_mode("What is currently visible on my desktop window?"),
            VisionMode.GENERAL.value,
        )

    def test_build_vision_prompt_auto_and_explicit_modes(self) -> None:
        # Auto-detección cuando mode="" o None
        debug_prompt = build_vision_prompt("", "Tengo un bug y un traceback en la terminal", lang="es")
        self.assertIn("DEBUG", debug_prompt)
        self.assertIn("español", debug_prompt.lower())

        ux_prompt = build_vision_prompt(None, "How can I improve this Figma UI layout?", lang="es")
        self.assertIn("UX_AUDIT", ux_prompt)

        pid_prompt = build_vision_prompt("biomedical_pid", "Analiza esta curva", lang="es")
        self.assertIn("BIOMEDICAL_PID", pid_prompt)
        self.assertIn("overshoot", pid_prompt.lower())

        general_prompt = build_vision_prompt("general", "Lee el texto del documento", lang="es")
        self.assertIn("GENERAL", general_prompt)

    def test_capture_screen_headless_synthetic_fallback(self) -> None:
        with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}, clear=False):
            capture = capture_screen(self.config)
            self.assertIsInstance(capture, VisionCapture)
            self.assertTrue(capture.is_synthetic_fallback)
            self.assertEqual(capture.width, 1280)
            self.assertEqual(capture.height, 720)
            self.assertTrue(capture.file_path.exists())
            self.assertTrue(capture.file_path.name.startswith("ultron_vision_"))
            self.assertTrue(capture.file_path.name.endswith(".png"))
            # Verificar firma mágica PNG (\x89PNG\r\n\x1a\n)
            self.assertEqual(capture.image_bytes[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(capture.file_path.read_bytes(), capture.image_bytes)

    def test_analyze_screen_with_mocked_gemini(self) -> None:
        self.config.gemini_api_key = "fake-gemini-key-for-testing"
        vision = UltronVision(self.config)

        # Construimos un mock limpio de `google.genai` y `google.genai.types`
        mock_google = types.ModuleType("google")
        mock_genai = types.ModuleType("google.genai")
        mock_genai_types = types.ModuleType("google.genai.types")

        mock_part_cls = MagicMock()
        mock_part_cls.from_bytes.return_value = "FAKE_IMAGE_PART"
        mock_genai_types.Part = mock_part_cls
        mock_genai_types.GenerateContentConfig = MagicMock()

        mock_response = MagicMock()
        mock_response.text = (
            "En la línea 42 de app.py tienes un ZeroDivisionError. "
            "Valida que el denominador sea distinto de cero antes de dividir."
        )
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client_cls = MagicMock(return_value=mock_client_instance)

        mock_genai.Client = mock_client_cls
        mock_genai.types = mock_genai_types
        mock_google.genai = mock_genai

        with patch.dict(
            sys.modules,
            {
                "google": mock_google,
                "google.genai": mock_genai,
                "google.genai.types": mock_genai_types,
            },
        ), patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}, clear=False):
            result = vision.analyze_screen(
                user_query="Why am I getting this traceback error in my terminal?"
            )

        self.assertIsInstance(result, VisionAnalysisResult)
        self.assertEqual(result.mode, VisionMode.DEBUG.value)
        self.assertEqual(result.provider_used, "gemini")
        self.assertIn("ZeroDivisionError", result.analysis)
        self.assertTrue(result.image_path.exists())
        self.assertGreaterEqual(result.latency_ms, 1)
        mock_part_cls.from_bytes.assert_called_once()

    @patch("ultron.vision.requests.post")
    def test_analyze_screen_with_mocked_ollama(self, mock_post: MagicMock) -> None:
        self.config.gemini_api_key = ""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "La curva PID muestra un overshoot del 18% y un tiempo de establecimiento de 1.4 segundos."
        }
        mock_post.return_value = mock_resp

        vision = UltronVision(self.config)
        with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}, clear=False):
            result = vision.analyze_screen(
                user_query="Analiza la gráfica del control PID en el osciloscopio"
            )

        self.assertEqual(result.mode, VisionMode.BIOMEDICAL_PID.value)
        self.assertEqual(result.provider_used, "ollama")
        self.assertIn("overshoot del 18%", result.analysis)
        self.assertTrue(result.image_path.exists())
        mock_post.assert_called_once()
        sent_json = mock_post.call_args.kwargs["json"]
        self.assertIn("images", sent_json)
        self.assertEqual(len(sent_json["images"]), 1)

    @patch("ultron.vision.requests.post", side_effect=Exception("Connection refused"))
    def test_analyze_screen_local_fallback_when_no_vlm_available(
        self, _mock_post: MagicMock
    ) -> None:
        self.config.gemini_api_key = ""
        vision = UltronVision(self.config)

        with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}, clear=False):
            result = vision.analyze_screen(
                user_query="Revisa el diseño UX de mi interfaz en Tailwind"
            )

        self.assertIsInstance(result, VisionAnalysisResult)
        self.assertEqual(result.mode, VisionMode.UX_AUDIT.value)
        self.assertEqual(result.provider_used, "local_fallback")
        self.assertIn("1280x720", result.analysis)
        self.assertIn("GEMINI_API_KEY", result.analysis)
        self.assertIn("ollama run llava", result.analysis)
        self.assertTrue(result.image_path.exists())

    def test_analyze_screen_with_existing_image_path(self) -> None:
        custom_img_path = self.base_path / "custom_test.png"
        capture = capture_screen(self.config, output_path=custom_img_path)
        self.assertEqual(capture.file_path, custom_img_path)

        vision = UltronVision(self.config)
        with patch("ultron.vision.requests.post", side_effect=Exception("Offline")):
            result = vision.analyze_screen(
                user_query="¿Qué hay en mi pantalla?",
                mode="general",
                image_path=custom_img_path,
            )
        self.assertEqual(result.image_path, custom_img_path)
        self.assertEqual(result.mode, VisionMode.GENERAL.value)
        self.assertEqual(result.provider_used, "local_fallback")


if __name__ == "__main__":
    unittest.main()
