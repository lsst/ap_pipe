from __future__ import print_function
from lsst.obs.decam import ingest
from lsst.obs.decam import ingestCalibs
from lsst.obs.decam.ingest import DecamParseTask
from lsst.pipe.tasks.ingest import IngestConfig
from lsst.pipe.tasks.ingestCalibs import IngestCalibsConfig, IngestCalibsTask
from lsst.pipe.tasks.ingestCalibs import IngestCalibsArgumentParser
from lsst.pipe.tasks.processCcd import ProcessCcdTask, ProcessCcdConfig
from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
from lsst.utils import getPackageDir
from lsst.ip.diffim.getTemplate import GetCalexpAsTemplateTask
from lsst.pipe.tasks.imageDifference import ImageDifferenceConfig, ImageDifferenceTask
from glob import glob
import sqlite3
import os
import argparse
import textwrap
import tarfile
'''
Process raw decam images with MasterCals from ingestion --> difference imaging

TODO: Rename script and GitHub repo to ap_pipe (not decam_hits or decam_process).
      This will be done in DM-11324.

USAGE:
$ python decam_process.py -d dataset_root -o output_location -i "visit=12345, ccd=5"

NOTE: -i flag is not implemented yet. For now, set the visit and ccd in main().

TODO: Update DMTN-039 to reflect the new user interface.
      I'm postponing this until DM-11422 and/or DM-11390 are complete.
'''


