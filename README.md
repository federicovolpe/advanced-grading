# Lab Grade Monitor & Custom Grading

Strumenti nati per il corso Red Hat **DO180 (Red Hat OpenShift Administration
I)**, ma il meccanismo è generico: qualunque corso eseguito con lo stesso tool
`lab` (rpm `lab-service`) può avere script di grading custom aggiunti qui
(vedi [CLAUDE.md](CLAUDE.md) per estenderlo ad altri corsi). Oggi il repo
copre anche **DO280 (Red Hat OpenShift Administration II)**, **DO380 (Red
Hat OpenShift Administration III)**, **RH124 (Red Hat System Administration
I)** e **RH134 (Red Hat System Administration II)**. Risolvono due problemi:

1. **Nessun feedback visivo dopo `lab start`.** Un monitor grafico (Tkinter) si apre automaticamente e mostra, come una fila di semafori, l'esito di `lab grade` aggiornato periodicamente.
2. **Molte guided exercise non hanno un `lab grade` ufficiale.** Un wrapper attorno al comando `lab` intercetta la risposta `"The grade command is not supported for this lab."` e, se esiste, esegue al suo posto uno script di grading "custom" scritto per quell'esercizio specifico.

Tutto è pensato per essere trasparente: se un esercizio ha già un grading ufficiale, il comportamento di `lab` non cambia in alcun modo.

## Installazione

```bash
git clone --depth 1 https://github.com/federicovolpe/advanced-grading.git /tmp/do180-lab-grading
bash /tmp/do180-lab-grading/install.sh
```

Poi apri un nuovo terminale (o esegui `source ~/.bashrc`) perché il wrapper sia attivo nella shell corrente.

**Requisito per il monitor grafico**: `python3-tkinter`. Se manca, l'installer lo segnala; un amministratore deve installarlo con:

```bash
sudo dnf install python3-tkinter -y
```

Il fallback di grading su `lab grade` funziona comunque anche senza tkinter (è solo il monitor grafico a richiederlo).

### Aggiornare un'installazione esistente

Rilanciare l'installer sovrascrive i file con la versione corrente del repo:

```bash
git -C /tmp/do180-lab-grading pull
bash /tmp/do180-lab-grading/install.sh
```

## Cosa installa

| File/cartella sorgente | Destinazione | Scopo |
|---|---|---|
| `bin/lab_grade_monitor.py` | `~/.local/bin/lab_grade_monitor.py` | Monitor grafico a semafori per `lab grade` |
| `bashrc.d/lab-grade-monitor.sh` | `~/.bashrc.d/lab-grade-monitor.sh` | Wrapper della funzione `lab` (intercetta `start` e `grade`) |
| `lab-custom-grading/*.py` | `~/.local/share/lab-custom-grading/*.py` | Script di grading custom, uno per esercizio |

## Come funziona il wrapper

La funzione bash `lab()` (definita in `bashrc.d/lab-grade-monitor.sh`) sostituisce il comando `lab` nella shell:

