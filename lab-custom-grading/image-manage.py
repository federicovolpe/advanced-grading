#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "image-manage" (sezione PDF
18.8 "Manage Image Mode-based Systems", pag. 481-486), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida.

L'esercizio fa un ciclo completo: modifica /var/www/html/index.html
direttamente su serverc (passo 1.3, stato locale persistente non toccato
da bootc), poi aggiorna l'immagine bootc con mod_ssl/vim-enhanced (passi
4-7), e infine fa un ROLLBACK esplicito all'immagine precedente (passi
10-12): lo stato finale atteso NON ha piu' mod_ssl/vim-enhanced installati
e non risponde piu' su HTTPS (443), ma /var/www/html/index.html conserva
la modifica locale del passo 1.3 (persistente attraverso l'intero ciclo di
update+rollback, essendo /var stato macchina-locale non gestito da bootc).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

SERVERC = "serverc"
_EXTRA_LINE = "Local content edited on serverc."


def main():
    print("🔧 Grading personalizzato per 'image-manage'")

    reachable = True
    with GradingStep(f"{SERVERC} e' raggiungibile via SSH") as step:
        result = run("true", host=SERVERC)
        if result.returncode != 0:
            reachable = False
            step.fail(f"{SERVERC} non raggiungibile")

    if not reachable:
        return

    with GradingStep(f"/var/www/html/index.html su {SERVERC} conserva la modifica locale del passo 1.3") as step:
        result = run("cat /var/www/html/index.html", host=SERVERC, sudo=True)
        if _EXTRA_LINE not in result.stdout:
            step.add_error(f"Riga attesa '{_EXTRA_LINE}' non trovata in index.html")

    with GradingStep("Il rollback bootc e' stato eseguito (bootc status mostra un rollback)") as step:
        result = run("bootc status", host=SERVERC, sudo=True)
        if "Rollback image:" not in result.stdout:
            step.add_error("Nessuna 'Rollback image:' nell'output di bootc status: il ciclo upgrade+rollback non risulta completato")

    with GradingStep("mod_ssl e vim-enhanced non sono installati (rollback completato, passo 12.2)") as step:
        result = run("rpm -q mod_ssl vim-enhanced", host=SERVERC, sudo=True)
        if result.returncode == 0:
            step.add_error(f"mod_ssl/vim-enhanced risultano ancora installati: {result.stdout.strip()}")

    with GradingStep("Il webserver non risponde piu' su HTTPS/443 (immagine con mod_ssl non piu' attiva)") as step:
        result = run("curl -sk --max-time 5 https://serverc.lab.example.com")
        if result.returncode == 0:
            step.add_error("HTTPS ancora raggiungibile: il rollback non risulta effettivo")


if __name__ == "__main__":
    main()
