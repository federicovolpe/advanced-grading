#!/bin/bash
# Installer per il monitor grafico "lab grade" + grading custom per le
# guided exercise DO180 sprovviste di grading ufficiale.
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

mkdir -p "$BIN_DIR" "$BASHRC_D_DIR" "$GRADING_DIR"

install -m 755 "$SCRIPT_DIR/bin/lab_grade_monitor.py" "$BIN_DIR/lab_grade_monitor.py"
install -m 644 "$SCRIPT_DIR/bashrc.d/lab-grade-monitor.sh" "$BASHRC_D_DIR/lab-grade-monitor.sh"

for f in "$SCRIPT_DIR"/lab-custom-grading/*.py; do
    install -m 644 "$f" "$GRADING_DIR/$(basename "$f")"
done

echo "Installati/aggiornati:"
echo "  - $BIN_DIR/lab_grade_monitor.py"
echo "  - $BASHRC_D_DIR/lab-grade-monitor.sh"
echo "  - $GRADING_DIR/*.py ($(ls "$SCRIPT_DIR"/lab-custom-grading/*.py | wc -l) script di grading)"

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo
    echo "ATTENZIONE: tkinter non e' installato per python3 su questa macchina."
    echo "Il monitor grafico non potra' aprirsi finche' non viene installato (richiede un admin):"
    echo "    sudo dnf install python3-tkinter -y"
fi

echo
echo "Fatto. Apri un nuovo terminale (o esegui 'source ~/.bashrc') perche'"
echo "il wrapper 'lab' (start/grade) sia attivo nella shell corrente."
