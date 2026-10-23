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

      osc1.type = 'sine';
      osc2.type = 'sine';
      osc1.frequency.setValueAtTime(880, now);   // A5
      osc2.frequency.setValueAtTime(1760, now);  // A6

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

      osc.type = 'sine';
      osc.frequency.setValueAtTime(70, now);
      osc.frequency.exponentialRampToValueAtTime(140, now + 0.15);

      gain.gain.setValueAtTime(this.volume * 0.7, now);
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

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(1800, now);
      osc.frequency.exponentialRampToValueAtTime(400, now + 0.012);

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
  const badgeCpu = document.getElementById('badge-cpu');
  const badgeAnchor = document.getElementById('badge-anchor');
  const pillAnchorStatus = document.getElementById('pill-anchor-status');
  const pillHandsMode = document.getElementById('pill-hands-mode');
  const badgeHandsIcon = document.getElementById('badge-hands-icon');
  const badgeHandsMode = document.getElementById('badge-hands-mode');
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
  const switchLaser = document.getElementById('switch-laser');
  const switchClahe = document.getElementById('switch-clahe');
  const valLaserStatus = document.getElementById('val-laser-status');

  // Bimanual Controls
  const switchTwoHands = document.getElementById('switch-two-hands');
  const btnDomRight = document.getElementById('btn-dom-right');
  const btnDomLeft = document.getElementById('btn-dom-left');

  // Click Mode Buttons
  const btnModeThumb = document.getElementById('btn-mode-thumb');
  const btnModePinch = document.getElementById('btn-mode-pinch');
  const modeHintText = document.getElementById('mode-hint-text');

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
    soundSynth.playRadialChime();
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
    const radialDockBtn = document.querySelector('.dock-btn[data-view="view-radial"]');
    if (radialDockBtn) radialDockBtn.click();
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

    // Audio triggers on gesture transition
    if (cleanName !== previousGesture) {
      if (cleanName.includes('PINCH') || cleanName.includes('THUMB')) soundSynth.playPinch();
      else if (cleanName.includes('RIGHT')) soundSynth.playRightClick();
      else if (cleanName.includes('DRAG')) soundSynth.playDragStart();
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
  switchClahe?.addEventListener('change', (e) => postSettings({ use_clahe: e.target.checked }));
  switchLegacyGestures?.addEventListener('change', (e) => postSettings({ enable_legacy_shortcuts: e.target.checked }));
  
  switchLaser?.addEventListener('change', (e) => {
    valLaserStatus.textContent = e.target.checked ? 'ЛАЗЕР ВКЛ' : 'Обычный';
    valLaserStatus.style.color = e.target.checked ? '#ff007f' : 'var(--aero-cyan)';
    soundSynth.playLaserFx();
    postSettings({ laser_pointer_mode: e.target.checked });
  });

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
    } else {
      pauseIndicator.classList.remove('paused');
      pauseBtnText.textContent = 'Пауза';
    }
    soundSynth.playPinch();
    postSettings({ manual_pause: newPauseState });
  });

  // Click Mode (Thumb Bend vs Pinch)
  btnModeThumb?.addEventListener('click', () => {
    btnModeThumb.classList.add('active');
    btnModePinch.classList.remove('active');
    modeHintText.innerHTML = 'Наведите курсор указательным пальцем и <strong>согните большой палец</strong> для клика без смещения мыши.';
    gaugeLabelTitle.textContent = 'Сгиб большого пальца';
    soundSynth.playPinch();
    postSettings({ click_mode: 'thumb_bend' });
  });

  btnModePinch?.addEventListener('click', () => {
    btnModePinch.classList.add('active');
    btnModeThumb.classList.remove('active');
    modeHintText.innerHTML = 'Сведите <strong>кончики большого и указательного пальцев</strong> (щипок) для клика, удерживайте для Drag & Drop.';
    gaugeLabelTitle.textContent = 'Сила щипка (Pinch)';
    soundSynth.playPinch();
    postSettings({ click_mode: 'pinch' });
  });

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
  // 8. 20 Hz Real-Time Telemetry Polling Loop
  // =========================================================================
  function pollStatus() {
    fetch('/api/status')
      .then(r => r.json())
      .then(data => {
        loadingOverlay.style.display = 'none';

        // Telemetry top badges
        badgeFps.textContent = `${data.fps || 0} FPS`;
        badgeLatency.textContent = `${data.latency_ms || 0} ms`;
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

        // Pinch force gauge
        const pct = Math.max(0, Math.min(100, Math.round(data.pinch_pct || 0)));
        pinchPercentText.textContent = `${pct}%`;
        pinchBarFill.style.width = `${pct}%`;

        // Update active gesture card
        updateCoreGestureHighlight(data.gesture);

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
      })
      .catch(() => {})
      .finally(() => setTimeout(pollStatus, 50));
  }

  // Start telemetry loop
  pollStatus();

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

});
