from lsst.ip.diffim import GetCalexpAsTemplateTask

config.differencer.getTemplate.retarget(GetCalexpAsTemplateTask)
config.differencer.doSelectSources = True
