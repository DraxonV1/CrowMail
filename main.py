#!/usr/bin/env python3
"""
Crowmail Multi-Tool Launcher
Interactive menu with keyboard arrow navigation, numeric shortcuts, and CTRL+C handling.
"""

import ctypes
import os
import subprocess
import sys
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import easygradients as eg

GEN_SCRIPT = PROJECT_ROOT / "gen" / "main.py"
CHANGER_SCRIPT = PROJECT_ROOT / "password" / "changer.py"


class C:
    DG = "\033[38;5;238m"
    WH = "\033[38;5;255m"
    RS = "\033[0m"
    ORANGE = "\033[38;5;208m"
    GREEN = "\033[38;5;46m"
    CYAN = "\033[38;5;51m"


def set_title(title: str):
    try:
        if sys.platform not in ("linux", "darwin"):
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()
    except Exception:
        pass


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def bannerprint():
    banner = """    ████▄   ▄▄▄▄   ▄▄▄  ▄▄ ▄▄  ▄▄▄  ▄▄  ▄▄
    ██  ██ ██▄█▄ ██▀██ ▀█▄█▀ ██▀██ ███▄██
    ████▀  ██ ██ ██▀██ ██ ██ ▀███▀ ██ ▀██
    """
    print(eg.gradient(banner, ["#00f5a0", "#00ebbe", "#00d9f5"]))
    print()
    print(
        f"    {eg.gradient('>', ['#00f5a0', '#00ebbe'])} Crowmail Suite "
        f"\033[90mMade by @DraxonV1\033[0m"
    )
    print(
        f"    {eg.gradient('>', ['#00ebbe', '#00d9f5'])} Select a tool with \033[97m↑/↓ + ENTER\033[0m or press \033[97m1-3\033[0m"
    )
    print()


def get_key() -> str:
    """Read a single keypress without waiting for Enter."""
    if not sys.stdin.isatty():
        ch = sys.stdin.read(1)
        if not ch:
            return "ESC"
        if ch in ("\r", "\n"):
            return "ENTER"
        return ch

    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getch()
        if ch == b"\x03":
            raise KeyboardInterrupt
        if ch in (b"\x00", b"\xe0"):
            ch2 = msvcrt.getch()
            if ch2 == b"H":
                return "UP"
            elif ch2 == b"P":
                return "DOWN"
            return "SPECIAL"
        if ch in (b"\r", b"\n"):
            return "ENTER"
        if ch == b"\x1b":
            return "ESC"
        try:
            return ch.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\x1b":
                # Check for arrow key escape sequence
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":
                        return "UP"
                    elif ch3 == "B":
                        return "DOWN"
                return "ESC"
            if ch in ("\r", "\n"):
                return "ENTER"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


MENU_OPTIONS = [
    {
        "id": "gen",
        "num": "1",
        "title": "Inbox Generator",
        "desc": "Create fresh Crowmail inboxes in bulk",
        "target": GEN_SCRIPT,
    },
    {
        "id": "changer",
        "num": "2",
        "title": "Password Changer",
        "desc": "Rotate passwords for existing inboxes",
        "target": CHANGER_SCRIPT,
    },
    {
        "id": "exit",
        "num": "3",
        "title": "Exit",
        "desc": "Close the launcher",
        "target": None,
    },
]


def render_menu(selected_idx: int):
    clear_screen()
    bannerprint()

    for idx, opt in enumerate(MENU_OPTIONS):
        is_sel = idx == selected_idx
        num = opt["num"]
        title = opt["title"]
        desc = opt["desc"]

        if is_sel:
            arrow = eg.gradient(">", ["#00f5a0", "#00ebbe"])
            num_tag = f"{C.GREEN}[{num}]{C.RS}"
            title_tag = f"{C.GREEN}{title}{C.RS}"
            desc_tag = f"{C.WH}{desc}{C.RS}"
            print(f"    {arrow} {num_tag} {title_tag} {C.DG}•{C.RS} {desc_tag}")
        else:
            arrow = " "
            num_tag = f"{C.DG}[{num}]{C.RS}"
            title_tag = f"{C.WH}{title}{C.RS}"
            desc_tag = f"{C.DG}{desc}{C.RS}"
            print(f"      {num_tag} {title_tag} {C.DG}•{C.RS} {desc_tag}")

    print()
    print(f"    {C.DG}Navigate: [↑/↓] or [1-3] | Select: [ENTER] | Quit: [CTRL+C / ESC]{C.RS}")
    print()


def run_tool(script_path: Path):
    clear_screen()
    try:
        subprocess.run([sys.executable, str(script_path)])
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"\n[!] Error launching tool: {exc}")

    print()
    print(f"    {C.ORANGE}[>]{C.RS} {C.WH}Press any key to return to menu...{C.RS}", end="", flush=True)
    try:
        get_key()
    except KeyboardInterrupt:
        pass


def main():
    set_title("Crowmail Suite | Made by @DraxonV1")
    selected_idx = 0

    while True:
        set_title("Crowmail Suite | Made by @DraxonV1")
        render_menu(selected_idx)

        try:
            key = get_key()
        except KeyboardInterrupt:
            clear_screen()
            print(f"\n    {C.GREEN}[*]{C.RS} {C.WH}Exiting. Goodbye!{C.RS}\n")
            sys.exit(0)

        if key == "UP":
            selected_idx = (selected_idx - 1) % len(MENU_OPTIONS)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(MENU_OPTIONS)
        elif key == "ENTER":
            choice = MENU_OPTIONS[selected_idx]
            if choice["id"] == "exit":
                clear_screen()
                print(f"\n    {C.GREEN}[*]{C.RS} {C.WH}Exiting. Goodbye!{C.RS}\n")
                sys.exit(0)
            elif choice["target"]:
                run_tool(choice["target"])
        elif key in ("1", "2", "3"):
            idx = int(key) - 1
            if 0 <= idx < len(MENU_OPTIONS):
                choice = MENU_OPTIONS[idx]
                if choice["id"] == "exit":
                    clear_screen()
                    print(f"\n    {C.GREEN}[*]{C.RS} {C.WH}Exiting. Goodbye!{C.RS}\n")
                    sys.exit(0)
                elif choice["target"]:
                    run_tool(choice["target"])
        elif key in ("ESC", "q", "Q"):
            clear_screen()
            print(f"\n    {C.GREEN}[*]{C.RS} {C.WH}Exiting. Goodbye!{C.RS}\n")
            sys.exit(0)


if __name__ == "__main__":
    main()
