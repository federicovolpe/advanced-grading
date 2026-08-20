#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "scale-hosts" (Cap. 6.4
"Selecting Hosts by Using Host Patterns", pag. 359-368), sprovvista di
`lab grade` ufficiale (scale-hosts.py nel pacchetto au0024l non definisce
grade()).

L'esercizio fa modificare piu' volte lo STESSO campo `hosts:` dell'unico
play in host_patterns.yml (passi 4-14 della guida), rieseguendo il playbook
dopo ogni modifica per osservarne l'effetto. Solo l'ULTIMO stato prima di
"Finish" e' verificabile in modo persistente: ogni passo successivo
sovrascrive il precedente. Il passo 14.1 (l'ultimo, pag. 367) chiede
esplicitamente:

    "Modify the host pattern in the playbook to use '*example*' as the
    host pattern" -> hosts: '*example*'

il cui effetto atteso (pag. 367-368) e' selezionare tutti gli host il cui
nome contiene la stringa "example", cioe' tutti gli host con FQDN
dell'inventory (web1/web2/db1/db2/redis1/redis2/lb1/lb2), esclusi i due IP
"ungrouped" 192.168.0.1 e 192.168.0.2.

Anziche' confrontare il TESTO letterale del pattern (che boccerebbe
formulazioni equivalenti diverse da '*example*', es. un elenco esplicito di
gruppi/host con lo stesso effetto), verifichiamo l'EFFETTO: risolviamo il
pattern scritto dallo studente con il comando reale `ansible <pattern>
--list-hosts` contro l'inventory dell'esercizio (lettura pura, nessuna
esecuzione di play) e confrontiamo l'insieme di host risultante con quello
atteso. Cosi' il grading regge a qualunque pattern semanticamente
equivalente.

I passi intermedi (4-13) non sono gradati: sono transitori (il campo
`hosts:` viene sovrascritto ad ogni passo successivo) e non sopravvivono
fino alla fine dell'esercizio.
"""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, read_text_file

LAB_NAME = "scale-hosts"
WORKDIR_DEFAULT = os.path.expanduser(f"~/{LAB_NAME}")

# Host attesi dopo il passo 14.1 (pattern '*example*', pag. 367-368): tutti
# gli host con FQDN contenente "example", esclusi i due IP ungrouped.
_EXPECTED_HOSTS = {
    "web1.na.example.com", "web2.eu.example.com",
    "db1.na.example.com", "db2.eu.example.com",
    "redis1.na.example.com", "redis2.eu.example.com",
    "lb1.na.example.com", "lb2.eu.example.com",
}


def get_hosts_pattern(playbook_path):
    """Estrae il valore del campo hosts: della prima play in
    host_patterns.yml. Usa un parsing testuale semplice (non yaml.safe_load)
    perche' il pattern puo' contenere caratteri speciali YAML (!, *, &) che
    la guida chiede di racchiudere fra apici singoli: un parser YAML
    completo va bene comunque, ma una regex sulla singola riga e' piu'
    robusta a varianti di quoting mantenendo lo stesso risultato."""
    content = read_text_file(playbook_path)
    if content is None:
        return None
    match = re.search(r"^\s*hosts:\s*(.+?)\s*$", content, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value


def resolve_hosts(pattern, inventory_path):
    """Ritorna l'insieme di host risolti da Ansible per un host pattern,
    usando l'inventory reale dell'esercizio (comando in sola lettura: risolve
    soltanto l'inventory, non esegue alcun task/play)."""
    result = subprocess.run(
        ["ansible", pattern, "-i", inventory_path, "--list-hosts"],
        capture_output=True, text=True,
    )
    hosts = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("hosts ("):
            continue
        hosts.add(line)
    return hosts


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else WORKDIR_DEFAULT
    if not os.path.isabs(project_dir):
        project_dir = os.path.expanduser(f"~/{project_dir}")
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (directory: {project_dir})")

    playbook_path = os.path.join(project_dir, "host_patterns.yml")
    inventory_path = os.path.join(project_dir, "inventory")

    with GradingStep("La directory dell'esercizio e i file di partenza esistono") as step:
        if not os.path.isdir(project_dir):
            step.fail(f"Directory '{project_dir}' non trovata: esegui 'lab start {LAB_NAME}'")
        elif not os.path.isfile(playbook_path):
            step.fail("host_patterns.yml non trovato")
        elif not os.path.isfile(inventory_path):
            step.fail("inventory non trovato")

    with GradingStep("host_patterns.yml seleziona esattamente gli host con 'example' nel nome (passo 14)") as step:
        if not (os.path.isfile(playbook_path) and os.path.isfile(inventory_path)):
            step.fail("Prerequisito mancante: vedi lo step precedente")
        else:
            pattern = get_hosts_pattern(playbook_path)
            if not pattern:
                step.fail("Campo 'hosts:' non trovato in host_patterns.yml")
            else:
                actual = resolve_hosts(pattern, inventory_path)
                if actual != _EXPECTED_HOSTS:
                    missing = _EXPECTED_HOSTS - actual
                    extra = actual - _EXPECTED_HOSTS
                    if missing:
                        step.add_error(f"Host mancanti dal pattern '{pattern}': {', '.join(sorted(missing))}")
                    if extra:
                        step.add_error(f"Host selezionati in piu' dal pattern '{pattern}': {', '.join(sorted(extra))}")


if __name__ == "__main__":
    main()
