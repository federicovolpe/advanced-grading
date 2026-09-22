"""
Cap. 2 — Podman Basics: Container Networking Basics / Accessing
Containerized Network Services.
Crea una rete Podman dedicata e collega due container, verificando che si
raggiungano per nome (risoluzione DNS automatica sulle reti utente).

Nota: in Podman rootless (rootlessNetworkCmd=pasta, di default su questa
workstation) l'IP di un container su una rete bridge utente NON e'
raggiungibile direttamente dall'host — solo da altri container sulla stessa
rete. Verificato dal vivo prima di scrivere questo esercizio: un primo
tentativo che curlava l'IP del container dall'host falliva sempre (000),
mentre un container che curla l'altro per nome funziona. Per questo il
grading verifica la raggiungibilita' container-to-container, non host-to-
container (per quella vedi c2-01, che usa -p esplicito).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, podman_reset, podman_network_exists, podman_container,
    container_is_running, container_networks, podman_exec, run_cli,
)

IMAGE = "registry.access.redhat.com/ubi9/httpd-24"
NETWORK = "training-net"
NAME_A = "training-net-a"
NAME_B = "training-net-b"

TASK = f"""\
Crea una rete Podman chiamata "{NETWORK}", poi avvia due container su quella
rete: "{NAME_A}" e "{NAME_B}" (entrambi dall'immagine "{IMAGE}"). Verifica che
"{NAME_A}" riesca a raggiungere "{NAME_B}" per NOME (risoluzione DNS
automatica di Podman sulle reti definite dall'utente).

Comandi suggeriti (3):
  podman network create {NETWORK}
  podman run -d --name {NAME_A} --network {NETWORK} {IMAGE}
  podman run -d --name {NAME_B} --network {NETWORK} {IMAGE}
"""

CHAPTER = "Cap. 2 — Podman Basics"
TITLE = "Crea una rete e collega due container"
PROJECT = None


def setup():
    podman_reset(containers=[NAME_A, NAME_B], networks=[NETWORK])


def grade():
    with GradingStep(f"La rete {NETWORK} esiste") as step:
        if not podman_network_exists(NETWORK):
            step.fail(f"Rete '{NETWORK}' non trovata")

    for name in (NAME_A, NAME_B):
        with GradingStep(f"Il container {name} e' in esecuzione sulla rete {NETWORK}") as step:
            if not container_is_running(name):
                step.fail(f"Container '{name}' non trovato o non in esecuzione")
            elif NETWORK not in container_networks(name):
                step.add_error(f"reti collegate: {sorted(container_networks(name))}")

    with GradingStep(f"{NAME_A} raggiunge {NAME_B} per nome sulla porta 8080") as step:
        if not container_is_running(NAME_A) or not container_is_running(NAME_B):
            step.fail("Entrambi i container devono essere in esecuzione")
        else:
            result = podman_exec(
                NAME_A, "curl", "-s", "-o", "/dev/null",
                "-w", "%{http_code}", "--max-time", "5",
                f"http://{NAME_B}:8080/",
            )
            code = (result.stdout or "").strip()
            if result.returncode != 0 or not code.isdigit():
                step.add_error(f"curl da {NAME_A} a {NAME_B} fallita: {result.stderr.strip()}")
            elif code == "000":
                step.add_error(f"nessuna connessione (curl ha risposto {code})")


def cleanup():
    podman_reset(containers=[NAME_A, NAME_B], networks=[NETWORK])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
