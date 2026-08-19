"""
Grading personalizzato per 'serving-vllm' (AI0016L - Deploy and Serve LLMs
with vLLM).

Da testo guida studente: lo studente distribuisce 'my-llm' con vLLM CPU e,
attraverso piu' iterazioni, arriva alla configurazione finale:
- --chat-template=/mnt/models/template_chatml.jinja
- --max-num-seqs=200 (dopo aver visto fallire richieste con valore 1)
- VLLM_CPU_OMP_THREADS_BIND=0-6
- VLLM_CPU_KVCACHE_SPACE=8 (ultimo valore impostato, dopo il test con 1)
- Route esterna con autenticazione token, service account 'my-sa'
- spec.predictor.timeout=180 (impostato via `oc patch` a meta' esercizio)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, condition_true, get_route_host

LAB_NAME = "serving-vllm"
INFERENCESERVICE_NAME = "my-llm"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"La InferenceService '{INFERENCESERVICE_NAME}' e' configurata correttamente") as step:
        svc = oc_get_json("inferenceservice", INFERENCESERVICE_NAME, "-n", project)
        if not svc:
            step.fail(f"InferenceService '{INFERENCESERVICE_NAME}' non trovata")
        else:
            model = svc.get("spec", {}).get("predictor", {}).get("model", {})
            args = model.get("args", []) or []
            env = {e.get("name"): e.get("value") for e in (model.get("env") or [])}

            if not any("--chat-template" in a for a in args):
                step.add_error("Manca l'argomento --chat-template")
            if "--max-num-seqs=200" not in args:
                step.add_error(f"--max-num-seqs non e' 200 (argomenti: {args})")
            if env.get("VLLM_CPU_OMP_THREADS_BIND") != "0-6":
                step.add_error(
                    f"VLLM_CPU_OMP_THREADS_BIND e' '{env.get('VLLM_CPU_OMP_THREADS_BIND')}', atteso '0-6'"
                )
            if env.get("VLLM_CPU_KVCACHE_SPACE") != "8":
                step.add_error(
                    f"VLLM_CPU_KVCACHE_SPACE e' '{env.get('VLLM_CPU_KVCACHE_SPACE')}', atteso '8'"
                )
            timeout = svc.get("spec", {}).get("predictor", {}).get("timeout")
            if timeout != 180:
                step.add_error(f"spec.predictor.timeout e' {timeout}, atteso 180")
            if not condition_true(svc, "Ready"):
                step.add_error(f"InferenceService '{INFERENCESERVICE_NAME}' non e' Ready")

    with GradingStep("La Route esterna e' esposta") as step:
        if not get_route_host(INFERENCESERVICE_NAME, project):
            step.fail(f"Route '{INFERENCESERVICE_NAME}' non trovata")


if __name__ == "__main__":
    main()
