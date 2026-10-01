"""
Utilita' condivise dalla traccia "try-exam" (simulazione d'esame DO188,
stato Podman locale). Il file inizia con '_' cosi' training_monitor.py non
lo carica come esercizio.

Le immagini del tema (oci-registry:5000/...) vivono su un registry che
esiste solo nell'ambiente d'esame: qui le ricreiamo in LOCALE con gli
stessi identici nomi (podman tag / podman build partendo dalle immagini
ufficiali docker.io), cosi' lo studente digita gli stessi comandi
dell'esame e `podman run` le trova in locale senza tentare il pull
(pull policy di default: "missing").
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (  # noqa: E402,F401
    GradingStep, podman, podman_reset, podman_container, podman_image,
    container_is_running, container_port_mappings, container_mounts,
    container_networks, container_env, podman_exec, podman_logs,
    podman_network_exists, podman_volume_exists, podman_attached_clients,
    http_get, run_cli,
)

# I file di partenza dello studente (nel tema: "/home/.../...").
BASE_DIR = os.path.expanduser("~/try-exam")

# Il pull di wordpress/mariadb al primo setup puo' superare i 180s di
# default del monitor (vedi SETUP_TIMEOUT in training_monitor.py).
SETUP_TIMEOUT = 900

UPSTREAM_NGINX = "docker.io/library/nginx:latest"
UPSTREAM_MARIADB = "docker.io/library/mariadb:latest"
UPSTREAM_WORDPRESS = "docker.io/library/wordpress:latest"

IMG_NGINX = "oci-registry:5000/nginx:latest"
IMG_NGINX_ACME = "oci-registry:5000/nginx:acme"
IMG_WP_BACKEND = "oci-registry:5000/acme:wp-backend"
IMG_WP_BACKEND_BROKEN = "oci-registry:5000/acme:wp-backend-broken"
IMG_WP_APP_BROKEN = "oci-registry:5000/acme:wp-app-broken"

# Credenziali "cotte" nelle immagini wp-*: devono combaciare tra backend e
# app, ed e' proprio questo che rende l'es. 6 risolvibile senza indovinare.
WP_DB_ENV = {
    "MARIADB_DATABASE": "wordpress",
    "MARIADB_USER": "wordpress",
    "MARIADB_PASSWORD": "acme-wp-pass",
}

_BUILDS = {
    # nginx che risponde con $WELCOME_MESSAGE: l'entrypoint ufficiale passa
    # /etc/nginx/templates/*.template da envsubst all'avvio. Il default
    # serve perche' una variabile non definita resterebbe "${...}" nel
    # file e nginx rifiuterebbe di partire (variabile nginx sconosciuta).
    # listen [::]:80 serve davvero: "localhost" risolve prima a ::1 e il
    # port forwarding rootless (pasta) lo inoltra a ::1 nel container,
    # dove senza listener la connessione viene resettata (visto dal vivo).
    IMG_NGINX_ACME: {
        "Containerfile": f"""\
FROM {UPSTREAM_NGINX}
ENV WELCOME_MESSAGE="ACME nginx"
COPY default.conf.template /etc/nginx/templates/default.conf.template
""",
        "default.conf.template": """\
server {
    listen 80;
    listen [::]:80;
    location / {
        default_type text/plain;
        return 200 "${WELCOME_MESSAGE}\\n";
    }
}
""",
    },
    IMG_WP_BACKEND: {
        "Containerfile": f"""\
FROM {UPSTREAM_MARIADB}
ENV MARIADB_ROOT_PASSWORD=acme-root \\
    MARIADB_DATABASE={WP_DB_ENV['MARIADB_DATABASE']} \\
    MARIADB_USER={WP_DB_ENV['MARIADB_USER']} \\
    MARIADB_PASSWORD={WP_DB_ENV['MARIADB_PASSWORD']}
""",
    },
    # Guasto 1 (es. 6): manca la password di root -> l'entrypoint mariadb
    # esce subito, il motivo si legge in `podman logs`.
    IMG_WP_BACKEND_BROKEN: {
        "Containerfile": f"""\
FROM {UPSTREAM_MARIADB}
ENV MARIADB_DATABASE={WP_DB_ENV['MARIADB_DATABASE']} \\
    MARIADB_USER={WP_DB_ENV['MARIADB_USER']} \\
    MARIADB_PASSWORD={WP_DB_ENV['MARIADB_PASSWORD']}
