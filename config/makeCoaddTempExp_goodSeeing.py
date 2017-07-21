from lsst.decam.hits import MaxPsfWcsSelectImagesTask

config.bgSubtracted=True

# changing coaddName from deep requires modifying the obs_ package--wait 
# until after upcoming RFD
#config.coaddName='goodSeeing'

config.select.retarget(MaxPsfWcsSelectImagesTask)
config.doPsfMatch=True
# !! This must be the same as the kernelSize in the processEimage psfMeasurement.
config.modelPsf.size=25
# I don't know why the wings hurt the matching so much, but I couldn't get matching to
# work in many cases with Run 3 data unless I turned this off.
config.modelPsf.addWing=False
config.warpAndPsfMatch.matchThenWarp=True
# Size (rows) in pixels of each SpatialCell for spatial modeling
config.warpAndPsfMatch.psfMatch.kernel['AL'].sizeCellX=500

# Size (columns) in pixels of each SpatialCell for spatial modeling
config.warpAndPsfMatch.psfMatch.kernel['AL'].sizeCellY=500

