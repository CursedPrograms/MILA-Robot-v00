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
"""

import os
import argparse
import threading
import time

import pygame
import requests

import keymap as keys_window         # scripts/keymap.py: every key and button, in its own window (F1)
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

    def cmd(self, action):
        threading.Thread(target=self._get, args=(f"/cmd?v={action}",), daemon=True).start()

    def mode(self, m):
        threading.Thread(target=self._get, args=(f"/mode?v={m}",), daemon=True).start()


# ----------------------------------------------------------------------------
# UI — same dark/cyan palette as the onboard dashboard
# ----------------------------------------------------------------------------

BG      = (10, 10, 15)     # --bg
PANEL   = (18, 18, 26)     # --panel
BORDER  = (30, 30, 46)     # --border
ACCENT  = (0, 212, 255)    # --accent
ACCENT2 = (124, 58, 237)   # --accent2
RED     = (255, 68, 68)    # --red
GREEN   = (0, 255, 136)    # --green
TEXT    = (224, 224, 240)  # --text
DIM     = (102, 102, 136)  # --sub
ACCENT_BG = (14, 34, 46)

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
    args = ap.parse_args()

    link = WifiLink(args.host, args.port)
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

    def set_mode(m):
        nonlocal mode
        mode = m
        link.mode(m)
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
        link.cmd(f"SPEED:{new_pct}")

    speed_btns = [
        add((20, 150, 180, 40), "SPD -", lambda: adjust_speed(-25)),
        add((220, 150, 180, 40), "SPD +", lambda: adjust_speed(25)),
    ]

    # WASD d-pad
    pad_cx, pad_cy, bs, gap = W // 2, 280, 70, 8
    def start_drive(action):
        nonlocal active_drive
        active_drive = action
        link.cmd(action)

    def stop_drive():
        nonlocal active_drive
        if active_drive:
            active_drive = None
            link.cmd("STOP")

    wasd_btns = {
        "FORWARD": add((pad_cx - bs // 2, pad_cy - bs - gap, bs, bs), "^", lambda: start_drive("FORWARD")),
        "BACKWARD": add((pad_cx - bs // 2, pad_cy + gap, bs, bs), "v", lambda: start_drive("BACKWARD")),
        "LEFT": add((pad_cx - bs - gap - bs // 2 - gap, pad_cy - bs // 2, bs, bs), "<", lambda: start_drive("LEFT")),
        "RIGHT": add((pad_cx + gap + bs // 2 + gap, pad_cy - bs // 2, bs, bs), ">", lambda: start_drive("RIGHT")),
    }
    stop_btn = add((pad_cx - bs // 2, pad_cy - bs // 2, bs, bs), "STOP", lambda: link.cmd("STOP"))

    # TANK track buttons
    tank_y = 280
    tank_btns = [
        add((60, tank_y - 40, 90, 50), "Q\nL-FWD", lambda: start_drive("L_FWD")),
        add((60, tank_y + 40, 90, 50), "A\nL-BWD", lambda: start_drive("L_BWD")),
        add((W - 150, tank_y - 40, 90, 50), "E\nR-FWD", lambda: start_drive("R_FWD")),
        add((W - 150, tank_y + 40, 90, 50), "D\nR-BWD", lambda: start_drive("R_BWD")),
    ]

    key_drive_wasd = {
        pygame.K_UP: "FORWARD", pygame.K_w: "FORWARD",
        pygame.K_DOWN: "BACKWARD", pygame.K_s: "BACKWARD",
        pygame.K_LEFT: "LEFT", pygame.K_a: "LEFT",
        pygame.K_RIGHT: "RIGHT", pygame.K_d: "RIGHT",
    }
    key_drive_tank = {
        pygame.K_q: "L_FWD", pygame.K_a: "L_BWD",
        pygame.K_e: "R_FWD", pygame.K_d: "R_BWD",
    }

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
                    stop_drive()
                elif mode == "wasd" and ev.key in key_drive_wasd:
                    start_drive(key_drive_wasd[ev.key])
                elif mode == "tank" and ev.key in key_drive_tank:
                    start_drive(key_drive_tank[ev.key])

            elif ev.type == pygame.KEYUP:
                keymap = key_drive_wasd if mode == "wasd" else key_drive_tank
                if ev.key in keymap and active_drive == keymap[ev.key]:
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

        # gamepad: the stick / D-pad drives in WASD mode, buttons do the rest
        d = PAD_DRIVE.get(pad.direction()) if mode == "wasd" else None
        if d != pad_drive:
            if d:
                start_drive(d)
            elif active_drive == pad_drive:
                stop_drive()
            pad_drive = d
        for b in pad.presses():
            if b == 0: stop_drive(); link.cmd("STOP")
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
        if "speed" in t:
            try:
                speed_state["pct"] = int(float(t["speed"]))
            except (TypeError, ValueError):
                pass

        if avatar:
            screen.blit(avatar, (16, 10))
        title = f_big.render("MILA", True, ACCENT)
        screen.blit(title, title.get_rect(centerx=W // 2, y=14))
        conn = "connected" if link.ok else "OFFLINE"
        col = GREEN if link.ok else RED
        sub = f_sml.render(f"{args.host}:{args.port}   {conn}", True, col)
        screen.blit(sub, sub.get_rect(centerx=W // 2, y=46))

        for b in mode_btns:
            b.draw(screen)

        for b in speed_btns:
            b.draw(screen)

        if mode == "wasd":
            for b in wasd_btns.values():
                b.draw(screen)
            stop_btn.draw(screen)
        elif mode == "tank":
            for b in tank_btns:
                b.draw(screen)

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

        hint = f_sml.render("1/2/3 mode - WASD/QAED drive - space stop - esc quit", True, DIM)
        screen.blit(hint, hint.get_rect(centerx=W // 2, y=H - 24))

        if her_mind.on:
            mind_panel.draw(screen, pygame.Rect(8, H - 196, W - 16, 168), her_mind, f_med, f_sml, NAME,
                            note="M: off", colours=(TEXT, DIM, RED, ACCENT))
        elif not mind_state["capable"]:
            screen.blit(f_sml.render(f"mind: {mind_state['why']}"[:60], True, DIM), (12, H - 40))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
