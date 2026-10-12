#!/bin/bash
# Installer per il monitor grafico "lab grade" + grading custom per le
# guided exercise DO180 sprovviste di grading ufficiale, e per il
# curriculum di training "libero" (esercizi inventati indipendenti da
# `lab`, comando 'start-training'/'training start').
#
# Uso:
#   git clone --depth 1 https://github.com/<ORG>/<REPO>.git /tmp/do180-lab-grading
#   bash /tmp/do180-lab-grading/install.sh
#
# Reinstallabile: rilanciarlo sovrascrive i file con la versione corrente
# del repo (utile per aggiornare dopo un `git pull`).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BIN_DIR="$HOME/.local/bin"
BASHRC_D_DIR="$HOME/.bashrc.d"
GRADING_DIR="$HOME/.local/share/lab-custom-grading"
TRAINING_DIR="$HOME/.local/share/training"

mkdir -p "$BIN_DIR" "$BASHRC_D_DIR" "$GRADING_DIR" "$TRAINING_DIR/exercises" "$TRAINING_DIR/exercises-do188"

install -m 755 "$SCRIPT_DIR/bin/lab_grade_monitor.py" "$BIN_DIR/lab_grade_monitor.py"
install -m 755 "$SCRIPT_DIR/bin/training_monitor.py" "$BIN_DIR/training_monitor.py"
install -m 644 "$SCRIPT_DIR/bashrc.d/lab-grade-monitor.sh" "$BASHRC_D_DIR/lab-grade-monitor.sh"
install -m 644 "$SCRIPT_DIR/bashrc.d/training.sh" "$BASHRC_D_DIR/training.sh"

for f in "$SCRIPT_DIR"/lab-custom-grading/*.py; do
    install -m 644 "$f" "$GRADING_DIR/$(basename "$f")"
done

install -m 644 "$SCRIPT_DIR/training/_training_common.py" "$TRAINING_DIR/_training_common.py"
for f in "$SCRIPT_DIR"/training/exercises/*.py; do
    install -m 644 "$f" "$TRAINING_DIR/exercises/$(basename "$f")"
done
for f in "$SCRIPT_DIR"/training/exercises-do188/*.py; do
    install -m 644 "$f" "$TRAINING_DIR/exercises-do188/$(basename "$f")"
done

# Simulazioni d'esame: una directory per esame (exercises-try-exam-<esame>),
# scoperte da sole anche da 'start-try-exam <esame>' — un esame nuovo non
# richiede modifiche qui ne' in training.sh.
for d in "$SCRIPT_DIR"/training/exercises-try-exam-*/; do
    name="$(basename "$d")"
    mkdir -p "$TRAINING_DIR/$name"
    for f in "$d"*.py; do
        install -m 644 "$f" "$TRAINING_DIR/$name/$(basename "$f")"
    done
done

# Migrazione: la simulazione DO188 si chiamava 'try-exam' (senza esame).
# Si tengono i progressi e si toglie la vecchia copia installata, che
# altrimenti comparirebbe come un esame chiamato "exercises-try-exam".
if [[ -f "$TRAINING_DIR/progress-exercises-try-exam.json" && ! -f "$TRAINING_DIR/progress-exercises-try-exam-ex188.json" ]]; then
    mv "$TRAINING_DIR/progress-exercises-try-exam.json" "$TRAINING_DIR/progress-exercises-try-exam-ex188.json"
fi
rm -rf "$TRAINING_DIR/exercises-try-exam"

echo "Installati/aggiornati:"
echo "  - $BIN_DIR/lab_grade_monitor.py"
echo "  - $BIN_DIR/training_monitor.py"
echo "  - $BASHRC_D_DIR/lab-grade-monitor.sh"
echo "  - $BASHRC_D_DIR/training.sh"
echo "  - $GRADING_DIR/*.py ($(ls "$SCRIPT_DIR"/lab-custom-grading/*.py | wc -l) script di grading)"
echo "  - $TRAINING_DIR/exercises/*.py ($(ls "$SCRIPT_DIR"/training/exercises/*.py | wc -l) esercizi di training DO180)"
echo "  - $TRAINING_DIR/exercises-do188/*.py ($(ls "$SCRIPT_DIR"/training/exercises-do188/*.py | wc -l) esercizi di training DO188)"
for d in "$SCRIPT_DIR"/training/exercises-try-exam-*/; do
    name="$(basename "$d")"
    echo "  - $TRAINING_DIR/$name/*.py ($(ls "$d"e*.py | wc -l) esercizi della simulazione d'esame ${name#exercises-try-exam-})"
done

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo
    echo "ATTENZIONE: tkinter non e' installato per python3 su questa macchina."
    echo "Il monitor grafico non potra' aprirsi finche' non viene installato (richiede un admin):"
    echo "    sudo dnf install python3-tkinter -y"
fi

echo
echo "Fatto. Apri un nuovo terminale (o esegui 'source ~/.bashrc') perche'"
echo "il wrapper 'lab' (start/grade) e i comandi 'start-training' (DO180) /"
echo "'start-training-do188' (DO188) / 'start-try-exam <esame>' siano attivi nella shell corrente."
