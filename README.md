# DO180/DO280 Lab Grade Monitor & Custom Grading

Strumenti nati per il corso Red Hat **DO180 (Red Hat OpenShift Administration I)**, poi estesi anche a **DO280 (Red Hat OpenShift Administration II)**, che risolvono due problemi (il meccanismo è generico, vedi [CLAUDE.md](CLAUDE.md) per estenderlo ad altri corsi):

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
- `oc_get_json(*args)` — esegue `oc get <args> -o json` e ritorna il dict Python, o `None` se la risorsa non esiste.
- `project_exists(name)` — controlla se un progetto OpenShift esiste.

## Esercizi coperti

Script di grading scritti (in `lab-custom-grading/`):

- `reliability-probes`, `reliability-requests`, `reliability-limits`, `reliability-autoscaling`
- `deploy-newapp`, `deploy-services`
- `storage-statefulsets`, `storage-volumes`, `storage-configs`
- `updates-rollout`, `updates-triggers`, `updates-imagestreams`
- `intro-navigate`, `pods-troubleshooting`

**Nota**: alcuni script sono stati scritti senza accesso al testo ufficiale della guida studente, basandosi solo su file di partenza/soluzione presenti in cache e su `resources.txt`. Quando il testo della guida è stato poi fornito (es. `reliability-autoscaling`, `pods-troubleshooting`), gli script sono stati raffinati con i valori esatti. Se noti un FAIL su un lavoro che ritieni corretto, probabilmente lo script va tarato meglio — apri una issue o modifica direttamente il file.

Esercizi guidati **senza** grading ufficiale né custom (giudicati non gradabili in modo oggettivo: sono esercizi puramente esplorativi da CLI/console, senza uno stato finale univoco sul cluster, oppure privi di materiali sufficienti a dedurre una specifica): `cli-health`, `cli-interfaces`, `cli-resources`, `deploy-routes`, `deploy-workloads`, `intro-monitor`, `pods-containers`, `pods-images`, `storage-classes`, `reliability-ha`, `updates-ids`.

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

## Aggiungere il grading per un nuovo esercizio

1. Crea `~/.local/share/lab-custom-grading/<nome-esercizio>.py` (o direttamente in `lab-custom-grading/` in questo repo).
2. Usa `reliability-probes.py` o `reliability-requests.py` come modello di partenza.
3. Determina il nome del progetto OpenShift (di solito uguale al nome dell'esercizio) e le risorse da controllare, confrontando i file di partenza e la soluzione ufficiale del corso (quando disponibili), oppure il testo della guida studente.
4. Accetta opzionalmente il nome del progetto come primo argomento da linea di comando (default = nome esercizio), per restare coerente con gli altri script.
5. Nessuna modifica al wrapper è necessaria: il fallback lo trova automaticamente in base al nome del file.
