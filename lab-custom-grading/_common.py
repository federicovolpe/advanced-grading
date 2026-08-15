"""
Utilita' condivise per gli script di grading "custom" (esercizi DO180 sprovvisti
di un `lab grade` ufficiale). Il formato di stampa (PASS/FAIL <titolo> seguito
da dettagli indentati di 8 spazi) e' compatibile con il parser di
~/.local/bin/lab_grade_monitor.py, cosi' i semafori funzionano anche qui.
"""

import json
import subprocess


class GradingStep:
    """Riproduce grossolanamente labs.ui.GradingStep usato nei grading
    ufficiali Red Hat Training (vedi do180/reliability-review.py): un check
    e' FAIL se viene chiamato add_error()/fail() al suo interno, altrimenti
    e' PASS."""

    def __init__(self, title):
        self.title = title
        self.errors = []
        self.failed = False

    def add_error(self, message):
        self.errors.append(message)

    def fail(self, message=None):
        self.failed = True
        if message:
            self.errors.append(message)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        status = "FAIL" if (self.failed or self.errors) else "PASS"
        print(f"{status} {self.title}")
        for e in self.errors:
            print(f"        - {e}")
        return False


def oc_get_json(*args):
    """Esegue `oc get <args> -o json` e ritorna il dict, o None se la
    risorsa non esiste o il comando fallisce."""
    result = subprocess.run(
        ["oc", "get", *args, "-o", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def project_exists(name):
    result = subprocess.run(["oc", "get", "project", name], capture_output=True)
    return result.returncode == 0


# --- Helper per corsi RHCSA (RH124/RH134): niente OpenShift, i controlli
# girano su workstation o su un host remoto (servera/serverb) raggiungibile
# via SSH senza password, come nei grading ufficiali (labs.common.commands).


def run(command, host="workstation", sudo=False):
    """Esegue un comando su workstation (subprocess locale) o su un host
    remoto della classroom (via `ssh`, chiavi già configurate dal corso).
    Ritorna un subprocess.CompletedProcess (stdout/stderr come str).

    sudo=True usa la password standard della classroom ("student", la
    stessa indicata nelle guide ufficiali RH124/RH134), perché l'utente
    student non ha sudo passwordless su servera/serverb."""
    if sudo:
        command = f"echo student | sudo -S -p '' {command}"
    if host in ("workstation", "localhost", None):
        return subprocess.run(
            ["bash", "-c", command], capture_output=True, text=True
        )
    return subprocess.run(
        ["ssh", host, command], capture_output=True, text=True
    )


def command_ok(command, host="workstation", sudo=False):
    """True se il comando esce con codice 0."""
    return run(command, host=host, sudo=sudo).returncode == 0


def user_exists(username, host="workstation"):
    return command_ok(f"getent passwd {username}", host=host)


def group_exists(groupname, host="workstation"):
    return command_ok(f"getent group {groupname}", host=host)


def package_installed(package, host="workstation"):
    return command_ok(f"rpm -q {package}", host=host)


def service_is_active(service, host="workstation"):
    return command_ok(f"systemctl is-active --quiet {service}", host=host)


def service_is_enabled(service, host="workstation"):
    return command_ok(f"systemctl is-enabled --quiet {service}", host=host)


def file_exists(path, host="workstation", sudo=False):
    return command_ok(f"test -e {path}", host=host, sudo=sudo)


def password_matches(username, plaintext, host="workstation"):
    """Confronta la password di un utente locale con un valore atteso,
    senza mai stamparla: legge l'hash da /etc/shadow (serve sudo) e lo
    confronta ricalcolando l'hash con lo stesso salt via `crypt`."""
    import crypt

    result = run(f"getent shadow {username}", host=host, sudo=True)
    if result.returncode != 0:
        return False
    fields = result.stdout.strip().split(":")
    if len(fields) < 2:
        return False
    stored_hash = fields[1]
    if not stored_hash or stored_hash in ("!", "*", "!!", "!!*"):
        return False
    return crypt.crypt(plaintext, stored_hash) == stored_hash
