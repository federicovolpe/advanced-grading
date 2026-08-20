#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "files-templates" (sku
au0023l, sez. 5.4 "Using Jinja2 Templates and Filters"), sprovvista di
`lab grade` ufficiale.

Fonte primaria: materials/labs/files-templates/solutions/{motd.j2,
motd.yml}.sol nel pacchetto pip del corso (identiche al testo della guida,
pag. 320-323) e l'inventory di partenza (gruppo webhosts = servera,
serverc; gruppo workstations = serverb, serverd).

Come richiesto dalla consegna, si gradua il FILE RENDERIZZATO risultante
(/etc/motd) su host reali, non il template Jinja2 letterale: leggiamo
davvero ansible_facts['fqdn']/['distribution']/['distribution_version'] di
ciascun host (via `hostname -f` e /etc/os-release, in sola lettura) e
costruiamo il contenuto atteso dinamicamente, cosi' il check resta valido
anche se cambia l'immagine/versione RHEL della classroom. L'unico valore
letterale preso dalla guida e' system_owner = "web-support@example.com"
(pag. 321, step 4.2), usato solo per gli host del gruppo webhosts.

remote_user: devops non lascia alcun effetto verificabile a posteriori
(serve solo alla connessione SSH usata da ansible-playbook, e' effimero):
per questo unico valore si verifica la STRUTTURA locale di motd.yml
(regola d'oro: struttura solo se l'effetto non e' osservabile).

Non testato end-to-end dal vivo: applicare la soluzione ufficiale avrebbe
richiesto eseguire ansible-playbook motd.yml come utente devops (con
become) su servera-serverd, scrivendo davvero /etc/motd su host condivisi
con altri esercizi in corso in parallelo in questa sessione. Le letture
in sola lettura fatte per validare la logica (hostname -f, /etc/os-release,
/etc/motd attuale) confermano pero' che i valori attesi sono calcolati
correttamente e che lo stato di partenza (motd vuoto) da' FAIL come atteso.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

LAB_NAME = "files-templates"

_SYSTEM_OWNER = "web-support@example.com"  # guida pag. 321, step 4.2


def parse_inventory_groups(path):
    """Parsing minimale di un inventory INI-style Ansible: ritorna
    {nome_gruppo: [host, ...]}. Basta per l'inventory statico e piccolo di
    questo esercizio (nessuna variabile host/gruppo, solo [gruppo] + host)."""
    groups = {}
    current = None
    try:
        with open(path) as f:
            lines = f.readlines()
    except OSError:
        return groups
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            groups.setdefault(current, [])
            continue
        if current:
            groups[current].append(line.split()[0])
    return groups


def short_name(fqdn_or_host):
    """Ritorna il nome breve (prima del primo punto) di un host, per usarlo
    come alias SSH di _common.run (es. 'servera' da
    'servera.lab.example.com')."""
    return fqdn_or_host.split(".")[0]


def remote_fqdn(host):
    result = run("hostname -f", host=host)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def remote_distribution(host):
    """Ritorna (distribution, distribution_version) come li calcolerebbe
    Ansible per RHEL: ansible_facts['distribution'] vale sempre "RedHat"
    (non il NAME completo di /etc/os-release), distribution_version e' il
    VERSION_ID cosi' com'e'."""
    result = run("cat /etc/os-release", host=host)
    if result.returncode != 0:
        return None, None
    version_id = None
    for line in result.stdout.splitlines():
        if line.startswith("VERSION_ID="):
            version_id = line.split("=", 1)[1].strip().strip('"')
    return "RedHat", version_id


def remote_motd(host):
    result = run("cat /etc/motd", host=host)
    if result.returncode != 0:
        return None
    return result.stdout


def remote_stat_owner_group_mode(path, host):
    result = run(f"stat -c '%U %G %a' {path}", host=host)
    if result.returncode != 0:
        return None
    parts = result.stdout.strip().split()
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def expected_motd_lines(host, extra_line):
    """Costruisce le righe attese di /etc/motd per un host, usando i fatti
    reali letti dall'host stesso (non hardcoded)."""
    fqdn = remote_fqdn(host)
    distribution, version = remote_distribution(host)
    if not fqdn or not distribution or not version:
        return None
    return [
        f"This is the system {fqdn}.",
        f"This is a {distribution} version {version} system.",
        extra_line,
    ]


def content_has_lines(content, expected_lines):
    """True se ogni riga attesa compare (come sottostringa, per tollerare
    differenze di a-capo/spazi introdotte dal template) nel contenuto."""
    return all(line in content for line in expected_lines)


def main():
    exercise_dir = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    workdir = os.path.expanduser(f"~/{exercise_dir}")
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (dir: {workdir})")

    template_path = os.path.join(workdir, "templates", "motd.j2")
    playbook_path = os.path.join(workdir, "motd.yml")
    inventory_path = os.path.join(workdir, "inventory")

    with GradingStep("templates/motd.j2 e motd.yml esistono nella directory dell'esercizio") as step:
        if not os.path.exists(template_path):
            step.add_error(f"'{template_path}' non trovato")
        if not os.path.exists(playbook_path):
            step.add_error(f"'{playbook_path}' non trovato")

    groups = parse_inventory_groups(inventory_path)
    # Fallback ai valori dell'inventory di partenza se il file locale manca
    # o e' stato alterato in modo da non contenere piu' i gruppi attesi.
    webhosts = [short_name(h) for h in groups.get("webhosts", [])] or ["servera", "serverc"]
    workstations = [short_name(h) for h in groups.get("workstations", [])] or ["serverb", "serverd"]

    with GradingStep(
        f"/etc/motd renderizzato correttamente sugli host webhosts ({', '.join(webhosts)})"
    ) as step:
        extra_line = f"Please report issues to: {_SYSTEM_OWNER}."
        for host in webhosts:
            expected = expected_motd_lines(host, extra_line)
            if expected is None:
                step.add_error(f"Impossibile leggere fqdn/distribuzione da {host} (host irraggiungibile?)")
                continue
            content = remote_motd(host)
            if content is None:
                step.fail(f"Impossibile leggere /etc/motd su {host}")
            elif not content_has_lines(content, expected):
                step.add_error(f"/etc/motd su {host} non contiene le righe attese: {expected}")

    with GradingStep(
        f"/etc/motd renderizzato correttamente sugli host workstations ({', '.join(workstations)})"
    ) as step:
        extra_line = "As a workstation user, you need to submit a ticket to receive help with any issues."
        for host in workstations:
            expected = expected_motd_lines(host, extra_line)
            if expected is None:
                step.add_error(f"Impossibile leggere fqdn/distribuzione da {host} (host irraggiungibile?)")
                continue
            content = remote_motd(host)
            if content is None:
                step.fail(f"Impossibile leggere /etc/motd su {host}")
            elif not content_has_lines(content, expected):
                step.add_error(f"/etc/motd su {host} non contiene le righe attese: {expected}")

    with GradingStep("/etc/motd ha owner root, group root e mode 0644 su tutti gli host (effetto del task template)") as step:
        for host in webhosts + workstations:
            info = remote_stat_owner_group_mode("/etc/motd", host=host)
            if info is None:
                step.add_error(f"Impossibile leggere i permessi di /etc/motd su {host}")
                continue
            owner, group, mode = info
            if owner != "root" or group != "root":
                step.add_error(f"Owner/group di /etc/motd su {host} = {owner}:{group}, attesi root:root")
            if mode != "644":
                step.add_error(f"Mode di /etc/motd su {host} = {mode}, atteso 644")

    # remote_user: devops non lascia effetto persistente osservabile (usato
    # solo per la connessione SSH del playbook run): unico check strutturale.
    if os.path.exists(playbook_path):
        import yaml

        with GradingStep("motd.yml usa remote_user: devops per connettersi agli host gestiti") as step:
            try:
                with open(playbook_path) as f:
                    docs = yaml.safe_load(f)
                play = docs[0] if isinstance(docs, list) and docs else {}
            except (OSError, yaml.YAMLError):
                play = {}
            if play.get("remote_user") != "devops":
                step.add_error(f"remote_user = {play.get('remote_user')!r}, atteso 'devops'")


if __name__ == "__main__":
    main()
