/**
 * AeroPoint Quantum 3.0 — Spatial Neural HCI & Web Audio Engine
 */

document.addEventListener('DOMContentLoaded', () => {

  // =========================================================================
  // 1. Web Audio Spatial Sound Synthesizer (Zero External Dependencies)
  // =========================================================================
  class SpatialAudioSynthesizer {
    constructor() {
      this.ctx = null;
      this.enabled = true;
      this.volume = 0.65;
      this.theme = 'quantum';
      this.lastScrollSoundTime = 0;
      this.lastPinchSoundTime = 0;
    }

    init() {
      if (!this.ctx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
          this.ctx = new AudioContext();
        }
      }
      if (this.ctx && this.ctx.state === 'suspended') {
        this.ctx.resume();
      }
    }

    playPinch() {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      if (now - this.lastPinchSoundTime < 0.08) return;
      this.lastPinchSoundTime = now;

      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      if (this.theme === 'vision') {
        // Ethereal subtle glass tap
        osc.type = 'sine';
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(1400, now + 0.025);
        gain.gain.setValueAtTime(this.volume * 0.45, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.045);
      } else if (this.theme === 'bionic') {
        // Bionic tactile micro-relay servo click
        osc.type = 'square';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(90, now + 0.035);
        gain.gain.setValueAtTime(this.volume * 0.35, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.045);
      } else {
        // Quantum Cyber click (crisp tactile snap)
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(1200, now);
        osc.frequency.exponentialRampToValueAtTime(320, now + 0.035);
        gain.gain.setValueAtTime(this.volume * 0.6, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.045);
      }
    }

    playRightClick() {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      const osc1 = this.ctx.createOscillator();
      const osc2 = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      if (this.theme === 'vision') {
        // Apple Vision soft bell dual chime
        osc1.type = 'sine';
        osc2.type = 'sine';
        osc1.frequency.setValueAtTime(880, now);    // A5
        osc2.frequency.setValueAtTime(1108.7, now); // C#6
      } else if (this.theme === 'bionic') {
        // Dual mechanical relay trigger
        osc1.type = 'square';
        osc2.type = 'triangle';
        osc1.frequency.setValueAtTime(550, now);
        osc2.frequency.setValueAtTime(1100, now);
      } else {
        // Quantum octave harmonic ping
        osc1.type = 'sine';
        osc2.type = 'sine';
        osc1.frequency.setValueAtTime(880, now);   // A5
        osc2.frequency.setValueAtTime(1760, now);  // A6
      }

      gain.gain.setValueAtTime(this.volume * 0.35, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(this.ctx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 0.13);
      osc2.stop(now + 0.13);
    }

    playDragStart() {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      if (this.theme === 'bionic') {
        // Heavy hydraulic lock buzz
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(65, now);
        osc.frequency.exponentialRampToValueAtTime(130, now + 0.15);
      } else if (this.theme === 'vision') {
        // Smooth ethereal swell
        osc.type = 'sine';
        osc.frequency.setValueAtTime(110, now);
        osc.frequency.exponentialRampToValueAtTime(220, now + 0.15);
      } else {
        // Quantum bass warp
        osc.type = 'sine';
        osc.frequency.setValueAtTime(70, now);
        osc.frequency.exponentialRampToValueAtTime(140, now + 0.15);
      }

      gain.gain.setValueAtTime(this.volume * 0.65, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.20);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 0.21);
    }

    playScrollTick() {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      if (now - this.lastScrollSoundTime < 0.05) return;
      this.lastScrollSoundTime = now;

      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      if (this.theme === 'vision') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(2200, now);
        osc.frequency.exponentialRampToValueAtTime(900, now + 0.012);
      } else if (this.theme === 'bionic') {
        osc.type = 'square';
        osc.frequency.setValueAtTime(1400, now);
        osc.frequency.exponentialRampToValueAtTime(200, now + 0.012);
      } else {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(1800, now);
        osc.frequency.exponentialRampToValueAtTime(400, now + 0.012);
      }

      gain.gain.setValueAtTime(this.volume * 0.25, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.015);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 0.018);
    }

    playRadialChime() {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      // 4-voice polyphonic visionOS harmonic chord (C5, E5, G5, B5)
      const freqs = [523.25, 659.25, 783.99, 987.77];
      freqs.forEach((f, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(f, now + idx * 0.025);

        gain.gain.setValueAtTime(this.volume * 0.2, now + idx * 0.025);
        gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.025 + 0.25);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now + idx * 0.025);
        osc.stop(now + idx * 0.025 + 0.26);
      });
    }

    playLaserFx() {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(2400, now);
      osc.frequency.exponentialRampToValueAtTime(600, now + 0.09);

      gain.gain.setValueAtTime(this.volume * 0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 0.11);
    }

    playShutterFx() {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      [0, 0.045].forEach((offset, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(idx === 0 ? 1800 : 1200, now + offset);
        osc.frequency.exponentialRampToValueAtTime(300, now + offset + 0.035);
        gain.gain.setValueAtTime(this.volume * 0.45, now + offset);
        gain.gain.exponentialRampToValueAtTime(0.001, now + offset + 0.04);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now + offset);
        osc.stop(now + offset + 0.045);
      });
    }

    playAirClap() {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(340, now);
      osc.frequency.exponentialRampToValueAtTime(75, now + 0.08);

      gain.gain.setValueAtTime(this.volume * 0.75, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.09);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 0.095);
    }

    playPianoNote(noteName) {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const freqs = {
        'C4': 261.63,
        'D4': 293.66,
        'E4': 329.63,
        'G4': 392.00,
        'A4': 440.00
      };
      const freq = freqs[noteName] || 440.0;
      const now = this.ctx.currentTime;

      [1.0, 2.01].forEach((mult, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = idx === 0 ? 'sine' : 'triangle';
        osc.frequency.setValueAtTime(freq * mult, now);
        const amp = (this.volume * (idx === 0 ? 0.45 : 0.20));
        gain.gain.setValueAtTime(amp, now);
        gain.gain.exponentialRampToValueAtTime(0.0005, now + (idx === 0 ? 0.35 : 0.18));
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 0.36);
      });
    }

    playZoom(isZoomIn = true) {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      const f1 = isZoomIn ? 320 : 640;
      const f2 = isZoomIn ? 640 : 320;
      osc.frequency.setValueAtTime(f1, now);
      osc.frequency.exponentialRampToValueAtTime(f2, now + 0.07);

      gain.gain.setValueAtTime(this.volume * 0.35, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 0.085);
    }

    playPitchGliss(isUp = true) {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';

      const startFreq = isUp ? 520 : 780;
      const endFreq = isUp ? 880 : 440;
      osc.frequency.setValueAtTime(startFreq, now);
      osc.frequency.exponentialRampToValueAtTime(endFreq, now + 0.12);

      gain.gain.setValueAtTime(this.volume * 0.4, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.15);
    }
  }

  const soundSynth = new SpatialAudioSynthesizer();
  window.addEventListener('click', () => soundSynth.init(), { once: true });

  // =========================================================================
  // 2. Navigation Dock View Switching
  // =========================================================================
  const dockButtons = document.querySelectorAll('.dock-btn');
  const quantumViews = document.querySelectorAll('.quantum-view');

  dockButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetViewId = btn.getAttribute('data-view');
      dockButtons.forEach(b => b.classList.remove('active'));
      quantumViews.forEach(v => v.classList.remove('active'));

      btn.classList.add('active');
      const targetView = document.getElementById(targetViewId);
      if (targetView) {
        targetView.classList.add('active');
      }
      soundSynth.playPinch();
    });
  });

  // =========================================================================
  // 3. Elements Mapping & State
  // =========================================================================
  const cameraSelect = document.getElementById('camera-select');
  const btnRefreshCams = document.getElementById('btn-refresh-cams');
  const masterControlSwitch = document.getElementById('master-control-switch');
  const controlStateSub = document.getElementById('control-state-sub');
  const btnSafetyPause = document.getElementById('btn-safety-pause');
  const pauseIndicator = document.getElementById('pause-indicator');
  const pauseBtnText = document.getElementById('pause-btn-text');

  // Viewport & Stream
  const streamImg = document.getElementById('video-stream');
  const loadingOverlay = document.getElementById('camera-loading-overlay');

  // Telemetry Badges
  const badgeFps = document.getElementById('badge-fps');
  const badgeLatency = document.getElementById('badge-latency');
  const badgeSignal = document.getElementById('badge-signal');
  const dotSignal = document.getElementById('dot-signal');
  const badgeCpu = document.getElementById('badge-cpu');
  const badgeAnchor = document.getElementById('badge-anchor');
  const pillAnchorStatus = document.getElementById('pill-anchor-status');
  const pillHandsMode = document.getElementById('pill-hands-mode');
  const badgeHandsIcon = document.getElementById('badge-hands-icon');
  const badgeHandsMode = document.getElementById('badge-hands-mode');
  const pillLighting = document.getElementById('pill-lighting');
  const badgeLightingIcon = document.getElementById('badge-lighting-icon');
  const badgeLightingText = document.getElementById('badge-lighting-text');
  const pillVelocity = document.getElementById('pill-velocity');
  const badgeVelocity = document.getElementById('badge-velocity');
  const pillDistance = document.getElementById('pill-distance');
  const badgeDistance = document.getElementById('badge-distance');
  const pillPowerMode = document.getElementById('pill-power-mode');
  const badgePowerIcon = document.getElementById('badge-power-icon');
  const badgePowerText = document.getElementById('badge-power-text');
  const trackingStatusBadge = document.getElementById('tracking-status-badge');

  // Gesture Banner & Pinch Gauge
  const bannerIcon = document.getElementById('gesture-banner-icon');
  const bannerTitle = document.getElementById('gesture-banner-title');
  const bannerSub = document.getElementById('gesture-banner-sub');
  const pinchBarFill = document.getElementById('pinch-bar-fill');
  const pinchPercentText = document.getElementById('pinch-percent-text');
  const gaugeLabelTitle = document.getElementById('gauge-label-title');

  // Precision Sliders & Toggles
  const sliderSensitivity = document.getElementById('slider-sensitivity');
  const valSensitivity = document.getElementById('val-sensitivity');
  const sliderSmooth = document.getElementById('slider-smooth');
  const valSmooth = document.getElementById('val-smooth');
  const sliderDeadzone = document.getElementById('slider-deadzone');
  const valDeadzone = document.getElementById('val-deadzone');
  const sliderReach = document.getElementById('slider-reach');
  const valReach = document.getElementById('val-reach');
  const switchAnchor = document.getElementById('switch-anchor');
  const switchAcceleration = document.getElementById('switch-acceleration');
  const switchCornerSnap = document.getElementById('switch-corner-snap');
  const switchWindowSnap = document.getElementById('switch-window-snap');
  const switchDistanceAdaptation = document.getElementById('switch-distance-adaptation');
  const switchLaser = document.getElementById('switch-laser');
  const switchClahe = document.getElementById('switch-clahe');
  const switchAmbientTheme = document.getElementById('switch-ambient-theme');
  const switchWristClock = document.getElementById('switch-wrist-clock');
  const switchAirPiano = document.getElementById('switch-air-piano');
  const valLaserStatus = document.getElementById('val-laser-status');
  const btnProfCad = document.getElementById('btn-prof-cad');
  const btnProfDesktop = document.getElementById('btn-prof-desktop');
  const btnProfGaming = document.getElementById('btn-prof-gaming');
  const badgeActiveProfile = document.getElementById('badge-active-profile');

  // Bimanual Controls
  const switchTwoHands = document.getElementById('switch-two-hands');
  const btnDomRight = document.getElementById('btn-dom-right');
  const btnDomLeft = document.getElementById('btn-dom-left');

  // Click Mode Buttons
  const btnModeThumb = document.getElementById('btn-mode-thumb');
  const btnModePinch = document.getElementById('btn-mode-pinch');
  const btnModeAirTap = document.getElementById('btn-mode-airtap');
  const modeHintText = document.getElementById('mode-hint-text');

  // Presentation & Air-Swipe Switch
  const switchPresentation = document.getElementById('switch-presentation');
  const switchSpotlight = document.getElementById('switch-spotlight');
  const switchVirtualSurface = document.getElementById('switch-virtual-surface');
  const btnCalibrateSurface = document.getElementById('btn-calibrate-surface');
  const switchScreenLoupe = document.getElementById('switch-screen-loupe');

  // Legacy Gestures Switch
  const switchLegacyGestures = document.getElementById('switch-legacy-gestures');

  // iPhone Sensor Elements
  const tabBtnWebcam = document.getElementById('tab-btn-webcam');
  const tabBtnIphone = document.getElementById('tab-btn-iphone');
  const badgeIphoneConn = document.getElementById('badge-iphone-conn');
  const valIphoneSensor = document.getElementById('val-iphone-sensor');
  const valIphonePing = document.getElementById('val-iphone-ping');
  const valIphoneBattery = document.getElementById('val-iphone-battery');
  const valIphoneDepth = document.getElementById('val-iphone-depth');
  const valIphoneDepthDisplay = document.getElementById('val-iphone-depth-display');
  const barIphoneDepth = document.getElementById('bar-iphone-depth');
  const btnToggleMirror = document.getElementById('btn-toggle-mirror');
  const txtMirrorStatus = document.getElementById('txt-mirror-status');
  const btnCopyUrl = document.getElementById('btn-copy-url');
  const mobileUrlText = document.getElementById('mobile-url-text');
  const btnOpenIpaFolder = document.getElementById('btn-open-ipa-folder');
  btnOpenIpaFolder?.addEventListener('click', () => {
    fetch('/api/open_ipa_folder', { method: 'POST' }).catch(() => {});
    soundSynth.playClick();
    flashActionCapsule('📂', 'Папка с IPA открыта');
  });

  // Audio Controls
  const switchSoundMaster = document.getElementById('switch-sound-master');
  const sliderSoundVolume = document.getElementById('slider-sound-volume');
  const valSoundVolume = document.getElementById('val-sound-volume');

  // Sound Test Buttons
  document.getElementById('snd-test-click')?.addEventListener('click', () => soundSynth.playPinch());
  document.getElementById('snd-test-right')?.addEventListener('click', () => soundSynth.playRightClick());
  document.getElementById('snd-test-drag')?.addEventListener('click', () => soundSynth.playDragStart());
  document.getElementById('snd-test-scroll')?.addEventListener('click', () => soundSynth.playScrollTick());
  document.getElementById('snd-test-dial')?.addEventListener('click', () => soundSynth.playRadialChime());
  document.getElementById('snd-test-laser')?.addEventListener('click', () => soundSynth.playLaserFx());

  // Sound Themes
  document.querySelectorAll('.sound-theme-picker .seg-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sound-theme-picker .seg-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      soundSynth.theme = btn.getAttribute('data-theme') || 'quantum';
      soundSynth.playRadialChime();
      postSettings({ sound_theme: soundSynth.theme });
    });
  });

  // Sound Volume & Toggle
  sliderSoundVolume?.addEventListener('input', (e) => {
    const vol = parseInt(e.target.value) / 100.0;
    soundSynth.volume = vol;
    valSoundVolume.textContent = `${e.target.value}%`;
    postSettings({ sound_volume: vol });
  });

  switchSoundMaster?.addEventListener('change', (e) => {
    soundSynth.enabled = e.target.checked;
    postSettings({ sound_enabled: e.target.checked });
  });

  // =========================================================================
  // 4. Interactive Radial Quick-Dial (Pie Menu) Logic
  // =========================================================================
  const wheelSectors = document.querySelectorAll('.wheel-sector');
  const actionListItems = document.querySelectorAll('.action-item');

  function triggerRadialAction(actionName) {
    if (actionName.includes('up')) {
      soundSynth.playPitchGliss(true);
    } else if (actionName.includes('down')) {
      soundSynth.playPitchGliss(false);
    } else {
      soundSynth.playRadialChime();
    }
    flashActionCapsule('✨', `Диск: ${actionName}`);
    fetch('/api/radial/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: actionName })
    }).catch(err => console.error('[!] Radial action failed:', err));
  }

  wheelSectors.forEach(sec => {
    sec.addEventListener('click', () => {
      const act = sec.getAttribute('data-action');
      if (act) {
        sec.classList.add('active-sector');
        setTimeout(() => sec.classList.remove('active-sector'), 300);
        triggerRadialAction(act);
      }
    });
  });

  actionListItems.forEach(item => {
    const testBtn = item.querySelector('.test-btn');
    const act = item.getAttribute('data-action');
    if (testBtn && act) {
      testBtn.addEventListener('click', () => triggerRadialAction(act));
    }
  });

  document.getElementById('btn-open-radial-modal')?.addEventListener('click', () => {
    fetch('/api/radial/toggle', { method: 'POST' })
      .then(r => r.json())
      .then(d => {
        soundSynth.playRadialChime();
        flashActionCapsule('⭕', d.radial_open ? 'Quick-Dial в эфире: ВКЛ (Наведите руку на сектор)' : 'Quick-Dial: ЗАКРЫТ');
      })
      .catch(() => {
        const radialDockBtn = document.querySelector('.dock-btn[data-view="view-radial"]');
        if (radialDockBtn) radialDockBtn.click();
      });
  });

  // =========================================================================
  // 5. Essential 5 Gestures Dictionary & Visual Active States
  // =========================================================================
  const coreGestureCards = {
    'HOVER': { id: 'card-hover', title: 'Наведение', desc: 'Плавное позиционирование курсора', icon: '☝️' },
    'HOVER (MOVE)': { id: 'card-hover', title: 'Наведение', desc: 'Плавное позиционирование курсора', icon: '☝️' },
    'PINCH (LEFT CLICK)': { id: 'card-pinch', title: 'Левый клик (Щипок)', desc: 'Нажатие левой кнопки мыши', icon: '🤏' },
    'THUMB BEND (LEFT CLICK)': { id: 'card-pinch', title: 'Левый клик (Сгиб)', desc: 'Стабильный клик сгибом пальца', icon: '👍' },
    'DRAG': { id: 'card-drag', title: 'Зажатие (Drag)', desc: 'Удержание щипка / кулака для переноса', icon: '✊' },
    'DRAG & DROP': { id: 'card-drag', title: 'Зажатие (Drag)', desc: 'Удержание щипка / кулака для переноса', icon: '✊' },
    'RIGHT CLICK': { id: 'card-right', title: 'Правый клик', desc: 'Касание средним пальцем', icon: '👌' },
    'SCROLL': { id: 'card-scroll', title: 'Прокрутка', desc: 'Два пальца вверх / вниз', icon: '✌️' },
    'PAUSE': { id: 'card-pause', title: 'Защитная пауза', desc: 'Ладонь раскрыта (5 пальцев)', icon: '🖐️' },
    'PAUSE (NEUTRAL)': { id: 'card-pause', title: 'Защитная пауза', desc: 'Ладонь раскрыта (5 пальцев)', icon: '🖐️' },
    'NO HAND': { id: null, title: 'Поиск руки', desc: 'Поместите ладонь перед камерой', icon: '🔍' }
  };

  let previousGesture = 'NO HAND';

  const actionCapsule = document.getElementById('action-capsule');
  const actionCapsuleIcon = document.getElementById('action-capsule-icon');
  const actionCapsuleText = document.getElementById('action-capsule-text');
  let capsuleTimer = null;

  function flashActionCapsule(icon, text, soundFn = null) {
    if (!actionCapsule) return;
    if (actionCapsuleIcon) actionCapsuleIcon.textContent = icon;
    if (actionCapsuleText) actionCapsuleText.textContent = text;
    actionCapsule.classList.add('show');
    if (soundFn) soundFn();

    clearTimeout(capsuleTimer);
    capsuleTimer = setTimeout(() => {
      actionCapsule.classList.remove('show');
    }, 1300);
  }

  function updateCoreGestureHighlight(gestureName) {
    const cleanName = (gestureName || 'NO HAND').trim();
    let info = coreGestureCards[cleanName];
    if (!info) {
      if (cleanName.includes('PINCH') || cleanName.includes('THUMB')) info = coreGestureCards['PINCH (LEFT CLICK)'];
      else if (cleanName.includes('RIGHT')) info = coreGestureCards['RIGHT CLICK'];
      else if (cleanName.includes('SCROLL')) info = coreGestureCards['SCROLL'];
      else if (cleanName.includes('DRAG')) info = coreGestureCards['DRAG'];
      else if (cleanName.includes('PAUSE')) info = coreGestureCards['PAUSE'];
      else if (cleanName.includes('HOVER')) info = coreGestureCards['HOVER'];
      else info = coreGestureCards['NO HAND'];
    }

    // Audio triggers & Dynamic Action Capsule on gesture transition
    if (cleanName !== previousGesture) {
      if (cleanName.includes('PINCH') || cleanName.includes('THUMB')) soundSynth.playPinch();
      else if (cleanName.includes('RIGHT')) soundSynth.playRightClick();
      else if (cleanName.includes('DRAG')) soundSynth.playDragStart();

      if (cleanName !== 'NO HAND' && !cleanName.includes('HOVER')) {
        flashActionCapsule(info.icon, info.title);
      }
      previousGesture = cleanName;
    }

    // Update banner
    if (bannerIcon) bannerIcon.textContent = info.icon;
    if (bannerTitle) bannerTitle.textContent = info.title;
    if (bannerSub) bannerSub.textContent = info.desc;

    // Highlight active card
    document.querySelectorAll('.core-gesture-card').forEach(c => c.classList.remove('active-pose'));
    if (info.id) {
      const cardEl = document.getElementById(info.id);
      if (cardEl) cardEl.classList.add('active-pose');
    }

    // Process coach training
    processCoachGesture(cleanName);
  }

  // Interactive Gesture Coach Steps
  const coachSteps = [
    { name: '1. Наведение (☝️)', hint: 'Вытяните указательный палец в сторону камеры, согнув остальные пальцы.', test: (g) => g.includes('HOVER') },
    { name: '2. Левый клик (🤏 / 👍)', hint: 'Сожмите большой и указательный пальцы (или согните большой палец).', test: (g) => g.includes('PINCH') || g.includes('THUMB') || g.includes('AIR_TAP') },
    { name: '3. Зажатие / Перетаскивание (✊)', hint: 'Сожмите кулак или удерживайте щипок дольше 0.22 сек.', test: (g) => g.includes('DRAG') },
    { name: '4. Правый клик (👌)', hint: 'Сомкните кончики большого и среднего пальцев.', test: (g) => g.includes('RIGHT') },
    { name: '5. Прокрутка вверх/вниз (✌️)', hint: 'Поднимите указательный и средний пальцы вместе вверх («знак V»).', test: (g) => g.includes('SCROLL') },
    { name: 'Защитная пауза (🖐️)', hint: 'Полностью раскройте ладонь (5 пальцев), чтобы зафиксировать курсор.', test: (g) => g.includes('PAUSE') }
  ];

  let currentCoachIdx = 0;
  let coachHoldFrames = 0;
  const coachTargetName = document.getElementById('coach-target-name');
  const coachHint = document.getElementById('coach-hint');
  const coachMatchPct = document.getElementById('coach-match-pct');
  const coachStatusText = document.getElementById('coach-status-text');
  const btnCoachNext = document.getElementById('btn-coach-next');

  function updateCoachUI() {
    const step = coachSteps[currentCoachIdx];
    if (coachTargetName) coachTargetName.textContent = `Попробуйте жест: ${step.name}`;
    if (coachHint) coachHint.textContent = step.hint;
    if (coachMatchPct) {
      coachMatchPct.textContent = '0%';
      coachMatchPct.parentElement.classList.remove('success');
    }
    if (coachStatusText) coachStatusText.textContent = 'Ожидание жеста...';
    coachHoldFrames = 0;
  }

  btnCoachNext?.addEventListener('click', () => {
    currentCoachIdx = (currentCoachIdx + 1) % coachSteps.length;
    updateCoachUI();
    soundSynth.playClick();
  });

  function processCoachGesture(cleanName) {
    if (!coachTargetName) return;
    const step = coachSteps[currentCoachIdx];
    const isMatching = step.test(cleanName);

    if (isMatching) {
      coachHoldFrames = Math.min(30, coachHoldFrames + 2);
    } else {
      coachHoldFrames = Math.max(0, coachHoldFrames - 1);
    }

    const pct = Math.round((coachHoldFrames / 30) * 100);
    if (coachMatchPct) {
      coachMatchPct.textContent = `${pct}%`;
      if (pct >= 100) {
        coachMatchPct.parentElement.classList.add('success');
        if (coachStatusText) coachStatusText.textContent = '✓ Идеально!';
        if (coachHoldFrames === 30) {
          soundSynth.playChord();
          flashActionCapsule('✨', `Жест освоен: ${step.name}`);
          setTimeout(() => {
            currentCoachIdx = (currentCoachIdx + 1) % coachSteps.length;
            updateCoachUI();
          }, 900);
        }
      } else if (pct > 0) {
        if (coachStatusText) coachStatusText.textContent = 'Удерживайте...';
      } else {
        if (coachStatusText) coachStatusText.textContent = 'Ожидание жеста...';
      }
    }
  }

  // =========================================================================
  // 6. Settings Synchronization (POST /api/settings)
  // =========================================================================
  function postSettings(settingsObj) {
    fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settingsObj)
    }).catch(err => console.error('[!] Error updating settings:', err));
  }

  // Sliders
  sliderSensitivity?.addEventListener('input', (e) => {
    valSensitivity.textContent = `${e.target.value}x`;
    postSettings({ sensitivity: parseFloat(e.target.value) });
  });

  sliderSmooth?.addEventListener('input', (e) => {
    valSmooth.textContent = e.target.value;
    postSettings({ smoothing_alpha: parseFloat(e.target.value) });
  });

  sliderDeadzone?.addEventListener('input', (e) => {
    valDeadzone.textContent = `${e.target.value} px`;
    postSettings({ deadzone_radius: parseFloat(e.target.value) });
  });

  sliderReach?.addEventListener('input', (e) => {
    const margin = parseInt(e.target.value) / 100.0;
    valReach.textContent = `${e.target.value}%`;
    postSettings({ margin_x: margin, margin_y: margin + 0.02 });
  });

  // Toggles
  switchAnchor?.addEventListener('change', (e) => postSettings({ enable_anchor: e.target.checked }));
  switchAcceleration?.addEventListener('change', (e) => postSettings({ enable_acceleration: e.target.checked }));
  switchCornerSnap?.addEventListener('change', (e) => postSettings({ enable_corner_snap: e.target.checked }));
  switchWindowSnap?.addEventListener('change', (e) => postSettings({ enable_window_snap_zones: e.target.checked }));
  switchDistanceAdaptation?.addEventListener('change', (e) => postSettings({ enable_distance_adaptation: e.target.checked }));
  switchClahe?.addEventListener('change', (e) => postSettings({ use_clahe: e.target.checked }));
  switchAmbientTheme?.addEventListener('change', (e) => {
    soundSynth.playLaserFx();
    postSettings({ ambient_theme_auto_sync: e.target.checked });
    flashActionCapsule('🌗', e.target.checked ? 'Авто-тема освещения ВКЛ' : 'Авто-тема освещения ВЫКЛ');
  });
  switchLegacyGestures?.addEventListener('change', (e) => postSettings({ enable_legacy_shortcuts: e.target.checked }));
  switchWristClock?.addEventListener('change', (e) => {
    soundSynth.playLaserFx();
    postSettings({ show_wrist_hud_clock: e.target.checked });
    flashActionCapsule('⌚', e.target.checked ? 'Часы на запястье ВКЛ' : 'Часы на запястье ВЫКЛ');
  });

  switchAirPiano?.addEventListener('change', (e) => {
    soundSynth.playPianoNote('C4');
    postSettings({ enable_air_piano: e.target.checked });
    flashActionCapsule('🎹', e.target.checked ? 'Air-Piano ВКЛ' : 'Air-Piano ВЫКЛ');
  });

  document.querySelectorAll('.piano-test-key').forEach(btn => {
    btn.addEventListener('click', () => {
      const note = btn.getAttribute('data-note');
      if (note) {
        soundSynth.playPianoNote(note);
        flashActionCapsule('🎵', `Нота: ${note}`);
      }
    });
  });
  
  switchLaser?.addEventListener('change', (e) => {
    valLaserStatus.textContent = e.target.checked ? 'ЛАЗЕР ВКЛ' : 'Обычный';
    valLaserStatus.style.color = e.target.checked ? '#ff007f' : 'var(--aero-cyan)';
    soundSynth.playLaserFx();
    flashActionCapsule('🎯', e.target.checked ? 'Лазерный прицел ВКЛ' : 'Обычный курсор');
    postSettings({ laser_pointer_mode: e.target.checked });
  });

  // Laser Pointer Palette Selection (Cyan, Green, Red, Gold)
  document.querySelectorAll('.laser-color-pill .seg-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.laser-color-pill .seg-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const color = btn.getAttribute('data-laser-color');
      soundSynth.playLaserFx();
      fetch('/api/laser/color', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ color })
      }).catch(() => {});
      flashActionCapsule('🎨', `Цвет лазера: ${btn.textContent.trim()}`);
    });
  });

  // Precision Profile Presets (CAD / Desktop / Gaming)
  function updateProfileButtons(profile) {
    [btnProfCad, btnProfDesktop, btnProfGaming].forEach(btn => btn?.classList.remove('active'));
    if (profile === 'cad') {
      btnProfCad?.classList.add('active');
      if (badgeActiveProfile) badgeActiveProfile.textContent = 'CAD СВЕРХТОЧНОСТЬ';
      if (sliderSensitivity && valSensitivity) { sliderSensitivity.value = "1.3"; valSensitivity.textContent = "1.3x"; }
      if (sliderSmooth && valSmooth) { sliderSmooth.value = "0.15"; valSmooth.textContent = "0.15"; }
      if (sliderDeadzone && valDeadzone) { sliderDeadzone.value = "4.2"; valDeadzone.textContent = "4.2 px"; }
    } else if (profile === 'gaming') {
      btnProfGaming?.classList.add('active');
      if (badgeActiveProfile) badgeActiveProfile.textContent = 'ЭКШЕН ТУРБО';
      if (sliderSensitivity && valSensitivity) { sliderSensitivity.value = "2.6"; valSensitivity.textContent = "2.6x"; }
      if (sliderSmooth && valSmooth) { sliderSmooth.value = "0.70"; valSmooth.textContent = "0.70"; }
      if (sliderDeadzone && valDeadzone) { sliderDeadzone.value = "1.8"; valDeadzone.textContent = "1.8 px"; }
    } else {
      btnProfDesktop?.classList.add('active');
      if (badgeActiveProfile) badgeActiveProfile.textContent = 'БАЛАНС';
      if (sliderSensitivity && valSensitivity) { sliderSensitivity.value = "1.8"; valSensitivity.textContent = "1.8x"; }
      if (sliderSmooth && valSmooth) { sliderSmooth.value = "0.30"; valSmooth.textContent = "0.30"; }
      if (sliderDeadzone && valDeadzone) { sliderDeadzone.value = "3.5"; valDeadzone.textContent = "3.5 px"; }
    }
  }

  btnProfCad?.addEventListener('click', () => {
    updateProfileButtons('cad');
    soundSynth.playClick();
    flashActionCapsule('🎯', 'Пресет: CAD / Дизайн (Сверхточность)');
    postSettings({ precision_profile: 'cad', sensitivity: 1.3, deadzone_radius: 4.2 });
  });

  btnProfDesktop?.addEventListener('click', () => {
    updateProfileButtons('desktop');
    soundSynth.playClick();
    flashActionCapsule('🌐', 'Пресет: Базовый десктоп');
    postSettings({ precision_profile: 'desktop', sensitivity: 1.8, deadzone_radius: 3.5 });
  });

  btnProfGaming?.addEventListener('click', () => {
    updateProfileButtons('gaming');
    soundSynth.playClick();
    flashActionCapsule('⚡', 'Пресет: Экшен & Презентации (Турбо)');
    postSettings({ precision_profile: 'gaming', sensitivity: 2.6, deadzone_radius: 1.8 });
  });

  // Kinetic Acceleration Curve Selector & Live Canvas
  const curveSelectorPill = document.querySelector('.curve-selector-pill');
  const badgeActiveCurve = document.getElementById('badge-active-curve');
  const accelCanvas = document.getElementById('accel-curve-canvas');
  let currentActiveCurve = 'exponential';
  let currentLiveVelocity = 0.0;
  let currentLiveGain = 1.0;

  function updateCurveButtons(curve) {
    currentActiveCurve = curve;
    document.querySelectorAll('.curve-selector-pill .seg-btn').forEach(btn => {
      if (btn.getAttribute('data-curve') === curve) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
    if (badgeActiveCurve) {
      if (curve === 'sigmoid') badgeActiveCurve.textContent = 'SIGMOID S';
      else if (curve === 'linear') badgeActiveCurve.textContent = 'LINEAR 1:1';
      else badgeActiveCurve.textContent = 'POWER EXP';
    }
    drawAccelCurve();
  }

  document.querySelectorAll('.curve-selector-pill .seg-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const curve = btn.getAttribute('data-curve') || 'exponential';
      window._curveUserInteracted = true;
      updateCurveButtons(curve);
      soundSynth.playRadialChime();
      flashActionCapsule('📈', `Кривая: ${curve.toUpperCase()}`);
      postSettings({ acceleration_curve: curve });
    });
  });

  function drawAccelCurve() {
    if (!accelCanvas) return;
    const ctx = accelCanvas.getContext('2d');
    if (!ctx) return;
    const w = accelCanvas.width;
    const h = accelCanvas.height;
    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.lineWidth = 1;
    for (let x = 40; x < w; x += 60) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 20; y < h; y += 30) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Baseline Gain 1.0 line
    const baselineY = h - (1.0 / 2.0) * (h - 24) - 12;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.20)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(35, baselineY);
    ctx.lineTo(w - 10, baselineY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.font = '10px Inter, sans-serif';
    ctx.fillText('1.0x', 8, baselineY + 3);

    // Compute gain function
    function evalGain(v) {
      if (currentActiveCurve === 'linear') return 1.0;
      if (currentActiveCurve === 'sigmoid') {
        const z = Math.max(-10.0, Math.min(10.0, (v - 140.0) / 45.0));
        return 0.70 + 0.85 / (1.0 + Math.exp(-z));
      }
      if (v < 80.0) return 0.75 + 0.25 * (v / 80.0);
      if (v > 180.0) return Math.min(1.60, 1.0 + 0.60 * ((v - 180.0) / 400.0));
      return 1.0;
    }

    // Plot Curve
    ctx.beginPath();
    ctx.strokeStyle = '#00f2fe';
    ctx.lineWidth = 2.5;
    ctx.shadowColor = 'rgba(0, 242, 254, 0.6)';
    ctx.shadowBlur = 8;
    const maxV = 600.0;
    const maxGain = 1.8;
    for (let px = 35; px <= w - 10; px++) {
      const v = ((px - 35) / (w - 45)) * maxV;
      const g = evalGain(v);
      const py = h - 12 - (g / maxGain) * (h - 24);
      if (px === 35) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Live Velocity Pulse Dot
    const liveV = Math.max(0.0, Math.min(maxV, currentLiveVelocity));
    const dotX = 35 + (liveV / maxV) * (w - 45);
    const dotG = evalGain(liveV);
    const dotY = h - 12 - (dotG / maxGain) * (h - 24);

    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(dotX, dotY, 4.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = '#00f2fe';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(dotX, dotY, 8.5, 0, Math.PI * 2);
    ctx.stroke();

    // Live readout text
    ctx.fillStyle = '#00f2fe';
    ctx.font = '10px Inter, sans-serif';
    ctx.fillText(`${Math.round(liveV)} px/s (${dotG.toFixed(2)}x)`, Math.min(w - 95, Math.max(35, dotX - 25)), Math.max(16, dotY - 12));
  }

  // Master Switch & Pause
  masterControlSwitch?.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    controlStateSub.textContent = isChecked ? 'Включено' : 'Выключено';
    controlStateSub.style.color = isChecked ? '#00e676' : 'var(--text-tertiary)';
    soundSynth.playPinch();
    postSettings({ control_enabled: isChecked });
  });

  btnSafetyPause?.addEventListener('click', () => {
    const isPaused = pauseIndicator.classList.contains('paused');
    const newPauseState = !isPaused;
    if (newPauseState) {
      pauseIndicator.classList.add('paused');
      pauseBtnText.textContent = 'Возобновить';
      flashActionCapsule('⏸️', 'Пауза управления');
    } else {
      pauseIndicator.classList.remove('paused');
      pauseBtnText.textContent = 'Пауза';
      flashActionCapsule('▶️', 'Управление возобновлено');
    }
    soundSynth.playPinch();
    postSettings({ manual_pause: newPauseState });
  });

  // Zen Mode (Fullscreen Spatial HUD) Toggle
  const btnZenMode = document.getElementById('btn-zen-mode');
  const zenExitPill = document.getElementById('zen-exit-pill');

  function toggleZenMode() {
    const isZen = document.body.classList.toggle('zen-mode');
    soundSynth.playRadialChime();
    flashActionCapsule('🧘', isZen ? 'Zen HUD: Полный экран' : 'Оконный режим');

    if (isZen) {
      if (document.documentElement.requestFullscreen && !document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      }
    } else {
      if (document.exitFullscreen && document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }
    }
  }

  btnZenMode?.addEventListener('click', toggleZenMode);
  zenExitPill?.addEventListener('click', toggleZenMode);

  window.addEventListener('keydown', (e) => {
    if (e.key === 'F11') {
      e.preventDefault();
      toggleZenMode();
    } else if (e.key === 'Escape' && document.body.classList.contains('zen-mode')) {
      toggleZenMode();
    }
  });

  // Click Mode (Thumb Bend vs Pinch vs Air-Tap)
  btnModeThumb?.addEventListener('click', () => {
    btnModeThumb.classList.add('active');
    btnModePinch?.classList.remove('active');
    btnModeAirTap?.classList.remove('active');
    modeHintText.innerHTML = 'Наведите курсор указательным пальцем и <strong>согните большой палец</strong> для клика без смещения мыши.';
    gaugeLabelTitle.textContent = 'Сгиб большого пальца';
    soundSynth.playPinch();
    try { localStorage.setItem('aeropoint_click_mode', 'thumb_bend'); } catch (e) {}
    postSettings({ click_mode: 'thumb_bend' });
  });

  btnModePinch?.addEventListener('click', () => {
    btnModePinch.classList.add('active');
    btnModeThumb?.classList.remove('active');
    btnModeAirTap?.classList.remove('active');
    modeHintText.innerHTML = 'Сведите <strong>кончики большого и указательного пальцев</strong> (щипок) для клика, удерживайте для Drag & Drop.';
    gaugeLabelTitle.textContent = 'Сила щипка (Pinch)';
    soundSynth.playPinch();
    try { localStorage.setItem('aeropoint_click_mode', 'pinch'); } catch (e) {}
    postSettings({ click_mode: 'pinch' });
  });

  btnModeAirTap?.addEventListener('click', () => {
    btnModeAirTap.classList.add('active');
    btnModeThumb?.classList.remove('active');
    btnModePinch?.classList.remove('active');
    modeHintText.innerHTML = 'Направьте указательный палец и <strong>толкните воздух вперед</strong> (Vision Pro Push-to-Click)!';
    gaugeLabelTitle.textContent = 'Глубина нажатия (Z-Push)';
    soundSynth.playPinch();
    try { localStorage.setItem('aeropoint_click_mode', 'air_tap'); } catch (e) {}
    postSettings({ click_mode: 'air_tap' });
  });

  // Restore saved preferences on startup
  try {
    const savedMode = localStorage.getItem('aeropoint_click_mode');
    if (savedMode === 'pinch') btnModePinch?.click();
    else if (savedMode === 'air_tap') btnModeAirTap?.click();

    const savedVol = localStorage.getItem('aeropoint_sound_vol');
    if (savedVol && sliderSoundVolume) {
      sliderSoundVolume.value = savedVol;
      soundSynth.volume = parseFloat(savedVol) / 100.0;
      if (valSoundVolume) valSoundVolume.textContent = `${savedVol}%`;
    }
  } catch (e) {}

  switchPresentation?.addEventListener('change', (e) => {
    soundSynth.playPinch();
    postSettings({ presentation_mode_enabled: e.target.checked });
  });

  switchSpotlight?.addEventListener('change', (e) => {
    soundSynth.playLaserFx();
    fetch('/api/spotlight/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: e.target.checked })
    }).catch(() => {});
    flashActionCapsule('💡', e.target.checked ? 'Spotlight включен' : 'Spotlight выключен');
  });

  switchVirtualSurface?.addEventListener('change', (e) => {
    soundSynth.playRadialChime();
    postSettings({ enable_virtual_touch_surface: e.target.checked });
    flashActionCapsule('🪟', e.target.checked ? 'Виртуальный стол ВКЛ' : 'Виртуальный стол ВЫКЛ');
  });

  btnCalibrateSurface?.addEventListener('click', () => {
    soundSynth.playLaserFx();
    fetch('/api/surface/calibrate', { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          if (switchVirtualSurface) switchVirtualSurface.checked = true;
          flashActionCapsule('🪟', `Плоскость откалибрована: Z = ${data.virtual_surface_z}м`);
        }
      })
      .catch(() => {});
  });

  switchScreenLoupe?.addEventListener('change', (e) => {
    soundSynth.playLaserFx();
    postSettings({ enable_screen_magnifier: e.target.checked });
    flashActionCapsule('🔍', e.target.checked ? 'Микро-лупа ВКЛ' : 'Микро-лупа ВЫКЛ');
  });

  // Air-Snap Screenshot Capture & Gallery
  const btnAirSnap = document.getElementById('btn-air-snap-capture');
  const airSnapGallery = document.getElementById('air-snap-gallery');

  function renderAirSnapGallery(snaps) {
    if (!airSnapGallery) return;
    if (!snaps || snaps.length === 0) {
      airSnapGallery.innerHTML = '<span style="font-size: 0.70rem; color: var(--text-secondary); align-self: center;">Снимков пока нет. Нажмите «Сделать снимок» для мгновенного захвата.</span>';
      return;
    }
    airSnapGallery.innerHTML = '';
    snaps.forEach(s => {
      const card = document.createElement('a');
      card.href = s.url;
      card.target = '_blank';
      card.title = `${s.filename} (${s.formatted_time || ''})`;
      card.style.cssText = 'position: relative; flex-shrink: 0; width: 72px; height: 48px; border-radius: 6px; overflow: hidden; border: 1px solid rgba(0, 242, 254, 0.3); background: #000; display: block;';
      card.innerHTML = `<img src="${s.url}" alt="Snap" style="width: 100%; height: 100%; object-fit: cover;"><span style="position: absolute; bottom: 2px; right: 3px; font-size: 0.58rem; background: rgba(0,0,0,0.7); color: #fff; padding: 1px 3px; border-radius: 3px;">${s.formatted_time || ''}</span>`;
      airSnapGallery.appendChild(card);
    });
  }

  btnAirSnap?.addEventListener('click', () => {
    soundSynth.playShutterFx();
    btnAirSnap.disabled = true;
    btnAirSnap.textContent = 'Захват...';
    fetch('/api/screenshot/capture', { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        btnAirSnap.disabled = false;
        btnAirSnap.textContent = 'Сделать снимок';
        if (data.status === 'ok') {
          flashActionCapsule('📸', `Снимок сохранен: ${data.screenshot.filename}`);
          loadAirSnapGallery();
        }
      })
      .catch(() => {
        btnAirSnap.disabled = false;
        btnAirSnap.textContent = 'Сделать снимок';
      });
  });

  function loadAirSnapGallery() {
    fetch('/api/screenshots')
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') renderAirSnapGallery(data.screenshots);
      })
      .catch(() => {});
  }
  loadAirSnapGallery();

  // Two-Hand Dominant Hand
  switchTwoHands?.addEventListener('change', (e) => postSettings({ enable_two_hands: e.target.checked }));
  btnDomRight?.addEventListener('click', () => {
    btnDomRight.classList.add('active');
    btnDomLeft.classList.remove('active');
    postSettings({ dominant_hand: 'Right' });
  });
  btnDomLeft?.addEventListener('click', () => {
    btnDomLeft.classList.add('active');
    btnDomRight.classList.remove('active');
    postSettings({ dominant_hand: 'Left' });
  });

  // HUD Visual Skin Switcher
  const badgeHudThemeLabel = document.getElementById('badge-hud-theme-label');
  const skinButtons = document.querySelectorAll('.seg-mini-btn[data-skin]');

  function updateActiveSkin(skin) {
    if (!skin) return;
    const cleanSkin = skin.toLowerCase();
    skinButtons.forEach(b => b.classList.toggle('active', b.getAttribute('data-skin') === cleanSkin));
    document.body.classList.remove('theme-cyberpunk', 'theme-visionos', 'theme-matrix', 'theme-solar', 'theme-stealth');
    document.body.classList.add(`theme-${cleanSkin}`);
    if (badgeHudThemeLabel) {
      badgeHudThemeLabel.textContent = cleanSkin.toUpperCase();
    }
  }

  skinButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const skin = btn.getAttribute('data-skin');
      if (!skin) return;
      updateActiveSkin(skin);
      soundSynth.playClick();
      flashActionCapsule('🎨', `Скин HUD: ${skin.toUpperCase()}`);
      postSettings({ hud_theme: skin });
    });
  });

  // Tab Switcher (Webcam vs iPhone)
  tabBtnWebcam?.addEventListener('click', () => {
    tabBtnWebcam.classList.add('active');
    tabBtnIphone.classList.remove('active');
    fetch('/api/switch_tab', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tab: 'webcam' })
    });
    soundSynth.playPinch();
  });

  tabBtnIphone?.addEventListener('click', () => {
    tabBtnIphone.classList.add('active');
    tabBtnWebcam.classList.remove('active');
    fetch('/api/switch_tab', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tab: 'iphone' })
    });
    soundSynth.playRadialChime();
    // Switch to iPhone Studio view in dock as well
    document.querySelector('.dock-btn[data-view="view-iphone"]')?.click();
  });

  // iPhone Rear LiDAR Mirror Toggle
  btnToggleMirror?.addEventListener('click', () => {
    fetch('/api/spatial/mirror', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      .then(res => res.json())
      .then(data => {
        const isM = !!data.mirror_x;
        txtMirrorStatus.textContent = isM ? 'ЗЕРКАЛЬНО: ВКЛ' : 'ПРЯМО: ВЫКЛ';
        btnToggleMirror.style.borderColor = isM ? 'var(--aero-cyan)' : 'rgba(255,255,255,0.2)';
        soundSynth.playPinch();
      });
  });

  // Copy mobile Safari URL
  btnCopyUrl?.addEventListener('click', () => {
    const text = mobileUrlText.textContent;
    navigator.clipboard.writeText(text).then(() => {
      btnCopyUrl.textContent = 'Скопировано!';
      setTimeout(() => btnCopyUrl.textContent = 'Копировать', 1500);
      soundSynth.playPinch();
    });
  });

  // =========================================================================
  // 7. DirectShow Camera Discovery
  // =========================================================================
  function refreshCameras() {
    fetch('/api/cameras')
      .then(r => r.json())
      .then(data => {
        cameraSelect.innerHTML = '';
        if (data.cameras && data.cameras.length > 0) {
          data.cameras.forEach(cam => {
            const opt = document.createElement('option');
            opt.value = cam.id;
            opt.textContent = `${cam.name} (${cam.width}x${cam.height})`;
            if (cam.id === data.active_id) opt.selected = true;
            cameraSelect.appendChild(opt);
          });
        } else {
          const opt = document.createElement('option');
          opt.value = 0;
          opt.textContent = 'Камера #0 (По умолчанию)';
          cameraSelect.appendChild(opt);
        }
      })
      .catch(err => console.error('[!] Failed to load cameras:', err));
  }

  btnRefreshCams?.addEventListener('click', refreshCameras);
  cameraSelect?.addEventListener('change', (e) => {
    const camId = parseInt(e.target.value);
    loadingOverlay.style.display = 'flex';
    fetch('/api/select_camera', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ camera_id: camId })
    }).finally(() => {
      setTimeout(() => loadingOverlay.style.display = 'none', 600);
    });
  });

  refreshCameras();

  // =========================================================================
  // 7.1 Multi-Monitor Management & Selector
  // =========================================================================
  const monitorContainer = document.getElementById('monitor-selector-container');
  let currentActiveMonitorId = -1;

  function loadMonitorsList() {
    if (!monitorContainer) return;
    fetch('/api/monitors')
      .then(res => res.json())
      .then(data => {
        if (!data || !data.monitors) return;
        currentActiveMonitorId = data.active_monitor !== undefined ? data.active_monitor : -1;
        monitorContainer.innerHTML = '';

        // All monitors button
        const btnAll = document.createElement('button');
        btnAll.className = `monitor-btn ${currentActiveMonitorId === -1 ? 'active' : ''}`;
        btnAll.setAttribute('data-monitor', '-1');
        btnAll.innerHTML = `
          <span class="m-icon">🌌</span>
          <span class="m-title">Весь рабочий стол</span>
          <span class="m-res">Все мониторы (${data.monitors.length})</span>
        `;
        btnAll.addEventListener('click', () => selectMonitor(-1));
        monitorContainer.appendChild(btnAll);

        // Individual monitors
        data.monitors.forEach(m => {
          const btn = document.createElement('button');
          btn.className = `monitor-btn ${currentActiveMonitorId === m.id ? 'active' : ''}`;
          btn.setAttribute('data-monitor', m.id);
          btn.innerHTML = `
            <span class="m-icon">🖥️</span>
            <span class="m-title">${m.name}</span>
            <span class="m-res">${m.width}x${m.height}</span>
          `;
          btn.addEventListener('click', () => selectMonitor(m.id));
          monitorContainer.appendChild(btn);
        });
      })
      .catch(err => console.error('[!] Error loading monitors:', err));
  }

  function selectMonitor(monitorId) {
    currentActiveMonitorId = monitorId;
    fetch('/api/monitors/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ monitor_id: monitorId })
    })
    .then(res => res.json())
    .then(data => {
      soundSynth.playClick();
      const label = monitorId === -1 ? 'Весь рабочий стол' : `Монитор #${monitorId + 1}`;
      flashActionCapsule('🖥️', `Дисплей: ${label}`);
      document.querySelectorAll('.monitor-btn').forEach(b => {
        const id = parseInt(b.getAttribute('data-monitor'));
        b.classList.toggle('active', id === monitorId);
      });
    })
    .catch(err => console.error('[!] Error switching monitor:', err));
  }

  loadMonitorsList();

  // =========================================================================
  // 8. 25-60 Hz Real-Time Telemetry Stream (SSE with Polling Fallback)
  // =========================================================================
  function handleStatusData(data) {
    if (!data) return;
    loadingOverlay.style.display = 'none';

    // Initial settings sync on first telemetry packet
    if (!window._initialSettingsLoaded) {
      window._initialSettingsLoaded = true;
      if (switchCornerSnap && typeof data.enable_corner_snap === 'boolean') {
        switchCornerSnap.checked = data.enable_corner_snap;
      }
      if (switchWindowSnap && typeof data.enable_window_snap_zones === 'boolean') {
        switchWindowSnap.checked = data.enable_window_snap_zones;
      }
      if (switchSpotlight && typeof data.presentation_spotlight_mode === 'boolean') {
        switchSpotlight.checked = data.presentation_spotlight_mode;
      }
      if (switchVirtualSurface && typeof data.enable_virtual_touch_surface === 'boolean') {
        switchVirtualSurface.checked = data.enable_virtual_touch_surface;
      }
      if (switchScreenLoupe && typeof data.enable_screen_magnifier === 'boolean') {
        switchScreenLoupe.checked = data.enable_screen_magnifier;
      }
      if (switchDistanceAdaptation && typeof data.enable_distance_adaptation === 'boolean') {
        switchDistanceAdaptation.checked = data.enable_distance_adaptation;
      }
      if (switchAnchor && typeof data.enable_anchor === 'boolean') {
        switchAnchor.checked = data.enable_anchor;
      }
      if (switchAcceleration && typeof data.enable_acceleration === 'boolean') {
        switchAcceleration.checked = data.enable_acceleration;
      }
      if (switchLaser && typeof data.laser_pointer_mode === 'boolean') {
        switchLaser.checked = data.laser_pointer_mode;
      }
      if (data.laser_color) {
        document.querySelectorAll('.laser-color-pill .seg-btn').forEach(b => {
          b.classList.toggle('active', b.getAttribute('data-laser-color') === data.laser_color);
        });
      }
      if (switchClahe && typeof data.use_clahe === 'boolean') {
        switchClahe.checked = data.use_clahe;
      }
      if (switchWristClock && typeof data.show_wrist_hud_clock === 'boolean') {
        switchWristClock.checked = data.show_wrist_hud_clock;
      }
      if (switchAirPiano && typeof data.enable_air_piano === 'boolean') {
        switchAirPiano.checked = data.enable_air_piano;
      }
      if (switchAmbientTheme && typeof data.ambient_theme_auto_sync === 'boolean') {
        switchAmbientTheme.checked = data.ambient_theme_auto_sync;
      }
      if (data.precision_profile) {
        updateProfileButtons(data.precision_profile);
      }
      if (data.hud_theme) {
        updateActiveSkin(data.hud_theme);
      }
    }

    // Store live landmarks for 3D Holographic Visualizer
    window._latestLandmarks3D = data.landmarks_3d || null;

    // Play live Air-Piano notes if triggered
    if (data.air_piano_notes && Array.isArray(data.air_piano_notes) && data.air_piano_notes.length > 0) {
      data.air_piano_notes.forEach(note => {
        soundSynth.playPianoNote(note);
        flashActionCapsule('🎹', `Нота: ${note}`);
      });
    }

    // Multi-Monitor sync from telemetry / hotkey cycle
    if (typeof data.active_monitor === 'number' && data.active_monitor !== currentActiveMonitorId) {
      currentActiveMonitorId = data.active_monitor;
      document.querySelectorAll('.monitor-btn').forEach(b => {
        const id = parseInt(b.getAttribute('data-monitor'));
        b.classList.toggle('active', id === currentActiveMonitorId);
      });
    }

    // Telemetry top badges
    badgeFps.textContent = `${data.fps || 0} FPS`;
    badgeLatency.textContent = `${data.latency_ms || 0} ms`;
    if (badgeSignal && typeof data.confidence_pct === 'number') {
      const conf = Math.round(data.confidence_pct);
      badgeSignal.textContent = `${conf}%`;
      if (dotSignal) {
        if (conf >= 85) dotSignal.style.background = '#00e676';
        else if (conf >= 60) dotSignal.style.background = '#ffd600';
        else dotSignal.style.background = '#ff5252';
      }
    }
    if (badgeCpu) badgeCpu.textContent = `${data.cpu || 0}%`;

    // Anchor status
    if (data.is_anchored) {
      badgeAnchor.textContent = 'Якорь: ЗАФИКСИРОВАН';
      pillAnchorStatus.style.borderColor = 'rgba(0, 242, 254, 0.7)';
    } else {
      badgeAnchor.textContent = 'Курсор: Свободен';
      pillAnchorStatus.style.borderColor = 'rgba(255, 255, 255, 0.12)';
    }

    // Hands Mode
    if (data.is_dual_hand) {
      badgeHandsIcon.textContent = '🙌';
      badgeHandsMode.textContent = '2 Руки (Bimanual)';
      pillHandsMode.style.borderColor = 'var(--aero-violet)';
    } else if (data.hand_detected) {
      badgeHandsIcon.textContent = '🖐️';
      badgeHandsMode.textContent = '1 Рука';
      pillHandsMode.style.borderColor = 'rgba(255, 255, 255, 0.12)';
    } else {
      badgeHandsIcon.textContent = '🔍';
      badgeHandsMode.textContent = 'Поиск руки...';
      pillHandsMode.style.borderColor = 'rgba(255, 255, 255, 0.12)';
    }

    // Lighting Telemetry Badge
    if (badgeLightingText && typeof data.luminance === 'number') {
      const lx = Math.round(data.luminance);
      const k = data.color_temp_kelvin ? ` | ${data.color_temp_kelvin}K` : '';
      if (data.is_night_mode) {
        if (badgeLightingIcon) badgeLightingIcon.textContent = '🌙';
        badgeLightingText.textContent = `${lx} lx${k} (Ночь)`;
        if (pillLighting) pillLighting.style.borderColor = 'rgba(255, 170, 0, 0.45)';
      } else if (lx >= 100) {
        if (badgeLightingIcon) badgeLightingIcon.textContent = '☀️';
        badgeLightingText.textContent = `${lx} lx${k}`;
        if (pillLighting) pillLighting.style.borderColor = 'rgba(0, 242, 254, 0.3)';
      } else {
        if (badgeLightingIcon) badgeLightingIcon.textContent = '⛅';
        badgeLightingText.textContent = `${lx} lx${k}`;
        if (pillLighting) pillLighting.style.borderColor = 'rgba(255, 255, 255, 0.12)';
      }
    }

    // Kinetic Speedometer telemetry
    if (badgeVelocity && typeof data.velocity_px_s === 'number') {
      badgeVelocity.textContent = `${Math.round(data.velocity_px_s)} px/s`;
      if (pillVelocity) {
        if (data.velocity_px_s > 350) {
          pillVelocity.style.borderColor = 'rgba(0, 242, 254, 0.65)';
        } else {
          pillVelocity.style.borderColor = 'rgba(255, 255, 255, 0.12)';
        }
      }
    }

    if (typeof data.velocity_px_s === 'number') {
      currentLiveVelocity = data.velocity_px_s;
    }
    if (typeof data.gain === 'number') {
      currentLiveGain = data.gain;
    }
    if (typeof data.acceleration_curve === 'string' && data.acceleration_curve !== currentActiveCurve && !window._curveUserInteracted) {
      updateCurveButtons(data.acceleration_curve);
    }
    drawAccelCurve();

    // Distance Caliper telemetry
    if (badgeDistance && typeof data.distance_cm === 'number' && data.distance_cm > 0) {
      badgeDistance.textContent = `${Math.round(data.distance_cm)} cm`;
      if (pillDistance) {
        if (data.distance_cm >= 35 && data.distance_cm <= 85) {
          pillDistance.style.borderColor = 'rgba(0, 242, 254, 0.5)';
        } else {
          pillDistance.style.borderColor = 'rgba(255, 255, 255, 0.12)';
        }
      }
    } else if (badgeDistance && !data.hand_detected) {
      badgeDistance.textContent = '-- cm';
      if (pillDistance) pillDistance.style.borderColor = 'rgba(255, 255, 255, 0.12)';
    }

    // Hand Tilt / Roll telemetry
    const badgeTilt = document.getElementById('badge-tilt');
    if (badgeTilt && typeof data.roll_deg === 'number' && data.hand_detected) {
      const sign = data.roll_deg > 0 ? '+' : '';
      badgeTilt.textContent = `${sign}${Math.round(data.roll_deg)}°`;
    } else if (badgeTilt && !data.hand_detected) {
      badgeTilt.textContent = '0°';
    }

    // Tracking status badge
    if (trackingStatusBadge) {
      if (data.hand_detected) {
        trackingStatusBadge.textContent = 'АКТИВЕН';
        trackingStatusBadge.style.color = '#00e676';
        trackingStatusBadge.style.borderColor = 'rgba(0, 230, 118, 0.4)';
      } else {
        trackingStatusBadge.textContent = 'СКАНИРОВАНИЕ';
        trackingStatusBadge.style.color = 'var(--aero-cyan)';
        trackingStatusBadge.style.borderColor = 'rgba(0, 242, 254, 0.3)';
      }
    }

    // Dynamic Power Saver Telemetry
    if (badgePowerText) {
      if (data.is_power_saver) {
        if (badgePowerIcon) badgePowerIcon.textContent = '🌱';
        badgePowerText.textContent = 'ECO 15';
        if (pillPowerMode) {
          pillPowerMode.style.borderColor = 'rgba(0, 230, 118, 0.45)';
          pillPowerMode.style.background = 'rgba(0, 230, 118, 0.12)';
        }
      } else {
        if (badgePowerIcon) badgePowerIcon.textContent = '⚡';
        badgePowerText.textContent = '60 FPS';
        if (pillPowerMode) {
          pillPowerMode.style.borderColor = 'rgba(0, 242, 254, 0.35)';
          pillPowerMode.style.background = 'rgba(255, 255, 255, 0.05)';
        }
      }
    }

    // Pinch force gauge
    const pct = Math.max(0, Math.min(100, Math.round(data.pinch_pct || 0)));
    pinchPercentText.textContent = `${pct}%`;
    pinchBarFill.style.width = `${pct}%`;

    // Update active gesture card
    updateCoreGestureHighlight(data.gesture);

    // Mid-air drawing sync
    if (typeof updateAirDrawFromTelemetry === 'function') {
      updateAirDrawFromTelemetry(data);
    }

    // Bimanual Air-Clap Audio Trigger
    if (data.action_gesture === 'AIR CLAP' && window._lastActionGesture !== 'AIR CLAP') {
      soundSynth.playAirClap();
    }
    window._lastActionGesture = data.action_gesture;

    // iPhone Sensor telemetry
    const iph = data.iphone_status;
    if (iph) {
      if (iph.connected) {
        badgeIphoneConn.textContent = 'ПОДКЛЮЧЕН';
        badgeIphoneConn.className = 'sensor-badge connected';
        valIphoneSensor.textContent = iph.sensor || 'TrueDepth';
        valIphonePing.textContent = `${iph.latency_ms || 0.8} ms`;
        valIphoneBattery.textContent = `${iph.battery || 100}%`;
        valIphoneDepth.textContent = `${Math.round(iph.depth_mm || 420)} mm`;
        valIphoneDepthDisplay.textContent = `${Math.round(iph.depth_mm || 420)} mm`;

        const depthPct = Math.max(5, Math.min(100, (iph.depth_mm / 800.0) * 100));
        barIphoneDepth.style.width = `${depthPct}%`;

        const isMirr = !!iph.mirror_x;
        txtMirrorStatus.textContent = isMirr ? 'ЗЕРКАЛЬНО: ВКЛ' : 'ПРЯМО: ВЫКЛ';
      } else {
        badgeIphoneConn.textContent = 'ОЖИДАНИЕ';
        badgeIphoneConn.className = 'sensor-badge disconnected';
      }
    }
  }

  // Real-time EventSource with Automatic Polling Fallback
  let eventSourceActive = false;
  if ('EventSource' in window) {
    try {
      const sse = new EventSource('/api/stream_events');
      sse.onmessage = (e) => {
        eventSourceActive = true;
        try {
          const data = JSON.parse(e.data);
          handleStatusData(data);
        } catch (err) {}
      };
      sse.onerror = () => {
        if (!eventSourceActive) pollStatus();
      };
    } catch (e) {
      pollStatus();
    }
  } else {
    pollStatus();
  }

  function pollStatus() {
    if (eventSourceActive) return;
    fetch('/api/status')
      .then(r => r.json())
      .then(handleStatusData)
      .catch(() => {})
      .finally(() => {
        if (!eventSourceActive) setTimeout(pollStatus, 50);
      });
  }

  // Load LAN Info for QR code
  fetch('/api/lan_info')
    .then(r => r.json())
    .then(data => {
      if (data.mobile_url) {
        mobileUrlText.textContent = data.mobile_url;
        const qrEl = document.getElementById('qr-code-img');
        if (qrEl) {
          qrEl.src = `https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(data.mobile_url)}`;
        }
      }
    });

  // =========================================================================
  // 9. Ambient Canvas Particle Nebula (Subtle 30 FPS Background Animation)
  // =========================================================================
  const canvas = document.getElementById('ambient-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    window.addEventListener('resize', () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });

    const particles = [];
    for (let i = 0; i < 45; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 1.5 + 0.5,
        alpha: Math.random() * 0.5 + 0.2
      });
    }

    function renderNebula() {
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#00f2fe';

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.globalAlpha = p.alpha;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();

        // Connect nearby particles
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
          if (dist < 110) {
            ctx.strokeStyle = '#6366f1';
            ctx.globalAlpha = (1 - dist / 110) * 0.15;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }

      setTimeout(() => requestAnimationFrame(renderNebula), 33);
    }
    renderNebula();
  }

  // =========================================================================
  // 10. Air-Keys Virtual Numpad & Presentation Remote
  // =========================================================================
  const numpadBuffer = document.getElementById('numpad-buffer');
  let currentKeyBuffer = '';

  document.querySelectorAll('.v-key, .dpad-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.getAttribute('data-key');
      if (!key) return;

      soundSynth.playClick();
      fetch('/api/keyboard/press', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: key })
      }).catch(err => console.error('[!] Key press error:', err));

      if (key === 'backspace') {
        currentKeyBuffer = currentKeyBuffer.slice(0, -1);
      } else if (key === 'enter') {
        soundSynth.playChord();
        currentKeyBuffer = '';
      } else if (key === 'space') {
        currentKeyBuffer += ' ';
      } else if (key === 'escape' || key === 'tab' || key.startsWith('dpad')) {
        // action keys
      } else if (key.length === 1) {
        currentKeyBuffer = (currentKeyBuffer + key).slice(-14);
      }
      if (numpadBuffer) {
        numpadBuffer.textContent = currentKeyBuffer.length > 0 ? currentKeyBuffer : '_';
      }
    });
  });

  document.getElementById('btn-clear-buffer')?.addEventListener('click', () => {
    currentKeyBuffer = '';
    if (numpadBuffer) numpadBuffer.textContent = '_';
    soundSynth.playClick();
  });

  // Remote Presentation Buttons
  document.getElementById('btn-remote-prev')?.addEventListener('click', () => {
    soundSynth.playClick();
    flashActionCapsule('⏪', 'Предыдущий слайд');
    fetch('/api/radial/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'prev_slide' })
    });
  });

  document.getElementById('btn-remote-play')?.addEventListener('click', () => {
    soundSynth.playChord();
    flashActionCapsule('⏯️', 'Play / Pause');
    fetch('/api/radial/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'play_pause' })
    });
  });

  document.getElementById('btn-remote-next')?.addEventListener('click', () => {
    soundSynth.playClick();
    flashActionCapsule('⏩', 'Следующий слайд');
    fetch('/api/radial/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'next_slide' })
    });
  });

  // Windows Aero Snap & Desktop Switcher Controls
  const snapActions = [
    { id: 'btn-snap-left', action: 'snap_left', label: 'Прикрепить влево' },
    { id: 'btn-snap-max', action: 'snap_maximize', label: 'Развернуть окно' },
    { id: 'btn-snap-right', action: 'snap_right', label: 'Прикрепить вправо' },
    { id: 'btn-desk-prev', action: 'desktop_prev', label: 'Предыдущий стол' },
    { id: 'btn-desk-next', action: 'desktop_next', label: 'Следующий стол' },
    { id: 'btn-macro-copy', action: 'copy', label: 'Копировать (Ctrl+C)' },
    { id: 'btn-macro-paste', action: 'paste', label: 'Вставить (Ctrl+V)' },
    { id: 'btn-macro-undo', action: 'undo', label: 'Отмена (Ctrl+Z)' },
    { id: 'btn-macro-search', action: 'search', label: 'Поиск Windows (Win+S)' },
    { id: 'btn-macro-refresh', action: 'refresh', label: 'Обновить страницу (F5)' },
  ];

  snapActions.forEach(({ id, action, label }) => {
    document.getElementById(id)?.addEventListener('click', () => {
      soundSynth.playPinch();
      flashActionCapsule('🪟', label);
      fetch('/api/radial/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
    });
  });

  // Spatial Media Deck Controller
  document.querySelectorAll('.media-ctrl-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const act = btn.getAttribute('data-media-act');
      if (!act) return;
      if (act.includes('vol') || act === 'mute') {
        soundSynth.playLaserFx();
      } else {
        soundSynth.playRadialChime();
      }
      flashActionCapsule('🎵', `Медиа: ${btn.textContent.trim()}`);
      fetch('/api/media/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: act })
      }).catch(() => {});
    });
  });

  // Air-Typer Text Broadcaster
  const typerTextInput = document.getElementById('typer-text-input');
  const btnTyperSend = document.getElementById('btn-typer-send');
  const btnTyperEnter = document.getElementById('btn-typer-enter');

  function sendTyperText(withEnter = false) {
    if (!typerTextInput) return;
    const text = typerTextInput.value;
    if (!text) return;
    soundSynth.playClick();
    flashActionCapsule('⌨️', `Ввод: "${text.length > 20 ? text.slice(0, 17) + '...' : text}"`);
    fetch('/api/keyboard/type', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text })
    })
    .then(() => {
      if (withEnter) {
        setTimeout(() => {
          fetch('/api/keyboard/press', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: 'enter' })
          });
          soundSynth.playChord();
        }, 30);
      }
    })
    .catch(err => console.error('[!] Typer error:', err));
  }

  btnTyperSend?.addEventListener('click', () => sendTyperText(false));
  btnTyperEnter?.addEventListener('click', () => sendTyperText(true));
  typerTextInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      sendTyperText(true);
    }
  });

  document.querySelectorAll('.chip-btn').forEach(chip => {
    chip.addEventListener('click', () => {
      const typeText = chip.getAttribute('data-type');
      const pressKey = chip.getAttribute('data-key');
      const snapAction = chip.getAttribute('data-action');
      soundSynth.playClick();
      if (typeText) {
        if (typerTextInput) typerTextInput.value = typeText;
        sendTyperText(false);
      } else if (pressKey) {
        fetch('/api/keyboard/press', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: pressKey })
        });
        flashActionCapsule('⌨️', `Клавиша: ${pressKey.toUpperCase()}`);
      } else if (snapAction) {
        fetch(`/api/action/${snapAction}`, { method: 'POST' });
        flashActionCapsule('🪟', `Окно: ${snapAction.replace('snap_', '').toUpperCase()}`);
      }
    });
  });

  // =========================================================================
  // 11. Interactive Auto-Calibration Wizard
  // =========================================================================
  const btnStartCalib = document.getElementById('btn-start-calibration');
  const cwProgressWrap = document.getElementById('cw-progress-wrap');
  const cwProgressFill = document.getElementById('cw-progress-fill');
  const cwStatusBadge = document.getElementById('cw-status-badge');
  const cwDescText = document.getElementById('cw-desc-text');
  let isCalibrating = false;

  btnStartCalib?.addEventListener('click', () => {
    if (isCalibrating) return;
    isCalibrating = true;
    btnStartCalib.disabled = true;
    cwProgressWrap.classList.remove('hidden');
    cwStatusBadge.textContent = 'ИЗМЕРЕНИЕ...';
    cwStatusBadge.style.color = '#ffaa00';
    cwDescText.innerHTML = '🎯 <strong>Анализ тремора:</strong> Зафиксируйте руку в воздухе на 3 секунды...';
    soundSynth.playChord();
    flashActionCapsule('🎯', 'Авто-калибровка: 3 сек...');
    fetch('/api/calibration/start', { method: 'POST' }).catch(() => {});

    let progress = 0;
    const interval = setInterval(() => {
      progress += 4;
      cwProgressFill.style.width = `${progress}%`;
      if (progress >= 100) {
        clearInterval(interval);
        isCalibrating = false;
        btnStartCalib.disabled = false;
        cwStatusBadge.textContent = '✓ ОТКАЛИБРОВАНО';
        cwStatusBadge.style.color = '#00e676';
        cwDescText.innerHTML = '✨ <strong>Готово!</strong> Мертвая зона установлена на <strong>3.0 px</strong>, фильтр 1-Euro синхронизирован с физиологией вашей кисти.';
        soundSynth.playChord();

        // Send optimal parameters
        postSettings({
          deadzone_radius: 3.0,
          sensitivity: 1.85,
          smoothing_alpha: 0.32
        });
        if (sliderDeadzone) sliderDeadzone.value = "3.0";
        if (valDeadzone) valDeadzone.textContent = "3.0 px";
        if (sliderSensitivity) sliderSensitivity.value = "1.85";
        if (valSensitivity) valSensitivity.textContent = "1.85x";
      }
    }, 120);
  });

  // =========================================================================
  // 12. Viewport 2D / 3D Switcher & Holographic WebGL/Canvas Projection
  // =========================================================================
  const btnVpVideo = document.getElementById('btn-vp-video');
  const btnVp3d = document.getElementById('btn-vp-3d');
  const hologramCanvas = document.getElementById('hologram-3d-canvas');
  let is3DModeActive = false;

  btnVpVideo?.addEventListener('click', () => {
    is3DModeActive = false;
    btnVpVideo.classList.add('active');
    btnVp3d?.classList.remove('active');
    streamImg.style.display = 'block';
    if (hologramCanvas) hologramCanvas.style.display = 'none';
    soundSynth.playClick();
  });

  btnVp3d?.addEventListener('click', () => {
    is3DModeActive = true;
    btnVp3d.classList.add('active');
    btnVpVideo?.classList.remove('active');
    streamImg.style.display = 'none';
    if (hologramCanvas) {
      hologramCanvas.style.display = 'block';
      start3DHologramLoop();
    }
    soundSynth.playChord();
  });

  // Canonical 3D hand landmarks model for holographic preview
  const CANONICAL_HAND_3D = [
    [0.0, 0.5, 0.0],          // 0: Wrist
    [-0.15, 0.35, 0.05],      // 1: Thumb CMC
    [-0.26, 0.22, 0.08],      // 2: Thumb MCP
    [-0.34, 0.12, 0.09],      // 3: Thumb IP
    [-0.40, 0.02, 0.08],      // 4: Thumb Tip
    [-0.10, 0.10, 0.04],      // 5: Index MCP
    [-0.11, -0.10, 0.05],     // 6: Index PIP
    [-0.12, -0.25, 0.05],     // 7: Index DIP
    [-0.13, -0.38, 0.04],     // 8: Index Tip
    [0.0, 0.08, 0.02],        // 9: Middle MCP
    [0.0, -0.14, 0.03],       // 10: Middle PIP
    [0.0, -0.30, 0.03],       // 11: Middle DIP
    [0.0, -0.44, 0.02],       // 12: Middle Tip
    [0.10, 0.10, 0.0],        // 13: Ring MCP
    [0.11, -0.10, 0.0],       // 14: Ring PIP
    [0.12, -0.24, 0.0],       // 15: Ring DIP
    [0.12, -0.37, -0.01],     // 16: Ring Tip
    [0.20, 0.15, -0.03],      // 17: Pinky MCP
    [0.22, -0.02, -0.04],     // 18: Pinky PIP
    [0.23, -0.14, -0.04],     // 19: Pinky DIP
    [0.24, -0.25, -0.05]      // 20: Pinky Tip
  ];

  const HAND_BONES = [
    [0,1],[1,2],[2,3],[3,4],
    [0,5],[5,6],[6,7],[7,8],
    [5,9],[9,10],[10,11],[11,12],
    [9,13],[13,14],[14,15],[15,16],
    [13,17],[17,18],[18,19],[19,20],
    [0,17]
  ];

  let holoAnimId = null;
  let holoListenersAttached = false;
  let holoAngleY = 0;
  let holoAngleX = 0.35;
  let holoZoom = 1.0;
  let holoDragging = false;
  let holoLastMouse = { x: 0, y: 0 };
  let holoAutoSpin = true;

  function start3DHologramLoop() {
    if (!hologramCanvas) return;
    const ctx = hologramCanvas.getContext('2d');

    if (!holoListenersAttached) {
      holoListenersAttached = true;
      hologramCanvas.style.cursor = 'grab';

      hologramCanvas.addEventListener('mousedown', (e) => {
        holoDragging = true;
        holoAutoSpin = false;
        holoLastMouse = { x: e.clientX, y: e.clientY };
        hologramCanvas.style.cursor = 'grabbing';
      });

      window.addEventListener('mousemove', (e) => {
        if (!holoDragging) return;
        const dx = e.clientX - holoLastMouse.x;
        const dy = e.clientY - holoLastMouse.y;
        holoAngleY += dx * 0.012;
        holoAngleX = Math.max(-1.2, Math.min(1.2, holoAngleX + dy * 0.012));
        holoLastMouse = { x: e.clientX, y: e.clientY };
      });

      window.addEventListener('mouseup', () => {
        if (holoDragging) {
          holoDragging = false;
          hologramCanvas.style.cursor = 'grab';
        }
      });

      hologramCanvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        holoZoom = Math.max(0.45, Math.min(2.4, holoZoom - e.deltaY * 0.0015));
      }, { passive: false });

      hologramCanvas.addEventListener('dblclick', () => {
        holoAngleY = 0;
        holoAngleX = 0.35;
        holoZoom = 1.0;
        holoAutoSpin = true;
        soundSynth.playPinch();
      });
    }

    function render3D() {
      if (!is3DModeActive) return;
      const w = hologramCanvas.width = hologramCanvas.clientWidth || 640;
      const h = hologramCanvas.height = hologramCanvas.clientHeight || 480;

      ctx.clearRect(0, 0, w, h);
      if (holoAutoSpin && !holoDragging) {
        holoAngleY += 0.018;
      }

      // 3D Perspective Projection Matrix with Dynamic Zoom
      const cx = w / 2;
      const cy = h / 2 + 30;
      const scale = Math.min(w, h) * 0.72 * holoZoom;

      const cosY = Math.cos(holoAngleY), sinY = Math.sin(holoAngleY);
      const cosX = Math.cos(holoAngleX), sinX = Math.sin(holoAngleX);

      // Determine active 3D vertices (Live Neural Hand vs Canonical Model)
      let vertices = CANONICAL_HAND_3D;
      let isLiveMesh = false;
      if (window._latestLandmarks3D && window._latestLandmarks3D.length === 21) {
        const raw = window._latestLandmarks3D;
        const wrist = raw[0];
        // Center around wrist, flip Y so fingers point up
        vertices = raw.map(p => [
          (p[0] - wrist[0]) * 2.2,
          (wrist[1] - p[1]) * 2.2,
          (p[2] - wrist[2]) * 2.2
        ]);
        isLiveMesh = true;
      }

      // Project 21 vertices
      const projected = vertices.map(([x, y, z]) => {
        // Rotate around Y
        let rx = x * cosY - z * sinY;
        let rz = x * sinY + z * cosY;
        // Rotate around X
        let ry = y * cosX - rz * sinX;
        rz = y * sinX + rz * cosX;

        // Perspective division
        const fov = 2.4;
        const pz = rz + fov;
        const px = cx + (rx / pz) * scale;
        const py = cy + (ry / pz) * scale;
        return { x: px, y: py, z: pz };
      });

      // Draw Depth Plane Grid
      ctx.strokeStyle = 'rgba(0, 242, 254, 0.08)';
      ctx.lineWidth = 1;
      for (let r = 40; r <= 220; r += 45) {
        ctx.beginPath();
        ctx.ellipse(cx, cy + 90, r, r * 0.35, 0, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Draw Bones
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#00f2fe';
      ctx.shadowColor = '#00f2fe';
      ctx.shadowBlur = 10;

      for (const [p1, p2] of HAND_BONES) {
        const pt1 = projected[p1];
        const pt2 = projected[p2];
        ctx.beginPath();
        ctx.moveTo(pt1.x, pt1.y);
        ctx.lineTo(pt2.x, pt2.y);
        ctx.stroke();
      }

      // Draw Joints
      for (let i = 0; i < projected.length; i++) {
        const pt = projected[i];
        const isTip = (i === 4 || i === 8 || i === 12 || i === 16 || i === 20);
        ctx.fillStyle = isTip ? '#ff007f' : '#ffffff';
        ctx.shadowColor = isTip ? '#ff007f' : '#00f2fe';
        ctx.shadowBlur = isTip ? 14 : 8;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, isTip ? 5.5 : 3.5, 0, Math.PI * 2);
        ctx.fill();
      }

      // HUD Hologram Label
      ctx.shadowBlur = 0;
      ctx.font = '600 11px "JetBrains Mono", monospace';
      ctx.fillStyle = isLiveMesh ? '#00e676' : 'rgba(0, 242, 254, 0.8)';
      ctx.fillText(isLiveMesh ? '✦ LIVE NEURAL 3D SKELETON (ACTIVE)' : '✦ 3D SPATIAL KINEMATIC MESH (STANDBY)', 24, 34);
      ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.fillText(`ROTATION Y: ${(holoAngleY % (Math.PI * 2)).toFixed(2)} rad | ZOOM: ${Math.round(holoZoom * 100)}% | MODE: ${isLiveMesh ? 'REAL-TIME 3D' : 'PROJECTION'} (Тяните мышь для вращения)`, 24, 52);

      holoAnimId = requestAnimationFrame(render3D);
    }

    render3D();
  }

  // =========================================================================
  // 13. Air-Draw Spatial Canvas & Drawing Studio
  // =========================================================================
  const btnVpDraw = document.getElementById('btn-vp-draw');
  const airDrawCanvas = document.getElementById('air-draw-canvas');
  const airDrawToolbar = document.getElementById('air-draw-toolbar');
  const airBrushCursor = document.getElementById('air-brush-cursor');
  let isAirDrawActive = false;
  let currentColor = '#00f2fe';
  let isPainting = false;
  let lastPaintPos = null;
  let airTipPrevPos = null;

  function updateAirDrawFromTelemetry(data) {
    if (!isAirDrawActive || !airDrawCanvas) {
      if (airBrushCursor) airBrushCursor.style.display = 'none';
      return;
    }

    if (!data.hand_detected || !data.landmarks_3d || data.landmarks_3d.length < 9) {
      if (airBrushCursor) airBrushCursor.style.display = 'none';
      airTipPrevPos = null;
      return;
    }

    // Index fingertip is landmark 8: [x, y, z]
    const tip = data.landmarks_3d[8];
    const curX = tip[0] * airDrawCanvas.width;
    const curY = tip[1] * airDrawCanvas.height;

    if (airBrushCursor) {
      airBrushCursor.style.display = 'block';
      airBrushCursor.style.left = `${(tip[0] * 100).toFixed(2)}%`;
      airBrushCursor.style.top = `${(tip[1] * 100).toFixed(2)}%`;
      airBrushCursor.style.borderColor = currentColor;
    }

    // Mid-air draw condition: pinch gesture or pinch force > 65% or air_tap
    const isDrawing = (data.gesture === 'pinch' || data.gesture === 'air_tap' || (data.pinch_pct && data.pinch_pct > 65));
    if (isDrawing) {
      if (airBrushCursor) airBrushCursor.classList.add('drawing');
      const dCtx = airDrawCanvas.getContext('2d');
      if (airTipPrevPos) {
        dCtx.strokeStyle = currentColor;
        dCtx.shadowColor = currentColor;
        dCtx.shadowBlur = 14;
        dCtx.lineWidth = 5;
        dCtx.lineCap = 'round';
        dCtx.lineJoin = 'round';
        dCtx.beginPath();
        dCtx.moveTo(airTipPrevPos.x, airTipPrevPos.y);
        dCtx.lineTo(curX, curY);
        dCtx.stroke();
      }
      airTipPrevPos = { x: curX, y: curY };
    } else {
      if (airBrushCursor) airBrushCursor.classList.remove('drawing');
      airTipPrevPos = null;
    }
  }

  btnVpDraw?.addEventListener('click', () => {
    isAirDrawActive = true;
    is3DModeActive = false;
    btnVpDraw.classList.add('active');
    btnVpVideo?.classList.remove('active');
    btnVp3d?.classList.remove('active');
    streamImg.style.display = 'block';
    if (hologramCanvas) hologramCanvas.style.display = 'none';
    if (airDrawCanvas) {
      airDrawCanvas.style.display = 'block';
      airDrawCanvas.width = airDrawCanvas.clientWidth || 640;
      airDrawCanvas.height = airDrawCanvas.clientHeight || 480;
    }
    if (airDrawToolbar) airDrawToolbar.style.display = 'flex';
    fetch('/api/canvas/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: true })
    }).catch(() => {});
    soundSynth.playChord();
  });

  // When switching away to 2D or 3D, hide air draw
  btnVpVideo?.addEventListener('click', () => {
    isAirDrawActive = false;
    btnVpDraw?.classList.remove('active');
    if (airDrawCanvas) airDrawCanvas.style.display = 'none';
    if (airDrawToolbar) airDrawToolbar.style.display = 'none';
    if (airBrushCursor) airBrushCursor.style.display = 'none';
    fetch('/api/canvas/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: false })
    }).catch(() => {});
  });

  btnVp3d?.addEventListener('click', () => {
    isAirDrawActive = false;
    btnVpDraw?.classList.remove('active');
    if (airDrawCanvas) airDrawCanvas.style.display = 'none';
    if (airDrawToolbar) airDrawToolbar.style.display = 'none';
    if (airBrushCursor) airBrushCursor.style.display = 'none';
    fetch('/api/canvas/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: false })
    }).catch(() => {});
  });

  // Color picker
  document.querySelectorAll('.color-btn').forEach(cBtn => {
    cBtn.addEventListener('click', () => {
      document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('active'));
      cBtn.classList.add('active');
      currentColor = cBtn.getAttribute('data-color') || '#00f2fe';
      const colorNameMap = {
        '#00f2fe': 'cyan',
        '#ff007f': 'magenta',
        '#32ff7e': 'green',
        '#ffd32a': 'gold',
        '#ffffff': 'white'
      };
      const colName = colorNameMap[currentColor.toLowerCase()] || 'cyan';
      fetch('/api/canvas/color', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ color: colName })
      }).catch(() => {});
      soundSynth.playClick();
    });
  });

  // Clear Canvas
  document.getElementById('btn-draw-clear')?.addEventListener('click', () => {
    if (airDrawCanvas) {
      const dCtx = airDrawCanvas.getContext('2d');
      dCtx.clearRect(0, 0, airDrawCanvas.width, airDrawCanvas.height);
      fetch('/api/canvas/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }).catch(() => {});
      soundSynth.playPinch();
    }
  });

  // Export Screenshot
  document.getElementById('btn-draw-save')?.addEventListener('click', () => {
    if (airDrawCanvas) {
      const link = document.createElement('a');
      link.download = `aeropoint_airdraw_${Date.now()}.png`;
      link.href = airDrawCanvas.toDataURL('image/png');
      link.click();
      soundSynth.playChord();
    }
  });

  // Canvas drawing events
  if (airDrawCanvas) {
    const dCtx = airDrawCanvas.getContext('2d');
    airDrawCanvas.addEventListener('mousedown', (e) => {
      isPainting = true;
      lastPaintPos = { x: e.offsetX, y: e.offsetY };
    });
    airDrawCanvas.addEventListener('mousemove', (e) => {
      if (!isPainting || !lastPaintPos) return;
      dCtx.strokeStyle = currentColor;
      dCtx.shadowColor = currentColor;
      dCtx.shadowBlur = 12;
      dCtx.lineWidth = 4;
      dCtx.lineCap = 'round';
      dCtx.lineJoin = 'round';
      dCtx.beginPath();
      dCtx.moveTo(lastPaintPos.x, lastPaintPos.y);
      dCtx.lineTo(e.offsetX, e.offsetY);
      dCtx.stroke();
      lastPaintPos = { x: e.offsetX, y: e.offsetY };
    });
    window.addEventListener('mouseup', () => {
      isPainting = false;
      lastPaintPos = null;
    });
  }

  // =========================================================================
  // 17. Deep System Health Diagnostics & Resource Telemetry
  // =========================================================================
  const btnQuickDiag = document.getElementById('btn-quick-diagnostics');
  const btnRunDiag = document.getElementById('btn-run-diagnostics');
  const btnResetFilters = document.getElementById('btn-reset-filters');
  const btnExportDiag = document.getElementById('btn-export-diagnostics');
  const diagTerminalLog = document.getElementById('diag-terminal-log');
  let cachedDiagnosticsData = null;

  function appendDiagLog(msg) {
    if (!diagTerminalLog) return;
    const timeStr = new Date().toLocaleTimeString();
    diagTerminalLog.textContent += `\n[${timeStr}] ${msg}`;
    diagTerminalLog.scrollTop = diagTerminalLog.scrollHeight;
  }

  const fpsSparkHistory = [];
  const cpuSparkHistory = [];
  const sparkFps = document.getElementById('spark-fps');
  const sparkCpu = document.getElementById('spark-cpu');

  function renderSparkline(canvas, history, strokeCol, fillCol) {
    if (!canvas || history.length < 2) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const min = Math.min(...history) * 0.85;
    const max = Math.max(...history) * 1.15 || 1.0;
    const range = max - min || 1.0;

    ctx.beginPath();
    for (let i = 0; i < history.length; i++) {
      const x = (i / (history.length - 1)) * w;
      const y = h - ((history[i] - min) / range) * (h - 6) - 3;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = strokeCol;
    ctx.lineWidth = 1.8;
    ctx.stroke();

    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = fillCol;
    ctx.fill();
  }

  async function fetchSystemDiagnostics(isManualTest = false) {
    const tStart = performance.now();
    try {
      const resp = await fetch('/api/diagnostics');
      const rtt = Math.round(performance.now() - tStart);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      cachedDiagnosticsData = data;

      // Update RTT and uptime
      const elRtt = document.getElementById('diag-val-rtt');
      const elUptime = document.getElementById('diag-val-uptime');
      if (elRtt) elRtt.textContent = rtt;
      if (elUptime) elUptime.textContent = data.uptime_sec || 0;

      // Update memory & CPU
      const memMb = data.system_resources?.memory_mb || 0;
      const cpuPct = data.system_resources?.cpu_percent || 0;
      const elMem = document.getElementById('diag-val-mem');
      const barMem = document.getElementById('diag-bar-mem');
      if (elMem) elMem.textContent = `${memMb} MB`;
      if (barMem) barMem.style.width = `${Math.min(100, Math.max(5, (memMb / 450) * 100))}%`;

      const elCpu = document.getElementById('diag-val-cpu');
      const barCpu = document.getElementById('diag-bar-cpu');
      if (elCpu) elCpu.textContent = `${cpuPct}%`;
      if (barCpu) barCpu.style.width = `${Math.min(100, Math.max(5, cpuPct * 2))}%`;
      cpuSparkHistory.push(cpuPct);
      if (cpuSparkHistory.length > 30) cpuSparkHistory.shift();
      renderSparkline(sparkCpu, cpuSparkHistory, '#00f2fe', 'rgba(0, 242, 254, 0.15)');

      // Update Camera & FPS
      const cam = data.subsystems?.camera_pipeline || {};
      const elFps = document.getElementById('diag-val-fps');
      const elLat = document.getElementById('diag-val-lat');
      const barFps = document.getElementById('diag-bar-fps');
      const fpsVal = cam.fps || 0;
      if (elFps) elFps.textContent = `${fpsVal} FPS`;
      if (elLat) elLat.textContent = cam.latency_ms || 0;
      if (barFps) barFps.style.width = `${Math.min(100, (fpsVal / 60) * 100)}%`;
      fpsSparkHistory.push(fpsVal);
      if (fpsSparkHistory.length > 30) fpsSparkHistory.shift();
      renderSparkline(sparkFps, fpsSparkHistory, '#00e676', 'rgba(0, 230, 118, 0.15)');

      const elSaver = document.getElementById('diag-val-saver');
      if (elSaver) {
        if (cam.power_saver_active) {
          elSaver.textContent = 'Standby (ECO 15 FPS)';
          elSaver.style.color = '#38bdf8';
        } else {
          elSaver.textContent = 'Turbo 60 FPS (Активен)';
          elSaver.style.color = '#00e676';
        }
      }

      // Camera Subsystem
      const elCamStatus = document.getElementById('diag-val-cam-status');
      if (elCamStatus) {
        if (cam.directshow_connected) {
          elCamStatus.textContent = `DirectShow Cam #${cam.active_camera_id} (Подключена)`;
          elCamStatus.style.color = '#00e676';
        } else {
          elCamStatus.textContent = `DirectShow Cam #${cam.active_camera_id} (Ожидание потока)`;
          elCamStatus.style.color = '#ff9800';
        }
      }

      // Spatial iPhone Subsystem
      const spatial = data.subsystems?.spatial_receiver || {};
      const elSpatialStatus = document.getElementById('diag-val-spatial-status');
      const elSpatialPackets = document.getElementById('diag-val-spatial-packets');
      if (elSpatialStatus) {
        if (spatial.connected) {
          elSpatialStatus.textContent = `Подключен iPhone (UDP 8765)`;
          elSpatialStatus.style.color = '#00e676';
        } else {
          elSpatialStatus.textContent = `Ожидание iPhone (UDP 0.0.0.0:8765)`;
          elSpatialStatus.style.color = 'var(--text-secondary)';
        }
      }
      if (elSpatialPackets) elSpatialPackets.textContent = spatial.packet_count || 0;

      // Displays
      const display = data.subsystems?.display_and_mouse || {};
      const elMonitors = document.getElementById('diag-val-monitors');
      if (elMonitors) {
        elMonitors.textContent = `${display.monitors_count || 1} монитор(ов) | ${display.size?.[0] || 1920}x${display.size?.[1] || 1080}`;
      }

      // Precision Engine
      const prec = data.subsystems?.precision_engine || {};
      const elProfile = document.getElementById('diag-val-profile');
      const elCutoffs = document.getElementById('diag-val-cutoffs');
      const elAnchor = document.getElementById('diag-val-anchor');
      if (elProfile) elProfile.textContent = (prec.profile || 'desktop').toUpperCase();
      if (elCutoffs) elCutoffs.textContent = `${prec.min_cutoff} Hz / ${prec.beta}`;
      if (elAnchor) elAnchor.textContent = `${prec.deadzone} px / ${prec.is_anchored ? '🔒 Заблокирован' : 'Свободен'}`;

      if (isManualTest) {
        appendDiagLog(`[OK] Экспресс-тест завершен за ${rtt} мс. Все контрольные точки подсистем в норме.`);
      }
    } catch (err) {
      if (isManualTest) {
        appendDiagLog(`[ОШИБКА] Сбой опроса диагностики: ${err.message}`);
      }
    }
  }

  // Quick button switches view to diagnostics
  if (btnQuickDiag) {
    btnQuickDiag.addEventListener('click', () => {
      dockButtons.forEach(b => b.classList.remove('active'));
      quantumViews.forEach(v => v.classList.remove('active'));

      const diagDockBtn = document.querySelector('.dock-btn[data-view="view-diagnostics"]');
      if (diagDockBtn) diagDockBtn.classList.add('active');

      const diagView = document.getElementById('view-diagnostics');
      if (diagView) diagView.classList.add('active');

      soundSynth.playChord();
      fetchSystemDiagnostics(true);
    });
  }

  // Manual express test
  if (btnRunDiag) {
    btnRunDiag.addEventListener('click', () => {
      appendDiagLog('[START] Запуск экспресс-теста целостности аппаратного и программного стека...');
      soundSynth.playChord();
      fetchSystemDiagnostics(true);
    });
  }

  // Filter Reset
  if (btnResetFilters) {
    btnResetFilters.addEventListener('click', async () => {
      try {
        appendDiagLog('[CMD] Отправка команды сброса математического сглаживания 1-Euro...');
        const resp = await fetch('/api/precision/profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile: 'desktop' })
        });
        if (resp.ok) {
          appendDiagLog('[OK] Фильтры 1-Euro очищены и переинициализированы (профиль desktop).');
          soundSynth.playClick();
          fetchSystemDiagnostics(false);
        }
      } catch (e) {
        appendDiagLog(`[ERR] Не удалось сбросить фильтры: ${e.message}`);
      }
    });
  }

  // Export JSON Report
  if (btnExportDiag) {
    btnExportDiag.addEventListener('click', () => {
      if (!cachedDiagnosticsData) {
        appendDiagLog('[WARN] Нет кэшированных данных диагностики для экспорта.');
        return;
      }
      const blob = new Blob([JSON.stringify(cachedDiagnosticsData, null, 2)], { type: 'application/json' });
      const link = document.createElement('a');
      link.download = `aeropoint_diagnostics_${Date.now()}.json`;
      link.href = URL.createObjectURL(blob);
      link.click();
      soundSynth.playChord();
      appendDiagLog('[EXPORT] Отчет диагностики сохранен на диск.');
    });
  }

  // Export Session Telemetry Timeline to CSV
  const btnExportCsv = document.getElementById('btn-export-telemetry-csv');
  if (btnExportCsv) {
    btnExportCsv.addEventListener('click', async () => {
      try {
        appendDiagLog('[EXPORT] Запрос хронологической истории телеметрии сессии для экспорта в CSV...');
        const resp = await fetch('/api/session/export');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        const samples = data.samples || [];
        if (samples.length === 0) {
          appendDiagLog('[WARN] История телеметрии пока пуста (требуется несколько секунд активности).');
          return;
        }

        const headers = ['time_sec', 'fps', 'latency_ms', 'gesture', 'hand_detected', 'pinch_pct', 'distance_cm', 'tilt_deg'];
        const csvRows = [headers.join(',')];

        samples.forEach(s => {
          csvRows.push([
            s.t ?? '',
            s.fps ?? '',
            s.lat ?? '',
            `"${s.gest || ''}"`,
            s.hand ? 1 : 0,
            s.pinch ?? '',
            s.dist ?? '',
            s.tilt ?? ''
          ].join(','));
        });

        const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvRows.join('\n'));
        const link = document.createElement('a');
        link.download = `aeropoint_telemetry_${Date.now()}.csv`;
        link.href = csvContent;
        link.click();

        soundSynth.playChord();
        appendDiagLog(`[EXPORT] ${samples.length} записей телеметрии успешно экспортированы в файл CSV.`);
      } catch (e) {
        appendDiagLog(`[ERR] Сбой экспорта CSV: ${e.message}`);
      }
    });
  }

  // Periodically refresh diagnostics when diagnostics view is active
  setInterval(() => {
    const diagView = document.getElementById('view-diagnostics');
    if (diagView && diagView.classList.contains('active')) {
      fetchSystemDiagnostics(false);
    }
  }, 2000);

});
