"""fake_mila.py - a pretend MILA on this PC, to try the controller with no robot (EMULATE).

Answers the same web calls as her esp8266.ino on :5010 (/status, /cmd, /mode, /unlock, the wheel
lock, /scan, /mind, /chirp, /fleet) and acts them out with her tracks: each track forward, back or
off (her UNO has no speed control yet: section 12), so one track alone curves her; she drives about
a pretend room, her sonar reading drops as she nears a wall, and her UNO's guard won't let her
drive forward within 20 cm. Every command she gets is printed.

    python scripts/fake_mila.py         then: python scripts/mila_controller.py --emulate
                                        (or press EMULATE in the controller: it starts one itself)
"""

import math
import time

from controller_kit import FakeRobot

CONTROL_PIN = "1234"      # secrets.h CONTROL_PIN_SECRET (a safety catch, not security)
GUARD_CM = 20             # her UNO's forward guard / MIND_WALL_CM
ROOM = (260.0, 200.0)     # cm
MIND_STEP_S = 0.4
TRACKS = {"FORWARD": (1, 1), "BACKWARD": (-1, -1), "LEFT": (-1, 1), "RIGHT": (1, -1), "STOP": (0, 0)}
ONE = {"L_FWD": (0, 1), "L_BWD": (0, -1), "R_FWD": (1, 1), "R_BWD": (1, -1)}   # (track 0 = left, 1 = right), dir


