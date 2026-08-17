#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise images-basics, sprovvista di
`lab grade` ufficiale (la classe ImageBasics nel pacchetto do188 implementa
solo start()/finish(), non grade()).

L'esercizio (Cap. 3.2 "Container Image Registries") non crea un progetto
OpenShift proprio: usa OpenShift SOLO come registry interno delle immagini
(`registry.ocp4.example.com:8443`). Il compito e': `skopeo copy` dell'immagine
`default-route-openshift-image-registry.apps.ocp4.example.com/default/python:3.9-ubi8`
verso `registry.ocp4.example.com:8443/developer/python:3.9-ubi8`, poi renderla
PUBBLICA in quel registry interno (rimuovendo le RoleBinding che richiedono
autenticazione), infine verificare con `podman logout --all` seguito da
`podman pull` che l'immagine sia scaricabile senza credenziali.

Questo stato PERSISTE oltre l'esercizio: finish() (vedi do188/images-basics.py)
esegue solo pulizia di container/immagini Podman locali, non toglie
l'immagine dal registry interno né la richiude a privata. Il check e' quindi
valido sia durante l'esercizio che dopo `lab finish`.

Verifica: `skopeo inspect docker://<image>` SENZA credenziali (ne' --creds,
ne' login) deve avere successo. E' lo stesso pattern usato dal grading
ufficiale del corso per verificare i push degli studenti (vedi
do188/images-lab.py, funzione _check_remote_image) — e conferma che, nella
classroom "normale" (non DEV_LOCAL), la CA del registry e' gia' fidata, quindi
non serve --tls-verify=false.

Uso: images-basics.py   (nessun progetto OpenShift: e' solo interazione col registry)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, skopeo_inspect

LAB_NAME = "images-basics"
REGISTRY = "registry.ocp4.example.com:8443"
IMAGE = f"{REGISTRY}/developer/python:3.9-ubi8"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(
        f"L'immagine '{IMAGE}' e' stata copiata nel registry interno ed e' pubblica"
    ) as step:
        ok, _ = skopeo_inspect(IMAGE)
        if not ok:
            step.fail(
                f"'skopeo inspect docker://{IMAGE}' senza credenziali non ha "
                "successo: l'immagine non e' stata copiata nel registry "
                "interno, oppure non e' stata resa pubblica (assicurarsi di "
                "aver fatto `podman logout --all` prima di verificare)"
            )


if __name__ == "__main__":
    main()
