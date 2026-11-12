"""
Try-exam EX180, 7 — health probe: liveness e readiness.

Il tema: "imposta delle probes (health probes, liveness probe)". Non dice
quali ne' come: qui si chiedono una liveness E una readiness probe HTTP GET
(la "health probe" del tema letta come readiness: e' una nostra
interpretazione).

Scostamenti dal tema annotato (scelte nostre): deployment web (httpd UBI 9,
porta 8080), tipo di probe (HTTP GET su / porta 8080), progetto. I tempi
(initialDelaySeconds, periodSeconds, ...) non sono richiesti e non vengono
gradati.

Il setup() monta nella document root (/var/www/html) una ConfigMap con un
index.html: senza, l'httpd delle immagini RHEL/UBI risponde a "/" con la
pagina di benvenuto e codice 403 (welcome.conf), e una probe HTTP su "/"
fallirebbe sempre (il kubelet considera riuscita solo una risposta 200-399).
Non verificato dal vivo su ubi9/httpd-24: e' una precauzione.

La porta della probe puo' essere un numero o il NOME di una porta del
container (IntOrString): un nome si risolve in containerPort guardando
container.ports. Un path vuoto equivale a "/" (il kubelet chiede "/").
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, HTTP_PORT, GradingStep, oc, oc_get_json, reset_project,
    delete_project, check_project, create_httpd_deployment, pod_spec, ready_pods, run_cli,
)

SLUG = "e07"
PROJECT = "ex180-e07"
TITLE = "7) Liveness e readiness probe"
APP = "web"
PATH = "/"

TASK = f"""\
Nel progetto {PROJECT} trovi il deployment {APP} (httpd, ascolta sulla
porta {HTTP_PORT}).

Configura sul suo container:
  - una liveness probe di tipo HTTP GET sul path {PATH}, porta {HTTP_PORT};
  - una readiness probe di tipo HTTP GET sul path {PATH}, porta {HTTP_PORT}.

I tempi delle probe sono a tua scelta. Il deployment deve restare
disponibile.
"""

SOLUTION = f"""\
oc project {PROJECT}
oc set probe deployment/{APP} --liveness  --get-url=http://:{HTTP_PORT}{PATH}
oc set probe deployment/{APP} --readiness --get-url=http://:{HTTP_PORT}{PATH}
#   (facoltativi: --initial-delay-seconds=5 --period-seconds=10 ...)

oc describe deployment/{APP} | grep -E 'Liveness|Readiness'
oc get pods                          # READY 1/1
"""


def _resolve_port(container, port):
    if isinstance(port, int):
        return port
    if isinstance(port, str) and port.isdigit():
        return int(port)
    for p in container.get("ports") or []:
        if p.get("name") == port:
            return p.get("containerPort")
    return None


def probe_problems(container, kind):
    """Lista di problemi della probe `kind` ('livenessProbe' | 'readinessProbe'),
    vuota se e' un HTTP GET su PATH/HTTP_PORT."""
    probe = container.get(kind)
    if not probe:
        return ["non definita"]
    http = probe.get("httpGet")
    if not http:
        other = next((k for k in ("tcpSocket", "exec", "grpc") if k in probe), "?")
        return [f"e' di tipo {other}, non HTTP GET"]
    errors = []
    if (http.get("path") or "/") != PATH:
        errors.append(f"path = {http.get('path')!r}")
    port = _resolve_port(container, http.get("port"))
    if port != HTTP_PORT:
        errors.append(f"porta = {http.get('port')!r}"
                      + (f" (-> {port})" if port not in (None, http.get("port")) else ""))
    return errors


def _good_containers(obj):
    """Container (di un deployment o di un pod) con entrambe le probe giuste."""
    return [c for c in pod_spec(obj).get("containers") or []
            if not probe_problems(c, "livenessProbe") and not probe_problems(c, "readinessProbe")]


def setup():
    reset_project(PROJECT)
    oc("create", "configmap", "web-content",
       "--from-literal=index.html=<html><body>EX180 probe test</body></html>",
       "-n", PROJECT, check=True)
    create_httpd_deployment(APP, PROJECT)
    oc("set", "volume", f"deployment/{APP}", "--add", "--name=content", "--type=configmap",
       "--configmap-name=web-content", "--mount-path=/var/www/html", "-n", PROJECT, check=True)


def grade():
    check_project(PROJECT)
    dep = oc_get_json("deployment", APP, "-n", PROJECT)
    containers = pod_spec(dep).get("containers") or []

    with GradingStep(f"Il deployment {APP} esiste") as step:
        if not dep:
            step.fail(f"Deployment '{APP}' non trovato in {PROJECT}")

    for kind, label in (("livenessProbe", "liveness"), ("readinessProbe", "readiness")):
        with GradingStep(f"{label.capitalize()} probe HTTP GET {PATH} sulla porta {HTTP_PORT}") as step:
            if not containers:
                step.fail("Deployment (o container) non trovato")
            elif not any(not probe_problems(c, kind) for c in containers):
                for c in containers:
                    for err in probe_problems(c, kind):
                        step.add_error(f"container {c.get('name')}: {err}")

    with GradingStep(f"Il deployment {APP} e' disponibile con le probe attive") as step:
        if not dep:
            step.fail("Deployment non trovato")
        elif not ready_pods(dep, PROJECT, lambda p: bool(_good_containers(p))):
            step.fail("nessun pod Running e Ready con le due probe (una probe sbagliata "
                      "tiene il pod non pronto o lo fa riavviare: oc describe pod)")


def cleanup():
    delete_project(PROJECT)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
