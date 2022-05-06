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
LSST Cam-specific overrides for CalibrateTask
"""

# This file was copied from obs_lsst as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path

# HACK: Throw away any changes imposed by obs configs, especially plugins.
config.loadFromString(type(config)().saveToString())

obsConfigDir = os.path.join(os.path.dirname(__file__))

bgFile = os.path.join(obsConfigDir, "background.py")

# Cosmic rays and background estimation
config.detection.background.load(bgFile)

# Enable temporary local background subtraction
config.detection.doTempLocalBackground  = True

# Reference catalog
for refObjLoader in (config.astromRefObjLoader,
                     config.photoRefObjLoader,
                     ):
    refObjLoader.load(os.path.join(obsConfigDir, 'filterMap.py'))
    refObjLoader.ref_dataset_name = 'cal_ref_cat'
    # Use the filterMap instead of the "any" filter.
    refObjLoader.anyFilterMapsToThis = None

config.connections.astromRefCat = "cal_ref_cat"
config.connections.photoRefCat = "cal_ref_cat"

# Set to match defaults currenyly used in HSC production runs (e.g. S15B)
config.catalogCalculation.plugins['base_ClassificationExtendedness'].fluxRatio = 0.95

# No color term in simulation at the moment
config.photoCal.applyColorTerms = False
config.photoCal.match.referenceSelection.doMagLimit = True
config.photoCal.match.referenceSelection.magLimit.fluxField = "lsst_i_smeared_flux"
config.photoCal.match.referenceSelection.magLimit.maximum = 22.0
# select only stars for photometry calibration
config.photoCal.match.sourceSelection.unresolved.maximum = 0.5

# Demand astrometry and photoCal succeed
config.requireAstrometry = True
config.requirePhotoCal = True

# Detection
config.detection.isotropicGrow = True

# Activate calibration of measurements: required for aperture corrections
config.measurement.load(os.path.join(obsConfigDir, "apertures.py"))
config.measurement.load(os.path.join(obsConfigDir, "kron.py"))
config.measurement.load(os.path.join(obsConfigDir, "hsm.py"))

# Deblender
config.deblend.maxFootprintSize = 0
config.deblend.maskLimits["NO_DATA"] = 0.25 # Ignore sources that are in the vignetted region
config.deblend.maxFootprintArea = 10000

config.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]

config.measurement.plugins["base_Jacobian"].pixelScale = 0.2

# Prevent spurious detections in vignetting areas
config.detection.thresholdType = 'pixel_stdev'

# This file was inserted from obs_lsst/config/imsim/calibrate.py as part of
# DM-31063. Feel free to modify this file to better reflect the needs of AP;
# however, when it comes time to permanently remove the obs_* configs, we
# should check that none of the changes made there since April 12, 2022 would
# be useful here.

# Additional configs for star+galaxy ref cats post DM-17917
config.astrometry.referenceSelector.doUnresolved = True
config.astrometry.referenceSelector.unresolved.name = "resolved"
config.astrometry.referenceSelector.unresolved.minimum = None
config.astrometry.referenceSelector.unresolved.maximum = 0.5

config.astromRefObjLoader.load(os.path.join(obsConfigDir, "filterMap.py"))
# Use the filterMap instead of the "any" filter.
config.astromRefObjLoader.anyFilterMapsToThis = None
config.photoRefObjLoader.load(os.path.join(obsConfigDir, "filterMap.py"))

config.astrometry.doMagnitudeOutlierRejection = True
# Set threshold above which astrometry will be considered a failure (DM-32129)
config.astrometry.maxMeanDistanceArcsec = 0.05

# Reduce Chebyshev polynomial order for background fitting (DM-30820)
config.detection.background.approxOrderX = 1
config.detection.tempLocalBackground.approxOrderX = 1
config.detection.tempWideBackground.approxOrderX = 1

# Make sure galaxies are not used for zero-point calculation.
config.photoCal.match.referenceSelection.doUnresolved = True
config.photoCal.match.referenceSelection.unresolved.name = "resolved"
config.photoCal.match.referenceSelection.unresolved.minimum = None
config.photoCal.match.referenceSelection.unresolved.maximum = 0.5

# S/N cuts for zero-point calculation source selection
config.photoCal.match.sourceSelection.doSignalToNoise = True
config.photoCal.match.sourceSelection.signalToNoise.minimum = 150
config.photoCal.match.sourceSelection.signalToNoise.fluxField = "base_PsfFlux_instFlux"
config.photoCal.match.sourceSelection.signalToNoise.errField = "base_PsfFlux_instFluxErr"
