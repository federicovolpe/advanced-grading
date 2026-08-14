"""
Utilita' condivise per gli script di grading "custom" (esercizi DO180 sprovvisti
di un `lab grade` ufficiale). Il formato di stampa (PASS/FAIL <titolo> seguito
da dettagli indentati di 8 spazi) e' compatibile con il parser di
~/.local/bin/lab_grade_monitor.py, cosi' i semafori funzionano anche qui.
"""

import json
import subprocess


class GradingStep:
    """Riproduce grossolanamente labs.ui.GradingStep usato nei grading
    ufficiali Red Hat Training (vedi do180/reliability-review.py): un check
    e' FAIL se viene chiamato add_error()/fail() al suo interno, altrimenti
    e' PASS."""

    def __init__(self, title):
        self.title = title
        self.errors = []
        self.failed = False

    def add_error(self, message):
        self.errors.append(message)

    def fail(self, message=None):
        self.failed = True
        if message:
            self.errors.append(message)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        status = "FAIL" if (self.failed or self.errors) else "PASS"
        print(f"{status} {self.title}")
        for e in self.errors:
            print(f"        - {e}")
        return False


def oc_get_json(*args):
    """Esegue `oc get <args> -o json` e ritorna il dict, o None se la
    risorsa non esiste o il comando fallisce."""
    result = subprocess.run(
        ["oc", "get", *args, "-o", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def project_exists(name):
    result = subprocess.run(["oc", "get", "project", name], capture_output=True)
    return result.returncode == 0
