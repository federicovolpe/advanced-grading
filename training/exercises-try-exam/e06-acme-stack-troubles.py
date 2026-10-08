"""
Try-exam 6 — troubleshooting dello stack dell'es. 5 con tre immagini
-broken, un guasto per immagine (vedi _BUILDS in _exam_common):
  - db-broken: MYSQL_PASSWORD sbagliata rispetto al tema;
  - app-broken: WORDPRESS_DB_HOST verso un host inesistente;
  - frontend-broken: ACME_APP_HOST=fixme.
Si correggono solo con opzioni di `podman run` (-e), senza cambiare
immagine. Trappola voluta: mysql applica MYSQL_PASSWORD solo alla prima
inizializzazione del volume, quindi dopo averla corretta il volume va
ricreato. Il grading lo verifica facendo login con la password del tema.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _exam_common import (
    IMG_DB_BROKEN, IMG_APP_BROKEN, IMG_FRONTEND_BROKEN, STACK_DB,
    SETUP_TIMEOUT, GradingStep, podman_reset, podman_exec,
    container_is_running, ensure_images, check_container_basics,
    check_network_member, check_volume_mount, check_networks_exist,
    check_volumes_exist, check_port, check_stack_http, run_cli,
)

NETWORK = "acme-troubles"
DB_VOLUME = "acme-db-data-ts"
APP_VOLUME = "acme-app-data-ts"
DB_NAME = "acme-db-ts"
APP_NAME = "acme-app-ts"
FRONTEND_NAME = "acme-frontend-ts"
PORT = 8003

TASK = f"""\
Tira su di nuovo lo stack ACME, questa volta con le immagini fornite dal
team di sviluppo.

  - una network chiamata {NETWORK}, a cui sono collegati tutti i container
  - un volume {DB_VOLUME} per i dati del database
  - un volume {APP_VOLUME} per i file dell'applicazione

  Database:
    - nome {DB_NAME}, immagine {IMG_DB_BROKEN}
    - volume {DB_VOLUME} sulla directory /var/lib/mysql
  Applicazione:
    - nome {APP_NAME}, immagine {IMG_APP_BROKEN}
    - volume {APP_VOLUME} sulla directory /var/www/html
  Frontend:
    - nome {FRONTEND_NAME}, immagine {IMG_FRONTEND_BROKEN}
    - porta 80 del container pubblicata sulla porta {PORT} dell'host

  Tutti i container staccati dalla command line.

Le credenziali applicative corrette del database sono:
  database {STACK_DB['name']}, utente {STACK_DB['user']}, password {STACK_DB['password']}

Le immagini contengono errori di configurazione: individuali e
correggili SENZA cambiare immagine, finche' http://localhost:{PORT}
mostra l'installazione di WordPress.
"""

SOLUTION = f"""\
podman network create {NETWORK}
podman volume create {DB_VOLUME}
podman volume create {APP_VOLUME}

podman run -d --name {DB_NAME} --network {NETWORK} \\
    -v {DB_VOLUME}:/var/lib/mysql \\
    -e MYSQL_PASSWORD={STACK_DB['password']} \\
    {IMG_DB_BROKEN}

podman run -d --name {APP_NAME} --network {NETWORK} \\
    -v {APP_VOLUME}:/var/www/html \\
    -e WORDPRESS_DB_HOST={DB_NAME} \\
    {IMG_APP_BROKEN}

podman run -d --name {FRONTEND_NAME} --network {NETWORK} \\
    -p {PORT}:80 \\
    -e ACME_APP_HOST={APP_NAME} \\
    {IMG_FRONTEND_BROKEN}

Metodo: prima di avviare, guarda cosa c'e' "cotto" nelle immagini:
  podman image inspect <immagine> --format '{{{{.Config.Env}}}}'
e confronta ogni valore con il tema (nomi container, credenziali).

I tre guasti e come si vedono:
  1. frontend: ACME_APP_HOST=fixme
     -> il container esce; podman logs {FRONTEND_NAME}:
        host not found in upstream "fixme:80"
  2. app: WORDPRESS_DB_HOST=acme-database (nessun container con quel nome)
     -> la pagina dice "Error establishing a database connection";
        podman logs {APP_NAME}:
        php_network_getaddresses: getaddrinfo for acme-database failed:
        Name or service not known
     "Name or service not known" = errore DNS: l'hostname non esiste
     sulla rete. Il DB si raggiunge col NOME DEL CONTAINER ({DB_NAME}).
  3. db: MYSQL_PASSWORD=changeme, l'app usa {STACK_DB['password']}
     -> sistemato l'host, i log dell'app passano a
        Access denied for user '{STACK_DB['user']}'@...
     Si corregge la password del DB come da tema (-e MYSQL_PASSWORD=...).

ATTENZIONE: mysql crea utente e password SOLO alla prima inizializzazione
di un volume vuoto. Se il DB e' gia' partito una volta con la password
sbagliata, correggere -e non basta:
  podman rm -f {DB_NAME}
  podman volume rm {DB_VOLUME} && podman volume create {DB_VOLUME}
  (e poi di nuovo podman run ... del DB)

Per ricreare un container corretto: podman rm -f <nome>, poi podman run.
Ordine di avvio: db -> app -> frontend.

ATTENZIONE 2: nginx risolve l'IP dell'app solo all'avvio. Se ricrei
l'app con il frontend gia' attivo, il frontend risponde 502 Bad Gateway
(punta al vecchio IP): podman restart {FRONTEND_NAME}.

Verifica:
  curl -sI localhost:{PORT}     (302 verso wp-admin/install.php)
"""

CHAPTER = "Try exam"
TITLE = "6) Troubleshooting stack con immagini -broken"
PROJECT = None


def setup():
    cleanup()
    ensure_images(IMG_DB_BROKEN, IMG_APP_BROKEN, IMG_FRONTEND_BROKEN)


def grade():
    check_networks_exist(NETWORK)
    check_volumes_exist(DB_VOLUME, APP_VOLUME)

    check_container_basics(DB_NAME, IMG_DB_BROKEN)
    check_network_member(DB_NAME, NETWORK)
    check_volume_mount(DB_NAME, DB_VOLUME, "/var/lib/mysql")

    with GradingStep(f"{DB_NAME}: l'utente {STACK_DB['user']} accede con la password del tema") as step:
        if not container_is_running(DB_NAME):
            step.fail("Container non in esecuzione")
        else:
            result = podman_exec(
                DB_NAME, "mysql", f"-u{STACK_DB['user']}", f"-p{STACK_DB['password']}",
                "-h", "127.0.0.1", STACK_DB["name"], "-e", "SELECT 1",
            )
            if result.returncode != 0:
                step.add_error((result.stderr or "accesso fallito").strip().splitlines()[-1])

    check_container_basics(APP_NAME, IMG_APP_BROKEN)
    check_network_member(APP_NAME, NETWORK)
    check_volume_mount(APP_NAME, APP_VOLUME, "/var/www/html")

    check_container_basics(FRONTEND_NAME, IMG_FRONTEND_BROKEN)
    check_network_member(FRONTEND_NAME, NETWORK)
    check_port(FRONTEND_NAME, PORT)

    check_stack_http(PORT)


def cleanup():
    podman_reset(
        containers=[FRONTEND_NAME, APP_NAME, DB_NAME],
        volumes=[DB_VOLUME, APP_VOLUME],
        networks=[NETWORK],
    )


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
