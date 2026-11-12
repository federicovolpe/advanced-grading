"""
Try-exam EX180, 4 — deployment con il secret montato sotto /messages e la
configmap.

Il setup() crea gia' cio' che gli esercizi 2 e 3 avrebbero prodotto (la
ConfigMap app-config e il secret web-index dal file index.html), in un
progetto proprio: questo esercizio non dipende da come sono andati i due
precedenti.

Scostamenti dal tema annotato (scelte nostre): nome del deployment (web),
immagine (httpd UBI 9, come gli esercizi DO180 di training), progetto. Il
tema dice solo "e la configmap" senza dire COME usarla: si accetta qualunque
uso che la renda disponibile al container (envFrom, env con
configMapKeyRef, volume). /messages invece e' scritto nel tema.

Grading per risultato: il montaggio si cerca per contenuto (volume che punta
al secret, qualunque nome abbia), e la prova finale legge
/messages/index.html DENTRO un pod pronto della versione nuova del
deployment, confrontandolo col contenuto del secret.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, IMG_HTTPD, INDEX_HTML, GradingStep, oc, oc_get_json,
    reset_project, delete_project, check_project, write_index_html, configmap_used,
    volume_mounts, mounted_at, ready_pods, secret_value, pod_exec, run_cli,
)

SLUG = "e04"
PROJECT = "ex180-e04"
TITLE = "4) Deployment con secret montato e configmap"
APP = "web"
CM = "app-config"
SECRET = "web-index"
MOUNT = "/messages"

TASK = f"""\
Nel progetto {PROJECT} trovi gia' la ConfigMap {CM} e il secret
{SECRET} (creato dal file {INDEX_HTML}).

Crea un deployment di nome {APP} con l'immagine
    {IMG_HTTPD}
in modo che:
  - il secret {SECRET} sia montato come volume nella directory {MOUNT}
    del container (il file deve risultare {MOUNT}/index.html);
  - la ConfigMap {CM} sia resa disponibile al container
    (come variabili d'ambiente o come volume, a tua scelta).

Il deployment deve essere disponibile.
"""

SOLUTION = f"""\
oc project {PROJECT}
oc create deployment {APP} --image={IMG_HTTPD}

oc set volume deployment/{APP} --add --name=messages \\
    --type=secret --secret-name={SECRET} --mount-path={MOUNT}
oc set env deployment/{APP} --from=configmap/{CM}
#   (in alternativa: oc set volume deployment/{APP} --add --type=configmap \\
#        --configmap-name={CM} --mount-path=/config)

oc get pods
oc exec deployment/{APP} -- cat {MOUNT}/index.html
oc exec deployment/{APP} -- env | grep -E 'GREETING|APP_ENV'
"""


def setup():
    write_index_html()
    reset_project(PROJECT)
    oc("create", "configmap", CM, "--from-literal=GREETING=ciao", "--from-literal=APP_ENV=exam",
       "-n", PROJECT, check=True)
    oc("create", "secret", "generic", SECRET, f"--from-file=index.html={INDEX_HTML}",
       "-n", PROJECT, check=True)


def _image_ok(image):
    strip = lambda s: s[:-len(":latest")] if s.endswith(":latest") else s  # noqa: E731
    return strip(image or "") == strip(IMG_HTTPD)


def _pod_has_mount(pod):
    return mounted_at(pod, "secret", SECRET, MOUNT) is not None


def grade():
    check_project(PROJECT)
    dep = oc_get_json("deployment", APP, "-n", PROJECT)
    containers = (((dep or {}).get("spec") or {}).get("template") or {}).get("spec", {}).get("containers") or []

    with GradingStep(f"Il deployment {APP} esiste e usa l'immagine httpd richiesta") as step:
        if not dep:
            step.fail(f"Deployment '{APP}' non trovato in {PROJECT}")
        elif not any(_image_ok(c.get("image")) for c in containers):
            step.add_error(f"immagini: {[c.get('image') for c in containers]}")

    mount_container = mounted_at(dep, "secret", SECRET, MOUNT) if dep else None
    with GradingStep(f"Il secret {SECRET} e' montato su {MOUNT}") as step:
        if not dep:
            step.fail("Deployment non trovato")
        elif not mount_container:
            found = volume_mounts(dep, "secret", SECRET)
            if found:
                step.add_error("secret montato altrove: "
                               + ", ".join(f"{p} (container {c})" for c, p, _s in found))
            else:
                step.add_error(f"nessun volume del deployment monta il secret {SECRET}")

    with GradingStep(f"La ConfigMap {CM} e' usata dal deployment") as step:
        if not dep:
            step.fail("Deployment non trovato")
        elif not configmap_used(dep, CM):
            step.add_error("nessun envFrom/env/volume del pod fa riferimento alla ConfigMap "
                           f"{CM}")

    pods = ready_pods(dep, PROJECT, _pod_has_mount) if dep else []
    with GradingStep(f"Il deployment {APP} e' disponibile (pod pronto con il secret montato)") as step:
        if not dep:
            step.fail("Deployment non trovato")
        elif not pods:
            step.fail("nessun pod Running e Ready con il secret su "
                      f"{MOUNT} (oc get pods, oc describe pod)")

    with GradingStep(f"Nel pod, {MOUNT}/index.html ha il contenuto del secret") as step:
        expected = secret_value(oc_get_json("secret", SECRET, "-n", PROJECT), "index.html")
        if not pods:
            step.fail("nessun pod pronto con il montaggio (vedi check precedente)")
        elif expected is None:
            step.fail(f"il secret {SECRET} (chiave index.html) non e' piu' leggibile")
        else:
            pod = pods[0]
            container = mounted_at(pod, "secret", SECRET, MOUNT)
            out, err = pod_exec(PROJECT, pod["metadata"]["name"], container, "cat", f"{MOUNT}/index.html")
            if err:
                step.add_error(err)
            elif out != expected:
                step.add_error(f"contenuto diverso: {out[:80]!r}")


def cleanup():
    delete_project(PROJECT)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
