#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "scheduling-at" (sezione PDF
3.2 "Schedule a Future User Job", pag. 67-69), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera.

Stato finale atteso:
- ~/myjob.txt esiste e non e' vuoto (job "at now +2min", eseguito ormai da
  tempo qualunque sia il momento del grading, passo 2).
- Il job schedulato nella coda "g" (teatime) e' stato rimosso con `atrm`
  (passo 6): ~/tea.txt non deve esistere e non deve comparire in atq.
- Il job schedulato nella coda "b" (16:05, cookies.txt) resta verificabile
  in due modi alternativi a seconda di quando avviene il grading rispetto
  alle 16:05: o e' ancora in coda (atq mostra la coda "b"), oppure ha gia'
  girato e ~/cookies.txt esiste col messaggio atteso. Non fissiamo un
  singolo stato perche' il tempo trascorso dipende da quando lo studente
  ha svolto l'esercizio, non da un valore della guida.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, file_exists

HOST = "servera"


def atq_lines():
    result = run("atq", host=HOST)
    return [l for l in result.stdout.splitlines() if l.strip()]


def main():
    print(f"🔧 Grading personalizzato per 'scheduling-at' (host: {HOST})")

    with GradingStep("~/myjob.txt esiste e contiene l'output del job 'at' (passo 2)") as step:
        result = run("cat ~/myjob.txt", host=HOST)
        if result.returncode != 0 or not result.stdout.strip():
            step.fail("~/myjob.txt non trovato o vuoto")

    with GradingStep("Il job nella coda 'g' (teatime) e' stato rimosso con atrm (passo 6)") as step:
        lines = atq_lines()
        queue_g = [l for l in lines if len(l.split()) >= 2 and l.split()[-2] == "g"]
        if queue_g:
            step.add_error(f"Job ancora presente in coda 'g': {queue_g}")
        if file_exists("~/tea.txt", host=HOST):
            step.add_error("~/tea.txt esiste: il job rimosso non doveva mai essere eseguito")

    with GradingStep("Il job nella coda 'b' (cookies, 16:05) e' stato creato (passi 4-5)") as step:
        lines = atq_lines()
        queue_b = [l for l in lines if len(l.split()) >= 2 and l.split()[-2] == "b"]
        cookies_exists = file_exists("~/cookies.txt", host=HOST)
        if not queue_b and not cookies_exists:
            step.add_error(
                "Nessun job in coda 'b' ancora pendente e ~/cookies.txt non esiste: "
                "il job non risulta mai stato creato"
            )


if __name__ == "__main__":
    main()
