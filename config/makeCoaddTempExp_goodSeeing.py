from lsst.pipe.tasks.selectImages import BestSeeingWcsSelectImagesTask

config.bgSubtracted = True
#config.coaddName='goodSeeing'
config.coaddName='deep'
config.select.retarget(BestSeeingWcsSelectImagesTask)
config.makePsfMatched = True
config.makeDirect = True
