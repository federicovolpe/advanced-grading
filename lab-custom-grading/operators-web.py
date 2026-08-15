#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato operators-web, sprovvisto di
`lab grade` ufficiale (la classe OperatorsWeb nel pacchetto do280 implementa
solo start()/finish(), non grade() - vedi <cache>/do280/operators-web.py).

Questo esercizio guida lo studente a installare il File Integrity Operator
DALLA WEB CONSOLE, ma lo stato risultante sul cluster (namespace,
OperatorGroup, Subscription, CSV) e' identico a quello ottenibile via CLI
nell'esercizio gemello operators-cli, quindi e' gradabile allo stesso modo
con `oc`. Non essendoci ne' materials/labs ne' materials/solutions per
operators-web (entrambe vuote in cache), i valori attesi (nome pacchetto
"file-integrity-operator", channel "stable", catalog source "gls-catalog-cs"
in openshift-marketplace) sono dedotti da
materials/solutions/operators-cli/{operator-group,subscription}.yaml, che
installa lo STESSO operatore dallo STESSO catalogo mirror del corso (il testo
di operators-web conferma "the file integrity operator has a single
available update channel" nel registro mirror disconnesso, coerente con lo
"stable" gia' visto in operators-cli).

Differenze rispetto a operators-cli tenute in conto (dal testo della guida,
sezione 7.4 del workbook):
- Il testo dice esplicitamente "You can use the default options" per la
  pagina Install Operator: NON verifichiamo quindi installPlanApproval (in
  operators-cli e' impostato manualmente a "Manual", ma il default della web
  console e' "Automatic" se lo studente non lo cambia) ne' i targetNamespaces
  esatti dell'OperatorGroup (il testo dice che l'operatore "installs to all
  namespaces", mentre operators-cli crea un OperatorGroup con
  targetNamespaces ristretto a se stesso: la web console potrebbe generarne
  uno diverso). Verifichiamo solo che un OperatorGroup esista nel namespace,
  non i suoi targetNamespaces.
- Il passo 4 ("Optionally, test the file integrity operator", creazione di
  una risorsa FileIntegrity "example-fileintegrity" con gracePeriod 60) e'
  esplicitamente OPZIONALE nel testo: non lo grading.
- I passi 6-7 finali chiedono allo studente di DISINSTALLARE l'operatore ed
  ELIMINARE il namespace openshift-file-integrity prima di "lab finish"
  (coerente col fatto che sia start() sia finish() del modulo ufficiale
  chiamano remove_operator_step + cancellazione del namespace, quindi il
  cluster viene comunque ripulito a fine esercizio indipendentemente da
  quanto fatto manualmente). Gradare lo stato "finale" prima di lab finish
  significherebbe verificare che NON esista piu' nulla, il che non sarebbe un
  controllo utile ne' distinguerebbe uno studente che ha completato
  l'esercizio da uno che non l'ha mai iniziato. Questo script grada quindi il
  checkpoint intermedio piu' significativo e verificabile: l'installazione
  riuscita dell'operatore (punti 1-3 della guida), il momento in cui uno
  studente eseguirebbe piu' sensatamente `lab grade operators-web` prima di
  procedere con la disinstallazione finale.

Uso: operators-web.py [nome-progetto]   (default: openshift-file-integrity)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "operators-web"
NAMESPACE = "openshift-file-integrity"
EXPECTED_PACKAGE = "file-integrity-operator"
EXPECTED_CHANNEL = "stable"
EXPECTED_SOURCE = "gls-catalog-cs"
EXPECTED_SOURCE_NAMESPACE = "openshift-marketplace"
EXPECTED_CSV_SUBSTR = "file-integrity"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else NAMESPACE
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep("Esiste un OperatorGroup nel namespace") as step:
        groups = oc_get_json("operatorgroup", "-n", project)
        if not groups or not groups.get("items"):
            step.fail(
                f"Nessun OperatorGroup trovato nel namespace '{project}' "
                "(la web console ne crea uno automaticamente durante "
                "l'installazione dell'operatore)"
            )

    subscription = None
    subs = oc_get_json("subscription", "-n", project)
    if subs and subs.get("items"):
        for sub in subs["items"]:
            if sub.get("spec", {}).get("name") == EXPECTED_PACKAGE:
                subscription = sub
                break

    with GradingStep(
        f"La Subscription al pacchetto {EXPECTED_PACKAGE} e' corretta"
    ) as step:
        if subscription is None:
            step.fail(
                f"Nessuna Subscription al pacchetto '{EXPECTED_PACKAGE}' "
                f"trovata nel namespace '{project}'"
            )
        else:
            spec = subscription.get("spec", {})
            if spec.get("channel") != EXPECTED_CHANNEL:
                step.add_error(
                    f"channel atteso '{EXPECTED_CHANNEL}' "
                    f"(trovato: {spec.get('channel')})"
                )
            if spec.get("source") != EXPECTED_SOURCE:
                step.add_error(
                    f"source atteso '{EXPECTED_SOURCE}' "
                    f"(trovato: {spec.get('source')})"
                )
            if spec.get("sourceNamespace") != EXPECTED_SOURCE_NAMESPACE:
                step.add_error(
                    f"sourceNamespace atteso '{EXPECTED_SOURCE_NAMESPACE}' "
                    f"(trovato: {spec.get('sourceNamespace')})"
                )

    with GradingStep(
        "Il ClusterServiceVersion del File Integrity Operator e' Succeeded"
    ) as step:
        csvs = oc_get_json("csv", "-n", project)
        if not csvs or not csvs.get("items"):
            step.fail(f"Nessun CSV trovato nel namespace '{project}'")
        else:
            csv = None
            for item in csvs["items"]:
                name = item.get("metadata", {}).get("name", "")
                display_name = item.get("spec", {}).get("displayName", "")
                if (
                    EXPECTED_CSV_SUBSTR in name.lower()
                    or EXPECTED_CSV_SUBSTR in display_name.lower()
                ):
                    csv = item
                    break
            if csv is None:
                step.fail(
                    "Nessun CSV relativo al File Integrity Operator trovato "
                    f"nel namespace '{project}'"
                )
            else:
                phase = csv.get("status", {}).get("phase")
                if phase != "Succeeded":
                    step.add_error(
                        f"Il CSV '{csv['metadata']['name']}' e' in fase "
                        f"'{phase}' (atteso: Succeeded)"
                    )


if __name__ == "__main__":
    main()
