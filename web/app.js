/**
 * AeroPoint Studio — Neural Kinetic HCI Logic & Motion Design
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
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
  const loadingStatusText = document.getElementById('loading-status-text');

  // Badges & Telemetry
  const badgeFps = document.getElementById('badge-fps');
  const badgeLatency = document.getElementById('badge-latency');
  const badgeCpu = document.getElementById('badge-cpu');
  const badgePinchRatio = document.getElementById('badge-pinch-ratio');
  const trackingStatusBadge = document.getElementById('tracking-status-badge');
  const badgeAnchor = document.getElementById('badge-anchor');
  const pillAnchorStatus = document.getElementById('pill-anchor-status');
  const pillHandsMode = document.getElementById('pill-hands-mode');
  const badgeHandsIcon = document.getElementById('badge-hands-icon');
  const badgeHandsMode = document.getElementById('badge-hands-mode');

  // Two-Handed Control Elements
  const switchTwoHands = document.getElementById('switch-two-hands');
  const btnDomRight = document.getElementById('btn-dom-right');
  const btnDomLeft = document.getElementById('btn-dom-left');
  const valDominantHand = document.getElementById('val-dominant-hand');

  // Gesture Banner & Dynamic Gauge
  const bannerIcon = document.getElementById('gesture-banner-icon');
  const bannerTitle = document.getElementById('gesture-banner-title');
  const bannerSub = document.getElementById('gesture-banner-sub');
  const pinchBarFill = document.getElementById('pinch-bar-fill');
  const pinchPercentText = document.getElementById('pinch-percent-text');
  const gaugeLabelTitle = document.getElementById('gauge-label-title');

  // Sliders
  const sliderSensitivity = document.getElementById('slider-sensitivity');
  const valSensitivity = document.getElementById('val-sensitivity');
  const sliderSmooth = document.getElementById('slider-smooth');
  const valSmooth = document.getElementById('val-smooth');
  const sliderDeadzone = document.getElementById('slider-deadzone');
  const valDeadzone = document.getElementById('val-deadzone');
  const sliderReach = document.getElementById('slider-reach');
  const valReach = document.getElementById('val-reach');
  const sliderPinch = document.getElementById('slider-pinch');
  const valPinch = document.getElementById('val-pinch');

  // Switches
  const switchAnchor = document.getElementById('switch-anchor');
  const switchAcceleration = document.getElementById('switch-acceleration');
  const switchClahe = document.getElementById('switch-clahe');
  const switchSkeleton = document.getElementById('switch-skeleton');
  const switchSound = document.getElementById('switch-sound');

  // Mode Segment Buttons
  const btnModeThumb = document.getElementById('btn-mode-thumb');
  const btnModePinch = document.getElementById('btn-mode-pinch');
  const tagCurrentMode = document.getElementById('tag-current-mode');
  const modeHintText = document.getElementById('mode-hint-text');

  // Gesture Cards Dictionary with exact matching and normalization
  const gestureCards = {
    'HOVER': { icon: '☝️', title: 'Наведение', sub: 'Плавное позиционирование', card: 'card-hover' },
    'HOVER (MOVE)': { icon: '☝️', title: 'Наведение', sub: 'Плавное позиционирование', card: 'card-hover' },
    'PINCH (LEFT CLICK)': { icon: '🤏', title: 'Щипок (ЛКМ)', sub: 'Левый клик мыши', card: 'card-pinch' },
    'THUMB BEND (LEFT CLICK)': { icon: '👍', title: 'Сгиб пальца (ЛКМ)', sub: 'Стабильный левый клик', card: 'card-pinch' },
    'RIGHT CLICK': { icon: '👌', title: 'Правый клик', sub: 'Контекстное меню', card: 'card-right' },
    'MIDDLE CLICK (WHEEL)': { icon: '🔘', title: 'Колёсико мыши', sub: 'Безымянный палец', card: 'card-middle' },
    'TASK SWITCH (WIN+TAB)': { icon: '🪟', title: 'Обзор окон (Win+Tab)', sub: 'Щипок мизинцем', card: 'card-task' },
    'QUICK ALT+TAB': { icon: '🤘', title: 'Смена окна (Alt+Tab)', sub: 'Рок-жест', card: 'card-rock' },
    'SHOW DESKTOP (WIN+D)': { icon: '🤙', title: 'Свернуть всё (Win+D)', sub: 'Шака-жест', card: 'card-shaka' },
    'SCROLL': { icon: '✌️', title: 'Прокрутка', sub: 'Скролл двумя пальцами', card: 'card-scroll' },
    'DRAG': { icon: '✊', title: 'Зажатие (Drag)', sub: 'Перетаскивание объектов', card: 'card-drag' },
    'DRAG & DROP': { icon: '✊', title: 'Зажатие (Drag)', sub: 'Перетаскивание объектов', card: 'card-drag' },
    'PAUSE': { icon: '🖐️', title: 'Защитная пауза', sub: 'Открытая ладонь', card: 'card-pause' },
    'PAUSE (NEUTRAL)': { icon: '🖐️', title: 'Защитная пауза', sub: 'Открытая ладонь', card: 'card-pause' },
    'NO HAND': { icon: '🔍', title: 'Поиск руки', sub: 'Поместите ладонь в кадр', card: null }
  };

  function resolveGestureInfo(gest) {
    if (!gest) return gestureCards['NO HAND'];
    const g = gest.trim();
    if (gestureCards[g]) return gestureCards[g];
    if (g.includes('MIDDLE')) return gestureCards['MIDDLE CLICK (WHEEL)'];
    if (g.includes('TASK')) return gestureCards['TASK SWITCH (WIN+TAB)'];
    if (g.includes('ALT+TAB') || g.includes('ROCK')) return gestureCards['QUICK ALT+TAB'];
    if (g.includes('DESKTOP') || g.includes('SHAKA')) return gestureCards['SHOW DESKTOP (WIN+D)'];
    if (g.includes('HOVER')) return gestureCards['HOVER (MOVE)'];
    if (g.includes('THUMB')) return gestureCards['THUMB BEND (LEFT CLICK)'];
    if (g.includes('PINCH')) return gestureCards['PINCH (LEFT CLICK)'];
    if (g.includes('RIGHT')) return gestureCards['RIGHT CLICK'];
    if (g.includes('SCROLL')) return gestureCards['SCROLL'];
    if (g.includes('DRAG')) return gestureCards['DRAG & DROP'];
    if (g.includes('PAUSE')) return gestureCards['PAUSE'];
    return gestureCards['NO HAND'];
  }

  let isPaused = false;
  let frameReceived = false;
  let pollingInterval = null;
  let prevGesture = 'NO HAND';

  // --- Synthetic Microswitch Click Sound (Web Audio API) ---
  let audioCtx = null;
  function playHapticClick(isRight = false) {
    if (!switchSound || !switchSound.checked) return;
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      osc.type = 'triangle';
      const baseFreq = isRight ? 720 : 980;
      osc.frequency.setValueAtTime(baseFreq, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(120, audioCtx.currentTime + 0.012);

      gain.gain.setValueAtTime(0.18, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.012);

      osc.connect(gain);
      gain.connect(audioCtx.destination);

      osc.start();
      osc.stop(audioCtx.currentTime + 0.015);
    } catch (e) {
      // AudioContext unavailable or suppressed
    }
  }

  // --- Motion Design 1: Click Shockwave Ripple Effect ---
  function triggerShockwave() {
    const viewport = document.querySelector('.stream-viewport');
    if (!viewport) return;
    const wave = document.createElement('div');
    wave.className = 'click-shockwave';
    wave.style.width = '70px';
    wave.style.height = '70px';
    wave.style.left = 'calc(50% - 35px)';
    wave.style.top = 'calc(50% - 35px)';
    viewport.appendChild(wave);
    setTimeout(() => wave.remove(), 550);
  }

  // --- Motion Design 2: 3D Perspective Tilt on Cards ---
  function initCardTilt() {
    const cards = document.querySelectorAll('.kinetic-card');
    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left - (rect.width / 2);
        const y = e.clientY - rect.top - (rect.height / 2);
        const rotateX = (-y / rect.height) * 6;
        const rotateY = (x / rect.width) * 6;
        card.style.transform = `perspective(800px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-2px)`;
      });
      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg) translateY(0px)';
      });
    });
  }
  initCardTilt();

  // --- Stream Reception & Smart Failover ---
  function markFrameLoaded() {
    frameReceived = true;
    if (loadingOverlay) {
      loadingOverlay.classList.add('hidden');
    }
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }

  streamImg.addEventListener('load', markFrameLoaded);
  streamImg.addEventListener('error', () => {
    console.warn('[AeroPoint] Stream dropped, engaging fallback polling...');
    startSnapshotFallback();
  });

  function startSnapshotFallback() {
    if (pollingInterval) return;
    console.log('[AeroPoint] Running snapshot fallback...');
    pollingInterval = setInterval(() => {
      const img = new Image();
      img.onload = () => {
        streamImg.src = img.src;
        markFrameLoaded();
      };
      img.src = '/api/frame.jpg?t=' + Date.now();
    }, 60);
  }

  // --- 1. Load Real DirectShow Cameras List ---
  async function loadCameras() {
    try {
      const res = await fetch('/api/cameras');
      const data = await res.json();
      cameraSelect.innerHTML = '';

      if (!data.cameras || data.cameras.length === 0) {
        const opt = document.createElement('option');
        opt.textContent = 'Камеры не найдены';
        cameraSelect.appendChild(opt);
        return;
      }

      data.cameras.forEach(cam => {
        const opt = document.createElement('option');
        opt.value = cam.id;
        opt.textContent = `${cam.label} [ID: ${cam.id}]`;
        if (cam.id === data.active_id) {
          opt.selected = true;
        }
        cameraSelect.appendChild(opt);
      });
    } catch (e) {
      console.error('Error loading cameras:', e);
    }
  }

  // Camera change event (Strict DirectShow Index Match)
  cameraSelect.addEventListener('change', async (e) => {
    const camId = parseInt(e.target.value);
    const selectedText = cameraSelect.options[cameraSelect.selectedIndex]?.text || `Камера #${camId}`;
    
    if (loadingOverlay) {
      loadingOverlay.classList.remove('hidden');
      if (loadingStatusText) loadingStatusText.textContent = `Подключение: ${selectedText}...`;
    }
    frameReceived = false;

    try {
      const res = await fetch('/api/select_camera', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: camId })
      });
      const data = await res.json();
      if (data && data.active_id !== undefined) {
        cameraSelect.value = data.active_id;
      }
      setTimeout(() => {
        streamImg.src = '/video_feed?t=' + Date.now();
      }, 350);
    } catch (err) {
      console.error('Error selecting camera:', err);
      loadCameras();
    }
  });

  btnRefreshCams.addEventListener('click', loadCameras);

  // --- 1.5 Click Mode Segmented Selector ---
  if (btnModeThumb && btnModePinch) {
    btnModeThumb.addEventListener('click', async () => {
      btnModeThumb.classList.add('active');
      btnModePinch.classList.remove('active');
      tagCurrentMode.textContent = 'Сгиб пальца';
      if (gaugeLabelTitle) gaugeLabelTitle.textContent = 'Угол сгиба пальца';
      modeHintText.innerHTML = '☝️ <strong>Рекомендовано:</strong> наведите курсор указательным пальцем и согните большой палец для 100% стабильного клика без смещения мыши.';
      await sendSettings({ click_mode: 'thumb_bend' });
    });

    btnModePinch.addEventListener('click', async () => {
      btnModePinch.classList.add('active');
      btnModeThumb.classList.remove('active');
      tagCurrentMode.textContent = 'Щипок (Pinch)';
      if (gaugeLabelTitle) gaugeLabelTitle.textContent = 'Сила щипка (Pinch)';
      modeHintText.innerHTML = '🤏 <strong>Классический щипок:</strong> соприкосновение кончиков большого и указательного пальцев.';
      await sendSettings({ click_mode: 'pinch' });
    });
  }

  // --- 1.6 Two-Handed (Bimanual) Controls ---
  if (switchTwoHands) {
    switchTwoHands.addEventListener('change', async (e) => {
      await sendSettings({ enable_two_hands: e.target.checked });
    });
  }

  if (btnDomRight && btnDomLeft) {
    btnDomRight.addEventListener('click', async () => {
      btnDomRight.classList.add('active');
      btnDomLeft.classList.remove('active');
      if (valDominantHand) valDominantHand.textContent = 'Правая';
      await sendSettings({ dominant_hand: 'Right' });
    });

    btnDomLeft.addEventListener('click', async () => {
      btnDomLeft.classList.add('active');
      btnDomRight.classList.remove('active');
      if (valDominantHand) valDominantHand.textContent = 'Левая';
      await sendSettings({ dominant_hand: 'Left' });
    });
  }

  // --- 0. Source Tabs: Webcam vs iPhone Spatial ---
  const tabBtnWebcam = document.getElementById('tab-btn-webcam');
  const tabBtnIphone = document.getElementById('tab-btn-iphone');
  const cameraPickerWrap = document.getElementById('camera-picker-wrap');
  const iphoneDashboardCard = document.getElementById('iphone-dashboard-card');
  const badgeIphoneConn = document.getElementById('badge-iphone-conn');
  const valIphoneSensor = document.getElementById('val-iphone-sensor');
  const valIphonePing = document.getElementById('val-iphone-ping');
  const valIphoneBattery = document.getElementById('val-iphone-battery');
  const valIphoneDepth = document.getElementById('val-iphone-depth');
  const barIphoneDepth = document.getElementById('bar-iphone-depth');

  const btnOpenIosGuide = document.getElementById('btn-open-ios-guide');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const modalIosGuide = document.getElementById('modal-ios-guide');

  if (tabBtnWebcam && tabBtnIphone) {
    tabBtnWebcam.addEventListener('click', async () => {
      tabBtnWebcam.classList.add('active');
      tabBtnIphone.classList.remove('active');
      if (cameraPickerWrap) cameraPickerWrap.style.display = 'flex';
      if (iphoneDashboardCard) iphoneDashboardCard.style.display = 'none';
      await fetch('/api/switch_tab', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tab: 'webcam' })
      });
    });

    tabBtnIphone.addEventListener('click', async () => {
      tabBtnIphone.classList.add('active');
      tabBtnWebcam.classList.remove('active');
      if (cameraPickerWrap) cameraPickerWrap.style.display = 'none';
      if (iphoneDashboardCard) iphoneDashboardCard.style.display = 'block';
      await fetch('/api/switch_tab', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tab: 'iphone' })
      });
    });
  }

  if (btnOpenIosGuide && modalIosGuide) {
    btnOpenIosGuide.addEventListener('click', () => {
      modalIosGuide.classList.add('open');
    });
  }
  if (btnCloseModal && modalIosGuide) {
    btnCloseModal.addEventListener('click', () => {
      modalIosGuide.classList.remove('open');
    });
  }
  if (modalIosGuide) {
    modalIosGuide.addEventListener('click', (e) => {
      if (e.target === modalIosGuide) modalIosGuide.classList.remove('open');
    });
  }

  // --- LAN Info & Mobile QR Code ---
  const qrCodeImg = document.getElementById('qr-code-img');
  const mobileUrlText = document.getElementById('mobile-url-text');
  const btnCopyUrl = document.getElementById('btn-copy-url');

  async function loadLanInfo() {
    try {
      const res = await fetch('/api/lan_info');
      if (res.ok) {
        const data = await res.json();
        if (data.mobile_url) {
          if (mobileUrlText) mobileUrlText.textContent = data.mobile_url;
          if (qrCodeImg) {
            qrCodeImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=110x110&data=${encodeURIComponent(data.mobile_url)}`;
          }
        }
      }
    } catch (e) {
      console.warn("Failed to fetch LAN info", e);
    }
  }
  loadLanInfo();

  if (btnCopyUrl && mobileUrlText) {
    btnCopyUrl.addEventListener('click', () => {
      navigator.clipboard.writeText(mobileUrlText.textContent);
      const orig = btnCopyUrl.textContent;
      btnCopyUrl.textContent = '✓';
      setTimeout(() => { btnCopyUrl.textContent = orig; }, 1500);
    });
  }

  // --- 2. Master Control Switch ---
  masterControlSwitch.addEventListener('change', async (e) => {
    const enabled = e.target.checked;
    controlStateSub.textContent = enabled ? 'Включено' : 'Предпросмотр';
    controlStateSub.style.color = enabled ? 'var(--aero-emerald)' : 'var(--text-tertiary)';
    await sendSettings({ control_enabled: enabled });
  });

  // --- 3. Safety Pause Toggle ---
  btnSafetyPause.addEventListener('click', async () => {
    isPaused = !isPaused;
    updatePauseUI(isPaused);
    await sendSettings({ manual_pause: isPaused });
  });

  function updatePauseUI(paused) {
    if (paused) {
      pauseIndicator.classList.add('paused');
      pauseBtnText.textContent = 'На паузе';
      btnSafetyPause.style.borderColor = 'var(--aero-amber)';
    } else {
      pauseIndicator.classList.remove('paused');
      pauseBtnText.textContent = 'Пауза';
      btnSafetyPause.style.borderColor = 'var(--surface-border)';
    }
  }

  // --- 4. Sliders ---
  if (sliderSensitivity) {
    sliderSensitivity.addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      const tag = v >= 2.5 ? 'Максимум' : (v >= 1.6 ? 'Быстро' : 'Стандарт');
      valSensitivity.textContent = `${v.toFixed(1)}x (${tag})`;
    });
    sliderSensitivity.addEventListener('change', async (e) => {
      await sendSettings({ sensitivity: parseFloat(e.target.value) });
    });
  }

  sliderSmooth.addEventListener('input', (e) => {
    valSmooth.textContent = `${e.target.value} Hz`;
  });
  sliderSmooth.addEventListener('change', async (e) => {
    await sendSettings({ smoothing_alpha: parseFloat(e.target.value) });
  });

  sliderDeadzone.addEventListener('input', (e) => {
    valDeadzone.textContent = `${e.target.value} px`;
  });
  sliderDeadzone.addEventListener('change', async (e) => {
    await sendSettings({ deadzone_radius: parseFloat(e.target.value) });
  });

  sliderReach.addEventListener('input', (e) => {
    const pct = Math.round(parseFloat(e.target.value) * 100);
    valReach.textContent = `${pct}% (${pct <= 8 ? 'Широкий' : 'Компактный'})`;
  });
  sliderReach.addEventListener('change', async (e) => {
    const val = parseFloat(e.target.value);
    await sendSettings({ margin_x: val, margin_y: val + 0.02 });
  });

  sliderPinch.addEventListener('input', (e) => {
    valPinch.textContent = e.target.value;
  });
  sliderPinch.addEventListener('change', async (e) => {
    await sendSettings({ pinch_activate_ratio: parseFloat(e.target.value) });
  });

  // --- 5. Switches ---
  switchAnchor.addEventListener('change', async (e) => {
    await sendSettings({ enable_anchor: e.target.checked });
  });
  switchAcceleration.addEventListener('change', async (e) => {
    await sendSettings({ enable_acceleration: e.target.checked });
  });
  switchClahe.addEventListener('change', async (e) => {
    await sendSettings({ use_clahe: e.target.checked });
  });
  switchSkeleton.addEventListener('change', async (e) => {
    await sendSettings({ show_skeleton: e.target.checked });
  });
  switchSound.addEventListener('change', async (e) => {
    await sendSettings({ enable_sound: e.target.checked });
  });

  async function sendSettings(payload) {
    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (err) {
      console.error('Error updating settings:', err);
    }
  }

  // --- 6. Telemetry Polling Loop ---
  async function pollStatus() {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        
        badgeFps.textContent = `${data.fps} FPS`;
        badgeLatency.textContent = `${data.latency_ms} ms`;
        badgeCpu.textContent = `${data.cpu} %`;
        badgePinchRatio.textContent = data.pinch_ratio;

        if (data.fps > 0) {
          markFrameLoaded();
        }

        // Tracking status badge
        if (data.hand_detected) {
          trackingStatusBadge.textContent = data.is_dual_hand ? '2 РУКИ (BIMANUAL)' : 'ТРЕКИНГ';
          trackingStatusBadge.style.color = data.is_dual_hand ? 'var(--aero-violet)' : 'var(--aero-emerald)';
          trackingStatusBadge.style.background = data.is_dual_hand ? 'rgba(139, 92, 246, 0.20)' : 'rgba(16, 185, 129, 0.16)';
        } else {
          trackingStatusBadge.textContent = 'СКАНИРОВАНИЕ';
          trackingStatusBadge.style.color = 'var(--text-secondary)';
          trackingStatusBadge.style.background = 'rgba(255, 255, 255, 0.08)';
        }

        // Bimanual / Two-handed mode capsule indicator
        if (pillHandsMode && badgeHandsMode && badgeHandsIcon) {
          if (data.is_dual_hand) {
            pillHandsMode.classList.add('dual-active');
            badgeHandsIcon.textContent = '🖐️🖐️';
            badgeHandsMode.textContent = '2 Руки (Бимануальный)';
            badgeHandsMode.style.color = 'var(--aero-violet)';
          } else if (data.hands_count === 1) {
            pillHandsMode.classList.remove('dual-active');
            badgeHandsIcon.textContent = '🖐️';
            badgeHandsMode.textContent = '1 Рука';
            badgeHandsMode.style.color = 'var(--aero-cyan)';
          } else {
            pillHandsMode.classList.remove('dual-active');
            badgeHandsIcon.textContent = '🔍';
            badgeHandsMode.textContent = '0 Рук';
            badgeHandsMode.style.color = 'var(--text-tertiary)';
          }
        }

        // Click Anchor Indicator
        if (data.is_anchored) {
          pillAnchorStatus.classList.add('anchor-active');
          badgeAnchor.textContent = 'Якорь: ЗАФИКСИРОВАН';
          badgeAnchor.style.color = 'var(--aero-blue)';
        } else {
          pillAnchorStatus.classList.remove('anchor-active');
          badgeAnchor.textContent = 'Якорь: Свободно';
          badgeAnchor.style.color = 'var(--aero-cyan)';
        }

        // Update iPhone Spatial Status
        if (data.iphone_status) {
          const iph = data.iphone_status;
          if (badgeIphoneConn) {
            badgeIphoneConn.textContent = iph.connected ? 'ПОДКЛЮЧЕНО' : 'ОЖИДАНИЕ';
            badgeIphoneConn.className = `sensor-badge ${iph.connected ? 'active' : 'disconnected'}`;
          }
          if (valIphoneSensor) valIphoneSensor.textContent = iph.sensor;
          if (valIphonePing) valIphonePing.textContent = `${iph.latency_ms.toFixed(1)} ms`;
          if (valIphoneBattery) valIphoneBattery.textContent = `${iph.battery}%`;
          if (valIphoneDepth) valIphoneDepth.textContent = `${Math.round(iph.depth_mm)} mm`;
          if (barIphoneDepth) {
            const zPct = Math.max(10, Math.min(100, (iph.depth_mm / 800.0) * 100));
            barIphoneDepth.style.width = `${zPct}%`;
          }
        }

        // Live Dynamic Gauge update
        const pct = Math.max(0, Math.min(100, data.pinch_pct || 0));
        pinchBarFill.style.width = `${pct}%`;
        pinchPercentText.textContent = `${Math.round(pct)}%`;
        if (pct >= 90) {
          pinchBarFill.style.background = 'linear-gradient(90deg, var(--aero-cyan), var(--aero-emerald))';
        } else {
          pinchBarFill.style.background = 'linear-gradient(90deg, var(--aero-blue), var(--aero-cyan))';
        }

        // Gesture Trigger Events (Sound & Shockwave)
        const isLeftClick = (data.gesture === 'PINCH (LEFT CLICK)' || data.gesture === 'THUMB BEND (LEFT CLICK)');
        const wasLeftClick = (prevGesture === 'PINCH (LEFT CLICK)' || prevGesture === 'THUMB BEND (LEFT CLICK)');
        if (isLeftClick && !wasLeftClick) {
          playHapticClick(false);
          triggerShockwave();
        } else if (data.gesture === 'RIGHT CLICK' && prevGesture !== 'RIGHT CLICK') {
          playHapticClick(true);
          triggerShockwave();
        }
        prevGesture = data.gesture;

        // Sync click mode indicator
        if (data.click_mode === 'thumb_bend') {
          if (btnModeThumb && !btnModeThumb.classList.contains('active')) {
            btnModeThumb.classList.add('active');
            btnModePinch.classList.remove('active');
            tagCurrentMode.textContent = 'Сгиб пальца';
            if (gaugeLabelTitle) gaugeLabelTitle.textContent = 'Угол сгиба пальца';
          }
        } else if (data.click_mode === 'pinch') {
          if (btnModePinch && !btnModePinch.classList.contains('active')) {
            btnModePinch.classList.add('active');
            btnModeThumb.classList.remove('active');
            tagCurrentMode.textContent = 'Щипок (Pinch)';
            if (gaugeLabelTitle) gaugeLabelTitle.textContent = 'Сила щипка (Pinch)';
          }
        }

        // Gesture Banner update with guaranteed resolution
        const gestureInfo = resolveGestureInfo(data.gesture);
        bannerIcon.textContent = gestureInfo.icon;
        bannerTitle.textContent = gestureInfo.title;
        if (data.is_dual_hand && data.action_gesture && data.action_gesture !== 'NONE') {
          const actInfo = resolveGestureInfo(data.action_gesture);
          bannerSub.textContent = `Командная рука: ${actInfo.title}`;
        } else {
          bannerSub.textContent = gestureInfo.sub;
        }

        // Gesture Cards Highlighting
        Object.values(gestureCards).forEach(g => {
          if (g.card) {
            const el = document.getElementById(g.card);
            if (el) el.classList.remove('active');
          }
        });

        if (gestureInfo.card) {
          const activeEl = document.getElementById(gestureInfo.card);
          if (activeEl) activeEl.classList.add('active');
        }
      }
    } catch (e) {
      // Telemetry poll error
    }
  }

  // Initial load
  loadCameras();
  setInterval(pollStatus, 100);
  const inspector = document.querySelector('.inspector-section');
  if (inspector) {
    setTimeout(() => { inspector.scrollTop = 0; }, 100);
  }
});
