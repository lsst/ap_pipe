# Enable the basic HSM shapes, which is preferred over SdssShape.
# `config` is a SourceMeasurementConfig.

import lsst.meas.extensions.shapeHSM

config.plugins.names |= ["ext_shapeHSM_HsmSourceMoments", "ext_shapeHSM_HsmPsfMoments"]
config.slots.shape = "ext_shapeHSM_HsmSourceMoments"
config.slots.psfShape = "ext_shapeHSM_HsmPsfMoments"