- **`lab start <nome>`**: esegue il comando reale, poi lancia in background `lab_grade_monitor.py <nome>` (solo se c'è un display grafico disponibile).
- **`lab grade <nome>`**: esegue il comando reale e ne mostra l'output. Se la risposta contiene `"The grade command is not supported for this lab."`, cerca `~/.local/share/lab-custom-grading/<nome>.py` e, se esiste, lo esegue al posto del grading ufficiale.
- Qualsiasi altro sottocomando passa invariato al binario originale (`command lab ...`).

Il monitor grafico chiama `lab grade` passando dalla shell (sourciando il wrapper), non invocando direttamente il binario: così il fallback su grading custom scatta anche dalla finestra del monitor, non solo da terminale.

## Libreria condivisa per i grading custom (`_common.py`)

Ogni script di grading custom segue lo stesso schema, ricalcato sull'API usata nei grading ufficiali Red Hat Training (`labs.ui.GradingStep`):

```python
from _common import GradingStep, oc_get_json, project_exists

with GradingStep("Titolo del check") as step:
    if qualcosa_non_va:
        step.add_error("messaggio specifico")   # segna FAIL e aggiunge un dettaglio
    if condizione_grave:
        step.fail("messaggio")                  # segna FAIL direttamente
```

All'uscita dal blocco `with`, viene stampato automaticamente:

```
PASS Titolo del check
```
oppure
```
FAIL Titolo del check
        - messaggio specifico
```

Questo formato (`PASS`/`FAIL <titolo>` + dettagli indentati di 8 spazi) è compatibile con il parser di `lab_grade_monitor.py`, quindi i risultati appaiono correttamente anche come semafori nella finestra grafica.

`_common.py` fornisce inoltre:
- `oc_get_json(*args)` — esegue `oc get <args> -o json` e ritorna il dict Python, o `None` se la risorsa non esiste. (OpenShift/DO180)
- `project_exists(name)` — controlla se un progetto OpenShift esiste. (OpenShift/DO180)
- `run(command, host="workstation", sudo=False)` — esegue un comando in locale o su un host della classroom (`servera`/`serverb`) via `ssh`, per corsi non-OpenShift come RH124/RH134.
- `command_ok`, `user_exists`, `group_exists`, `package_installed`, `service_is_active`, `service_is_enabled`, `file_exists` — helper generici costruiti su `run()` per i controlli RHCSA più comuni.

## Esercizi coperti

### DO180 (Red Hat OpenShift Administration I)

Script di grading scritti (in `lab-custom-grading/`):

- `reliability-probes`, `reliability-requests`, `reliability-limits`, `reliability-autoscaling`
- `deploy-newapp`, `deploy-services`
- `storage-statefulsets`, `storage-volumes`, `storage-configs`
- `updates-rollout`, `updates-triggers`, `updates-imagestreams`
- `intro-navigate`, `pods-troubleshooting`
- `pods-containers` — **check "sul momento", non a posteriori**: la guida (Cap. 3.2) fa cancellare quasi tutti i pod creati, ma lascia deliberatamente `ubi9-command` in esecuzione fino a `lab finish`. Lo script grada quello stato live; dopo `lab finish` il progetto non esiste più ed è corretto che torni FAIL.

**Nota**: alcuni script sono stati scritti senza accesso al testo ufficiale della guida studente, basandosi solo su file di partenza/soluzione presenti in cache e su `resources.txt`. Quando il testo della guida è stato poi fornito (es. `reliability-autoscaling`, `pods-troubleshooting`, `pods-containers`), gli script sono stati raffinati/corretti con i valori esatti. Se noti un FAIL su un lavoro che ritieni corretto, probabilmente lo script va tarato meglio — apri una issue o modifica direttamente il file.

Esercizi guidati **senza** grading ufficiale né custom (giudicati non gradabili in modo oggettivo: sono esercizi puramente esplorativi da CLI/console, senza uno stato — nemmeno temporaneo — univoco sul cluster, oppure privi di materiali sufficienti a dedurre una specifica): `cli-health`, `cli-interfaces`, `cli-resources`, `deploy-routes`, `deploy-workloads`, `intro-monitor`, `pods-images`, `storage-classes`, `reliability-ha`, `updates-ids`. **Da riverificare con il testo della guida** (lo stesso errore di giudizio di `pods-containers` — dedotto senza leggere il manuale — potrebbe valere anche per alcuni di questi).

### DO280 (Red Hat OpenShift Administration II)

Tutte le 19 guided exercise del corso che non hanno un `lab grade` ufficiale sono coperte:

- Cap. 1 Declarative Resource Management: `declarative-manifests`, `declarative-kustomize`
- Cap. 2 Deploying Packaged Applications: `packaged-templates`, `packaged-charts`
- Cap. 3 Authentication and Authorization: `auth-providers`, `auth-rbac`
- Cap. 4 Network Security: `network-ingress`, `network-policy`, `network-svccerts`
- Cap. 5 Exposing non-HTTP/SNI Applications: `non-http-lb`, `non-http-multus`
- Cap. 6 Enabling Developer Self-service: `selfservice-quotas`, `selfservice-ranges`, `selfservice-projtemplate`
- Cap. 7 Managing Kubernetes Operators: `operators-web`, `operators-cli`
- Cap. 8 Application Security: `appsec-scc`, `appsec-api`, `appsec-prune`

Scritti a partire dal testo integrale della guida studente (PDF ufficiale DO280-RHOCP4.18-en-1-20251205) incrociato con `materials/labs`/`materials/solutions` del pacchetto `rht-labs-do280`, quando presenti. Alcuni esercizi non avevano alcun materiale in cache (`packaged-charts`, `auth-rbac`, `selfservice-quotas`, `selfservice-ranges`, `appsec-scc`): i relativi script si basano solo sul testo della guida, e alcuni dettagli non documentati con precisione (es. valori CPU non menzionati in `selfservice-ranges`) sono stati volutamente omessi invece di essere inventati — vedi i commenti in testa a ciascun file. `appsec-prune.py` documenta una discrepanza reale trovata fra `materials/solutions/appsec-prune/rbac-prune.yaml` e il testo della guida (percorso RBAC diverso): è stato seguito il testo della guida, più affidabile.

### DO380 (Red Hat OpenShift Administration III)

Tutte le 17 guided exercise del corso che non hanno un `lab grade` ufficiale sono coperte (le 8 "review" di fine capitolo e la comprehensive review hanno già un `lab grade` ufficiale, non toccate):

- Cap. 1 Authentication and Identity Management: `auth-ldap`, `auth-sync`, `auth-oidc`, `auth-conflict`, `auth-tls`
- Cap. 2 Backup, Restore, and Migration of Applications with OADP: `backup-export`, `backup-oadp`, `backup-restore`
- Cap. 3 Pod Scheduling: `scheduling-selector`, `scheduling-pdb`
- Cap. 4 OpenShift GitOps: `gitops-admin`, `gitops-app`
- Cap. 5 OpenShift Monitoring: `monitoring-alerts`
- Cap. 6 Logging for Red Hat OpenShift: `logging-forward`, `logging-central`
- Cap. 7 Cluster Partitioning: `nodes-mco`, `nodes-operators`

Scritti a partire dal testo integrale della guida studente (PDF ufficiale DO380-RHOCP4.18-en-2-20260525) incrociato con `materials/labs`/`materials/solutions` del pacchetto `do380` (installato con `lab install do380`, senza mai eseguire `lab start` durante l'analisi). La maggior parte degli esercizi aveva una cartella `materials/solutions` completa e non ambigua (ogni placeholder `CHANGE_ME` ha un solo valore plausibile), usata come specifica primaria; per `auth-ldap`, `auth-tls`, `monitoring-alerts` e `monitoring-cluster`, privi di `materials/solutions`, si è seguito solo il testo della guida. Alcuni script notano esplicitamente valori intenzionalmente non gradati perché non specificati con precisione in nessuna fonte (es. gli attributi `id`/`name`/`preferredUsername` dell'IdP LDAP in `auth-ldap`, o il contenuto del backup su PVC in `gitops-app`).

`auth-sync.py` documenta una discrepanza reale fra `materials/solutions/auth-sync/` (che usa un namespace `auth-group-sync` mai citato né creato da alcun comando nel testo) e la guida ufficiale: è stato seguito il testo della guida, più affidabile, come già fatto per `appsec-prune` in DO280.

`auth-tls.py` e `scheduling-selector.py` (per il taint su worker01/worker03) sono check **"sul momento"**, validi solo prima di `lab finish` (vedi CLAUDE.md sez.2): la guida lascia deliberatamente una CRON job attiva e un taint applicato fino alla fine dell'esercizio.

Esercizi guidati DO380 **senza** grading ufficiale né custom (non gradabili in modo oggettivo): `intro-monitor` (non è referenziato da nessun capitolo della guida in questa edizione del corso — il modulo ufficiale crea e cancella solo un progetto vuoto, nessuno stato da verificare) e `monitoring-cluster` (Cap. 5.2: l'intera guided exercise è un'attività di sola lettura tramite dashboard web console e query Prometheus per diagnosticare un'app e un nodo NotReady preconfigurati da `start()` — nessuna modifica richiesta allo studente, nessuno stato univoco verificabile via `oc`).

### RH124 (Red Hat System Administration I)

Nessuno di questi esercizi ha `materials/solutions/` né un `resources.txt`
utile in cache (sono guided exercise puramente CLI): la specifica è stata
ricavata dal testo della guida ufficiale (PDF `RH124_..._en_10.0.pdf`),
citando sezione/pagina nel docstring di ogni script.

- `lightspeed-assistant` (5.2), `files-manage` (7.2), `users-user` (10.6),
  `software-dnf` (12.4), `flatpak-configure` (13.2), `processes-kill` (15.6),
  `processes-monitor` (15.8), `services-control` (16.4), `net-configure` (18.2),
  `net-edit` (18.4)

Esercizi guidati RH124 **senza** grading ufficiale né custom (non gradabili
in modo oggettivo: puro `man`/`locate`/`find` esplorativo su stato
preesistente della VM, nessuno stato persistente attribuibile allo
studente):
- `help-manual` (3.2) — solo consultazione di man page, nessun output verificabile a posteriori.
- `fs-locate` (14.6) — solo interrogazioni `locate`/`find` in lettura; anche `updatedb` non è un segnale valido perché il DB di `plocate` viene aggiornato comunque da un timer di sistema indipendente.

### RH134 (Red Hat System Administration II)

Come per RH124, nessuno di questi esercizi ha `materials/solutions/` né un
`resources.txt` utile in cache: la specifica è stata ricavata dal testo
della guida ufficiale (PDF `RH134_..._en_10.0.pdf`), citando sezione/pagina
nel docstring di ogni script. Gira su `servera`/`serverb`/`workstation` a
seconda dell'esercizio; alcuni esercizi del capitolo 16/18 (installazione
RHEL/image mode) dipendono da un host `serverc` che non esiste finché
l'installazione (interattiva o via Kickstart) non è completata — il
grading verifica lo stato solo quando `serverc` diventa raggiungibile via
SSH, senza mai bloccare (vedi il timeout SSH aggiunto a `run()` in
`_common.py`).

- Cap. 1: `scripts-env`, `scripts-write`, `scripts-loops`
- Cap. 2: `regexes-regex`
- Cap. 3: `scheduling-at`, `scheduling-cron`
- Cap. 4: `systasks-timers`, `systasks-tempfiles`, `systasks-syscron`
- Cap. 5: `logs-syslog`, `logs-preserve`, `logs-maintain`
- Cap. 6: `selinux-opsmode`, `selinux-filecontexts`, `selinux-booleans`, `selinux-issues`
- Cap. 7: `archive-manage`
- Cap. 8: `rcopy-sync`
- Cap. 9: `tuning-profiles`
- Cap. 10: `storage-partitions`, `storage-swap`
- Cap. 11: `lvm-create`, `lvm-extend`
- Cap. 12: `boot-grub`, `boot-selecting`, `boot-repairing`
- Cap. 13: `rootpw-recover`
- Cap. 14: `netsecurity-firewalls`, `netsecurity-ports`
- Cap. 15: `nfsclient-nfs`, `nfsclient-autofs`
- Cap. 16: `installing-install`, `installing-kickstart`
- Cap. 17: `containers-image`
- Cap. 18: `image-bootable`, `image-server`, `image-manage`

Alcuni esercizi fanno un "giro completo" (portano il sistema a uno stato
che coincide con quello iniziale, es. `selinux-opsmode`, `boot-grub`,
`boot-selecting`, `rootpw-recover`): il check verifica comunque lo stato
finale corretto, ma non distingue "mai fatto" da "fatto e ripristinato
correttamente" — è un limite intrinseco documentato nel docstring di
ciascuno di questi script.

Esercizi guidati RH134 **senza** grading ufficiale né custom (non
gradabili in modo oggettivo):
- `logs-systemd` (5.6) — solo query `journalctl` in lettura, nessuno stato persistente.
- `tuning-nice` (9.4) — tutti i processi di test vengono terminati esplicitamente a fine esercizio, nessun residuo.
- `containers-podman` (17.4) — round-trip completo (crea, verifica, rimuove tutti i container), nessuno stato finale distintivo.

### DO432 (Multicluster Management with Red Hat Advanced Cluster Management for Kubernetes)

A differenza degli altri corsi qui sopra, DO432 gestisce SEMPRE due cluster OpenShift distinti (il hub RHACM e un "managed cluster"): `_common.py` espone `oc_get_json_hub`/`oc_get_json_managed`/`project_exists_hub`/`project_exists_managed` (kubeconfig cache in `~/.auth/ocp4-kubeconfig`/`~/.auth/ocp4-mng-kubeconfig`, popolati da `start()` tramite `rht-labs-acm`, indipendenti da dove sia loggata la sessione `oc` corrente dello studente) e `condition_true` (per CR con `status.conditions` standard, es. `ManagedCluster`).

17 delle 18 guided exercise del corso senza `lab grade` ufficiale sono coperte (le 5 "review" di fine capitolo hanno già un `lab grade` ufficiale, non toccate). **Nota**: `virtualization-manage` e `virtualization-monitor` non compaiono in `~/.grading/lab_manifest.json` di questa macchina — quel file è un tracker di curriculum incompleto, non autoritativo — ma esistono come guided exercise reali (moduli con `__LAB__`, materiali dedicati, GE 6.6/6.8 nella guida) e sono quindi gradati comunque, seguendo CLAUDE.md step 1 (il pacchetto installato come fonte di verità).

- Cap. 1 Installing RHACM: `install-rhacm`
- Cap. 2 Managing Multiple Clusters: `manage-navigate`, `manage-configure`, `manage-troubleshoot`
- Cap. 3 Governance and Policies: `policies-deploy`, `policies-generator`, `policies-compliance`, `policies-integration`, `policies-troubleshoot`
- Cap. 4 Observability: `observability-enable`, `observability-customize`
- Cap. 5 Application Lifecycle Management with GitOps: `gitops-configure`, `gitops-deploy`, `gitops-troubleshoot`
- Cap. 6 OpenShift Virtualization with RHACM: `virtualization-deploy`, `virtualization-manage`, `virtualization-monitor`

Scritti a partire dal testo integrale della guida studente (PDF ufficiale DO432-RHACM2.13-en-2) incrociato con `materials/labs`/`materials/solutions` dei pacchetti `do0011l`..`do0016l`, quando presenti (`policies-generator`, `gitops-deploy` e `install-rhacm` non hanno alcun materiale in cache — script basati solo sul testo guida). Nessun cluster era raggiungibile da questa macchina durante la scrittura (kubeconfig assente): nessuno script è stato testato end-to-end, solo analisi statica.

Diversi esercizi fanno un "giro completo" (creano poi cancellano la risorsa principale prima di `lab finish`): il check grada il segnale persistente che resta comunque (es. `manage-configure` grada le `ClusterRoleBinding` orfane rimaste dopo la cancellazione dei ManagedClusterSet, `policies-deploy` grada il certificato TLS rinnovato invece della Policy transitoria che lo studente cancella allo step 7). `observability-customize` e i tre esercizi di virtualizzazione sono check **"sul momento"**, validi solo prima di `lab finish` (la guida cancella l'intera stack/i progetti a fine esercizio).

`install-rhacm` è un caso opposto: l'installazione di RHACM non viene rimossa da nessun `finish()` successivo (resta infrastruttura condivisa per tutto il corso), quindi il check resta valido anche a lunga distanza da quell'esercizio, non solo "sul momento".

Esercizio guidato DO432 **senza** grading ufficiale né custom (non gradabile in modo oggettivo): `manage-lifecycle` (2.2) — la guida importa poi scollega (`detach`) il managed cluster prima di `lab finish` (e `start()` lo lascia già scollegato), quindi lo stato finale è indistinguibile da "esercizio non svolto" — stesso giudizio di `containers-podman` in RH134.

## Aggiungere il grading per un nuovo esercizio

1. Crea `~/.local/share/lab-custom-grading/<nome-esercizio>.py` (o direttamente in `lab-custom-grading/` in questo repo).
2. Usa `reliability-probes.py` o `reliability-requests.py` come modello di partenza.
3. Determina il nome del progetto OpenShift (di solito uguale al nome dell'esercizio) e le risorse da controllare, confrontando i file di partenza e la soluzione ufficiale del corso (quando disponibili), oppure il testo della guida studente.
4. Accetta opzionalmente il nome del progetto come primo argomento da linea di comando (default = nome esercizio), per restare coerente con gli altri script.
5. Nessuna modifica al wrapper è necessaria: il fallback lo trova automaticamente in base al nome del file.
