#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio "files-manage" — nome che COLLIDE fra due
corsi diversi (vedi CLAUDE.md sez. 6, "Attenzione alle collisioni tra
corsi"): RH124 sezione 7.2 "Manage Files with Command-line Tools" (sku
rh0016l) e AU294 sezione 5.2 "Automating File Management Tasks" (sku
au0023l). Il wrapper cerca lo script per nome esatto dell'esercizio senza
distinguere per corso, quindi questo file dispatcha in base al
`course_sku` registrato per "files-manage" in ~/.grading/lab_manifest.json
(popolato dal `lab` di QUESTA macchina in base a quale corso e' installato)
ed esegue la logica del corso corretto.

--- RH124 files-manage (sku rh0016l, sez. 7.2) ---
Nessuna materials/solutions ne' resources.txt: specifica presa dal testo
della guida (RH124 7.2, passi 2-7), eseguita interamente sull'host servera
nella home di student. Stato finale atteso: Music/, Pictures/, Videos/
contengono rispettivamente i 6 file songN.mp3, snapN.jpg, filmN.avi
(spostati con mv dalla home); friends/, family/, work/ sono state create
al passo 4, popolate con cp ai passi 5-6, e infine RIMOSSE con `rm -rf` al
passo 7.2 (pulizia finale).

--- AU294 files-manage (sku au0023l, sez. 5.2) ---
Fonte primaria: materials/labs/files-manage/solutions/{vsftpd-server,
file-operations}.yml.sol nel pacchetto pip del corso (confermate identiche
al testo della guida, pag. 299-309) e l'inventory di partenza (gruppo
ftp_servers = serverc, serverd).

Strategia di grading:
- vsftpd-server.yml: i suoi 7 task (dnf/lineinfile/blockinfile/
  systemd_service/firewalld/file/copy) producono uno stato reale e
  persistente su serverc/serverd (sopravvive fino a `lab finish`, la
  guida stessa lo verifica al passo 5 collegandosi via ftp). Gradiamo
  quindi l'EFFETTO reale via SSH in sola lettura, non il testo YAML: e'
  piu' robusto (indipendente da nomi task/ordine) e piu' vicino a cosa
  chiede davvero l'esercizio ("Run the playbook and verify").
- file-operations.yml: i task 1-2 (stat/debug) non lasciano alcuno stato
  persistente (il debug stampa solo a video), quindi per quei due si
  verifica la STRUTTURA del playbook locale (regola d'oro: se l'effetto
  non e' verificabile, si verifica la struttura). Il task 3 (find) e' a
  sua volta strutturale perche' il risultato dipende da quali file di log
  superano 10000 byte in quel momento (stato non deterministico, non
  fissabile). Per il task 4 (fetch) verifichiamo invece l'effetto reale:
  la presenza locale di almeno un file *.log >10000 byte scaricato sotto
  <workdir>/serverc.lab.example.com/var/log/ (fetch con dest: ./ crea
  automaticamente la sottocartella per host), a riprova che il playbook e'
  stato eseguito con successo.

Non testato end-to-end dal vivo: l'utente demoftp (richiesto dai task 6/7
di vsftpd-server.yml) non esiste su serverc/serverd finche' lo studente non
esegue `lab start files-manage` (verificato in sola lettura in questa
sessione: demoftp assente, vsftpd non installato). Applicare la soluzione
ufficiale qui avrebbe richiesto ricreare a mano quell'utente e installare/
avviare pacchetti e servizi reali su host condivisi con altri esercizi in
corso in parallelo: rischio di stato residuo non banale da annullare in
sicurezza, quindi si e' preferita l'analisi statica della logica di verifica
(READ-ONLY, confermata funzionante contro lo stato attuale non ancora
configurato, che correttamente da' FAIL).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep, run, command_ok, file_exists, package_installed,
    service_is_active, service_is_enabled,
)

LAB_NAME = "files-manage"


def _current_course_sku():
    """Legge il course_sku registrato per questo esercizio sulla macchina
    corrente (~/.grading/lab_manifest.json), per capire quale dei due corsi
    collidenti e' installato qui. Stringa vuota se non determinabile."""
    manifest_path = os.path.expanduser("~/.grading/lab_manifest.json")
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ""
    return (manifest.get(LAB_NAME) or {}).get("course_sku", "")


# ============================== RH124 (rh0016l) ==============================

_RH124_HOST = "servera"

_RH124_MEDIA_DIRS = {
    "Music": [f"song{i}.mp3" for i in range(1, 7)],
    "Pictures": [f"snap{i}.jpg" for i in range(1, 7)],
    "Videos": [f"film{i}.avi" for i in range(1, 7)],
}
_RH124_CLEANED_UP_DIRS = ["friends", "family", "work"]


