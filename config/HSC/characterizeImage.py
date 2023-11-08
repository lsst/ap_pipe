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

# Cosmic rays and background estimation
config.repair.cosmicray.nCrPixelMax = 1000000
config.repair.cosmicray.cond3_fac2 = 0.4

# PSF determination
config.measurePsf.reserve.fraction = 0.2

# Activate calibration of measurements: required for aperture corrections
config.measurement.load(os.path.join(ObsConfigDir, "apertures.py"))

config.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]
config.measurement.plugins["base_Jacobian"].pixelScale = 0.168

# For aperture correction modeling, only use objects that were used in the
# PSF model and have psf flux signal-to-noise > 200.
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
