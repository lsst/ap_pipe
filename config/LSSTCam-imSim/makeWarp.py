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

# This file was copied from obs_lsst as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path

# Load configs shared between assembleCoadd and makeCoaddTempExp
config.load(os.path.join(os.path.dirname(__file__), "coaddBase.py"))

config.makePsfMatched = True
config.warpAndPsfMatch.psfMatch.kernel['AL'].alardSigGauss = [1.0, 2.0, 4.5]
config.modelPsf.defaultFwhm = 7.7

# FUTURE: Set both to True when we decide to run jointcal
config.doApplyExternalPhotoCalib = False
config.doApplyExternalSkyWcs = False

# FUTURE: Set to True when we have sky background estimate
config.doApplySkyCorr = False

# This file was inserted from obs_lsst/config/imsim/makeWarp.py as part of
# DM-31063. Feel free to modify this file to better reflect the needs of AP;
# however, when it comes time to permanently remove the obs_* configs, we
# should check that none of the changes made there since April 12, 2022 would
# be useful here.

# Set thresholds for PSF fidelity of visit/detector to get included in coadd.
# These thresholds have been conditioned based on the w_2021_48 processing
# of the test-med-1 dataset and the w_2021_40 processing of the ~5-yr depth
# 4431 tract (and considering the HSC thresholds by comparing the metric
# distributions). See DM-32625 for details.
config.select.maxEllipResidual = 0.0045
config.select.maxScaledSizeScatter = 0.006
