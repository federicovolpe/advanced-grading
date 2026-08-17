#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato auth-oidc (DO380, Cap. 1.8
"Configure OIDC Authentication and Group Synchronization"), sprovvisto di
`lab grade` ufficiale (la classe AuthOidc in do380/auth-oidc.py implementa
solo start()/finish(), non grade()).

Come in auth-providers (DO280), la risorsa chiave e' cluster-scoped
(OAuth/cluster), non il progetto "auth-oidc" creato da start().

Specifica dedotta, in ordine di fonte:
1. Diff tra materials/labs/auth-oidc/sso_config.yaml (placeholder
   CHANGE_ME) e materials/solutions/auth-oidc/sso_config.yaml: lo studente
   deve aggiungere un secondo identityProvider di tipo OpenID (preservando
   quello LDAP esistente) con clientID "ocp_rhsso", clientSecret.name
   "rhsso-oidc-client-secret", issuer
   "https://sso.ocp4.example.com:8080/auth/realms/external_providers",
   mappingMethod "claim", name "RHSSO_OIDC", e claims email/name/
   preferredUsername/groups come da manifest.
2. Guida studente (Cap. 1.8, pag. 56-65): conferma gli stessi valori e
   aggiunge un passo RBAC esplicito (punto 1): assegnare il ruolo cluster
   "edit" al gruppo "contractors" e il ruolo cluster "view" al gruppo
   "partners", tramite `oc adm policy add-role-to-group edit contractors`
   e `... view partners` SENZA l'opzione -n. Questi comandi, nonostante il
   testo descriva l'effetto come limitato al progetto "auth-oidc", creano
   in realta' un ClusterRoleBinding (confermato dall'output della guida
   stessa: "clusterrole.rbac.authorization.k8s.io/edit added"), non una
   RoleBinding namespaced: gradiamo quindi un ClusterRoleBinding.
3. do380/auth-oidc.py: conferma che il secret del client OIDC si chiama
   "rhsso-oidc-client-secret" e vive nel namespace "openshift-config".

I gruppi "contractors"/"partners" e la loro membership utente sono creati
automaticamente da OpenShift al primo login (mappingMethod: claim) e
dipendono da quali utenti hanno gia' effettuato l'accesso quando gira il
grading: verifichiamo solo che i gruppi esistano (creati dal comando
add-role-to-group stesso, anche prima di un login) e non la membership
esatta, che e' intermittente e non richiesta esplicitamente allo stato
finale dell'esercizio.

Uso: auth-oidc.py [nome-progetto]   (default: auth-oidc, non usato)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

LAB_NAME = "auth-oidc"

EXPECTED_IDP_NAME = "RHSSO_OIDC"
EXPECTED_CLIENT_ID = "ocp_rhsso"
EXPECTED_SECRET_NAME = "rhsso-oidc-client-secret"
EXPECTED_SECRET_NAMESPACE = "openshift-config"
EXPECTED_ISSUER = "https://sso.ocp4.example.com:8080/auth/realms/external_providers"
EXPECTED_MAPPING_METHOD = "claim"

CONTRACTORS_GROUP = "contractors"
PARTNERS_GROUP = "partners"


def find_openid_idp(oauth):
    """Ritorna il primo identityProvider di tipo OpenID nell'OAuth
    cluster, o None se non presente."""
    providers = oauth.get("spec", {}).get("identityProviders", []) or []
    for idp in providers:
        if idp.get("type") == "OpenID":
            return idp
    return None


def has_ldap_idp(oauth):
    providers = oauth.get("spec", {}).get("identityProviders", []) or []
    return any(idp.get("type") == "LDAP" for idp in providers)


def clusterrolebinding_grants(binding, role, group):
    if binding is None:
        return False
    role_ref = binding.get("roleRef", {})
    if role_ref.get("name") != role:
        return False
    for subject in binding.get("subjects") or []:
        if subject.get("kind") == "Group" and subject.get("name") == group:
            return True
    return False


def find_binding_for_group(bindings, role, group):
    for binding in bindings.get("items", []) or []:
        if clusterrolebinding_grants(binding, role, group):
            return binding
    return None