""",
    },
    # Guasto 2 (es. 6): l'host del DB punta al container dell'es. 5, che non
    # e' sulla rete acme-troubles -> "Error establishing a database connection".
    IMG_WP_APP_BROKEN: {
        "Containerfile": f"""\
FROM {UPSTREAM_WORDPRESS}
ENV WORDPRESS_DB_HOST=acme-wp-backend \\
    WORDPRESS_DB_NAME={WP_DB_ENV['MARIADB_DATABASE']} \\
    WORDPRESS_DB_USER={WP_DB_ENV['MARIADB_USER']} \\
    WORDPRESS_DB_PASSWORD={WP_DB_ENV['MARIADB_PASSWORD']}
""",
    },
}


def image_exists(name):
    return subprocess.run(["podman", "image", "exists", name]).returncode == 0


def ensure_upstream(ref):
    if not image_exists(ref):
        podman("pull", "-q", ref, check=True)


def ensure_images(*names):
    """Crea (solo se mancano) le immagini locali con i nomi del tema.
    Non vengono mai rimosse dai cleanup(): sono costose da ricreare e non
    fanno parte di cio' che lo studente deve produrre."""
    for name in names:
        if image_exists(name):
            continue
        if name == IMG_NGINX:
            ensure_upstream(UPSTREAM_NGINX)
            podman("tag", UPSTREAM_NGINX, IMG_NGINX, check=True)
            continue
        files = _BUILDS[name]
        for line in files["Containerfile"].splitlines():
            if line.startswith("FROM "):
                ensure_upstream(line.split()[1])
        with tempfile.TemporaryDirectory() as ctx:
            for fname, content in files.items():
                with open(os.path.join(ctx, fname), "w") as fh:
                    fh.write(content)
            podman("build", "-q", "-t", name, ctx, check=True)


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


def check_container_basics(name, image, step_prefix=""):
    """I tre check comuni a quasi tutti gli esercizi: esiste, usa
    l'immagine giusta, e' in esecuzione staccato dalla CLI. Ritorna il dict
    inspect (o None) per i check successivi."""
    c = podman_container(name)
    with GradingStep(f"{step_prefix}Il container {name} esiste") as step:
        if not c:
            step.fail(f"Container '{name}' non trovato")

    with GradingStep(f"{step_prefix}{name} usa l'immagine {image}") as step:
        if not c:
            step.fail("Container non trovato")
        elif image not in (c.get("ImageName") or ""):
            step.add_error(f"immagine effettiva: {c.get('ImageName')!r}")

    with GradingStep(f"{step_prefix}{name} e' in esecuzione, staccato dalla CLI") as step:
        if not container_is_running(name):
            state = ((c or {}).get("State") or {}).get("Status")
            step.fail(f"Container non in esecuzione (stato: {state})")
        else:
            for cmd in podman_attached_clients(name):
                step.add_error(f"terminale ancora agganciato: {cmd}")
    return c


def check_port(name, host_port, container_port="80/tcp"):
    with GradingStep(f"{name}: porta {container_port.split('/')[0]} pubblicata sull'host come {host_port}") as step:
        host_ports = container_port_mappings(name).get(container_port, [])
        if str(host_port) not in host_ports:
            step.add_error(f"porte pubblicate per {container_port}: {host_ports}")


def check_network_member(name, network):
    with GradingStep(f"{name} e' collegato alla rete {network}") as step:
        nets = container_networks(name)
        if network not in nets:
            step.add_error(f"reti del container: {sorted(nets) or 'nessuna'}")


def check_volume_mount(name, volume, destination):
    with GradingStep(f"{name}: volume {volume} montato su {destination}") as step:
        mounts = container_mounts(name)
        if not any(m.get("Type") == "volume" and m.get("Name") == volume
                   and m.get("Destination") == destination for m in mounts):
            found = [f"{m.get('Name') or m.get('Source')} -> {m.get('Destination')}" for m in mounts]
            step.add_error(f"mount trovati: {found or 'nessuno'}")


def check_networks_exist(*names):
    for net in names:
        with GradingStep(f"La rete {net} esiste") as step:
            if not podman_network_exists(net):
                step.fail(f"Rete '{net}' non trovata")


def check_volumes_exist(*names):
    for vol in names:
        with GradingStep(f"Il volume {vol} esiste") as step:
            if not podman_volume_exists(vol):
                step.fail(f"Volume '{vol}' non trovato")