class FakeMila(FakeRobot):
    NAME = "MILA"
    PORTS = (5010,)

    def __init__(self, host="127.0.0.1"):
        self.mode, self.locked, self.speed = "wasd", False, 100
        self.unlocked, self.mind_host_seen = False, 0.0
        self.tracks = [0, 0]                 # left, right: -1 / 0 / 1
        self.x, self.y, self.heading = ROOM[0] / 2, ROOM[1] / 2, 0.0
        self.last_cmd, self.guard, self.blocked = "STOP", False, False
        self.mind_until, self.scan = 0.0, (-1, -1, -1, 0.0)
        super().__init__(host)

    def _distance(self, angle=0.0):
        a = self.heading + angle
        dx, dy = math.cos(a), math.sin(a)
        best = 400.0
        if dx > 1e-6: best = min(best, (ROOM[0] - self.x) / dx)
        if dx < -1e-6: best = min(best, -self.x / dx)
        if dy > 1e-6: best = min(best, (ROOM[1] - self.y) / dy)
        if dy < -1e-6: best = min(best, -self.y / dy)
        return int(max(2, best))

    def step(self, dt):
        now = time.monotonic()
        if self.mode == "mind" and self.mind_until and now > self.mind_until:
            self.mind_until = 0
            self._set_tracks(0, 0)
        if self.mode == "obstacle":
            self.tracks = [-1, 1] if self._distance() < 30 else [1, 1]
        if self.mode == "follow":      # keeps a hand 30 cm away; nothing within 80 cm: stands
            d = self._distance()
            self.tracks = [0, 0] if d > 80 or abs(d - 30) <= 4 else [1, 1] if d > 30 else [-1, -1]
        l, r = (0, 0) if self.locked else self.tracks
        fwd, turn = (l + r) / 2, (r - l) / 2
        if fwd > 0 and self._distance() < GUARD_CM:   # her UNO's guard
            if not self.guard:
                self.guard = True
                self.log(f"guard: wall at {self._distance()} cm, stops")
            self.tracks, fwd, turn = [0, 0], 0, 0
        v = 35 * self.speed / 100
        self.x = min(ROOM[0] - 1, max(1, self.x + fwd * math.cos(self.heading) * v * dt))
        self.y = min(ROOM[1] - 1, max(1, self.y + fwd * math.sin(self.heading) * v * dt))
        self.heading += turn * 2.0 * dt

    def _set_tracks(self, l, r, why=None):
        if [l, r] != self.tracks:
            name = {(1, 1): "forward", (-1, -1): "backward", (-1, 1): "turns left", (1, -1): "turns right",
                    (0, 0): "stops", (0, 1): "curves left (right track)", (1, 0): "curves right (left track)",
                    (0, -1): "backs round (right track)", (-1, 0): "backs round (left track)"}.get((l, r), f"tracks {l} {r}")
            self.log(why or name)
        self.tracks = [l, r]

    def status(self):
        now = time.monotonic()
        sl, sf, sr, sat = self.scan
        return {"mode": self.mode, "lock": int(self.locked), "cmd": self.last_cmd, "dist": self._distance(),
                "left": "---" if sl < 0 else str(sl), "right": "---" if sr < 0 else str(sr), "turn": "",
                "ir": "-", "temp": 22.0, "hum": 45.0, "light": 1, "ip": "127.0.0.1", "fleet": 0,
                "speed": self.speed, "guard": int(self.guard), "mindHost": int(now - self.mind_host_seen < 5),
                "mindSteps": int(self.mind_until > now) and max(1, int((self.mind_until - now) / MIND_STEP_S + 0.99)),
                "blocked": int(self.blocked), "ml": self.tracks[0], "mr": self.tracks[1],
                "scan_l": sl, "scan_f": sf, "scan_r": sr, "scan_ms": int((now - sat) * 1000) if sat else -1}

    def route(self, port, path, q):
        now = time.monotonic()
        if path == "/status":
            if q.get("ctl") == "1" and self.mind_host_seen:
                self.mind_host_seen = now
            return 200, self.status()
        if path == "/fleet":
            return 200, {"authority": "MILA", "robots": [{"name": "MILA", "ip": "127.0.0.1"}]}
        if path == "/unlock":
            if q.get("pw") != CONTROL_PIN:
                return 403, {"ok": False, "error": "bad pin"}
            self.unlocked = True
            if q.get("ctl") == "1":
                self.mind_host_seen = now
            self.log("unlocked by the controller")
            return 200, {"ok": True, "controller": "127.0.0.1"}
        if path == "/motorlockOn":
            self.locked = True
            self._set_tracks(0, 0, "wheels locked")
            return 200, "OK"
        if path == "/motorlockOff":
            if q.get("pw") != CONTROL_PIN:
                return 403, "DENIED"
            self.locked = False
            self.log("wheels free")
            return 200, "OK"
        if path == "/scan":
            if self.mode == "obstacle":
                return 409, {"ok": False, "error": "obstacle mode sweeps by itself"}
            self._set_tracks(0, 0)
            l, f, r = self._distance(math.pi / 3), self._distance(), self._distance(-math.pi / 3)
            self.scan = (l, f, r, now)
            self.log(f"looks round: left {l}, ahead {f}, right {r} cm")
            return 200, {"ok": True, "left": l, "front": f, "right": r}
        if path == "/chirp":
            self.log(f"chirps line {q.get('u')}")
            return 200, {"ok": True}
        if not self.unlocked:
            return 403, "LOCKED"
        if path == "/cmd":
            v = q.get("v", "")
            if v == "SPEEDCYCLE" or v.startswith("SPEED:"):
                self.speed = int(v[6:]) if v.startswith("SPEED:") else {100: 75, 75: 50, 50: 25, 25: 100}.get(self.speed, 100)
                self.log(f"speed {self.speed}%")
                return 200, "OK"
            if self.mode in ("obstacle", "follow") or (self.mode == "mind" and v != "STOP"):
                return 200, "IGNORED"
            self.last_cmd = v
            if v in ("HELLO", "DANCE"):
                self._set_tracks(0, 0, "waves hello" if v == "HELLO" else "dances on the spot")
            if v in TRACKS:
                self.guard = False
                self._set_tracks(*TRACKS[v])
            elif v in ONE:
                side, d = ONE[v]
                t = list(self.tracks)
                t[side] = d
                self.guard = False
                self._set_tracks(*t)
            return 200, "OK"
        if path == "/mode":
            m = q.get("v", "wasd")
            if m == "mind" and now - self.mind_host_seen > 5:
                return 409, "no mind controller running"
            self.mode, self.mind_until = m, 0
            self.log(f"mode -> {m.upper()}")
            self._set_tracks(0, 0)
            return 200, "OK"
        if path == "/mind":
            if self.mode != "mind":
                return 409, {"ok": False, "error": "not in mind mode"}
            act = q.get("act")
            cmd = {"fwd": "FORWARD", "bwd": "BACKWARD", "left": "LEFT", "right": "RIGHT", "stop": "STOP"}.get(act)
            if not cmd:
                return 400, {"ok": False, "error": "bad act"}
            self.blocked = cmd == "FORWARD" and self._distance() < GUARD_CM
            if self.blocked:
                return 200, {"ok": False, "blocked": True, "distance": self._distance()}
            steps = max(1, min(4, int(q.get("steps", 1) or 1)))
            self.mind_until = 0 if cmd == "STOP" else now + steps * MIND_STEP_S
            self._set_tracks(*TRACKS[cmd], f"mind: {act} x{steps}")
            return 200, {"ok": True}
        return 404, "not found"


def start(quiet=False):
    """A fresh fake MILA on 127.0.0.1:5010. OSError if the port's taken."""
    robot = FakeMila()
    robot.quiet = quiet
    return robot


if __name__ == "__main__":
    try:
        mila = start()
    except OSError as e:
        raise SystemExit(f"Can't open :5010 ({e}). Is another fake MILA running?")
    print("Fake MILA at http://127.0.0.1:5010. Ctrl+C stops her.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mila.stop()
