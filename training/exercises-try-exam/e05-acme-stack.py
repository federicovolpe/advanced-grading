"""
Try-exam 5 — stack a tre livelli: database mysql, applicazione WordPress,
frontend nginx (reverse proxy verso l'app) pubblicato su 8003.

Il tema dice solo "tira su lo stack": va bene sia con `podman run` sia con
podman-compose, purche' nomi di container/rete/volumi siano quelli chiesti
(con compose servono container_name e name: espliciti, altrimenti
compose li prefissa col nome del progetto).

Il frontend risolve l'app all'avvio (nginx esce se l'upstream non esiste):
l'ordine di avvio conta, db -> app -> frontend.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _exam_common import (
    IMG_MYSQL, IMG_WORDPRESS, IMG_FRONTEND, STACK_DB, SETUP_TIMEOUT,
    GradingStep, podman_reset, podman_exec, container_is_running,
    ensure_images, check_container_basics, check_network_member,
    check_volume_mount, check_networks_exist, check_volumes_exist,
    check_port, check_stack_http, run_cli,
)

NETWORK = "acme-stack"
DB_VOLUME = "acme-db-data"
APP_VOLUME = "acme-app-data"
DB_NAME = "acme-db"
APP_NAME = "acme-app"
FRONTEND_NAME = "acme-frontend"
PORT = 8003
ROOT_PASSWORD = "acme-root"

TASK = f"""\
Tira su lo stack applicativo ACME, composto da tre container.

  - una network chiamata {NETWORK}, a cui sono collegati tutti i container
  - un volume {DB_VOLUME} per i dati del database
  - un volume {APP_VOLUME} per i file dell'applicazione

  Database:
    - nome {DB_NAME}, immagine {IMG_MYSQL}
    - volume {DB_VOLUME} sulla directory /var/lib/mysql
    - password di root: {ROOT_PASSWORD}
    - database applicativo: {STACK_DB['name']}
    - utente applicativo: {STACK_DB['user']}, password {STACK_DB['password']}

  Applicazione:
    - nome {APP_NAME}, immagine {IMG_WORDPRESS}
    - volume {APP_VOLUME} sulla directory /var/www/html
    - deve usare il database {DB_NAME} con le credenziali applicative sopra

  Frontend:
    - nome {FRONTEND_NAME}, immagine {IMG_FRONTEND}
    - inoltra le richieste all'applicazione
    - la porta 80 del container e' pubblicata sulla porta {PORT} dell'host

  Tutti i container staccati dalla command line.
  Lo stack funziona quando http://localhost:{PORT} mostra l'installazione
  di WordPress.
"""

SOLUTION = f"""\
podman network create {NETWORK}
podman volume create {DB_VOLUME}
podman volume create {APP_VOLUME}

podman run -d --name {DB_NAME} --network {NETWORK} \\
    -v {DB_VOLUME}:/var/lib/mysql \\
    -e MYSQL_ROOT_PASSWORD={ROOT_PASSWORD} \\
    -e MYSQL_DATABASE={STACK_DB['name']} \\
    -e MYSQL_USER={STACK_DB['user']} \\
    -e MYSQL_PASSWORD={STACK_DB['password']} \\
    {IMG_MYSQL}

podman run -d --name {APP_NAME} --network {NETWORK} \\
    -v {APP_VOLUME}:/var/www/html \\
    -e WORDPRESS_DB_HOST={DB_NAME} \\
    -e WORDPRESS_DB_NAME={STACK_DB['name']} \\
    -e WORDPRESS_DB_USER={STACK_DB['user']} \\
    -e WORDPRESS_DB_PASSWORD={STACK_DB['password']} \\
    {IMG_WORDPRESS}

podman run -d --name {FRONTEND_NAME} --network {NETWORK} \\
    -p {PORT}:80 {IMG_FRONTEND}

Come si scopre a chi inoltra il frontend:
  podman image inspect {IMG_FRONTEND} --format '{{{{.Config.Env}}}}'
  -> ACME_APP_HOST=acme-app: l'app deve chiamarsi cosi' (oppure si passa
     -e ACME_APP_HOST=<nome> al frontend).
Ordine: db -> app -> frontend. Se il frontend parte prima dell'app, nginx
esce con "host not found in upstream" (podman logs {FRONTEND_NAME}).

Le porte si pubblicano SOLO sul frontend: db e app parlano tra loro
sulla rete {NETWORK}, risolvendosi per nome container.

Variante con podman-compose (compose.yaml), stesso risultato:

  services:
    db:
      container_name: {DB_NAME}
      image: {IMG_MYSQL}
      environment:
        MYSQL_ROOT_PASSWORD: {ROOT_PASSWORD}
        MYSQL_DATABASE: {STACK_DB['name']}
        MYSQL_USER: {STACK_DB['user']}
        MYSQL_PASSWORD: {STACK_DB['password']}
      volumes: [ "{DB_VOLUME}:/var/lib/mysql" ]
      networks: [ {NETWORK} ]
    app:
      container_name: {APP_NAME}
      image: {IMG_WORDPRESS}
      environment:
        WORDPRESS_DB_HOST: {DB_NAME}
        WORDPRESS_DB_NAME: {STACK_DB['name']}
        WORDPRESS_DB_USER: {STACK_DB['user']}
        WORDPRESS_DB_PASSWORD: {STACK_DB['password']}
      volumes: [ "{APP_VOLUME}:/var/www/html" ]
      networks: [ {NETWORK} ]
      depends_on: [ db ]
    frontend:
      container_name: {FRONTEND_NAME}
      image: {IMG_FRONTEND}
      ports: [ "{PORT}:80" ]
      networks: [ {NETWORK} ]
      depends_on: [ app ]
  networks:
    {NETWORK}: {{ name: {NETWORK} }}
  volumes:
    {DB_VOLUME}: {{ name: {DB_VOLUME} }}
    {APP_VOLUME}: {{ name: {APP_VOLUME} }}

  podman-compose up -d

Verifica:
  curl -sI localhost:{PORT}     (302 verso wp-admin/install.php)
"""

CHAPTER = "Try exam"
TITLE = "5) Stack mysql + WordPress + frontend nginx"
PROJECT = None


def setup():
    cleanup()
    ensure_images(IMG_MYSQL, IMG_WORDPRESS, IMG_FRONTEND)


def grade():
    check_networks_exist(NETWORK)
    check_volumes_exist(DB_VOLUME, APP_VOLUME)

    check_container_basics(DB_NAME, IMG_MYSQL)
    check_network_member(DB_NAME, NETWORK)
    check_volume_mount(DB_NAME, DB_VOLUME, "/var/lib/mysql")

    with GradingStep(f"{DB_NAME}: l'utente {STACK_DB['user']} accede al database {STACK_DB['name']}") as step:
        if not container_is_running(DB_NAME):
            step.fail("Container non in esecuzione")
        else:
            result = podman_exec(
                DB_NAME, "mysql", f"-u{STACK_DB['user']}", f"-p{STACK_DB['password']}",
                "-h", "127.0.0.1", STACK_DB["name"], "-e", "SELECT 1",
            )
            if result.returncode != 0:
                step.add_error((result.stderr or "accesso fallito").strip().splitlines()[-1])

    check_container_basics(APP_NAME, IMG_WORDPRESS)
    check_network_member(APP_NAME, NETWORK)
    check_volume_mount(APP_NAME, APP_VOLUME, "/var/www/html")

    check_container_basics(FRONTEND_NAME, IMG_FRONTEND)
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
