"""
Try-exam 6 — troubleshooting. Le immagini -broken sono costruite da
_exam_common.ensure_images() con due guasti, scoperti dai log/dal
comportamento e risolvibili solo con opzioni di `podman run` (l'immagine
e' imposta dal tema):
  - wp-backend-broken: manca MARIADB_ROOT_PASSWORD -> il DB esce subito;
  - wp-app-broken: WORDPRESS_DB_HOST punta ad acme-wp-backend (l'es. 5),
    non raggiungibile sulla rete acme-troubles.
Il nome del container DB non e' nel tema annotato: acme-wp-backend-ts,
coerente con gli altri nomi "-ts".

Il check finale chiede la home di WordPress dall'interno del container app
(curl c'e' nell'immagine ufficiale): nessuna porta host richiesta dal tema.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _exam_common import (
    IMG_WP_BACKEND_BROKEN, IMG_WP_APP_BROKEN, SETUP_TIMEOUT, GradingStep,
    podman_reset, podman_exec, container_is_running, ensure_images,
    check_container_basics, check_network_member, check_volume_mount,
    check_networks_exist, check_volumes_exist, run_cli,
)

NETWORK = "acme-troubles"
DB_VOLUME = "acme-wp-backend-ts"
APP_VOLUME = "acme-wp-app-ts"
DB_NAME = "acme-wp-backend-ts"
APP_NAME = "acme-wp-app-ts"

TASK = f"""\
  - crea una network chiamata {NETWORK}
  - crea il volume per il database e chiamalo {DB_VOLUME}
  - crea un altro volume per l'applicazione WordPress, chiamalo {APP_VOLUME}
  - il container database backend deve avere queste specifiche:
      - immagine {IMG_WP_BACKEND_BROKEN}
      - nome {DB_NAME}
      - network {NETWORK}
      - volume {DB_VOLUME} sulla directory /var/lib/mysql
  - l'applicazione WordPress deve avere queste specifiche:
      - immagine {IMG_WP_APP_BROKEN}
      - nome {APP_NAME}
      - network {NETWORK}
      - volume {APP_VOLUME} accessibile dal container al path /var/www/html
  - entrambi i container staccati dalla command line

Le immagini contengono degli errori di configurazione: individuali e
correggili (senza cambiare immagine) finche' entrambi i container sono in
esecuzione e WordPress riesce a collegarsi al database.
"""

CHAPTER = "Try exam"
TITLE = "6) Troubleshooting WordPress + database"
PROJECT = None


def setup():
    cleanup()
    ensure_images(IMG_WP_BACKEND_BROKEN, IMG_WP_APP_BROKEN)


def grade():
    check_networks_exist(NETWORK)
    check_volumes_exist(DB_VOLUME, APP_VOLUME)

    check_container_basics(DB_NAME, IMG_WP_BACKEND_BROKEN)
    check_network_member(DB_NAME, NETWORK)
    check_volume_mount(DB_NAME, DB_VOLUME, "/var/lib/mysql")

    check_container_basics(APP_NAME, IMG_WP_APP_BROKEN)
    check_network_member(APP_NAME, NETWORK)
    check_volume_mount(APP_NAME, APP_VOLUME, "/var/www/html")

    with GradingStep("WordPress si collega al database") as step:
        if not container_is_running(APP_NAME):
            step.fail("Container WordPress non in esecuzione")
        else:
            result = podman_exec(
                APP_NAME, "curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{redirect_url}",
                "--max-time", "10", "http://localhost/",
            )
            out = result.stdout.strip()
            # Con il DB raggiungibile e non ancora installato, WordPress
            # redirige a wp-admin/install.php; senza DB risponde 500.
            if not (out.startswith("200") or "install.php" in out):
                step.add_error(f"risposta di WordPress: {out or 'nessuna'} (errore di connessione al database?)")


def cleanup():
    podman_reset(containers=[APP_NAME, DB_NAME], volumes=[DB_VOLUME, APP_VOLUME], networks=[NETWORK])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
