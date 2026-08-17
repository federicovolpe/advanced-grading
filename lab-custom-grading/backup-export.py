import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, project_exists

LAB_NAME = "backup-export"
# La guida lavora sempre sul progetto "production" (vedi NAMESPACE nel modulo
# ufficiale backup-export.py), non su un progetto "backup-export".
DEFAULT_PROJECT = "production"

EXPORT_DIR = os.path.expanduser("~/DO380/labs/backup-export/production")

# Campi che la guida chiede esplicitamente di rimuovere dagli export (Cap. 2.2,
# passi 3.4/3.6/3.8/3.10) prima di poterli riapplicare nel progetto "stage".
FORBIDDEN_SNIPPETS = (
    "resourceVersion:",
    "uid:",
    "creationTimestamp:",
    "CHANGE_ME",
)


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROJECT
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    # L'esercizio (Cap. 2.2) termina con una pulizia esplicita al passo 12 che
    # cancella il progetto "stage" e ripristina il registry: alla fine della
    # procedura il cluster torna allo stato iniziale. L'unico artefatto che
    # sopravvive (finché non si esegue "lab finish", che cancella l'intera
    # cartella dei materiali) sono i file esportati sulla workstation.

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep("Risorse Kubernetes esportate e ripulite in ~/DO380/labs/backup-export/production") as step:
        expected_files = {
            "01-pvc.yaml": "PersistentVolumeClaim",
            "02-deployment.yaml": "Deployment",
            "03-service.yaml": "Service",
            "04-route.yaml": "Route",
        }
        for filename, kind in expected_files.items():
            path = os.path.join(EXPORT_DIR, filename)
            if not os.path.isfile(path):
                step.add_error(f"File '{filename}' ({kind}) non trovato in {EXPORT_DIR}")
                continue
            with open(path) as f:
                content = f.read()
            for snippet in FORBIDDEN_SNIPPETS:
                if snippet in content:
                    step.add_error(
                        f"'{filename}' contiene ancora '{snippet.strip(':')}': "
                        "il file non è stato ripulito come richiesto dalla guida"
                    )

    with GradingStep("Dati dell'applicazione esportati dallo snapshot del volume") as step:
        data_dir = os.path.join(EXPORT_DIR, "data")
        if not os.path.isdir(data_dir):
            step.fail(f"Directory '{data_dir}' non trovata: dati non esportati dal pod export-snapshot")
        elif not os.listdir(data_dir):
            step.fail(f"Directory '{data_dir}' vuota")

    with GradingStep("Immagini container dell'etherpad esportate con oc image mirror") as step:
        images_dir = os.path.join(EXPORT_DIR, "v2", "etherpad")
        if not os.path.isdir(images_dir):
            step.fail(f"Directory '{images_dir}' non trovata: immagini non esportate")


if __name__ == "__main__":
    main()
