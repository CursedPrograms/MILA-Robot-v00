"""gamepad_drive.py - drive with any joystick pygame sees: a gamepad, or ARM's flight stick.

Plug it in or pull it out at any time (hot-plug). The same file in the controllers that use it.

    pad = PadDrive()
    ...in the event loop:   pad.handle(ev)
    ...every frame:         pad.vector()     -> (forward, side, turn), -1..1 each, blended: the stick
                                                forward and a little left is both (side / turn + = left)
                            pad.direction()  -> "fw" / "bw" / "left" / "right" / "turnL" / "turnR" / None
                                                (the strongest of those, for robots without blended drive)
                            pad.presses()    -> buttons pressed since the last frame, e.g. {0, 3}
                            pad.rumble(*rumble_level(cm_ahead))   -> buzz as a wall gets close

A pad SDL knows (Xbox, PlayStation, Switch, most USB pads: SDL's controller database) is read through
SDL's GameController layer, so they all have the same buttons, numbered as an Xbox pad's: A 0, B 1,
X 2, Y 3, LB 4, RB 5, Back / Select 6, Start 7, left stick click 8, right stick click 9 (presses()
gives those numbers whatever the pad is). Anything else (a flight stick, a pad SDL doesn't know) is
read raw, by its own button numbers.

Drive: the left stick, the D-pad or a flight stick. Turn: LB / RB, the right stick across, or a
flight stick's twist. An axis that rests far from the middle when the pad is plugged in (a trigger,
a throttle) is never read as steering.

Rumble (KIDA-01's haptics.py, for every pad): while you drive, the light motor buzzes from WARN_CM
on, harder the closer the wall in the way, full at STOP_CM; a tipping robot shakes both motors full.
"""
import time

import pygame

DEAD = 0.4          # stick travel that counts as pushed, for direction()
AXIS_DEAD = 0.15    # ...and the dead zone for vector()
TURN_AXES = (2, 3)  # raw: the right stick across (Windows: 2, Linux: 3) or a flight stick's twist (2)
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


def _controller_module():
    try:
        from pygame._sdl2 import controller
        controller.init()
        return controller
    except (ImportError, pygame.error):
        return None


class PadDrive:
    # SDL's buttons in Xbox order, so presses() numbers them the same whatever the pad
    _CTL_BUTTONS = ("CONTROLLER_BUTTON_A", "CONTROLLER_BUTTON_B", "CONTROLLER_BUTTON_X", "CONTROLLER_BUTTON_Y",
                    "CONTROLLER_BUTTON_LEFTSHOULDER", "CONTROLLER_BUTTON_RIGHTSHOULDER",
                    "CONTROLLER_BUTTON_BACK", "CONTROLLER_BUTTON_START",
                    "CONTROLLER_BUTTON_LEFTSTICK", "CONTROLLER_BUTTON_RIGHTSTICK")

    def __init__(self):
        pygame.joystick.init()
        self.js = None
        self.ctl = None          # SDL GameController, when SDL knows the pad
        self.rest = []
        self._held = set()
        self._rumble, self._rumble_at = (0.0, 0.0), 0.0
        if pygame.joystick.get_count():
            self._open(0)

    def _open(self, index):
        try:
            self.js = pygame.joystick.Joystick(index)
            self.js.init()
            gc = _controller_module()
            self.ctl = gc.Controller(index) if gc and gc.is_controller(index) else None
            pygame.event.pump()
            self.rest = [self.js.get_axis(a) for a in range(self.js.get_numaxes())]
            self._held = self._buttons_down()
        except pygame.error:
            self.js = self.ctl = None

    def handle(self, ev):
        """Hot-plug: pass every pygame event through here."""
        if ev.type == pygame.JOYDEVICEADDED and self.js is None:
            self._open(ev.device_index)
        elif ev.type == pygame.JOYDEVICEREMOVED and self.js is not None \
                and ev.instance_id == self.js.get_instance_id():
            self.js = self.ctl = None

    @property
    def name(self):
        if self.ctl:
            return self.ctl.name or self.js.get_name()
        return self.js.get_name() if self.js else None

    def _button(self, b):
        try:
            if self.ctl:
                return b < len(self._CTL_BUTTONS) and bool(self.ctl.get_button(getattr(pygame, self._CTL_BUTTONS[b])))
            return bool(self.js and b < self.js.get_numbuttons() and self.js.get_button(b))
        except pygame.error:
            return False

    def _buttons_down(self):
        n = len(self._CTL_BUTTONS) if self.ctl else (self.js.get_numbuttons() if self.js else 0)
        return {b for b in range(n) if self._button(b)}

    def _raw_axis(self, a):
        if not self.js or a >= self.js.get_numaxes():
            return 0.0
        try:
            return self.js.get_axis(a)
        except pygame.error:
            return 0.0

    def _sticks(self):
        """(x, y, turn) -1..1, y down = +, from the sticks, the D-pad and LB / RB."""
        if self.ctl:
            try:
                g, b = self.ctl.get_axis, self.ctl.get_button
                x = g(pygame.CONTROLLER_AXIS_LEFTX) / 32767
                y = g(pygame.CONTROLLER_AXIS_LEFTY) / 32767
                turn = g(pygame.CONTROLLER_AXIS_RIGHTX) / 32767
                hx = b(pygame.CONTROLLER_BUTTON_DPAD_RIGHT) - b(pygame.CONTROLLER_BUTTON_DPAD_LEFT)
                hy = b(pygame.CONTROLLER_BUTTON_DPAD_DOWN) - b(pygame.CONTROLLER_BUTTON_DPAD_UP)
            except pygame.error:
                return 0.0, 0.0, 0.0
        else:
            x, y, turn = self._raw_axis(0), self._raw_axis(1), 0.0
            for a in TURN_AXES:
                if a < len(self.rest) and abs(self.rest[a]) < 0.5 and abs(self._raw_axis(a)) > AXIS_DEAD:
                    turn = self._raw_axis(a)
                    break
            hx, hy = 0, 0
            if self.js.get_numhats():
                hx, hy = self.js.get_hat(0)
                hy = -hy
        if hx or hy:
            x, y = float(hx), float(hy)
        if self._button(4):
            turn = -1.0
        if self._button(5):
            turn = 1.0
        return tuple(max(-1.0, min(1.0, v)) for v in (x, y, turn))

    def vector(self):
        """(forward, side, turn) -1..1 each, side / turn + = left: blended, for robots that take it."""
        if not self.js:
            return 0.0, 0.0, 0.0
        x, y, turn = self._sticks()
        return tuple(0.0 if abs(v) < AXIS_DEAD else round(v, 2) + 0.0 for v in (-y, -x, -turn))

    def direction(self):
        if not self.js:
            return None
        x, y, turn = (v if abs(v) > DEAD else 0.0 for v in self._sticks())
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
            (self.ctl or self.js).rumble(level[0], level[1], 500 if any(level) else 1)
        except (pygame.error, AttributeError):
            pass

    def presses(self):
        """Buttons that went down since the last call (not 4 / 5: those turn)."""
        if not self.js:
            self._held = set()
            return set()
        now = self._buttons_down()
        new, self._held = now - self._held, now
        return new - {4, 5}