def main():
    '''
    Parse command-line args and run the pipeline. NOT used by ap_verify.

    This main function is solely for the purpose of running ap_pipe alone,
    from the command line, on a dataset intended for ap_verify. It is useful
    for testing or standalone image processing independently from verification.
    '''
    # Parse command line arguments with argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=textwrap.dedent('''
    Process raw decam images with MasterCals from ingestion --> difference imaging

    USAGE:
    $ python decam_process.py -d dataset_root -o output_location -i "visit=12345, ccd=5"
                                     '''))
    parser.add_argument('-d', '--dataset',
                        help="Location on disk of dataset_root, which contains subdirectories of raw data, calibs, etc.")
    parser.add_argument('-o', '--output',
                        help="Location on disk where output repos will live.")
    # TODO: implement this argument
    # parser.add_argument('-i', '--id',
    #                    help="String containing visit and ccd information. Typically set as 'visit=12345, ccd=5'.")
    args = parser.parse_args()

    if not os.path.isdir(args.output):
        os.mkdir(args.output)
    repo = os.path.join(args.output, 'ingested')
    calibrepo = os.path.join(args.output, 'calibingested')
    processedrepo = os.path.join(args.output, 'processed')
    diffimrepo = os.path.join(args.output, 'diffim')
    types = ('*.fits', '*.fz')
    datafiles = []
    allcalibdatafiles = []
    for files in types:
        datafiles.extend(glob(os.path.join(args.dataset, 'raw', files)))
        allcalibdatafiles.extend(glob(os.path.join(args.dataset, 'calib', files)))

    # Ignore wtmaps and illumcors
    calibdatafiles = []
    for file in allcalibdatafiles:
        if ('fcw' not in file) and ('zcw' not in file) and ('ici' not in file):
            calibdatafiles.append(file)

    # Retrieve defect filenames from tarball
    # TODO: search for a single filename beginning with `defects` and ending in `.tar.gz`
    #       rather than hardcoding the name of the tarball.
    defectloc = os.path.join(args.dataset, 'calib')
    defecttarfile = glob(os.path.join(defectloc, 'defects_2014-12-05.tar.gz'))[0]
    defectfiles = tarfile.open(defecttarfile).getnames()
    defectfiles = [os.path.join(defectloc, file) for file in defectfiles]

    # Provide location of ref_cats directory containing gaia and pan-starrs tarballs
    ref_cats = os.path.join(args.dataset, 'ref_cats')

    # TEMPORARY HARDWIRED THINGS ARE TEMPORARY
    # TODO: - use a coadd as a template instead of a visit (DM-11422)
    #       - implement the --id argument and pull visit and ccdnum from there (default = all CCDs)
    visit = '410985'  # one arbitrary g-band visit in Blind15A40
    templatevisit = '410929'  # another arbitrary g-band visit in Blind15A40
    ccdnum = '25'  # arbitrary single CCD for testing
    sciencevisit = visit  # for doDiffIm, for now

    # Run all the tasks in order
    doIngest(repo, ref_cats, datafiles)
    doIngestCalibs(repo, calibrepo, calibdatafiles, defectfiles)
    doProcessCcd(repo, calibrepo, processedrepo, visit, ccdnum)
    doProcessCcd(repo, calibrepo, processedrepo, templatevisit, ccdnum, ref_cats)  # temporary
    doDiffIm(processedrepo, sciencevisit, ccdnum, templatevisit, diffimrepo)
    print('Prototype AP Pipeline run complete.')

    return


def doIngest(repo, ref_cats, datafiles):
    '''
    Ingest raw DECam images into a repository with a corresponding registry

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    ref_cats: `str`
        A directory containing two .tar.gz files with LSST-formatted astrometric
        and photometric reference catalog information, one from Gaia and one
        from Pan-STARRS. These files must be called `gaia_HiTS_2015.tar.gz`
        and `ps1_HiTS_2015.tar.gz`, respectively.
    datafiles: `list`
        A list of the filenames of each raw image file.

    BASH EQUIVALENT:
    $ ingestImagesDecam.py repo --filetype raw --mode link datafiles
    ** If run from bash, ref_cats must also be manually copied or symlinked to repo

    RESULT:
    repo populated with *links* to datafiles, organized by date
    sqlite3 database registry of ingested images also created in repo

    NOTE:
    This functions ingests *all* the images, not just the ones for the
    specified visits and/or filters. We may want to revisit this in the future.
    '''
    if os.path.exists(os.path.join(repo, 'registry.sqlite3')):
        print('Raw images were previously ingested, skipping...')
    else:
        if not os.path.isdir(repo):
            os.mkdir(repo)
        # make a text file that handles the mapper, per the obs_decam github README
        with open(os.path.join(repo, '_mapper'), 'w') as f:
            print('lsst.obs.decam.DecamMapper', file=f)
        print('Ingesting raw images...')
        # save arguments you'd put on the command line after 'ingestImagesDecam.py'
        # (extend the list with all the filenames as the last set of arguments)
        args = [repo, '--filetype', 'raw', '--mode', 'link']
        args.extend(datafiles)
        # set up the decam ingest task so it can take arguments
        # ('name' says which file in obs_decam/config to use)
        argumentParser = ingest.DecamIngestArgumentParser(name='ingest')
        # create an instance of ingest configuration
        # the retarget command is from line 2 of obs_decam/config/ingest.py
        config = IngestConfig()
        config.parse.retarget(DecamParseTask)
        # create an instance of the decam ingest task
        ingestTask = ingest.DecamIngestTask(config=config)
        # feed everything to the argument parser
        parsedCmd = argumentParser.parse_args(config=config, args=args)
        # finally, run the ingestTask
        ingestTask.run(parsedCmd)
        # Copy ref_cats files to repo (needed for doProcessCcd)
        gaiatarball = os.path.join(ref_cats, 'gaia_HiTS_2015.tar.gz')
        panstarrstarball = os.path.join(ref_cats, 'ps1_HiTS_2015.tar.gz')
        tarfile.open(gaiatarball, 'r').extractall(os.path.join(repo, 'ref_cats', 'gaia'))
        tarfile.open(panstarrstarball, 'r').extractall(os.path.join(repo, 'ref_cats', 'pan-starrs'))
        print('Images are now ingested in {0}'.format(repo))
    return


def doIngestCalibs(repo, calibrepo, calibdatafiles, defectfiles):
    '''
    Ingest DECam MasterCal biases and flats into a calibration repository with a corresponding registry.
    Also ingest DECam defects into the calib registry.

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    calibrepo: `str`
        The output repository location on disk where ingested calibration images live.
    calibdatafiles: `list`
        A list of the filenames of each flat and bias image file.
    defectfiles: `list`
            A list of the filenames of each defect image file.
            The first element in this list must be the name of a .tar.gz file
            which contains all the compressed defect images.

    BASH EQUIVALENT:
    $ ingestCalibs.py repo --calib calibrepo --mode=link --validity 999 calibdatafiles
    $ cd calibrepo
    $ ingestCalibs.py ../../repo --calib . --mode=skip --calibType defect --validity 999 defectfiles
    $ cd ..

    RESULT:
    calibrepo populated with *links* to calibdatafiles,
    organized by date (bias and flat images only)
    sqlite3 database registry of ingested calibration products (bias, flat,
    and defect images) created in calibrepo

    NOTE:
    calib ingestion ingests *all* the calibs, not just the ones needed
    for the specified visits. We may want to revisit this in the future.
    '''

    def flatBiasIngest(repo, calibrepo, calibdatafiles):
        '''
        Ingest DECam flats and biases
    
        Parameters
        ----------
        repo: `str`
            The output repository location on disk where ingested raw images live.
        calibrepo: `str`
            The output repository location on disk where ingested calibration images live.
        calibdatafiles: `list`
            A list of the filenames of each flat and bias image file.
    
        '''
        print('Ingesting flats and biases...')
        args = [repo, '--calib', calibrepo, '--mode', 'link', '--validity', '999']
        args.extend(calibdatafiles)
        argumentParser = IngestCalibsArgumentParser(name='ingestCalibs')
        config = IngestCalibsConfig()
        config.parse.retarget(ingestCalibs.DecamCalibsParseTask)
        ingestTask = IngestCalibsTask(config=config, name='ingestCalibs')
        parsedCmd = argumentParser.parse_args(config=config, args=args)
        try:
            ingestTask.run(parsedCmd)
        except sqlite3.IntegrityError as detail:
            print('sqlite3.IntegrityError: ', detail)
            print('(sqlite3 doesn\'t think all the calibration files are unique)')
        else:
            print('Success!')
            print('Calibrations corresponding to {0} are now ingested in {1}'.format(repo, calibrepo))
        return

    def defectIngest(repo, calibrepo, defectfiles):
        '''
        Ingest DECam defect images
    
        Parameters
        ----------
        repo: `str`
            The output repository location on disk where ingested raw images live.
        calibrepo: `str`
            The output repository location on disk where ingested calibration images live.
        defectfiles: `list`
            A list of the filenames of each defect image file.
            The first element in this list must be the name of a .tar.gz file
            which contains all the compressed defect images.

        This function assumes very particular things about defect ingestion:
        - They must live in a .tar.gz file in the same location on disk as the other calibs
        - They will be ingested using ingestCalibs.py run from the calibrepo directory
        - They will be manually uncompressed and saved in calibrepo/defects/<tarballname>/.
        - They will be added to the calib registry, but not linked like the flats and biases
        '''
        os.chdir(calibrepo)
        try:
            os.mkdir('defects')
        except OSError:
            # defects directory already exists
            print('Defects were previously ingested, skipping...')
        else:
            print('Ingesting defects...')
            defectargs = ['../../' + repo, '--calib', '.', '--calibType', 'defect',
                          '--mode', 'skip', '--validity', '999']
            defecttarball = defectfiles[0] + '.tar.gz'
            tarfile.open(os.path.join('../../', defecttarball), 'r').extractall('defects')
            defectfiles = glob(os.path.join('defects', os.path.basename(defectfiles[0]), '*.fits'))
            defectargs.extend(defectfiles)
            defectargumentParser = IngestCalibsArgumentParser(name='ingestCalibs')
            defectconfig = IngestCalibsConfig()
            defectconfig.parse.retarget(ingestCalibs.DecamCalibsParseTask)
            defectIngestTask = IngestCalibsTask(config=defectconfig, name='ingestCalibs')
            defectParsedCmd = defectargumentParser.parse_args(config=defectconfig, args=defectargs)
            defectIngestTask.run(defectParsedCmd)
        finally:
            os.chdir('../..')
        return

    if not os.path.isdir(calibrepo):
        os.mkdir(calibrepo)
        flatBiasIngest(repo, calibrepo, calibdatafiles)
        defectIngest(repo, calibrepo, defectfiles)
    elif os.path.exists(os.path.join(calibrepo, 'cpBIAS')):
        print('Flats and biases were previously ingested, skipping...')
        defectIngest(repo, calibrepo, defectfiles)
    else:
        flatBiasIngest(repo, calibrepo, calibdatafiles)
        defectIngest(repo, calibrepo, defectfiles)

    return


def doProcessCcd(repo, calibrepo, processedrepo, visit, ccdnum):
    '''
    Perform ISR with ingested images and calibrations via processCcd

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    calibrepo: `str`
        The output repository location on disk where ingested calibration images live.
    processedrepo: `str`
        The output repository location on disk where processed raw images live.
    visit: `str`
        One or more DECam visit numbers, e.g., `54321`. Multiple visits may be
        indicated with standard Butler parsing, e.g., `54321^12345`.
    ccdnum: `str`
        One or more DECam CCDs (`1` through `62` are allowed). Setting
        ccdnum='1..62' will process all of the CCDs.

    BASH EQUIVALENT:
    $ processCcd.py repo --id visit=visit ccdnum=ccdnum
            --output processedrepo --calib calibrepo
            -C $OBS_DECAM_DIR/config/processCcdCpIsr.py
            -C processccd_config.py
            --config calibrate.doAstrometry=True calibrate.doPhotoCal=True
    ** to run from bash, 'processccd_config.py' must exist and contain
       all of the refObjLoader information in the code below. repo must also
       already contain the ref_cats (this is done during doIngest).

    RESULT:
    processedrepo/visit populated with subdirectories containing the
    usual post-ISR data (bkgd, calexp, icExp, icSrc, postISR).
    '''
    if os.path.isdir(os.path.join(processedrepo, '0'+visit)):
        print('ProcessCcd has already been run for visit {0}, skipping...'.format(visit))
    else:
        if not os.path.isdir(processedrepo):
            os.mkdir(processedrepo)
        print('Running ProcessCcd...')
        OBS_DECAM_DIR = getPackageDir('obs_decam')
        config = ProcessCcdConfig()
        # Use gaia for astrometry (phot_g_mean_mag is only available DR1 filter)
        # Use pan-starrs for photometry (grizy filters)
        for refObjLoader in (config.calibrate.astromRefObjLoader,
                             config.calibrate.photoRefObjLoader,
                             config.charImage.refObjLoader,):
            refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
        config.calibrate.astromRefObjLoader.ref_dataset_name = 'gaia'
        config.calibrate.astromRefObjLoader.filterMap = {'u': 'phot_g_mean_mag',
                                                         'g': 'phot_g_mean_mag',
                                                         'r': 'phot_g_mean_mag',
                                                         'i': 'phot_g_mean_mag',
                                                         'z': 'phot_g_mean_mag',
                                                         'y': 'phot_g_mean_mag',
                                                         'VR': 'phot_g_mean_mag'}
        config.calibrate.photoRefObjLoader.ref_dataset_name = 'pan-starrs'
        config.calibrate.photoRefObjLoader.filterMap = {'u': 'g',
                                                        'g': 'g',
                                                        'r': 'r',
                                                        'i': 'i',
                                                        'z': 'z',
                                                        'y': 'y',
                                                        'VR': 'g'}
        args = [repo, '--id', 'visit=' + visit, 'ccdnum=' + ccdnum,
                '--output', processedrepo,
                '--calib', calibrepo,
                '-C', OBS_DECAM_DIR + '/config/processCcdCpIsr.py',
                '--config', 'calibrate.doAstrometry=True',
                'calibrate.doPhotoCal=True']
        ProcessCcdTask.parseAndRun(args=args, config=config)
    return


def doDiffIm(processedrepo, sciencevisit, ccdnum, templatevisit, diffimrepo):
    '''
    Do difference imaging with a visit as a template and one or more as science
    
    Parameters
    ----------
    processedrepo: `str`
        The output repository location on disk where processed raw images live.
    sciencevisit: `str`
        One or more DECam visit numbers, e.g., `54321`. Multiple visits may be
        indicated with standard Butler parsing, e.g., `54321^12345`.
    ccdnum: `str`
        One or more DECam CCDs (`1` through `62` are allowed). Setting
        ccdnum='1..62' will process all of the CCDs.
    templatevisit: `str`
        The single DECam visit number which will be used as a template for
        difference imaging.
    diffimrepo: `str`
        The output repository location on disk where difference images live.

    BASH EQUIVALENT:
    $ imageDifference.py processedrepo --id visit=sciencevisit ccdnum=ccdnum
            --templateId visit=templatevisit --output diffimrepo
            -C diffim_config.py
    ** to run from bash, 'diffim_config.py' must exist and contain, e.g.,
        from lsst.ip.diffim.getTemplate import GetCalexpAsTemplateTask
        config.getTemplate.retarget(GetCalexpAsTemplateTask)
        config.detection.thresholdValue = 5.0
        config.doDecorrelation = True

    TODO: use coadds as templates by default, not another visit (DM-11422).
    
    RESULT:
    diffimrepo/deepDiff/v+sciencevisit populated with difference images
    and catalogs of detected sources (diaSrc, diffexp, and metadata files)
    '''
    if os.path.exists(os.path.join(diffimrepo, 'deepDiff', 'v' + sciencevisit)):
        print('DiffIm has already been run for visit {0}, skipping...'.format(sciencevisit))
    else:
        if not os.path.isdir(diffimrepo):
            os.mkdir(diffimrepo)
        print('Running ImageDifference...')
        config = ImageDifferenceConfig()
        config.getTemplate.retarget(GetCalexpAsTemplateTask)
        config.detection.thresholdValue = 5.0
        config.doDecorrelation = True
        args = [processedrepo, '--id', 'visit=' + sciencevisit, 'ccdnum=' + ccdnum,
                '--templateId', 'visit=' + templatevisit, '--output', diffimrepo]
        ImageDifferenceTask.parseAndRun(args=args, config=config)
    return


if __name__ == '__main__':
    main()
