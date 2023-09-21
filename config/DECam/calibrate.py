"""
DECam-specific overrides for CalibrateTask
"""

# This file was copied from obs_decam as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path

from lsst.meas.algorithms import ColorLimit
from lsst.meas.astrom import MatchOptimisticBConfig

# HACK: Throw away any changes imposed by obs configs, especially plugins.
config.loadFromString(type(config)().saveToString())

obsConfigDir = os.path.join(os.path.dirname(__file__))

config.photoRefObjLoader.load(os.path.join(obsConfigDir, "filterMap.py"))

# Photometric calibration: use color terms
config.photoCal.applyColorTerms = True
colors = config.photoCal.match.referenceSelection.colorLimits
# The following two color limits are adopted from obs_subaru for the HSC SSP survey
colors["g-r"] = ColorLimit(primary="g_flux", secondary="r_flux", minimum=0.0)
colors["r-i"] = ColorLimit(primary="r_flux", secondary="i_flux", maximum=0.5)
config.photoCal.match.referenceSelection.doMagLimit = True
config.photoCal.match.referenceSelection.magLimit.fluxField = "i_flux"
config.photoCal.match.referenceSelection.magLimit.maximum = 22.0
config.photoCal.colorterms.load(os.path.join(obsConfigDir, 'colorterms.py'))

# The Task default was reduced from 4 to 2 on RFC-577. We believe that 4 is
# more appropriate for use with DECam data until a Jointcal-derived distortion
# model is available (DM-24431); at that point, this override should likely be
# removed.
# See Slack: https://lsstc.slack.com/archives/C2B6X08LS/p1586468459084600
config.astrometry.wcsFitter.order = 4

for matchConfig in (config.astrometry,
                    ):
    matchConfig.sourceFluxType = 'Psf'
    matchConfig.sourceSelector.active.sourceFluxType = 'Psf'
    matchConfig.matcher.maxOffsetPix = 250
    if isinstance(matchConfig.matcher, MatchOptimisticBConfig):
        matchConfig.matcher.allowedNonperpDeg = 0.2
        matchConfig.matcher.maxMatchDistArcSec = 2.0
        matchConfig.sourceSelector.active.excludePixelFlags = False


config.measurement.load(os.path.join(obsConfigDir, "apertures.py"))

config.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]
config.measurement.plugins["base_Jacobian"].pixelScale = 0.263
