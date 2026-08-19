"""
Grading personalizzato per 'genai-app' (AI0022L - GenAI Applications).

A differenza degli esercizi DO180, qui `lab start` non applica manifest che
lo studente deve completare sul cluster: crea gia' lui stesso il progetto,
distribuisce PostgreSQL+vLLM (Qwen3-0.6B) e Llama Stack (vedi
ai0022l/exercises/genai_app.py -> start()). Il compito dello studente e'
completare tre TODO nei file copiati localmente in ~/course/labs/genai-app/
(confrontati con materials/solutions/genai-app/ per la specifica esatta):

1. llm_client.py: implementare lo streaming completion con l'SDK OpenAI.
2. .env (da .env.example): puntare OPENAI_BASE_URL alla Route del vLLM.
3. test-llama-stack.py: istanziare LlamaStackClient e usare la Responses API
   in streaming.

Nessuna di queste modifiche produce una risorsa Kubernetes verificabile: si
gradano i file locali.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    project_exists,
    lab_materials_dir,
    read_text_file,
    parse_env_file,
    get_route_host,
)

LAB_NAME = "genai-app"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    materials_dir = lab_materials_dir(LAB_NAME)

    with GradingStep("llm_client.py implementa lo streaming completion") as step:
        content = read_text_file(os.path.join(materials_dir, "llm_client.py"))
        if content is None:
            step.fail(f"File llm_client.py non trovato in {materials_dir}")
        else:
            if "TODO" in content:
                step.add_error("Sono ancora presenti dei TODO non completati")
            if "stream = None" in content:
                step.add_error("stream e' ancora inizializzato a None")
            if "self.client.chat.completions.create(" not in content:
                step.add_error(
                    "Non trovata la chiamata a self.client.chat.completions.create()"
                )
            if "stream=True" not in content:
                step.add_error("La chiamata non richiede una risposta in streaming (stream=True)")

    with GradingStep("test-llama-stack.py usa la Responses API in streaming") as step:
        content = read_text_file(os.path.join(materials_dir, "test-llama-stack.py"))
        if content is None:
            step.fail(f"File test-llama-stack.py non trovato in {materials_dir}")
        else:
            if "TODO" in content:
                step.add_error("Sono ancora presenti dei TODO non completati")
            if 'LS_URL = "changeme"' in content:
                step.add_error("LS_URL non e' stato impostato")
            if "LlamaStackClient(" not in content or "base_url" not in content:
                step.add_error("LlamaStackClient non e' istanziato con base_url")
            if "stream = None" in content:
                step.add_error("stream e' ancora inizializzato a None")
            if "client.responses.create(" not in content:
                step.add_error("Non trovata la chiamata a client.responses.create()")
            if "stream=True" not in content:
                step.add_error("La chiamata non richiede una risposta in streaming (stream=True)")

    with GradingStep("Il file .env punta alla Route del vLLM") as step:
        env_path = os.path.join(materials_dir, ".env")
        env = parse_env_file(env_path)
        if not env:
            step.fail(f"File .env non trovato in {materials_dir} (copiare da .env.example)")
        else:
            base_url = env.get("OPENAI_BASE_URL", "")
            if not base_url or "TODO" in base_url:
                step.add_error("OPENAI_BASE_URL non e' stato impostato")
            else:
                vllm_host = get_route_host("qwen-vllm", project)
                if vllm_host and vllm_host not in base_url:
                    step.add_error(
                        f"OPENAI_BASE_URL ('{base_url}') non punta alla Route "
                        f"del vLLM ('{vllm_host}')"
                    )


if __name__ == "__main__":
    main()
