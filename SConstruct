# -*- python -*-
import os

from lsst.sconsUtils import scripts, targets
from lsst.sconsUtils.state import env
from lsst.sconsUtils.utils import libraryLoaderEnvironment
from SCons.Script import Default

# Python-only package
# Force shebang and policy to come first so the file first appears in the bin
# directory before it is used. This is required to run on macos.
PKG_ROOT = env.ProductDir("ap_pipe")

additional_fakes_tasks = os.path.join(
    PKG_ROOT,
    "pipelines",
    "_ingredients",
    "injection",
    "ApPipePostInjectedTasks.yaml",
)
ap_pipe_with_fakes_path = os.path.join(
    PKG_ROOT,
    "pipelines",
    "_ingredients",
    "ApPipeWithFakes.yaml"
)

subset_names = ["apPipe", "prompt"]

ingredients_ap_pipe_with_fakes = env.Command(
    target=ap_pipe_with_fakes_path,
    source=os.path.join(PKG_ROOT, "pipelines", "_ingredients", "ApPipe.yaml"),
    action=" ".join(
        [
            libraryLoaderEnvironment(),
            f"make_injection_pipeline  -t preliminary_visit_image -r $SOURCE -f $TARGET "
            f"-a {additional_fakes_tasks} ",
            " ".join(f"-s {subset_name}" for subset_name in subset_names),
            f"--config inject_visit:external_psf=False ",
            f"--config inject_visit:external_photo_calib=False ",
            f"--config inject_visit:external_wcs=False ",
            f"--prefix 'fakes_' -c parameters:apdb_config='-' --overwrite ",
        ]
    ),
)
Default([ingredients_ap_pipe_with_fakes])

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
