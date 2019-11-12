#!/bin/bash

# A script to set things up to run ap_pipe via slurm on some DECam data.
#
# First, run this script:
#       $ bash prep_ap_pipe.sh (will use all default values)
# e.g., $ bash prep_ap_pipe.sh -r slurm7 -R myFavRepo -f g
#
# (Note each argument is optional and is set with defaults below)
#
# This will create three new files: CONFFILE, RUNFILE, and BATCHFILE
# (called run_ap_pipe.conf, run_ap_pipe.sh, and run_ap_pipe.sl, respectively).
#
# Then, you are ready to submit a slurm job:
#       $ sbatch run_ap_pipe.sl
# e.g., $ sbatch run_ap_pipe.sl

# Print some info about how to use this script
usage()
{
    echo "usage: prep_ap_pipe [ [[-r rerun] [-o obs-camera] [-R repo] [-c calib] [-t template] [-f filter] [-p apdb] [-i]] | [-h] ]"
}

# Get directory of this shell script file
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

# Parse arguments
# First, some default values
RERUN=slurm1
OBSCAMERA=decam
REPO=/project/mrawls/hits2015
CALIB=/project/mrawls/hits2015/calib3
TEMPLATE=/project/mrawls/hits2015/templates
FILTERNAME=g
APDB=association.db
interactive=

# Next, a way to change the defaults above
while [ "$1" != "" ]; do
    case $1 in
        -r | --rerun )          shift
                                RERUN=$1
                                ;;
        -o | --obs-camera )     shift
                                OBSCAMERA=$1
                                ;;
        -R | --repo )           shift
                                REPO=$1
                                ;;
        -c | --calib )          shift
                                CALIB=$1
                                ;;
        -t | --template )       shift
                                TEMPLATE=$1
                                ;;
        -f | --filtername )     shift
                                FILTERNAME=$1
                                ;;
        -p | --apdb )           shift
                                APDB=$1
                                ;;
        -i | --interactive )    interactive=1
                                ;;
        -h | --help )           usage
                                exit
                                ;;
        * )                     usage
                                exit 1
    esac
    shift
done

if [ "$interactive" = "1" ]; then
    response=
    echo -n "Name of rerun [$RERUN] > "
    read response
    if [ -n "$response" ]; then
        RERUN=$response
    fi
    echo -n "Name of obs-camera [$OBSCAMERA] > "
    read response
    if [ -n "$response" ]; then
        OBSCAMERA=$response
    fi
    echo -n "Path to main input repo [$REPO] > "
    read response
    if [ -n "$response" ]; then
        REPO=$response
    fi
    echo -n "Path to calib repo [$CALIB] > "
    read response
    if [ -n "$response" ]; then
        CALIB=$response
    fi
    echo -n "Path to templates [$TEMPLATE] > "
    read response
    if [ -n "$response" ]; then
        TEMPLATE=$response
    fi
    echo -n "Filter to process [$FILTERNAME] > "
    read response
    if [ -n "$response" ]; then
        FILTERNAME=$response
    fi
    echo -n "Location for Prompt Products Database [$APDB] > "
    read response
    if [ -n "$response" ]; then
        APDB=$response
    fi
fi

# Print what is happening for confirmation
echo "The command to be slurmified is:"
echo "ap_pipe.py ${REPO} --calib ${CALIB} --template ${TEMPLATE} --rerun ${RERUN} -c associator.level1_db.db_name=${APDB} -c differencer.getTemplate.warpType='psfMatched'"
echo "For all CCDs and visits in the ${FILTERNAME} filter using the obs-camera ${OBSCAMERA}."

# Create a directory to write slurm outfiles to if it doesn't exist yet
mkdir -p slurm


# Create CONFFILE
CONFFILE=run_ap_pipe.conf
rm -f ${CONFFILE}

# Loop over CCDs (users may add additional cameras on an as-needed basis below)
if [ $OBSCAMERA == "decam" ]; then
    CCDRANGE=( 1 {3..60} 62 )
    CCDKEYWORD=ccdnum
elif [ $OBSCAMERA == "hsc" ]; then
    CCDRANGE=( {0..8} {10..103} )
    CCDKEYWORD=ccd
else
    echo "Unrecognized obs-camera $OBSCAMERA"
    exit 1
fi

for ccdidx in "${!CCDRANGE[@]}";
do
    idString="${CCDKEYWORD}=${CCDRANGE[ccdidx]} filter=${FILTERNAME}"
    echo "${ccdidx} ${DIR}/run_ap_pipe.sh ${idString}">>${CONFFILE}
done

chmod +x ${CONFFILE}


# Create RUNFILE
RUNFILE=run_ap_pipe.sh
rm -f ${RUNFILE}

echo "#!/bin/bash">>${RUNFILE}
echo "">>${RUNFILE}
echo "# This script is created by prep_ap_pipe.sh">>${RUNFILE}
echo "# It is called by run_ap_pipe.conf, which is called by run_ap_pipe.sl">>${RUNFILE}
echo "">>${RUNFILE}
echo "# Set up the stack, which now includes the needed ap_ packages">>${RUNFILE}
echo "source /software/lsstsw/stack/loadLSST.bash">>${RUNFILE}
echo "setup lsst_distrib">>${RUNFILE}
echo "">>${RUNFILE}
echo "ap_pipe.py ${REPO} --calib ${CALIB} --template ${TEMPLATE} --rerun ${RERUN} -c associator.level1_db.db_name=${APDB} -c differencer.getTemplate.warpType='psfMatched' --id \$*">>${RUNFILE}

chmod +x ${RUNFILE}


# Create BATCHFILE
BATCHFILE=run_ap_pipe.sl
rm -f ${BATCHFILE}

# Use the number of CCDs as the number of tasks
# Divide by 24 (# of cores on lsst-dev) and add 1 to allocate enough processors
NTASKS=${#CCDRANGE[@]}
let "NNODES=${NTASKS} / 24 + 1"

echo "#!/bin/bash -l">>${BATCHFILE}
echo "">>${BATCHFILE}
echo "#SBATCH -p normal">>${BATCHFILE}
echo "#SBATCH -N ${NNODES}">>${BATCHFILE}
echo "#SBATCH -n ${NTASKS}">>${BATCHFILE}
echo "#SBATCH -t 12:00:00">>${BATCHFILE}
echo "#SBATCH -J ap_pipe">>${BATCHFILE}
echo "">>${BATCHFILE}
echo "# To submit a slurm job:">>${BATCHFILE}
echo "#       \$ sbatch run_ap_pipe.sl">>${BATCHFILE}
echo "">>${BATCHFILE}
echo "VISITS=\`sqlite3 ${REPO}/registry.sqlite3 \"select distinct visit from raw where filter = '${FILTERNAME}';\"\`">>${BATCHFILE}
echo "">>${BATCHFILE}
echo "for VISIT in \${VISITS};">>${BATCHFILE}
echo "do">>${BATCHFILE}
echo "    echo \"Processing \${VISIT}\"">>${BATCHFILE}
echo "    srun --output slurm/ap_pipe%j-%2t.out --multi-prog ${CONFFILE} visit=\${VISIT}">>${BATCHFILE}
echo "done">>${BATCHFILE}
echo "wait">>${BATCHFILE}
