#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato declarative-kustomize, sprovvisto di
`lab grade` ufficiale (la classe DeclarativeKustomize nel pacchetto do280
implementa solo start()/finish(), non grade()).

Specifica dedotta da materials/solutions/declarative-kustomize (struttura
Kustomize progressiva v1.1.0 -> v1.1.3) e dal testo della guida studente:
- v1.1.0: base/ con database (Deployment+Service+ConfigMap "database") ed
  exoplanets (Deployment+Service+Route), piu' un secretGenerator "db-secrets"
  e un configMapGenerator "db-config" nel kustomization.yaml radice.
- v1.1.1: aggiorna l'immagine di exoplanets a :v1.1.1 (unico cambiamento).
- v1.1.2: cambia il literal DB_PASSWORD del secretGenerator da "password" a
  "newpassword" (Kustomize rigenera il Secret con un hash diverso).
- v1.1.3: aggiunge overlays/production/ con una patch che porta le repliche
  di exoplanets a 2.

La guida (passo 10) fa terminare l'esercizio cancellando le risorse con
`oc delete -k base` prima di `lab finish`: lo stato gradabile e' quindi
quello raggiunto al passo 9, dopo `oc apply -k overlays/production`, che e'
il momento in cui uno studente invocherebbe `lab grade`.

Nomi di ConfigMap/Secret generati da Kustomize hanno un hash-suffix non
deterministico (es. "db-config-2d7thbcgkc"): li individuiamo per prefisso,
come suggerito in README.md per i casi di nomi non fissi (vedi
storage-configs.py).

