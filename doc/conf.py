#!/usr/bin/env python

from documenteer.sphinxconfig.stackconf import build_package_configs
import lsst.ap.pipe

_g = globals()
_g.update(build_package_configs(
    project_name='ap_pipe',
    version=lsst.ap.pipe.version.__version__))
