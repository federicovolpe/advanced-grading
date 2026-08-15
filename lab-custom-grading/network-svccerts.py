#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato network-svccerts (DO280), sprovvisto
di `lab grade` ufficiale (la classe NetworkSvccerts nel pacchetto do280
implementa solo start()/finish(), non grade()).

A differenza degli esercizi DO180 gia' presenti in questo repo, qui i nomi
delle risorse NON sono lasciati alla scelta dello studente: sono dettati
esplicitamente dal testo della guida (network-svccerts.pdf, Capitolo 4.6) e
confermati dal confronto lab-vs-solution in
do280/materials/{labs,solutions}/network-svccerts:

- Service "server" (creato da start()) deve ricevere l'annotazione
  service.beta.openshift.io/serving-cert-secret-name=server-secret, che fa
  generare al service-ca controller un Secret "server-secret" (tipo
  kubernetes.io/tls, chiavi tls.crt/tls.key).
- Il Deployment "server" deve montare quel Secret in /etc/pki/nginx/, con
  tls.crt->server.crt e tls.key->private/server.key (vedi
  server-secret.yaml lab vs soluzione: solo i CHANGE_ME cambiano, la forma
  e' identica).
- Una ConfigMap "ca-bundle" (creata vuota dallo studente) deve avere
  l'annotazione service.beta.openshift.io/inject-cabundle=true, che fa
  iniettare al service-ca controller la chiave service-ca.crt.
- Il Deployment "client" (applicato da client.yaml) deve montare quella
  ConfigMap in /etc/pki/ca-trust/extracted/pem con service-ca.crt->
  tls-ca-bundle.pem (client.yaml lab vs soluzione: solo i CHANGE_ME
  cambiano).

Il controllo funzionale finale ricalca il passo 4.1 della guida stessa
(oc exec deploy/client -- curl -s https://server.network-svccerts.svc):
e' un comando in sola lettura (nessuna risorsa Kubernetes viene creata o
modificata), quindi ammesso dalle regole del repo, ed e' l'unico modo per
verificare "black box" che il client si fidi davvero della CA iniettata
(un mount corretto ma con contenuto vuoto/sbagliato passerebbe comunque i
controlli strutturali sopra).

Uso: network-svccerts.py [nome-progetto]   (default: network-svccerts)
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "network-svccerts"

SERVICE_NAME = "server"
SERVER_SECRET_NAME = "server-secret"
SERVER_DEPLOYMENT_NAME = "server"
SERVER_MOUNT_PATH = "/etc/pki/nginx/"

CA_CONFIGMAP_NAME = "ca-bundle"
CLIENT_DEPLOYMENT_NAME = "client"
CLIENT_MOUNT_PATH = "/etc/pki/ca-trust/extracted/pem"

SERVING_CERT_ANNOTATION = "service.beta.openshift.io/serving-cert-secret-name"
INJECT_CABUNDLE_ANNOTATION = "service.beta.openshift.io/inject-cabundle"


def get_container(deployment, name):
    if deployment is None:
        return None
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def find_secret_volume_mount(deployment, container, secret_name):
    """Ritorna (volume, volume_mount) del primo volume 'secret' che punta a
    secret_name e risulta montato nel container, o (None, None)."""
    if deployment is None or container is None:
        return None, None
    volumes = deployment["spec"]["template"]["spec"].get("volumes", []) or []
    mounts = {vm.get("name"): vm for vm in (container.get("volumeMounts") or [])}
    for vol in volumes:
        secret = vol.get("secret")
        if secret and secret.get("secretName") == secret_name and vol.get("name") in mounts:
            return vol, mounts[vol["name"]]
    return None, None


def find_configmap_volume_mount(deployment, container, configmap_name):
    """Ritorna (volume, volume_mount) del primo volume 'configMap' che punta a
    configmap_name e risulta montato nel container, o (None, None)."""
    if deployment is None or container is None:
        return None, None
    volumes = deployment["spec"]["template"]["spec"].get("volumes", []) or []
    mounts = {vm.get("name"): vm for vm in (container.get("volumeMounts") or [])}
    for vol in volumes:
        cm = vol.get("configMap")
        if cm and cm.get("name") == configmap_name and vol.get("name") in mounts:
            return vol, mounts[vol["name"]]
    return None, None


def items_map(items):
    """[{'key': k, 'path': p}, ...] -> {k: p}"""
    return {i.get("key"): i.get("path") for i in (items or [])}


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # --- Parte server: annotazione sul Service + Secret generato ---

    service = oc_get_json("service", SERVICE_NAME, "-n", project)

    with GradingStep(
        f"Il Service '{SERVICE_NAME}' ha l'annotazione serving-cert-secret-name"
    ) as step:
        if service is None:
            step.fail(f"Service '{SERVICE_NAME}' non trovato nel progetto")
        else:
            annotations = service["metadata"].get("annotations") or {}
            value = annotations.get(SERVING_CERT_ANNOTATION)
            if value is None:
                step.add_error(
                    f"Manca l'annotazione '{SERVING_CERT_ANNOTATION}' sul Service"
                )
            elif value != SERVER_SECRET_NAME:
                step.add_error(
                    f"L'annotazione '{SERVING_CERT_ANNOTATION}' vale '{value}', "
                    f"atteso '{SERVER_SECRET_NAME}' (deve combaciare con il nome "
                    "del Secret montato nel deployment)"
                )

    secret = oc_get_json("secret", SERVER_SECRET_NAME, "-n", project)

    with GradingStep(
        f"Il Secret '{SERVER_SECRET_NAME}' e' stato generato dal service-ca controller"
    ) as step:
        if secret is None:
            step.fail(
                f"Secret '{SERVER_SECRET_NAME}' non trovato: verifica che "
                "l'annotazione sul Service sia corretta e che il service-ca "
                "controller abbia fatto in tempo a generarlo"
            )
        else:
            if secret.get("type") != "kubernetes.io/tls":
                step.add_error(
                    f"Il Secret e' di tipo '{secret.get('type')}', atteso "
                    "'kubernetes.io/tls' (non e' stato creato dal service-ca "
                    "controller)"
                )
            data = secret.get("data") or {}
            for key in ("tls.crt", "tls.key"):
                if not data.get(key):
                    step.add_error(f"Il Secret non contiene la chiave '{key}'")

    # --- Parte server: il deployment monta il Secret correttamente ---

    server_deployment = oc_get_json("deployment", SERVER_DEPLOYMENT_NAME, "-n", project)
    server_container = get_container(server_deployment, "server")

    with GradingStep(
        f"Il deployment '{SERVER_DEPLOYMENT_NAME}' esiste ed e' pronto"
    ) as step:
        if server_deployment is None:
            step.fail(f"Deployment '{SERVER_DEPLOYMENT_NAME}' non trovato")
        elif not server_deployment.get("status", {}).get("readyReplicas", 0):
            step.add_error(
                f"Nessuna replica pronta per il deployment "
                f"'{SERVER_DEPLOYMENT_NAME}' (il pod monta correttamente il "
                "certificato? controlla 'oc describe pod')"
            )

    with GradingStep(
        f"Il deployment '{SERVER_DEPLOYMENT_NAME}' monta '{SERVER_SECRET_NAME}' "
        f"in {SERVER_MOUNT_PATH}"
    ) as step:
        if server_deployment is None or server_container is None:
            step.fail()
        else:
            vol, vm = find_secret_volume_mount(
                server_deployment, server_container, SERVER_SECRET_NAME
            )
            if vol is None:
                step.add_error(
                    f"Nessun volume da Secret '{SERVER_SECRET_NAME}' risulta "
                    "montato nel container 'server'"
                )
            else:
                if vm.get("mountPath") != SERVER_MOUNT_PATH:
                    step.add_error(
                        f"mountPath e' '{vm.get('mountPath')}', atteso "
                        f"'{SERVER_MOUNT_PATH}'"
                    )
                paths = items_map(vol["secret"].get("items"))
                if paths.get("tls.crt") != "server.crt":
                    step.add_error(
                        "La chiave 'tls.crt' deve essere montata come "
                        f"'server.crt' (trovato: {paths.get('tls.crt')!r})"
                    )
                if paths.get("tls.key") != "private/server.key":
                    step.add_error(
                        "La chiave 'tls.key' deve essere montata come "
                        f"'private/server.key' (trovato: {paths.get('tls.key')!r})"
                    )

    # --- Parte client: ConfigMap con la CA iniettata ---

    ca_configmap = oc_get_json("configmap", CA_CONFIGMAP_NAME, "-n", project)

    with GradingStep(
        f"La ConfigMap '{CA_CONFIGMAP_NAME}' ha l'annotazione inject-cabundle "
        "ed espone service-ca.crt"
    ) as step:
        if ca_configmap is None:
            step.fail(f"ConfigMap '{CA_CONFIGMAP_NAME}' non trovata nel progetto")
        else:
            annotations = ca_configmap["metadata"].get("annotations") or {}
            value = annotations.get(INJECT_CABUNDLE_ANNOTATION)
            if value != "true":
                step.add_error(
                    f"L'annotazione '{INJECT_CABUNDLE_ANNOTATION}' vale "
                    f"'{value}', attesa 'true'"
                )
            if not (ca_configmap.get("data") or {}).get("service-ca.crt"):
                step.add_error(
                    "La ConfigMap non contiene la chiave 'service-ca.crt': "
                    "il service-ca controller non ha (ancora) iniettato il "
                    "bundle, verifica l'annotazione o riprova tra qualche istante"
                )

    # --- Parte client: il deployment monta la ConfigMap correttamente ---

    client_deployment = oc_get_json("deployment", CLIENT_DEPLOYMENT_NAME, "-n", project)
    client_container = get_container(client_deployment, "client-deploy")

    with GradingStep(
        f"Il deployment '{CLIENT_DEPLOYMENT_NAME}' esiste ed e' pronto"
    ) as step:
        if client_deployment is None:
            step.fail(
                f"Deployment '{CLIENT_DEPLOYMENT_NAME}' non trovato: e' stato "
                "applicato ~/DO280/labs/network-svccerts/client.yaml?"
            )
        elif not client_deployment.get("status", {}).get("readyReplicas", 0):
            step.add_error(
                f"Nessuna replica pronta per il deployment "
                f"'{CLIENT_DEPLOYMENT_NAME}'"
            )

    with GradingStep(
        f"Il deployment '{CLIENT_DEPLOYMENT_NAME}' monta '{CA_CONFIGMAP_NAME}' "
        f"in {CLIENT_MOUNT_PATH}"
    ) as step:
        if client_deployment is None or client_container is None:
            step.fail()
        else:
            vol, vm = find_configmap_volume_mount(
                client_deployment, client_container, CA_CONFIGMAP_NAME
            )
            if vol is None:
                step.add_error(
                    f"Nessun volume da ConfigMap '{CA_CONFIGMAP_NAME}' risulta "
                    "montato nel container"
                )
            else:
                if vm.get("mountPath") != CLIENT_MOUNT_PATH:
                    step.add_error(
                        f"mountPath e' '{vm.get('mountPath')}', atteso "
                        f"'{CLIENT_MOUNT_PATH}'"
                    )
                paths = items_map(vol["configMap"].get("items"))
                if paths.get("service-ca.crt") != "tls-ca-bundle.pem":
                    step.add_error(
                        "La chiave 'service-ca.crt' deve essere montata come "
                        f"'tls-ca-bundle.pem' (trovato: "
                        f"{paths.get('service-ca.crt')!r})"
                    )

    # --- Controllo funzionale: il client raggiunge il server in HTTPS
    # fidandosi della CA iniettata (stesso comando del passo 4.1 della
    # guida: sola lettura, non modifica lo stato del cluster). ---

    with GradingStep(
        "Il client raggiunge il server in HTTPS fidandosi della CA iniettata"
    ) as step:
        if client_deployment is None or server_deployment is None:
            step.add_error(
                "Salto il controllo funzionale: deployment client e/o server mancanti"
            )
        elif not client_deployment.get("status", {}).get("readyReplicas", 0):
            step.add_error(
                "Salto il controllo funzionale: il pod client non e' pronto"
            )
        else:
            result = subprocess.run(
                [
                    "oc", "exec", f"deploy/{CLIENT_DEPLOYMENT_NAME}", "-n", project,
                    "--", "curl", "-s", "--max-time", "10",
                    f"https://{SERVICE_NAME}.{project}.svc",
                ],
                capture_output=True, text=True, timeout=20,
            )
            if result.returncode != 0:
                step.add_error(
                    f"'oc exec ... curl' e' fallito (rc={result.returncode}): "
                    f"{result.stderr.strip()[-300:]}"
                )
            elif "Hello, world from nginx!" not in result.stdout:
                step.add_error(
                    "La risposta HTTPS del server non contiene il testo atteso "
                    f"'Hello, world from nginx!' (curl ha stampato: "
                    f"{result.stdout.strip()[:200]!r})"
                )


if __name__ == "__main__":
    main()
