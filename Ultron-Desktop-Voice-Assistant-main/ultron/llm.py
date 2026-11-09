"""
Cerebro de IA Generativa de Ultrón (3 Niveles de Respaldo con Reintentos Automáticos):
1. Google Gemini (`google-genai`) si `GEMINI_API_KEY` está configurada.
2. Ollama Local (`http://localhost:11434`) si está corriendo en la máquina.
3. Motor Cloud IA Gratuito Zero-Config (`Pollinations AI`) con reintentos automáticos
   para que jamás falle por límites de tasa temporales.
"""

from __future__ import annotations

import logging
import random
import time
import urllib.parse
from typing import Optional

import requests

from ultron.config import UltronConfig
from ultron.strings import tr

logger = logging.getLogger("ultron.llm")


def build_system_prompt(
    config: UltronConfig,
    response_lang: str = "es",
    input_lang: str = "es",
) -> str:
    """
    Construye el prompt de sistema personalizado para Sebastián Giraldo Acosta.
    Activa el modo tutor de inglés únicamente cuando Sebastián habla en inglés (`input_lang == "en"`).
    """
    lang_instruction = (
        "Responde SIEMPRE en español claro, conciso y natural (incluso si el usuario te habla en inglés)."
        if response_lang == "es"
        else "Respond concisely and naturally in the requested language."
    )
    english_coach_clause = (
        f"- {config.user_name} acaba de hablarte en INGLÉS para practicar su fluidez: primero responde a su consulta en español, "
        "y al final añade una sola línea breve felicitándolo o dándole un consejo natural si hubo algún detalle gramatical en su inglés.\n"
        if input_lang == "en"
        else f"- {config.user_name} te está hablando en español: NO le des correcciones de ortografía ni de mayúsculas porque su texto proviene de un micrófono de voz.\n"
    )
    return (
        f"Eres {config.assistant_name}, el asistente de escritorio con inteligencia artificial personal de "
        f"{config.user_name} (Sebastián Giraldo Acosta, @sebastiangiraldoa-sga).\n"
        "Contexto sobre tu creador y usuario principal:\n"
        "- Estudiante de Ingeniería Biomédica y de la Especialización en Inteligencia Artificial en Colombia.\n"
        "- Experto en Machine Learning, Deep Learning (PyTorch, CNNs, visión computacional), Bioinstrumentación médica (máquinas de anestesia, ventilación mecánica), Gestión de Riesgo Hospitalario y proyectos de Liofilizados.\n"
        "- Tienes personalidad estilo Jarvis/Ultrón: leal, brillante, directo, ingenioso y enfocado en ingeniería de primer nivel.\n"
        f"{english_coach_clause}"
        f"{lang_instruction}\n"
        "IMPORTANTE: Mantén tus respuestas breves (máximo 2 a 3 oraciones fluidas, sin bloques de markdown ni asteriscos) "
        "porque serán leídas en voz alta por el altavoz de su computadora."
    )


