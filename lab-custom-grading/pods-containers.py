#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato pods-containers (DO180), sprovvisto
di `lab grade` ufficiale (la classe PodsContainers nel pacchetto do180
implementa solo start()/finish(), non grade() - vedi do180/pods-containers.py).

IMPORTANTE - questo e' un check "sul momento", non a posteriori: quasi tutti
i pod creati durante l'esercizio (ubi9-user x2, ubi9-date) vengono
esplicitamente cancellati dallo studente passo per passo (guida DO180,
Capitolo 3.2, pag. 159-166). L'UNICO stato che sopravvive fino alla fine
dell'esercizio e' il pod `ubi9-command`: il punto 8.2 della guida chiede
esplicitamente di confermare "the pod is still running" prima di lanciare
`lab finish pods-containers` (che cancella l'intero progetto). Quindi:
- questo script da' un risultato SOLO se eseguito PRIMA di `lab finish`,
  mentre il pod ubi9-command e' ancora attivo (esattamente il caso d'uso
  del monitor grafico, che ripete il check ogni 30s);
- dopo `lab finish` il progetto non esiste piu' e tutto torna FAIL, il che
  e' corretto (non c'e' piu' nulla da verificare, l'esercizio e' concluso).

Uso: pods-containers.py [nome-progetto]   (default: pods-containers)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "pods-containers"
EXPECTED_POD = "ubi9-command"
EXPECTED_IMAGE_SUBSTR = "ubi9/ubi"
# Pod che la guida fa cancellare esplicitamente durante l'esercizio (punti
# 2.2, 2.5, 3.4): se sono ancora presenti, lo studente non ha completato
# quei passi di pulizia.
EXPECTED_DELETED_PODS = ["ubi9-user", "ubi9-date"]


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(
                f"Progetto '{project}' non trovato: se hai gia' eseguito "
                "'lab finish', e' normale (l'esercizio e' concluso e non "
                "resta nulla da verificare)"
            )

    pod = oc_get_json("pod", EXPECTED_POD, "-n", project)

    with GradingStep(
        f"Il pod '{EXPECTED_POD}' e' in esecuzione (punto 8.2 della guida)"
    ) as step:
        if pod is None:
            step.fail(
                f"Pod '{EXPECTED_POD}' non trovato in '{project}': deve "
                "restare in esecuzione fino alla fine dell'esercizio, "
                "prima di 'lab finish' (questo check funziona solo mentre "
                "il pod e' ancora attivo)"
            )
        else:
            phase = pod.get("status", {}).get("phase")
            if phase != "Running":
                step.add_error(f"Il pod e' in fase '{phase}', atteso 'Running'")
            containers = pod["spec"].get("containers", [])
            image = containers[0].get("image", "") if containers else ""
            if EXPECTED_IMAGE_SUBSTR not in image:
                step.add_error(
                    f"L'immagine del pod deve contenere '{EXPECTED_IMAGE_SUBSTR}' "
                    f"(trovata: '{image}')"
                )

    with GradingStep(
        "I pod temporanei ubi9-user/ubi9-date sono stati eliminati (punti 2.2, 2.5, 3.4)"
    ) as step:
        for name in EXPECTED_DELETED_PODS:
            if oc_get_json("pod", name, "-n", project) is not None:
                step.add_error(
                    f"Pod '{name}' ancora presente: andava eliminato con "
                    f"'oc delete pod {name}' durante l'esercizio"
                )


if __name__ == "__main__":
    main()
