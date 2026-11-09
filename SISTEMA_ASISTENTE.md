# Sistema de Gestión Personal - Asistente & Sebastián

## Perfil Académico
- **Pregrado**: Ingeniería Biomédica
- **Posgrado**: Especialización en Inteligencia Artificial (IA)
- **Zona Horaria**: `America/Bogota` (UTC-5)
- **Estilo de Acompañamiento**: Cercano y motivador si se cumplen los objetivos; directo y exigente ante retrasos o incumplimientos.

---

## Horario Semanal de Clases

| Día | Horario | Asignatura | Programa |
|---|---|---|---|
| **Lunes** | 08:30 - 11:30 | Ingeniería Clínica 2 | Ing. Biomédica |
| **Lunes** | 14:00 - 17:00 | Monitoría de Formación Ciudadana | Docencia / Apoyo |
| **Martes** | 10:00 - 11:30 | Redes Neuronales Artificiales y Deep Learning | Ing. Biomédica |
| **Miércoles** | 10:00 - 12:00 | Seminario de Ingeniería Biomédica | Ing. Biomédica |
| **Jueves** | 14:00 - 17:30 | Bioinstrumentación 2 | Ing. Biomédica |
| **Jueves** | 18:30 - 21:30 | Aprendizaje Automático | Esp. en IA |
| **Viernes** | 14:00 - 17:00 | Diseño Biomédico 2 | Ing. Biomédica |
| **Viernes** | 18:30 - 21:30 | Visión Computacional con Deep Learning | Esp. en IA |
| **Sábado** | 08:00 - 11:00 | Visión Computacional con Deep Learning | Esp. en IA |
| **Sábado** | 11:00 - 14:00 | Aprendizaje Automático | Esp. en IA |

---

## Protocolo de Trabajo en Equipo
1. **Check-in Diario**: Al iniciar el día, revisamos clases del día, entregas críticas y bloques de estudio sugeridos.
2. **Control de Entregas & Tareas**: Cada tarea se clasifica con fecha límite, prioridad y estado (`[ ] Pendiente`, `[-] En curso`, `[x] Completado`).
3. **Métrica de Cumplimiento & Tono**:
   - **En verde (cumpliendo)**: Acompañamiento estratégico, tips de estudio, optimización y felicitaciones.
   - **En amarillo/rojo (rezago)**: Advertencias claras, eliminación de distracciones, planes de rescate y seguimiento estricto.

---

## Pipeline Automático de Clases y Grabaciones
- **Buzón en Google Drive**: Carpeta `Clases_Transcripciones` (ID: `1nf8koqAAbCYYPRcrA3FL110iizrh4Yir`).
  - `Vision_Computacional/` (ID: `1b867rfz_V7hoLiUVMfqDZ02MeOhTI9f5`)
  - `Aprendizaje_Automatico/` (ID: `10uGn7kjXuIZbaN0KsAZayPWa3BrNkvvR`)
  - `Bioinstrumentacion_2/` (ID: `1a-1fdbgXt2rhNyy5F_I77fLyq0etF_2T`)
  - `Ingenieria_Clinica_2/` (ID: `1e4_1Ge7jBqifSqmQ6TEpgZVlWsRAQBWn`)
  - `Redes_Neuronales_DL/` (ID: `1vr7UYBh_VX-qN15evz8kdj8EbIevZCIl`)
  - `Diseno_Biomedico_2/` (ID: `1-3IgiGQ50eUotZ_IQGM3-vnQP0eIEWZF`)
  - `Seminario_Biomedica/` (ID: `1IJ4ybyVX35VNdSvjlaRyFa2Tjlz7lZEK`)
  - `Monitoria_Ciudadana/` (ID: `1O3ZbJ0PdZ6b516YJ1HUjRWK4_vUOtQAM`)

- **Grabaciones Universitarias (Webex/Video/Audio)**:
  - Las grabaciones oficiales que comparte la universidad (`.mp4`, `.m4a`, `.mp3`) se suben o mueven directo a la subcarpeta de la materia.
  - El motor local Whisper extrae el audio directamente del video sin conversiones previas.
- **Clases Presenciales (iPhone)**: Grabación en 1 toque desde Notas de Voz compartida a la subcarpeta de la materia en Google Drive.
- **Flujo de Procesamiento**: Con solo decir *"Procesa la última clase de [Materia]"*, extraigo transcripción, conceptos, fórmulas y tareas.

---

## Equipo de Subagentes Especializados
Para trabajar en paralelo y resolver procesos extensos con máxima rapidez y precisión, contamos con subagentes dedicados:

1. **`transcription_processor` (Especialista en Audio & Síntesis)**:
   - Descarga audios/videos de Drive, corre el modelo Whisper local, genera apuntes estructurados con KaTeX y detecta compromisos para la agenda.
2. **`ia_engineer` (Especialista en Machine Learning & Deep Learning)**:
   - Desarrolla código en PyTorch, Scikit-learn y OpenCV. Diseña la CNN con regularización, entrena modelos y realiza experimentación reproducible.
3. **`biomedical_writer` (Especialista en Ingeniería Biomédica & Documentación)**:
   - Redacta informes técnicos de laboratorio (Máquina de Anestesia, Bioinstrumentación 2), análisis clínicos y memorias de proyecto en Markdown o Google Docs.
4. **`research` (Investigador Académico & Codebase)**:
   - Subagente de exploración rápida de literatura, documentación de librerías y consultas en segundo plano.
5. **`halcon_prompt_engineer` (Evolución de HALCÓN & Prompt Engineering)**:
   - Administra, edita y perfecciona los prompts de sistema y habilidades de HALCÓN (`ultron/llm.py`, `ultron/vision.py`, `ultron/skills.py`). Adapta sus respuestas al perfil dual biomédico e IA de Sebastián.
6. **`halcon_qa_tester` (Aseguramiento de Calidad & Estabilidad Operativa)**:
   - Ejecuta suites de pruebas automatizadas con `pytest`, verifica endpoints REST del Stark HUD (`/api/*`), telemetría de hardware, tolerancia a fallos y ausencia de regresiones.
7. **`halcon_gemini_integrator` (Puente de Integración Gemini & Cloud)**:
   - Diseña el enlace más directo, eficiente y seguro entre HALCÓN y el proyecto de Gemini / Antigravity, sincronizando contexto académico, Google Calendar, Google Drive y streaming de respuestas de baja latencia.

