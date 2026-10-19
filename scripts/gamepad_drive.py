"""gamepad_drive.py - drive with any joystick pygame sees: a gamepad, or ARM's flight stick.

Plug it in or pull it out at any time (hot-plug). The same file in the controllers that use it.

    pad = PadDrive()
    ...in the event loop:   pad.handle(ev)
    ...every frame:         pad.direction()  -> "fw" / "bw" / "left" / "right" / "turnL" / "turnR" / None
                            pad.presses()    -> buttons pressed since the last frame, e.g. {0, 3}

Drive: the left stick, the D-pad (hat) or a flight stick. Turn: LB / RB (buttons 4 / 5), the right
stick across, or a flight stick's twist. An axis that rests far from the middle when the pad is
plugged in (a trigger, a throttle) is never read as steering.
"""
import pygame

DEAD = 0.4          # stick travel that counts as pushed
TURN_AXES = (2, 3)  # the right stick across (Windows: 2, Linux: 3) or a flight stick's twist (2)


class PadDrive:
    def __init__(self):
        pygame.joystick.init()
        self.js = None
        self.rest = []
        self._held = set()
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

    def presses(self):
        """Buttons that went down since the last call (not 4 / 5: those turn)."""
        if not self.js:
            self._held = set()
            return set()
        now = {b for b in range(self.js.get_numbuttons()) if self.js.get_button(b)}
        new, self._held = now - self._held, now
        return new - {4, 5}
