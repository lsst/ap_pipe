#!/bin/sh
set -eu

# An executable script that will prepare and submit the daytime Alert Production pipeline

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 YYYY-MM-DD" >&2
    exit 1
fi

DATE="$1"

# POSIX-safe date normalization
DAY_OBS=$(printf '%s\n' "$DATE" | tr -d '-')

# Create a temp file with the date in the name
TMP_APDB_REL=$(mktemp "apdb_config_${DATE}.XXXXXX.yaml")

# Resolve to absolute path without readlink -f
case "$TMP_APDB_REL" in
    /*) TMP_APDB="$TMP_APDB_REL" ;;
    *)  TMP_APDB="$(pwd)/$TMP_APDB_REL" ;;
esac

# Copy APDB config from S3 using Singularity AWS CLI
singularity exec /sdf/sw/s3/aws-cli_latest.sif \
  aws --endpoint-url https://sdfembs3.sdf.slac.stanford.edu s3 \
  --profile embargo-s3 \
  cp s3://rubin-summit-users/apdb_config/cassandra/pp_apdb_lsstcam.yaml \
  "$TMP_APDB"

# NOTE:
# No cleanup of TMP_APDB here since the job is launched with nohup
# and runtime duration is unknown.

# Redirect Cassandra logs
export DAX_APDB_MONITOR_CONFIG="logging:lsst.dax.apdb.monitor"

# Configure the filesystem to allow many open files
ulimit -n 65536

INSTRUMENT="LSSTCam"

# List of detectors currently excluded from Prompt Processing
# These include the non-imaging wavefront sensors as well as some that are disabled in fan-out.
# See https://github.com/lsst-sqre/phalanx/blob/main/applications/next-visit-fan-out/values-usdfprod-prompt-processing.yaml
BAD_DETECTORS="120 122 0 20 27 65 123 161 168 188 1 19 30 68 158 169 187 \
189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204"

# Space-delimited list of observing blocks that generate science images
BLOCKS="BLOCK-407 BLOCK-408 BLOCK-416 BLOCK-417 BLOCK-419 BLOCK-421 BLOCK-T637"

OUTPUT_COLLECTION="LSSTCam/prompt/output-${DATE}/daytime"

# Convert lists to SQL IN() form
BAD_DETECTORS_SQL="($(printf '%s,' $BAD_DETECTORS | sed 's/,$//'))"
BLOCKS_SQL="($(printf "'%s'," $BLOCKS | sed 's/,$//'))"

nohup bps submit "${AP_PIPE_DIR}/bps/LSSTCam/bps_Daytime.yaml" \
  --extra-qgraph-options "--skip-existing-in LSSTCam/prompt/output-${DATE} -c parameters:release_id=1 -c parameters:apdb_config=${TMP_APDB} --dataset-query-constraint template_coadd" \
  --extra-run-quantum-options "--no-raise-on-partial-outputs" \
  --input "LSSTCam/defaults,LSSTCam/templates,LSSTCam/prompt/output-${DATE}" \
  --output "$OUTPUT_COLLECTION" \
  -d "instrument='$INSTRUMENT' \
      AND skymap='lsst_cells_v1' \
      AND detector NOT IN $BAD_DETECTORS_SQL \
      AND day_obs=$DAY_OBS \
      AND exposure.science_program IN $BLOCKS_SQL" \
  > "output-${DATE}-step1.out" 2>&1 &

echo "Submission started for date ${DATE}"
echo "Temporary APDB config: ${TMP_APDB}"
echo "Submission output log written to output-${DATE}.out"
