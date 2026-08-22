#!/usr/bin/env python3
"""
Pannello con semafori per il monitoraggio in tempo reale di `lab grade`.

Uso:
    ./lab_grade_monitor.py <nome-lab> [--interval SECONDI] [--host user@host]

Lancia periodicamente `lab grade <nome-lab>` (in locale o via ssh se --host
e' specificato) e mostra i check come semafori in una finestrella sempre in
primo piano. Passa il mouse su un semaforo per vedere titolo e dettagli del
check.

Fonte dei check, in ordine di preferenza:
1. ~/.grading/grade_results.jsonl — log strutturato scritto dal pacchetto
   ufficiale `labs` (rht-labs-cli) ad ogni `lab grade`, indipendentemente da
   come quella run renderizza l'output a schermo (testo "PASS"/"FAIL",
   simboli colorati "check-mark"/"cross-mark" con spinner, o altro ancora in
   futuro). E' la fonte piu' robusta: quando presente e non vuota, e' quella
   usata.
2. Fallback: regex sull'output testuale grezzo di 'lab grade' (stdout+stderr)
   — usato quando il JSONL manca (versione di 'labs' senza grading_log) o
   quando il check-list e' vuoto (es. grade() non implementato per l'esercizio
   -> lo script di grading custom, invocato dal wrapper bash, stampa comunque
   "PASS <titolo>"/"FAIL <titolo>" in quel formato testuale).
"""

import argparse
import json
import re
import shlex
import subprocess
import threading
import time
import tkinter as tk
from datetime import datetime

JSON_MARKER = "__LAB_GRADE_MONITOR_JSON_TAIL__"

CHECK_RE = re.compile(r"^(PASS|FAIL)\s+(.+?)\s*$")
# CSI generico (ECMA-48): ESC [ <param 0x30-0x3F>* <intermediate 0x20-0x2F>* <final 0x40-0x7E>
# Deve includere '?' (0x3F) altrimenti le sequenze "private mode" tipo
# ESC[?25l / ESC[?25h (show/hide cursor, usate dallo spinner di `lab grade`)
# non vengono rimosse e lasciano un residuo "\x1b[?25hFAIL" che rompe il match
# a inizio riga.
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
# Righe dello spinner di progresso (es. "   -    Verifying ...", "   \\    Verifying ...")
# indentate di poco (3 spazi) rispetto ai dettagli reali di un check (indentati
# di 8 spazi, "        - dettaglio"). Sotto questa soglia consideriamo la riga
# rumore di spinner e la scartiamo invece di trattarla come dettaglio.
DETAIL_MIN_INDENT = 5


def strip_ansi(text):
    return ANSI_RE.sub("", text)


def parse_lab_grade_output(text):
    """Ritorna una lista di dict: {status, title, details}."""
    checks = []
    current = None
    for raw_line in strip_ansi(text).splitlines():
        line = raw_line.rstrip()
        m = CHECK_RE.match(line)
        if m:
            if current:
                checks.append(current)
            current = {"status": m.group(1), "title": m.group(2), "details": []}
            continue
        if current is None:
            continue
        content = line.strip()
        if not content:
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent < DETAIL_MIN_INDENT:
            # riga di spinner/progresso residua, non un dettaglio del check
            continue
        current["details"].append(content.lstrip("- ").strip())
    if current:
        checks.append(current)
    return checks


def parse_grade_result_jsonl(line):
    """Converte l'ultima riga di grade_results.jsonl per questo lab in una
    lista di check {status, title, details}, o None se assente/vuota/non
    valida (in quel caso il chiamante ricade sul parsing testuale)."""
    if not line:
        return None
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    checks = record.get("checks") or []
    if not checks:
        return None
    return [
        {
            "status": "PASS" if c.get("result") in ("PASS", "SUCCESS") else "FAIL",
            "title": c.get("name", "(check senza nome)"),
            "details": list(c.get("secondary_messages") or []),
        }
        for c in checks
    ]


