/**
 * ULTRÓN v5.1 — 21ST.DEV MINIMAL SPATIAL GLASS & VOLUMETRIC SHADER HUD ENGINE
 * Architecture:
 * 1. Progressive Disclosure Slide-Over Glass Drawers (Telemetry & Multimodal Vision Studio)
 * 2. Real-Time Hardware Telemetry & Process Monitor (/api/telemetry @ 2.5s + Live Topbar Pill)
 * 3. 60 FPS 3D Volumetric Liquid Plasma / Harmonic Shader Orb (WebAudio AnalyserNode + 40 Orbital Particles)
 * 4. Low-Latency Continuous Voice Engine with 1700ms Smart Silence Debounce & Push-to-Talk
 * 5. Neural TTS Playback (/api/tts Edge-TTS MP3 + WebAudio Spectrum + WebSpeech Fallback)
 * 6. 21st.dev / Raycast Command Palette (Ctrl+K) & Quick-Action Pills
 */

(() => {
  'use strict';

  // ==========================================================================
  // APPLICATION STATE & CONSTANTS
  // ==========================================================================
  const TELEMETRY_POLL_MS = 2500;
  const SILENCE_DEBOUNCE_MS = 1700;
  const RESUME_MIC_DELAY_MS = 350;
  const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 40; // r = 40 -> 251.327

  // Crisp Inline Vector SVG Library (Zero Emojis Anywhere)
  const SVG_ICONS = {
    ultronAvatar:
      '<svg class="svg-icon icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>',
    speakerWave:
      '<svg class="svg-icon icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>',
    eyeScan:
      '<svg class="svg-icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path><circle cx="12" cy="12" r="3"></circle></svg>',
    spinner:
      '<svg class="svg-icon icon-sm spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>',
    mic:
      '<svg class="svg-icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>',
    recordPulse:
      '<svg class="svg-icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><circle cx="12" cy="12" r="4" fill="currentColor"></circle></svg>',
    rocket:
      '<svg class="svg-icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path></svg>',
    cube:
      '<svg class="svg-icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path><path d="m3.3 7 8.7 5 8.7-5"></path><path d="M12 22V12"></path></svg>',
    calendar:
      '<svg class="svg-icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
    music:
      '<svg class="svg-icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><path d="M8 14.5c2.5-1 5.5-1 8 0"></path><path d="M7 11.5c3.2-1.2 6.8-1.2 10 0"></path></svg>',
    code:
      '<svg class="svg-icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline><line x1="14" y1="4" x2="10" y2="20"></line></svg>',
    pulse:
      '<svg class="svg-icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>',
  };

  // 21st.dev / Raycast Command Palette Catalog
  const COMMAND_PALETTE_ITEMS = [
    {
      id: 'cmd-nutricoach',
      title: 'NutriCoach Pro',
      subtitle: 'abre nutricoach — Lanzar plataforma de nutrición IA',
      category: 'PROYECTO',
      icon: SVG_ICONS.rocket,
      action: () => sendCommand('abre nutricoach'),
    },
    {
      id: 'cmd-inventario',
      title: 'Inventario Web Pro',
      subtitle: 'abre inventario — Lanzar sistema de gestión de inventario',
      category: 'PROYECTO',
      icon: SVG_ICONS.cube,
      action: () => sendCommand('abre inventario'),
    },
    {
      id: 'cmd-calendar',
      title: 'Google Calendar',
      subtitle: 'abre google calendar — Consultar agenda y eventos',
      category: 'PRODUCTIVIDAD',
      icon: SVG_ICONS.calendar,
      action: () => sendCommand('abre google calendar'),
    },
    {
      id: 'cmd-spotify',
      title: 'Spotify',
      subtitle: 'abre spotify — Iniciar reproductor musical',
      category: 'MEDIA',
      icon: SVG_ICONS.music,
      action: () => sendCommand('abre spotify'),
    },
    {
      id: 'cmd-vscode',
      title: 'VS Code',
      subtitle: 'abre vscode — Abrir entorno de desarrollo integrado',
      category: 'DEV TOOLS',
      icon: SVG_ICONS.code,
      action: () => sendCommand('abre vscode'),
    },
    {
      id: 'cmd-diagnostico',
      title: 'Diagnóstico de Hardware',
      subtitle: 'analiza mi sistema — Auditoría completa de CPU, RAM, Disco y Red',
      category: 'TELEMETRÍA',
      icon: SVG_ICONS.pulse,
      action: () => {
        openDrawer('telemetry');
        sendCommand('analiza mi sistema');
      },
    },
    {
      id: 'cmd-vision-general',
      title: 'Visión: Inspección General',
      subtitle: 'Captura el escritorio y ofrece recomendaciones técnicas',
      category: 'VISIÓN VLM',
      icon: SVG_ICONS.eyeScan,
      action: () => {
        openDrawer('vision');
        runVisionAnalysis(
          '¿Qué hay en mi pantalla y qué recomendaciones técnicas tienes?',
          'general'
        );
      },
    },
    {
      id: 'cmd-vision-debug',
      title: 'Visión: Depurar Código',
      subtitle: 'Inspecciona errores de código, stacktraces o consola en vivo',
      category: 'VISIÓN VLM',
      icon: SVG_ICONS.code,
      action: () => {
        openDrawer('vision');
        runVisionAnalysis(
          'Analiza el código o la terminal en mi pantalla y detecta posibles errores o mejoras.',
          'debug'
        );
      },
    },
    {
      id: 'cmd-vision-ux',
      title: 'Visión: Auditoría UX',
      subtitle: 'Evalúa jerarquía visual, contraste y alineación de la interfaz',
      category: 'VISIÓN VLM',
      icon: SVG_ICONS.eyeScan,
      action: () => {
        openDrawer('vision');
        runVisionAnalysis(
          'Realiza una auditoría UX/UI de la interfaz en pantalla verificando contraste y diseño.',
          'ux_audit'
        );
      },
    },
    {
      id: 'cmd-vision-pid',
      title: 'Visión: Control PID',
      subtitle: 'Analiza señales biomédicas, sobretiro y estabilidad de lazo PID',
      category: 'VISIÓN VLM',
      icon: SVG_ICONS.pulse,
      action: () => {
        openDrawer('vision');
        runVisionAnalysis(
          'Analiza las señales y gráficas del lazo de control PID en pantalla.',
          'biomedical_pid'
        );
      },
    },
    {
      id: 'cmd-organize-downloads',
      title: 'Jarvis Pro: Organizar Descargas',
      subtitle: 'organiza mis descargas — Clasifica PDFs, imágenes, videos, ZIPs y código',
      category: 'JARVIS PRO',
      icon: SVG_ICONS.cube,
      action: () => sendCommand('organiza mis descargas'),
    },
    {
      id: 'cmd-organize-desktop',
      title: 'Jarvis Pro: Organizar Escritorio',
      subtitle: 'organiza mi escritorio — Ordena automáticamente los archivos del Escritorio',
      category: 'JARVIS PRO',
      icon: SVG_ICONS.cube,
      action: () => sendCommand('organiza mi escritorio'),
    },
    {
      id: 'cmd-edit-clipboard',
      title: 'Jarvis Pro: Editar Portapapeles In-Place',
      subtitle: 'mejora el texto copiado — Limpia o refactoriza el texto de tu portapapeles',
      category: 'JARVIS PRO',
      icon: SVG_ICONS.code,
      action: () => sendCommand('mejora el texto copiado'),
    },
    {
      id: 'cmd-mini-pill',
      title: 'Jarvis Pro: Modo Píldora Flotante',
      subtitle: 'Alternar vista compacta de onda acústica (Jarvis Waveform Pill)',
      category: 'JARVIS PRO',
      icon: SVG_ICONS.mic,
      action: () => toggleMiniPillMode(),
    },
  ];

  const state = {
    ultronState: 'idle', // 'idle' | 'listening' | 'processing' | 'speaking'
    voiceMode: 'handsfree', // 'handsfree' | 'ptt' | 'muted'
    speechLang: 'es-CO', // 'es-CO' | 'en-US'
    ttsEnabled: true,
    isSpeaking: false,
    isProcessing: false,
    pttActive: false,
    recognitionRunning: false,
    accumulatedTranscript: '',
    interimTranscript: '',
    silenceTimer: null,
    debounceStartAt: 0,
    currentAudioUrl: null,
    ttsAbortController: null,
    audioCtx: null,
    micAnalyser: null,
    ttsAnalyser: null,
    micStream: null,
    mediaElementCon: false,
    activeDrawer: null, // null | 'telemetry' | 'vision'
    miniPillMode: false,
    cmdPaletteOpen: false,
    cmdPaletteSelectedIndex: 0,
    filteredCommands: [...COMMAND_PALETTE_ITEMS],
  };

  // ==========================================================================
  // DOM REFERENCES
  // ==========================================================================
  const dom = {
    // Topbar & Drawer Triggers
    btnToggleTelemetry: document.getElementById('btn-toggle-telemetry'),
    btnToggleVision: document.getElementById('btn-toggle-vision'),
    btnMiniPill: document.getElementById('btn-mini-pill'),
    miniPillDock: document.getElementById('mini-pill-dock'),
    miniPillMicBtn: document.getElementById('mini-pill-mic-btn'),
    miniPillExpandBtn: document.getElementById('mini-pill-expand-btn'),
    miniPillText: document.getElementById('mini-pill-text'),
    pillCpuVal: document.getElementById('pill-cpu-val'),
    pillRamVal: document.getElementById('pill-ram-val'),
    cmdPaletteTriggerBtn: document.getElementById('cmd-palette-trigger-btn'),
    dockCmdPaletteBtn: document.getElementById('dock-cmd-palette-btn'),
    ttsToggleBtn: document.getElementById('tts-toggle-btn'),
    ttsToggleLabel: document.getElementById('tts-toggle-label'),
    langEsBtn: document.getElementById('lang-es-btn'),
    langEnBtn: document.getElementById('lang-en-btn'),

    // Slide-Over Drawers
    drawerBackdrop: document.getElementById('drawer-backdrop'),
    telemetryDrawer: document.getElementById('telemetry-drawer'),
    visionDrawer: document.getElementById('vision-drawer'),
    closeTelemetryDrawerBtn: document.getElementById('close-telemetry-drawer-btn'),
    closeVisionDrawerBtn: document.getElementById('close-vision-drawer-btn'),

    // Telemetry Drawer Elements
    connectionPill: document.getElementById('connection-status-pill'),
    systemStatusText: document.getElementById('system-status-text'),
    apiLatencyMs: document.getElementById('api-latency-ms'),
    uptimeReadout: document.getElementById('uptime-readout'),
    platformInfo: document.getElementById('platform-info'),
    healthBadge: document.getElementById('health-status-badge'),
    refreshTelemetryBtn: document.getElementById('refresh-telemetry-btn'),
    telemetryAlerts: document.getElementById('telemetry-alerts'),
    telemetryAlertsText: document.getElementById('telemetry-alerts-text'),
    cpuGaugeRing: document.getElementById('cpu-gauge-ring'),
    cpuPercent: document.getElementById('cpu-percent'),
    cpuCores: document.getElementById('cpu-cores'),
    cpuFreq: document.getElementById('cpu-freq'),
    cpuTemp: document.getElementById('cpu-temp'),
    cpuStateLabel: document.getElementById('cpu-state-label'),
    ramGaugeRing: document.getElementById('ram-gauge-ring'),
    ramPercent: document.getElementById('ram-percent'),
    ramUsedTotal: document.getElementById('ram-used-total'),
    ramAvail: document.getElementById('ram-avail'),
    ramSwap: document.getElementById('ram-swap'),
    ramThresholdLabel: document.getElementById('ram-threshold-label'),
    ramProgressBar: document.getElementById('ram-progress-bar'),
    diskFree: document.getElementById('disk-free'),
    diskPercent: document.getElementById('disk-percent'),
    diskUsedTotal: document.getElementById('disk-used-total'),
    diskMount: document.getElementById('disk-mount'),
    diskProgressBar: document.getElementById('disk-progress-bar'),
    netStatus: document.getElementById('net-status'),
    netTraffic: document.getElementById('net-traffic'),
    batteryStatus: document.getElementById('battery-status'),
    telemetryUpdatedAt: document.getElementById('telemetry-updated-at'),
    topProcessesBody: document.getElementById('top-processes-body'),

    // Center Stage: Shader Orb + Stream + Dock
    reactorClickZone: document.getElementById('reactor-click-zone'),
    reactorCanvas: document.getElementById('reactor-canvas'),
    reactorStateBadge: document.getElementById('reactor-state-badge'),
    bargeInBtn: document.getElementById('barge-in-btn'),
    modeHandsfreeBtn: document.getElementById('mode-handsfree-btn'),
    modePttBtn: document.getElementById('mode-ptt-btn'),
    modeMutedBtn: document.getElementById('mode-muted-btn'),
    pttHoldBtn: document.getElementById('ptt-hold-btn'),
    transcriptDot: document.getElementById('transcript-activity-dot'),
    liveTranscript: document.getElementById('live-transcript'),
    flushTranscriptBtn: document.getElementById('flush-transcript-btn'),
    suggestionChips: document.getElementById('suggestion-chips'),
    chatLog: document.getElementById('chat-log'),
    clearChatBtn: document.getElementById('clear-chat-btn'),
    commandForm: document.getElementById('command-form'),
    commandInput: document.getElementById('command-input'),
    commandSubmitBtn: document.getElementById('command-submit-btn'),
    quickActionBtns: document.querySelectorAll('.quick-action-btn[data-command]'),
    visionQuickBtn: document.getElementById('qa-vision-quick'),

    // Vision Drawer Elements
    visionForm: document.getElementById('vision-form'),
    visionModeSelect: document.getElementById('vision-mode-select'),
    visionQueryInput: document.getElementById('vision-query-input'),
    visionCaptureBtn: document.getElementById('vision-capture-btn'),
    visionMetaBadge: document.getElementById('vision-meta-badge'),
    visionEmptyState: document.getElementById('vision-empty-state'),
    visionImageWrapper: document.getElementById('vision-image-wrapper'),
    visionPreviewImg: document.getElementById('vision-preview-img'),
    visionResolutionTag: document.getElementById('vision-resolution-tag'),
    visionLatencyTag: document.getElementById('vision-latency-tag'),
    visionAnalysisOutput: document.getElementById('vision-analysis-output'),

    // Modals & Audio Player
    cmdPaletteModal: document.getElementById('command-palette-modal'),
    cmdPaletteInput: document.getElementById('cmd-palette-input'),
    cmdPaletteList: document.getElementById('cmd-palette-list'),
    cmdPaletteCloseBtn: document.getElementById('cmd-palette-close-btn'),
    lightboxModal: document.getElementById('vision-lightbox-modal'),
    lightboxImg: document.getElementById('lightbox-img'),
    lightboxCloseBtn: document.getElementById('lightbox-close-btn'),
    audioPlayer: document.getElementById('ultron-audio-player'),
  };

  // ==========================================================================
  // SLIDE-OVER DRAWERS MANAGEMENT (PROGRESSIVE DISCLOSURE)
  // ==========================================================================
  function openDrawer(drawerName) {
    state.activeDrawer = drawerName;
    const isTelemetry = drawerName === 'telemetry';
    const isVision = drawerName === 'vision';

    if (dom.telemetryDrawer) {
      dom.telemetryDrawer.classList.toggle('open', isTelemetry);
      dom.telemetryDrawer.setAttribute('aria-hidden', String(!isTelemetry));
    }
    if (dom.visionDrawer) {
      dom.visionDrawer.classList.toggle('open', isVision);
      dom.visionDrawer.setAttribute('aria-hidden', String(!isVision));
    }
    if (dom.btnToggleTelemetry) {
      dom.btnToggleTelemetry.classList.toggle('active', isTelemetry);
      dom.btnToggleTelemetry.setAttribute('aria-expanded', String(isTelemetry));
    }
    if (dom.btnToggleVision) {
      dom.btnToggleVision.classList.toggle('active', isVision);
      dom.btnToggleVision.setAttribute('aria-expanded', String(isVision));
    }
    if (dom.drawerBackdrop) {
      dom.drawerBackdrop.classList.toggle('hidden', !isTelemetry && !isVision);
    }
  }

  function closeDrawers() {
    openDrawer(null);
  }

  function toggleDrawer(drawerName) {
    if (state.activeDrawer === drawerName) {
      closeDrawers();
    } else {
      openDrawer(drawerName);
    }
  }

  function toggleMiniPillMode(forceState) {
    const nextState = typeof forceState === 'boolean' ? forceState : !state.miniPillMode;
    state.miniPillMode = nextState;
    document.body.classList.toggle('mini-pill-mode', nextState);
    if (dom.btnMiniPill) {
      dom.btnMiniPill.classList.toggle('active', nextState);
      dom.btnMiniPill.setAttribute('aria-pressed', String(nextState));
    }
    if (dom.miniPillDock) {
      dom.miniPillDock.classList.toggle('hidden', !nextState);
    }
    if (nextState) {
      closeDrawers();
    }
  }

  // ==========================================================================
  // UI STATE MANAGEMENT
  // ==========================================================================
  function setUltronState(newState) {
    state.ultronState = newState;
    const visualState = newState === 'idle' ? 'listening' : newState;
    document.body.setAttribute('data-ultron-state', newState);
    document.body.setAttribute('data-state', visualState);
    if (!dom.reactorStateBadge) return;

    dom.reactorStateBadge.setAttribute('data-state', newState);
    switch (newState) {
      case 'listening':
        dom.reactorStateBadge.textContent = 'Escuchando';
        dom.bargeInBtn.classList.add('hidden');
        if (dom.miniPillText) dom.miniPillText.textContent = 'ESCUCHANDO...';
        break;
      case 'processing':
        dom.reactorStateBadge.textContent = 'Procesando...';
        dom.bargeInBtn.classList.add('hidden');
        if (dom.miniPillText) dom.miniPillText.textContent = 'PROCESANDO ORDEN...';
        break;
      case 'speaking':
        dom.reactorStateBadge.textContent = 'Hablando';
        dom.bargeInBtn.classList.remove('hidden');
        if (dom.miniPillText) dom.miniPillText.textContent = 'ULTRÓN HABLANDO...';
        break;
      default:
        dom.reactorStateBadge.textContent = 'En espera';
        dom.bargeInBtn.classList.add('hidden');
        if (dom.miniPillText) dom.miniPillText.textContent = 'ULTRÓN EN ESPERA';
        break;
    }
  }

  function updateLiveTranscriptDisplay(text, isPlaceholder = false) {
    if (!dom.liveTranscript) return;
    dom.liveTranscript.textContent = text;
    if (dom.miniPillText && !isPlaceholder && text) {
      dom.miniPillText.textContent = text;
    }
    if (isPlaceholder) {
      dom.liveTranscript.classList.add('placeholder');
      dom.transcriptDot.classList.remove('active');
      dom.flushTranscriptBtn.classList.add('hidden');
    } else {
      dom.liveTranscript.classList.remove('placeholder');
      dom.transcriptDot.classList.add('active');
      dom.flushTranscriptBtn.classList.remove('hidden');
    }
  }

  function appendChatMessage({ sender = 'Ultrón', text, meta = '', isUser = false }) {
    if (!dom.chatLog) return;
    const entry = document.createElement('div');
    entry.className = `chat-entry ${isUser ? 'user-entry' : 'ultron-entry'}`;

    if (isUser) {
      // Clean, minimal user bubble (no noisy headers or badges)
      const bodyDiv = document.createElement('div');
      bodyDiv.className = 'chat-body';
      bodyDiv.textContent = text;
      entry.appendChild(bodyDiv);
    } else {
      // Clean Ultrón response with subtle glowing emblem + readable prose + minimal footer
      const avatarBadge = document.createElement('span');
      avatarBadge.className = 'chat-avatar-badge';
      avatarBadge.innerHTML = SVG_ICONS.ultronAvatar;

      const contentCol = document.createElement('div');
      contentCol.className = 'chat-content-col';

      const bodyDiv = document.createElement('div');
      bodyDiv.className = 'chat-body';
      bodyDiv.textContent = text;

      const footerMeta = document.createElement('div');
      footerMeta.className = 'chat-footer-meta';

      const timestamp = new Date().toLocaleTimeString('es-CO', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
      });

      const metaSpan = document.createElement('span');
      metaSpan.textContent = meta ? `${sender} · ${timestamp} · ${meta}` : `${sender} · ${timestamp}`;
      footerMeta.appendChild(metaSpan);

      if (text) {
        const replayBtn = document.createElement('button');
        replayBtn.type = 'button';
        replayBtn.className = 'replay-tts-btn';
        replayBtn.title = 'Reproducir respuesta por voz';
        replayBtn.setAttribute('aria-label', 'Reproducir respuesta por voz');
        replayBtn.innerHTML = `${SVG_ICONS.speakerWave}<span>Escuchar</span>`;
        replayBtn.addEventListener('click', () => {
          speakResponse(text, 'es');
        });
        footerMeta.appendChild(replayBtn);
      }

      contentCol.appendChild(bodyDiv);
      contentCol.appendChild(footerMeta);

      entry.appendChild(avatarBadge);
      entry.appendChild(contentCol);
    }

    dom.chatLog.appendChild(entry);
    dom.chatLog.scrollTop = dom.chatLog.scrollHeight;
  }

  // ==========================================================================
  // 1. REAL-TIME HARDWARE TELEMETRY & PROCESS MONITOR (/api/telemetry)
  // ==========================================================================
  function setRadialGauge(circleEl, percent, warnThreshold = 75, critThreshold = 85) {
    if (!circleEl) return;
    const clamped = Math.max(0, Math.min(100, Number(percent) || 0));
    const offset = GAUGE_CIRCUMFERENCE - (clamped / 100) * GAUGE_CIRCUMFERENCE;
    circleEl.style.strokeDashoffset = offset.toFixed(2);
    circleEl.classList.remove('warn', 'crit');
    if (clamped >= critThreshold) {
      circleEl.classList.add('crit');
    } else if (clamped >= warnThreshold) {
      circleEl.classList.add('warn');
    }
  }

  function setLinearBar(barEl, percent, warnThreshold = 75, critThreshold = 85) {
    if (!barEl) return;
    const clamped = Math.max(0, Math.min(100, Number(percent) || 0));
    barEl.style.width = `${clamped.toFixed(1)}%`;
    barEl.classList.remove('warn', 'crit');
    if (clamped >= critThreshold) {
      barEl.classList.add('crit');
    } else if (clamped >= warnThreshold) {
      barEl.classList.add('warn');
    }
  }

  function formatUptime(minutes) {
    const totalMins = Math.max(0, Math.floor(Number(minutes) || 0));
    const hrs = Math.floor(totalMins / 60);
    const mins = totalMins % 60;
    return `${String(hrs).padStart(2, '0')}h ${String(mins).padStart(2, '0')}m`;
  }

  async function fetchTelemetry() {
    const t0 = performance.now();
    try {
      const resp = await fetch('/api/telemetry', { cache: 'no-store' });
      const latency = Math.max(1, Math.round(performance.now() - t0));

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const data = await resp.json();
      const overallStatus = (data.status || 'OPTIMAL').toUpperCase();

      // Connection & Topbar Live Pill
      if (dom.connectionPill) {
        dom.connectionPill.setAttribute('data-status', 'online');
      }
      if (dom.btnToggleTelemetry) {
        dom.btnToggleTelemetry.setAttribute('data-status', 'online');
        dom.btnToggleTelemetry.setAttribute('data-health', overallStatus);
      }
      if (dom.systemStatusText) {
        dom.systemStatusText.textContent = 'EN LÍNEA';
      }
      if (dom.apiLatencyMs) {
        dom.apiLatencyMs.textContent = `${latency} ms`;
      }
      if (data.platform_info && dom.platformInfo) {
        dom.platformInfo.textContent = data.platform_info.toUpperCase();
      }
      if (typeof data.uptime_minutes === 'number' && dom.uptimeReadout) {
        dom.uptimeReadout.textContent = formatUptime(data.uptime_minutes);
      }

      // Health Status Badge
      if (dom.healthBadge) {
        dom.healthBadge.textContent = overallStatus;
        dom.healthBadge.setAttribute('data-health', overallStatus);
      }

      // Hardware Alerts Banner
      const alerts = Array.isArray(data.alerts) ? data.alerts : [];
      if (dom.telemetryAlerts) {
        if (alerts.length > 0) {
          dom.telemetryAlerts.classList.remove('hidden');
          dom.telemetryAlerts.classList.toggle('critical', overallStatus === 'CRITICAL');
          dom.telemetryAlertsText.textContent = alerts.join(' · ');
        } else {
          dom.telemetryAlerts.classList.add('hidden');
        }
      }

      // CPU Metrics
      const cpu = data.cpu || {};
      const cpuPct = Number(cpu.usage_percent) || 0;
      if (dom.pillCpuVal) {
        dom.pillCpuVal.textContent = `${Math.round(cpuPct)}%`;
      }
      if (dom.cpuPercent) {
        dom.cpuPercent.textContent = cpuPct.toFixed(1);
      }
      setRadialGauge(dom.cpuGaugeRing, cpuPct, 75, 90);
      if (dom.cpuCores) {
        dom.cpuCores.textContent = `${cpu.core_count_physical || '--'}P / ${cpu.core_count_logical || '--'}L`;
      }
      if (dom.cpuFreq) {
        dom.cpuFreq.textContent = cpu.frequency_mhz ? `${Math.round(cpu.frequency_mhz)} MHz` : 'NOMINAL';
      }
      if (dom.cpuTemp) {
        dom.cpuTemp.textContent = cpu.temperature_c ? `${Number(cpu.temperature_c).toFixed(1)} °C` : 'TEMP OK';
      }
      if (dom.cpuStateLabel) {
        dom.cpuStateLabel.textContent = cpuPct >= 90 ? 'CRÍTICO' : cpuPct >= 75 ? 'CARGA ALTA' : 'ESTABLE';
      }

      // Memory (RAM) Metrics
      const mem = data.memory || {};
      const ramPct = Number(mem.percent) || 0;
      if (dom.pillRamVal) {
        dom.pillRamVal.textContent = `${Math.round(ramPct)}%`;
      }
      if (dom.ramPercent) {
        dom.ramPercent.textContent = ramPct.toFixed(1);
      }
      setRadialGauge(dom.ramGaugeRing, ramPct, 75, 85);
      setLinearBar(dom.ramProgressBar, ramPct, 75, 85);
      if (dom.ramUsedTotal) {
        dom.ramUsedTotal.textContent = `${Number(mem.used_gb || 0).toFixed(1)} / ${Number(mem.total_gb || 0).toFixed(1)} GB`;
      }
      if (dom.ramAvail) {
        dom.ramAvail.textContent = `${Number(mem.available_gb || 0).toFixed(1)} GB`;
      }
      if (dom.ramSwap) {
        dom.ramSwap.textContent = `SWAP ${Number(mem.swap_percent || 0).toFixed(0)}%`;
      }
      if (dom.ramThresholdLabel) {
        dom.ramThresholdLabel.textContent =
          ramPct >= 85 ? 'ALERTA > 85%' : ramPct >= 75 ? 'ELEVADO > 75%' : '< 85% NOMINAL';
      }

      // Disk Metrics
      const disk = data.disk || {};
      const diskPct = Number(disk.percent) || 0;
      if (dom.diskFree) {
        dom.diskFree.textContent = `${Number(disk.free_gb || 0).toFixed(1)} GB LIBRES`;
      }
      if (dom.diskPercent) {
        dom.diskPercent.textContent = `${diskPct.toFixed(1)}%`;
      }
      if (dom.diskUsedTotal) {
        dom.diskUsedTotal.textContent = `${Number(disk.used_gb || 0).toFixed(1)} / ${Number(disk.total_gb || 0).toFixed(1)} GB`;
      }
      if (dom.diskMount) {
        dom.diskMount.textContent = disk.mount_point || '/';
      }
      setLinearBar(dom.diskProgressBar, diskPct, 80, 90);

      // Network & Battery Metrics
      const net = data.network || {};
      if (dom.netStatus) {
        dom.netStatus.textContent = net.is_connected !== false ? 'ONLINE' : 'OFFLINE';
      }
      if (dom.netTraffic) {
        dom.netTraffic.textContent = `↑ ${Number(net.bytes_sent_mb || 0).toFixed(1)} MB · ↓ ${Number(net.bytes_recv_mb || 0).toFixed(1)} MB`;
      }

      const bat = data.battery || {};
      if (dom.batteryStatus) {
        if (bat.present && bat.percent !== null && bat.percent !== undefined) {
          const plugStr = bat.power_plugged ? 'AC' : 'BAT';
          dom.batteryStatus.textContent = `${Number(bat.percent).toFixed(0)}% · ${plugStr}`;
        } else {
          dom.batteryStatus.textContent = 'AC CONECTADO';
        }
      }

      // Top 5 Active Processes Table
      const procs = Array.isArray(data.top_processes) ? data.top_processes.slice(0, 5) : [];
      renderTopProcesses(procs);

      const nowStr = new Date().toLocaleTimeString('es-CO', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      if (dom.telemetryUpdatedAt) {
        dom.telemetryUpdatedAt.textContent = `SYNC ${nowStr}`;
      }
    } catch (err) {
      if (dom.connectionPill) {
        dom.connectionPill.setAttribute('data-status', 'offline');
      }
      if (dom.btnToggleTelemetry) {
        dom.btnToggleTelemetry.setAttribute('data-status', 'offline');
      }
      if (dom.systemStatusText) {
        dom.systemStatusText.textContent = 'SIN SEÑAL';
      }
    }
  }

  function renderTopProcesses(procs) {
    if (!dom.topProcessesBody) return;
    if (!procs.length) {
      dom.topProcessesBody.innerHTML =
        '<tr><td colspan="4" class="empty-row">Sin procesos reportados</td></tr>';
      return;
    }

    dom.topProcessesBody.innerHTML = '';
    for (const proc of procs) {
      const tr = document.createElement('tr');

      const nameTd = document.createElement('td');
      nameTd.className = 'proc-name-cell';
      nameTd.title = proc.name || 'proceso';
      nameTd.textContent = proc.name || 'proceso';

      const pidTd = document.createElement('td');
      pidTd.className = 'proc-pid-cell';
      pidTd.textContent = String(proc.pid ?? '--');

      const mbVal = Number(proc.memory_mb || 0);
      const mbTd = document.createElement('td');
      mbTd.className = `num-col ${mbVal >= 500 ? 'proc-mem-high' : ''}`;
      mbTd.textContent = `${mbVal.toFixed(1)}`;

      const pctVal = Number(proc.memory_percent || 0);
      const pctTd = document.createElement('td');
      pctTd.className = `num-col ${pctVal >= 10 ? 'proc-mem-high' : ''}`;
      pctTd.textContent = `${pctVal.toFixed(1)}%`;

      tr.appendChild(nameTd);
      tr.appendChild(pidTd);
      tr.appendChild(mbTd);
      tr.appendChild(pctTd);
      dom.topProcessesBody.appendChild(tr);
    }
  }

  // ==========================================================================
  // 2. WEBAUDIO PIPELINE & 60 FPS 3D VOLUMETRIC SHADER ORB
  // ==========================================================================
  function ensureAudioContext() {
    if (!state.audioCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        state.audioCtx = new AudioCtx();
      }
    }
    if (state.audioCtx && state.audioCtx.state === 'suspended') {
      state.audioCtx.resume().catch(() => {});
    }
    if (state.audioCtx && !state.mediaElementCon && dom.audioPlayer) {
      try {
        state.ttsAnalyser = state.audioCtx.createAnalyser();
        state.ttsAnalyser.fftSize = 256;
        state.ttsAnalyser.smoothingTimeConstant = 0.78;
        const source = state.audioCtx.createMediaElementSource(dom.audioPlayer);
        source.connect(state.ttsAnalyser);
        state.ttsAnalyser.connect(state.audioCtx.destination);
        state.mediaElementCon = true;
      } catch (e) {
        // Fallback if already connected
      }
    }
  }

  async function initMicrophoneVisualizer() {
    if (state.micStream || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      state.micStream = stream;
      ensureAudioContext();
      if (state.audioCtx) {
        const micSource = state.audioCtx.createMediaStreamSource(stream);
        state.micAnalyser = state.audioCtx.createAnalyser();
        state.micAnalyser.fftSize = 256;
        state.micAnalyser.smoothingTimeConstant = 0.75;
        micSource.connect(state.micAnalyser);
      }
    } catch (err) {
      // Continues smoothly with synthetic harmonic shader if mic permission denied
    }
  }

  function startReactorLoop() {
    const canvas = dom.reactorCanvas;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const freqBins = new Uint8Array(128);
    const waveBins = new Uint8Array(128);
    let phase = 0;

    // 40 Reactive 3D Orbital Quantum Particles
    const PARTICLE_COUNT = 40;
    const particles = Array.from({ length: PARTICLE_COUNT }, (_, idx) => ({
      theta: (idx / PARTICLE_COUNT) * Math.PI * 2,
      phi: Math.acos(2 * ((idx * 0.6180339887) % 1) - 1),
      radius: 40 + (idx % 5) * 6,
      speed: 0.008 + (idx % 7) * 0.0025,
      size: 1.15 + (idx % 3) * 0.55,
    }));

    // 4 Volumetric Plasma Ribbon Layers
    const plasmaRibbons = [
      { freq1: 3, freq2: 5, speed: 1.1, baseRadius: 34, amp: 11, alpha: 0.42 },
      { freq1: 4, freq2: 3, speed: -0.85, baseRadius: 32, amp: 13, alpha: 0.36 },
      { freq1: 2, freq2: 6, speed: 1.45, baseRadius: 29, amp: 10, alpha: 0.32 },
      { freq1: 5, freq2: 4, speed: -1.25, baseRadius: 36, amp: 9, alpha: 0.25 },
    ];

    function renderFrame(timestamp) {
      const dpr = window.devicePixelRatio || 1;
      const displaySize = 144;
      if (canvas.width !== displaySize * dpr || canvas.height !== displaySize * dpr) {
        canvas.width = displaySize * dpr;
        canvas.height = displaySize * dpr;
      }

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, displaySize, displaySize);

      const cx = displaySize / 2;
      const cy = displaySize / 2;

      // Sample real WebAudio spectrum if available, else generate organic harmonic envelope
      let activeAnalyser = null;
      if (state.ultronState === 'speaking' && state.ttsAnalyser) {
        activeAnalyser = state.ttsAnalyser;
      } else if (state.ultronState === 'listening' && state.micAnalyser) {
        activeAnalyser = state.micAnalyser;
      }

      let avgEnergy = 0;
      if (activeAnalyser) {
        activeAnalyser.getByteFrequencyData(freqBins);
        activeAnalyser.getByteTimeDomainData(waveBins);
        let sum = 0;
        for (let i = 0; i < 64; i++) {
          sum += freqBins[i];
        }
        avgEnergy = sum / (64 * 255);
      }

      if (state.ultronState === 'speaking' && avgEnergy < 0.05) {
        const t = timestamp * 0.008;
        for (let i = 0; i < 64; i++) {
          const syllabicWave =
            Math.sin(t * 2.3 + i * 0.25) * 0.5 +
            Math.cos(t * 5.1 - i * 0.15) * 0.35 +
            Math.sin(t * 1.1) * 0.25;
          freqBins[i] = Math.max(18, Math.min(245, Math.floor(Math.abs(syllabicWave) * 215)));
        }
        avgEnergy = 0.44 + 0.24 * Math.sin(t * 3.4);
      } else if (state.ultronState === 'processing') {
        const t = timestamp * 0.012;
        for (let i = 0; i < 64; i++) {
          freqBins[i] = Math.floor(70 + 60 * Math.sin(t + i * 0.3));
        }
        avgEnergy = 0.32;
      } else if (avgEnergy < 0.02) {
        const t = timestamp * 0.0035;
        for (let i = 0; i < 64; i++) {
          freqBins[i] = Math.floor(14 + 10 * Math.sin(t + i * 0.2));
        }
        avgEnergy = 0.06;
      }

      phase += 0.022 + avgEnergy * 0.055;

      // Select 21st.dev Volumetric Shader Palette by Ultrón State
      let coreRgb = '0, 240, 255'; // Electric Cyan
      let secondaryRgb = '56, 189, 248'; // Sky Blue
      let tertiaryRgb = '99, 102, 241'; // Indigo Plasma
      if (state.ultronState === 'speaking') {
        coreRgb = '255, 42, 95'; // Ultron Crimson
        secondaryRgb = '244, 63, 94'; // Rose Neon
        tertiaryRgb = '217, 70, 239'; // Magenta Plasma
      } else if (state.ultronState === 'processing') {
        coreRgb = '245, 158, 11'; // Quantum Amber
        secondaryRgb = '251, 191, 36'; // Solar Gold
        tertiaryRgb = '249, 115, 22'; // Deep Orange
      }

      // 1. Outer 48-Bin Precision Radial Frequency Halo
      const haloBaseR = 54;
      const numBars = 48;
      for (let i = 0; i < numBars; i++) {
        const angle = (i / numBars) * Math.PI * 2 - Math.PI / 2;
        const binVal = freqBins[i] / 255;
        const barLen = 2 + binVal * 12;
        const x1 = cx + Math.cos(angle) * haloBaseR;
        const y1 = cy + Math.sin(angle) * haloBaseR;
        const x2 = cx + Math.cos(angle) * (haloBaseR + barLen);
        const y2 = cy + Math.sin(angle) * (haloBaseR + barLen);

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle =
          binVal > 0.42 ? `rgba(${coreRgb}, 0.85)` : `rgba(${secondaryRgb}, 0.28)`;
        ctx.lineWidth = 1.5;
        ctx.lineCap = 'round';
        ctx.stroke();
      }

      // 2. Multi-Layered Volumetric Liquid Plasma / Harmonic Ribbons (screen blend)
      ctx.save();
      ctx.globalCompositeOperation = 'screen';

      for (let rIdx = 0; rIdx < plasmaRibbons.length; rIdx++) {
        const rib = plasmaRibbons[rIdx];
        const vertices = 60;
        ctx.beginPath();

        for (let v = 0; v <= vertices; v++) {
          const theta = (v / vertices) * Math.PI * 2;
          const binSample = freqBins[(v * 2 + rIdx * 7) % 64] / 255;
          const harmonicOffset =
            Math.sin(theta * rib.freq1 + phase * rib.speed) *
              (2.4 + avgEnergy * rib.amp) +
            Math.cos(theta * rib.freq2 - phase * rib.speed * 0.8) *
              (1.8 + binSample * (rib.amp * 0.65));

          const rad = rib.baseRadius + avgEnergy * 7.5 + harmonicOffset;
          const vx = cx + Math.cos(theta) * rad;
          const vy = cy + Math.sin(theta) * rad;

          if (v === 0) {
            ctx.moveTo(vx, vy);
          } else {
            ctx.lineTo(vx, vy);
          }
        }
        ctx.closePath();

        const ribbonGrad = ctx.createRadialGradient(cx, cy, 2, cx, cy, 52);
        const layerRgb = rIdx % 2 === 0 ? coreRgb : rIdx === 1 ? secondaryRgb : tertiaryRgb;
        ribbonGrad.addColorStop(0, `rgba(255, 255, 255, ${rib.alpha * 0.9})`);
        ribbonGrad.addColorStop(0.45, `rgba(${layerRgb}, ${rib.alpha})`);
        ribbonGrad.addColorStop(1, `rgba(${tertiaryRgb}, 0.02)`);

        ctx.fillStyle = ribbonGrad;
        ctx.fill();

        ctx.strokeStyle = `rgba(${layerRgb}, ${0.45 + avgEnergy * 0.35})`;
        ctx.lineWidth = 1.15;
        ctx.stroke();
      }

      // 3. 3D Tilted Elliptical Orbital Rings (ctx.ellipse)
      const numRings = 3;
      for (let k = 0; k < numRings; k++) {
        ctx.save();
        ctx.translate(cx, cy);
        const tiltAngle = phase * (k % 2 === 0 ? 0.55 : -0.45) + (k * Math.PI) / 3;
        const rx = 47 + k * 3.5 + avgEnergy * 6;
        const ry = 15 + k * 4.5 + Math.sin(phase * 0.7 + k) * 4;

        ctx.beginPath();
        ctx.ellipse(0, 0, rx, Math.max(6, Math.abs(ry)), tiltAngle, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${k === 0 ? coreRgb : secondaryRgb}, ${0.32 + avgEnergy * 0.3})`;
        ctx.lineWidth = 1.1;
        ctx.stroke();
        ctx.restore();
      }

      // 4. 40 Floating Reactive 3D Energy Particles
      const speedBoost = 1 + avgEnergy * 4.2;
      for (let pIdx = 0; pIdx < particles.length; pIdx++) {
        const p = particles[pIdx];
        p.theta += p.speed * speedBoost;
        const r3d = p.radius + avgEnergy * 9;

        const x3d = r3d * Math.sin(p.phi) * Math.cos(p.theta);
        const y3d = r3d * Math.cos(p.phi);
        const z3d = r3d * Math.sin(p.phi) * Math.sin(p.theta);

        // Perspective projection
        const perspective = 120 / (120 - z3d);
        const px = cx + x3d * perspective;
        const py = cy + y3d * perspective;
        const alpha = Math.max(0.15, Math.min(0.95, (z3d + r3d) / (2 * r3d)));

        ctx.beginPath();
        ctx.arc(px, py, p.size * perspective, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${pIdx % 3 === 0 ? '255, 255, 255' : coreRgb}, ${alpha})`;
        ctx.fill();
      }

      // 5. Inner Singularity Specular Core
      const innerR = 17 + avgEnergy * 8.5;
      const coreGrad = ctx.createRadialGradient(cx - 3, cy - 3, 1, cx, cy, innerR * 1.6);
      coreGrad.addColorStop(0, 'rgba(255, 255, 255, 0.95)');
      coreGrad.addColorStop(0.35, `rgba(${coreRgb}, 0.75)`);
      coreGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

      ctx.beginPath();
      ctx.arc(cx, cy, innerR * 1.6, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();

      ctx.restore();
      ctx.restore();
      requestAnimationFrame(renderFrame);
    }

    requestAnimationFrame(renderFrame);
  }

  // ==========================================================================
  // 3. LOW-LATENCY CONTINUOUS VOICE ENGINE (SOLVES SENTENCE CUTOFF)
  // ==========================================================================
  const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;

  function clearSilenceDebounce() {
    if (state.silenceTimer) {
      clearTimeout(state.silenceTimer);
      state.silenceTimer = null;
    }
  }

  function scheduleSilenceCommit() {
    clearSilenceDebounce();
    if (state.voiceMode !== 'handsfree') {
      return;
    }
    state.debounceStartAt = performance.now();
    state.silenceTimer = setTimeout(() => {
      flushAccumulatedTranscript();
    }, SILENCE_DEBOUNCE_MS);
  }

  function flushAccumulatedTranscript() {
    clearSilenceDebounce();
    const combined = `${state.accumulatedTranscript} ${state.interimTranscript}`
      .replace(/\s+/g, ' ')
      .trim();

    state.accumulatedTranscript = '';
    state.interimTranscript = '';

    if (!combined) {
      updateLiveTranscriptDisplay('Habla con naturalidad o escribe tu consulta abajo...', true);
      return;
    }

    updateLiveTranscriptDisplay(`Enviando: "${combined}"`, false);
    sendCommand(combined);
  }

  function initSpeechRecognition() {
    if (!SpeechRecognitionAPI) {
      updateLiveTranscriptDisplay(
        'Usa el cuadro de texto inferior o abre en Chrome/Edge para voz continua.',
        true
      );
      return;
    }

    recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.lang = state.speechLang;

    recognition.onstart = () => {
      state.recognitionRunning = true;
      if (!state.isSpeaking && !state.isProcessing) {
        setUltronState('listening');
      }
    };

    recognition.onresult = (event) => {
      if (state.isSpeaking) {
        return;
      }

      let latestInterim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        const transcriptChunk = res[0].transcript;
        if (res.isFinal) {
          state.accumulatedTranscript = `${state.accumulatedTranscript} ${transcriptChunk}`
            .replace(/\s+/g, ' ')
            .trim();
        } else {
          latestInterim += transcriptChunk;
        }
      }

      state.interimTranscript = latestInterim.trim();
      const previewText = `${state.accumulatedTranscript} ${state.interimTranscript}`
        .replace(/\s+/g, ' ')
        .trim();

      if (previewText) {
        updateLiveTranscriptDisplay(previewText, false);
        if (state.voiceMode === 'handsfree') {
          scheduleSilenceCommit();
        }
      }
    };

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        updateLiveTranscriptDisplay(
          'Permiso de micrófono denegado. Actívalo en la barra del navegador.',
          true
        );
      }
    };

    recognition.onend = () => {
      state.recognitionRunning = false;

      const shouldKeepListening =
        !state.isSpeaking &&
        !state.isProcessing &&
        (state.voiceMode === 'handsfree' || (state.voiceMode === 'ptt' && state.pttActive));

      if (shouldKeepListening) {
        setTimeout(() => {
          safeStartRecognition();
        }, 180);
      } else if (!state.isSpeaking && !state.isProcessing) {
        setUltronState('idle');
      }
    };
  }

  function safeStartRecognition() {
    if (!recognition || state.recognitionRunning || state.isSpeaking) return;
    try {
      recognition.lang = state.speechLang;
      recognition.start();
      initMicrophoneVisualizer();
    } catch (e) {
      // Already started
    }
  }

  function safeStopRecognition() {
    if (!recognition) return;
    try {
      recognition.stop();
    } catch (e) {
      // Ignore stop errors
    }
    state.recognitionRunning = false;
  }

  function setVoiceMode(mode) {
    state.voiceMode = mode;
    clearSilenceDebounce();
    state.accumulatedTranscript = '';
    state.interimTranscript = '';

    dom.modeHandsfreeBtn.classList.toggle('active', mode === 'handsfree');
    dom.modePttBtn.classList.toggle('active', mode === 'ptt');
    dom.modeMutedBtn.classList.toggle('active', mode === 'muted');
    dom.pttHoldBtn.classList.toggle('hidden', mode !== 'ptt');

    if (mode === 'handsfree') {
      updateLiveTranscriptDisplay(
        'Habla con naturalidad o escribe tu consulta abajo...',
        true
      );
      if (!state.isSpeaking && !state.isProcessing) {
        safeStartRecognition();
      }
    } else if (mode === 'ptt') {
      safeStopRecognition();
      setUltronState('idle');
      updateLiveTranscriptDisplay(
        'Mantén presionada la barra [Espacio] o el botón inferior para hablar...',
        true
      );
    } else {
      safeStopRecognition();
      setUltronState('idle');
      updateLiveTranscriptDisplay(
        'Micrófono en pausa. Usa el teclado o reactiva Manos Libres.',
        true
      );
    }
  }

  function setSpeechLanguage(langCode) {
    state.speechLang = langCode;
    dom.langEsBtn.classList.toggle('active', langCode === 'es-CO');
    dom.langEnBtn.classList.toggle('active', langCode === 'en-US');

    if (recognition) {
      recognition.lang = langCode;
      if (state.recognitionRunning) {
        safeStopRecognition();
        setTimeout(() => safeStartRecognition(), 200);
      }
    }
  }

  // ==========================================================================
  // 4. NEURAL TTS PLAYBACK (/api/tts + WebSpeech Fallback) & BARGE-IN
  // ==========================================================================
  function stopSpeakingBargeIn() {
    if (state.ttsAbortController) {
      state.ttsAbortController.abort();
      state.ttsAbortController = null;
    }

    if (dom.audioPlayer) {
      try {
        dom.audioPlayer.pause();
        dom.audioPlayer.currentTime = 0;
        dom.audioPlayer.removeAttribute('src');
      } catch (e) {}
    }

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }

    if (state.currentAudioUrl) {
      URL.revokeObjectURL(state.currentAudioUrl);
      state.currentAudioUrl = null;
    }

    state.isSpeaking = false;
    setUltronState(state.voiceMode === 'handsfree' ? 'listening' : 'idle');

    if (state.voiceMode === 'handsfree') {
      setTimeout(() => {
        safeStartRecognition();
      }, RESUME_MIC_DELAY_MS);
    }
  }

  function finishSpeakingAndResumeMic() {
    state.isSpeaking = false;
    if (state.currentAudioUrl) {
      URL.revokeObjectURL(state.currentAudioUrl);
      state.currentAudioUrl = null;
    }
    if (state.voiceMode === 'handsfree') {
      setTimeout(() => {
        if (!state.isSpeaking && !state.isProcessing) {
          setUltronState('listening');
          safeStartRecognition();
        }
      }, RESUME_MIC_DELAY_MS);
    } else {
      setUltronState('idle');
    }
  }

  function speakWithBrowserFallback(text, lang = 'es') {
    if (!('speechSynthesis' in window)) {
      finishSpeakingAndResumeMic();
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang.startsWith('en') ? 'en-US' : 'es-CO';
    utterance.rate = 1.03;
    utterance.pitch = 0.96;

    const voices = window.speechSynthesis.getVoices();
    const preferredVoice =
      voices.find(
        (v) =>
          v.lang.toLowerCase().startsWith('es') &&
          /natural|neural|sabina|helena|dalia|jorge|google/i.test(v.name)
      ) || voices.find((v) => v.lang.toLowerCase().startsWith('es'));

    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    utterance.onstart = () => {
      state.isSpeaking = true;
      setUltronState('speaking');
    };
    utterance.onend = () => {
      finishSpeakingAndResumeMic();
    };
    utterance.onerror = () => {
      finishSpeakingAndResumeMic();
    };

    window.speechSynthesis.speak(utterance);
  }

  async function speakResponse(text, lang = 'es') {
    const cleanText = String(text || '').trim();
    if (!cleanText || !state.ttsEnabled) {
      finishSpeakingAndResumeMic();
      return;
    }

    safeStopRecognition();
    state.isSpeaking = true;
    setUltronState('speaking');
    ensureAudioContext();

    if (state.ttsAbortController) {
      state.ttsAbortController.abort();
    }
    state.ttsAbortController = new AbortController();

    try {
      const ttsUrl = `/api/tts?text=${encodeURIComponent(cleanText)}&lang=${encodeURIComponent(lang || 'es')}`;
      const resp = await fetch(ttsUrl, { signal: state.ttsAbortController.signal });

      if (resp.status === 200) {
        const blob = await resp.blob();
        if (blob && blob.size > 0) {
          if (state.currentAudioUrl) {
            URL.revokeObjectURL(state.currentAudioUrl);
          }
          const audioUrl = URL.createObjectURL(blob);
          state.currentAudioUrl = audioUrl;
          dom.audioPlayer.src = audioUrl;

          dom.audioPlayer.onended = () => {
            finishSpeakingAndResumeMic();
          };
          dom.audioPlayer.onerror = () => {
            speakWithBrowserFallback(cleanText, lang);
          };

          await dom.audioPlayer.play();
          return;
        }
      }

      speakWithBrowserFallback(cleanText, lang);
    } catch (err) {
      if (err && err.name === 'AbortError') {
        return;
      }
      speakWithBrowserFallback(cleanText, lang);
    }
  }

  // ==========================================================================
  // 5. COMMAND DISPATCHER (/api/command) & MULTIMODAL VISION (/api/vision)
  // ==========================================================================
  async function sendCommand(rawText) {
    const text = String(rawText || '').trim();
    if (!text) return;

    ensureAudioContext();
    clearSilenceDebounce();
    safeStopRecognition();

    const langShort = state.speechLang.startsWith('en') ? 'en' : 'es';
    appendChatMessage({
      text,
      isUser: true,
    });

    updateLiveTranscriptDisplay('Habla con naturalidad o escribe tu consulta abajo...', true);
    state.isProcessing = true;
    setUltronState('processing');

    const t0 = performance.now();
    try {
      const resp = await fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          lang: langShort,
          speak_on_server: false,
        }),
      });

      const elapsedMs = Math.max(1, Math.round(performance.now() - t0));
      const data = await resp.json();
      const replyText = data.reply || 'Orden procesada correctamente.';

      appendChatMessage({
        sender: 'Ultrón',
        text: replyText,
        meta: `${elapsedMs} ms`,
        isUser: false,
      });

      state.isProcessing = false;
      await speakResponse(replyText, 'es');
    } catch (err) {
      state.isProcessing = false;
      const errMsg =
        'Error de enlace con el núcleo local de Ultrón. Verifica que el servidor esté activo.';
      appendChatMessage({
        sender: 'Ultrón',
        text: errMsg,
        meta: 'Error',
        isUser: false,
      });
      setUltronState(state.voiceMode === 'handsfree' ? 'listening' : 'idle');
      if (state.voiceMode === 'handsfree') {
        safeStartRecognition();
      }
    }
  }

  async function runVisionAnalysis(customQuery, customMode) {
    ensureAudioContext();
    openDrawer('vision');

    const query =
      customQuery ||
      (dom.visionQueryInput ? dom.visionQueryInput.value.trim() : '') ||
      '¿Qué hay en mi pantalla?';
    const mode =
      customMode || (dom.visionModeSelect ? dom.visionModeSelect.value : 'general');

    if (dom.visionModeSelect && customMode) {
      dom.visionModeSelect.value = customMode;
    }

    dom.visionCaptureBtn.disabled = true;
    dom.visionCaptureBtn.innerHTML = `${SVG_ICONS.spinner}<span>Capturando y analizando...</span>`;
    dom.visionAnalysisOutput.textContent =
      'Capturando frame del escritorio y ejecutando inspección multimodal...';
    state.isProcessing = true;
    setUltronState('processing');

    try {
      const resp = await fetch('/api/vision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode }),
      });

      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      if (data.image_data_url) {
        dom.visionPreviewImg.src = data.image_data_url;
        dom.lightboxImg.src = data.image_data_url;
        dom.visionEmptyState.classList.add('hidden');
        dom.visionImageWrapper.classList.remove('hidden');
      }

      const providerLabel = (data.provider_used || 'VLM').toUpperCase();
      dom.visionMetaBadge.textContent = `${String(data.mode || mode).toUpperCase()} · ${providerLabel}`;
      dom.visionLatencyTag.textContent = `${data.latency_ms || 0} ms`;
      dom.visionAnalysisOutput.textContent = data.analysis || 'Inspección completada.';

      appendChatMessage({
        sender: 'Ultrón Visión',
        text: data.analysis,
        meta: `${data.latency_ms || 0} ms · ${providerLabel}`,
        isUser: false,
      });

      state.isProcessing = false;
      await speakResponse(data.analysis, 'es');
    } catch (err) {
      state.isProcessing = false;
      dom.visionAnalysisOutput.textContent = `No se pudo completar el análisis visual: ${err.message}`;
      setUltronState(state.voiceMode === 'handsfree' ? 'listening' : 'idle');
    } finally {
      dom.visionCaptureBtn.disabled = false;
      dom.visionCaptureBtn.innerHTML = `${SVG_ICONS.eyeScan}<span>Capturar y Analizar Pantalla</span>`;
    }
  }

  // ==========================================================================
  // 6. 21ST.DEV / RAYCAST COMMAND PALETTE MODAL (Ctrl + K)
  // ==========================================================================
  function renderCommandPaletteList() {
    if (!dom.cmdPaletteList) return;
    dom.cmdPaletteList.innerHTML = '';

    if (state.filteredCommands.length === 0) {
      const emptyEl = document.createElement('div');
      emptyEl.className = 'empty-row mono-sub';
      emptyEl.textContent = 'No se encontraron comandos que coincidan con tu búsqueda.';
      dom.cmdPaletteList.appendChild(emptyEl);
      return;
    }

    state.filteredCommands.forEach((item, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `cmd-palette-item ${idx === state.cmdPaletteSelectedIndex ? 'active' : ''}`;
      btn.setAttribute('role', 'option');
      btn.setAttribute('aria-selected', String(idx === state.cmdPaletteSelectedIndex));

      btn.innerHTML = `
        <div class="cmd-item-left">
          <span class="cmd-item-icon">${item.icon}</span>
          <div class="cmd-item-text">
            <span class="cmd-item-title">${item.title}</span>
            <span class="cmd-item-sub">${item.subtitle}</span>
          </div>
        </div>
        <span class="cmd-item-category">${item.category}</span>
      `;

      btn.addEventListener('mouseenter', () => {
        state.cmdPaletteSelectedIndex = idx;
        updateCommandPaletteActiveHighlight();
      });

      btn.addEventListener('click', () => {
        closeCommandPalette();
        item.action();
      });

      dom.cmdPaletteList.appendChild(btn);
    });
  }

  function updateCommandPaletteActiveHighlight() {
    if (!dom.cmdPaletteList) return;
    const items = dom.cmdPaletteList.querySelectorAll('.cmd-palette-item');
    items.forEach((el, idx) => {
      const isSelected = idx === state.cmdPaletteSelectedIndex;
      el.classList.toggle('active', isSelected);
      el.setAttribute('aria-selected', String(isSelected));
      if (isSelected) {
        el.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  function openCommandPalette() {
    if (!dom.cmdPaletteModal) return;
    state.cmdPaletteOpen = true;
    state.cmdPaletteSelectedIndex = 0;
    state.filteredCommands = [...COMMAND_PALETTE_ITEMS];
    dom.cmdPaletteModal.classList.remove('hidden');
    if (dom.cmdPaletteInput) {
      dom.cmdPaletteInput.value = '';
      renderCommandPaletteList();
      setTimeout(() => dom.cmdPaletteInput.focus(), 20);
    }
  }

  function closeCommandPalette() {
    if (!dom.cmdPaletteModal) return;
    state.cmdPaletteOpen = false;
    dom.cmdPaletteModal.classList.add('hidden');
  }

  function filterCommandPalette(query) {
    const q = String(query || '').toLowerCase().trim();
    if (!q) {
      state.filteredCommands = [...COMMAND_PALETTE_ITEMS];
    } else {
      state.filteredCommands = COMMAND_PALETTE_ITEMS.filter(
        (item) =>
          item.title.toLowerCase().includes(q) ||
          item.subtitle.toLowerCase().includes(q) ||
          item.category.toLowerCase().includes(q)
      );
    }
    state.cmdPaletteSelectedIndex = 0;
    renderCommandPaletteList();
  }

  // ==========================================================================
  // EVENT LISTENERS & INTERACTION BINDINGS
  // ==========================================================================
  function bindEvents() {
    // Slide-Over Drawer Toggles
    if (dom.btnToggleTelemetry) {
      dom.btnToggleTelemetry.addEventListener('click', () => toggleDrawer('telemetry'));
    }
    if (dom.btnToggleVision) {
      dom.btnToggleVision.addEventListener('click', () => toggleDrawer('vision'));
    }
    if (dom.closeTelemetryDrawerBtn) {
      dom.closeTelemetryDrawerBtn.addEventListener('click', closeDrawers);
    }
    if (dom.closeVisionDrawerBtn) {
      dom.closeVisionDrawerBtn.addEventListener('click', closeDrawers);
    }
    if (dom.drawerBackdrop) {
      dom.drawerBackdrop.addEventListener('click', closeDrawers);
    }

    // Mini-Pill Floating Waveform Mode (Jarvis Pro)
    if (dom.btnMiniPill) {
      dom.btnMiniPill.addEventListener('click', () => toggleMiniPillMode());
    }
    if (dom.miniPillExpandBtn) {
      dom.miniPillExpandBtn.addEventListener('click', () => toggleMiniPillMode(false));
    }
    if (dom.miniPillMicBtn) {
      dom.miniPillMicBtn.addEventListener('click', () => {
        ensureAudioContext();
        if (state.isSpeaking) {
          stopSpeakingBargeIn();
        } else if (state.voiceMode === 'muted') {
          setVoiceMode('handsfree');
        } else if (!state.recognitionRunning) {
          safeStartRecognition();
        }
      });
    }

    // Neural Voice Toggle
    dom.ttsToggleBtn.addEventListener('click', () => {
      state.ttsEnabled = !state.ttsEnabled;
      dom.ttsToggleBtn.classList.toggle('active', state.ttsEnabled);
      dom.ttsToggleBtn.setAttribute('aria-pressed', String(state.ttsEnabled));
      dom.ttsToggleLabel.textContent = state.ttsEnabled ? 'Voz Activa' : 'Silencio';
      if (!state.ttsEnabled && state.isSpeaking) {
        stopSpeakingBargeIn();
      }
    });

    // Command Palette Triggers (Topbar + Dock + Modal Close)
    if (dom.cmdPaletteTriggerBtn) {
      dom.cmdPaletteTriggerBtn.addEventListener('click', openCommandPalette);
    }
    if (dom.dockCmdPaletteBtn) {
      dom.dockCmdPaletteBtn.addEventListener('click', openCommandPalette);
    }
    if (dom.cmdPaletteCloseBtn) {
      dom.cmdPaletteCloseBtn.addEventListener('click', closeCommandPalette);
    }
    if (dom.cmdPaletteModal) {
      dom.cmdPaletteModal.addEventListener('click', (e) => {
        if (e.target === dom.cmdPaletteModal) {
          closeCommandPalette();
        }
      });
    }
    if (dom.cmdPaletteInput) {
      dom.cmdPaletteInput.addEventListener('input', (e) => {
        filterCommandPalette(e.target.value);
      });
    }

    // Manual Telemetry Refresh
    if (dom.refreshTelemetryBtn) {
      dom.refreshTelemetryBtn.addEventListener('click', () => {
        fetchTelemetry();
      });
    }

    // Language Selector (es-CO vs en-US Tutor)
    dom.langEsBtn.addEventListener('click', () => setSpeechLanguage('es-CO'));
    dom.langEnBtn.addEventListener('click', () => setSpeechLanguage('en-US'));

    // Voice Mode Selector
    dom.modeHandsfreeBtn.addEventListener('click', () => setVoiceMode('handsfree'));
    dom.modePttBtn.addEventListener('click', () => setVoiceMode('ptt'));
    dom.modeMutedBtn.addEventListener('click', () => setVoiceMode('muted'));

    // Flush Live Transcript Immediately
    dom.flushTranscriptBtn.addEventListener('click', () => {
      flushAccumulatedTranscript();
    });

    // Quick-Action Vision Button
    if (dom.visionQuickBtn) {
      dom.visionQuickBtn.addEventListener('click', () => {
        openDrawer('vision');
        runVisionAnalysis(
          '¿Qué hay en mi pantalla y qué recomendaciones técnicas tienes?',
          'general'
        );
      });
    }

    // Reactor Click -> Barge-In if speaking, or toggle mic
    const handleReactorAction = () => {
      ensureAudioContext();
      if (state.isSpeaking) {
        stopSpeakingBargeIn();
        return;
      }
      if (state.voiceMode === 'muted') {
        setVoiceMode('handsfree');
      } else if (!state.recognitionRunning) {
        safeStartRecognition();
      }
    };

    dom.reactorClickZone.addEventListener('click', handleReactorAction);
    dom.reactorStateBadge.addEventListener('click', () => {
      if (state.isSpeaking) stopSpeakingBargeIn();
    });
    dom.bargeInBtn.addEventListener('click', stopSpeakingBargeIn);

    // Push-to-Talk Button Hold (Mouse & Touch)
    const startPttHold = (e) => {
      if (e) e.preventDefault();
      if (state.voiceMode !== 'ptt' || state.pttActive) return;
      ensureAudioContext();
      if (state.isSpeaking) stopSpeakingBargeIn();
      state.pttActive = true;
      state.accumulatedTranscript = '';
      state.interimTranscript = '';
      dom.pttHoldBtn.classList.add('recording');
      dom.pttHoldBtn.innerHTML = `${SVG_ICONS.recordPulse}<span>Grabando... suelta para enviar tu orden</span>`;
      setUltronState('listening');
      updateLiveTranscriptDisplay(
        'Escuchando (mantén presionado todo el tiempo que necesites)...',
        false
      );
      safeStartRecognition();
    };

    const endPttHold = (e) => {
      if (e) e.preventDefault();
      if (!state.pttActive) return;
      state.pttActive = false;
      dom.pttHoldBtn.classList.remove('recording');
      dom.pttHoldBtn.innerHTML = `${SVG_ICONS.mic}<span>Mantén presionado aquí o [Espacio] para hablar sin cortes</span>`;
      safeStopRecognition();
      setTimeout(() => {
        flushAccumulatedTranscript();
      }, 220);
    };

    dom.pttHoldBtn.addEventListener('mousedown', startPttHold);
    window.addEventListener('mouseup', () => {
      if (state.pttActive) endPttHold();
    });
    dom.pttHoldBtn.addEventListener('touchstart', startPttHold, { passive: false });
    dom.pttHoldBtn.addEventListener('touchend', endPttHold, { passive: false });

    // Global Keyboard Shortcuts: Ctrl+K (Command Palette), Escape (Modals / Drawers / Barge-In) & Spacebar (PTT)
    window.addEventListener('keydown', (e) => {
      // Ctrl+K or Cmd+K toggles Command Palette
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (state.cmdPaletteOpen) {
          closeCommandPalette();
        } else {
          openCommandPalette();
        }
        return;
      }

      // Keyboard navigation when Command Palette is open
      if (state.cmdPaletteOpen) {
        if (e.key === 'Escape') {
          e.preventDefault();
          closeCommandPalette();
          return;
        }
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          if (state.filteredCommands.length > 0) {
            state.cmdPaletteSelectedIndex =
              (state.cmdPaletteSelectedIndex + 1) % state.filteredCommands.length;
            updateCommandPaletteActiveHighlight();
          }
          return;
        }
        if (e.key === 'ArrowUp') {
          e.preventDefault();
          if (state.filteredCommands.length > 0) {
            state.cmdPaletteSelectedIndex =
              (state.cmdPaletteSelectedIndex - 1 + state.filteredCommands.length) %
              state.filteredCommands.length;
            updateCommandPaletteActiveHighlight();
          }
          return;
        }
        if (e.key === 'Enter') {
          e.preventDefault();
          const chosen = state.filteredCommands[state.cmdPaletteSelectedIndex];
          if (chosen) {
            closeCommandPalette();
            chosen.action();
          }
          return;
        }
      }

      if (e.key === 'Escape') {
        if (!dom.lightboxModal.classList.contains('hidden')) {
          dom.lightboxModal.classList.add('hidden');
          return;
        }
        if (state.activeDrawer) {
          closeDrawers();
          return;
        }
        if (state.isSpeaking) {
          stopSpeakingBargeIn();
        }
      }

      const tag = (document.activeElement && document.activeElement.tagName) || '';
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

      if (e.code === 'Space' && !isTyping && state.voiceMode === 'ptt' && !e.repeat) {
        startPttHold(e);
      }
    });

    window.addEventListener('keyup', (e) => {
      const tag = (document.activeElement && document.activeElement.tagName) || '';
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
      if (e.code === 'Space' && !isTyping && state.voiceMode === 'ptt' && state.pttActive) {
        endPttHold(e);
      }
    });

    // Hybrid Command Form Submit
    dom.commandForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const val = dom.commandInput.value.trim();
      if (!val) return;
      dom.commandInput.value = '';
      sendCommand(val);
    });

    // Clear Chat Console
    dom.clearChatBtn.addEventListener('click', () => {
      dom.chatLog.innerHTML = '';
    });

    // Quick Action Pills
    dom.quickActionBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const cmd = btn.getAttribute('data-command');
        if (cmd) {
          if (btn.id === 'qa-diagnostico') {
            openDrawer('telemetry');
          }
          sendCommand(cmd);
        }
      });
    });

    // Multimodal Vision Studio Form
    dom.visionForm.addEventListener('submit', (e) => {
      e.preventDefault();
      runVisionAnalysis();
    });

    // Screenshot Lightbox Modal
    dom.visionImageWrapper.addEventListener('click', () => {
      if (dom.visionPreviewImg.src) {
        dom.lightboxModal.classList.remove('hidden');
      }
    });

    dom.lightboxCloseBtn.addEventListener('click', () => {
      dom.lightboxModal.classList.add('hidden');
    });

    dom.lightboxModal.addEventListener('click', (e) => {
      if (e.target === dom.lightboxModal) {
        dom.lightboxModal.classList.add('hidden');
      }
    });
  }

  // ==========================================================================
  // BOOTSTRAP ULTRÓN v5.1 SPATIAL OS
  // ==========================================================================
  function initHud() {
    bindEvents();
    startReactorLoop();
    initSpeechRecognition();

    // Clean, calm welcome greeting
    appendChatMessage({
      sender: 'Ultrón',
      text: 'Hola Sebastián. Estoy en línea y escuchando. Puedes hablarme con naturalidad, escribir abajo o usar los accesos rápidos.',
      isUser: false,
    });

    // Start real-time telemetry polling (every 2.5s)
    fetchTelemetry();
    setInterval(fetchTelemetry, TELEMETRY_POLL_MS);

    // Start continuous recognition automatically if allowed by browser
    if (state.voiceMode === 'handsfree') {
      safeStartRecognition();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHud);
  } else {
    initHud();
  }
})();