Uso: declarative-kustomize.py [nome-progetto]   (default: declarative-kustomize)
"""

import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "declarative-kustomize"

EXOPLANETS_IMAGE_SUFFIX = "redhattraining/exoplanets:v1.1.1"
DATABASE_IMAGE_SUFFIX = "rhel8/postgresql-13:1-7"
EXPECTED_REPLICAS = 2  # da overlays/production/patch-replicas.yaml (v1.1.3)
EXPECTED_DB_PASSWORD = "newpassword"  # da base/kustomization.yaml (v1.1.2)


def find_by_prefix(kind, project, prefix):
    """Cerca, fra le risorse del progetto, quella il cui nome inizia col
    prefisso dato (per i nomi generati da Kustomize con hash-suffix)."""
    items = oc_get_json(kind, "-n", project)
    if not items:
        return None
    for item in items.get("items", []):
        if item["metadata"]["name"].startswith(prefix):
            return item
    return None


def decode_secret_data(secret):
    """I valori in .data di un Secret sono codificati in base64."""
    data = secret.get("data", {}) or {}
    decoded = {}
    for key, value in data.items():
        try:
            decoded[key] = base64.b64decode(value).decode("utf-8")
        except Exception:
            decoded[key] = None
    return decoded


def get_container(deployment, name):
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def envfrom_names(container):
    """Ritorna l'insieme dei nomi (configMapRef/secretRef) referenziati in
    envFrom del container."""
    names = set()
    for ref in container.get("envFrom", []) or []:
        cm = ref.get("configMapRef")
        sec = ref.get("secretRef")
        if cm:
            names.add(cm.get("name"))
        if sec:
            names.add(sec.get("name"))
    return names


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    db_deployment = oc_get_json("deployment", "database", "-n", project)
    exo_deployment = oc_get_json("deployment", "exoplanets", "-n", project)

    with GradingStep("Il database e' distribuito con l'immagine attesa") as step:
        if db_deployment is None:
            step.fail("Deployment 'database' non trovato nel progetto")
        else:
            container = get_container(db_deployment, "postgresql")
            if container is None:
                step.fail("Nessun container trovato nel deployment 'database'")
            elif not container.get("image", "").endswith(DATABASE_IMAGE_SUFFIX):
                step.add_error(
                    f"Immagine del database non corrisponde a "
                    f"'*{DATABASE_IMAGE_SUFFIX}' (trovata: {container.get('image')})"
                )
            ready = db_deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error("Nessuna replica pronta per il deployment 'database'")

    with GradingStep(
        "L'applicazione exoplanets e' aggiornata alla versione v1.1.1"
    ) as step:
        if exo_deployment is None:
            step.fail("Deployment 'exoplanets' non trovato nel progetto")
        else:
            container = get_container(exo_deployment, "exoplanets")
            if container is None:
                step.fail("Nessun container trovato nel deployment 'exoplanets'")
            elif not container.get("image", "").endswith(EXOPLANETS_IMAGE_SUFFIX):
                step.add_error(
                    f"Immagine di exoplanets non corrisponde a "
                    f"'*{EXOPLANETS_IMAGE_SUFFIX}' (trovata: {container.get('image')}). "
                    "Verificare che 'oc apply -k base' sia stato eseguito dopo "
                    "il checkout del branch v1.1.1"
                )

    db_config = find_by_prefix("configmap", project, "db-config-")
    db_secret = find_by_prefix("secret", project, "db-secrets-")

    with GradingStep(
        "I deployment referenziano la ConfigMap e il Secret generati da Kustomize"
    ) as step:
        if exo_deployment is None or db_deployment is None:
            step.fail()
        else:
            exo_container = get_container(exo_deployment, "exoplanets")
            db_container = get_container(db_deployment, "postgresql")
            if db_config is None:
                step.add_error(
                    "Nessuna ConfigMap generata con prefisso 'db-config-' trovata "
                    "(atteso dal configMapGenerator in base/kustomization.yaml)"
                )
            elif exo_container is None or db_config["metadata"]["name"] not in envfrom_names(
                exo_container
            ):
                step.add_error(
                    "Il deployment 'exoplanets' non referenzia la ConfigMap generata "
                    "'db-config-*' in envFrom"
                )
            if db_secret is None:
                step.add_error(
                    "Nessun Secret generato con prefisso 'db-secrets-' trovato "
                    "(atteso dal secretGenerator in base/kustomization.yaml)"
                )
            elif db_container is not None:
                secret_used = any(
                    env.get("valueFrom", {}).get("secretKeyRef", {}).get("name")
                    == db_secret["metadata"]["name"]
                    for env in db_container.get("env", []) or []
                )
                if not secret_used:
                    step.add_error(
                        "Il deployment 'database' non referenzia il Secret generato "
                        "'db-secrets-*' nelle variabili d'ambiente"
                    )

    with GradingStep(
        "Il Secret generato contiene la password aggiornata (v1.1.2)"
    ) as step:
        if db_secret is None:
            step.fail()
        else:
            values = decode_secret_data(db_secret)
            if values.get("DB_PASSWORD") != EXPECTED_DB_PASSWORD:
                step.add_error(
                    f"DB_PASSWORD nel Secret generato e' "
                    f"'{values.get('DB_PASSWORD')}', atteso '{EXPECTED_DB_PASSWORD}' "
                    "(base/kustomization.yaml aggiornato al branch v1.1.2 e "
                    "poi 'oc apply -k base' rieseguito)"
                )

    with GradingStep(
        "L'overlay di produzione e' applicato: exoplanets ha 2 repliche"
    ) as step:
        if exo_deployment is None:
            step.fail()
        else:
            replicas = exo_deployment.get("spec", {}).get("replicas")
            if replicas != EXPECTED_REPLICAS:
                step.add_error(
                    f"spec.replicas di 'exoplanets' e' {replicas}, atteso "
                    f"{EXPECTED_REPLICAS} (overlays/production applicato con "
                    "'oc apply -k overlays/production')"
                )

    service_db = oc_get_json("service", "database", "-n", project)
    service_exo = oc_get_json("service", "exoplanets", "-n", project)
    route_exo = oc_get_json("route", "exoplanets", "-n", project)

    with GradingStep(
        "I Service e la Route dell'applicazione sono presenti e collegati"
    ) as step:
        if service_db is None:
            step.add_error("Service 'database' non trovato (porta 5432 attesa)")
        if service_exo is None:
            step.add_error("Service 'exoplanets' non trovato (porta 8080 attesa)")
        if route_exo is None:
            step.add_error("Route 'exoplanets' non trovata")
        elif route_exo.get("spec", {}).get("to", {}).get("name") != "exoplanets":
            step.add_error(
                "La Route 'exoplanets' non punta al Service 'exoplanets'"
            )
        # L'host esatto della Route (es. exoplanets-declarative-kustomize.
        # apps.ocp4.example.com) dipende dal dominio wildcard del cluster:
        # non lo verifichiamo per nome, solo che sia stato assegnato.
        elif not route_exo.get("spec", {}).get("host"):
            step.add_error("La Route 'exoplanets' non ha un host assegnato")


if __name__ == "__main__":
    main()
