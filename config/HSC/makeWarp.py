# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import os.path

# HACK: Throw away any changes imposed by obs configs.
config.loadFromString(type(config)().saveToString())

config.makePsfMatched = True
config.doApplySkyCorr = True

config.modelPsf.defaultFwhm = 7.7
config.warpAndPsfMatch.psfMatch.kernel["AL"].kernelSize = 29
config.warpAndPsfMatch.psfMatch.kernel["AL"].alardSigGauss = [1.0, 2.0, 4.5]
config.warpAndPsfMatch.warp.warpingKernelName = "lanczos5"
config.coaddPsf.warpingKernelName = "lanczos5"
