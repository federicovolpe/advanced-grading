"""
Try-exam 3 — due container dalla stessa immagine, configurati via env.
Il tema annotato chiedeva 8080:80 per entrambi E che coesistessero, cosa
impossibile (la porta host e' una sola): lo scopo era averli attivi
insieme, quindi il secondo usa 8081. Il grading verifica anche che
ognuno risponda col proprio WELCOME_MESSAGE (l'immagine nginx:acme lo
restituisce come corpo della pagina).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _exam_common import (
    IMG_NGINX_ACME, SETUP_TIMEOUT, GradingStep, podman_reset, container_env,
    http_get, ensure_images, check_container_basics, check_port, run_cli,
)

CONTAINERS = [
    ("acme-demo-runtime_1", "ACME_Container_1", 8080),
    ("acme-demo-runtime_2", "ACME_Container_2", 8081),
]
NAMES = [n for n, _, _ in CONTAINERS]

TASK = f"""\
Crea 2 container con l'immagine {IMG_NGINX_ACME}:
  - i nomi devono essere {NAMES[0]} e {NAMES[1]}
  - a {NAMES[0]} passa la variabile d'ambiente
      WELCOME_MESSAGE = {CONTAINERS[0][1]}
  - a {NAMES[1]} passa la variabile d'ambiente
      WELCOME_MESSAGE = {CONTAINERS[1][1]}
  - la porta 80 di {NAMES[0]} deve essere mappata sulla porta {CONTAINERS[0][2]}
    dell'host, quella di {NAMES[1]} sulla porta {CONTAINERS[1][2]}
  - i container devono essere staccati dalla command line
  - i container devono essere in esecuzione contemporaneamente
"""

SOLUTION = f"""\
podman run -d --name {NAMES[0]} -e WELCOME_MESSAGE={CONTAINERS[0][1]} \\
    -p {CONTAINERS[0][2]}:80 {IMG_NGINX_ACME}
podman run -d --name {NAMES[1]} -e WELCOME_MESSAGE={CONTAINERS[1][1]} \\
    -p {CONTAINERS[1][2]}:80 {IMG_NGINX_ACME}

Due container non possono pubblicare la stessa porta dell'host: per farli
coesistere ognuno usa una porta host diversa.

Verifica:
  curl localhost:{CONTAINERS[0][2]}
  curl localhost:{CONTAINERS[1][2]}
"""

CHAPTER = "Try exam"
TITLE = "3) Due container con variabili d'ambiente"
PROJECT = None


def setup():
    podman_reset(containers=NAMES)
    ensure_images(IMG_NGINX_ACME)


def grade():
    for name, message, port in CONTAINERS:
        check_container_basics(name, IMG_NGINX_ACME)

        with GradingStep(f"{name}: WELCOME_MESSAGE={message}") as step:
            value = container_env(name).get("WELCOME_MESSAGE")
            if value != message:
                step.add_error(f"valore trovato: {value!r}")

        check_port(name, port)

        with GradingStep(f"localhost:{port} risponde con {message}") as step:
            ok, body = http_get(f"http://localhost:{port}/")
            if not ok:
                step.add_error(f"nessuna risposta valida da localhost:{port}")
            elif body.strip() != message:
                step.add_error(f"risposta: {body.strip()!r}")


def cleanup():
    podman_reset(containers=NAMES)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
