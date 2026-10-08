"""
Try-exam 5 — rete, volumi e container database. Il volume acme-wp-app
viene solo creato (il tema non avvia l'applicazione WordPress qui).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _exam_common import (
    IMG_WP_BACKEND, SETUP_TIMEOUT, GradingStep, podman_reset, podman_exec,
    container_is_running, ensure_images, check_container_basics,
    check_network_member, check_volume_mount, check_networks_exist,
    check_volumes_exist, run_cli,
)

NETWORK = "acme-wp"
DB_VOLUME = "acme-wp-backend"
APP_VOLUME = "acme-wp-app"
NAME = "acme-wp-backend"

TASK = f"""\
  - crea una network chiamata {NETWORK}
  - crea il volume per il database e chiamalo {DB_VOLUME}
  - crea un altro volume per l'applicazione WordPress, chiamalo {APP_VOLUME}
  - fai partire il database con l'immagine {IMG_WP_BACKEND}:
      - staccato dalla command line
      - deve chiamarsi {NAME}
      - montaci il volume {DB_VOLUME} nella directory /var/lib/mysql
      - collegalo alla network {NETWORK}
"""

SOLUTION = f"""\
podman network create {NETWORK}
podman volume create {DB_VOLUME}
podman volume create {APP_VOLUME}
podman run -d --name {NAME} --network {NETWORK} \\
    -v {DB_VOLUME}:/var/lib/mysql \\
    {IMG_WP_BACKEND}

Verifica:
  podman logs {NAME}      (attendi "ready for connections")
"""

CHAPTER = "Try exam"
TITLE = "5) Rete, volumi e database"
PROJECT = None


def setup():
    cleanup()
    ensure_images(IMG_WP_BACKEND)


def grade():
    check_networks_exist(NETWORK)
    check_volumes_exist(DB_VOLUME, APP_VOLUME)
    check_container_basics(NAME, IMG_WP_BACKEND)
    check_volume_mount(NAME, DB_VOLUME, "/var/lib/mysql")
    check_network_member(NAME, NETWORK)

    with GradingStep("Il database risponde") as step:
        if not container_is_running(NAME):
            step.fail("Container non in esecuzione")
        else:
            # Senza credenziali ping stampa "Access denied" ma esce con 0 se
            # il server e' su: conta l'exit code, non l'output.
            result = podman_exec(NAME, "mariadb-admin", "ping")
            if result.returncode != 0:
                step.add_error("mariadb non ancora pronto (riprova tra qualche secondo)")


def cleanup():
    podman_reset(containers=[NAME], volumes=[DB_VOLUME, APP_VOLUME], networks=[NETWORK])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