def main_rh124():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (RH124, host: {_RH124_HOST})")

    for directory, files in _RH124_MEDIA_DIRS.items():
        with GradingStep(f"~/{directory} contiene i file attesi") as step:
            for f in files:
                if not file_exists(f"~/{directory}/{f}", host=_RH124_HOST):
                    step.add_error(f"Manca ~/{directory}/{f}")

    for directory in _RH124_CLEANED_UP_DIRS:
        with GradingStep(f"~/{directory} e' stata rimossa (pulizia finale)") as step:
            if file_exists(f"~/{directory}", host=_RH124_HOST):
                step.fail(
                    f"~/{directory} esiste ancora: il passo 7.2 (rm -rf) non e' stato completato"
                )

    with GradingStep("Nessun file multimediale residuo nella home") as step:
        result = run("ls ~/*.mp3 ~/*.jpg ~/*.avi 2>/dev/null", host=_RH124_HOST)
        leftover = result.stdout.strip()
        if leftover:
            step.add_error(f"File non spostati trovati nella home: {leftover}")


# ============================== AU294 (au0023l) ==============================

_FTP_SERVERS = ["serverc", "serverd"]

# Valori delle variabili fissati dalla guida (Tabella 18, pag. 300): li usiamo
# per sapere COSA cercare come effetto, non per gradare il testo YAML.
_FTP_PACKAGE = "vsftpd"
_FTP_CONFIG = "/etc/vsftpd/vsftpd.conf"
_FTP_SERVICE = "vsftpd"
_FIREWALL_SERVICE = "ftp"
_FTP_USER = "demoftp"
_UPLOAD_PATH = "/home/demoftp/upload"


def read_remote_file(path, host, sudo=False):
    """Legge un file su un host remoto via SSH. Ritorna None se non esiste
    o il comando fallisce."""
    result = run(f"cat {path}", host=host, sudo=sudo)
    if result.returncode != 0:
        return None
    return result.stdout


def stat_owner_group_mode(path, host, sudo=False):
    """Ritorna (owner, group, mode_ottale_3cifre) di un path remoto, o None."""
    result = run(f"stat -c '%U %G %a' {path}", host=host, sudo=sudo)
    if result.returncode != 0:
        return None
    parts = result.stdout.strip().split()
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def firewalld_service_permanent(service, host):
    """True se il servizio e' abilitato PERMANENTEMENTE nel firewalld di
    quell'host (richiede lettura della configurazione persistita, serve
    sudo)."""
    return command_ok(
        f"firewall-cmd --permanent --query-service={service}",
        host=host, sudo=True,
    )


def find_task(tasks, name):
    """Cerca un task per nome esatto in una lista di task di un play YAML
    gia' decodificato. Ritorna il dict del task, o None."""
    for task in tasks or []:
        if isinstance(task, dict) and task.get("name") == name:
            return task
    return None


def local_log_fetched(workdir, min_size=10000):
    """True se sotto <workdir>/serverc.lab.example.com/var/log/ esiste
    almeno un file *.log (ricorsivo) piu' grande di min_size byte: prova che
    il task 'Fetch all the files found' di file-operations.yml e' stato
    eseguito con successo (l'esatto elenco di file dipende dallo stato
    corrente di /var/log su serverc, quindi non e' fissabile a priori)."""
    fetch_dir = os.path.join(workdir, "serverc.lab.example.com", "var", "log")
    if not os.path.isdir(fetch_dir):
        return False
    for root, _dirs, files in os.walk(fetch_dir):
        for fname in files:
            if fname.endswith(".log"):
                full = os.path.join(root, fname)
                try:
                    if os.path.getsize(full) > min_size:
                        return True
                except OSError:
                    continue
    return False


