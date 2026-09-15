#!/usr/bin/env python3
"""
Crowmail Bulk Inbox Generator
"""

import ctypes
import os
import secrets
import string
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

from crowmail import APIError, AuthenticationError, CrowmailClient, CrowmailError, RateLimitError

OUTPUT_DIR = PROJECT_ROOT / "output" / "generator"
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
        "INFO": "\033[38;5;51m",
        "INF": "\033[38;5;51m",
        "WARN": "\033[38;5;226m",
        "FAIL": "\033[38;5;196m",
        "ERR": "\033[38;5;196m",
        "ERROR": "\033[38;5;196m",
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
        f"    {eg.gradient('>', ['#00f5a0', '#00ebbe'])} Crowmail Inbox Generator "
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


def random_username(length: int = 10) -> str:
    """Generate clean random lowercase username."""
    chars = string.ascii_lowercase + string.digits
    first = secrets.choice(string.ascii_lowercase)
    rest = "".join(secrets.choice(chars) for _ in range(length - 1))
    return first + rest


class InboxGenerator:
    def __init__(
        self,
        amount: int,
        threads: int = 5,
        domain: str = "crowmail.sbs",
        password: str = "",
    ) -> None:
        self.amount = amount
        self.threads = max(1, threads)
        self.domain = domain.strip().lstrip("@")
        self.password = password
        self.output_lock = threading.Lock()
        self.success_count = 0
        self.fail_count = 0

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        self.start_time = time.time()
        self.running = True

    def _title_loop(self):
        while self.running:
            try:
                elapsed = round(time.time() - self.start_time, 1)
                title = (
                    f"Crowmail Gen | Created: {self.success_count} | "
                    f"Failed: {self.fail_count} | Target: {self.amount} | "
                    f"Elapsed: {elapsed}s | Made by @DraxonV1"
                )
                set_title(title)
            except Exception:
                pass
            time.sleep(0.3)

    def update_console_title(self):
        elapsed = round(time.time() - self.start_time, 1)
        set_title(
            f"Crowmail Gen | Created: {self.success_count} | "
            f"Failed: {self.fail_count} | Target: {self.amount} | "
            f"Elapsed: {elapsed}s | Made by @DraxonV1"
        )
    def save_result(self, email: str, pwd: str) -> None:
        with self.output_lock:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"{email}:{pwd}\n")

    def create_single_inbox(self) -> bool:
        username = random_username(10)
        email = f"{username}@{self.domain}"
        pwd = (
            self.password
            if self.password
            else CrowmailClient.generate_password(12)
        )

        with CrowmailClient(timeout=20) as client:
            try:
                client.create_account(email, pwd, expires_in=0)
                self.save_result(email, pwd)

                with self.output_lock:
                    self.success_count += 1
                self.update_console_title()

                C.log("OK", f"Created {email}", password=pwd)
                return True

            except RateLimitError as exc:
                with self.output_lock:
                    self.fail_count += 1
                self.update_console_title()
                C.log("WARN", f"Rate limited creating {email}", reason=str(exc))
                return False

            except APIError as exc:
                with self.output_lock:
                    self.fail_count += 1
                self.update_console_title()
                C.log("FAIL", f"Failed creating {email}", reason=str(exc))
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
        pass_mode = f"'{self.password}'" if self.password else "Random (12 chars)"
        print()
        print(f"    {C.DG}•{C.RS} {C.WH}Inboxes:{C.RS} {C.ORANGE}{self.amount}{C.RS}")
        print(f"    {C.DG}•{C.RS} {C.WH}Threads:{C.RS} {C.ORANGE}{self.threads}{C.RS}")
        print(f"    {C.DG}•{C.RS} {C.WH}Domain:{C.RS} {C.ORANGE}@{self.domain}{C.RS}")
        print(f"    {C.DG}•{C.RS} {C.WH}Password:{C.RS} {C.ORANGE}{pass_mode}{C.RS}")
        print(f"    {C.DG}•{C.RS} {C.WH}Saving to:{C.RS} {C.ORANGE}{OUTPUT_FILE}{C.RS}")
        print()

        C.log("INFO", f"Generating {self.amount} inboxes...")

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [
                executor.submit(self.create_single_inbox)
                for _ in range(self.amount)
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
            f"Done! Created {self.success_count}/{self.amount} inboxes",
            created=self.success_count,
            failed=self.fail_count,
        )
        print()


def get_default_domain() -> str:
    try:
        with CrowmailClient(timeout=8) as client:
            domains = client.get_domains()
            members = domains.get("hydra:member", [])
            if members and isinstance(members, list):
                dom = members[0].get("domain")
                if dom:
                    return dom
    except Exception:
        pass
    return "crowmail.sbs"


def main() -> None:
    set_title("Crowmail Inbox Generator | Made by @DraxonV1")
    bannerprint()

    # 1. Ask how many inboxes
    while True:
        amount_str = ask_input("How many inboxes to generate?", default="10")
        try:
            amount = int(amount_str)
            if amount <= 0:
                print(f"    {C.COLORS['FAIL']}[!] Amount must be greater than 0.{C.RS}")
                continue
            break
        except ValueError:
            print(f"    {C.COLORS['FAIL']}[!] Enter a valid number.{C.RS}")

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
            print(f"    {C.COLORS['FAIL']}[!] Enter a valid number.{C.RS}")

    # 3. Ask domain
    def_domain = get_default_domain()
    domain = ask_input("Domain for inboxes", default=def_domain)

    # 4. Ask password
    password = ask_input("Password (leave blank for random)", default="")

    # 5. Run generator
    generator = InboxGenerator(
        amount=amount,
        threads=threads,
        domain=domain,
        password=password,
    )
    generator.run()


if __name__ == "__main__":
    main()