class Tooltip:
    """Tooltip semplice che segue il mouse su un widget."""

    def __init__(self, widget, text_fn):
        self.widget = widget
        self.text_fn = text_fn
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event):
        text = self.text_fn()
        if not text:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        label = tk.Label(
            self.tip,
            text=text,
            justify="left",
            background="#2b2b2b",
            foreground="#f0f0f0",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
            font=("monospace", 10),
            wraplength=420,
        )
        label.pack()

    def hide(self, event):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class LabGradeMonitor:
    PASS_COLOR = "#2ecc71"
    FAIL_COLOR = "#e74c3c"
    PENDING_COLOR = "#7f8c8d"

    def __init__(self, root, lab_name, interval, host=None):
        self.root = root
        self.lab_name = lab_name
        self.interval = interval
        self.host = host
        self.checks = []
        self.running = True
        self.last_run = None
        self.last_raw_output = ""

        root.title(f"lab grade — {lab_name}")
        root.attributes("-topmost", True)
        root.geometry("480x360")
        root.configure(bg="#1e1e1e")

        header = tk.Frame(root, bg="#1e1e1e")
        header.pack(fill="x", padx=10, pady=(10, 4))

        self.summary_label = tk.Label(
            header, text="In attesa del primo grading…",
            bg="#1e1e1e", fg="#f0f0f0", font=("sans-serif", 11, "bold"),
        )
        self.summary_label.pack(side="left")

        refresh_btn = tk.Button(header, text="Aggiorna ora", command=self.run_grade_async)
        refresh_btn.pack(side="right")

        self.grid_frame = tk.Frame(root, bg="#1e1e1e")
        self.grid_frame.pack(fill="both", expand=True, padx=10, pady=6)

        self.status_label = tk.Label(
            root, text="", bg="#1e1e1e", fg="#9aa0a6", font=("sans-serif", 9),
        )
        self.status_label.pack(fill="x", padx=10, pady=(0, 8))

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.run_grade_async()
        self.schedule_next()

    def schedule_next(self):
        self.root.after(self.interval * 1000, self.run_grade_async)

    def run_grade_async(self):
        threading.Thread(target=self._run_grade, daemon=True).start()

    def _run_grade(self):
        # Passiamo dalla shell (sourciando il file che definisce il wrapper
        # `lab()`) invece di invocare direttamente il binario `lab`: cosi'
        # il fallback sul grading custom (~/.local/share/lab-custom-grading/)
        # scatta anche da qui, non solo lanciando `lab grade` a mano.
        # Dopo 'lab grade', stampiamo un marcatore seguito dall'ultima riga di
        # grade_results.jsonl per questo lab (se esiste): e' il log
        # strutturato scritto dal pacchetto ufficiale 'labs', indipendente dal
        # formato con cui quella run ha renderizzato l'output a schermo.
        grep_pattern = shlex.quote(f'"lab_name": "{self.lab_name}"')
        shell_cmd = (
            "source ~/.bashrc.d/lab-grade-monitor.sh 2>/dev/null; "
            f"lab grade {shlex.quote(self.lab_name)}; "
            f"printf '\\n{JSON_MARKER}\\n'; "
            f"grep -F {grep_pattern} ~/.grading/grade_results.jsonl 2>/dev/null | tail -n1"
        )
        if self.host:
            cmd = ["ssh", self.host, shell_cmd]
        else:
            cmd = ["bash", "-c", shell_cmd]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            # Non scartare uno stream a favore dell'altro: a volte il banner
            # "Running: ..." finisce su stdout mentre i dettagli di un
            # fallimento anticipato (es. VM non ancora pronte appena dopo
            # 'lab start') finiscono su stderr, o viceversa.
            output = result.stdout + result.stderr
            grade_text, _, json_tail = output.partition(JSON_MARKER)
            json_line = json_tail.strip().splitlines()[-1] if json_tail.strip() else None
            checks = parse_grade_result_jsonl(json_line)
            if checks is None:
                checks = parse_lab_grade_output(grade_text)
            output = grade_text
            error = None
        except Exception as exc:
            output = ""
            checks = []
            error = str(exc)
        self.root.after(0, self._on_grade_done, checks, error, output)

    def _on_grade_done(self, checks, error, raw_output):
        self.last_run = datetime.now()
        self.last_raw_output = raw_output
        timestamp = self.last_run.strftime("%H:%M:%S")
        if error:
            self.status_label.config(
                text=f"Errore alle {timestamp}: {error}"
            )
        else:
            self.checks = checks
            self.render()
            self.status_label.config(
                text=f"Ultimo controllo: {timestamp} — prossimo tra {self.interval}s"
            )
        if self.running:
            self.schedule_next()

    def render(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        total = len(self.checks)
        passed = sum(1 for c in self.checks if c["status"] == "PASS")
        self.summary_label.config(
            text=f"{self.lab_name}: {passed}/{total} PASS"
            if total else "Nessun check trovato nell'output"
        )

        if not total:
            self._render_raw_debug()
            return

        cols = 8
        for i, check in enumerate(self.checks):
            color = self.PASS_COLOR if check["status"] == "PASS" else self.FAIL_COLOR
            dot = tk.Canvas(
                self.grid_frame, width=32, height=32,
                bg="#1e1e1e", highlightthickness=0,
            )
            dot.create_oval(4, 4, 28, 28, fill=color, outline="")
            dot.grid(row=i // cols, column=i % cols, padx=4, pady=4)

            def tip_text(c=check):
                lines = [c["title"]]
                lines += [f"- {d}" for d in c["details"]]
                return "\n".join(lines)

            Tooltip(dot, tip_text)

    def _render_raw_debug(self):
        """Mostra l'output grezzo quando il parser non trova nessun check,
        cosi' si vede subito il formato reale invece di uno schermo vuoto."""
        tk.Label(
            self.grid_frame,
            text="Output grezzo di 'lab grade' (debug — nessun check riconosciuto):",
            bg="#1e1e1e", fg="#9aa0a6", font=("sans-serif", 9), anchor="w",
        ).pack(fill="x")

        text_box = tk.Text(
            self.grid_frame, bg="#111111", fg="#e0e0e0",
            font=("monospace", 9), wrap="word",
        )
        text_box.insert("1.0", self.last_raw_output or "(output vuoto)")
        text_box.config(state="disabled")
        text_box.pack(fill="both", expand=True)

    def on_close(self):
        self.running = False
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lab_name", help="Nome del laboratorio (come passato a 'lab grade')")
    parser.add_argument("--interval", type=int, default=30, help="Secondi tra un grading e il successivo (default: 30)")
    parser.add_argument("--host", help="Host remoto (es. student@workstation) su cui lanciare 'lab grade' via ssh")
    args = parser.parse_args()

    root = tk.Tk()
    LabGradeMonitor(root, args.lab_name, args.interval, args.host)
    root.mainloop()


if __name__ == "__main__":
    main()
