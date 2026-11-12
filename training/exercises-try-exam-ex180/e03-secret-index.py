"""
Try-exam EX180, 3 — secret dal file index.html "presente sulla macchina M".

Il file di partenza lo crea setup() in ~/try-exam-ex180/index.html. Il
secret si confronta con il contenuto che il file ha al momento del grading.

Scostamenti dal tema annotato: la "macchina M" e' la workstation; contenuto
del file, percorso, progetto, nome del secret e chiave (index.html, il nome
che `--from-file` usa di default) sono scelte NOSTRE.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, INDEX_HTML, GradingStep, oc, oc_get_json, reset_project,
    delete_project, check_project, write_index_html, read_index_html, secret_value, run_cli,
)

SLUG = "e03"
PROJECT = "ex180-e03"
TITLE = "3) Secret dal file index.html"
SECRET = "web-index"

TASK = f"""\
Sulla macchina (workstation) c'e' il file
    {INDEX_HTML}

Nel progetto {PROJECT} crea un secret di nome {SECRET} che
contenga quel file, con la chiave index.html.
"""

SOLUTION = f"""\
oc project {PROJECT}
oc create secret generic {SECRET} --from-file=index.html={INDEX_HTML}
oc get secret {SECRET} -o jsonpath='{{.data.index\\.html}}' | base64 -d
"""


def setup():
    write_index_html()
    reset_project(PROJECT)


def grade():
    check_project(PROJECT)
    secret = oc_get_json("secret", SECRET, "-n", PROJECT)
    with GradingStep(f"Il secret {SECRET} esiste") as step:
        if not secret:
            step.fail(f"Secret '{SECRET}' non trovato in {PROJECT}")

    with GradingStep("Ha la chiave index.html") as step:
        if not secret:
            step.fail("Secret non trovato")
        elif "index.html" not in (secret.get("data") or {}):
            step.fail(f"chiavi presenti: {sorted((secret.get('data') or {}))}")

    with GradingStep(f"Il contenuto e' quello del file {INDEX_HTML}") as step:
        got = secret_value(secret, "index.html")
        expected = read_index_html()
        if got is None:
            step.fail("chiave index.html assente")
        elif expected is None:
            step.fail(f"file {INDEX_HTML} non leggibile")
        elif got != expected:
            step.add_error("il contenuto del secret e' diverso da quello del file")


def cleanup():
    delete_project(PROJECT)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
