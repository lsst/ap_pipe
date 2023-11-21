# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path

from lsst.meas.algorithms import ColorLimit
from lsst.meas.astrom import MatchOptimisticBConfig

# HACK: Throw away any changes imposed by obs configs, especially plugins.
config.loadFromString(type(config)().saveToString())

ObsConfigDir = os.path.dirname(__file__)

# Use PS1 for HSC astrometric calibration; Gaia is not dense enough to work
# for all of the the deep and narrower HSC images.
config.connections.astromRefCat = "ps1_pv3_3pi_20170110"
config.astromRefObjLoader.load(os.path.join(ObsConfigDir, "filterMap.py"))
# Gaia uses anyFilterMapsToThis: override it for PS1.
config.astromRefObjLoader.anyFilterMapsToThis = None

# Use the HSC filterMap for PS1 photometric calibration.
config.photoRefObjLoader.load(os.path.join(ObsConfigDir, "filterMap.py"))

# Set to match defaults currently used in HSC production runs (e.g. S15B)
config.astrometry.wcsFitter.numRejIter = 3
config.astrometry.wcsFitter.order = 3

config.astrometry.matcher.maxRotationDeg = 1.145916

config.photoCal.applyColorTerms = True
config.photoCal.photoCatName = "ps1_pv3_3pi_20170110"
colors = config.photoCal.match.referenceSelection.colorLimits
colors["g-r"] = ColorLimit(primary="g_flux", secondary="r_flux", minimum=0.0)
colors["r-i"] = ColorLimit(primary="r_flux", secondary="i_flux", maximum=0.5)
config.photoCal.match.referenceSelection.doMagLimit = True
config.photoCal.match.referenceSelection.magLimit.fluxField = "i_flux"
config.photoCal.match.referenceSelection.magLimit.maximum = 22.0
config.photoCal.colorterms.load(os.path.join(ObsConfigDir, 'colorterms.py'))


config.measurement.load(os.path.join(ObsConfigDir, "apertures.py"))

config.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]
config.measurement.plugins["base_Jacobian"].pixelScale = 0.168
