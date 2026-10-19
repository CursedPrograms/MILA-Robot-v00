"""gamepad_drive.py - drive with any joystick pygame sees: a gamepad, or ARM's flight stick.

Plug it in or pull it out at any time (hot-plug). The same file in the controllers that use it.

    pad = PadDrive()
    ...in the event loop:   pad.handle(ev)
    ...every frame:         pad.direction()  -> "fw" / "bw" / "left" / "right" / "turnL" / "turnR" / None
                            pad.presses()    -> buttons pressed since the last frame, e.g. {0, 3}
                            pad.rumble(*rumble_level(cm_ahead))   -> buzz as a wall gets close

Drive: the left stick, the D-pad (hat) or a flight stick. Turn: LB / RB (buttons 4 / 5), the right
stick across, or a flight stick's twist. An axis that rests far from the middle when the pad is
plugged in (a trigger, a throttle) is never read as steering.

Rumble (KIDA-01's haptics.py, for every pad): while you drive, the light motor buzzes from WARN_CM
on, harder the closer the wall in the way, full at STOP_CM; a tipping robot shakes both motors full.
"""
import time

import pygame

DEAD = 0.4          # stick travel that counts as pushed
TURN_AXES = (2, 3)  # the right stick across (Windows: 2, Linux: 3) or a flight stick's twist (2)
WARN_CM = 40        # rumble starts this close to a wall (KIDA-01's sensor_assist WARN_DIST_CM)
STOP_CM = 15        # ...and is full here (the robots stop by themselves about now)


def rumble_level(cm_ahead, tipping=False):
    """(low, high) motor strengths 0..1 for the distance to the wall in the way (None / "--" /
    no reading: nothing in the way), or tipping."""
    if tipping:
        return 1.0, 1.0
    try:
        cm = float(cm_ahead)
    except (TypeError, ValueError):
        return 0.0, 0.0
    if cm <= 0 or cm >= WARN_CM:
        return 0.0, 0.0
    return 0.0, min(1.0, (WARN_CM - cm) / (WARN_CM - STOP_CM))


class PadDrive:
    def __init__(self):
        pygame.joystick.init()
        self.js = None
        self.rest = []
        self._held = set()
        self._rumble, self._rumble_at = (0.0, 0.0), 0.0
        if pygame.joystick.get_count():
            self._open(0)

    def _open(self, index):
        try:
            self.js = pygame.joystick.Joystick(index)
            self.js.init()
            pygame.event.pump()
            self.rest = [self.js.get_axis(a) for a in range(self.js.get_numaxes())]
            self._held = {b for b in range(self.js.get_numbuttons()) if self.js.get_button(b)}
        except pygame.error:
            self.js = None

    def handle(self, ev):
        """Hot-plug: pass every pygame event through here."""
        if ev.type == pygame.JOYDEVICEADDED and self.js is None:
            self._open(ev.device_index)
        elif ev.type == pygame.JOYDEVICEREMOVED and self.js is not None \
                and ev.instance_id == self.js.get_instance_id():
            self.js = None

    @property
    def name(self):
        return self.js.get_name() if self.js else None

    def _axis(self, a):
        if not self.js or a >= self.js.get_numaxes():
            return 0.0
        v = self.js.get_axis(a)
        return v if abs(v) > DEAD else 0.0

    def _button(self, b):
        return bool(self.js and b < self.js.get_numbuttons() and self.js.get_button(b))

    def direction(self):
        if not self.js:
            return None
        x, y = self._axis(0), self._axis(1)
        if self.js.get_numhats():
            hx, hy = self.js.get_hat(0)
            x, y = x or hx, y or -hy
        turn = 0.0
        for a in TURN_AXES:
            if a < len(self.rest) and abs(self.rest[a]) < 0.5 and self._axis(a):
                turn = self._axis(a)
                break
        if self._button(4):
            turn = -1.0
        if self._button(5):
            turn = 1.0
        if y and abs(y) >= abs(x):
            return "fw" if y < 0 else "bw"
        if x:
            return "left" if x < 0 else "right"
        if turn:
            return "turnL" if turn < 0 else "turnR"
        return None

    def rumble(self, low, high):
        """Keep the pad rumbling at (low, high), 0..1. Call it every frame: it renews itself, and
        (0, 0) stops it. Pads without rumble motors ignore it."""
        if not self.js:
            return
        now = time.monotonic()
        level = (round(low, 2), round(high, 2))
        if level == self._rumble and (not any(level) or now - self._rumble_at < 0.3):
            return
        self._rumble, self._rumble_at = level, now
        try:
            if any(level):
                self.js.rumble(level[0], level[1], 500)
            else:
                self.js.stop_rumble()
        except (pygame.error, AttributeError):
            pass

    def presses(self):
        """Buttons that went down since the last call (not 4 / 5: those turn)."""
        if not self.js:
            self._held = set()
            return set()
        now = {b for b in range(self.js.get_numbuttons()) if self.js.get_button(b)}
        new, self._held = now - self._held, now
        return new - {4, 5}
