#!/bin/bash
set -eu

# An executable script that will prepare and submit the daytime Alert Production pipeline

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 YYYYMMDD" >&2
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
#singularity exec /sdf/sw/s3/aws-cli_latest.sif \
#  aws --endpoint-url https://sdfembs3.sdf.slac.stanford.edu s3 \
#  --profile embargo-s3 \
#  cp s3://rubin-summit-users/apdb_config/cassandra/pp_apdb_lsstcam.yaml \
#  "$TMP_APDB"

echo "TMP_APDB = "$TMP_APDB
mc cp embargo/rubin-summit-users/apdb_config/cassandra/pp_apdb_lsstcam.yaml "$TMP_APDB"


# NOTE:
# No cleanup of TMP_APDB here since the job is launched in the background
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
# See https://github.com/lsst-sqre/phalanx/blob/main/applications/prompt-keda-lsstcam/values-usdfprod-prompt-processing.yaml#L21-L45
BLOCKS="BLOCK-365 BLOCK-407 BLOCK-408 BLOCK-416 BLOCK-417 BLOCK-419 BLOCK-421 \
BLOCK-T698 BLOCK-T703 BLOCK-T704 BLOCK-T706"

OUTPUT_COLLECTION="LSSTCam/runs/daytimeAP/${DATE}"

LOG_FILE="output-${DATE}.out"

# Convert lists to SQL IN() form
BAD_DETECTORS_SQL="($(printf '%s,' $BAD_DETECTORS | sed 's/,$//'))"
BLOCKS_SQL="($(printf "'%s'," $BLOCKS | sed 's/,$//'))"

# Pipeline and butler config must mirror bps_Daytime.yaml — we replicate them
# here because we build the quantum graph ourselves before calling BPS.
PIPELINE_YAML="${AP_PIPE_DIR}/pipelines/LSSTCam/ApPipe.yaml"
BUTLER_CONFIG="embargo"
INPUT_COLLECTIONS="LSSTCam/defaults,LSSTCam/templates,LSSTCam/runs/prompt-${DATE}"

# Generate an explicit output run so the pre-built and pruned quantum graphs
# share a single name with the eventual BPS submission.
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
OUTPUT_RUN="${OUTPUT_COLLECTION}/${TIMESTAMP}"

QGRAPH_DIR="$(pwd)/qgraphs/${DATE}/${TIMESTAMP}"
mkdir -p "$QGRAPH_DIR"
FULL_QGRAPH="${QGRAPH_DIR}/full.qg"
PRUNED_QGRAPH="${QGRAPH_DIR}/pruned.qg"

DATA_QUERY="instrument='$INSTRUMENT' \
    AND skymap='lsst_cells_v2' \
    AND detector NOT IN $BAD_DETECTORS_SQL \
    AND day_obs=$DAY_OBS \
    AND exposure.science_program IN $BLOCKS_SQL"

{
    set -e

    echo "[$(date)] Step 1/3: building full quantum graph"
    pipetask qgraph \
        -p "$PIPELINE_YAML" \
        -b "$BUTLER_CONFIG" \
        -i "$INPUT_COLLECTIONS" \
        --output "$OUTPUT_COLLECTION" \
        --output-run "$OUTPUT_RUN" \
        -d "$DATA_QUERY" \
        --skip-existing-in "LSSTCam/runs/prompt-${DATE}" \
        -c "parameters:release_id=1" \
        -c "parameters:apdb_config=${TMP_APDB}" \
        -c "associateApdb:doRunForcedMeasurement=False" \
        --dataset-query-constraint off \
        -q "$FULL_QGRAPH"

    echo "[$(date)] Step 2/3: pruning orphan loadDiaCatalogs quanta"
    python -m lsst.ap.pipe.prune_orphan_preloads \
        "$FULL_QGRAPH" "$PRUNED_QGRAPH"

    echo "[$(date)] Step 3/3: submitting BPS workflow with pruned graph"
    bps submit "${AP_PIPE_DIR}/bps/LSSTCam/bps_Daytime.yaml" \
        --qgraph "$PRUNED_QGRAPH" \
        --extra-run-quantum-options "--no-raise-on-partial-outputs" \
        --input "$INPUT_COLLECTIONS" \
        --output "$OUTPUT_COLLECTION" \
        --output-run "$OUTPUT_RUN"
} > "${LOG_FILE}" 2>&1 &
disown

echo "Submission started for date ${DATE}"
echo "Temporary APDB config: ${TMP_APDB}"
echo "Full quantum graph: ${FULL_QGRAPH}"
echo "Pruned quantum graph: ${PRUNED_QGRAPH}"
echo "Submission output log written to ${LOG_FILE}"
