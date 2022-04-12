# This file was copied from obs_decam as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

# Enable measurement of convolved fluxes
# 'config' is a SourceMeasurementConfig
try:
    import lsst.meas.extensions.convolved  # noqa: Load flux.convolved algorithm
except ImportError as exc:
    import logging
    logging.getLogger("lsst.obs.decam.config").warning("Cannot import lsst.meas.extensions.convolved (%s):"
                                                       " disabling convolved flux measurements", exc)
else:
    config.plugins.names.add("ext_convolved_ConvolvedFlux")
    config.plugins["ext_convolved_ConvolvedFlux"].seeing.append(8.0)
