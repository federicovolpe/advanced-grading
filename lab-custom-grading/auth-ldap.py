#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato auth-ldap (DO380, Cap. 1.4
"Configure LDAP Authentication"), sprovvisto di `lab grade` ufficiale (la
classe AuthLdap nel pacchetto do380 implementa solo start()/finish()).

L'esercizio non usa un progetto OpenShift come stato gradabile: chiede di
AGGIUNGERE un secondo identity provider LDAP (oltre a quello IdM già
preesistente in cluster, vedi Introduzione della guida) alla risorsa
cluster-scoped OAuth/cluster, puntando al server RHDS (rhds.ocp4.example.com).

Valori attesi presi dal testo della guida (Cap. 1.4, passi 5.1-5.4):
- Name: "Red Hat Directory Server"
- URL: ldaps://rhds.ocp4.example.com/dc=example,dc=com?uid
- Bind DN: cn=Directory Manager
- mappingMethod: claim (default, non esplicitamente cambiato)
- email attribute: mail (unico campo attributi impostato esplicitamente nel
  form; id/name/preferredUsername non sono menzionati nella guida, quindi
  non li gradiamo per non inventare valori non richiesti esplicitamente)

Il nome del Secret con la bind password e della ConfigMap con la CA sono
generati automaticamente dalla web console con un nome casuale: non sono
deducibili in anticipo, quindi il grading li risolve seguendo i riferimenti
bindPassword.name/ca.name dentro la entry LDAP, invece di assumere un nome
fisso (stesso pattern di storage-configs.py/storage-volumes.py in DO180).
La bind password non viene decodificata/confrontata in chiaro: verificarne
la sola presenza è sufficiente a confermare che il wizard l'abbia salvata.

Uso: auth-ldap.py [ignorato]  (l'esercizio non ha un progetto associato,
l'argomento è accettato solo per coerenza con lo schema comune)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

EXPECTED_NAME = "Red Hat Directory Server"
EXPECTED_URL = "ldaps://rhds.ocp4.example.com/dc=example,dc=com?uid"
EXPECTED_BIND_DN = "cn=Directory Manager"
PRE_EXISTING_NAME = "Red Hat Identity Management"


def find_idp(oauth, name):
    if oauth is None:
        return None
    providers = oauth.get("spec", {}).get("identityProviders", [])
    for idp in providers:
        if idp.get("name") == name:
            return idp
    return None


def main():
    print("🔧 Grading personalizzato per 'auth-ldap' (risorsa cluster-scoped OAuth/cluster)")

    oauth = oc_get_json("oauth", "cluster")

    with GradingStep("La risorsa OAuth cluster esiste ed e' leggibile") as step:
        if oauth is None:
            step.fail("Impossibile leggere 'oc get oauth cluster'")

    with GradingStep(f"L'identity provider preesistente '{PRE_EXISTING_NAME}' e' ancora presente") as step:
        if oauth is not None and find_idp(oauth, PRE_EXISTING_NAME) is None:
            step.add_error(
                f"L'IdP '{PRE_EXISTING_NAME}' non e' piu' presente: l'esercizio chiede di "
                "AGGIUNGERE un nuovo IdP, non di sostituire quello esistente"
            )

    new_idp = find_idp(oauth, EXPECTED_NAME) if oauth is not None else None

    with GradingStep(f"L'identity provider '{EXPECTED_NAME}' e' stato aggiunto") as step:
        if new_idp is None:
            step.fail(f"Nessun identityProvider con name='{EXPECTED_NAME}' trovato in OAuth/cluster")

    with GradingStep("Il nuovo identity provider e' di tipo LDAP con i parametri corretti") as step:
        if new_idp is None:
            step.fail()
        else:
            if new_idp.get("type") != "LDAP":
                step.add_error(f"type deve essere 'LDAP' (trovato: {new_idp.get('type')})")
            ldap_cfg = new_idp.get("ldap", {})
            if ldap_cfg.get("url") != EXPECTED_URL:
                step.add_error(
                    f"url deve essere '{EXPECTED_URL}' (trovato: {ldap_cfg.get('url')})"
                )
            if ldap_cfg.get("bindDN") != EXPECTED_BIND_DN:
                step.add_error(
                    f"bindDN deve essere '{EXPECTED_BIND_DN}' (trovato: {ldap_cfg.get('bindDN')})"
                )
            email_attrs = ldap_cfg.get("attributes", {}).get("email", [])
            if "mail" not in email_attrs:
                step.add_error(
                    f"attributes.email deve includere 'mail' (trovato: {email_attrs})"
                )
            if not ldap_cfg.get("bindPassword", {}).get("name"):
                step.add_error("bindPassword.name non e' impostato (nessun Secret referenziato)")
            if not ldap_cfg.get("ca", {}).get("name"):
                step.add_error("ca.name non e' impostato (nessuna ConfigMap con la CA referenziata)")

    with GradingStep("Il Secret con la bind password esiste in openshift-config") as step:
        if new_idp is None:
            step.fail()
        else:
            secret_name = new_idp.get("ldap", {}).get("bindPassword", {}).get("name")
            if not secret_name:
                step.fail("Nessun Secret referenziato da bindPassword.name")
            elif oc_get_json("secret", secret_name, "-n", "openshift-config") is None:
                step.add_error(f"Secret '{secret_name}' non trovato in openshift-config")

    with GradingStep("La ConfigMap con la CA RHDS esiste in openshift-config") as step:
        if new_idp is None:
            step.fail()
        else:
            cm_name = new_idp.get("ldap", {}).get("ca", {}).get("name")
            if not cm_name:
                step.fail("Nessuna ConfigMap referenziata da ca.name")
            elif oc_get_json("configmap", cm_name, "-n", "openshift-config") is None:
                step.add_error(f"ConfigMap '{cm_name}' non trovata in openshift-config")


if __name__ == "__main__":
    main()
