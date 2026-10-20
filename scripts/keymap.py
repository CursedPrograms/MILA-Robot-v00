#!/usr/bin/env python3
"""keymap.py - every key, gamepad button and remote button MILA takes, in its own window.

    python scripts/keymap.py                  opens the window (the Python controller opens it with F1)
    python scripts/keymap.py --header FILE.h  writes the web page's /keys page (a PROGMEM string)
    python scripts/keymap.py --readme README.md   rewrites the README's "Controls" tables
    python scripts/keymap.py --markdown       prints those tables

The one list of the robot's controls. After changing it, write the header (and reflash) and
the README again, so all of them say the same.
"""

TITLE = "MILA - controls"

KEYMAP = [
    ("Keyboard: web page and every desktop controller", [
        ("1 / 2 / 3", "WASD / TANK / OBSTACLE mode"),
        ("W / Up, S / Down", "forward / back (WASD mode, hold)"),
        ("A / Left, D / Right", "turn left / right (WASD mode, hold)"),
        ("Q / A", "left track forward / back (TANK mode, hold)"),
        ("E / D", "right track forward / back (TANK mode, hold)"),
        ("Space", "stop (controllers)"),
        ("M", "her MIND mode on / off: the LLM on this PC drives her (Python controller; x86 PC, GTX 1050+)"),
        ("X", "speed preset: 100, 75, 50, 25 % (web page)"),
        ("F1", "this window (Python controller; KEYS on the web page)"),
        ("Esc", "quit (controllers)"),
        ("", "driving from the web page needs her PIN first (UNLOCK)"),
    ]),
    ("Gamepad or joystick (ARM's flight stick works too)", [
        ("Left stick / D-pad", "drive (WASD mode)"),
        ("LB / RB, right stick, twist", "turn left / right (Python controller)"),
        ("A (button 0)", "stop"),
        ("B (1) / X (2) / Y (3)", "OBSTACLE / WASD / TANK mode (Python controller)"),
        ("Start (7)", "speed + 25 % (Python controller)"),
        ("", "C++, C# and F# controllers: stick or D-pad drive, triggers speed, A stops, bumpers change mode"),
    ]),
    ("Her IR remote", [
        ("1 / 2 / 3", "WASD / TANK / OBSTACLE mode"),
        ("Up / Down / Left / Right", "drive (WASD mode, hold)"),
        ("Red / Green", "left track forward / back (TANK mode)"),
        ("Yellow / Blue", "right track forward / back (TANK mode)"),
        ("OK", "speed preset: 100, 75, 50, 25 %"),
    ]),
    ("NORA's IR link (her web page, controller or Bluetooth)", [
        ("arrows / I J K L", "drive"),
        ("STOP", "stop, and out of obstacle mode"),
        ("AUTO / MANUAL", "OBSTACLE / WASD mode"),
        ("SPEED", "speed preset"),
        ("LOCK / UNLOCK", "lock her wheels (nothing drives her) / free them"),
    ]),
]


# ── Everything below is the same in every robot's keymap.py ─────────────────────

