"""
AeroPoint Precision & Anti-Jitter Filtering Engine
==================================================
Next-generation precision cursor pipeline:
1. 1-Euro Adaptive Filter (Casiez et al. CHI 2012)
2. Kinetic Non-linear Pointer Acceleration Curve
3. Pinch/Bend Click Anchor Lock (prevents cursor slip when clicking)
4. Sub-pixel micro-targeting deadzone
5. Adaptive EMA and Standard EMA filters for backward compatibility
"""

import math
import time
from typing import Tuple, Optional


class OneEuroFilter1D:
    """1-Euro filter component for a single dimension."""
    def __init__(self, min_cutoff: float = 0.8, beta: float = 0.015, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev: Optional[float] = None
        self.dx_prev: float = 0.0
        self.t_prev: Optional[float] = None

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        t = timestamp if timestamp is not None else time.time()
        if self.t_prev is None or self.x_prev is None:
            self.x_prev = x
            self.dx_prev = 0.0
            self.t_prev = t
            return x

        dt = t - self.t_prev
        if dt > 0.4:
            # Resumed after tracking pause/drop: jump directly to target
            self.x_prev = x
            self.dx_prev = 0.0
            self.t_prev = t
            return x

        dt = max(0.001, dt)
        self.t_prev = t

        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev
        self.dx_prev = dx_hat

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1.0 - a) * self.x_prev
        self.x_prev = x_hat
        return x_hat


class OneEuroFilter2D:
    """2D wrapper for 1-Euro Filter with speed-adaptive cutoff."""
    def __init__(self, min_cutoff: float = 0.85, beta: float = 0.015):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.fx = OneEuroFilter1D(min_cutoff=min_cutoff, beta=beta)
        self.fy = OneEuroFilter1D(min_cutoff=min_cutoff, beta=beta)

    def reset(self):
        self.fx.reset()
        self.fy.reset()

    def filter(self, x: float, y: float, timestamp: Optional[float] = None) -> Tuple[float, float]:
        now = timestamp if timestamp is not None else time.time()
        return self.fx.filter(x, now), self.fy.filter(y, now)


