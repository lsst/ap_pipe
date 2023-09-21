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

config.calibrate.measurement.load(os.path.join(ObsConfigDir, "apertures.py"))

config.calibrate.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]
config.calibrate.measurement.plugins["base_Jacobian"].pixelScale = 0.168