def show(title=None, keymap=None):
    """The keymap in its own small window: one table per input, scrolls if it's long."""
    import tkinter as tk

    title, keymap = title or TITLE, keymap or KEYMAP
    bg, panel, accent, text, dim = "#07090f", "#0a0e1a", "#6496e6", "#d7e6ff", "#4a5f80"
    root = tk.Tk()
    root.title(title)
    root.configure(bg=bg)
    root.geometry("560x720")
    canvas = tk.Canvas(root, bg=bg, highlightthickness=0)
    bar = tk.Scrollbar(root, command=canvas.yview)
    body = tk.Frame(canvas, bg=bg)
    body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=body, anchor="nw")
    canvas.configure(yscrollcommand=bar.set)
    canvas.pack(side="left", fill="both", expand=True)
    bar.pack(side="right", fill="y")
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    tk.Label(body, text=title.upper(), bg=bg, fg=accent,
             font=("Courier New", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
    for section, rows in keymap:
        tk.Label(body, text=section, bg=bg, fg=accent,
                 font=("Courier New", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        table = tk.Frame(body, bg=panel)
        table.pack(fill="x", padx=16)
        for i, (key, does) in enumerate(rows):
            tk.Label(table, text=key, bg=panel, fg=text, font=("Courier New", 11, "bold"),
                     anchor="w", width=18).grid(row=i, column=0, sticky="w", padx=(8, 4), pady=1)
            tk.Label(table, text=does, bg=panel, fg=text if key else dim, font=("Courier New", 10),
                     anchor="w", justify="left", wraplength=330).grid(row=i, column=1, sticky="w", pady=1)
    root.bind("<Escape>", lambda e: root.destroy())
    root.bind("<F1>", lambda e: root.destroy())
    root.mainloop()


def to_markdown(keymap=None):
    """The README's "Controls" tables."""
    out = []
    for section, rows in keymap or KEYMAP:
        out += [f"**{section}**", "", "| Key | Does |", "|---|---|"]
        for key, does in rows:
            out.append(f"| {key} | {does} |" if key else f"| | *{does}* |")
        out.append("")
    return "\n".join(out)


def to_html(title=None, keymap=None):
    """The /keys page: the same tables, for the robot's own web page."""
    from html import escape
    title = title or TITLE
    rows = []
    for section, items in keymap or KEYMAP:
        rows.append(f"<h2>{escape(section)}</h2><table>")
        for key, does in items:
            rows.append(f"<tr><th>{escape(key)}</th><td>{escape(does)}</td></tr>" if key
                        else f"<tr><td colspan=2 class=n>{escape(does)}</td></tr>")
        rows.append("</table>")
    return ("<!DOCTYPE html><html><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{escape(title)}</title><style>"
            "body{background:#07090f;color:#d7e6ff;font-family:'Courier New',monospace;margin:0;padding:16px}"
            "h1{color:#6496e6;font-size:1.3rem;letter-spacing:2px}h2{color:#6496e6;font-size:1rem;margin:18px 0 6px}"
            "table{width:100%;border-collapse:collapse;background:#0a0e1a}"
            "th,td{text-align:left;padding:4px 8px;border-bottom:1px solid #1e3458;vertical-align:top}"
            "th{white-space:nowrap;width:1%}.n{color:#4a5f80;font-style:italic}"
            f"</style></head><body><h1>{escape(title.upper())}</h1>{''.join(rows)}</body></html>")


def write_header(path, name="KEYS_HTML"):
    """The /keys page as a C header for the ESP sketch. Generated: edit keymap.py, not the header."""
    import os
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"// {os.path.basename(path)} - generated by keymap.py (python keymap.py --header ...).\n"
                "// Don't edit it: change the list in keymap.py and write it again.\n"
                "#pragma once\n"
                f'static const char {name}[] PROGMEM = R"keys(' + to_html() + ')keys";\n')


def write_readme(path, start="<!-- keymap:start -->", end="<!-- keymap:end -->"):
    """Put the tables in the README between the two markers (added under "Controls" the first time)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    block = f"{start}\n<!-- generated by keymap.py --readme; edit the list there -->\n\n{to_markdown()}\n{end}"
    if start in text and end in text:
        text = text[:text.index(start)] + block + text[text.index(end) + len(end):]
    else:
        raise SystemExit(f"{path}: put {start} and {end} where the tables go")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def open_window():
    """Open the keymap window without blocking the caller (its own process, so pygame keeps running)."""
    import os
    import subprocess
    import sys
    try:
        subprocess.Popen([sys.executable, os.path.abspath(__file__)])
    except OSError as e:
        print(f"[keymap] can't open the window: {e}")


if __name__ == "__main__":
    import sys
    if "--header" in sys.argv:
        write_header(sys.argv[sys.argv.index("--header") + 1])
    elif "--readme" in sys.argv:
        write_readme(sys.argv[sys.argv.index("--readme") + 1])
    elif "--markdown" in sys.argv:
        print(to_markdown())
    else:
        show()
