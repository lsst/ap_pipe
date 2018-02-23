from lsst.ip.diffim import GetCalexpAsTemplateTask

config.differencer.getTemplate.retarget(GetCalexpAsTemplateTask)
config.differencer.doSelectSources = True
config.differencer.detection.thresholdValue = 5.0
config.differencer.doDecorrelation = True
