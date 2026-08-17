#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise openshift-applications, sprovvista di
`lab grade` ufficiale (la classe OpenshiftApplications nel pacchetto do188
implementa solo start()/finish(), non grade()).

Il modulo ufficiale (do188/openshift-applications.py) usa
`project = "ocp-applications"` (commento: "oc cannot create openshift-
projects"), diverso dal nome esercizio __LAB__ = "openshift-applications".

start() applica i manifest in materials/kubefiles/podman-hello/:
- server.yaml: Pod "hello-server" (immagine podman-hello-server, porta
  container 3000)
- server-service.yaml: Service "hello-server-svc", spec.ports[0] con
  port=3000 e targetPort=3000
- client.yaml: Pod "hello-client" (immagine podman-hello-client)

La guida (Cap. 8.2) chiede di modificare il Service "hello-server-svc" per
esporlo su port=8080 (lasciando targetPort=3000, dato che il server continua
ad ascoltare su 3000), e di ricreare il Pod "hello-client" con la env
PORT=8080 cosi' che il client contatti il server tramite il nuovo port del
Service. Il manuale mostra che l'ultima riga di `oc logs hello-client` e'
esattamente `{"hello":"world"}` (risposta del server tramite curl nel client).

Uso: openshift-applications.py [nome-progetto]   (default: ocp-applications,
nome REALE del progetto usato dal modulo ufficiale, diverso dal nome
esercizio)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, oc_logs, project_exists

LAB_NAME = "openshift-applications"
PROJECT = "ocp-applications"
SERVICE = "hello-server-svc"
CLIENT_POD = "hello-client"
CLIENT_IMAGE_PREFIX = "registry.ocp4.example.com:8443/redhattraining/podman-hello-client"
EXPECTED_SVC_PORT = 8080
EXPECTED_TARGET_PORT = 3000
EXPECTED_LOG_LINE = '{"hello":"world"}'


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else PROJECT
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il Service '{SERVICE}' espone la porta {EXPECTED_SVC_PORT} "
        f"(invece della {EXPECTED_TARGET_PORT} iniziale)"
    ) as step:
        svc = oc_get_json("service", SERVICE, "-n", project)
        if not svc:
            step.fail(f"Service '{SERVICE}' non trovato")
        else:
            ports = (svc.get("spec") or {}).get("ports") or []
            if not ports:
                step.fail("Il Service non ha porte definite")
            else:
                port0 = ports[0]
                if port0.get("port") != EXPECTED_SVC_PORT:
                    step.add_error(
                        f"spec.ports[0].port e' {port0.get('port')!r}, "
                        f"atteso {EXPECTED_SVC_PORT}"
                    )
                if port0.get("targetPort") != EXPECTED_TARGET_PORT:
                    step.add_error(
                        f"spec.ports[0].targetPort e' {port0.get('targetPort')!r}, "
                        f"atteso {EXPECTED_TARGET_PORT} (il server ascolta ancora su 3000)"
                    )

    pod = oc_get_json("pod", CLIENT_POD, "-n", project)
    with GradingStep(
        f"Il Pod '{CLIENT_POD}' e' stato ricreato con env PORT={EXPECTED_SVC_PORT} "
        "e l'immagine corretta"
    ) as step:
        if not pod:
            step.fail(f"Pod '{CLIENT_POD}' non trovato")
        else:
            phase = (pod.get("status") or {}).get("phase")
            if phase != "Running":
                step.add_error(f"Il pod non e' in stato Running (fase attuale: {phase!r})")

            containers = (pod.get("spec") or {}).get("containers") or []
            container = next(
                (c for c in containers if c.get("name") == CLIENT_POD), None
            ) or (containers[0] if containers else {})

            image = container.get("image", "")
            if not image.startswith(CLIENT_IMAGE_PREFIX):
                step.add_error(f"Immagine del container errata: {image!r}")

            env = {e.get("name"): e.get("value") for e in (container.get("env") or [])}
            if env.get("PORT") != str(EXPECTED_SVC_PORT):
                step.add_error(
                    f"Env var PORT errata (trovata: {env.get('PORT')!r}), "
                    f"attesa {str(EXPECTED_SVC_PORT)!r}"
                )

    with GradingStep(
        f"I log di '{CLIENT_POD}' mostrano l'ultima risposta corretta dal server"
    ) as step:
        if not pod:
            step.fail(f"Pod '{CLIENT_POD}' non trovato")
        else:
            logs = oc_logs(CLIENT_POD, project, tail=1)
            last_line = logs.strip().splitlines()[-1] if logs.strip() else ""
            if last_line != EXPECTED_LOG_LINE:
                step.add_error(
                    f"Ultima riga dei log errata: {last_line!r}, "
                    f"attesa {EXPECTED_LOG_LINE!r}"
                )


if __name__ == "__main__":
    main()
