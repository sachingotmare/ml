from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk

from mlab_live_flow_runner import MLabFlowRunner, RunOptions


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MLab Live Flow Tester")
        self.geometry("860x620")

        self.vars = {
            "all": tk.BooleanVar(value=False),
            "masters_accounts": tk.BooleanVar(value=False),
            "masters_tests": tk.BooleanVar(value=False),
            "masters_rates": tk.BooleanVar(value=False),
            "masters_doctors": tk.BooleanVar(value=False),
            "main_patient_entry": tk.BooleanVar(value=False),
            "main_readings": tk.BooleanVar(value=False),
            "main_receipt_entry": tk.BooleanVar(value=False),
            "reports_all": tk.BooleanVar(value=False),
            "headless": tk.BooleanVar(value=False),
            "manual_login_fallback": tk.BooleanVar(value=True),
        }
        self.manual_timeout = tk.StringVar(value="120")

        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Live URL: https://mlab.sgsoftech.in/login", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(frm, text="Lab: Demo2026 | User: demo2026admin", foreground="#555").pack(anchor="w", pady=(0, 10))

        ttk.Checkbutton(frm, text="All", variable=self.vars["all"], command=self._toggle_all).pack(anchor="w", pady=(0, 8))

        masters = ttk.LabelFrame(frm, text="Masters", padding=8)
        masters.pack(fill="x", pady=4)
        for k, t in [
            ("masters_accounts", "Accounts"),
            ("masters_tests", "Tests"),
            ("masters_rates", "Rates"),
            ("masters_doctors", "Doctors"),
        ]:
            ttk.Checkbutton(masters, text=t, variable=self.vars[k]).pack(side="left", padx=8)

        main = ttk.LabelFrame(frm, text="Main", padding=8)
        main.pack(fill="x", pady=4)
        for k, t in [
            ("main_patient_entry", "Patient Entry"),
            ("main_readings", "Readings"),
            ("main_receipt_entry", "Receipt Entry"),
        ]:
            ttk.Checkbutton(main, text=t, variable=self.vars[k]).pack(side="left", padx=8)

        reports = ttk.LabelFrame(frm, text="Reports", padding=8)
        reports.pack(fill="x", pady=4)
        ttk.Checkbutton(reports, text="All Reports", variable=self.vars["reports_all"]).pack(side="left", padx=8)

        run_opts = ttk.Frame(frm)
        run_opts.pack(fill="x", pady=(8, 8))
        ttk.Checkbutton(run_opts, text="Headless browser", variable=self.vars["headless"]).pack(side="left")
        ttk.Checkbutton(
            run_opts,
            text="Manual login fallback",
            variable=self.vars["manual_login_fallback"],
        ).pack(side="left", padx=(12, 0))
        ttk.Label(run_opts, text="Manual wait (sec):").pack(side="left", padx=(12, 4))
        ttk.Entry(run_opts, textvariable=self.manual_timeout, width=6).pack(side="left")

        ttk.Label(
            frm,
            text=(
                "Rule: If only Main modules are selected, runner uses existing Account/Test/Doctor\n"
                "and will not create new masters."
            ),
            foreground="#444",
        ).pack(anchor="w", pady=(0, 8))

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(0, 8))
        ttk.Button(btns, text="Run Selected", command=self._run).pack(side="left")
        ttk.Button(btns, text="Run + Manual Login Pause", command=self._run_with_manual_pause).pack(side="left", padx=(8, 0))

        self.log = tk.Text(frm, height=20, wrap="word")
        self.log.pack(fill="both", expand=True)

    def _toggle_all(self):
        v = self.vars["all"].get()
        for k in (
            "masters_accounts",
            "masters_tests",
            "masters_rates",
            "masters_doctors",
            "main_patient_entry",
            "main_readings",
            "main_receipt_entry",
            "reports_all",
        ):
            self.vars[k].set(v)

    def _append(self, msg: str):
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.update_idletasks()

    def _run(self):
        timeout = self._manual_timeout_sec()
        opts = RunOptions(
            all_cases=self.vars["all"].get(),
            masters_accounts=self.vars["masters_accounts"].get(),
            masters_tests=self.vars["masters_tests"].get(),
            masters_rates=self.vars["masters_rates"].get(),
            masters_doctors=self.vars["masters_doctors"].get(),
            main_patient_entry=self.vars["main_patient_entry"].get(),
            main_readings=self.vars["main_readings"].get(),
            main_receipt_entry=self.vars["main_receipt_entry"].get(),
            reports_all=self.vars["reports_all"].get(),
            headless=self.vars["headless"].get(),
            manual_login_fallback=self.vars["manual_login_fallback"].get(),
            manual_login_timeout_sec=timeout,
        )

        def worker():
            self._append("Starting run...")
            runner = MLabFlowRunner(self._append)
            results = runner.run(opts)
            self._append("--- Summary ---")
            for r in results:
                self._append(f"{r.status:4} | {r.name} | {r.details}")

        threading.Thread(target=worker, daemon=True).start()

    def _run_with_manual_pause(self):
        self.vars["manual_login_fallback"].set(True)
        if self.vars["headless"].get():
            self._append("Headless disabled for manual login pause run.")
            self.vars["headless"].set(False)
        self._run()

    def _manual_timeout_sec(self) -> int:
        try:
            return max(30, int(self.manual_timeout.get().strip()))
        except Exception:
            return 120


if __name__ == "__main__":
    App().mainloop()
