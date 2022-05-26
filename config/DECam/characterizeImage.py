"""
DECam-specific overrides for CharacterizeImageTask
"""

# This file was copied from obs_decam as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path

from lsst.meas.astrom import MatchOptimisticBConfig

# HACK: Throw away any changes imposed by obs configs, especially plugins.
config.loadFromString(type(config)().saveToString())

obsConfigDir = os.path.dirname(__file__)

# Cosmic rays
# These configs match obs_subaru, to facilitate 1:1 comparisons between DECam and HSC
config.repair.cosmicray.nCrPixelMax = 100000
config.repair.cosmicray.cond3_fac2 = 0.4

# PSF determination
# These configs match obs_subaru, to facilitate 1:1 comparisons between DECam and HSC
config.measurePsf.reserve.fraction = 0.2
config.measurePsf.starSelector["objectSize"].sourceFluxField = "base_PsfFlux_instFlux"
config.measurePsf.starSelector["objectSize"].widthMin = 0.9
config.measurePsf.starSelector["objectSize"].fluxMin = 4000

# Set to match defaults currently used in HSC production runs (e.g. S15B)
config.catalogCalculation.plugins['base_ClassificationExtendedness'].fluxRatio = 0.95

# Detection
# This config matches obs_subaru, to facilitate 1:1 comparisons between DECam and HSC
config.detection.isotropicGrow = True

# Activate calibration of measurements: required for aperture corrections
config.measurement.load(os.path.join(obsConfigDir, "apertures.py"))
# hsm shapes are the preferred shape measurement (over SdssShape).
config.measurement.load(os.path.join(obsConfigDir, "../hsm.py"))

# Deblender
config.deblend.maskLimits["NO_DATA"] = 0.25  # Ignore sources that are in the vignetted region
config.deblend.maxFootprintArea = 10000

config.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]
config.measurement.plugins["base_Jacobian"].pixelScale = 0.263

# For aperture correction modeling, only use objects that were used in the
# PSF model and have psf flux signal-to-noise > 200.
# These configs match obs_subaru, to facilitate 1:1 comparisons between DECam and HSC
config.measureApCorr.sourceSelector['science'].doFlags = True
config.measureApCorr.sourceSelector['science'].doUnresolved = False
config.measureApCorr.sourceSelector['science'].doSignalToNoise = True
config.measureApCorr.sourceSelector['science'].flags.good = ["calib_psf_used"]
config.measureApCorr.sourceSelector['science'].flags.bad = []
config.measureApCorr.sourceSelector['science'].signalToNoise.minimum = 200.0
config.measureApCorr.sourceSelector['science'].signalToNoise.maximum = None
config.measureApCorr.sourceSelector['science'].signalToNoise.fluxField = "base_PsfFlux_instFlux"
config.measureApCorr.sourceSelector['science'].signalToNoise.errField = "base_PsfFlux_instFluxErr"
config.measureApCorr.sourceSelector.name = "science"

config.ref_match.sourceSelector.name = 'matcher'
for matchConfig in (config.ref_match,
                    ):
    matchConfig.sourceFluxType = 'Psf'
    matchConfig.sourceSelector.active.sourceFluxType = 'Psf'
    matchConfig.matcher.maxOffsetPix = 250
    if isinstance(matchConfig.matcher, MatchOptimisticBConfig):
        matchConfig.matcher.allowedNonperpDeg = 0.2
        matchConfig.matcher.maxMatchDistArcSec = 2.0
        matchConfig.sourceSelector.active.excludePixelFlags = False
