# Enable measurement of convolved fluxes
# 'config' is a SourceMeasurementConfig

# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

try:
    import lsst.meas.extensions.convolved  # noqa: Load flux.convolved algorithm
except ImportError as exc:
    print("Cannot import lsst.meas.extensions.convolved (%s): disabling convolved flux measurements" % (exc,))
else:
    config.plugins.names.add("ext_convolved_ConvolvedFlux")
    config.plugins["ext_convolved_ConvolvedFlux"].seeing.append(8.0)
