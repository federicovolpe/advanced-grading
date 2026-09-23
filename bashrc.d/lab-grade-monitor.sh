# Wrapper non distruttivo attorno al comando reale `lab` (/usr/local/bin/lab,
# pacchetto rpm lab-service):
#   - intercetta `lab start <nome-lab>` per far partire in automatico il
#     monitor a semafori (lab_grade_monitor.py) dopo che l'avvio del lab e'
#     andato a buon fine, cosi' lo studente non deve piu' lanciarlo a mano.
#   - intercetta `lab grade <nome-lab>`: se il grading ufficiale risponde
#     "The grade command is not supported for this lab." (caso delle guided
#     exercise, che non hanno grade()), cerca uno script di grading custom in
#     ~/.local/share/lab-custom-grading/<nome-lab>.py e lo esegue al suo posto.
# Tutti gli altri sottocomandi passano invariati al binario originale tramite
# `command lab`.

_lab_grade_with_custom_fallback() {
    local lab_name="" arg
    for arg in "$@"; do
        if [[ "$arg" != -* ]]; then
            lab_name="$arg"
        fi
    done

    local output status stripped
    output=$(command lab grade "$@" 2>&1)
    status=$?
    printf '%s\n' "$output"

    # Fallback sul grading custom non solo quando l'ufficiale risponde
    # letteralmente "The grade command is not supported for this lab.", ma
    # ogni volta che non produce nessun check PASS/FAIL/✓/✗ reale: capita
    # anche per un blip transitorio del comando ufficiale (es. subito dopo
    # 'lab start', cluster/progetto non ancora del tutto pronti) che
    # restituisce solo il banner "Running: ..." e nient'altro, senza quella
    # stringa esatta — in quel caso lo script custom (se esiste) resta
    # comunque la fonte di verita' migliore disponibile.
    #
    # Il pattern deve riconoscere ENTRAMBI i formati di esito, non solo
    # "PASS "/"FAIL " testuale: le versioni attuali di 'lab grade' rendono
    # l'esito coi simboli colorati ✓/✗ (mai quel testo), come gia' fa
    # lab_grade_monitor.py (SYMBOL_CHECK_RE) — questo controllo era rimasto
    # indietro e trattava un grading ufficiale perfettamente riuscito come
    # "non disponibile", rilanciando inutilmente lo script custom sopra a un
    # risultato gia' buono. Le sequenze ANSI (colore/cursore) vanno rimosse
    # prima del match, altrimenti un simbolo colorato non e' mai a inizio
    # riga "pulito".
    stripped=$(printf '%s' "$output" | sed -E 's/\x1b\[[0-9;?]*[a-zA-Z]//g')
    if [[ -n "$lab_name" ]] && ! grep -qE '^(PASS|FAIL) |^[✓✔✗✘] ' <<<"$stripped"; then
        local custom="$HOME/.local/share/lab-custom-grading/${lab_name}.py"
        if [[ -f "$custom" ]]; then
            echo
            echo "🔧 Grading ufficiale non disponibile o incompleto per '${lab_name}': eseguo lo script di grading personalizzato..."
            python3 "$custom"
            return $?
        fi
    fi

    return $status
}

lab() {
    if [[ "$1" == "grade" ]]; then
        _lab_grade_with_custom_fallback "${@:2}"
        return $?
    fi

    if [[ "$1" != "start" ]]; then
        command lab "$@"
        return $?
    fi

    command lab "$@"
    local status=$?

    if [[ $status -ne 0 ]]; then
        return $status
    fi

    # Nome del lab: ultimo argomento che non e' un'opzione (gestisce sia
    # "lab start nome" sia eventuali "lab start [OPTIONS] nome").
    local lab_name=""
    local arg
    for arg in "${@:2}"; do
        if [[ "$arg" != -* ]]; then
            lab_name="$arg"
        fi
    done

    if [[ -z "$lab_name" ]]; then
        return $status
    fi

    # Azzera lo stato "milestone" (vedi _common.py: ever_true()/
    # attempt_started_at()) di un eventuale tentativo precedente di questo
    # stesso esercizio, e registra l'istante di questo 'lab start': gli
    # script di grading custom per compiti che l'esercizio stesso chiede di
    # smontare (es. "crea un container", poi "rimuovilo" in un passo
    # successivo) devono ricordarsi che una fase e' stata completata anche
    # dopo che quello stato e' stato distrutto — ma solo per QUESTO
    # tentativo, non per uno precedente (altrimenti un 'lab start' di reset
    # ripartirebbe con dei check gia' verdi senza che lo studente abbia
    # fatto nulla).
    local state_dir="$HOME/.grading/custom-state"
    mkdir -p "$state_dir"
    rm -f "$state_dir/${lab_name}."*
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$state_dir/${lab_name}.started_at"

    # Niente display grafico (es. sessione SSH pura): non provare a lanciare
    # Tkinter, ma non rompere comunque `lab start`.
    if [[ -z "$DISPLAY" && -z "$WAYLAND_DISPLAY" ]]; then
        return $status
    fi

    # Un solo esercizio per volta: chiudi qualunque finestra di grading
    # gia' aperta (di un esercizio precedente, o anche di questo stesso se
    # e' un 'lab start' di reset) prima di aprirne una nuova, altrimenti
    # restano finestre vecchie in giro a mostrare lo stato di un altro
    # esercizio (o uno stato pre-reset, ormai stale).
    pkill -f "lab_grade_monitor\.py " >/dev/null 2>&1

    # '</dev/null' esplicito: se stdin resta il terminale, nohup lo
    # sostituisce con un /dev/null in sola scrittura, che fa uscire subito
    # lo 'script' usato internamente da 'lab grade' (nessun check in output).
    nohup python3 "$HOME/.local/bin/lab_grade_monitor.py" "$lab_name" </dev/null >/dev/null 2>&1 &
    disown

    return $status
}
