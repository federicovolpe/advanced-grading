#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato reliability-ha, sprovvisto di
`lab grade` ufficiale (la classe ReliabilityHa nel pacchetto do180 implementa
solo start()/finish(), non grade() - vedi
~/.cache/uv/.../do180/exercises/reliability_ha.py, LAB = "reliability-ha").

Questo esercizio e' in gran parte osservativo (restartPolicy, crash via
/destruct, attesa di uno startup delay, load-balancing via /togglesick): la
guida non chiede di produrre un artefatto finale unico, ma DETTA per intero
il contenuto di due manifest in due momenti precisi, che restano applicati
fino a "Finish" (nessun passo della guida chiede di eliminarli prima):

1. long-load.yaml (Pod standalone, ~/DO180/labs/reliability-ha): l'ULTIMA
   versione dettata dalla guida (punto 4.1) e' restartPolicy: Always +
   env START_DELAY=60000, applicata al punto 4.2 e mai piu' toccata/eliminata
   nei passi successivi. E' quindi lo stato finale verificabile di questo
   file/pod.
2. long-load-deploy.yaml (Deployment+Service+Route "long-load", stesso
   materials/labs, NON modificato dallo studente): la guida chiede solo di
   applicarlo cosi' com'e' (punto 5.3) per osservare il load balancing fra
   3 repliche con START_DELAY=15000. Verificarne la presenza/correttezza
   equivale a verificare che lo studente abbia eseguito quell'apply.

NON gradato (nessun valore atteso oggettivo o stato stabile):
- Restart count del pod dopo /destruct nei passi 2-3 (transiente, il pod
  viene ricreato/eliminato piu' volte nella stessa guida: un check qui
  darebbe falsi negativi a seconda del momento esatto in cui gira il
  grading).
- Lo stato "sick"/"unhealthy" indotto da /togglesick sul pod del deployment
  al punto 5.5: e' un solo pod su 3, non deterministico quale, e la guida
  non chiede di ripristinarlo: il check sulla Route sotto usa piu' tentativi
  proprio per non dipendere da quale pod risponde.

Uso: reliability-ha.py [nome-progetto]   (default: reliability-ha)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, http_get, get_route_host

LAB_NAME = "reliability-ha"
IMAGE_SUBSTR = "redhattraining/long-load:v1"

STANDALONE_POD = "long-load"
EXPECTED_STANDALONE_START_DELAY = "60000"  # guida, punto 4.1

DEPLOY_NAME = "long-load"
SERVICE_NAME = "long-load"
ROUTE_NAME = "long-load"
EXPECTED_REPLICAS = 3
EXPECTED_DEPLOY_START_DELAY = "15000"  # guida, punto 5.1 (file non modificato)
APP_PORT = 3000

HEALTH_CHECK_ATTEMPTS = 5  # per non dipendere dal pod "toggled sick" al 5.5


def get_env(container, name):
    for e in (container.get("env") or []):
        if e.get("name") == name:
            return e.get("value")
    return None