def main_au294():
    exercise_dir = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    workdir = os.path.expanduser(f"~/{exercise_dir}")
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (AU294, dir: {workdir})")

    vsftpd_playbook = os.path.join(workdir, "vsftpd-server.yml")
    file_ops_playbook = os.path.join(workdir, "file-operations.yml")

    with GradingStep("I playbook vsftpd-server.yml e file-operations.yml esistono") as step:
        if not os.path.exists(vsftpd_playbook):
            step.add_error(f"'{vsftpd_playbook}' non trovato")
        if not os.path.exists(file_ops_playbook):
            step.add_error(f"'{file_ops_playbook}' non trovato")

    # --- Effetto reale di vsftpd-server.yml su serverc/serverd (task 1-7) ---

    with GradingStep(f"Pacchetto {_FTP_PACKAGE} installato su {', '.join(_FTP_SERVERS)} (task 1)") as step:
        for host in _FTP_SERVERS:
            if not package_installed(_FTP_PACKAGE, host=host):
                step.add_error(f"Pacchetto '{_FTP_PACKAGE}' non installato su {host}")

    with GradingStep(f"anonymous_enable=YES impostato in {_FTP_CONFIG} (task 2)") as step:
        for host in _FTP_SERVERS:
            content = read_remote_file(_FTP_CONFIG, host=host, sudo=True)
            if content is None:
                step.add_error(f"Impossibile leggere '{_FTP_CONFIG}' su {host}")
            elif "anonymous_enable=YES" not in content:
                step.add_error(f"Riga 'anonymous_enable=YES' non trovata su {host}")

    with GradingStep(f"Blocco anonymous upload aggiunto in {_FTP_CONFIG} (task 3)") as step:
        expected_lines = [
            "anon_upload_enable=YES",
            "anon_mkdir_write_enable=YES",
            "xferlog_file=/var/log/xferlog",
        ]
        for host in _FTP_SERVERS:
            content = read_remote_file(_FTP_CONFIG, host=host, sudo=True)
            if content is None:
                step.add_error(f"Impossibile leggere '{_FTP_CONFIG}' su {host}")
                continue
            missing = [line for line in expected_lines if line not in content]
            if missing:
                step.add_error(f"Righe mancanti su {host}: {missing}")

    with GradingStep(f"Servizio {_FTP_SERVICE} avviato e abilitato (task 4)") as step:
        for host in _FTP_SERVERS:
            if not service_is_active(_FTP_SERVICE, host=host):
                step.add_error(f"Servizio '{_FTP_SERVICE}' non attivo su {host}")
            if not service_is_enabled(_FTP_SERVICE, host=host):
                step.add_error(f"Servizio '{_FTP_SERVICE}' non abilitato su {host}")

    with GradingStep(f"Servizio {_FIREWALL_SERVICE} abilitato permanentemente nel firewall (task 5)") as step:
        for host in _FTP_SERVERS:
            if not firewalld_service_permanent(_FIREWALL_SERVICE, host=host):
                step.add_error(f"Servizio firewalld '{_FIREWALL_SERVICE}' non permanente su {host}")

    with GradingStep(f"Directory {_UPLOAD_PATH} creata con owner/group {_FTP_USER} e mode 0755 (task 6)") as step:
        for host in _FTP_SERVERS:
            info = stat_owner_group_mode(_UPLOAD_PATH, host=host, sudo=True)
            if info is None:
                step.add_error(f"Directory '{_UPLOAD_PATH}' non trovata su {host}")
                continue
            owner, group, mode = info
            if owner != _FTP_USER or group != _FTP_USER:
                step.add_error(f"Owner/group '{_UPLOAD_PATH}' su {host} = {owner}:{group}, attesi {_FTP_USER}:{_FTP_USER}")
            if mode != "755":
                step.add_error(f"Mode '{_UPLOAD_PATH}' su {host} = {mode}, atteso 755")

    with GradingStep(f"File testfile copiato in {_UPLOAD_PATH} con owner/group {_FTP_USER} e mode 0644 (task 7)") as step:
        local_testfile = os.path.join(workdir, "files", "testfile")
        try:
            with open(local_testfile) as f:
                expected_content = f.read()
        except OSError:
            step.fail(f"File locale '{local_testfile}' non trovato: impossibile confrontare il contenuto")
            expected_content = None

        if expected_content is not None:
            remote_path = f"{_UPLOAD_PATH}/testfile"
            for host in _FTP_SERVERS:
                info = stat_owner_group_mode(remote_path, host=host, sudo=True)
                if info is None:
                    step.add_error(f"File '{remote_path}' non trovato su {host}")
                    continue
                owner, group, mode = info
                if owner != _FTP_USER or group != _FTP_USER:
                    step.add_error(f"Owner/group '{remote_path}' su {host} = {owner}:{group}, attesi {_FTP_USER}:{_FTP_USER}")
                if mode != "644":
                    step.add_error(f"Mode '{remote_path}' su {host} = {mode}, atteso 644")
                remote_content = read_remote_file(remote_path, host=host, sudo=True)
                if remote_content is None:
                    step.add_error(f"Impossibile leggere '{remote_path}' su {host}")
                elif remote_content.strip() != expected_content.strip():
                    step.add_error(f"Contenuto di '{remote_path}' su {host} diverso da files/testfile")

    # --- file-operations.yml: struttura per i task senza stato persistente ---

    if os.path.exists(file_ops_playbook):
        import yaml

        try:
            with open(file_ops_playbook) as f:
                docs = yaml.safe_load(f)
            play = docs[0] if isinstance(docs, list) and docs else {}
        except (OSError, yaml.YAMLError):
            play = {}

        tasks = play.get("tasks") or []

        with GradingStep("Play 'Testing File Operations' definito su serverc.lab.example.com con become true") as step:
            if play.get("hosts") != "serverc.lab.example.com":
                step.add_error(f"hosts = {play.get('hosts')!r}, atteso 'serverc.lab.example.com'")
            if play.get("become") is not True:
                step.add_error(f"become = {play.get('become')!r}, atteso true")

        with GradingStep("Task ansible.builtin.stat su /var/log/xferlog registrato in xferlog_info (task 1)") as step:
            task = find_task(tasks, "Gathering stat of xferlog")
            if task is None:
                step.fail("Task 'Gathering stat of xferlog' non trovato")
            else:
                stat_args = task.get("ansible.builtin.stat") or {}
                if stat_args.get("path") != "/var/log/xferlog":
                    step.add_error(f"path = {stat_args.get('path')!r}, atteso '/var/log/xferlog'")
                if task.get("register") != "xferlog_info":
                    step.add_error(f"register = {task.get('register')!r}, atteso 'xferlog_info'")

        with GradingStep("Task ansible.builtin.debug stampa il checksum condizionatamente all'esistenza del file (task 2)") as step:
            task = find_task(tasks, "Printing the checksum")
            if task is None:
                step.fail("Task 'Printing the checksum' non trovato")
            else:
                debug_args = task.get("ansible.builtin.debug") or {}
                var_expr = str(debug_args.get("var", ""))
                when_expr = str(task.get("when", ""))
                if "xferlog_info" not in var_expr or "checksum" not in var_expr:
                    step.add_error(f"var = {var_expr!r}, atteso un riferimento a xferlog_info[...][checksum]")
                if "xferlog_info" not in when_expr or "exists" not in when_expr:
                    step.add_error(f"when = {when_expr!r}, atteso un riferimento a xferlog_info[...][exists]")

        with GradingStep("Task ansible.builtin.find su /var/log con pattern *.log, recurse e size 10000 (task 3)") as step:
            task = find_task(tasks, "Find all log files larger than 10k")
            if task is None:
                step.fail("Task 'Find all log files larger than 10k' non trovato")
            else:
                find_args = task.get("ansible.builtin.find") or {}
                if str(find_args.get("paths", "")).rstrip("/") != "/var/log":
                    step.add_error(f"paths = {find_args.get('paths')!r}, atteso '/var/log/'")
                if find_args.get("patterns") != "*.log":
                    step.add_error(f"patterns = {find_args.get('patterns')!r}, atteso '*.log'")
                if find_args.get("recurse") is not True:
                    step.add_error(f"recurse = {find_args.get('recurse')!r}, atteso true")
                if find_args.get("size") != 10000:
                    step.add_error(f"size = {find_args.get('size')!r}, atteso 10000")
                if task.get("register") != "found_logs":
                    step.add_error(f"register = {task.get('register')!r}, atteso 'found_logs'")

        with GradingStep("Task ansible.builtin.fetch scarica in loop i file trovati (task 4)") as step:
            task = find_task(tasks, "Fetch all the files found")
            if task is None:
                step.fail("Task 'Fetch all the files found' non trovato")
            else:
                fetch_args = task.get("ansible.builtin.fetch") or {}
                src_expr = str(fetch_args.get("src", ""))
                loop_expr = str(task.get("loop", ""))
                if "item" not in src_expr or "path" not in src_expr:
                    step.add_error(f"src = {src_expr!r}, atteso un riferimento a item['path']")
                if str(fetch_args.get("dest", "")) not in ("./", "."):
                    step.add_error(f"dest = {fetch_args.get('dest')!r}, atteso './'")
                if "found_logs" not in loop_expr or "files" not in loop_expr:
                    step.add_error(f"loop = {loop_expr!r}, atteso un riferimento a found_logs['files']")

        with GradingStep("Almeno un file *.log >10000 byte scaricato localmente da serverc (effetto del task fetch)") as step:
            if not local_log_fetched(workdir):
                step.fail(
                    f"Nessun file *.log >10000 byte trovato sotto "
                    f"'{os.path.join(workdir, 'serverc.lab.example.com', 'var', 'log')}'"
                )


def main():
    sku = _current_course_sku()
    if sku.startswith("au"):
        main_au294()
    else:
        # Default a RH124: sku vuoto (manifest non ancora popolato/non
        # leggibile) o sku "rh...".
        main_rh124()


if __name__ == "__main__":
    main()
