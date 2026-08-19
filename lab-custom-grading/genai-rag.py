"""
Grading personalizzato per 'genai-rag' (AI0022L - RAG Applications).

Come 'genai-app', `lab start` (ai0022l/exercises/genai_rag.py) distribuisce
gia' lui vLLM e Llama Stack; il compito dello studente e' completare 4 TODO
nei file copiati localmente in ~/course/labs/genai-rag/ (confrontati con
materials/solutions/genai-rag/ per la specifica esatta): creare il vector
store, ingerire i documenti, interrogarlo e costruire il prompt RAG finale.
Nessuna di queste modifiche produce una risorsa Kubernetes verificabile: si
gradano i file locali.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, project_exists, lab_materials_dir, read_text_file

LAB_NAME = "genai-rag"

# Per ciascun file: le stringhe la cui presenza indica il TODO completato
CHECKS = {
    "register_vector_db.py": [
        "client.vector_stores.create(",
        "embedding_model",
    ],
    "ingest_documents.py": [
        "client.files.create(",
        "client.vector_stores.files.create(",
    ],
    "query_rag.py": [
        "client.vector_stores.search(",
        "vector_store_id=vs_id",
    ],
    "rag_application.py": [
        "client.chat.completions.create(",
        "context",
    ],
}


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    materials_dir = lab_materials_dir(LAB_NAME)

    for filename, required_snippets in CHECKS.items():
        with GradingStep(f"{filename} completa il TODO richiesto") as step:
            content = read_text_file(os.path.join(materials_dir, filename))
            if content is None:
                step.fail(f"File {filename} non trovato in {materials_dir}")
                continue
            if "TODO" in content:
                step.add_error("E' ancora presente un TODO non completato")
            for snippet in required_snippets:
                if snippet not in content:
                    step.add_error(f"Non trovato '{snippet}'")


if __name__ == "__main__":
    main()
