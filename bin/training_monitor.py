#!/usr/bin/env python3
"""
Finestra di training "libero" DO180: mostra un esercizio alla volta (nome
progetto, testo del compito, semafori di grading con polling automatico) e
lascia avanzare al successivo con un pulsante, in stile lab_grade_monitor.py
ma per un curriculum indipendente dal tool ufficiale `lab` (vedi
training/README.md in questo repo).

Uso:
    ./training_monitor.py [--interval SECONDI] [--exercises-dir DIR] [--list] [--goto N]

Ogni file in --exercises-dir (default ~/.local/share/training/exercises,
ordinato per nome — da cui il prefisso "cNN-" nei nomi file) e' un modulo
Python indipendente che espone CHAPTER/TITLE/PROJECT/TASK e le funzioni
setup()/grade() (vedi training/_training_common.py:run_cli). Il monitor
esegue ciascuno come `python3 <file>.py setup|grade` — un processo per
run, cosi' un esercizio non puo' corrompere lo stato Python di un altro.
"""

import argparse
import json
import os
import queue
import re
import subprocess
import threading
import time
# tkinter e' importato solo dentro main(), non qui: --list deve funzionare
# anche su una macchina/sessione senza display grafico o senza il pacchetto
# python3-tkinter installato (vedi README, stesso vincolo di
# lab_grade_monitor.py).

DEFAULT_EXERCISES_DIR = os.path.expanduser("~/.local/share/training/exercises")
PROGRESS_FILE = os.path.expanduser("~/.local/share/training/progress.json")

CHECK_RE = re.compile(r"^(PASS|FAIL)\s+(.+?)\s*$")
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DETAIL_MIN_INDENT = 5


def strip_ansi(text):
    return ANSI_RE.sub("", text)


def parse_grade_output(text):
    """Stesso formato PASS/FAIL usato da lab_grade_monitor.py per il
    fallback su grading custom: qui e' l'UNICA fonte (niente JSONL, questi
    esercizi non passano dal pacchetto ufficiale 'labs')."""
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
            continue
        current["details"].append(content.lstrip("- ").strip())
    if current:
        checks.append(current)
    return checks


def load_exercises(exercises_dir):
    files = sorted(
        f for f in os.listdir(exercises_dir)
        if f.endswith(".py") and not f.startswith("_")
    )
    exercises = []
    for fname in files:
        path = os.path.join(exercises_dir, fname)
        # Ogni esercizio fa 'sys.path.insert(..., os.path.dirname(__file__))'
        # in testa al file: __file__ deve esistere nel namespace di exec()
        # (che di suo non lo definisce) o quella riga si rompe subito.
        ns = {"__file__": path}
        with open(path) as fh:
            source = fh.read()
        try:
            # Eseguiamo solo per leggere le costanti di modulo (CHAPTER/
            # TITLE/PROJECT/TASK): setup()/grade() sono definite ma non
            # vengono chiamate qui, quindi non toccano il cluster.
            exec(compile(source, path, "exec"), ns)
        except Exception as exc:
            print(f"Attenzione: non riesco a caricare {fname}: {exc}")
            continue
        exercises.append({
            "file": path,
            "slug": fname[:-3],
            "chapter": ns.get("CHAPTER", "?"),
            "title": ns.get("TITLE", fname),
            "project": ns.get("PROJECT", "?"),
            "task": ns.get("TASK", ""),
        })
    return exercises


def load_progress():
    try:
        with open(PROGRESS_FILE) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"index": 0}


def save_progress(progress):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w") as fh:
        json.dump(progress, fh)


