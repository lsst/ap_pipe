# Pipeline Definitions

This directory contains pipeline definition YAML files which are used when processing data with the LSST Science Pipelines.

The pipelines defined here come in three flavors: camera-specific (within named directories), camera-agnostic (top-level, if any), and building-block ingredients (within the [\_ingredients](_ingredients) directory).
Pipelines within the ingredients directory are meant to be imported by other pipelines, and are not intended to be used directly by end-users.

The `pipetask build` command can be used to expand a pipeline YAML and resolve any imports for the purposes of visualizing it.
For example, to visualize the `apPipe` subset from the [LSSTCam-imSim ApPipe pipeline](https://github.com/lsst/ap_pipe/blob/main/pipelines/LSSTCam-imSim/ApPipe.yaml) pipeline, run:

```bash
pipetask build \
-p $AP_PIPE_DIR/pipelines/LSSTCam-imSim/ApPipe.yaml#apPipe \
--show pipeline
```
