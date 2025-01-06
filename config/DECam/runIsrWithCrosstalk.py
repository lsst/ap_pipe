# Config fragment for lsst.ip.isr.IsrTask
# This config supports overscan output from pipelines/DECam/RunIsrForCrosstalkSources.
# It does not override any other aspect of the ISR config and is not intended
# as a standalone config file.

config.connections.crosstalkSources: 'overscanRaw'
config.doOverscan: True
config.doCrosstalk: True
