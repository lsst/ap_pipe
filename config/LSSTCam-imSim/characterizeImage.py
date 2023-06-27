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

# HACK: Throw away any changes imposed by obs configs, especially plugins.
config.loadFromString(type(config)().saveToString())

obsConfigDir = os.path.join(os.path.dirname(__file__))

# Cosmic rays and background estimation
config.repair.cosmicray.nCrPixelMax = 1000000
config.repair.cosmicray.cond3_fac2 = 0.4

# PSF determination
config.measurePsf.reserve.fraction = 0.2

# Activate calibration of measurements: required for aperture corrections
config.measurement.load(os.path.join(obsConfigDir, "apertures.py"))

config.measurement.plugins.names |= ["base_Jacobian", "base_FPPosition"]

config.measurement.plugins["base_Jacobian"].pixelScale = 0.2

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

# S/N cuts for computing aperture corrections to include only objects that
# were used in the PSF model and have PSF flux S/N greater than the minimum
# set (DM-23071).
config.measureApCorr.sourceSelector["science"].doFlags = True
config.measureApCorr.sourceSelector["science"].doSignalToNoise = True
config.measureApCorr.sourceSelector["science"].flags.good = ["calib_psf_used"]
config.measureApCorr.sourceSelector["science"].flags.bad = []
config.measureApCorr.sourceSelector["science"].signalToNoise.minimum = 150.0
config.measureApCorr.sourceSelector.name = "science"
