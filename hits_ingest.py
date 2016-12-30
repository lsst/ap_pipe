from __future__ import print_function
import numpy as np
import matplotlib.pyplot as plt
#from astropy.io import fits
from lsst.utils import getPackageDir
from lsst.obs.decam import ingest, ingestCalibs
from lsst.pipe.tasks.ingest import IngestConfig
from glob import glob
import sys
from lsst.obs.decam.ingest import DecamParseTask
'''
Little script to ingest some raw decam images

You have to specify two things:
1. repodir, an empty directory where you want the nicely organized and ingested images to live
2. datadir, a directory where some '*.fits.fz' images currently live

Usage: $ python hits_ingest.py 'path/to/datadir/'

Result: repodir will be populated with **links** to the files in datadir, organized by date

The command line equivalent given the variables below is:
$ ingestImagesDecam.py repodir datafiles --filetype raw --mode link
'''

# edit directory names as desired below
repodir = '../ingested/' # on lsst-dev
#repodir = 'ingested/' # on laptop
datadir = sys.argv[1] # or '/lsst7/mrawls/HiTS/Blind15A_38/' on lsst-dev or 'data/' on laptop
datafiles = glob(datadir + '*.fits.fz')

# first, need to make a text file that handles the mapper, per the obs_decam github README
f = open(repodir+'_mapper', 'w')
print('lsst.obs.decam.DecamMapper', file=f)
f.close()

# next, create the arguments you'd usually put on the command line after 'ingestImagesDecam.py'
# (extend the list with all the filenames as the last set of arguments)
args = [repodir, '--filetype', 'raw', '--mode', 'link']
args.extend(datafiles)

# set up the decam ingest task so it can take arguments ('name' says which file in obs_decam/config to use)
argumentParser = ingest.DecamIngestArgumentParser(name='ingest')

# create an instance of ingest configuration
config = IngestConfig()
config.parse.retarget(DecamParseTask) # this is from line 2 of obs_decam/config/ingest.py 

# create an instance of the decam ingest task
ingestTask = ingest.DecamIngestTask(config=config)

# feed everything to the argument parser
parsedCmd = argumentParser.parse_args(config=config, args=args)

# finally, run the ingestTask
ingestTask.run(parsedCmd)

