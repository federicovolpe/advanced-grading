"""
Grading personalizzato per 'monitoring-performance' (AI0018L - Hardware and
Performance Metrics).

`lab start` distribuisce gia' DistilBERT (OpenVINO) e Qwen3-0.6B (vLLM); il
compito dello studente e' inviare richieste di inferenza a entrambi
(request_to_distilbert.sh, request_inference_to_qwen3.sh) per generare
metriche osservabili. Verifica dal vivo (contatori Prometheus, endpoint
/metrics pubblico senza autenticazione, come mostrato nella guida):
- ovms_requests_success{...method="ModelInfer"...name="distilbert"} > 0
- vllm:generation_tokens_total{...model_name="qwen3-06b"} > 0
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, project_exists, get_route_host, http_get

LAB_NAME = "monitoring-performance"


def _metric_value(text, pattern):
    match = re.search(pattern, text)
    if not match:
        return None
    return float(match.group(1))


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep("Sono state inviate richieste di inferenza a 'distilbert'") as step:
        host = get_route_host("distilbert", project)
        if not host:
            step.fail("Route 'distilbert' non trovata")
        else:
            ok, body = http_get(f"https://{host}/metrics")
            if not ok:
                step.fail("Impossibile interrogare /metrics di distilbert")
            else:
                value = _metric_value(
                    body,
                    r'ovms_requests_success\{[^}]*method="ModelInfer"[^}]*name="distilbert"[^}]*\}\s+([\d.]+)',
                )
                if not value:
                    step.add_error(
                        "ovms_requests_success (ModelInfer) e' 0 o non trovato: "
                        "nessuna richiesta di inferenza inviata"
                    )

    with GradingStep("Sono state inviate richieste di inferenza a 'qwen3-06b'") as step:
        host = get_route_host("qwen3-06b", project)
        if not host:
            step.fail("Route 'qwen3-06b' non trovata")
        else:
            ok, body = http_get(f"https://{host}/metrics")
            if not ok:
                step.fail("Impossibile interrogare /metrics di qwen3-06b")
            else:
                value = _metric_value(
                    body,
                    r'vllm:generation_tokens_total\{[^}]*model_name="qwen3-06b"[^}]*\}\s+([\d.]+)',
                )
                if not value:
                    step.add_error(
                        "vllm:generation_tokens_total e' 0 o non trovato: "
                        "nessuna richiesta di inferenza inviata"
                    )


if __name__ == "__main__":
    main()
