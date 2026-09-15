#!/usr/bin/env python3
"""
Crowmail Bulk Password Changer
"""

import ctypes
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import easygradients as eg

from crowmail import AuthenticationError, CrowmailClient, CrowmailError, RateLimitError

INPUT_FILE = PROJECT_ROOT / "input" / "emails.txt"
OUTPUT_DIR = PROJECT_ROOT / "output" / "password-changer"
OUTPUT_FILE = OUTPUT_DIR / "emails.txt"


class C:
    DG = "\033[38;5;238m"
    WH = "\033[38;5;255m"
    RS = "\033[0m"
    ORANGE = "\033[38;5;208m"

    COLORS = {
        "SUCCESS": "\033[38;5;46m",
        "OK": "\033[38;5;46m",
        "DONE": "\033[38;5;46m",
        "ONLINE": "\033[38;5;46m",
        "VIEW": "\033[38;5;87m",
        "INFO": "\033[38;5;51m",
        "INF": "\033[38;5;51m",
        "WARN": "\033[38;5;226m",
        "FAIL": "\033[38;5;196m",
        "ERR": "\033[38;5;196m",
        "ERROR": "\033[38;5;196m",
        "EMAIL": "\033[38;5;141m",
    }
    lock = threading.Lock()

    @staticmethod
    def log(stamp: str, msg: str, **kwargs):
        ts = time.strftime("%H:%M:%S")
        clr = C.COLORS.get(stamp.upper(), C.WH)
        dg = C.DG
        wh = C.WH
        rst = C.RS

        tag = stamp.upper()[:4]
        line = f"{wh}{ts} {clr}{tag:<4}{rst} {dg}•{rst} {wh}{msg}{rst}"
        if kwargs:
            parts = [f"{wh}{k}: {dg}[{clr}{v}{dg}]{rst}" for k, v in kwargs.items()]
            line += f" {dg}|{rst} " + f" {dg}|{rst} ".join(parts)

        with C.lock:
            print(line)


def set_title(title: str):
    try:
        if sys.platform not in ("linux", "darwin"):
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()
    except Exception:
        pass


def bannerprint():
    banner = """    ████▄   ▄▄▄▄   ▄▄▄  ▄▄ ▄▄  ▄▄▄  ▄▄  ▄▄
    ██  ██ ██▄█▄ ██▀██ ▀█▄█▀ ██▀██ ███▄██
    ████▀  ██ ██ ██▀██ ██ ██ ▀███▀ ██ ▀██
    """
    print(eg.gradient(banner, ["#00f5a0", "#00ebbe", "#00d9f5"]))
    print()
    print(
        f"    {eg.gradient('>', ['#00f5a0', '#00ebbe'])} Crowmail Password Changer "
        f"\033[90mMade by @DraxonV1\033[0m"
    )
    print()


def ask_input(label: str, default: Optional[str] = None) -> str:
    default_str = f" (default: {default})" if default is not None else ""
    prompt = f"    {C.ORANGE}[>]{C.RS} {C.WH}{label}{default_str}:{C.RS} "
    val = input(prompt)
    res = val.strip()
    if not res and default is not None:
        return default
    return res


