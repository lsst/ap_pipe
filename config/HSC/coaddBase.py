# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

# Configs shared between makeCoaddTempExp and assemble
config.matchingKernelSize = 29
config.doApplyExternalPhotoCalib = True
config.externalPhotoCalibName = 'fgcm'
config.doApplyExternalSkyWcs = True
