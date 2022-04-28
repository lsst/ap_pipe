# Enable CModel mags (unsetup meas_modelfit to disable)
# 'config' is a SourceMeasurementConfig.

# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

try:
    import lsst.meas.modelfit
    config.measurement.plugins.names |= ["modelfit_DoubleShapeletPsfApprox", "modelfit_CModel"]
    config.measurement.slots.modelFlux = 'modelfit_CModel'
    config.catalogCalculation.plugins['base_ClassificationExtendedness'].fluxRatio = 0.985
except (KeyError, ImportError):
    print("Cannot import lsst.meas.modelfit: disabling CModel measurements")
