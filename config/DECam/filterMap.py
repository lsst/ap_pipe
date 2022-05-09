# This file was copied from obs_decam as part of DM-34699. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

# Mapping of camera filter name: reference catalog filter name; each reference filter must exist in the refcat.
# Note that this does not perform any bandpass corrections: it is just a lookup.
# Note u-band photometry may not be useful without a color term.
config.filterMap = {'u': 'g',
                    'Y': 'y',
                    'N419': 'g',
                    'N540': 'g',
                    'N708': 'i',
                    'N964': 'z',
                    'N419': 'g',
                    'N540': 'g',
                    'N708': 'i',
                    'N964': 'z',
                    }
