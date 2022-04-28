# Set up aperture photometry
# 'config' should be a SourceMeasurementConfig

# This file was copied from obs_decam as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

# Use a large aperture to be independent of seeing in calibration
# This config matches obs_subaru, to facilitate 1:1 comparisons between DECam and HSC
config.plugins["base_CircularApertureFlux"].maxSincRadius = 12.0
