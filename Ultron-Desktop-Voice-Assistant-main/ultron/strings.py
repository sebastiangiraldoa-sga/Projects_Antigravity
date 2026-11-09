"""
Sistema de internacionalización (ES / EN / FR) y detección de idioma para Ultrón.
"""

from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "es": {
        "welcome": "¡Bienvenido de nuevo, {user}!",
        "morning": "Buenos días.",
        "afternoon": "Buenas tardes.",
        "evening": "Buenas noches.",
        "night": "Es tarde, pero sigo operativo.",
        "service": "{assistant} en línea y a tu servicio. ¿Qué vamos a construir o automatizar hoy?",
        "time": "La hora actual es {time}.",
        "date": "Hoy es {date}.",
        "screenshot": "Captura de pantalla guardada en {path}.",
        "listening": "Escuchando...",
        "recognizing": "Procesando audio...",
        "wake_waiting": "Esperando palabra de activación ('{wake_word}')...",
        "wake_detected": "Sí, {user}, te escucho.",
        "error_music": "No encontré el directorio de Música en tu sistema.",
        "playing": "Reproduciendo {song}.",
        "no_song": "No encontré ninguna canción que coincida.",
        "ask_name": "¿Qué nuevo nombre deseas asignarme?",
        "name_set": "Entendido. A partir de ahora responderé al nombre de {name}.",
        "wiki_search": "Consultando Wikipedia...",
        "no_result": "No encontré resultados precisos en Wikipedia.",
        "note_asked": "¿Qué deseas que anote?",
        "note_saved": "Nota guardada correctamente: {note}",
        "notes_empty": "Aún no tienes notas guardadas.",
        "notes_header": "Tienes {count} notas registradas:",
        "opening_site": "Abriendo {site} en tu navegador.",
        "shutdown": "Iniciando secuencia de apagado del sistema. ¡Hasta pronto, {user}!",
        "restart": "Reiniciando el sistema.",
        "offline": "Pasando a modo desconectado. ¡Excelente sesión de código, {user}!",
        "llm_fallback_unavailable": (
            "No tengo conexión con el motor generativo en este momento, "
            "pero puedo ejecutar comandos locales (hora, fecha, notas, proyectos, Wikipedia o música)."
        ),
    },
    "en": {
        "welcome": "Welcome back, {user}!",
        "morning": "Good morning.",
        "afternoon": "Good afternoon.",
        "evening": "Good evening.",
        "night": "Working late tonight, I see.",
        "service": "{assistant} online and at your service. What are we building or automating today?",
        "time": "The current time is {time}.",
        "date": "Today's date is {date}.",
        "screenshot": "Screenshot saved at {path}.",
        "listening": "Listening...",
        "recognizing": "Processing speech...",
        "wake_waiting": "Waiting for wake word ('{wake_word}')...",
        "wake_detected": "Yes, {user}, I'm listening.",
        "error_music": "Music directory not found on your system.",
        "playing": "Playing {song}.",
        "no_song": "No matching song found.",
        "ask_name": "What would you like to name me?",
        "name_set": "Understood. I will respond to {name} from now on.",
        "wiki_search": "Searching Wikipedia...",
        "no_result": "I couldn't find anything matching that on Wikipedia.",
        "note_asked": "What would you like me to write down?",
        "note_saved": "Note saved successfully: {note}",
        "notes_empty": "You don't have any saved notes yet.",
        "notes_header": "You have {count} saved notes:",
        "opening_site": "Opening {site} in your browser.",
        "shutdown": "Initiating system shutdown. See you soon, {user}!",
        "restart": "Restarting the system.",
        "offline": "Going offline. Great coding session, {user}!",
        "llm_fallback_unavailable": (
            "Generative AI engine is currently unconfigured, "
            "but I can run local commands (time, date, notes, projects, Wikipedia, or music)."
        ),
    },
    "fr": {
        "welcome": "Bon retour, {user} !",
        "morning": "Bon matin.",
        "afternoon": "Bon après-midi.",
        "evening": "Bonsoir.",
        "night": "Bonne nuit.",
        "service": "{assistant} en ligne et à votre service. Comment puis-je vous aider ?",
        "time": "L'heure actuelle est {time}.",
        "date": "La date d'aujourd'hui est le {date}.",
        "screenshot": "Capture d'écran sauvegardée sous {path}.",
        "listening": "À l'écoute...",
        "recognizing": "Reconnaissance...",
        "wake_waiting": "En attente du mot d'activation ('{wake_word}')...",
        "wake_detected": "Oui, {user}, je vous écoute.",
        "error_music": "Répertoire Musique introuvable.",
        "playing": "Lecture de {song}.",
        "no_song": "Aucun morceau trouvé.",
        "ask_name": "Comment souhaitez-vous m'appeler ?",
        "name_set": "Très bien, je m'appellerai {name} à partir de maintenant.",
        "wiki_search": "Recherche sur Wikipédia...",
        "no_result": "Je n'ai rien trouvé sur Wikipédia.",
        "note_asked": "Que voulez-vous noter ?",
        "note_saved": "Note enregistrée : {note}",
        "notes_empty": "Vous n'avez aucune note enregistrée.",
        "notes_header": "Vous avez {count} notes :",
        "opening_site": "Ouverture de {site} dans le navigateur.",
        "shutdown": "Extinction du système !",
        "restart": "Redémarrage du système !",
        "offline": "Passage en mode hors ligne. Bonne journée, {user} !",
        "llm_fallback_unavailable": "Moteur IA non configuré pour le moment.",
    },
}

SPANISH_KEYWORDS = {
    "hora", "fecha", "qué", "que", "cómo", "como", "abre", "abrir",
    "reproduce", "música", "musica", "chiste", "nota", "notas",
    "apagar", "reiniciar", "captura", "busca", "buscar", "salir",
    "portafolio", "inventario", "cambiar", "nombre", "hola", "buenos",
}

FRENCH_KEYWORDS = {
    "heure", "musique", "ouvre", "extinction", "redémarrage",
    "capture", "blague", "bonjour", "bonsoir", "cherche",
}

ENGLISH_KEYWORDS = {
    "time", "what", "how", "open", "play", "music", "joke",
    "note", "notes", "shutdown", "restart", "screenshot",
    "search", "exit", "offline", "portfolio", "change", "name", "hello",
}


def detect_language(query: str, default_lang: str = "es") -> str:
    """
    Detecta el idioma de una consulta de texto basándose en marcadores léxicos,
    evitando la colisión de idiomas que ocurría en el repositorio original.
    """
    tokens = {
        t.strip("¿?¡!.,;:()\"'")
        for t in query.lower().split()
        if t.strip("¿?¡!.,;:()\"'")
    }
    es_score = len(tokens & SPANISH_KEYWORDS)
    en_score = len(tokens & ENGLISH_KEYWORDS)
    fr_score = len(tokens & FRENCH_KEYWORDS)

    if es_score == 0 and en_score == 0 and fr_score == 0:
        return default_lang if default_lang in STRINGS else "es"

    scores = {"es": es_score, "en": en_score, "fr": fr_score}
    return max(scores, key=lambda k: scores[k])


def tr(lang: str, key: str, **kwargs: object) -> str:
    """Obtiene una cadena traducida y formateada de forma segura."""
    lang_dict = STRINGS.get(lang, STRINGS["es"])
    template = lang_dict.get(key, STRINGS["es"].get(key, ""))
    return template.format(**kwargs)
