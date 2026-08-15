#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato auth-providers (DO280), sprovvisto
di `lab grade` ufficiale (la classe AuthProviders implementa solo
start()/finish(), non grade() - vedi do280/auth-providers.py).

A differenza degli esercizi DO180, qui la risorsa chiave non e' un progetto
applicativo ma OAuth/cluster (cluster-scoped): l'esercizio chiede di
aggiungere un identity provider HTPasswd che referenzia un Secret in
openshift-config. Il namespace nominale "auth-providers" (self.__LAB__)
viene creato e distrutto solo come sotto-passo dimostrativo (punto 6/9 della
guida) e non e' l'oggetto da gradare.

Specifica dedotta, in ordine di fonte:
1. Diff tra materials/labs/auth-providers/oauth.yaml e
   materials/solutions/auth-providers/oauth.yaml: la sola differenza e' un
   nuovo elemento in spec.identityProviders:
     - htpasswd.fileData.name: localusers
       mappingMethod: claim
       name: myusers
       type: HTPasswd
   (il provider LDAP preesistente non va toccato).
2. Guida studente (auth-providers.pdf.txt): conferma "myusers" come nome
   dell'IDP e "localusers" come Secret in openshift-config; al punto 1
   chiede di creare nel file htpasswd due utenti, new_admin e
   new_developer, poi al punto 2.3 di assegnare cluster-admin a new_admin.
   L'utente "manager" (punto 5) e le sue rimozioni successive (punti 8-9)
   sono passi dimostrativi intermedi dell'esercizio, non lo stato finale
   atteso: li ignoriamo.
3. do280/common/ocp/steps.py: delete_htpasswd_steps() (usato sia in start()
   che in finish()) rimuove secret/ruolo/IDP e ripristina oauth.yaml allo
   stato di partenza (solo LDAP) -> conferma che lo stato "arricchito" da
   gradare e' quello di solutions/oauth.yaml, non quello successivo alla
   pulizia manuale del punto 9 della guida (che precede comunque `lab
   finish`, il quale pulirebbe tutto di nuovo indipendentemente).

Non verifichiamo l'esistenza del progetto "auth-providers" (nome passato da
CLI per coerenza con gli altri script, ma non usato: qui non c'e' nulla di
namespaced da controllare) ne' le password in chiaro (il Secret contiene
solo hash bcrypt, irreversibili): verifichiamo pero' che gli username
new_admin/new_developer compaiano nel file htpasswd dentro il Secret,
perche' il contenuto del file (a differenza della password) non e' cifrato,
solo base64-encoded come qualunque dato di un Secret Kubernetes.

