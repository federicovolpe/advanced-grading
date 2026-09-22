"""
Cap. 6 — Troubleshooting Containers: Remote Debugging Containers.

Basato sul testo della guida (6.3, fornita dall'utente): per debuggare
un'app Node.js containerizzata serve (1) pubblicare la porta di debug
(9229, quella di default di --inspect) sull'host e (2) montare il codice
applicativo dall'host in bind mount, cosi' le modifiche non richiedono di
ricostruire l'immagine. La guida copre anche l'uso interattivo di VSCodium
per mettere breakpoint e ispezionare variabili: non e' uno stato oggettivo
verificabile via `podman`, quindi questo esercizio grada solo la parte
strutturale (porta pubblicata + bind mount + debugger davvero in ascolto),
non l'uso del debugger stesso — stesso criterio di giudizio gia' applicato
alle attivita' puramente esplorative nella traccia DO180 (vedi README.md).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, podman_reset, podman_container, container_is_running,
    container_port_mappings, container_mounts, run_cli,
)

IMAGE = "docker.io/library/node:20-alpine"
NAME = "training-debug-app"
APP_DIR = os.path.expanduser("~/training-nodeapp")
CONTAINER_APP_DIR = "/app"
DEBUG_PORT = "9229"
APP_JS = """\
const http = require('http');
http.createServer((req, res) => res.end('ok')).listen(3000);
"""

TASK = f"""\
Il codice dell'app Node.js e' gia' pronto in "{APP_DIR}/app.js". Avvia un
container chiamato "{NAME}" che:
  - monti quella cartella dall'host su {CONTAINER_APP_DIR} (bind mount, non
    un volume: cosi' le modifiche al codice sull'host si riflettono subito)
  - pubblichi la porta di debug {DEBUG_PORT} sull'host
  - esegua "node --inspect=0.0.0.0:{DEBUG_PORT} app.js"

Comando suggerito (1):
  podman run -d --name {NAME} -p {DEBUG_PORT}:{DEBUG_PORT} \\
      -v {APP_DIR}:{CONTAINER_APP_DIR}:Z -w {CONTAINER_APP_DIR} {IMAGE} \\
      node --inspect=0.0.0.0:{DEBUG_PORT} app.js
"""

CHAPTER = "Cap. 6 — Troubleshooting Containers"
TITLE = "Esponi la porta di debug di un'app Node.js containerizzata"
PROJECT = None


def setup():
    podman_reset(containers=[NAME])
    os.makedirs(APP_DIR, exist_ok=True)
    with open(os.path.join(APP_DIR, "app.js"), "w") as fh:
        fh.write(APP_JS)


def grade():
    c = podman_container(NAME)

    with GradingStep(f"Il container {NAME} e' in esecuzione") as step:
        if not c or not container_is_running(NAME):
            step.fail(f"Container '{NAME}' non trovato o non in esecuzione")

    with GradingStep(f"La porta di debug {DEBUG_PORT} e' pubblicata sull'host") as step:
        if not c:
            step.fail("Container non trovato")
        else:
            ports = container_port_mappings(NAME)
            host_ports = ports.get(f"{DEBUG_PORT}/tcp", [])
            if DEBUG_PORT not in host_ports:
                step.add_error(f"porte pubblicate per {DEBUG_PORT}/tcp: {host_ports}")

    with GradingStep(f"Il codice e' montato in bind mount su {CONTAINER_APP_DIR}") as step:
        if not c:
            step.fail("Container non trovato")
        else:
            mounts = container_mounts(NAME)
            match = next(
                (m for m in mounts if m.get("Destination") == CONTAINER_APP_DIR), None
            )
            if not match:
                step.add_error(f"mount trovati: {mounts}")
            elif match.get("Type") != "bind":
                step.add_error(f"tipo di mount: {match.get('Type')!r}, atteso 'bind' (non un volume)")
            elif os.path.realpath(match.get("Source", "")) != os.path.realpath(APP_DIR):
                step.add_error(f"sorgente del mount: {match.get('Source')!r}, attesa {APP_DIR!r}")

    with GradingStep("Il debugger Node.js e' davvero in ascolto sulla porta pubblicata") as step:
        if not c or not container_is_running(NAME):
            step.fail("Container non in esecuzione")
        else:
            import socket
            try:
                with socket.create_connection(("127.0.0.1", int(DEBUG_PORT)), timeout=3):
                    pass
            except OSError as exc:
                step.add_error(f"connessione TCP a 127.0.0.1:{DEBUG_PORT} fallita: {exc}")


def cleanup():
    podman_reset(containers=[NAME])
    import shutil
    shutil.rmtree(APP_DIR, ignore_errors=True)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
