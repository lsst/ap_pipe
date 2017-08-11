# ap_pipe

This package contains the Prototype AP Pipeline.

The main script is `ap_pipe.py`, which allows a user to run
each step of the Prototype AP Pipeline on data from DECam.

Individual functions in `ap_pipe.py` will be called by 
[`ap_verify`](https://github.com/lsst-dm/ap_verify), but the 
pipeline can also be run on its own without verification metrics using a dataset
structured like [`ap_verify_hits2015`](https://github.com/lsst/ap_verify_hits2015).

For more detailed documentation, including a tutorial, 
please see [DMTN-039](https://dmtn-039.lsst.io).

**Note**: the tutorial portion of the technote is not up-to-date with master.
This will be remedied as part of [DM-11390](https://jira.lsstcorp.org/browse/DM-11390) 
and/or [DM-11422](https://jira.lsstcorp.org/browse/DM-11422).