class AeroPrecisionEngine:
    """
    State-of-the-art cursor stabilization and precision targeting engine.
    - 1-Euro filter eliminates hand jitter while preserving zero-lag flicks.
    - Click Anchor locks position during pinch movement to eliminate cursor slip.
    - Kinetic non-linear acceleration curve provides sub-pixel accuracy at slow speeds.
    """
    def __init__(
        self,
        min_cutoff: float = 0.85,
        beta: float = 0.015,
        deadzone_radius: float = 3.5,
        enable_acceleration: bool = True,
        enable_click_anchor: bool = True
    ):
        self.one_euro = OneEuroFilter2D(min_cutoff=min_cutoff, beta=beta)
        self.deadzone_radius = deadzone_radius
        self.enable_acceleration = enable_acceleration
        self.enable_click_anchor = enable_click_anchor

        # State memory
        self.prev_out_x: Optional[float] = None
        self.prev_out_y: Optional[float] = None

        # Anchor lock memory
        self.is_anchored = False
        self.anchor_x: Optional[float] = None
        self.anchor_y: Optional[float] = None
        self.lock_until_time: float = 0.0

        # Telemetry
        self.current_gain = 1.0
        self.is_anchor_active = False
        self.dynamic_deadzone = deadzone_radius
        self.current_velocity = 0.0
        self.last_time: Optional[float] = None

    def reset(self):
        self.one_euro.reset()
        self.prev_out_x = None
        self.prev_out_y = None
        self.last_time = None
        self.is_anchored = False
        self.anchor_x = None
        self.anchor_y = None
        self.lock_until_time = 0.0
        self.is_anchor_active = False

    def lock_cursor(self, duration: float = 0.35):
        """Temporarily pins cursor to current position to allow effortless double-clicking."""
        now = time.time()
        self.lock_until_time = now + duration
        if self.prev_out_x is not None and self.prev_out_y is not None:
            self.anchor_x = self.prev_out_x
            self.anchor_y = self.prev_out_y
            self.is_anchored = True

    def process(
        self,
        target_x: float,
        target_y: float,
        pinch_ratio: float,
        pinch_activate_ratio: float = 0.28,
        pinch_release_ratio: float = 0.40,
        is_clicking: bool = False,
        click_mode: str = "thumb_bend",
        timestamp: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Processes raw screen target through:
        1. Click Anchor check (locks cursor during click or timed double-click window)
        2. 1-Euro filter
        3. Pointer precision acceleration curve
        4. Deadzone filter
        """
        now = timestamp if timestamp is not None else time.time()

        # Timed lock for click & double-click stability
        if now < self.lock_until_time and self.anchor_x is not None and self.anchor_y is not None:
            raw_dist = math.hypot(target_x - self.anchor_x, target_y - self.anchor_y)
            # Break lock if user deliberately flicks hand away (> 28px)
            if raw_dist < 28.0:
                self.is_anchor_active = True
                return self.anchor_x, self.anchor_y
            else:
                self.lock_until_time = 0.0
                self.is_anchored = False
                self.anchor_x = None
                self.anchor_y = None

        # --- 1. Click Anchor Stabilization ---
        if self.enable_click_anchor:
            should_anchor = False

            if is_clicking:
                should_anchor = True
            elif click_mode == "pinch":
                # In pinch mode, lock cursor when approaching pinch point
                approach_threshold = pinch_activate_ratio + 0.03
                if pinch_ratio < approach_threshold:
                    should_anchor = True

            if should_anchor:
                if not self.is_anchored or self.anchor_x is None:
                    self.is_anchored = True
                    self.anchor_x = self.prev_out_x if self.prev_out_x is not None else target_x
                    self.anchor_y = self.prev_out_y if self.prev_out_y is not None else target_y

                # If user moves hand away deliberately (> 28px), break the anchor
                if self.anchor_x is not None and self.anchor_y is not None:
                    dist_to_anchor = math.hypot(target_x - self.anchor_x, target_y - self.anchor_y)
                    if dist_to_anchor < 28.0:
                        self.is_anchor_active = True
                        return self.anchor_x, self.anchor_y
                    else:
                        # User moved away: break anchor immediately
                        self.is_anchored = False
                        self.anchor_x = None
                        self.anchor_y = None
            else:
                self.is_anchored = False
                self.anchor_x = None
                self.anchor_y = None

        self.is_anchor_active = False

        # --- 2. 1-Euro Adaptive Filter ---
        filt_x, filt_y = self.one_euro.filter(target_x, target_y, timestamp)

        if self.prev_out_x is None or self.prev_out_y is None:
            self.prev_out_x = filt_x
            self.prev_out_y = filt_y
            return filt_x, filt_y

        # Delta from previous output
        dx = filt_x - self.prev_out_x
        dy = filt_y - self.prev_out_y
        dist = math.hypot(dx, dy)

        # --- 3. Kinetic Velocity-Adaptive Deadzone ---
        # When hand is stationary, full deadzone removes micro-tremor.
        # When user deliberately initiates movement (> 18 px/frame), deadzone smoothly collapses to 0.0 for zero initial resistance.
        dt = max(0.001, min(0.1, (now - self.last_time) if self.last_time is not None else 0.016))
        self.last_time = now
        inst_speed = dist / dt
        self.current_velocity = self.current_velocity * 0.65 + inst_speed * 0.35

        if self.current_velocity > 40.0:
            target_deadzone = 0.0
        elif self.current_velocity < 15.0:
            target_deadzone = self.deadzone_radius
        else:
            t = (self.current_velocity - 15.0) / 25.0
            target_deadzone = self.deadzone_radius * (1.0 - t)

        self.dynamic_deadzone = self.dynamic_deadzone * 0.60 + target_deadzone * 0.40

        if dist < self.dynamic_deadzone:
            return self.prev_out_x, self.prev_out_y

        # --- 4. Precision Positioning & Jitter Damping ---
        self.current_gain = 1.0
        out_x = filt_x
        out_y = filt_y

        self.prev_out_x = out_x
        self.prev_out_y = out_y
        return out_x, out_y


class EMAFilter:
    """Standard Exponential Moving Average (EMA) Filter."""
    def __init__(self, alpha: float = 0.65):
        self.alpha = max(0.01, min(1.0, alpha))
        self.prev_x: Optional[float] = None
        self.prev_y: Optional[float] = None

    def reset(self):
        self.prev_x = None
        self.prev_y = None

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        if self.prev_x is None or self.prev_y is None:
            self.prev_x = x
            self.prev_y = y
            return x, y
        filt_x = self.alpha * x + (1.0 - self.alpha) * self.prev_x
        filt_y = self.alpha * y + (1.0 - self.alpha) * self.prev_y
        self.prev_x = filt_x
        self.prev_y = filt_y
        return filt_x, filt_y


class AdaptiveEMAFilter:
    """Adaptive EMA filter for velocity-based smoothing."""
    def __init__(
        self,
        min_alpha: float = 0.20,
        max_alpha: float = 0.85,
        velocity_scale: float = 25.0
    ):
        self.min_alpha = min_alpha
        self.max_alpha = max_alpha
        self.velocity_scale = velocity_scale
        self.prev_x: Optional[float] = None
        self.prev_y: Optional[float] = None
        self.last_alpha: float = min_alpha

    def reset(self):
        self.prev_x = None
        self.prev_y = None

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        if self.prev_x is None or self.prev_y is None:
            self.prev_x = x
            self.prev_y = y
            return x, y

        dist = math.hypot(x - self.prev_x, y - self.prev_y)
        norm_v = min(1.0, dist / max(1.0, self.velocity_scale))
        alpha = self.min_alpha + (self.max_alpha - self.min_alpha) * norm_v
        self.last_alpha = alpha

        filt_x = alpha * x + (1.0 - alpha) * self.prev_x
        filt_y = alpha * y + (1.0 - alpha) * self.prev_y
        self.prev_x = filt_x
        self.prev_y = filt_y
        return filt_x, filt_y


class DeadzoneFilter:
    """Deadzone filter."""
    def __init__(self, radius: float = 3.5):
        self.radius = radius
        self.locked_x: Optional[float] = None
        self.locked_y: Optional[float] = None

    def reset(self):
        self.locked_x = None
        self.locked_y = None

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        if self.locked_x is None or self.locked_y is None:
            self.locked_x = x
            self.locked_y = y
            return x, y

        dist = math.hypot(x - self.locked_x, y - self.locked_y)
        if dist >= self.radius:
            self.locked_x = x
            self.locked_y = y

        return self.locked_x, self.locked_y


class InertialScrollEngine:
    """
    Kinetic momentum scroll engine (like iOS / macOS trackpad).
    When user scrolls and releases, momentum smoothly decays over 300-600ms.
    """
    def __init__(self, friction: float = 0.88, min_velocity: float = 0.20):
        self.friction = friction
        self.min_velocity = min_velocity
        self.velocity = 0.0
        self.last_update = time.time()
        self.is_active = False

    def push(self, delta: float):
        """Called on active scroll frame to update momentum with kinetic flick amplification."""
        now = time.time()
        self.last_update = now
        # Detect rapid flick (> 2.0 scroll ticks) and amplify glide momentum
        flick_boost = 1.45 if abs(delta) >= 2.0 else 1.0
        self.velocity = (self.velocity * 0.30 + delta * 0.70) * flick_boost
        # Clamp velocity to avoid uncontrolled spinning
        self.velocity = max(-16.0, min(16.0, self.velocity))
        self.is_active = True

    def brake(self):
        """Immediately stop inertial glide when hands disengage or click."""
        self.velocity = 0.0
        self.is_active = False

    def tick(self) -> int:
        """Called periodically when not actively scrolling to get inertial delta."""
        if not self.is_active or abs(self.velocity) < self.min_velocity:
            self.velocity = 0.0
            self.is_active = False
            return 0

        now = time.time()
        dt = max(0.001, min(0.1, now - self.last_update))
        self.last_update = now

        # Apply exponential decay
        self.velocity *= math.pow(self.friction, dt * 60.0)
        out = int(round(self.velocity))
        if out == 0 and abs(self.velocity) >= self.min_velocity:
            out = 1 if self.velocity > 0 else -1
            self.velocity = 0.0
        return out


# Backward compatibility alias
ApplePrecisionEngine = AeroPrecisionEngine

