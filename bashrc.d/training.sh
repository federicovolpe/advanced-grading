# Comandi per i curricula di training "liberi" (indipendenti dal tool
# ufficiale `lab`: esercizi inventati, non le guided exercise vere e proprie,
# vedi README.md in questo repo). Tracce indipendenti, ciascuna col
# proprio progresso salvato:
#   do180 (default)  — stato su un progetto OpenShift dedicato per esercizio
#                      (training-<slug>), richiede un cluster raggiungibile.
#   do188            — stato locale Podman (container/immagini/volumi/reti
#                      sulla workstation), nessun cluster richiesto.
#   try-exam <esame> — simulazione d'esame, senza comandi suggeriti nel
#                      testo degli esercizi. L'esame e' obbligatorio: ogni
#                      directory exercises-try-exam-<esame> installata e' un
#                      esame disponibile (oggi ex188, ex280), quindi un esame
#                      nuovo non richiede modifiche qui. Si accettano anche
#                      "188", "do188", "EX188": conta solo il numero.
# Ogni esercizio viene gradato con polling automatico in una finestra
# grafica, con un pulsante per passare al successivo. L'ambiente
# dell'esercizio che si lascia viene ripulito automaticamente sia passando
# al successivo sia chiudendo la finestra (training_monitor.py);
# 'training cleanup'/'reset' sono solo una rete di sicurezza per chi la
# finestra l'ha chiusa in modo brusco (kill -9, crash, spegnimento della
# VM), quando quella pulizia automatica non ha potuto scattare.

_TRAINING_DIR="$HOME/.local/share/training"

_training_exercises_dir() {
    case "$1" in
        do188) echo "$_TRAINING_DIR/exercises-do188" ;;
        do180) echo "$_TRAINING_DIR/exercises" ;;
        try-exam-*)
            [[ -d "$_TRAINING_DIR/exercises-$1" ]] || return 1
            echo "$_TRAINING_DIR/exercises-$1"
            ;;
        *) return 1 ;;
    esac
}

_training_exams() {
    local d
    for d in "$_TRAINING_DIR"/exercises-try-exam-*/; do
        [[ -d "$d" ]] && basename "$d" | sed 's/^exercises-try-exam-//'
    done
}

# "188", "do188", "EX188" -> "ex188": l'esame si identifica dal numero.
_training_exam_name() {
    local digits="${1//[!0-9]/}"
    [[ -n "$digits" ]] && echo "ex$digits" || echo "${1,,}"
}

_training_exam_usage() {
    echo "Specifica l'esame: $1 <esame>"
    echo "Esami disponibili: $(_training_exams | tr '\n' ' ')"
}

training() {
    local subcmd="${1:-start}"
    shift || true

    local course="do180"
    if [[ "${1:-}" == "do180" || "${1:-}" == "do188" ]]; then
        course="$1"
        shift
    elif [[ "${1:-}" == "try-exam" ]]; then
        shift
        if [[ -z "${1:-}" ]]; then
            _training_exam_usage "training $subcmd try-exam"
            return 1
        fi
        course="try-exam-$(_training_exam_name "$1")"
        shift
    fi
    local exdir
    if ! exdir="$(_training_exercises_dir "$course")"; then
        echo "Esame o corso sconosciuto: ${course#try-exam-}"
        echo "Esami disponibili: $(_training_exams | tr '\n' ' ')"
        return 1
    fi

    case "$subcmd" in
        start)
            if [[ -z "$DISPLAY" && -z "$WAYLAND_DISPLAY" ]]; then
                echo "Serve un display grafico (X11/Wayland) per 'training start'."
                return 1
            fi
            if ! python3 -c "import tkinter" >/dev/null 2>&1; then
                echo "tkinter non e' installato per python3 (serve per la finestra grafica)."
                echo "Chiedi a un amministratore: sudo dnf install python3-tkinter -y"
                return 1
            fi
            # Una sola finestra di training per volta (qualunque traccia).
            pkill -f "training_monitor\.py" >/dev/null 2>&1
            nohup python3 "$HOME/.local/bin/training_monitor.py" --exercises-dir "$exdir" "$@" </dev/null >/dev/null 2>&1 &
            disown
            echo "Finestra di training avviata (traccia: $course)."
            ;;
        list)
            python3 "$HOME/.local/bin/training_monitor.py" --exercises-dir "$exdir" --list
            ;;
        goto)
            if [[ -z "${1:-}" ]]; then
                echo "Uso: training goto [do180|do188|try-exam <esame>] <numero-esercizio|nome-esercizio>"
                return 1
            fi
            if [[ "$course" == try-exam-* ]]; then
                training start try-exam "${course#try-exam-}" --goto "$1"
            else
                training start "$course" --goto "$1"
            fi
            ;;
        cleanup)
            python3 "$HOME/.local/bin/training_monitor.py" --exercises-dir "$exdir" --cleanup
            ;;
        reset)
            python3 "$HOME/.local/bin/training_monitor.py" --exercises-dir "$exdir" --reset
            ;;
        *)
            echo "Uso: training {start|list|goto <N|nome>|cleanup|reset} [do180|do188|try-exam <esame>]"
            return 1
            ;;
    esac
}

# Alias piu' immediati per chi si aspetta letteralmente "start training".
start-training() {
    training start do180 "$@"
}

start-training-do188() {
    training start do188 "$@"
}

start-try-exam() {
    if [[ -z "${1:-}" ]]; then
        _training_exam_usage "start-try-exam"
        return 1
    fi
    training start try-exam "$@"
}