def parse_account_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    for sep in (":", " ", "|", ","):
        if sep in line:
            parts = [p.strip() for p in line.split(sep, 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts[0], parts[1]

    return None


def load_accounts(filepath: Path) -> list[tuple[str, str]]:
    if not filepath.exists():
        return []

    accounts = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            acc = parse_account_line(line)
            if acc:
                accounts.append(acc)
    return accounts


class PasswordChanger:
    def __init__(
        self,
        accounts: list[tuple[str, str]],
        threads: int = 5,
        new_password: str = "",
    ) -> None:
        self.accounts = accounts
        self.threads = max(1, threads)
        self.new_password = new_password
        self.output_lock = threading.Lock()
        self.success_count = 0
        self.fail_count = 0
        self.total = len(accounts)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        self.start_time = time.time()
        self.running = True

    def _title_loop(self):
        while self.running:
            try:
                elapsed = round(time.time() - self.start_time, 1)
                title = (
                    f"Crowmail Changer | Success: {self.success_count} | "
                    f"Failed: {self.fail_count} | Total: {self.total} | "
                    f"Elapsed: {elapsed}s | Made by @DraxonV1"
                )
                set_title(title)
            except Exception:
                pass
            time.sleep(0.3)

    def update_console_title(self):
        elapsed = round(time.time() - self.start_time, 1)
        set_title(
            f"Crowmail Changer | Success: {self.success_count} | "
            f"Failed: {self.fail_count} | Total: {self.total} | "
            f"Elapsed: {elapsed}s | Made by @DraxonV1"
        )
    def save_result(self, email: str, new_pass: str) -> None:
        with self.output_lock:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"{email}:{new_pass}\n")

    def process_account(self, email: str, old_pass: str) -> bool:
        target_password = (
            self.new_password
            if self.new_password
            else CrowmailClient.generate_password(12)
        )

        with CrowmailClient(timeout=20) as client:
            try:
                # 1. Authenticate
                client.login(email, old_pass)

                # 2. Change password
                client.change_password(old_pass, target_password)

                # 3. Save
                self.save_result(email, target_password)
                with self.output_lock:
                    self.success_count += 1
                self.update_console_title()

                C.log("OK", f"Changed pass for {email}", new_pass=target_password)
                return True

            except AuthenticationError as exc:
                with self.output_lock:
                    self.fail_count += 1
                self.update_console_title()
                C.log("FAIL", f"Failed for {email}", reason=str(exc))
                return False

            except RateLimitError as exc:
                with self.output_lock:
                    self.fail_count += 1
                self.update_console_title()
                C.log("WARN", f"Rate limited on {email}", reason=str(exc))
                return False

            except CrowmailError as exc:
                with self.output_lock:
                    self.fail_count += 1
                self.update_console_title()
                C.log("FAIL", f"API error on {email}", reason=str(exc))
                return False

            except Exception as exc:
                with self.output_lock:
                    self.fail_count += 1
                self.update_console_title()
                C.log("ERR", f"Error on {email}", reason=str(exc))
                return False

    def run(self) -> None:
        self.start_time = time.time()
        self.running = True
        t_thread = threading.Thread(target=self._title_loop, daemon=True)
        t_thread.start()
        self.update_console_title()
        pass_mode = f"'{self.new_password}'" if self.new_password else "Random (12 chars)"
        print()
        print(f"    {C.DG}•{C.RS} {C.WH}Accounts:{C.RS} {C.ORANGE}{self.total}{C.RS}")
        print(f"    {C.DG}•{C.RS} {C.WH}Threads:{C.RS} {C.ORANGE}{self.threads}{C.RS}")
        print(f"    {C.DG}•{C.RS} {C.WH}New Pass:{C.RS} {C.ORANGE}{pass_mode}{C.RS}")
        print(f"    {C.DG}•{C.RS} {C.WH}Saving to:{C.RS} {C.ORANGE}{OUTPUT_FILE}{C.RS}")
        print()

        C.log("INFO", f"Changing pass for {self.total} accounts...")
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [
                executor.submit(self.process_account, email, pwd)
                for email, pwd in self.accounts
            ]
            try:
                for future in as_completed(futures):
                    future.result()
            except KeyboardInterrupt:
                C.log("WARN", "Stopped by user. Finishing up...")
                executor.shutdown(wait=False, cancel_futures=True)

        self.running = False
        self.update_console_title()
        print()
        C.log(
            "DONE",
            f"Changed pass for {self.success_count}/{self.total} accounts",
            success=self.success_count,
            failed=self.fail_count,
        )
        print()


def main() -> None:
    set_title("Crowmail Password Changer | Made by @DraxonV1")
    bannerprint()

    # 1. Ensure input file exists
    if not INPUT_FILE.exists():
        INPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        INPUT_FILE.touch()
        C.log("WARN", f"No input file yet. Made empty '{INPUT_FILE}'.")
        C.log("INFO", "Put email:password lines in it and run again.")
        sys.exit(1)

    accounts = load_accounts(INPUT_FILE)
    if not accounts:
        C.log("FAIL", f"No accounts found in '{INPUT_FILE}'.")
        C.log("INFO", "Format: email:password")
        sys.exit(1)

    C.log("INFO", f"Loaded {len(accounts)} accounts", file=str(INPUT_FILE))
    print()

    # 2. Ask how many threads
    while True:
        threads_str = ask_input("How many threads?", default="5")
        try:
            threads = int(threads_str)
            if threads <= 0:
                print(f"    {C.COLORS['FAIL']}[!] Threads must be greater than 0.{C.RS}")
                continue
            break
        except ValueError:
            print(f"    {C.COLORS['FAIL']}[!] Invalid integer.{C.RS}")

    # 3. Ask how many amount
    while True:
        amount_str = ask_input(f"How many accounts? (1-{len(accounts)})", default="all")
        if amount_str.lower() in ("all", ""):
            selected_accounts = accounts
            break
        try:
            amount = int(amount_str)
            if amount <= 0:
                print(f"    {C.COLORS['FAIL']}[!] Amount must be greater than 0.{C.RS}")
                continue
            selected_accounts = accounts[:amount]
            break
        except ValueError:
            print(f"    {C.COLORS['FAIL']}[!] Enter a number or 'all'.{C.RS}")

    # 4. Ask new password (leave blank for random)
    new_password = ask_input("New password (leave blank for random)", default="")

    # 5. Run changer
    changer = PasswordChanger(
        accounts=selected_accounts,
        threads=threads,
        new_password=new_password,
    )
    changer.run()


if __name__ == "__main__":
    main()
