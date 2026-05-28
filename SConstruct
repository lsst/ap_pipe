# -*- python -*-
import os

from lsst.sconsUtils import scripts, targets
from lsst.sconsUtils.state import env
from lsst.sconsUtils.utils import libraryLoaderEnvironment
from SCons.Script import Default, AddPostAction, Delete


# Python-only package
# Force shebang and policy to come first so the file first appears in the bin
# directory before it is used. This is required to run on macos.
PKG_ROOT = env.ProductDir("ap_pipe")

additional_fakes_tasks = os.path.join(
    PKG_ROOT,
    "pipelines",
    "_ingredients",
    "injection",
    "PostInjectedTasksApPipe.yaml",
)
ap_pipe_with_fakes_path = os.path.join(
    PKG_ROOT,
    "pipelines",
    "_ingredients",
    "ApPipeWithFakes.yaml"
)
intermediate_ap_pipe_with_fakes_path = os.path.join(
    PKG_ROOT,
    "pipelines",
    "_ingredients",
    "intermediate_ApPipeWithFakes.yaml"
)
template_injection_stub = os.path.join(
    PKG_ROOT,
    "pipelines",
    "_ingredients",
    "injection",
    "injectTemplate.yaml",
)

subset_names = ["apPipe", "prompt"]

intermediate_ap_pipe_with_fakes = env.Command(
    target=intermediate_ap_pipe_with_fakes_path,
    source=os.path.join(PKG_ROOT, "pipelines", "_ingredients", "ApPipe.yaml"),
    action=" ".join(
        [
            libraryLoaderEnvironment(),
            f"make_injection_pipeline  -t template_detector -r $SOURCE -f $TARGET ",
            f"-i {template_injection_stub} ",
            " ".join(f"-s {subset_name}" for subset_name in subset_names),
            f"--config injectTemplate:external_psf=False ",
            f"--config injectTemplate:external_photo_calib=False ",
            f"--config injectTemplate:external_wcs=False ",
            f"--prefix 'injectedTemplate_' -c parameters:apdb_config='-' --overwrite ",
        ]
    ),
)
ingredients_ap_pipe_with_fakes = env.Command(
    target=ap_pipe_with_fakes_path,
    source=intermediate_ap_pipe_with_fakes_path,
    action=" ".join(
        [
            libraryLoaderEnvironment(),
            f"make_injection_pipeline  -t preliminary_visit_image -r $SOURCE -f $TARGET "
            f"-a {additional_fakes_tasks} ",
            " ".join(f"-s {subset_name}" for subset_name in subset_names),
            f"--config injectVisit:external_psf=False ",
            f"--config injectVisit:external_photo_calib=False ",
            f"--config injectVisit:external_wcs=False ",
            f"--prefix 'fakes_' -c parameters:apdb_config='-' --overwrite ",
        ]
    ),
)
Default([ingredients_ap_pipe_with_fakes])
# Delete intermediate after final is successfully built
env.Clean(ingredients_ap_pipe_with_fakes, intermediate_ap_pipe_with_fakes_path)
AddPostAction(ingredients_ap_pipe_with_fakes, Delete(intermediate_ap_pipe_with_fakes_path))

targetList = (
    "version",
    "shebang",
    "policy",
    ap_pipe_with_fakes_path,
) + scripts.DEFAULT_TARGETS

scripts.BasicSConstruct(
    "ap_pipe", disableCc=True, noCfgFile=False, defaultTargets=targetList,
)

env.Depends(ap_pipe_with_fakes_path, targets["version"])
env.Depends(targets["tests"], ap_pipe_with_fakes_path)
