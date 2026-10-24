#!/usr/bin/env python3
"""
MILA WiFi controller (pygame) — mirrors the onboard web dashboard.

USAGE
  python3 mila_controller.py
  python3 mila_controller.py --host 192.168.4.1 --port 5010

  If MILA joined NORA's network (fleet mode) instead of hosting her own
  AP, she won't be at 192.168.4.1 anymore — check NORA's dashboard/fleet
  registry (http://192.168.4.1:5000/robots) for MILA's actual IP and pass
  it with --host.

INSTALL
  pip install pygame requests

CONTROLS
  1 / 2 / 3     WASD / TANK / OBSTACLE mode
  WASD mode:    Arrow keys or WASD to drive, Space to stop
  TANK mode:    Q/A = left track fwd/back, E/D = right track fwd/back
  Esc           quit
  F1            every key, gamepad button and remote button (scripts/keymap.py)
  Gamepad       stick / D-pad drive (WASD mode), A stops, B/X/Y obstacle/WASD/TANK, Start speed +
  Everything is also clickable with the mouse.
  Two keys at once curve her (W+A: only her right track drives, so she arcs forward-left), and so
  does the stick. Driving while she drives herself (OBSTACLE) takes over: WASD, and she stops when
  you let go. STOP works in any mode. EMULATE: a pretend robot on this PC (--emulate too).
  VOICE: she talks through this PC. THEME: default / light / custom, from colour_scheme.xml.
"""

import os
import argparse
import threading
import time

import pygame
import requests

import keymap as keys_window         # scripts/keymap.py: every key and button, in its own window (F1)
import controller_kit as kit         # scripts/controller_kit.py: themes, settings that stick, Voice (every robot's)
from gamepad_drive import PadDrive, rumble_level  # any gamepad, or ARM's flight stick
import mind          # scripts/mind.py: her LLM mind (M), the same file in every controller
import mind_panel    # scripts/mind_panel.py: the mind's strip in the window

# ----------------------------------------------------------------------------
# Transport
# ----------------------------------------------------------------------------

class WifiLink:
    """Talks to MILA's ESP8266 web server (/cmd, /mode, /status)."""

    def __init__(self, host, port):
        self.base = f"http://{host}:{port}"
        self.ok = False
        self.data = {}
        self._queue = []                   # /cmd and /mode, sent in order by one thread (a curve is
        self._queued = threading.Event()   # STOP then one track: the order matters)
        threading.Thread(target=self._sender, daemon=True).start()
        self.mind_host = False   # mind.can_think() said yes: unlock with ctl=1 and check in on /status?ctl=1
        self._unlocked = False
        self._lock = threading.Lock()
        threading.Thread(target=self._poll, daemon=True).start()

    def unlock(self):
        """Her PIN (secrets.h CONTROL_PIN_SECRET; a safety catch, not security): without it every
        /cmd and /mode is LOCKED. ctl=1 too when this PC can run her mind."""
        try:
            params = {"pw": CONTROL_PIN, "ctl": "1"} if self.mind_host else {"pw": CONTROL_PIN}
            self._unlocked = requests.get(self.base + "/unlock", params=params, timeout=2).status_code == 200
        except Exception:
            self._unlocked = False

    def get_json(self, path, timeout=3):
        try:
            return requests.get(self.base + path, timeout=timeout).json()
        except Exception:
            return None

    def _get(self, path):
        try:
            requests.get(self.base + path, timeout=1.0)
        except Exception:
            pass

    def _poll(self):
        while True:
            try:
                if not self._unlocked:   # at the start, and again after she reboots or WiFi drops
                    self.unlock()
                r = requests.get(self.base + "/status" + ("?ctl=1" if self.mind_host else ""), timeout=1.0)
                with self._lock:
                    self.data = r.json()
                self.ok = True
            except Exception:
                self.ok = False
                self._unlocked = False
            time.sleep(0.4)

    def telemetry(self):
        with self._lock:
            return dict(self.data)

    def _sender(self):
        while True:
            self._queued.wait()
            self._queued.clear()
            while self._queue:
                self._get(self._queue.pop(0))

    def _send(self, path):
        self._queue.append(path)
        self._queued.set()

    def cmd(self, action):
        self._send(f"/cmd?v={action}")

    def mode(self, m):
        self._send(f"/mode?v={m}")

    def move_to(self, host, port):
        """Talk to another address (EMULATE on / off); unlock again there."""
        self.base = f"http://{host}:{port}"
        self.ok, self._unlocked, self.data = False, False, {}


