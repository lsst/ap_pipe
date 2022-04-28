# Enable HSM shapes (unsetup meas_extensions_shapeHSM to disable)
# 'config' is a SourceMeasurementConfig.

# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path
from lsst.utils import getPackageDir

try:
    config.load(os.path.join(getPackageDir("meas_extensions_shapeHSM"), "config", "enable.py"))
    config.plugins["ext_shapeHSM_HsmShapeRegauss"].deblendNChild = "deblend_nChild"
    # Enable debiased moments
    config.plugins.names |= ["ext_shapeHSM_HsmPsfMomentsDebiased"]
except LookupError as e:
    print("Cannot enable shapeHSM (%s): disabling HSM shape measurements" % (e,))
