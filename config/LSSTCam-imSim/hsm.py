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


# Enable HSM shapes (unsetup meas_extensions_shapeHSM to disable)
# 'config' is a SourceMeasurementConfig.
import os.path
from lsst.utils import getPackageDir

try:
    config.load(os.path.join(getPackageDir("meas_extensions_shapeHSM"), "config", "enable.py"))
    config.plugins["ext_shapeHSM_HsmShapeRegauss"].deblendNChild = "deblend_nChild"
    # Enable debiased moments
    config.plugins.names |= ["ext_shapeHSM_HsmPsfMomentsDebiased"]
except LookupError as e:
    print("Cannot enable shapeHSM (%s): disabling HSM shape measurements" % (e,))
