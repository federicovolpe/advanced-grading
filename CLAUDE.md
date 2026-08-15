# Istruzioni per Claude — contribuire grading a nuovi corsi

Questo repo nasce per DO180 ma il meccanismo è generico: qualunque corso Red Hat
Training eseguito con lo stesso tool `lab` (rpm `lab-service`) può avere script
di grading custom aggiunti qui, per le guided exercise che non hanno un
`lab grade` ufficiale. Se sei un'istanza Claude aperta su una macchina di un
altro corso (DO280, DO0018L, DO0019L, ecc.) e l'utente ti ha chiesto di
contribuire, leggi questo file per intero prima di scrivere qualsiasi script.

Il README.md spiega installazione e architettura del wrapper: leggilo prima
se non l'hai già fatto. Qui invece c'è la METODOLOGIA per scrivere nuovi
script di grading, passo per passo, com'è stata effettivamente applicata per
i 24 esercizi DO180 già presenti in `lab-custom-grading/`.

## 0. Premessa: non serve toccare il wrapper

Il meccanismo di fallback (`~/.bashrc.d/lab-grade-monitor.sh`, installato da
`install.sh`) è già generico e funziona per qualunque corso senza modifiche:
intercetta `lab grade <nome-esercizio>`, e se il comando ufficiale risponde
`"The grade command is not supported for this lab."`, cerca
`~/.local/share/lab-custom-grading/<nome-esercizio>.py` e lo esegue. Per
contribuire un nuovo corso basta AGGIUNGERE file in `lab-custom-grading/`,
non modificare nient'altro.

## 1. Trova il materiale del corso

Ogni corso è un pacchetto Python installato via `uv`, la cui cache si trova
tipicamente in:

```
~/.cache/uv/archive-v0/<hash>/<codice-corso>/
```

dove `<codice-corso>` è tipo `do180`, `do280`, `do0018l`, `bfx001`, ecc.
(l'elenco dei pacchetti installati compare anche nel messaggio di errore di
`lab` quando dai un nome esercizio inesistente: "Available packages: [...]").

Dentro quella cartella trovi, per ogni esercizio:

- `<nome-esercizio>.py` — il modulo ufficiale: una classe che eredita da
  `GuidedExercise` (o simile) con metodi `start()`/`finish()` e, se presente,
  `grade()`. Se `grade()` manca, l'esercizio è un candidato per il grading
  custom.
- `common/` — funzioni condivise dal corso (nomi di progetto, step comuni,
  gestione immagini, ecc.) — utile per capire le convenzioni, ma non perderci
  troppo tempo.
- `materials/labs/<nome-esercizio>/` — i file di partenza copiati allo
  studente da `start()` (se presenti — molti esercizi puramente CLI non ne
  hanno).