def get_container(pod_or_deploy_spec, name):
    for c in pod_or_deploy_spec.get("containers", []) or []:
        if c.get("name") == name:
            return c
    containers = pod_or_deploy_spec.get("containers") or []
    return containers[0] if containers else None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # --- 1. Pod standalone "long-load" (punti 1-4 della guida) ---
    pod = oc_get_json("pod", STANDALONE_POD, "-n", project)
    with GradingStep(
        f"Il pod standalone '{STANDALONE_POD}' e' configurato come previsto "
        "dall'ultima modifica a long-load.yaml (restartPolicy: Always, "
        f"START_DELAY={EXPECTED_STANDALONE_START_DELAY})"
    ) as step:
        if pod is None:
            step.fail(
                f"Pod '{STANDALONE_POD}' non trovato: atteso presente e in "
                "esecuzione dal punto 4.2 della guida fino a 'lab finish'"
            )
        else:
            spec = pod.get("spec", {})
            container = get_container(spec, STANDALONE_POD)
            if container is None:
                step.add_error("Nessun container trovato nel pod")
            else:
                if IMAGE_SUBSTR not in container.get("image", ""):
                    step.add_error(
                        f"Immagine inattesa (trovata: {container.get('image')}, "
                        f"attesa una contenente '{IMAGE_SUBSTR}')"
                    )
                if spec.get("restartPolicy") != "Always":
                    step.add_error(
                        f"restartPolicy errata (trovata: {spec.get('restartPolicy')}, "
                        "attesa 'Always', come richiesto al punto 4.1 della guida)"
                    )
                start_delay = get_env(container, "START_DELAY")
                if start_delay != EXPECTED_STANDALONE_START_DELAY:
                    step.add_error(
                        f"Variabile START_DELAY errata (trovata: {start_delay}, "
                        f"attesa '{EXPECTED_STANDALONE_START_DELAY}', punto 4.1)"
                    )

    # --- 2. Deployment "long-load" (punto 5.1/5.3, file NON modificato) ---
    deployment = oc_get_json("deployment", DEPLOY_NAME, "-n", project)
    deploy_container = None
    with GradingStep(
        f"Il deployment '{DEPLOY_NAME}' e' stato applicato con 3 repliche "
        f"dell'immagine long-load:v1 (START_DELAY={EXPECTED_DEPLOY_START_DELAY})"
    ) as step:
        if deployment is None:
            step.fail(
                f"Deployment '{DEPLOY_NAME}' non trovato: atteso da "
                "'oc apply -f long-load-deploy.yaml' (punto 5.3 della guida)"
            )
        else:
            dep_spec = deployment.get("spec", {})
            if dep_spec.get("replicas") != EXPECTED_REPLICAS:
                step.add_error(
                    f"Numero di repliche errato (trovato: {dep_spec.get('replicas')}, "
                    f"atteso {EXPECTED_REPLICAS})"
                )
            deploy_container = get_container(
                dep_spec.get("template", {}).get("spec", {}), DEPLOY_NAME
            )
            if deploy_container is None:
                step.add_error("Nessun container trovato nel deployment")
            else:
                if IMAGE_SUBSTR not in deploy_container.get("image", ""):
                    step.add_error(
                        f"Immagine inattesa (trovata: {deploy_container.get('image')}, "
                        f"attesa una contenente '{IMAGE_SUBSTR}')"
                    )
                start_delay = get_env(deploy_container, "START_DELAY")
                if start_delay != EXPECTED_DEPLOY_START_DELAY:
                    step.add_error(
                        f"Variabile START_DELAY errata (trovata: {start_delay}, "
                        f"attesa '{EXPECTED_DEPLOY_START_DELAY}')"
                    )

    with GradingStep(
        f"Tutte le {EXPECTED_REPLICAS} repliche del deployment sono pronte"
    ) as step:
        if deployment is None:
            step.fail()
        else:
            ready = deployment.get("status", {}).get("readyReplicas", 0)
            if ready < EXPECTED_REPLICAS:
                step.add_error(
                    f"Repliche pronte: {ready}/{EXPECTED_REPLICAS} (atteso: tutte pronte, "
                    "dopo lo startup delay di 15s indicato nella guida)"
                )

    # --- 3. Service + Route (esposizione dell'app, punto 5.1/5.3) ---
    service = oc_get_json("service", SERVICE_NAME, "-n", project)
    with GradingStep(
        f"Il Service '{SERVICE_NAME}' espone l'applicazione sulla porta {APP_PORT}"
    ) as step:
        if service is None:
            step.fail(f"Service '{SERVICE_NAME}' non trovato nel progetto")
        else:
            ports = service.get("spec", {}).get("ports", []) or []
            if not any(p.get("port") == APP_PORT for p in ports):
                step.add_error(
                    f"Nessuna porta {APP_PORT} esposta dal Service "
                    f"(trovate: {[p.get('port') for p in ports]})"
                )

    route = oc_get_json("route", ROUTE_NAME, "-n", project)
    with GradingStep(f"La Route '{ROUTE_NAME}' punta al Service '{SERVICE_NAME}'") as step:
        if route is None:
            step.fail(f"Route '{ROUTE_NAME}' non trovata nel progetto")
        else:
            to = route.get("spec", {}).get("to", {})
            if to.get("name") != SERVICE_NAME:
                step.add_error(
                    f"La Route punta a '{to.get('name')}' invece di '{SERVICE_NAME}'"
                )

    with GradingStep(
        "La Route risponde correttamente su /health (almeno un pod sano)"
    ) as step:
        if route is None:
            step.fail()
        else:
            host = get_route_host(ROUTE_NAME, project)
            if not host:
                step.add_error("Impossibile determinare l'host della Route")
            else:
                url = f"http://{host}/health"
                # Piu' tentativi: al punto 5.5 della guida un pod su 3 viene
                # reso volutamente "unhealthy" (/togglesick) e non viene mai
                # ripristinato, quindi una singola richiesta puo' cadere su
                # quel pod per puro round-robin senza che sia un errore reale.
                ok_once = False
                last_body = None
                for _ in range(HEALTH_CHECK_ATTEMPTS):
                    ok, body = http_get(url, timeout=5)
                    last_body = body
                    if ok and body.strip() == "Ok":
                        ok_once = True
                        break
                if not ok_once:
                    step.add_error(
                        f"GET {url} non ha mai risposto 'Ok' in {HEALTH_CHECK_ATTEMPTS} "
                        f"tentativi (ultima risposta: {last_body!r})"
                    )


if __name__ == "__main__":
    main()
