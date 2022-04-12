# Set up aperture photometry
# 'config' should be a SourceMeasurementConfig

# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

config.plugins.names |= ["base_CircularApertureFlux"]
# Roughly (1.0, 1.5, 2.0, 3.0, 4.0, 5.7, 8.4, 11.8, 16.8, 23.5 arcsec) in diameter: 2**(0.5*i)
# (assuming plate scale of 0.168 arcsec pixels)
config.plugins["base_CircularApertureFlux"].radii = [3.0, 4.5, 6.0, 9.0, 12.0, 17.0, 25.0, 35.0, 50.0, 70.0]

# Use a large aperture to be independent of seeing in calibration
config.plugins["base_CircularApertureFlux"].maxSincRadius = 12.0
