#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise pipelines-creation (DO288), priva di
`lab grade` ufficiale (il modulo do288/pipelines-creation.py implementa solo
start()/finish()).

Lo studente crea una Pipeline Tekton "nodejs-build" (task fetch-repository,
npm-install, npm-test, npm-lint, app-version, build-image), un Task custom
"npm" (da npm-task.yaml) e un Secret "basic-user-pass" (basic-auth) collegato
al service account "pipeline" per il pull dal registry, poi esegue la
pipeline con `tkn p start` e un workspace PVC-backed: lo stato finale
verificabile e' quindi sia la definizione delle risorse Tekton, sia
l'esistenza di almeno un PipelineRun completato con successo.

Usiamo i nomi di risorsa completi di API group ("pipeline.tekton.dev",
"task.tekton.dev", "pipelinerun.tekton.dev") invece delle forme brevi
("pipeline", "task", "pipelinerun"): non e' stato possibile testare dal vivo
in questa sessione (nessun login al cluster, per policy del repo), e le
forme fully-qualified sono garantite univoche con `oc get` a prescindere da
eventuali altre CRD installate sul cluster che potrebbero condividere lo
stesso nome breve.

Specifica (fornita dall'utente, che ha letto guida ufficiale + manifest):
- Pipeline "nodejs-build": .spec.tasks contiene i 6 task richiesti, e il
  task "build-image" ha .runAfter che include tutti e tre "npm-test",
  "npm-lint", "app-version" (confronto per insiemi, l'ordine non conta).
- Task "npm" esiste.
- Secret "basic-user-pass" esiste, e il service account "pipeline" lo
  referenzia in .secrets[].name.
- Almeno un PipelineRun (label tekton.dev/pipeline=nodejs-build) ha la
  condizione type=="Succeeded" con status=="True".

Uso: pipelines-creation.py [nome-progetto]   (default: pipelines-creation)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "pipelines-creation"
PIPELINE = "nodejs-build"
TASK = "npm"
SECRET = "basic-user-pass"
SERVICE_ACCOUNT = "pipeline"
REQUIRED_TASKS = {
    "fetch-repository",
    "npm-install",
    "npm-test",
    "npm-lint",
    "app-version",
    "build-image",
}
BUILD_IMAGE_RUNAFTER = {"npm-test", "npm-lint", "app-version"}


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    pipeline = oc_get_json("pipeline.tekton.dev", PIPELINE, "-n", project)
    with GradingStep(f"La Pipeline '{PIPELINE}' esiste con tutti i task richiesti") as step:
        if not pipeline:
            step.fail(f"Pipeline '{PIPELINE}' non trovata")
        else:
            tasks = (pipeline.get("spec") or {}).get("tasks") or []
            names = {t.get("name") for t in tasks}
            missing = REQUIRED_TASKS - names
            if missing:
                step.add_error(f"Task mancanti nella pipeline: {sorted(missing)}")

    with GradingStep("Il task 'build-image' ha runAfter npm-test, npm-lint e app-version") as step:
        if not pipeline:
            step.fail(f"Pipeline '{PIPELINE}' non trovata")
        else:
            tasks = (pipeline.get("spec") or {}).get("tasks") or []
            build_image = next((t for t in tasks if t.get("name") == "build-image"), None)
            if not build_image:
                step.fail("Task 'build-image' non trovato nella pipeline")
            else:
                run_after = set(build_image.get("runAfter") or [])
                missing = BUILD_IMAGE_RUNAFTER - run_after
                if missing:
                    step.add_error(
                        f"'runAfter' di 'build-image' e' {sorted(run_after)}, "
                        f"manca: {sorted(missing)}"
                    )

    with GradingStep(f"Il Task custom '{TASK}' esiste") as step:
        task = oc_get_json("task.tekton.dev", TASK, "-n", project)
        if not task:
            step.fail(f"Task '{TASK}' non trovato")

    with GradingStep(f"Il Secret '{SECRET}' esiste") as step:
        secret = oc_get_json("secret", SECRET, "-n", project)
        if not secret:
            step.fail(f"Secret '{SECRET}' non trovato")

    with GradingStep(f"Il service account '{SERVICE_ACCOUNT}' referenzia il Secret '{SECRET}'") as step:
        sa = oc_get_json("sa", SERVICE_ACCOUNT, "-n", project)
        if not sa:
            step.fail(f"Service account '{SERVICE_ACCOUNT}' non trovato")
        else:
            secret_names = {s.get("name") for s in (sa.get("secrets") or [])}
            if SECRET not in secret_names:
                step.add_error(
                    f"'.secrets[].name' del service account non include '{SECRET}' "
                    f"(trovati: {sorted(secret_names)})"
                )

    with GradingStep(f"Almeno un PipelineRun di '{PIPELINE}' e' completato con successo") as step:
        runs = oc_get_json(
            "pipelinerun.tekton.dev", "-n", project, "-l", f"tekton.dev/pipeline={PIPELINE}"
        )
        items = (runs or {}).get("items") or []
        if not items:
            step.fail(f"Nessun PipelineRun trovato per la pipeline '{PIPELINE}'")
        else:
            def succeeded(run):
                conditions = ((run.get("status") or {}).get("conditions")) or []
                return any(
                    c.get("type") == "Succeeded" and c.get("status") == "True"
                    for c in conditions
                )

            if not any(succeeded(r) for r in items):
                step.add_error(
                    f"Nessuno dei {len(items)} PipelineRun trovati ha condizione "
                    "Succeeded/True"
                )


if __name__ == "__main__":
    main()