# ----------------------------------------------------------------------------
# UI — same dark/cyan palette as the onboard dashboard
# ----------------------------------------------------------------------------

# Always from her colour_scheme.xml (sampled from her avatar), through controller_kit's themes:
# DEFAULT, LIGHT or CUSTOM (THEME). Her scheme has no red, so warnings are its danger colour, brightened.
def bright(c):
    top = max(c) or 1
    return tuple(min(255, v * 255 // top) for v in c)


def apply_theme(c):
    globals().update(BG=c["background"], PANEL=c["panel"], BORDER=c["border"], ACCENT=c["accent"],
                     ACCENT2=c["accent2"], RED=bright(c["danger_bg"]), GREEN=c["accent_hover"], TEXT=c["text"],
                     DIM=c["text_sec"], ACCENT_BG=c["button_hover_bg"])


SETTINGS = kit.Settings()
apply_theme(SETTINGS.colours())

W, H = 420, 720

# ----------------------------------------------------------------------------
# Her mind (mind.py): M switches MIND mode on and off, only on a PC that can run it
# ----------------------------------------------------------------------------
CONTROL_PIN = "1234"   # esp8266/secrets.h CONTROL_PIN_SECRET
# --- persona start ---
PERSONA = (
    "You're MILA, a small, fast tracked robot: playful, quick, cheeky and easily excited, always on the "
    "go. You have one ultrasonic sensor on a servo that looks ahead and to the sides. Everyone in the "
    "DREAM Robotics fleet makes way for you (your ESP8266 can't hear their beacons), and you rather "
    "like that. NORA is the boss, WHIP is a show-off, NIKA is your little sister who thinks in square "
    "waves."
)
VOICE = ("Microsoft Zira Desktop", 3, "high")
NAME = "MILA"
# Her voice through this PC outside MIND too (VOICE): playful, quick, cheeky
LINES = {
    "connect": ["MILA here! Let's go go go!", "Ooh, a controller! Hi hi!", "Ready! Where are we going?"],
    "emulate": ["A pretend me? Cute. Still fast though.", "Practice mode! I'm pretending really hard."],
    "lost": ["Hey, where'd you go?", "Hello? Still there? I'm bored."],
    "mode_wasd": ["You drive! Don't be boring.", "Steering wheel's yours. Go fast!"],
    "mode_tank": ["Tank mode! One track each, let's roll.", "Left track, right track. Easy peasy."],
    "mode_obstacle": ["Off I go, exploring by myself!", "Byeee! I'll find my own way."],
    "wall": ["Whoa, wall! Nope.", "Bonk avoided!", "Who put that there?"],
    "locked": ["Hey! My wheels are locked!", "NORA, really? Locked again?"],
    "unlocked": ["Free! Wheee!", "Wheels back! Let's go!"],
    "speed": ["Speed {speed} percent. Faster is better.", "{speed} percent! Zoom zoom."],
}
# --- persona end ---
MOVES = {"fwd": "drive forward", "bwd": "drive backward", "left": "turn left", "right": "turn right",
         "scan": "stop and look left, ahead and right with your sensor"}
SAFETY = "she won't drive forward into anything within 20 cm, and NORA can lock her wheels"
MIND_MOVE_TIMEOUT_S = 6.0


def body(link):
    """mind.Mind's look / act, over her /status, /mind and /scan."""
    def look():
        s = link.get_json("/status?ctl=1") or {}
        senses = {k: s.get(k) for k in ("dist", "left", "right", "guard", "blocked", "temp", "hum", "light",
                                         "thought", "hz", "ird") if k in s}
        if s.get("scan_ms", -1) >= 0:
            senses["last_scan_cm"] = {"left": s.get("scan_l"), "front": s.get("scan_f"), "right": s.get("scan_r"),
                                      "age_s": round(s["scan_ms"] / 1000, 1)}
        return senses

    def act(move, steps):
        if move == "scan":
            return link.get_json("/scan", timeout=5) or {"ok": False, "error": "no answer"}
        r = link.get_json(f"/mind?act={move}&steps={steps}")
        if r is None:
            raise ConnectionError(f"{NAME} isn't answering")
        if move == "stop" or not r.get("ok"):
            return r
        t0 = time.time()
        while time.time() - t0 < MIND_MOVE_TIMEOUT_S:
            time.sleep(0.3)
            s = link.get_json("/status?ctl=1") or {}
            if not s.get("mindSteps"):
                return {"ok": True, "stopped_at_a_wall": bool(s.get("blocked")), "front_cm": s.get("dist")}
        return {"ok": True, "note": "still moving"}

    return look, act


class Button:
    def __init__(self, rect, label, cb, font, active=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.cb = cb
        self.font = font
        self.active = active
        self.pressed = False

    def draw(self, surf):
        color = ACCENT if (self.active or self.pressed) else BORDER
        bg = ACCENT_BG if (self.active or self.pressed) else PANEL
        pygame.draw.rect(surf, bg, self.rect, border_radius=8)
        pygame.draw.rect(surf, color, self.rect, 2, border_radius=8)
        txt = self.font.render(self.label, True, ACCENT if (self.active or self.pressed) else TEXT)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.rect.collidepoint(pos)


def stat_tile(surf, font_label, font_val, x, y, w, label, value):
    box = pygame.Rect(x, y, w, 46)
    pygame.draw.rect(surf, PANEL, box, border_radius=6)
    pygame.draw.rect(surf, BORDER, box, 1, border_radius=6)
    surf.blit(font_label.render(label, True, DIM), (x + 8, y + 6))
    surf.blit(font_val.render(str(value), True, ACCENT), (x + 8, y + 20))


def round_avatar(path, size):
    """The robot's avatar as a circular surface, or None if it can't be loaded.
    The one place the avatar is loaded: swap in animation frames here later."""
    try:
        img = pygame.transform.smoothscale(pygame.image.load(path).convert(), (size, size))
    except (pygame.error, OSError):
        return None
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
    out = pygame.Surface((size, size), pygame.SRCALPHA)
    out.blit(img, (0, 0))
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.4.1")
    ap.add_argument("--port", type=int, default=5010)
    ap.add_argument("--emulate", action="store_true", help="a pretend robot on this PC, no robot needed")
    args = ap.parse_args()

    link = WifiLink(args.host, args.port)
    fake = {"robot": None}   # EMULATE: the fake robot running in here

    def toggle_emulate():
        if fake["robot"]:
            fake["robot"].stop()
            fake["robot"] = None
            link.move_to(args.host, args.port)
        else:
            import fake_mila
            try:
                fake["robot"] = fake_mila.start(quiet=True)
                link.move_to("127.0.0.1", fake_mila.FakeMila.PORTS[0])
            except OSError as e:
                print(f"Can't start the fake: {e}")
        emu_btn.active = fake["robot"] is not None

    voice = kit.Voice(VOICE[0], LINES, VOICE[1], VOICE[2])
    voice.on = SETTINGS.get("voice", True)
    heard = {"s": None}
    if args.emulate:
        toggle_emulate_at_start = True
    else:
        toggle_emulate_at_start = False
    look, act = body(link)
    her_mind = mind.Mind(NAME, PERSONA, MOVES, look, act, voice=VOICE[0], rate=VOICE[1], pitch=VOICE[2], safety=SAFETY)
    mind_state = {"capable": False, "why": "checking this PC..."}

    def check_mind():
        mind_state["capable"], mind_state["why"] = mind.can_think()
        if mind_state["capable"]:
            link.mind_host = True
            link.unlock()
    threading.Thread(target=check_mind, daemon=True).start()

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("MILA Control")
    try:  # window icon: the robot's avatar
        pygame.display.set_icon(pygame.image.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images", "mila-icon.png")))
    except (pygame.error, OSError):
        pass
    clock = pygame.time.Clock()
    avatar = round_avatar(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images", "mila_avatar.jpg"), 52)
    f_big = pygame.font.SysFont("monospace", 26, bold=True)
    f_med = pygame.font.SysFont("monospace", 15, bold=True)
    f_sml = pygame.font.SysFont("monospace", 12)

    mode = "wasd"   # mirrors the firmware's WASD boot default
    active_drive = None
    buttons = []

    def add(rect, label, cb, active=False):
        b = Button(rect, label, cb, f_med, active)
        buttons.append(b)
        return b

    pending = kit.Pending()   # mode / speed re-sent until her /status says so

    def set_mode(m):
        nonlocal mode
        mode = m
        pending.want("mode", m, lambda: link.mode(m))
        for b, name in zip(mode_btns, ("wasd", "tank", "obstacle")):
            b.active = (name == m)

    mode_btns = [
        add((20, 100, 120, 40), "WASD", lambda: set_mode("wasd"), True),
        add((150, 100, 120, 40), "TANK", lambda: set_mode("tank")),
        add((280, 100, 120, 40), "OBSTACLE", lambda: set_mode("obstacle")),
    ]

    # Speed presets mirror the firmware's speedPresets[] (100/75/50/25).
    # speed_state tracks the last-known value, kept in sync from telemetry
    # each frame so it stays correct even if the IR remote or dashboard
    # changed it out from under us.
    speed_state = {"pct": 100}

    def adjust_speed(delta):
        new_pct = max(25, min(100, speed_state["pct"] + delta))
        speed_state["pct"] = new_pct
        pending.want("speed", new_pct, lambda: link.cmd(f"SPEED:{new_pct}"))

    speed_btns = [
        add((20, 150, 180, 40), "SPD -", lambda: adjust_speed(-25)),
        add((220, 150, 180, 40), "SPD +", lambda: adjust_speed(25)),
    ]

    # WASD d-pad
    pad_cx, pad_cy, bs, gap = W // 2, 290, 60, 6   # between the speed buttons (to y 190) and the tiles (from 400)
    def take_over():
        """Driving her while she drives herself (OBSTACLE): WASD, so she does what's pressed and
        stops on release. (Her ESP8266 ignores /cmd drives in OBSTACLE.)"""
        if mode == "obstacle":
            set_mode("wasd")

    def stop_all():
        """STOP, in any mode: out of OBSTACLE / MIND, tracks still."""
        nonlocal active_drive, curve
        active_drive, curve = None, None
        if mode in ("obstacle", "mind"):
            set_mode("wasd")
        link.cmd("STOP")

    def start_drive(action):
        nonlocal active_drive
        take_over()
        active_drive = action
        link.cmd(action)

    def stop_drive():
        nonlocal active_drive
        if active_drive:
            active_drive = None
            link.cmd("STOP")

    wasd_btns = {
        "FORWARD": add((pad_cx - bs // 2, pad_cy - bs // 2 - gap - bs, bs, bs), "^", lambda: start_drive("FORWARD")),
        "BACKWARD": add((pad_cx - bs // 2, pad_cy + bs // 2 + gap, bs, bs), "v", lambda: start_drive("BACKWARD")),
        "LEFT": add((pad_cx - bs // 2 - gap - bs, pad_cy - bs // 2, bs, bs), "<", lambda: start_drive("LEFT")),
        "RIGHT": add((pad_cx + bs // 2 + gap, pad_cy - bs // 2, bs, bs), ">", lambda: start_drive("RIGHT")),
    }
    stop_btn = add((pad_cx - bs // 2, pad_cy - bs // 2, bs, bs), "STOP", stop_all)

    # header row: EMULATE / VOICE / THEME
    def toggle_voice():
        voice.on = not voice.on
        SETTINGS["voice"] = voice.on
        SETTINGS.save()
        voice_btn.label = "VOICE ON" if voice.on else "VOICE OFF"
        voice_btn.active = voice.on

    def theme_next():
        apply_theme(SETTINGS.next_theme())
        theme_btn.label = SETTINGS.theme

    emu_btn = add((20, 62, 120, 28), "EMULATE", toggle_emulate)
    voice_btn = add((150, 62, 120, 28), "VOICE ON" if voice.on else "VOICE OFF", toggle_voice, voice.on)
    theme_btn = add((280, 62, 120, 28), SETTINGS.theme, theme_next)

    # held keys and the stick curve her: a track alone (she has no speed control yet)
    KEYS = {"fwd": (pygame.K_w, pygame.K_UP), "back": (pygame.K_s, pygame.K_DOWN),
            "turn_l": (pygame.K_a, pygame.K_LEFT), "turn_r": (pygame.K_d, pygame.K_RIGHT)}
    CURVES = {(1, 1): ["STOP", "R_FWD"], (1, -1): ["STOP", "L_FWD"],     # forward-left / -right
              (-1, 1): ["STOP", "R_BWD"], (-1, -1): ["STOP", "L_BWD"],   # back-left / -right
              (1, 0): ["FORWARD"], (-1, 0): ["BACKWARD"], (0, 1): ["LEFT"], (0, -1): ["RIGHT"]}
    curve = None   # what the keys / stick are doing now: (forward, turn) signs

    # TANK track buttons
    tank_y = 280
    tank_btns = [
        add((60, tank_y - 40, 90, 50), "Q\nL-FWD", lambda: start_drive("L_FWD")),
        add((60, tank_y + 40, 90, 50), "A\nL-BWD", lambda: start_drive("L_BWD")),
        add((W - 150, tank_y - 40, 90, 50), "E\nR-FWD", lambda: start_drive("R_FWD")),
        add((W - 150, tank_y + 40, 90, 50), "D\nR-BWD", lambda: start_drive("R_BWD")),
    ]

    key_drive_tank = {
        pygame.K_q: "L_FWD", pygame.K_a: "L_BWD",
        pygame.K_e: "R_FWD", pygame.K_d: "R_BWD",
    }

    if toggle_emulate_at_start:
        toggle_emulate()
    pad = PadDrive()          # a gamepad / joystick, plugged in any time
    pad_drive = None          # the drive the pad is holding
    PAD_DRIVE = {"fw": "FORWARD", "bw": "BACKWARD", "left": "LEFT", "right": "RIGHT",
                 "turnL": "LEFT", "turnR": "RIGHT"}

    running = True
    while running:
        for ev in pygame.event.get():
            pad.handle(ev)
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_F1:
                    keys_window.open_window()
                elif ev.key == pygame.K_m and mind_state["capable"]:   # her MIND mode on / off
                    set_mode("wasd" if her_mind.on else "mind")
                elif ev.key == pygame.K_1:
                    set_mode("wasd")
                elif ev.key == pygame.K_2:
                    set_mode("tank")
                elif ev.key == pygame.K_3:
                    set_mode("obstacle")
                elif ev.key == pygame.K_SPACE:
                    stop_all()
                elif mode == "tank" and ev.key in key_drive_tank:
                    start_drive(key_drive_tank[ev.key])

            elif ev.type == pygame.KEYUP:
                if mode == "tank" and ev.key in key_drive_tank and active_drive == key_drive_tank[ev.key]:
                    stop_drive()

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                for b in buttons:
                    if b.hit(ev.pos):
                        b.pressed = True
                        b.cb()

            elif ev.type == pygame.MOUSEBUTTONUP:
                for b in buttons:
                    b.pressed = False
                if active_drive:
                    stop_drive()

        # held keys and the stick drive her (not in TANK: its keys are the tracks), two at once a curve
        if mode != "tank":
            f, _, tn = kit.keys_vector(pygame.key.get_pressed(), KEYS)
            if not (f or tn):
                pf, ps, pt = pad.vector()
                tn = pt or ps   # a tank turns with the stick across
                f = 0 if abs(pf) < 0.3 else (1 if pf > 0 else -1)
                tn = 0 if abs(tn) < 0.3 else (1 if tn > 0 else -1)
            want = (f, tn) if (f or tn) else None
            if want != curve:
                if want:
                    take_over()
                    for c in CURVES[want]:
                        link.cmd(c)
                elif curve:
                    link.cmd("STOP")
                curve = want
            pad_drive = "FORWARD" if want and want[0] > 0 else None
        for b in pad.presses():
            if b == 0: stop_all()
            elif b == 1: set_mode("obstacle")
            elif b == 2: set_mode("wasd")
            elif b == 3: set_mode("tank")
            elif b == 7: adjust_speed(25)

        # ---- draw ----
        screen.fill(BG)
        t = link.telemetry()
        # her mode is the switch: MIND (from M here, or her page) = thinking, anything else = not
        in_mind = link.ok and t.get("mode") == "mind"
        if in_mind and not her_mind.on and mind_state["capable"]:
            her_mind.start(goal="explore the room, have fun, and don't bump into anything")
        elif not in_mind and her_mind.on:
            her_mind.on = False
            her_mind.state = "off"
        # the pad buzzes as she nears a wall while it drives her forward (gamepad_drive.rumble_level)
        pad.rumble(*rumble_level(t.get("dist") if pad_drive == "FORWARD" else None))
        if link.ok:
            pending.check(t)
        if "speed" in t and pending.value("speed") is None:
            try:
                speed_state["pct"] = int(float(t["speed"]))
            except (TypeError, ValueError):
                pass
        if t.get("mode") in ("wasd", "tank", "obstacle", "mind") and t["mode"] != mode and pending.value("mode") is None:
            mode = t["mode"]
            for b, name in zip(mode_btns, ("wasd", "tank", "obstacle")):
                b.active = (name == mode)

        # her voice, from what changed (her MIND talks for itself)
        was, now_s = heard["s"], (dict(t) if link.ok and t else None)
        heard["s"] = now_s
        if not her_mind.on:
            if now_s is None and was:
                voice.say("lost")
            elif now_s and was is None:
                voice.say("emulate" if fake["robot"] else "connect")
            elif now_s and was:
                if now_s.get("mode") != was.get("mode") and now_s.get("mode") != "mind":
                    voice.say("mode_" + str(now_s.get("mode")))
                if str(now_s.get("guard")) == "1" and str(was.get("guard")) != "1":
                    voice.say("wall")
                if now_s.get("lock") != was.get("lock"):
                    voice.say("locked" if now_s.get("lock") else "unlocked")
                if now_s.get("speed") != was.get("speed") and now_s.get("speed") is not None:
                    voice.say("speed", speed=now_s.get("speed"))

        if avatar:
            screen.blit(avatar, (16, 10))
        title = f_big.render("MILA", True, ACCENT)
        screen.blit(title, title.get_rect(centerx=W // 2, y=14))
        conn = "connected" if link.ok else "OFFLINE"
        col = GREEN if link.ok else RED
        where = f"EMULATED  {fake['robot'].last_log()}" if fake["robot"] else f"{args.host}:{args.port}   {conn}"
        sub = f_sml.render(kit.fit(where, f_sml, W - 90), True, col)
        screen.blit(sub, sub.get_rect(centerx=W // 2, y=46))

        for b in mode_btns + [emu_btn, voice_btn, theme_btn]:
            b.draw(screen)

        for b in speed_btns:
            b.draw(screen)

        if mode == "tank":
            for b in tank_btns:
                b.draw(screen)
        else:
            for b in wasd_btns.values():
                b.draw(screen)
        stop_btn.draw(screen)   # STOP in any mode

        # status tiles
        sy = 400
        colw = (W - 50) // 2
        stat_tile(screen, f_sml, f_med, 20, sy, colw, "FRONT CM", t.get("dist", "--"))
        stat_tile(screen, f_sml, f_med, 30 + colw, sy, colw, "LEFT CM", t.get("left", "--"))
        stat_tile(screen, f_sml, f_med, 20, sy + 54, colw, "RIGHT CM", t.get("right", "--"))
        stat_tile(screen, f_sml, f_med, 30 + colw, sy + 54, colw, "LAST CMD", t.get("cmd", "--"))
        stat_tile(screen, f_sml, f_med, 20, sy + 108, colw, "LAST IR", t.get("ir", "--"))
        stat_tile(screen, f_sml, f_med, 30 + colw, sy + 108, colw, "TEMP C", t.get("temp", "--"))
        stat_tile(screen, f_sml, f_med, 20, sy + 162, colw, "HUMIDITY %", t.get("hum", "--"))
        fleet_txt = "FLEET (joined NORA)" if t.get("fleet") == 1 else "STANDALONE AP"
        stat_tile(screen, f_sml, f_med, 30 + colw, sy + 162, colw, "IP  " + str(t.get("ip", "--")), fleet_txt)
        guard_txt = "ACTIVE" if str(t.get("guard")) == "1" else "clear"
        stat_tile(screen, f_sml, f_med, 20, sy + 216, colw, "SPEED %", t.get("speed", "--"))
        stat_tile(screen, f_sml, f_med, 30 + colw, sy + 216, colw, "GUARD", guard_txt)

        hint = f_sml.render(kit.fit("1/2/3 mode - WASD drive (W+A curves) - QAED tracks - space stop - esc quit",
                                    f_sml, W - 16), True, DIM)
        screen.blit(hint, hint.get_rect(centerx=W // 2, y=H - 24))

        if her_mind.on:
            mind_panel.draw(screen, pygame.Rect(8, H - 196, W - 16, 168), her_mind, f_med, f_sml, NAME,
                            note="M: off", colours=(TEXT, DIM, RED, ACCENT))
        elif voice.on and voice.said:
            screen.blit(f_sml.render(kit.fit(f'{NAME}: "{voice.said}"', f_sml, W - 24), True, TEXT), (12, H - 40))
        elif not mind_state["capable"]:
            screen.blit(f_sml.render(kit.fit(f"mind: {mind_state['why']}", f_sml, W - 24), True, DIM), (12, H - 40))

        pygame.display.flip()
        clock.tick(60)

    link.cmd("STOP")
    time.sleep(0.3)
    if fake["robot"]:
        fake["robot"].stop()
    pygame.quit()


if __name__ == "__main__":
    main()
