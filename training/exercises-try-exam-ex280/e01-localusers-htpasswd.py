"""
Try-exam EX280, 1 — aggiungere utenti al secret HTPasswd esistente
(tema: "CONFIGURE IDENTITY PROVIDER", punti 1-2).

setup() toglie dba/tester dal secret localusers se un giro precedente li
aveva lasciati, e si annota gli utenti gia' presenti: il check "gli utenti
esistenti funzionano ancora" coglie l'errore piu' tipico, `htpasswd -c`
(ricrea il file da zero e cancella admin/developer).

cleanup() NON rimuove dba/tester: servono all'es. 3 (deploy come utente
dba) e sono innocui per le altre tracce; li toglie solo il prossimo setup()
di questo esercizio.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex280_common import (
    CHAPTER, SETUP_TIMEOUT, LOCALUSERS, CONFIG_NS, GradingStep, track_lock,
    require_cluster_admin, read_htpasswd, write_htpasswd, check_htpasswd_users,
    oauth_identity_providers, check_authentication_operator_settled,
    save_state, load_state, run_cli,
)

SLUG = "e01"
USERS = ["dba", "tester"]
PASSWORD = "redhat"

TITLE = "1) Utenti dba e tester nell'identity provider HTPasswd"
PROJECT = None

TASK = f"""\
Il cluster usa un identity provider HTPasswd, i cui utenti sono nel
secret {LOCALUSERS} del progetto {CONFIG_NS}.

  - Aggiungi a quel secret gli utenti {' e '.join(USERS)}, entrambi con
    password {PASSWORD}.
  - Gli utenti gia' esistenti (admin, developer, ...) devono continuare
    a poter fare login.
  - Verifica che {USERS[0]} riesca a fare login sul cluster.

Puoi lavorare da CLI o dalla web console (Workloads -> Secrets).
"""

SOLUTION = f"""\
oc login -u admin -p redhatocp https://api.lab.example.com:6443

oc extract secret/{LOCALUSERS} -n {CONFIG_NS} --to /tmp/ --confirm
htpasswd -bB /tmp/htpasswd dba {PASSWORD}       # NIENTE -c: cancellerebbe gli altri utenti
htpasswd -bB /tmp/htpasswd tester {PASSWORD}
oc set data secret/{LOCALUSERS} -n {CONFIG_NS} --from-file htpasswd=/tmp/htpasswd

# l'operatore ridistribuisce i pod di oauth: attendi che siano nuovi e Running
watch oc get pods -n openshift-authentication

oc login -u dba -p {PASSWORD}
oc login -u admin -p redhatocp

Dalla web console: progetto {CONFIG_NS} -> Secrets -> {LOCALUSERS} ->
Edit Secret, e aggiungi in fondo le righe generate con
  htpasswd -nbB tester {PASSWORD}
"""


def setup():
    require_cluster_admin()
    with track_lock():
        entries = read_htpasswd(LOCALUSERS)
        if entries is None:
            raise RuntimeError(f"secret {LOCALUSERS} non trovato in {CONFIG_NS}")
        if any(u in entries for u in USERS):
            write_htpasswd(LOCALUSERS, {u: h for u, h in entries.items() if u not in USERS})
        save_state(SLUG, "preexisting", sorted(u for u in entries if u not in USERS))


def grade():
    entries = check_htpasswd_users(LOCALUSERS, USERS, PASSWORD)

    with GradingStep("Gli utenti preesistenti sono ancora nel secret") as step:
        before = load_state(SLUG, "preexisting", [])
        missing = [u for u in before if u not in (entries or {})]
        if entries is None:
            step.fail("Secret non trovato")
        elif missing:
            step.add_error(f"utenti spariti: {missing} (htpasswd -c?)")

    with GradingStep(f"L'identity provider usa ancora il secret {LOCALUSERS}") as step:
        idps = oauth_identity_providers()
        if not any((i.get("htpasswd") or {}).get("fileData", {}).get("name") == LOCALUSERS for i in idps):
            step.add_error(f"nessun identity provider HTPasswd punta a {LOCALUSERS}")

    check_authentication_operator_settled()


def cleanup():
    pass


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
