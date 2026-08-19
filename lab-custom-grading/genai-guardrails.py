"""
Grading personalizzato per 'genai-guardrails' (AI0022L - TrustyAI Guardrails).

`lab start` (ai0022l/exercises/genai_guardrails.py) applica gia' lui il
GuardrailsOrchestrator 'gorch' e le ConfigMap associate, ma la ConfigMap
'fms-orchestr8-config-gateway' viene applicata con due valori TODO vuoti
(vedi materials/labs/genai-guardrails/deploy-gorch.yaml): il compito dello
studente e' completarli e ri-applicare la ConfigMap sul cluster (confrontata
con materials/solutions/genai-guardrails/deploy-gorch.yaml per la specifica
esatta), poi completare guardrails_client.py con l'URL del gateway.
"""
import sys
import os
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    oc_get_json,
    project_exists,
    lab_materials_dir,
    read_text_file,
    get_route_host,
)

LAB_NAME = "genai-guardrails"
GATEWAY_CONFIGMAP = "fms-orchestr8-config-gateway"
GATEWAY_ROUTE = "gorch-gateway"
REQUIRED_REGEX_DETECTORS = {"email", "us-phone-number", "credit-card"}


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"La ConfigMap '{GATEWAY_CONFIGMAP}' e' configurata con i detector richiesti"
    ) as step:
        cm = oc_get_json("configmap", GATEWAY_CONFIGMAP, "-n", project)
        if not cm:
            step.fail(f"ConfigMap '{GATEWAY_CONFIGMAP}' non trovata")
        else:
            try:
                config = yaml.safe_load(cm.get("data", {}).get("config.yaml", ""))
            except yaml.YAMLError:
                config = None
            if not config:
                step.fail("config.yaml nella ConfigMap non e' YAML valido")
            else:
                detectors = {d.get("name"): d for d in config.get("detectors", []) or []}
                regex_params = set(
                    (detectors.get("regex", {}).get("detector_params") or {}).get("regex") or []
                )
                missing = REQUIRED_REGEX_DETECTORS - regex_params
                if missing:
                    step.add_error(
                        f"detector_params.regex non contiene: {', '.join(sorted(missing))}"
                    )
                routes = {r.get("name"): r.get("detectors") or [] for r in config.get("routes", []) or []}
                all_route_detectors = set(routes.get("all") or [])
                if not {"regex", "hap"} <= all_route_detectors:
                    step.add_error(
                        "La route 'all' non ha sia 'regex' che 'hap' tra i detector "
                        f"(trovati: {sorted(all_route_detectors)})"
                    )

    with GradingStep(f"Il Gateway TrustyAI ('{GATEWAY_ROUTE}') e' raggiungibile") as step:
        if not get_route_host(GATEWAY_ROUTE, project):
            step.fail(f"Route '{GATEWAY_ROUTE}' non trovata")

    materials_dir = lab_materials_dir(LAB_NAME)
    with GradingStep("guardrails_client.py punta al Gateway TrustyAI") as step:
        content = read_text_file(os.path.join(materials_dir, "guardrails_client.py"))
        if content is None:
            step.fail(f"File guardrails_client.py non trovato in {materials_dir}")
        else:
            if "TODO" in content or 'GUARDRAILS_GATEWAY = "changeme"' in content:
                step.add_error("GUARDRAILS_GATEWAY non e' stato impostato")
            gateway_host = get_route_host(GATEWAY_ROUTE, project)
            if gateway_host and gateway_host not in content:
                step.add_error(
                    f"GUARDRAILS_GATEWAY non punta alla Route '{GATEWAY_ROUTE}' ('{gateway_host}')"
                )
            if "URL_PASSTHROUGH" not in content or "/passthrough/v1/chat/completions" not in content:
                step.add_error("URL_PASSTHROUGH non e' costruito verso /passthrough/v1/chat/completions")
            if "URL_GUARDRAILS" not in content or "/all/v1/chat/completions" not in content:
                step.add_error("URL_GUARDRAILS non e' costruito verso /all/v1/chat/completions")


if __name__ == "__main__":
    main()