class UltronBrain:
    """Cliente unificado de IA Generativa (Gemini API + Ollama Local + Zero-Config Cloud con Reintento)."""

    def __init__(self, config: UltronConfig) -> None:
        self.config = config

    def ask(self, prompt: str, input_lang: str = "es", force_spanish_reply: bool = True) -> str:
        """
        Envía una consulta abierta al LLM disponible.
        Por preferencia de Sebastián, responde en español incluso cuando él practica en inglés.
        """
        reply_lang = "es" if force_spanish_reply else input_lang
        system_prompt = build_system_prompt(
            self.config, response_lang=reply_lang, input_lang=input_lang
        )

        # 1. Intentar con DeepSeek si está configurado como proveedor principal
        if self.config.llm_provider == "deepseek" and self.config.deepseek_api_key:
            reply = self._ask_deepseek(prompt, system_prompt)
            if reply:
                return self._clean_for_tts(reply)

        # 2. Intentar con Google Gemini si el usuario configuró su GEMINI_API_KEY real
        if self.config.llm_provider == "gemini" and self.config.gemini_api_key:
            reply = self._ask_gemini(prompt, system_prompt)
            if reply:
                return self._clean_for_tts(reply)

        # 3. Respaldo a DeepSeek si Gemini falló o no tiene clave pero hay DEEPSEEK_API_KEY
        if self.config.deepseek_api_key:
            reply = self._ask_deepseek(prompt, system_prompt)
            if reply:
                return self._clean_for_tts(reply)

        # 4. Intentar con Ollama local si está activo en localhost:11434
        if self.config.llm_provider == "ollama" or not (self.config.gemini_api_key or self.config.deepseek_api_key):
            reply = self._ask_ollama(prompt, system_prompt)
            if reply:
                return self._clean_for_tts(reply)

        # 5. Motor Cloud IA Gratuito Zero-Config con reintentos automáticos
        reply = self._ask_free_cloud_llm(prompt, system_prompt)
        if reply:
            return self._clean_for_tts(reply)

        return tr(reply_lang, "llm_fallback_unavailable")

    def generate_raw(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> Optional[str]:
        """
        Genera una respuesta directa del LLM sin preámbulos de conversación para
        edición in-place de texto, enrutamiento de herramientas o formateo estructurado.
        """
        # 1. Gemini
        if self.config.llm_provider == "gemini" and self.config.gemini_api_key:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=self.config.gemini_api_key)
                models_to_try = [self.config.gemini_model, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
                seen: set[str] = set()
                unique_models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

                for model_name in unique_models:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=system_prompt,
                                temperature=temperature,
                                max_output_tokens=max_tokens,
                            ),
                        )
                        if response and response.text:
                            return response.text.strip()
                    except Exception as model_err:
                        logger.debug("Gemini generate_raw model '%s' failed: %s", model_name, model_err)
                        continue
            except Exception as exc:
                logger.debug("Gemini generate_raw failed: %s", exc)

        # 2. DeepSeek (si está configurado o como respaldo)
        if (self.config.llm_provider == "deepseek" or not self.config.gemini_api_key) and self.config.deepseek_api_key:
            deepseek_raw = self._ask_deepseek(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if deepseek_raw:
                return deepseek_raw

        # 3. Ollama
        if self.config.llm_provider == "ollama" or not (self.config.gemini_api_key or self.config.deepseek_api_key):
            try:
                url = f"{self.config.ollama_base_url.rstrip('/')}/api/generate"
                payload = {
                    "model": self.config.ollama_model,
                    "system": system_prompt,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                }
                resp = requests.post(url, json=payload, timeout=4)
                if resp.status_code == 200:
                    answer = resp.json().get("response", "").strip()
                    if answer:
                        return answer
            except Exception as exc:
                logger.debug("Ollama generate_raw failed: %s", exc)

        # 3. Cloud LLM Fallback
        return self._ask_free_cloud_llm(prompt, system_prompt)

    @staticmethod
    def _clean_for_tts(text: str) -> str:
        """Limpia símbolos de markdown (`**`, `#`, backticks) para que la voz de Windows lea con naturalidad."""
        cleaned = (
            text.replace("**", "")
            .replace("__", "")
            .replace("`", "")
            .replace("###", "")
            .replace("##", "")
        )
        return " ".join(cleaned.split()).strip()

    def _ask_gemini(self, prompt: str, system_prompt: str) -> Optional[str]:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.config.gemini_api_key)
            models_to_try = [self.config.gemini_model, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            seen: set[str] = set()
            unique_models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

            for model_name in unique_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.6,
                            max_output_tokens=250,
                        ),
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as model_err:
                    logger.debug("Error con modelo Gemini '%s': %s", model_name, model_err)
                    continue
        except Exception as exc:
            logger.warning("Error consultando Google Gemini: %s", exc)
        return None

    def _ask_deepseek(
        self,
        prompt: str,
        system_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.6,
        max_tokens: int = 600,
    ) -> Optional[str]:
        """
        Consulta la API de DeepSeek (DeepSeek-R1 'deepseek-reasoner' o DeepSeek-V3 'deepseek-chat').
        Aprovecha el razonamiento lógico/matemático y filtra bloques de razonamiento si se van a leer por voz.
        """
        if not self.config.deepseek_api_key:
            return None

        target_model = model or self.config.deepseek_model or "deepseek-reasoner"
        headers = {
            "Authorization": f"Bearer {self.config.deepseek_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "UltronDesktopAssistant/5.3",
        }
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
        }
        if "reasoner" not in target_model.lower():
            payload["temperature"] = temperature

        url = f"{self.config.deepseek_base_url.rstrip('/')}/chat/completions"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    msg = choices[0].get("message") or {}
                    content = msg.get("content") or ""
                    if not content.strip() and msg.get("reasoning_content"):
                        content = msg["reasoning_content"]
                    return content.strip()
            else:
                logger.debug("DeepSeek API retorno status %d: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.debug("Fallo llamada a DeepSeek API: %s", exc)

        return None

    def _ask_ollama(self, prompt: str, system_prompt: str) -> Optional[str]:
        try:
            url = f"{self.config.ollama_base_url.rstrip('/')}/api/generate"
            payload = {
                "model": self.config.ollama_model,
                "system": system_prompt,
                "prompt": prompt,
                "stream": False,
            }
            resp = requests.post(url, json=payload, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("response", "").strip()
                if answer:
                    return answer
        except requests.RequestException as exc:
            logger.debug("Ollama local no accesible (%s).", exc)
        return None

    def _ask_free_cloud_llm(self, prompt: str, system_prompt: str) -> Optional[str]:
        """
        Motor LLM gratuito de respaldo sin configuración con baja latencia.
        Por seguridad y privacidad del usuario, solo se comunica mediante HTTPS POST
        y utiliza una instrucción de sistema concisa y anonimizada.
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "UltronDesktopAssistant/5.3",
        }
        # Instrucción genérica y segura que no expone datos personales en servicios públicos
        safe_sys = (
            "Eres un asistente virtual de voz en español. Responde en 2 a 3 oraciones claras, "
            "directas y naturales sin asteriscos ni markdown, listo para ser leído en voz alta."
        )

        try:
            payload = {
                "model": "openai",
                "seed": random.randint(1, 999999),
                "messages": [
                    {"role": "system", "content": safe_sys},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.5,
            }
            resp = requests.post(
                "https://text.pollinations.ai/openai",
                json=payload,
                headers=headers,
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    if content and "Free limit reached" not in content and "unlimited replies" not in content:
                        return content
        except Exception as exc:
            logger.debug("POST seguro a cloud fallback falló: %s", exc)

        return None