Uso: auth-providers.py [nome-progetto]   (default: auth-providers, non usato)
"""

import base64
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

LAB_NAME = "auth-providers"
EXPECTED_IDP_NAME = "myusers"
EXPECTED_SECRET_NAME = "localusers"
EXPECTED_SECRET_NAMESPACE = "openshift-config"
EXPECTED_MAPPING_METHOD = "claim"
EXPECTED_USERS = ("new_admin", "new_developer")


def find_htpasswd_idp(oauth):
    """Ritorna il primo identityProvider di tipo HTPasswd nell'OAuth
    cluster, o None se non presente."""
    providers = oauth.get("spec", {}).get("identityProviders", []) or []
    for idp in providers:
        if idp.get("type") == "HTPasswd":
            return idp
    return None


def main():
    # Il nome progetto e' accettato solo per coerenza di interfaccia con gli
    # altri script custom: questo esercizio gradua una risorsa cluster-scoped
    # (OAuth/cluster), non un progetto namespaced.
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (risorsa cluster-scoped OAuth/cluster)")

    oauth = oc_get_json("oauth", "cluster")

    with GradingStep("La risorsa OAuth/cluster esiste ed e' leggibile") as step:
        if oauth is None:
            step.fail("Impossibile leggere 'oc get oauth cluster -o json'")

    htpasswd_idp = None
    if oauth is not None:
        htpasswd_idp = find_htpasswd_idp(oauth)

    with GradingStep(
        f"E' configurato un identity provider HTPasswd di nome '{EXPECTED_IDP_NAME}'"
    ) as step:
        if oauth is None:
            step.fail()
        elif htpasswd_idp is None:
            step.fail(
                "Nessun identityProvider di tipo HTPasswd trovato in "
                "spec.identityProviders (oltre a quello LDAP esistente)"
            )
        else:
            if htpasswd_idp.get("name") != EXPECTED_IDP_NAME:
                step.add_error(
                    f"Il name dell'identity provider deve essere "
                    f"'{EXPECTED_IDP_NAME}' (trovato: {htpasswd_idp.get('name')})"
                )
            if htpasswd_idp.get("mappingMethod") != EXPECTED_MAPPING_METHOD:
                step.add_error(
                    f"mappingMethod deve essere '{EXPECTED_MAPPING_METHOD}' "
                    f"(trovato: {htpasswd_idp.get('mappingMethod')})"
                )
            secret_ref = (
                htpasswd_idp.get("htpasswd", {}).get("fileData", {}).get("name")
            )
            if secret_ref != EXPECTED_SECRET_NAME:
                step.add_error(
                    f"htpasswd.fileData.name deve essere "
                    f"'{EXPECTED_SECRET_NAME}' (trovato: {secret_ref})"
                )

    secret = oc_get_json(
        "secret", EXPECTED_SECRET_NAME, "-n", EXPECTED_SECRET_NAMESPACE
    )

    with GradingStep(
        f"Il Secret '{EXPECTED_SECRET_NAME}' esiste in "
        f"{EXPECTED_SECRET_NAMESPACE} e contiene il file htpasswd"
    ) as step:
        if secret is None:
            step.fail(
                f"Secret '{EXPECTED_SECRET_NAME}' non trovato nel namespace "
                f"'{EXPECTED_SECRET_NAMESPACE}'"
            )
        elif "htpasswd" not in (secret.get("data") or {}):
            step.add_error(
                "Il Secret non contiene una chiave 'htpasswd' "
                "(atteso da 'oc create secret generic ... --from-file htpasswd=...')"
            )

    with GradingStep(
        f"Il file htpasswd nel Secret include gli utenti "
        f"{', '.join(EXPECTED_USERS)}"
    ) as step:
        if secret is None or "htpasswd" not in (secret.get("data") or {}):
            step.fail()
        else:
            try:
                content = base64.b64decode(secret["data"]["htpasswd"]).decode(
                    "utf-8", errors="replace"
                )
            except Exception as exc:
                step.fail(f"Impossibile decodificare il contenuto del Secret: {exc}")
                content = ""
            for user in EXPECTED_USERS:
                # riga tipo "new_admin:$2y$05$..." - verifichiamo solo che
                # l'utente sia presente, non la password (hash irreversibile)
                if not re.search(rf"^{re.escape(user)}:", content, re.MULTILINE):
                    step.add_error(
                        f"Nessuna voce per l'utente '{user}' nel file htpasswd "
                        "del Secret"
                    )

    clusterrolebindings = oc_get_json("clusterrolebinding")

    with GradingStep(
        "L'utente new_admin ha il ruolo cluster-admin"
    ) as step:
        if not clusterrolebindings:
            step.fail("Impossibile elencare le ClusterRoleBinding")
        else:
            found = False
            for crb in clusterrolebindings.get("items", []):
                if crb.get("roleRef", {}).get("name") != "cluster-admin":
                    continue
                subjects = crb.get("subjects") or []
                if any(
                    s.get("kind") == "User" and s.get("name") == "new_admin"
                    for s in subjects
                ):
                    found = True
                    break
            if not found:
                step.add_error(
                    "Nessuna ClusterRoleBinding assegna il ruolo cluster-admin "
                    "all'utente new_admin (vedi 'oc adm policy "
                    "add-cluster-role-to-user cluster-admin new_admin')"
                )


if __name__ == "__main__":
    main()