def main():
    # Il nome progetto e' accettato solo per coerenza di interfaccia con gli
    # altri script custom: questo esercizio gradua risorse cluster-scoped
    # (OAuth/cluster, ClusterRoleBinding, Group), non il progetto namespaced.
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (risorse cluster-scoped)")

    oauth = oc_get_json("oauth", "cluster")

    with GradingStep("L'IdP OpenID RHSSO_OIDC e' configurato in OAuth/cluster") as step:
        if oauth is None:
            step.fail("Risorsa oauth/cluster non trovata")
        else:
            if not has_ldap_idp(oauth):
                step.add_error("L'IdP LDAP preesistente e' stato rimosso (andava preservato)")
            idp = find_openid_idp(oauth)
            if idp is None:
                step.add_error("Nessun identityProvider di tipo OpenID configurato")
            else:
                if idp.get("name") != EXPECTED_IDP_NAME:
                    step.add_error(
                        f"Nome IdP atteso '{EXPECTED_IDP_NAME}' (trovato: {idp.get('name')})"
                    )
                if idp.get("mappingMethod") != EXPECTED_MAPPING_METHOD:
                    step.add_error(
                        f"mappingMethod atteso '{EXPECTED_MAPPING_METHOD}' "
                        f"(trovato: {idp.get('mappingMethod')})"
                    )
                openid = idp.get("openID", {})
                if openid.get("clientID") != EXPECTED_CLIENT_ID:
                    step.add_error(
                        f"clientID atteso '{EXPECTED_CLIENT_ID}' (trovato: {openid.get('clientID')})"
                    )
                if openid.get("clientSecret", {}).get("name") != EXPECTED_SECRET_NAME:
                    step.add_error(
                        f"clientSecret.name atteso '{EXPECTED_SECRET_NAME}' "
                        f"(trovato: {openid.get('clientSecret', {}).get('name')})"
                    )
                issuer = (openid.get("issuer") or "").strip()
                if issuer != EXPECTED_ISSUER:
                    step.add_error(f"issuer atteso '{EXPECTED_ISSUER}' (trovato: '{issuer}')")
                claims = openid.get("claims", {})
                for claim_name, expected_value in (
                    ("email", "email"),
                    ("name", "name"),
                    ("preferredUsername", "preferred_username"),
                    ("groups", "groups"),
                ):
                    values = claims.get(claim_name) or []
                    if expected_value not in values:
                        step.add_error(
                            f"claims.{claim_name} deve includere '{expected_value}' "
                            f"(trovato: {values})"
                        )

    with GradingStep(f"Il secret {EXPECTED_SECRET_NAME} esiste in {EXPECTED_SECRET_NAMESPACE}") as step:
        secret = oc_get_json("secret", EXPECTED_SECRET_NAME, "-n", EXPECTED_SECRET_NAMESPACE)
        if secret is None:
            step.fail(f"Secret '{EXPECTED_SECRET_NAME}' non trovato in {EXPECTED_SECRET_NAMESPACE}")

    with GradingStep(f"Il ruolo cluster 'edit' e' assegnato al gruppo {CONTRACTORS_GROUP}") as step:
        bindings = oc_get_json("clusterrolebinding")
        if bindings is None:
            step.fail("Impossibile leggere i clusterrolebinding")
        elif find_binding_for_group(bindings, "edit", CONTRACTORS_GROUP) is None:
            step.add_error(
                f"Nessun ClusterRoleBinding assegna il ruolo 'edit' al gruppo {CONTRACTORS_GROUP} "
                f"(atteso da: oc adm policy add-role-to-group edit {CONTRACTORS_GROUP})"
            )

    with GradingStep(f"Il ruolo cluster 'view' e' assegnato al gruppo {PARTNERS_GROUP}") as step:
        bindings = oc_get_json("clusterrolebinding")
        if bindings is None:
            step.fail("Impossibile leggere i clusterrolebinding")
        elif find_binding_for_group(bindings, "view", PARTNERS_GROUP) is None:
            step.add_error(
                f"Nessun ClusterRoleBinding assegna il ruolo 'view' al gruppo {PARTNERS_GROUP} "
                f"(atteso da: oc adm policy add-role-to-group view {PARTNERS_GROUP})"
            )


if __name__ == "__main__":
    main()
