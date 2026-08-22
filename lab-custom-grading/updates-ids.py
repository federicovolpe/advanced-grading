#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato updates-ids (Cap. 7.2 "Container
Image Identity and Tags"), sprovvisto di `lab grade` ufficiale (la classe
UpdatesIds in do180/exercises/updates_ids.py implementa solo start()/finish(),
non grade()). Non esiste una cartella materials/labs o materials/solutions
per questo esercizio: e' puramente imperativo, senza manifest YAML, e la
specifica qui sotto viene dal testo del manuale (sezione 7.2), che elenca
passo-passo i comandi attesi.

start() (vedi do180/exercises/updates_ids.py) crea il progetto updates-ids,
verifica che le immagini ubi8/httpd-24:1-209 e ubi8/httpd-24:1-215 esistano
gia' nel registry della classroom (registry.lab.example.com:8443) e rende
pubblico il repository ubi8/httpd-24.

Stato finale atteso (prima di `lab finish`), uno per ogni azione concreta
richiesta dalla guida:

  - deployment/httpd1: creato dal tag 1-209 (punto 3.1) e mai piu' toccato:
    l'immagine resta quella per tutto il resto dell'esercizio.
  - deployment/httpd2: creato dal digest SHA del tag 1-209 (punto 5.4), poi
    aggiornato al tag 1-215 con `oc set image` (punto 6.1) - lo stato finale
    atteso e' quindi il tag 1-215, non il digest iniziale.
  - deployment/httpd3: creato SENZA specificare un tag (punto 7.4), per
    dimostrare che e' il container runtime a risolvere il default "latest",
    non `oc create deployment`. Di conseguenza l'immagine nello spec del
    Deployment resta il nome del repository SENZA suffisso ":tag" (non
    ":latest" - quella stringa non viene mai passata al comando). Scalato a
    2 repliche al punto 9.1.
  - Il tag "latest" nel registry: il punto 7.2 lo fa puntare al tag 1-209, ma
    il punto 8.1 lo ripunta al tag 1-215 (azione esplicita richiesta allo
    studente) - questo e' quindi lo stato atteso alla fine dell'esercizio,
    verificabile sul registry a prescindere dal cluster.

Non vengono gradati: i comandi di sola introspezione (oc image info, skopeo
inspect/login manuali, oc debug node + crictl - punti 2, 4, 5.2/5.3, 7.3/7.6),
che non modificano stato e non sono verificabili a posteriori; e il fatto che
i due pod di httpd3 finiscano per usare digest diversi (punti 9.3/9.4) - e'
una conseguenza osservata dalla guida, non un'azione che lo studente
configura, e dipende dal timing esatto delle pull del kubelet (se il pod piu'
vecchio venisse comunque ricreato in seguito, ripulirebbe la differenza senza
che lo studente abbia sbagliato nulla): gradarlo darebbe falsi negativi.

Uso: updates-ids.py [nome-progetto]   (default: updates-ids)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, skopeo_inspect

LAB_NAME = "updates-ids"

REGISTRY = "registry.lab.example.com:8443"
IMAGE_REPO = "ubi8/httpd-24"


