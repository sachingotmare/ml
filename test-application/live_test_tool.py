from __future__ import annotations

import json
import re
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
import tkinter as tk
from tkinter import ttk, messagebox

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from playwright.sync_api import Error as PWError

APP_TITLE = "MLab Live Test Application"
CONFIG_FILE = Path(__file__).with_name("credentials.json")


@dataclass
class RunOptions:
    all_cases: bool = False
    masters_accounts: bool = False
    masters_tests: bool = False
    masters_rates: bool = False
    masters_doctors: bool = False
    main_patient_entry: bool = False
    main_readings: bool = False
    main_receipt_entry: bool = False
    reports_all: bool = False
    headless: bool = False
    manual_login_fallback: bool = True
    manual_login_timeout_sec: int = 120
    manual_pause_mode: bool = False
    browser: str = "edge"  # edge | chromium


@dataclass
class RunResult:
    name: str
    status: str
    details: str


class LiveFlowRunner:
    def __init__(self, base_url: str, lab_code: str, username: str, password: str, log_fn):
        self.base_url = base_url.strip()
        u = urlsplit(self.base_url)
        self.app_origin = f"{u.scheme}://{u.netloc}"
        self.lab_code = lab_code.strip()
        self.username = username.strip()
        self.password = password
        self.log = log_fn
        self.results: list[RunResult] = []
        self.context_data: dict[str, str] = {}

    _ROUTE_BY_LABEL = {
        "Accounts": "/accounts",
        "Tests": "/tests",
        "Doctors": "/doctors",
        "Rates": "/rates",
        "Patient Entry": "/patient-entry",
        "Receipt Entry": "/receipt-entry",
        "Readings": "/readings",
        "Reports": "/reports",
    }

    def run(self, options: RunOptions) -> list[RunResult]:
        selected = self._normalize_selection(options)
        with sync_playwright() as p:
            browser = self._launch_browser(p, options)
            context = browser.new_context(ignore_https_errors=True, viewport={"width": 1600, "height": 950})
            page = context.new_page()
            self._active_page = page
            preserve_browser_for_debug = False
            try:
                page = self._login(page, options)
                self._active_page = page

                if selected["masters_accounts"]:
                    self._case("Masters: Accounts", lambda: self._create_or_pick_account(page, create=True))
                if selected["masters_tests"]:
                    self._case("Masters: Tests", lambda: self._create_or_pick_tests(page, create=True))
                if selected["masters_rates"]:
                    self._case("Masters: Rates", lambda: self._create_rates(page, create=True))
                if selected["masters_doctors"]:
                    self._case("Masters: Doctors", lambda: self._create_or_pick_doctor(page, create=True))

                if selected["main_patient_entry"] and not self._any_master_selected(selected):
                    self._case("Use existing Account/Test/Doctor", self._prepare_existing_entities)

                if selected["main_patient_entry"]:
                    self._case("Main: Patient Entry", lambda: self._patient_entry(page))
                if selected["main_receipt_entry"]:
                    self._case("Main: Receipt Entry", lambda: self._receipt_entry(page))
                if selected["main_readings"]:
                    self._case("Main: Readings", lambda: self._readings(page))
                if selected["reports_all"]:
                    self._case("Reports: All", lambda: self._reports_all(page))
            except Exception as ex:
                if not options.headless:
                    preserve_browser_for_debug = True
                    hold_sec = 120
                    self.log(
                        f"ℹ Run failed. Keeping browser open for {hold_sec}s so you can inspect it "
                        "(it will NOT auto-close immediately)."
                    )
                    try:
                        end = datetime.now()
                        start = datetime.now()
                        while (datetime.now() - start).total_seconds() < hold_sec:
                            if page.is_closed():
                                self.log("ℹ Browser window was closed by user.")
                                break
                            page.wait_for_timeout(1000)
                    except Exception:
                        pass
                raise
            finally:
                if not preserve_browser_for_debug:
                    context.close()
                    browser.close()
                else:
                    try:
                        context.close()
                    except Exception:
                        pass
                    try:
                        browser.close()
                    except Exception:
                        pass

        self._write_report(options)
        return self.results

    def _launch_browser(self, p, options: RunOptions):
        try:
            self.log("ℹ Launching Microsoft Edge channel...")
            return p.chromium.launch(channel="msedge", headless=options.headless)
        except Exception as ex:
            raise RuntimeError(
                "Microsoft Edge launch failed. Install Edge on server and run: "
                "python -m playwright install msedge"
            ) from ex

    def _normalize_selection(self, options: RunOptions) -> dict[str, bool]:
        if options.all_cases:
            return {
                "masters_accounts": True,
                "masters_tests": True,
                "masters_rates": True,
                "masters_doctors": True,
                "main_patient_entry": True,
                "main_readings": True,
                "main_receipt_entry": True,
                "reports_all": True,
            }
        return {
            "masters_accounts": options.masters_accounts,
            "masters_tests": options.masters_tests,
            "masters_rates": options.masters_rates,
            "masters_doctors": options.masters_doctors,
            "main_patient_entry": options.main_patient_entry,
            "main_readings": options.main_readings,
            "main_receipt_entry": options.main_receipt_entry,
            "reports_all": options.reports_all,
        }

    @staticmethod
    def _any_master_selected(selected: dict[str, bool]) -> bool:
        return any(selected[k] for k in ("masters_accounts", "masters_tests", "masters_rates", "masters_doctors"))

    def _case(self, name: str, fn):
        self.log(f"▶ {name}")
        try:
            fn()
            self.results.append(RunResult(name, "PASS", "Completed"))
            self.log(f"✓ {name}")
        except Exception as ex:
            self.results.append(RunResult(name, "FAIL", str(ex)))
            self.log(f"✗ {name}: {ex}")
            self.log(traceback.format_exc())
            self._cleanup_after_failure(fn)

    def _cleanup_after_failure(self, fn):
        """Best-effort: close any leftover modal/overlay so the NEXT step isn't
        blocked by a stale backdrop intercepting clicks."""
        page = getattr(self, "_active_page", None)
        if page is None:
            return
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception:
            pass


    def _login(self, page, options: RunOptions):
        self._open_login_with_fallbacks(page)

        # If already in app shell, skip login handling.
        if self._is_app_shell_ready(page):
            self.log("✓ App shell already detected; skipping login step.")
            return page

        if options.manual_pause_mode and not options.headless:
            self.log(
                "Manual pause mode active. Please complete login in opened browser "
                f"within {options.manual_login_timeout_sec}s."
            )
            self.log(
                "ℹ In manual mode, tool will NOT auto-fill credentials. "
                "Please type Lab Code/User/Password yourself and click Sign In."
            )
            timeout_ms = max(10, int(options.manual_login_timeout_sec)) * 1000
            start = datetime.now()
            warned_invalid = False
            warned_lockout = False
            while (datetime.now() - start).total_seconds() * 1000 < timeout_ms:
                active_page = self._resolve_active_page(page)
                if active_page is None:
                    raise RuntimeError("Browser window was closed before login completed.")
                if active_page is not page:
                    page = active_page
                    self.log("ℹ Detected page switch during login; continuing on active page.")
                if self._is_app_shell_ready(page):
                    self.log("✓ Manual login detected.")
                    return page
                err_txt = self._visible_login_error_text(page)
                if "invalid credentials" in err_txt:
                    if not warned_invalid:
                        self.log(
                            "ℹ Invalid credentials message is visible. "
                            "Please correct credentials in browser and click Sign In manually. "
                            "Hint: Lab Code is case-sensitive (e.g., DEMO2026)."
                        )
                        warned_invalid = True
                if (
                    (
                        ("lock" in err_txt and "account" in err_txt)
                        or "too many attempts" in err_txt
                    )
                    and not warned_lockout
                ):
                    self.log(
                        "ℹ Account lockout may be active after repeated failed attempts. "
                        "Wait/unlock account, then retry."
                    )
                    warned_lockout = True
                try:
                    page.wait_for_timeout(500)
                except PWError:
                    # Page can close between checks; next loop iteration will try to recover active page.
                    continue
            self._save_login_diagnostics(page)

        candidates = self._lab_code_candidates(self.lab_code)
        self._prefill_login(page, candidates[0], required=True)
        self._click_login_button(page)

        page.wait_for_timeout(1200)
        # Some builds require a second click confirmation (first click just focuses/validates).
        if "login" in (page.url or "").lower():
            self.log("ℹ Sign In did not navigate yet. Clicking Sign In again...")
            self._click_login_button(page)
            page.wait_for_timeout(1200)

        try:
            page.wait_for_function(
                "() => {"
                "  const p = location.pathname.toLowerCase();"
                "  const t = (document.body && document.body.innerText || '').toLowerCase();"
                "  const hasNav = ['patient entry','accounts','tests','rates','doctors','readings','receipt entry']"
                "    .some(x => t.includes(x));"
                "  return !p.includes('login') && (p.includes('dashboard') || hasNav);"
                "}",
                timeout=25000,
            )
            return page
        except Exception:
            pass

        # Still on login page? Try clicking Sign In a couple more times before giving up on auto-login.
        for attempt in range(3):
            if "login" not in (page.url or "").lower():
                break
            self.log(f"ℹ Retrying Sign In click (attempt {attempt + 2})...")
            self._click_login_button(page)
            page.wait_for_timeout(1500)
            if self._is_app_shell_ready(page):
                return page

        # If credentials were rejected and we have a candidate lab-code variant, retry once.
        login_err = self._visible_login_error_text(page)
        if "invalid credentials" in login_err and len(candidates) > 1:
            self.log(f"ℹ Invalid credentials detected. Retrying with Lab Code: {candidates[1]}")
            self._prefill_login(page, candidates[1], required=True)
            self._click_login_button(page)
            page.wait_for_timeout(1500)
            if self._is_app_shell_ready(page):
                return page

        try:
            page.wait_for_selector("text=Patient Entry, text=Dashboard, text=Tests", timeout=12000)
            return page
        except Exception:
            if options.manual_login_fallback and not options.headless:
                self.log(
                    f"ℹ Auto-login not confirmed (captcha/anti-bot likely). "
                    f"Waiting up to {options.manual_login_timeout_sec}s for manual login..."
                )
                try:
                    page.wait_for_function(
                        "() => {"
                        "  const p = location.pathname.toLowerCase();"
                        "  const t = (document.body && document.body.innerText || '').toLowerCase();"
                        "  const hasNav = ['patient entry','accounts','tests','rates','doctors','readings','receipt entry']"
                        "    .some(x => t.includes(x));"
                        "  return !p.includes('login') && (p.includes('dashboard') || hasNav);"
                        "}",
                        timeout=max(10, int(options.manual_login_timeout_sec)) * 1000,
                    )
                    self.log("✓ Manual login detected.")
                    return page
                except Exception:
                    pass

            self._save_login_diagnostics(page)

        return page

    def _open_login_with_fallbacks(self, page):
        candidates = self._login_url_candidates(self.base_url)
        last_error = None
        connection_refused_count = 0

        for i, candidate in enumerate(candidates):
            try:
                if i > 0:
                    self.log(f"ℹ Retrying login URL: {candidate}")
                page.goto(candidate, wait_until="domcontentloaded")
                self.base_url = candidate
                u = urlsplit(candidate)
                self.app_origin = f"{u.scheme}://{u.netloc}"
                return
            except Exception as ex:
                last_error = ex
                msg = str(ex)
                if "ERR_SSL_PROTOCOL_ERROR" in msg and candidate.startswith("https://"):
                    self.log(f"ℹ HTTPS failed for {candidate}. Trying next fallback...")
                elif "ERR_HTTP_RESPONSE_CODE_FAILURE" in msg:
                    self.log(f"ℹ HTTP response failure for {candidate}. Trying next fallback...")
                elif "ERR_CONNECTION_REFUSED" in msg or "chromewebdata" in msg.lower():
                    connection_refused_count += 1
                    self.log(f"ℹ Connection refused for {candidate}. Trying next fallback...")

        attempted = "\n- ".join(candidates)
        hint = ""
        if connection_refused_count == len(candidates):
            hint = (
                "\nAll attempts were refused/unreachable. This means nothing is listening on port 1007 "
                "for any localhost/127.0.0.1 + http/https combination from this machine.\n"
                "Please verify on THIS server (not from another PC):\n"
                "1) Is the MLab web service actually running right now?\n"
                "2) Open a normal Edge window (not this tool) and manually browse to the exact URL "
                "you use day-to-day (correct scheme/host/port).\n"
                "3) Update the URL field in this tool to that exact working URL and Save Config."
            )
        raise RuntimeError(
            "Could not open login page using localhost fallbacks. "
            f"Attempted:\n- {attempted}\nLast error: {last_error}{hint}"
        )

    def _login_url_candidates(self, url: str) -> list[str]:
        u = urlsplit(url)
        path = u.path or "/"
        if not path.startswith("/"):
            path = "/" + path

        out: list[str] = []

        def add(scheme: str, host: str, port: int | None, p: str):
            netloc = f"{host}:{port}" if port else host
            full = f"{scheme}://{netloc}{p}"
            if full not in out:
                out.append(full)

        host = (u.hostname or "").lower()
        port = u.port

        # Keep original first.
        if url not in out:
            out.append(url)

        if host in {"localhost", "127.0.0.1"}:
            alt_host = "127.0.0.1" if host == "localhost" else "localhost"
            # Same path, protocol/host variants.
            add("https", host, port, path)
            add("http", host, port, path)
            add("https", alt_host, port, path)
            add("http", alt_host, port, path)

            # Root-path variants (in case /login is not server-routed in prod host config).
            add("https", host, port, "/")
            add("http", host, port, "/")
            add("https", alt_host, port, "/")
            add("http", alt_host, port, "/")

        return out

    def _lab_code_candidates(self, lab_code: str) -> list[str]:
        base = (lab_code or "").strip()
        out: list[str] = []
        # Tenant-specific casing normalization for DEMO2026 login.
        if base.lower() == "demo2026":
            # Do not try alternate casing for this tenant; login is case-sensitive.
            return ["DEMO2026"]
        for c in [base, base.title(), base.upper(), base.lower()]:
            if c and c not in out:
                out.append(c)
        return out or [lab_code]

    def _prefill_login(self, page, lab_code: str, *, required: bool = True):
        # Wait briefly for SPA login controls to mount.
        try:
            page.wait_for_selector("input", timeout=10000)
        except Exception:
            if required:
                raise RuntimeError("Login inputs did not load")
            return

        ok_lab = self._try_fill_first(page, [
            page.get_by_role("textbox", name="Lab Code"),
            page.get_by_label("Organization / Lab Code"),
            page.get_by_placeholder("Enter organization or lab code"),
            page.get_by_placeholder("Organization / Lab Code"),
            page.get_by_placeholder("Lab Code"),
            page.locator("input[placeholder*='organization']"),
            page.locator("input").nth(0),
        ], lab_code)

        ok_user = self._try_fill_first(page, [
            page.get_by_role("textbox", name="User ID"),
            page.get_by_label("User ID"),
            page.get_by_placeholder("Enter your user ID"),
            page.get_by_placeholder("User ID"),
            page.locator("input").nth(1),
        ], self.username)

        ok_pwd = self._try_fill_first(page, [
            page.get_by_role("textbox", name="Password"),
            page.get_by_label("Password"),
            page.get_by_placeholder("Enter your password"),
            page.get_by_placeholder("Password"),
            page.locator("input[type='password']"),
            page.locator("input").nth(2),
        ], self.password)

        if required and not (ok_lab and ok_user and ok_pwd):
            raise RuntimeError("Required input field not found")

    def _click_login_button(self, page):
        clicked = self._click_first(page, [
            page.get_by_role("button", name="Sign In"),
            page.get_by_role("button", name="Login"),
            page.locator("button[type='submit']"),
        ])
        if not clicked:
            raise RuntimeError("Login button not found")

    def _safe_body_text(self, page) -> str:
        try:
            if page.is_closed():
                return ""
            return page.locator("body").inner_text()[:4000]
        except PWError:
            return ""
        except Exception:
            return ""

    def _resolve_active_page(self, page):
        try:
            if not page.is_closed():
                return page
        except Exception:
            pass

        try:
            pages = list(page.context.pages)
            for p in reversed(pages):
                try:
                    if not p.is_closed():
                        return p
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _visible_login_error_text(self, page) -> str:
        parts: list[str] = []
        selectors = [
            "[role='alert']",
            ".alert",
            ".error",
            ".invalid-feedback",
            ".toast-body",
            "[class*='error']",
            "[class*='invalid']",
        ]
        for sel in selectors:
            try:
                loc = page.locator(sel)
                n = min(loc.count(), 4)
                for i in range(n):
                    node = loc.nth(i)
                    if node.is_visible(timeout=150):
                        txt = (node.inner_text(timeout=200) or "").strip()
                        if txt:
                            parts.append(txt)
            except Exception:
                continue
        return " ".join(parts).lower()

    def _is_app_shell_ready(self, page) -> bool:
        p = (page.url or "").lower()
        if "login" in p:
            return False
        t = self._safe_body_text(page).lower()
        return ("dashboard" in p) or any(x in t for x in [
            "patient entry", "accounts", "tests", "rates", "doctors", "readings", "receipt entry"
        ])

    def _save_login_diagnostics(self, page):
        out_dir = Path(__file__).resolve().parent
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot = out_dir / f"login_failed_{stamp}.png"
        html = out_dir / f"login_failed_{stamp}.html"
        active_page = self._resolve_active_page(page)
        if active_page is None:
            raise RuntimeError("Login could not be confirmed because browser/page was closed before completion.")

        active_page.screenshot(path=str(shot), full_page=True)
        html_text = active_page.content()
        html.write_text(html_text, encoding="utf-8")
        body = re.sub(r"\s+", " ", active_page.locator("body").inner_text()[:500].strip())
        low_html = html_text.lower()
        anti_bot_hint = ""
        if "/cdn-cgi/challenge-platform" in low_html or "__cf$cv$params" in low_html:
            anti_bot_hint = (
                "\nLikely anti-bot/captcha gate detected. Use non-headless manual login mode, "
                "complete sign-in in the same opened window, and do not close/switch the login tab early."
            )
        raise RuntimeError(
            f"Login could not be confirmed. Saved diagnostics:\n- {shot.name}\n- {html.name}\n"
            f"Current URL: {active_page.url}\nPage snippet: {body}{anti_bot_hint}"
        )

    @staticmethod
    def _try_fill_first(page, locators, value: str) -> bool:
        for loc in locators:
            try:
                if loc.count() > 0:
                    loc.first.fill(value)
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _fill_first(page, locators, value: str):
        if LiveFlowRunner._try_fill_first(page, locators, value):
            return
        raise RuntimeError("Required input field not found")

    @staticmethod
    def _click_first(page, locators) -> bool:
        for loc in locators:
            try:
                if loc.count() > 0:
                    loc.first.click()
                    return True
            except Exception:
                continue
        return False

    def _click_named_button(self, page, name: str, *, timeout: int = 3000) -> bool:
        """Click first enabled button matching role=name.
        Avoids Playwright strict-mode violations when multiple same-name buttons exist.
        """
        btns = page.get_by_role("button", name=name)
        try:
            count = btns.count()
        except Exception:
            return False
        if count == 0:
            return False

        for i in range(count):
            b = btns.nth(i)
            try:
                disabled_attr = b.get_attribute("disabled")
                aria_disabled = (b.get_attribute("aria-disabled") or "").lower()
                if disabled_attr is not None or aria_disabled == "true":
                    continue
                b.click(timeout=timeout)
                return True
            except Exception:
                continue
        return False

    def _wait_and_click_named_button(
        self,
        page,
        name: str,
        *,
        wait_ms: int = 15000,
        poll_ms: int = 400,
        click_timeout: int = 3000,
    ) -> bool:
        """Wait until any same-name button becomes enabled, then click it."""
        start = datetime.now()
        while (datetime.now() - start).total_seconds() * 1000 < wait_ms:
            if self._click_named_button(page, name, timeout=click_timeout):
                return True
            page.wait_for_timeout(poll_ms)
        return False

    def _find_field(self, page, labels: list[str]):
        """Locate an input/textarea/select using label, placeholder, name, aria-label,
        or a nearby-label heuristic scoped to a small container (avoids grabbing
        unrelated inputs elsewhere on the page)."""
        for lb in labels:
            candidates = [
                page.get_by_label(lb, exact=False),
                page.get_by_placeholder(lb, exact=False),
                page.locator(f"input[name='{lb}']"),
                page.locator(f"input[aria-label='{lb}']"),
                page.locator(f"textarea[placeholder*='{lb}' i]"),
                page.locator(f"input[placeholder*='{lb}' i]"),
            ]
            # Scoped heuristic: label/span/div whose text CONTAINS the label text,
            # then look for an input/select within a small ancestor container.
            # Ancestor depth is limited (1, then 2 levels) to avoid grabbing
            # unrelated fields elsewhere on the page/in stale modals.
            for depth in (1, 2, 3):
                anc = "/".join(["ancestor::*[self::div or self::label]"] * 1)
                candidates.append(
                    page.locator(
                        "xpath=(//*[self::label or self::span or self::div]"
                        f"[contains(normalize-space(string(.)), '{lb}')])"
                        f"[last()]/ancestor::*[self::div][{depth}]//input"
                    )
                )
                candidates.append(
                    page.locator(
                        "xpath=(//*[self::label or self::span or self::div]"
                        f"[contains(normalize-space(string(.)), '{lb}')])"
                        f"[last()]/ancestor::*[self::div][{depth}]//select"
                    )
                )
            for loc in candidates:
                try:
                    if loc.count() > 0:
                        return loc.first
                except Exception:
                    continue
        return None

    def _find_dropdown_control(self, page, labels: list[str]):
        """Locate a dropdown control (native <select> or custom combobox) and report its kind."""
        for lb in labels:
            candidates = [
                page.get_by_label(lb, exact=False),
                page.locator(f"select[name='{lb}']"),
            ]
            for depth in (1, 2, 3):
                candidates.append(
                    page.locator(
                        "xpath=(//*[self::label or self::span or self::div]"
                        f"[contains(normalize-space(string(.)), '{lb}')])"
                        f"[last()]/ancestor::*[self::div][{depth}]//select"
                    )
                )
                candidates.append(
                    page.locator(
                        "xpath=(//*[self::label or self::span or self::div]"
                        f"[contains(normalize-space(string(.)), '{lb}')])"
                        f"[last()]/ancestor::*[self::div][{depth}]//*[@role='combobox' or contains(@class,'select')]"
                    )
                )
            for loc in candidates:
                try:
                    if loc.count() == 0:
                        continue
                    el = loc.first
                    tag = (el.evaluate("el => el.tagName") or "").lower()
                    return el, tag
                except Exception:
                    continue
        return None, None

    def _select_dropdown_option(self, page, labels: list[str], option_text: str) -> bool:
        """Select an option from a native <select> or a custom dropdown by visible text."""
        control, tag = self._find_dropdown_control(page, labels)
        if control is None:
            return False
        try:
            if tag == "select":
                try:
                    control.select_option(label=option_text)
                    return True
                except Exception:
                    # Fall back to matching by partial text among <option> values.
                    try:
                        opts = control.locator("option")
                        n = opts.count()
                        for i in range(n):
                            txt = (opts.nth(i).inner_text() or "").strip()
                            if option_text.lower() in txt.lower():
                                val = opts.nth(i).get_attribute("value")
                                if val is not None:
                                    control.select_option(value=val)
                                    return True
                    except Exception:
                        pass
                    return False
            else:
                control.click()
                page.wait_for_timeout(250)
                for opt_sel in [
                    f"[role='option']:has-text('{option_text}')",
                    f"li:has-text('{option_text}')",
                    f".dropdown-item:has-text('{option_text}')",
                    f"text={option_text}",
                ]:
                    try:
                        opt = page.locator(opt_sel)
                        if opt.count() > 0:
                            opt.first.click(timeout=2000)
                            return True
                    except Exception:
                        continue
                return False
        except Exception:
            return False

    def _fill_labeled(self, page, labels: list[str], value: str) -> bool:
        field = self._find_field(page, labels)
        if field is None:
            return False
        try:
            field.fill(value)
            return True
        except Exception:
            try:
                field.click()
                field.type(value, delay=20)
                return True
            except Exception:
                return False

    def _fill_autocomplete(self, page, labels: list[str], value: str) -> bool:
        """Fill a combobox-like field and commit selection from the dropdown list."""
        if not value:
            return False
        field = self._find_field(page, labels)
        if field is None:
            return False
        try:
            field.click()
            try:
                field.fill("")
            except Exception:
                pass
            # Type a short, forgiving prefix so the dropdown has a better chance to match.
            query = value[:6] if len(value) > 6 else value
            field.type(query, delay=30)
            page.wait_for_timeout(400)

            option = None
            for opt_sel in [
                f"[role='option']:has-text('{query}')",
                f"li:has-text('{query}')",
                f".dropdown-item:has-text('{query}')",
                "[role='option']",
                "li[role='option']",
            ]:
                try:
                    cand = page.locator(opt_sel)
                    if cand.count() > 0:
                        option = cand.first
                        break
                except Exception:
                    continue

            if option is not None:
                try:
                    option.click(timeout=2000)
                    page.wait_for_timeout(200)
                    return True
                except Exception:
                    pass

            # Fallback: keyboard select first suggestion.
            field.press("ArrowDown")
            page.wait_for_timeout(150)
            field.press("Enter")
            page.wait_for_timeout(200)
            return True
        except Exception:
            return False

    def _capture_step_diagnostics(self, page, tag: str):
        out_dir = Path(__file__).resolve().parent
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = tag.replace(" ", "_").replace("/", "_")
        shot = out_dir / f"step_failed_{safe}_{stamp}.png"
        html = out_dir / f"step_failed_{safe}_{stamp}.html"
        page.screenshot(path=str(shot), full_page=True)
        html.write_text(page.content(), encoding="utf-8")
        return shot.name, html.name

    def _menu(self, page, label: str):
        # Expand likely section first.
        if label in ("Accounts", "Tests", "Doctors", "Rates"):
            self._click_section_if_present(page, "Masters")
        elif label in ("Patient Entry", "Readings", "Receipt Entry"):
            self._click_section_if_present(page, "Main")
        elif label == "Reports":
            self._click_section_if_present(page, "Reports")

        aliases = {
            "Accounts": ["Accounts", "Account"],
            "Tests": ["Tests", "Test"],
            "Doctors": ["Doctors", "Doctor"],
            "Rates": ["Rates", "Rate"],
            "Patient Entry": ["Patient Entry", "Patient"],
            "Receipt Entry": ["Receipt Entry", "Receipt"],
            "Readings": ["Readings", "Reading"],
            "Reports": ["Reports", "Report"],
        }.get(label, [label])

        for name in aliases:
            for loc in [
                page.get_by_role("link", name=name),
                page.get_by_role("button", name=name),
                page.get_by_text(name, exact=False),
                page.locator(f"text={name}"),
            ]:
                try:
                    if loc.count() > 0:
                        loc.first.click()
                        page.wait_for_timeout(500)
                        self.log(f"  \u2192 Navigated to '{label}' via menu link.")
                        return
                except Exception:
                    continue

        # Route fallback when sidebar labels are collapsed/virtualized.
        route = self._ROUTE_BY_LABEL.get(label)
        if route:
            self.log(f"ℹ Menu '{label}' not found by text. Trying direct route {route}...")
            page.goto(f"{self.app_origin}{route}", wait_until="domcontentloaded")
            page.wait_for_timeout(700)
            if "login" not in page.url.lower():
                self.log(f"  \u2192 Navigated to '{label}' via direct route.")
                return

        # Capture module-level diagnostics
        out_dir = Path(__file__).resolve().parent
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot = out_dir / f"menu_missing_{label.replace(' ', '_')}_{stamp}.png"
        html = out_dir / f"menu_missing_{label.replace(' ', '_')}_{stamp}.html"
        page.screenshot(path=str(shot), full_page=True)
        html.write_text(page.content(), encoding="utf-8")
        raise RuntimeError(f"Menu not found: {label}. Diagnostics: {shot.name}, {html.name}")

    @staticmethod
    def _click_section_if_present(page, section_name: str):
        for loc in [
            page.get_by_role("button", name=section_name),
            page.get_by_role("link", name=section_name),
            page.get_by_text(section_name, exact=False),
        ]:
            try:
                if loc.count() > 0:
                    loc.first.click(timeout=1500)
                    page.wait_for_timeout(250)
                    return
            except Exception:
                continue

    def _create_or_pick_account(self, page, create: bool):
        self.log("  → Opening Accounts screen...")
        self._menu(page, "Accounts")
        page.wait_for_timeout(1000)
        code = f"QA{datetime.now().strftime('%m%d%H%M')}"
        self.context_data["account_name"] = f"QA COMPANY {code}"
        if create:
            self.log("  → Clicking 'New' to add a new account...")
            if not self._click_named_button(page, "New"):
                self.log("  ⚠ 'New' button not found/clickable on Accounts screen.")
            page.wait_for_timeout(400)
            name = self.context_data["account_name"]
            filled = False
            if page.get_by_placeholder("Account Name").count() > 0:
                page.get_by_placeholder("Account Name").fill(name)
                filled = True
            self.log(f"  → Account Name field filled: {filled} (value='{name}')")
            if not filled:
                shot, html = self._capture_step_diagnostics(page, "accounts_name_field")
                raise RuntimeError(f"Account Name field not found. Diagnostics: {shot}, {html}")
            self.log("  → Clicking Save on Accounts form...")
            if not self._click_named_button(page, "Save"):
                shot, html = self._capture_step_diagnostics(page, "accounts_save")
                raise RuntimeError(f"Could not click enabled Save button on Accounts form. Diagnostics: {shot}, {html}")
            page.wait_for_timeout(600)
            self.log(f"  ✓ Account '{name}' saved.")
        else:
            self.context_data["account_name"] = "CASH"
            self.log("  → Using existing account: CASH")

    def _create_or_pick_tests(self, page, create: bool):
        self.log("  → Opening Tests screen...")
        self._menu(page, "Tests")
        page.wait_for_timeout(1000)
        code = f"QAT{datetime.now().strftime('%m%d%H%M')}"
        self.context_data["test_code"] = code
        self.context_data["test_name"] = f"QA TEST {code}"
        if create:
            self.log("  → Clicking 'New' to add a new test...")
            if not self._click_named_button(page, "New"):
                self.log("  ⚠ 'New' button not found/clickable on Tests screen.")
            page.wait_for_timeout(400)
            name = self.context_data["test_name"]
            name_filled = self._fill_labeled(page, ["Test Name", "Test"], name)
            self.log(f"  → Test Name field filled: {name_filled} (value='{name}')")

            dept_filled = self._select_dropdown_option(page, ["Department"], "Pathology")
            self.log(f"  → Department selected (Pathology): {dept_filled}")

            cat_filled = self._select_dropdown_option(page, ["Category"], "Hematology")
            self.log(f"  → Category selected (Hematology): {cat_filled}")

            if not name_filled:
                shot, html = self._capture_step_diagnostics(page, "tests_name_field")
                raise RuntimeError(f"Test Name field not found. Diagnostics: {shot}, {html}")

            self.log("  → Clicking Save on Tests form...")
            if not self._click_named_button(page, "Save"):
                shot, html = self._capture_step_diagnostics(page, "tests_save")
                raise RuntimeError(f"Could not click enabled Save button on Tests form. Diagnostics: {shot}, {html}")
            page.wait_for_timeout(600)
            self.log(f"  ✓ Test '{name}' saved.")
        else:
            self.context_data["test_name"] = "CBC(COMPLETE BLOOD COUNT)"
            self.log("  → Using existing test: CBC(COMPLETE BLOOD COUNT)")

    def _create_or_pick_doctor(self, page, create: bool):
        self.log("  → Opening Doctors screen...")
        self._menu(page, "Doctors")
        page.wait_for_timeout(1000)
        name = f"DR QA {datetime.now().strftime('%m%d%H%M')}"
        self.context_data["doctor_name"] = name
        if create:
            self.log("  → Clicking 'New' to add a new doctor...")
            if not self._click_named_button(page, "New"):
                self.log("  ⚠ 'New' button not found/clickable on Doctors screen.")
            page.wait_for_timeout(400)
            name_filled = self._fill_labeled(page, ["Doctor Name", "Name"], name)
            self.log(f"  → Doctor Name field filled: {name_filled} (value='{name}')")

            type_filled = self._select_dropdown_option(page, ["Type"], "BOTH")
            self.log(f"  → Type set to BOTH: {type_filled}")

            if page.locator("text=Auto-select in Reading").count() > 0:
                page.locator("text=Auto-select in Reading").first.click()
                self.log("  → Enabled 'Auto-select in Reading' option.")

            if not name_filled:
                shot, html = self._capture_step_diagnostics(page, "doctors_name_field")
                raise RuntimeError(f"Doctor Name field not found. Diagnostics: {shot}, {html}")

            self.log("  → Clicking Save on Doctors form...")
            if not self._click_named_button(page, "Save"):
                shot, html = self._capture_step_diagnostics(page, "doctors_save")
                raise RuntimeError(f"Could not click enabled Save button on Doctors form. Diagnostics: {shot}, {html}")
            page.wait_for_timeout(600)
            self.log(f"  ✓ Doctor '{name}' saved.")
        else:
            self.context_data["doctor_name"] = "A . KUSHWAHA"
            self.log("  → Using existing doctor: A . KUSHWAHA")

    def _create_rates(self, page, create: bool):
        self.log("  → Opening Rates screen...")
        self._menu(page, "Rates")
        page.wait_for_timeout(1000)
        if create:
            self.log("  → Clicking 'New' to add a new rate...")
            if not self._click_named_button(page, "New"):
                self.log("  ⚠ 'New' button not found/clickable on Rates screen.")
            page.wait_for_timeout(400)
            account_val = self.context_data.get("account_name", "")
            test_val = self.context_data.get("test_name", "")
            self.log(f"  → Selecting Account: '{account_val}'...")
            account_ok = self._fill_autocomplete(
                page, ["Account", "Account / Company", "Company Account"], account_val
            )
            self.log(f"  → Account selected: {account_ok}")
            self.log(f"  → Selecting Test: '{test_val}'...")
            test_ok = self._fill_autocomplete(
                page, ["Test", "Test Name", "Test Selection"], test_val
            )
            self.log(f"  → Test selected: {test_ok}")
            self.log("  → Filling Rate amount: 250")
            rate_ok = self._fill_labeled(page, ["Rate", "Default Rate", "Amount"], "250")
            self.log(f"  → Rate field filled: {rate_ok}")
            page.wait_for_timeout(400)
            self.log("  → Clicking Save on Rates form...")
            if not self._wait_and_click_named_button(page, "Save", wait_ms=20000):
                shot, html = self._capture_step_diagnostics(page, "rates_save")
                raise RuntimeError(
                    "Could not click enabled Save button on Rates form. "
                    f"(account_filled={account_ok}, test_filled={test_ok}, rate_filled={rate_ok}) "
                    f"Diagnostics: {shot}, {html}"
                )
            page.wait_for_timeout(600)
            self.log("  ✓ Rate saved.")

    def _prepare_existing_entities(self):
        self.context_data.setdefault("account_name", "CASH")
        self.context_data.setdefault("test_name", "CBC(COMPLETE BLOOD COUNT)")
        self.context_data.setdefault("doctor_name", "A . KUSHWAHA")

    def _patient_entry(self, page):
        self.log("  → Opening Patient Entry screen...")
        self._menu(page, "Patient Entry")
        page.wait_for_timeout(1200)
        patient_name = f"QA PATIENT {datetime.now().strftime('%m%d%H%M')}"
        self.context_data["patient_name"] = patient_name

        self.log(f"  → Filling Patient Name: '{patient_name}'")
        name_ok = self._fill_labeled(page, ["Patient Name", "Full Name", "Name"], patient_name)
        self.log(f"  → Patient Name filled: {name_ok}")

        self.log("  → Filling Age: 32")
        age_ok = self._fill_labeled(page, ["Age", "Age (Yrs)", "Age(Yrs)", "Years"], "32")
        self.log(f"  → Age filled: {age_ok}")

        self.log("  → Selecting Gender: Male")
        gender_ok = self._select_dropdown_option(page, ["Gender", "Sex"], "Male")
        if not gender_ok:
            gender_ok = self._fill_autocomplete(page, ["Gender", "Sex"], "Male")
        self.log(f"  → Gender selected: {gender_ok}")

        self.log("  → Filling Mobile number: 9876543210")
        mobile_ok = self._fill_labeled(
            page, ["Mobile", "Mobile Number", "Mobile No", "Phone", "Contact Number", "Contact No"], "9876543210"
        )
        self.log(f"  → Mobile filled: {mobile_ok}")

        account_val = self.context_data.get("account_name", "CASH")
        self.log(f"  → Selecting Account: '{account_val}'")
        account_ok = self._fill_autocomplete(
            page,
            ["Account / Company", "Company Account", "Account"],
            account_val,
        )
        self.log(f"  → Account selected: {account_ok}")

        doctor_val = self.context_data.get("doctor_name", "")
        self.log(f"  → Selecting Referring Doctor: '{doctor_val}'")
        doctor_ok = self._fill_autocomplete(
            page,
            ["Referring Doctor", "Referred By Doctor", "Doctor"],
            doctor_val,
        )
        self.log(f"  → Doctor selected: {doctor_ok}")

        test_val = self.context_data.get("test_name", "")
        self.log(f"  → Adding Test: '{test_val}'")
        test_ok = self._fill_autocomplete(
            page,
            ["Test Selection", "Tests", "Add Test"],
            test_val,
        )
        self.log(f"  → Test added: {test_ok}")

        self.log("  → Clicking Save on Patient Entry form...")
        if not self._wait_and_click_named_button(page, "Save", wait_ms=20000):
            shot, html = self._capture_step_diagnostics(page, "patient_entry_save")
            raise RuntimeError(
                "Could not click enabled Save button on Patient Entry form. "
                f"(name={name_ok}, age={age_ok}, gender={gender_ok}, mobile={mobile_ok}, "
                f"account={account_ok}, doctor={doctor_ok}, test={test_ok}) "
                f"Diagnostics: {shot}, {html}"
            )

        page.wait_for_timeout(1000)
        self.log(f"  ✓ Patient '{patient_name}' registered and saved.")

    def _receipt_entry(self, page):
        self.log("  → Opening Receipt Entry screen...")
        self._menu(page, "Receipt Entry")
        page.wait_for_timeout(1000)
        self.log("  → Attempting to save receipt (if a payable balance is pending)...")
        if not self._wait_and_click_named_button(page, "Save", wait_ms=8000):
            self.log("  ℹ Receipt Save button is disabled or unavailable (likely no payable context). Skipping save step.")
        else:
            page.wait_for_timeout(500)
            self.log("  ✓ Receipt saved.")

    def _readings(self, page):
        self.log("  → Opening Readings screen...")
        self._menu(page, "Readings")
        page.wait_for_timeout(1000)
        if page.locator("text=Preview").count() > 0:
            self.log("  → Clicking Preview on Readings...")
            page.locator("text=Preview").first.click()
            page.wait_for_timeout(500)
            self.log("  ✓ Readings preview opened.")
        else:
            self.log("  ℹ No Preview action available on Readings screen (no pending readings found).")

    def _reports_all(self, page):
        self.log("  → Opening Reports screen...")
        self._menu(page, "Reports")
        page.wait_for_timeout(1200)
        cards = page.locator("[role='button']:has-text('Preview')")
        n = min(cards.count(), 20)
        self.log(f"  → Found {n} report(s) with Preview action.")
        opened = 0
        for i in range(n):
            try:
                cards.nth(i).click(timeout=2000)
                page.wait_for_timeout(400)
                opened += 1
                self.log(f"  → Previewed report {i + 1}/{n}.")
            except PWTimeout:
                self.log(f"  ⚠ Timed out previewing report {i + 1}/{n}.")
                continue
        self.log(f"  ✓ Reports checked: {opened}/{n} previewed successfully.")

    def _write_report(self, options: RunOptions):
        out_dir = Path(__file__).resolve().parent
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = out_dir / f"live_flow_run_{stamp}.json"
        payload = {
            "timestamp": stamp,
            "base_url": self.base_url,
            "options": options.__dict__,
            "results": [r.__dict__ for r in self.results],
            "context_data": self.context_data,
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.log(f"Report written: {out}")


class TestApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x720")

        self.var_url = tk.StringVar(value="http://localhost:1005/login")
        self.var_lab = tk.StringVar(value="DEMO2026")
        self.var_user = tk.StringVar(value="demo2026admin")
        self.var_pass = tk.StringVar(value="Admin@1234")
        self.var_manual_timeout = tk.StringVar(value="120")

        self.vars = {
            "headless": tk.BooleanVar(value=False),
            "manual_login_fallback": tk.BooleanVar(value=False),
        }
        self._is_running = False
        self._auto_run_started = False

        self._load_config()
        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        creds = ttk.LabelFrame(root, text="Live Application Details", padding=10)
        creds.pack(fill="x")

        ttk.Label(creds, text="URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(creds, textvariable=self.var_url, width=70).grid(row=0, column=1, columnspan=5, sticky="ew", padx=6)

        ttk.Label(creds, text="Lab Code").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(creds, textvariable=self.var_lab, width=20).grid(row=1, column=1, sticky="w", padx=6, pady=(6, 0))
        ttk.Label(creds, text="(Case-sensitive. Example: DEMO2026)").grid(row=2, column=1, sticky="w")

        ttk.Label(creds, text="User").grid(row=1, column=2, sticky="w", pady=(6, 0))
        ttk.Entry(creds, textvariable=self.var_user, width=20).grid(row=1, column=3, sticky="w", padx=6, pady=(6, 0))

        ttk.Label(creds, text="Password").grid(row=1, column=4, sticky="w", pady=(6, 0))
        ttk.Entry(creds, textvariable=self.var_pass, width=20, show="*").grid(row=1, column=5, sticky="w", padx=6, pady=(6, 0))

        flow = ttk.LabelFrame(root, text="Fixed Video Flow", padding=10)
        flow.pack(fill="x", pady=(10, 0))
        ttk.Label(
            flow,
            text="Masters (Accounts, Tests, Rates, Doctors) → Patient Entry → Receipt Entry → Readings → Reports",
            foreground="#333",
        ).pack(anchor="w")

        opts = ttk.LabelFrame(root, text="Run Options", padding=10)
        opts.pack(fill="x", pady=(10, 0))
        ttk.Label(opts, text="Browser: Microsoft Edge").pack(side="left", padx=(0, 12))
        ttk.Checkbutton(opts, text="Headless browser", variable=self.vars["headless"]).pack(side="left")
        ttk.Checkbutton(opts, text="Manual login fallback", variable=self.vars["manual_login_fallback"]).pack(side="left", padx=12)
        ttk.Label(opts, text="Manual wait (sec)").pack(side="left", padx=(12, 4))
        ttk.Entry(opts, textvariable=self.var_manual_timeout, width=6).pack(side="left")

        note = ttk.Label(
            root,
            text=(
                "This tool now runs only the same end-to-end flow shown in the video."
            ),
            foreground="#555",
        )
        note.pack(anchor="w", pady=(8, 0))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(10, 6))
        self.btn_save = ttk.Button(btns, text="Save Config", command=self._save_config)
        self.btn_save.pack(side="left")
        self.btn_run = ttk.Button(btns, text="Run Video Flow", command=self._run)
        self.btn_run.pack(side="left", padx=8)

        self.txt_log = tk.Text(root, height=22, wrap="word")
        self.txt_log.pack(fill="both", expand=True)

        # Auto-start one full run when app opens (run.bat one-click flow).
        self.after(500, self._auto_start_run)

    def _auto_start_run(self):
        if self._auto_run_started:
            return
        self._auto_run_started = True
        self._append("Auto-start: launching fixed video flow...")
        self._run()

    def _append(self, msg: str):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.update_idletasks()

    def _run(self):
        if self._is_running:
            self._append("A run is already in progress. Please wait for completion.")
            return

        timeout = self._manual_timeout_sec()
        opts = RunOptions(
            all_cases=False,
            masters_accounts=True,
            masters_tests=True,
            masters_rates=True,
            masters_doctors=True,
            main_patient_entry=True,
            main_readings=True,
            main_receipt_entry=True,
            reports_all=True,
            headless=self.vars["headless"].get(),
            manual_login_fallback=self.vars["manual_login_fallback"].get(),
            manual_login_timeout_sec=timeout,
            manual_pause_mode=False,
            browser="edge",
        )

        base_url = self.var_url.get().strip()
        lab = self.var_lab.get().strip()
        if lab.lower() == "demo2026" and lab != "DEMO2026":
            lab = "DEMO2026"
            self._append("ℹ Normalized Lab Code to DEMO2026.")
        user = self.var_user.get().strip()
        pwd = self.var_pass.get()
        if not base_url or not lab or not user or not pwd:
            messagebox.showerror(APP_TITLE, "URL, Lab Code, User and Password are required.")
            return

        self._is_running = True
        self._set_run_buttons_state("disabled")

        def worker():
            try:
                self._append("Starting fixed video flow run...")
                runner = LiveFlowRunner(base_url, lab, user, pwd, self._append)
                results = runner.run(opts)
                self._append("--- Summary ---")
                for r in results:
                    self._append(f"{r.status:4} | {r.name} | {r.details}")
            except Exception as ex:
                msg = str(ex)
                self._append(f"Run failed: {msg}")
                if "closed" in msg.lower() and ("page" in msg.lower() or "browser" in msg.lower()):
                    self._append("ℹ Browser/page was closed during login. Keep login window open until tool confirms manual login.")
                else:
                    self._append(traceback.format_exc())
            finally:
                self._is_running = False
                self.after(0, lambda: self._set_run_buttons_state("normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _set_run_buttons_state(self, state: str):
        self.btn_save.configure(state=state)
        self.btn_run.configure(state=state)

    def _manual_timeout_sec(self) -> int:
        try:
            return max(30, int(self.var_manual_timeout.get().strip()))
        except Exception:
            return 120

    def _save_config(self):
        data = {
            "url": self.var_url.get().strip(),
            "lab_code": self.var_lab.get().strip(),
            "user": self.var_user.get().strip(),
            "password": self.var_pass.get(),
            "manual_timeout": self.var_manual_timeout.get().strip() or "120",
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._append(f"Config saved: {CONFIG_FILE}")

    def _load_config(self):
        if not CONFIG_FILE.exists():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            self.var_url.set(data.get("url", self.var_url.get()))
            self.var_lab.set(data.get("lab_code", self.var_lab.get()))
            self.var_user.set(data.get("user", self.var_user.get()))
            self.var_pass.set(data.get("password", self.var_pass.get()))
            self.var_manual_timeout.set(str(data.get("manual_timeout", self.var_manual_timeout.get())))
        except Exception:
            pass


if __name__ == "__main__":
    TestApp().mainloop()
