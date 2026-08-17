#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato auth-conflict (DO380, Cap. 1.9
"Solve User Sync Conflicts"), sprovvisto di `lab grade` ufficiale.

L'esercizio parte da una risorsa OAuth cluster-scoped con tre IdP (LDAP,
htpasswd_provider, RHSSO_OIDC) tutti con mappingMethod "claim": due IdP che
rivendicano lo stesso utente (abbyquincy) in "claim" generano un errore di
autenticazione. La guida chiede di impostare mappingMethod: add per gli IdP
htpasswd_provider e RHSSO_OIDC (l'IdP LDAP "Red Hat Identity Management"
resta "claim" ed e' incidentale: non viene toccato dallo studente).

Specifica confermata sia dal diff materials/labs vs materials/solutions
(oauth_config.yml) sia dal testo della guida (Cap. 1.9, punto 3.1).

La risorsa OAuth e' cluster-scoped (non esiste un progetto da gradare): il
progetto 'auth-conflict' creato da `lab start` contiene solo i materiali di
lavoro (oauth_config.yml da editare), non viene gradato.

Uso: auth-conflict.py [nome-esercizio]   (default: auth-conflict; l'argomento
non e' usato nei controlli, presente solo per coerenza con gli altri script)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

LAB_NAME = "auth-conflict"

IDP_ADD_REQUIRED = ("htpasswd_provider", "RHSSO_OIDC")


def find_idp(providers, name):
    for idp in providers:
        if idp.get("name") == name:
            return idp
    return None


def main():
    # Primo argomento accettato solo per coerenza con gli altri script del
    # repo (il wrapper lo passa comunque): qui non esiste un progetto da
    # verificare, la risorsa gradata (OAuth) e' cluster-scoped.
    sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    oauth = oc_get_json("oauth", "cluster")
    providers = []

    with GradingStep("La risorsa OAuth cluster e' presente e leggibile") as step:
        if oauth is None:
            step.fail("Risorsa 'oauth/cluster' non trovata o non leggibile")
        else:
            providers = oauth.get("spec", {}).get("identityProviders", [])
            if not providers:
                step.fail("La risorsa OAuth non definisce identityProviders")

    for idp_name in IDP_ADD_REQUIRED:
        with GradingStep(
            f"L'IdP {idp_name} usa mappingMethod: add"
        ) as step:
            idp = find_idp(providers, idp_name)
            if idp is None:
                step.fail(f"IdP '{idp_name}' non trovato nella risorsa OAuth")
            elif idp.get("mappingMethod") != "add":
                step.add_error(
                    f"mappingMethod e' '{idp.get('mappingMethod')}', atteso 'add'"
                )


if __name__ == "__main__":
    main()
