# This file is modeled after HSC's, and has all of the minimal DECam-specific
# calibrate configs. Since processCcdWithFakesTask uses a minimal version of
# calibrateTask, we can't import the whole thing, because it configs for
# astrometry and photometry; these are turned off in processCcdWithFakes.

import os.path

from lsst.meas.algorithms import ColorLimit
from lsst.meas.astrom import MatchOptimisticBConfig

# HACK: Throw away any changes imposed by obs configs, especially plugins.
config.loadFromString(type(config)().saveToString())

obsConfigDir = os.path.join(os.path.dirname(__file__))

config.calibrate.measurement.load(os.path.join(obsConfigDir, "apertures.py"))

config.calibrate.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]
config.calibrate.measurement.plugins["base_Jacobian"].pixelScale = 0.263