class TrainingMonitor:
    PASS_COLOR = "#2ecc71"
    FAIL_COLOR = "#e74c3c"
    BUSY_COLOR = "#7f8c8d"

    def __init__(self, root, exercises, start_index, interval):
        self.root = root
        self.exercises = exercises
        self.index = max(0, min(start_index, len(exercises) - 1))
        self.interval = interval
        self.checks = []
        self.running = True
        self.busy = False
        self.result_queue = queue.Queue()

        root.title("Training DO180")
        root.attributes("-topmost", True)
        root.geometry("620x520")
        root.configure(bg="#1e1e1e")

        top = tk.Frame(root, bg="#1e1e1e")
        top.pack(fill="x", padx=12, pady=(10, 4))
        self.progress_label = tk.Label(
            top, text="", bg="#1e1e1e", fg="#9aa0a6", font=("sans-serif", 9),
        )
        self.progress_label.pack(side="left")

        self.title_label = tk.Label(
            root, text="", bg="#1e1e1e", fg="#f0f0f0",
            font=("sans-serif", 13, "bold"), anchor="w", justify="left",
            wraplength=580,
        )
        self.title_label.pack(fill="x", padx=12, pady=(0, 6))

        self.task_text = scrolledtext.ScrolledText(
            root, height=10, bg="#111111", fg="#e0e0e0",
            font=("monospace", 10), wrap="word",
        )
        self.task_text.pack(fill="both", expand=False, padx=12, pady=(0, 8))
        self.task_text.config(state="disabled")

        self.summary_label = tk.Label(
            root, text="", bg="#1e1e1e", fg="#f0f0f0", font=("sans-serif", 10, "bold"),
        )
        self.summary_label.pack(fill="x", padx=12)

        self.grid_frame = tk.Frame(root, bg="#1e1e1e")
        self.grid_frame.pack(fill="both", expand=True, padx=12, pady=6)

        self.status_label = tk.Label(
            root, text="", bg="#1e1e1e", fg="#9aa0a6", font=("sans-serif", 9),
        )
        self.status_label.pack(fill="x", padx=12, pady=(0, 4))

        buttons = tk.Frame(root, bg="#1e1e1e")
        buttons.pack(fill="x", padx=12, pady=(0, 10))

        tk.Button(buttons, text="⟲ Ricomincia esercizio", command=self.restart_exercise).pack(side="left")
        tk.Button(buttons, text="Ricontrolla ora", command=self.grade_async).pack(side="left", padx=6)
        self.next_button = tk.Button(
            buttons, text="Esercizio successivo →", command=self.next_exercise,
        )
        self.next_button.pack(side="right")
        # "SystemButtonFace" (colore di default dei bottoni su Windows) non
        # e' un nome colore valido per Tk su X11/Wayland: leggiamo il grigio
        # di default vero di QUESTA piattaforma per poterlo ripristinare
        # dopo averlo tinto di verde a esercizio completato.
        self.DEFAULT_BUTTON_BG = self.next_button.cget("bg")
        tk.Button(buttons, text="Salta →", command=self.next_exercise).pack(side="right", padx=6)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self._poll_queue)
        self.enter_exercise(save=False)

    # --- gestione esercizio corrente -------------------------------------

    @property
    def current(self):
        return self.exercises[self.index]

    def enter_exercise(self, save=True):
        ex = self.current
        if save:
            save_progress({"index": self.index})
        self.checks = []
        self.progress_label.config(
            text=f"Esercizio {self.index + 1}/{len(self.exercises)} — {ex['chapter']}"
        )
        self.title_label.config(text=ex["title"])
        self.task_text.config(state="normal")
        self.task_text.delete("1.0", "end")
        self.task_text.insert("1.0", ex["task"])
        self.task_text.config(state="disabled")
        self.summary_label.config(text="")
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.set_busy(True, "Preparazione ambiente in corso…")
        threading.Thread(target=self._run_setup, daemon=True).start()

    def set_busy(self, busy, message=""):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.next_button.config(state=state)
        if message:
            self.status_label.config(text=message)

    def _run_setup(self):
        try:
            subprocess.run(
                ["python3", self.current["file"], "setup"],
                capture_output=True, text=True, timeout=180,
            )
            error = None
        except Exception as exc:
            error = str(exc)
        self.result_queue.put(("setup_done", error))

    # --- grading -----------------------------------------------------------

    def grade_async(self):
        if self.busy:
            return
        threading.Thread(target=self._run_grade, daemon=True).start()

    def _run_grade(self):
        try:
            result = subprocess.run(
                ["python3", self.current["file"], "grade"],
                capture_output=True, text=True, timeout=60,
            )
            checks = parse_grade_output(result.stdout + result.stderr)
            error = None
        except Exception as exc:
            checks = []
            error = str(exc)
        self.result_queue.put(("grade_done", checks, error))

    def _poll_queue(self):
        try:
            while True:
                item = self.result_queue.get_nowait()
                if item[0] == "setup_done":
                    self.set_busy(False)
                    self.grade_async()
                elif item[0] == "grade_done":
                    self._on_grade_done(item[1], item[2])
        except queue.Empty:
            pass
        if self.running:
            self.root.after(150, self._poll_queue)

    def _on_grade_done(self, checks, error):
        timestamp = time.strftime("%H:%M:%S")
        if error:
            self.status_label.config(text=f"Errore alle {timestamp}: {error}")
        else:
            self.checks = checks
            self.render()
            self.status_label.config(
                text=f"Ultimo controllo: {timestamp} — prossimo tra {self.interval}s"
            )
        if self.running and not self.busy:
            self.root.after(self.interval * 1000, self.grade_async)

    def render(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        total = len(self.checks)
        passed = sum(1 for c in self.checks if c["status"] == "PASS")
        all_pass = total > 0 and passed == total

        self.summary_label.config(
            text=("✅ Completato! " if all_pass else "") + f"{passed}/{total} PASS"
            if total else "Nessun check trovato nell'output"
        )
        self.next_button.config(
            bg=self.PASS_COLOR if all_pass else self.DEFAULT_BUTTON_BG,
        )

        for i, check in enumerate(self.checks):
            color = self.PASS_COLOR if check["status"] == "PASS" else self.FAIL_COLOR
            row = tk.Frame(self.grid_frame, bg="#1e1e1e")
            row.grid(row=i, column=0, sticky="w", pady=2)
            dot = tk.Canvas(row, width=18, height=18, bg="#1e1e1e", highlightthickness=0)
            dot.create_oval(2, 2, 16, 16, fill=color, outline="")
            dot.pack(side="left")
            label = tk.Label(
                row, text=check["title"], bg="#1e1e1e",
                fg="#f0f0f0" if check["status"] == "PASS" else "#ffb3b3",
                font=("sans-serif", 9), anchor="w", justify="left", wraplength=520,
            )
            label.pack(side="left", padx=6)
            if check["details"]:
                detail_text = "\n".join(f"- {d}" for d in check["details"])
                tk.Label(
                    self.grid_frame, text=detail_text, bg="#1e1e1e",
                    fg="#9aa0a6", font=("monospace", 8), anchor="w", justify="left",
                    wraplength=560,
                ).grid(row=i, column=1, sticky="w")

    # --- navigazione ---------------------------------------------------

    def restart_exercise(self):
        self.enter_exercise(save=False)

    def next_exercise(self):
        if self.index + 1 < len(self.exercises):
            self.index += 1
            self.enter_exercise()
        else:
            self.status_label.config(text="🎉 Hai completato tutti gli esercizi disponibili!")

    def on_close(self):
        self.running = False
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=int, default=8, help="Secondi tra un grading e il successivo (default: 8)")
    parser.add_argument("--exercises-dir", default=DEFAULT_EXERCISES_DIR)
    parser.add_argument("--goto", type=int, help="Indice (1-based) dell'esercizio da cui iniziare")
    parser.add_argument("--list", action="store_true", help="Elenca gli esercizi disponibili ed esce")
    args = parser.parse_args()

    exercises = load_exercises(args.exercises_dir)
    if not exercises:
        print(f"Nessun esercizio trovato in {args.exercises_dir}")
        return

    if args.list:
        progress = load_progress()
        for i, ex in enumerate(exercises):
            marker = "→" if i == progress.get("index", 0) else " "
            print(f"{marker} {i + 1:2d}. [{ex['chapter']}] {ex['title']}  ({ex['slug']})")
        return

    if args.goto:
        start_index = args.goto - 1
    else:
        start_index = load_progress().get("index", 0)

    global tk, scrolledtext
    import tkinter as tk
    from tkinter import scrolledtext

    root = tk.Tk()
    TrainingMonitor(root, exercises, start_index, args.interval)
    root.mainloop()


if __name__ == "__main__":
    main()
