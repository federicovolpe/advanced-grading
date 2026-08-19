"""
Grading personalizzato per 'genai-agentic' (AI0022L - Agentic AI Applications).

`lab start` (ai0022l/exercises/genai_agentic.py) crea gia' lui il progetto e
distribuisce vLLM (InferenceService 'qwen3-06b') e Llama Stack (Route
'llamastack-api', vedi ai0022l/kserve.py e odh_llamastack.py). Il compito
dello studente e' invece:

1. Distribuire il server MCP fornito (materials/labs/genai-agentic/
   mcp-todo-app/deployment.yaml): Deployment/Service 'todo-app', Service +
   Route 'todo-mcp' (porta 8081).
2. Completare client-chat-app/agent_config.env (confrontato con
   materials/solutions/genai-agentic/.../agent_config.env per la specifica):
   URL di Llama Stack, model id, endpoint MCP, etichetta del tool server.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    oc_get_json,
    project_exists,
    lab_materials_dir,
    parse_env_file,
    get_route_host,
)

LAB_NAME = "genai-agentic"
MCP_MODEL_NAME = "qwen3-06b"  # nome fisso dell'InferenceService, creato da start()


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep("Il server MCP 'todo-app' e' distribuito") as step:
        deploy = oc_get_json("deployment", "todo-app", "-n", project)
        if not deploy:
            step.fail("Deployment 'todo-app' non trovato")
        else:
            containers = {
                c.get("name")
                for c in (deploy.get("spec", {}).get("template", {})
                          .get("spec", {}).get("containers", []) or [])
            }
            if "todo-mcp" not in containers:
                step.add_error("Manca il container 'todo-mcp' nel Deployment")
            ready = deploy.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error("Il Deployment 'todo-app' non ha repliche pronte")

    with GradingStep("Il Service/Route 'todo-mcp' sono esposti sulla porta 8081") as step:
        svc = oc_get_json("service", "todo-mcp", "-n", project)
        if not svc:
            step.fail("Service 'todo-mcp' non trovato")
        else:
            ports = {p.get("port") for p in svc.get("spec", {}).get("ports", []) or []}
            if 8081 not in ports:
                step.add_error(f"Il Service 'todo-mcp' non espone la porta 8081 (trovate: {ports})")
        if not get_route_host("todo-mcp", project):
            step.add_error("Route 'todo-mcp' non trovata")

    materials_dir = lab_materials_dir(LAB_NAME)
    env_path = os.path.join(materials_dir, "client-chat-app", "agent_config.env")

    with GradingStep("agent_config.env e' configurato correttamente") as step:
        env = parse_env_file(env_path)
        if not env:
            step.fail(f"File non trovato in {env_path}")
        else:
            llamastack_host = get_route_host("llamastack-api", project)

            ls_url = env.get("LLAMA_STACK_URL", "")
            if not ls_url:
                step.add_error("LLAMA_STACK_URL non e' stato impostato")
            elif llamastack_host and llamastack_host not in ls_url:
                step.add_error(
                    f"LLAMA_STACK_URL ('{ls_url}') non punta alla Route "
                    f"'llamastack-api' ('{llamastack_host}')"
                )

            model = env.get("LLAMA_STACK_MODEL", "")
            if not model:
                step.add_error("LLAMA_STACK_MODEL non e' stato impostato")
            elif MCP_MODEL_NAME not in model:
                step.add_error(
                    f"LLAMA_STACK_MODEL ('{model}') non identifica il modello "
                    f"distribuito ('{MCP_MODEL_NAME}')"
                )

            mcp_url = env.get("MCP_SSE_URL", "")
            expected_mcp_dns = f"todo-mcp.{project}.svc"
            if not mcp_url:
                step.add_error("MCP_SSE_URL non e' stato impostato")
            elif expected_mcp_dns not in mcp_url or ":8081" not in mcp_url:
                step.add_error(
                    f"MCP_SSE_URL ('{mcp_url}') non punta al Service interno "
                    f"todo-mcp sulla porta 8081 (atteso host '{expected_mcp_dns}')"
                )

            if not env.get("MCP_SERVER_LABEL", ""):
                step.add_error("MCP_SERVER_LABEL non e' stato impostato")


if __name__ == "__main__":
    main()
