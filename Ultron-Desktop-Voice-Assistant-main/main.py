#!/usr/bin/env python3
"""
Punto de entrada principal de Ultrón v4.0 ("Stark HUD") - Asistente de Voz, Telemetría y Visión Multimodal
Personalizado para Sebastián Giraldo Acosta (@sebastiangiraldoa-sga).
"""

from __future__ import annotations

import argparse
import logging

from ultron.assistant import UltronAssistant
from ultron.config import UltronConfig
from ultron.hud_server import run_hud_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ultrón v4.0 (Stark HUD): Asistente de Voz de Escritorio con Interfaz Holográfica, "
            "Voz Neural, IA Generativa, Telemetría en Tiempo Real y Visión Multimodal."
        )
    )
    parser.add_argument(
        "--hud",
        action="store_true",
        help="Inicia la interfaz gráfica interactiva Stark HUD v4.0 en el navegador (modo recomendado).",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Fuerza el modo clásico por consola de texto/voz sin abrir la interfaz gráfica Stark HUD.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Puerto local para el servidor Stark HUD (por defecto: 8765).",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Dirección IP de enlace para Stark HUD (0.0.0.0 para acceso desde móvil/red local, o 127.0.0.1).",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Ejecuta Ultrón en modo interactivo por consola (sin requerir micrófono).",
    )
    parser.add_argument(
        "--no-wake",
        action="store_true",
        help="Desactiva la palabra de activación ('Ultrón') para procesar cada frase directamente.",
    )
    parser.add_argument(
        "--mute",
        action="store_true",
        help="Desactiva la síntesis de voz por altavoz (solo salida en pantalla).",
    )
    parser.add_argument(
        "--chatbot",
        action="store_true",
        help="Inicia HALCÓN exclusivamente en modo Chatbot (micrófono liberado y voz silenciada para reuniones/Spotify).",
    )
    parser.add_argument(
        "--command",
        type=str,
        default="",
        help="Ejecuta un único comando directo y termina.",
    )
    parser.add_argument(
        "--telemetry",
        action="store_true",
        help="Ejecuta un diagnóstico completo de hardware y procesos en tiempo real y termina.",
    )
    parser.add_argument(
        "--vision",
        type=str,
        default="",
        help="Captura la pantalla activa y la analiza con Visión Multimodal según tu consulta.",
    )
    parser.add_argument(
        "--vision-mode",
        type=str,
        default=None,
        choices=["general", "debug", "ux_audit", "biomedical_pid"],
        help="Modo especializado opcional para el análisis visual (--vision).",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    for noisy_logger in (
        "comtypes",
        "httpx",
        "httpx2",
        "httpcore",
        "httpcore2",
        "huggingface_hub",
        "urllib3",
        "faster_whisper",
        "google_genai",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

    args = parse_args()
    config = UltronConfig()

    if args.no_wake:
        config.wake_word_enabled = False

    is_mute = args.mute or args.chatbot
    assistant = UltronAssistant(
        config=config,
        text_mode=args.text or (args.chatbot and args.cli),
        mute=is_mute,
        force_spanish_reply=True,
    )

    if args.telemetry:
        assistant.skills.system_telemetry(lang="es")
        return

    if args.vision:
        assistant.skills.analyze_screen(query=args.vision, mode=args.vision_mode, lang="es")
        return

    if args.command:
        assistant.process_command(args.command)
        return

    # Stark HUD v4.0 es la experiencia interactiva predeterminada a menos que se pida --cli o --text
    use_hud = args.hud or not (args.cli or args.text)
    if use_hud:
        run_hud_server(
            assistant=assistant,
            host=args.host,
            port=args.port,
            open_browser=True,
            chatbot_mode=args.chatbot,
        )
        return

    assistant.run_forever()


if __name__ == "__main__":
    main()

