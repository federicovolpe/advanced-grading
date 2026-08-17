#!/usr/bin/env python3
"""
Grading "custom" per la LAB custom-lab (Cap. 6), sprovvista di `lab grade`
ufficiale (la classe CustomLab implementa solo start()/finish()).

I watch_items sono definiti direttamente nel modulo ufficiale
(do188/custom-lab.py, funzioni test_env_variables/test_workdir/
test_npm_run_defined/test_user_defined/test_entrypoint_defined/
test_application_running_http) e ispezionano l'IMMAGINE costruita dallo
studente, "localhost/podman-qr-app:latest" (non un container specifico per
nome: il nome del container non e' verificato da nessun watch_item, solo le
porte che risponde), con `podman inspect --format`:

- Config.Env contiene TLS_PORT=8443, HTTP_PORT=8080,
  CERTS_PATH=/etc/pki/tls/private/certs;
- Config.WorkingDir == /app;
- History contiene un layer con "npm install" (o "npm i");
- Config.User == student;
- Config.Entrypoint (non Cmd!) contiene "npm start";
- il container in esecuzione risponde su http://localhost:8080 e
  https://localhost:8443 (certificato self-signed, va ignorata la verifica
  TLS) con il testo "TEXT TO QR CODE CONVERTOR" nel body.

Il Containerfile ufficiale in materials/solutions/custom-lab/Containerfile
confronta esattamente questi valori (ENV, WORKDIR /app, USER student,
ENTRYPOINT npm start), confermando che sono impostati a build-time
sull'immagine e non a runtime sul container.

Uso: custom-lab.py   (nessun progetto OpenShift: solo Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, http_get_insecure, podman_image

LAB_NAME = "custom-lab"
IMAGE = "localhost/podman-qr-app:latest"

EXPECTED_ENV = {
    "TLS_PORT": "8443",
    "HTTP_PORT": "8080",
    "CERTS_PATH": "/etc/pki/tls/private/certs",
}
WORKDIR = "/app"
USER = "student"
HTTP_PORT = 8080
TLS_PORT = 8443
EXPECTED_TEXT = "TEXT TO QR CODE CONVERTOR"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    image = podman_image(IMAGE)

    with GradingStep(f"L'immagine '{IMAGE}' esiste") as step:
        if not image:
            step.fail(f"Immagine '{IMAGE}' non trovata")

    config = (image or {}).get("Config") or {}

    with GradingStep("L'immagine definisce TLS_PORT, HTTP_PORT e CERTS_PATH") as step:
        if not image:
            step.fail()
        else:
            env = {}
            for item in config.get("Env") or []:
                if "=" in item:
                    k, v = item.split("=", 1)
                    env[k] = v
            for key, value in EXPECTED_ENV.items():
                if env.get(key) != value:
                    step.add_error(f"Env var {key} errata (trovata: {env.get(key)!r})")

    with GradingStep(f"La working directory e' '{WORKDIR}'") as step:
        if not image:
            step.fail()
        elif config.get("WorkingDir") != WORKDIR:
            step.add_error(f"WorkingDir trovata: {config.get('WorkingDir')!r}")

    with GradingStep("Le dipendenze npm sono installate (layer 'npm install')") as step:
        if not image:
            step.fail()
        else:
            # Sostanzialmente identico a _check_npm_run() nel modulo ufficiale:
            # substring semplice su tutta la history, stessa imprecisione (es.
            # "npm i" e' un substring anche di "npm install") del test originale.
            history_text = " ".join(h.get("CreatedBy", "") for h in (image.get("History") or []))
            if not ("npm install" in history_text or "npm i" in history_text):
                step.add_error("Nessun layer della history esegue 'npm install'/'npm i'")

    with GradingStep(f"L'utente impostato e' '{USER}'") as step:
        if not image:
            step.fail()
        elif config.get("User") != USER:
            step.add_error(f"User trovato: {config.get('User')!r}")

    with GradingStep("L'entrypoint (non il cmd) esegue 'npm start'") as step:
        if not image:
            step.fail()
        else:
            entrypoint = config.get("Entrypoint") or []
            if "npm start" not in " ".join(entrypoint):
                step.add_error(f"Entrypoint trovato: {entrypoint!r}")

    with GradingStep("Il container risponde su http (8080) e https (8443)") as step:
        ok_http, body_http = http_get(f"http://localhost:{HTTP_PORT}")
        if not ok_http or EXPECTED_TEXT not in body_http:
            step.add_error(f"http://localhost:{HTTP_PORT} non risponde con il testo atteso")

        ok_https, body_https = http_get_insecure(f"https://localhost:{TLS_PORT}")
        if not ok_https or EXPECTED_TEXT not in body_https:
            step.add_error(f"https://localhost:{TLS_PORT} non risponde con il testo atteso")


if __name__ == "__main__":
    main()
