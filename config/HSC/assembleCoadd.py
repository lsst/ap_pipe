# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path

# HACK: Throw away any changes imposed by obs configs.
config.loadFromString(type(config)().saveToString())

# Load configs shared between assembleCoadd and makeCoaddTempExp
config.load(os.path.join(os.path.dirname(__file__), "coaddBase.py"))

# 200 rows (since patch width is typically < 10k pixels)
config.subregionSize = (10000, 200)
config.doMaskBrightObjects = True
config.removeMaskPlanes.append("CROSSTALK")
config.doNImage = True
config.badMaskPlanes += ["SUSPECT"]
config.doAttachTransmissionCurve = True
# Saturation trails are usually oriented east-west, so along rows
config.interpImage.transpose = True
config.coaddPsf.warpingKernelName = 'lanczos5'
config.matchingKernelSize = 29

from lsst.pipe.tasks.selectImages import PsfWcsSelectImagesTask
config.select.retarget(PsfWcsSelectImagesTask)
