# Enable GAaP (Gaussian Aperture and PSF) colors
# 'config' is typically a SourceMeasurementConfig

# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

try:
    import lsst.meas.extensions.gaap  # noqa
    config.plugins.names.add("ext_gaap_GaapFlux")
    config.plugins["ext_gaap_GaapFlux"].sigmas = [0.5, 0.7, 1.0, 1.5, 2.5, 3.0]
    # Enable PSF photometry after PSF-Gaussianization in the `ext_gaap_GaapFlux` plugin
    config.plugins["ext_gaap_GaapFlux"].doPsfPhotometry = True
except ImportError as exc:
    print("Cannot import lsst.meas.extensions.gaap (%s): disabling GAaP flux measurements" % (exc,))
