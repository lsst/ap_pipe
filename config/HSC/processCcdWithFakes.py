# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path

# HACK: Throw away any changes imposed by obs configs, especially plugins.
config.loadFromString(type(config)().saveToString())

ObsConfigDir = os.path.dirname(__file__)

# The following configs are copied from `ap_pipe/config/HSC/calibrate.py`
# We do not import the full file directly because only a minimal form of
# calibrateTask is used during `processCcdWithFakesTask`.

# Set to match defaults currently used in HSC production runs (e.g. S15B)
config.calibrate.catalogCalculation.plugins['base_ClassificationExtendedness'].fluxRatio = 0.95

config.calibrate.doWriteMatchesDenormalized = True

# Detection
config.calibrate.detection.isotropicGrow = True

config.calibrate.measurement.load(os.path.join(ObsConfigDir, "apertures.py"))

# Deblender
config.calibrate.deblend.maxFootprintSize = 0
# Ignore sources that are in the vignetted region
config.calibrate.deblend.maskLimits["NO_DATA"] = 0.25
config.calibrate.deblend.maxFootprintArea = 10000

config.calibrate.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]
config.calibrate.measurement.plugins["base_Jacobian"].pixelScale = 0.168
