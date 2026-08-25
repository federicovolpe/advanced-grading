# Comandi per il curriculum di training "libero" DO180 (indipendente dal
# tool ufficiale `lab`: esercizi inventati, non le guided exercise vere e
# proprie, vedi README.md in questo repo). Ogni esercizio crea da solo il
# proprio ambiente di partenza in un progetto OpenShift dedicato
# (training-<slug>) e viene gradato con polling automatico in una finestra
# grafica, con un pulsante per passare al successivo. Il progetto
# dell'esercizio che si lascia viene cancellato automaticamente sia
# passando al successivo sia chiudendo la finestra (training_monitor.py);
# 'training cleanup'/'reset' sono solo una rete di sicurezza per chi la
# finestra l'ha chiusa in modo brusco (kill -9, crash, spegnimento della
# VM), quando quella pulizia automatica non ha potuto scattare.

training() {
    local subcmd="${1:-start}"
    local dir="$HOME/.local/share/training"

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
            # Una sola finestra di training per volta.
            pkill -f "training_monitor\.py" >/dev/null 2>&1
            nohup python3 "$HOME/.local/bin/training_monitor.py" "${@:2}" >/dev/null 2>&1 &
            disown
            echo "Finestra di training avviata (progressi salvati in $dir/progress.json)."
            ;;
        list)
            python3 "$HOME/.local/bin/training_monitor.py" --list
            ;;
        goto)
            if [[ -z "${2:-}" ]]; then
                echo "Uso: training goto <numero-esercizio>"
                return 1
            fi
            training start --goto "$2"
            ;;
        cleanup)
            python3 "$HOME/.local/bin/training_monitor.py" --cleanup
            ;;
        reset)
            rm -f "$dir/progress.json"
            echo "Progressi azzerati: 'training start' ripartira' dal primo esercizio."
            python3 "$HOME/.local/bin/training_monitor.py" --cleanup
            ;;
        *)
            echo "Uso: training {start|list|goto <N>|cleanup|reset}"
            return 1
            ;;
    esac
}

# Alias piu' immediato per chi si aspetta letteralmente "start training".
start-training() {
    training start "$@"
}
