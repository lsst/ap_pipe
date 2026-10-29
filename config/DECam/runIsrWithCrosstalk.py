# Config fragment for lsst.ip.isr.IsrTask
# This config supports overscan output from pipelines/DECam/RunIsrForCrosstalkSources.
# It does not override any other aspect of the ISR config and is not intended
# as a standalone config file. obs_decam enables overscan and crosstalk
# correction.

config.connections.crosstalkSources = "overscanRaw"
