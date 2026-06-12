# Potentially dynamic variable definitions used by the AP Daytime submit script

# List of detectors currently excluded from Prompt Processing
# These include the non-imaging wavefront sensors as well as some that are disabled in fan-out.
# See https://github.com/lsst-sqre/phalanx/blob/main/applications/next-visit-fan-out/values-usdfprod-prompt-processing.yaml
BAD_DETECTORS="120 122 0 20 27 65 123 161 168 188 1 19 30 68 158 169 187 \
189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204"

# Space-delimited list of observing blocks that generate science images
# See https://github.com/lsst-sqre/phalanx/blob/main/applications/prompt-keda-lsstcam/values-usdfprod-prompt-processing.yaml#L21-L45
BLOCKS="BLOCK-365 BLOCK-407 BLOCK-408 BLOCK-416 BLOCK-417 BLOCK-419 BLOCK-421 \
BLOCK-T698 BLOCK-T703 BLOCK-T704 BLOCK-T706"

# Convert lists to SQL IN() form
export BAD_DETECTORS_SQL="($(printf '%s,' $BAD_DETECTORS | sed 's/,$//'))"
export BLOCKS_SQL="($(printf "'%s'," $BLOCKS | sed 's/,$//'))"
