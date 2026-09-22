"""
Cap. 7 — Multi-container Applications with Compose: Build Developer
Environments with Compose.
Scrivi un compose.yaml con due servizi e avvialo con 'podman-compose up -d'
(comando confermato dal testo della guida, 6.x/7.x: 'podman-compose up',
non 'podman compose up' — quest'ultimo esiste solo come wrapper a partire
da Podman 4.7 e richiede comunque podman-compose installato sotto).

I container creati da podman-compose sono identificati per label
('com.docker.compose.project'/'com.docker.compose.service'), non per nome
esatto: lo schema di naming (es. "<project>_web_1") e' un dettaglio di
implementazione di podman-compose, verificato dal vivo ma non garantito
stabile fra versioni.
"""
import sys, os, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, podman, podman_reset, podman_ps_by_label,
    container_is_running, podman_exec, run_cli,
)

IMAGE = "registry.access.redhat.com/ubi9/httpd-24"
PROJECT_DIR = os.path.expanduser("~/training-compose")
PROJECT_NAME = "training-compose"  # = basename(PROJECT_DIR): fissa il nome del progetto compose
NETWORK = f"{PROJECT_NAME}_default"
COMPOSE_CONTENT = f"""\
services:
  web:
    image: {IMAGE}
  api:
    image: {IMAGE}
"""

TASK = f"""\
Scrivi questo contenuto in "{PROJECT_DIR}/compose.yaml":

  services:
    web:
      image: {IMAGE}
    api:
      image: {IMAGE}

Poi avvialo con podman-compose (crea i due servizi su una rete condivisa,
con risoluzione DNS automatica per nome servizio).

Comando suggerito (dopo aver scritto compose.yaml):
  cd {PROJECT_DIR} && podman-compose up -d
"""

CHAPTER = "Cap. 7 — Multi-container Applications with Compose"
TITLE = "Avvia un'app multi-container con Compose"
PROJECT = None


def _compose_containers():
    return podman_ps_by_label("com.docker.compose.project", PROJECT_NAME)


def _teardown_compose():
    for name in _compose_containers():
        podman("rm", "-f", name)
    podman("network", "rm", "-f", NETWORK)


def setup():
    _teardown_compose()
    shutil.rmtree(PROJECT_DIR, ignore_errors=True)
    os.makedirs(PROJECT_DIR, exist_ok=True)


def grade():
    containers = _compose_containers()
    web = next((c for c in containers if "web" in c), None)
    api = next((c for c in containers if "api" in c), None)

    with GradingStep("Sono stati creati i due servizi 'web' e 'api' (podman-compose up)") as step:
        if not web or not api:
            step.fail(f"container trovati con label del progetto '{PROJECT_NAME}': {containers}")

    with GradingStep("Entrambi i servizi sono in esecuzione") as step:
        if not web or not api:
            step.fail("Servizi non trovati")
        elif not container_is_running(web) or not container_is_running(api):
            step.add_error(f"web running={bool(web and container_is_running(web))}, api running={bool(api and container_is_running(api))}")

    with GradingStep("Il servizio 'web' raggiunge 'api' per nome (rete condivisa di Compose)") as step:
        if not web or not api or not container_is_running(web) or not container_is_running(api):
            step.fail("Entrambi i servizi devono essere in esecuzione")
        else:
            result = podman_exec(
                web, "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                "--max-time", "5", "http://api:8080/",
            )
            code = (result.stdout or "").strip()
            if result.returncode != 0 or not code.isdigit() or code == "000":
                step.add_error(f"curl da 'web' ad 'api' fallita: rc={result.returncode} out={code!r} err={result.stderr.strip()[:200]}")


def cleanup():
    _teardown_compose()
    shutil.rmtree(PROJECT_DIR, ignore_errors=True)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
