# This file is part of ap_pipe.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.

"""
LSST Cam-specific overrides for CharacterizeImageTask
"""

# This file was copied from obs_lsst as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path

obsConfigDir = os.path.join(os.path.dirname(__file__))

bgFile = os.path.join(obsConfigDir, "background.py")

# Cosmic rays and background estimation
config.repair.cosmicray.nCrPixelMax = 1000000
config.repair.cosmicray.cond3_fac2 = 0.4
config.background.load(bgFile)
config.detection.background.load(bgFile)

# Enable temporary local background subtraction
config.detection.doTempLocalBackground=True

# PSF determination
config.measurePsf.reserve.fraction = 0.2
config.measurePsf.starSelector["objectSize"].sourceFluxField = 'base_PsfFlux_instFlux'

# Astrometry
config.refObjLoader.load(os.path.join(obsConfigDir, 'filterMap.py'))
config.refObjLoader.ref_dataset_name = 'cal_ref_cat'

# Set to match defaults currenyly used in HSC production runs (e.g. S15B)
config.catalogCalculation.plugins['base_ClassificationExtendedness'].fluxRatio = 0.95

# Detection
config.detection.isotropicGrow = True

# Activate calibration of measurements: required for aperture corrections
config.load(os.path.join(obsConfigDir, "cmodel.py"))
config.measurement.load(os.path.join(obsConfigDir, "apertures.py"))
config.measurement.load(os.path.join(obsConfigDir, "kron.py"))
config.measurement.load(os.path.join(obsConfigDir, "convolvedFluxes.py"))
config.measurement.load(os.path.join(obsConfigDir, "gaap.py"))
config.measurement.load(os.path.join(obsConfigDir, "hsm.py"))
if "ext_shapeHSM_HsmShapeRegauss" in config.measurement.plugins:
    # no deblending has been done
    config.measurement.plugins["ext_shapeHSM_HsmShapeRegauss"].deblendNChild = ""

# Deblender
config.deblend.maskLimits["NO_DATA"] = 0.25 # Ignore sources that are in the vignetted region
config.deblend.maxFootprintArea = 10000

config.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]

# Convolved fluxes can fail for small target seeing if the observation seeing is larger
if "ext_convolved_ConvolvedFlux" in config.measurement.plugins:
    names = config.measurement.plugins["ext_convolved_ConvolvedFlux"].getAllResultNames()
    config.measureApCorr.allowFailure += names

if "ext_gaap_GaapFlux" in config.measurement.plugins:
    names = config.measurement.plugins["ext_gaap_GaapFlux"].getAllGaapResultNames()
    config.measureApCorr.allowFailure += names

config.measurement.plugins["base_Jacobian"].pixelScale = 0.2

# Prevent spurious detections in vignetting areas
config.detection.thresholdType ='pixel_stdev'

# This file was inserted from obs_lsst/config/imsim/characterizeImage.py as
# part of DM-31063. Feel free to modify this file to better reflect the needs
# of AP; however, when it comes time to permanently remove the obs_* configs,
# we should check that none of the changes made there since April 12, 2022
# would be useful here.

# Reduce Chebyshev polynomial order for background fitting (DM-30820)
config.background.approxOrderX = 1
config.detection.background.approxOrderX = 1
config.detection.tempLocalBackground.approxOrderX = 1
config.detection.tempWideBackground.approxOrderX = 1
config.repair.cosmicray.background.approxOrderX = 1

# Select candidates for PSF modeling based on S/N threshold (DM-17043 & DM-16785)
config.measurePsf.starSelector["objectSize"].doFluxLimit = False
config.measurePsf.starSelector["objectSize"].doSignalToNoiseLimit = True

# S/N cuts for computing aperture corrections to include only objects that
# were used in the PSF model and have PSF flux S/N greater than the minimum
# set (DM-23071).
config.measureApCorr.sourceSelector["science"].doFlags = True
config.measureApCorr.sourceSelector["science"].doSignalToNoise = True
config.measureApCorr.sourceSelector["science"].flags.good = ["calib_psf_used"]
config.measureApCorr.sourceSelector["science"].flags.bad = []
config.measureApCorr.sourceSelector["science"].signalToNoise.minimum = 150.0
config.measureApCorr.sourceSelector.name = "science"
