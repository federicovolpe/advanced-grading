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

    local output status
    output=$(command lab grade "$@" 2>&1)
    status=$?
    printf '%s\n' "$output"

    if [[ -n "$lab_name" && "$output" == *"The grade command is not supported for this lab."* ]]; then
        local custom="$HOME/.local/share/lab-custom-grading/${lab_name}.py"
        if [[ -f "$custom" ]]; then
            echo
            echo "🔧 Grading ufficiale non disponibile per '${lab_name}': eseguo lo script di grading personalizzato..."
            python3 "$custom" "$lab_name"
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

    # Niente display grafico (es. sessione SSH pura): non provare a lanciare
    # Tkinter, ma non rompere comunque `lab start`.
    if [[ -z "$DISPLAY" && -z "$WAYLAND_DISPLAY" ]]; then
        return $status
    fi

    # Evita finestre duplicate se il monitor per questo lab e' gia' attivo.
    if pgrep -f "lab_grade_monitor\.py ${lab_name}\b" >/dev/null 2>&1; then
        return $status
    fi

    nohup python3 "$HOME/.local/bin/lab_grade_monitor.py" "$lab_name" >/dev/null 2>&1 &
    disown

    return $status
}
