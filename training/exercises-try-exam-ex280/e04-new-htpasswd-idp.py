"""
Try-exam EX280, 4 — un nuovo identity provider HTPasswd accanto a quello
esistente (tema: "CONFIGURE CLUSTER PERMISSION", parte "Create users").

Il tema annotato usa nomi segnaposto (<name>, identity-name): qui secret e
identity provider hanno nomi fissi per poterli gradare. Gli utenti sono
quelli dell'es. 5 (wozniak, jobs, pippo) piu' pluto, come negli appunti.

cleanup() riporta OAuth com'era (toglie SOLO l'identity provider di questo
esercizio, con un op "test" sul nome per non rimuovere quello sbagliato se
l'ordine e' cambiato nel frattempo), cancella il secret e gli oggetti
User/Identity creati dai login fatti per verifica.
"""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex280_common import (
    CHAPTER, SETUP_TIMEOUT, LOCALUSERS, CONFIG_NS, GradingStep, oc, oc_get_json,
    track_lock, require_cluster_admin, check_htpasswd_users,
    oauth_identity_providers, check_authentication_operator_settled, run_cli,
)

SLUG = "e04"
SECRET = "ex280-userlist"
IDP = "ex280-users"
USERS = ["wozniak", "jobs", "pippo", "pluto"]
PASSWORD = "pass"

TITLE = "4) Nuovo identity provider HTPasswd"
PROJECT = None

TASK = f"""\
  - Crea un file htpasswd con gli utenti {', '.join(USERS)},
    tutti con password {PASSWORD}.
  - Salvalo in un secret {SECRET} nel progetto {CONFIG_NS}.
  - Aggiungi alla configurazione OAuth del cluster un identity provider
    HTPasswd chiamato {IDP} che usa quel secret.
  - L'identity provider esistente ({LOCALUSERS}) deve restare
    configurato e funzionante.
  - Verifica che jobs riesca a fare login.
"""

SOLUTION = f"""\
htpasswd -c -bB /tmp/userlist {USERS[0]} {PASSWORD}     # -c solo per il PRIMO utente
{chr(10).join(f'htpasswd -bB /tmp/userlist {u} {PASSWORD}' for u in USERS[1:])}

oc create secret generic {SECRET} --from-file htpasswd=/tmp/userlist -n {CONFIG_NS}

oc get oauth cluster -o yaml > /tmp/oauth.yaml
# aggiungi in spec.identityProviders, SENZA togliere {LOCALUSERS}:
#   - name: {IDP}
#     mappingMethod: claim
#     type: HTPasswd
#     htpasswd:
#       fileData:
#         name: {SECRET}
oc replace -f /tmp/oauth.yaml

watch oc get pods -n openshift-authentication    # attendi i pod nuovi
oc login -u jobs -p {PASSWORD}
oc login -u admin -p redhatocp
"""


def _remove_idp():
    for i, idp in enumerate(oauth_identity_providers()):
        if idp.get("name") == IDP:
            patch = [
                {"op": "test", "path": f"/spec/identityProviders/{i}/name", "value": IDP},
                {"op": "remove", "path": f"/spec/identityProviders/{i}"},
            ]
            oc("patch", "oauth", "cluster", "--type=json", "-p", json.dumps(patch), check=True)
            return


def _remove_identities():
    identities = (oc_get_json("identity") or {}).get("items", [])
    for ident in identities:
        if ident.get("providerName") != IDP:
            continue
        user = (ident.get("user") or {}).get("name")
        oc("delete", "identity", ident["metadata"]["name"], "--ignore-not-found")
        if not user:
            continue
        # L'oggetto User si toglie solo se non ha identita' di altri provider.
        obj = oc_get_json("user", user)
        others = [i for i in (obj or {}).get("identities") or [] if not i.startswith(f"{IDP}:")]
        if obj and not others:
            oc("delete", "user", user, "--ignore-not-found")


def _reset():
    with track_lock():
        _remove_idp()
        oc("delete", "secret", SECRET, "-n", CONFIG_NS, "--ignore-not-found")
        _remove_identities()


def setup():
    require_cluster_admin()
    _reset()


def grade():
    check_htpasswd_users(SECRET, USERS, PASSWORD)

    idps = oauth_identity_providers()
    with GradingStep(f"OAuth ha l'identity provider HTPasswd {IDP} sul secret {SECRET}") as step:
        idp = next((i for i in idps if i.get("name") == IDP), None)
        if not idp:
            step.fail(f"identity provider '{IDP}' non trovato (presenti: {[i.get('name') for i in idps]})")
        else:
            if idp.get("type") != "HTPasswd":
                step.add_error(f"type = {idp.get('type')!r}")
            if (idp.get("htpasswd") or {}).get("fileData", {}).get("name") != SECRET:
                step.add_error(f"fileData.name = {(idp.get('htpasswd') or {}).get('fileData')!r}")

    with GradingStep(f"L'identity provider {LOCALUSERS} e' ancora configurato") as step:
        if not any((i.get("htpasswd") or {}).get("fileData", {}).get("name") == LOCALUSERS for i in idps):
            step.add_error(f"nessun identity provider punta piu' al secret {LOCALUSERS}")

    check_authentication_operator_settled()


def cleanup():
    _reset()


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
