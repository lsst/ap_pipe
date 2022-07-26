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

# Set to match defaults currently used in HSC production runs (e.g. S15B+)
config.calibrate.catalogCalculation.plugins['base_ClassificationExtendedness'].fluxRatio = 0.95

config.calibrate.doWriteMatchesDenormalized = True

# Detection
# This config matches obs_subaru, to facilitate 1:1 comparisons between DECam and HSC
config.calibrate.detection.isotropicGrow = True

config.calibrate.measurement.load(os.path.join(obsConfigDir, "apertures.py"))

# Deblender
# These configs match obs_subaru, to facilitate 1:1 comparisons between DECam and HSC
config.calibrate.deblend.maxFootprintSize = 0
config.calibrate.deblend.maskLimits["NO_DATA"] = 0.25  # Ignore sources that are in the vignetted region
config.calibrate.deblend.maxFootprintArea = 10000

config.calibrate.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]
config.calibrate.measurement.plugins["base_Jacobian"].pixelScale = 0.263