- `materials/solutions/<nome-esercizio>/` — la soluzione ufficiale (se
  presente — non tutti gli esercizi ce l'hanno).

Trova rapidamente quali esercizi mancano di grading ufficiale con:

```bash
CACHE_DIR=~/.cache/uv/archive-v0/<hash>/<codice-corso>
for py in "$CACHE_DIR"/*.py; do
  name=$(basename "$py" .py)
  grep -q "def grade(" "$py" && echo "$name: HA grading ufficiale" \
                              || echo "$name: senza grading"
done
```

## 2. Determina la specifica di grading, in ordine di preferenza

Per ogni esercizio senza grading, cerca — in quest'ordine — una fonte
oggettiva da cui derivare cosa verificare. **Non passare al passo successivo
finché non hai escluso il precedente.**

1. **`materials/solutions/<nome-esercizio>/`** — se esiste, il diff tra
   questi file e quelli in `materials/labs/<nome-esercizio>/` È la specifica.
   Confronta riga per riga.
2. **`resources.txt`** dentro `materials/labs/<nome-esercizio>/` — cheat
   sheet di comandi di riferimento per esercizi puramente imperativi (senza
   manifest YAML). Contiene spesso nomi di risorsa e valori esatti (vedi
   `deploy-services.py`, `updates-rollout.py` in questo repo come esempio).
3. **Il testo della guida studente**, se l'utente te lo fornisce (spesso
   incollando l'output di un terminale o il testo del workbook/PDF). Questa è
   la fonte più affidabile in assoluto: **chiedila esplicitamente
   all'utente/istruttore** se i punti 1 e 2 non bastano, prima di arrenderti.
   In questo repo, `reliability-autoscaling.py` e `pods-troubleshooting.py`
   sono stati completati/corretti proprio così — senza quel testo avremmo
   dovuto ipotizzare valori (min/max replicas, tag immagine, credenziali)
   che erano invece scritti chiaramente nella guida.
4. Il modulo ufficiale (`start()`/`finish()`) ti dà comunque sempre: il nome
   del progetto OpenShift (di solito `self.__LAB__`, ma verifica — alcuni
   esercizi usano un `self.project` diverso dal nome esercizio, es.
   `deploy-routes` usa `"web-applications"`), le immagini richieste, ed
   eventuali risorse applicate automaticamente da `start()`.

**Regola d'oro**: se dopo aver controllato tutte e 4 le fonti non hai un
valore atteso concreto e verificabile, **non inventarlo**. Non scrivere lo
script. Nel report/commit spiega perché l'esercizio non è gradabile in modo
oggettivo (esplorazione CLI pura, più soluzioni valide, nessuno stato
persistente, ecc.) — vedi la lista degli esercizi "non gradabili" in
README.md per esempi reali di questo giudizio.

**Attenzione — non confondere "nessuno stato persistente dopo `lab finish`"
con "nessuno stato verificabile":** il monitor grafico ripete `lab grade`
ogni 30s MENTRE lo studente lavora, quindi anche uno stato puramente
temporaneo (un pod che la guida chiede di lasciare in esecuzione fino a
`lab finish`, un servizio attivo solo per la durata dell'esercizio, ecc.) è
gradabile "sul momento" — non serve che sopravviva alla pulizia finale.
Prima di marcare un esercizio come "non gradabile" solo perché lo script
ufficiale (`start()`/`finish()`) non applica manifest e non lascia nulla in
`materials/solutions`, **leggi comunque il testo della guida fino in fondo**:
spesso l'ultimo passo prima di "Finish" chiede esplicitamente di verificare
che qualcosa sia ancora in esecuzione (es. `pods-containers` in DO180, Cap.
3.2, punto 8.2: "Confirm that the pod is still running"). In questi casi
scrivi comunque lo script, documentando chiaramente nel docstring che è un
check dal vivo valido solo PRIMA di `lab finish` (dopo, il progetto sparisce
ed è corretto che tutto torni FAIL).

## 3. Scrivi lo script

Usa `lab-custom-grading/_common.py` (già generico, va bene per qualunque
corso) e ricalca lo stile di `reliability-probes.py` o
`reliability-requests.py` come modello:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "nome-esercizio"

def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # ... un blocco GradingStep per ogni elemento verificabile ...

if __name__ == "__main__":
    main()
```

Convenzioni da rispettare sempre:

- **Nome file** = nome esatto dell'esercizio, cioè quello che si passa a
  `lab start`/`lab grade` (es. `pods-troubleshooting.py`).
- Primo argomento da CLI opzionale per il nome del progetto, default = nome
  esercizio.
- Dentro un `GradingStep`, usa `step.add_error(msg)` per un dettaglio
  specifico o `step.fail(msg)` quando l'intero check non ha senso proseguire
  (es. risorsa base assente). All'uscita dal blocco viene stampato
  automaticamente `PASS <titolo>` o `FAIL <titolo>` con i dettagli indentati
  di 8 spazi — **questo formato è obbligatorio**, lo interpreta anche
  `lab_grade_monitor.py` per disegnare i semafori.
- Gradua SOLO quello che l'esercizio chiede di fare/modificare, non dettagli
  incidentali già presenti nello starter e che lo studente non tocca.
- Se il progetto usa un nome diverso dall'esercizio, o alcune risorse hanno
  nomi non deterministici (es. generati da un wizard), preferisci cercare per
  caratteristiche (immagine, label) invece che per nome fisso — vedi
  `storage-configs.py`/`storage-volumes.py` per esempi di questo pattern.
- Commenti in italiano, concisi: spiega il "perché" di una scelta non ovvia
  (es. perché un certo dato non viene gradato), non "cosa fa" il codice.

## 4. Vincoli di sicurezza durante l'analisi

- **Mai** eseguire `oc apply`, `oc create`, `oc delete`, `lab start`, o
  qualunque comando che modifichi lo stato del cluster live durante la fase
  di analisi/scrittura dello script.
- Comandi READ-ONLY (`oc get`, `oc describe`, `oc explain`) sul cluster reale
  sono ok per confermare nomi di campi o la forma esatta di un'API (es.
  verificare come appare in JSON un HPA creato da `oc autoscale`).
- **Per testare lo script end-to-end** (consigliato, se la soluzione
  ufficiale esiste): applica temporaneamente la soluzione in un progetto,
  esegui lo script e verifica che dia PASS, poi **elimina le risorse create**
  per non lasciare l'esercizio già risolto per lo studente. Esempio già fatto
  in questo repo per `reliability-probes` e per verificare lo schema JSON
  dell'HPA in `reliability-autoscaling` (namespace temporaneo, poi
  cancellato).
- Interrogare dati in sola lettura dentro un pod (es. `oc exec ... -- mysql
  -e "SHOW TABLES"`) è accettabile quando serve a verificare un compito reale
  dello studente (vedi `pods-troubleshooting.py`) — non modifica risorse
  Kubernetes, legge soltanto.

## 5. Valida e pubblica

```bash
python3 -m py_compile lab-custom-grading/<nome-esercizio>.py
```

poi `git add`, commit descrittivo, `git push` (repo pubblico:
https://github.com/federicovolpe/advanced-grading — l'utente ha le
credenziali per il push, non chiederle/salvarle in chiaro su disco più del
necessario).

## 6. Attenzione alle collisioni tra corsi

Il fallback cerca il file per nome esatto dell'esercizio, senza distinguere
per corso: se due corsi diversi avessero un esercizio con lo stesso nome ma
contenuto diverso, ci sarebbe un conflitto. È un caso raro (i nomi sono
tipicamente specifici del corso), ma prima di aggiungere un file controlla
che non esista già uno script con lo stesso nome scritto per un corso
diverso.
