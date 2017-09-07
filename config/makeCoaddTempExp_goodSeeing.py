from lsst.ap.pipe import MaxPsfWcsSelectImagesTask

config.bgSubtracted=True

# changing coaddName from deep requires modifying the obs_ package--wait 
# until after upcoming RFD
#config.coaddName='goodSeeing'

config.select.retarget(MaxPsfWcsSelectImagesTask)
config.makePsfMatched=True
config.makeDirect=True
# !! This must be the same as the kernelSize in the processEimage
# psfMeasurement.
config.modelPsf.size=25