def get_image(deployment):
    """Ritorna l'immagine del (solo) container del pod template, o "". Tutti
    e tre i deployment di questo esercizio sono creati con `oc create
    deployment --image ...` da un'unica immagine, quindi hanno un solo
    container."""
    containers = (deployment.get("spec") or {}).get("template", {}).get("spec", {}).get("containers", [])
    return containers[0].get("image", "") if containers else ""


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # Punto 3.1: deployment httpd1 creato dal tag 1-209, mai aggiornato.
    httpd1 = oc_get_json("deployment", "httpd1", "-n", project)
    with GradingStep("Il deployment httpd1 usa l'immagine con il tag 1-209") as step:
        if httpd1 is None:
            step.fail(f"Deployment 'httpd1' non trovato nel progetto {project}")
        else:
            expected = f"{REGISTRY}/{IMAGE_REPO}:1-209"
            image = get_image(httpd1)
            if image != expected:
                step.add_error(f"Immagine attesa {expected!r}, trovata {image!r}")
            ready = (httpd1.get("status") or {}).get("readyReplicas", 0)
            if ready < 1:
                step.add_error(f"readyReplicas={ready}, atteso almeno 1 (pod non pronto)")

    # Punti 5.4 + 6.1: creato dal digest di 1-209, poi aggiornato al tag
    # 1-215 - e' quest'ultima l'immagine attesa nello stato finale.
    httpd2 = oc_get_json("deployment", "httpd2", "-n", project)
    with GradingStep("Il deployment httpd2 e' stato aggiornato al tag 1-215") as step:
        if httpd2 is None:
            step.fail(f"Deployment 'httpd2' non trovato nel progetto {project}")
        else:
            expected = f"{REGISTRY}/{IMAGE_REPO}:1-215"
            image = get_image(httpd2)
            if image != expected:
                step.add_error(f"Immagine attesa {expected!r}, trovata {image!r}")
            ready = (httpd2.get("status") or {}).get("readyReplicas", 0)
            if ready < 1:
                step.add_error(f"readyReplicas={ready}, atteso almeno 1 (pod non pronto)")

    # Punto 7.4: creato SENZA tag, per dimostrare la risoluzione implicita
    # del default "latest" da parte del runtime, non di oc.
    httpd3 = oc_get_json("deployment", "httpd3", "-n", project)
    with GradingStep("Il deployment httpd3 e' stato creato senza specificare un tag") as step:
        if httpd3 is None:
            step.fail(f"Deployment 'httpd3' non trovato nel progetto {project}")
        else:
            expected = f"{REGISTRY}/{IMAGE_REPO}"
            image = get_image(httpd3)
            if image != expected:
                step.add_error(f"Immagine attesa senza tag ({expected!r}), trovata {image!r}")

    # Punto 9.1: scale a 2 repliche.
    with GradingStep("Il deployment httpd3 e' stato scalato a 2 repliche") as step:
        if httpd3 is None:
            step.fail(f"Deployment 'httpd3' non trovato nel progetto {project}")
        else:
            spec_replicas = (httpd3.get("spec") or {}).get("replicas", 0)
            ready = (httpd3.get("status") or {}).get("readyReplicas", 0)
            if spec_replicas != 2:
                step.add_error(f"spec.replicas={spec_replicas}, attese 2")
            if ready < 2:
                step.add_error(f"readyReplicas={ready}, attese almeno 2 (pod non pronti)")

    # Punto 8.1: skopeo copy 1-215 -> latest ripunta il tag "latest" (che al
    # punto 7.2 puntava a 1-209) alla stessa immagine del tag 1-215. Verifica
    # sul registry, non sul cluster - confronta i digest riportati da skopeo.
    with GradingStep(
        "Il tag 'latest' nel registry punta alla stessa immagine del tag 1-215"
    ) as step:
        ok_latest, info_latest = skopeo_inspect(f"{REGISTRY}/{IMAGE_REPO}:latest")
        ok_1215, info_1215 = skopeo_inspect(f"{REGISTRY}/{IMAGE_REPO}:1-215")
        if not ok_latest or not info_latest:
            step.fail(f"Impossibile ispezionare {REGISTRY}/{IMAGE_REPO}:latest")
        elif not ok_1215 or not info_1215:
            step.fail(f"Impossibile ispezionare {REGISTRY}/{IMAGE_REPO}:1-215")
        else:
            digest_latest = info_latest.get("Digest")
            digest_1215 = info_1215.get("Digest")
            if not digest_latest or digest_latest != digest_1215:
                step.add_error(
                    f"Digest di 'latest' ({digest_latest}) diverso da quello di "
                    f"'1-215' ({digest_1215})"
                )


if __name__ == "__main__":
    main()
