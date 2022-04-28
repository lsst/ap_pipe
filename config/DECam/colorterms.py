# This file was copied from obs_decam as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

from lsst.pipe.tasks.colorterms import Colorterm, ColortermDict

# Average color terms for the DECam filters are calculated using the Pickles stellar spectra atlas.
# The following values are provided by Song Huang (Tsinghua University; dr.guangtou@gmail.com)
# Color terms for u, Y, N419 and N964 bands are not currently available.

# The values for DECam g, r & z-bands are calculated independently and are different to the values at:
# https://www.legacysurvey.org/dr9/description/

# A Jupyter notebook to reproduce these values is available at:
# https://github.com/MerianSurvey/caterpillar/blob/main/notebook/photocal/merian_filter_color_terms.ipynb

# In obs_subaru, colorterms.py is also used in:
# - config/skyAnalysis.py
# - config/compareCoaddAnalysis.py
# - config/coaddAnalysis.py
# - config/visitAnalysis.py
# - config/fgcmBuildStarsTable.py and config/fgcmBuildStars.py
# These files are not currently available for obs_decam.

config.data = {
    "decam*": ColortermDict(data={
        'g DECam SDSS c0001 4720.0 1520.0': Colorterm(primary="g", secondary="g"),
        'r DECam SDSS c0002 6415.0 1480.0': Colorterm(primary="r", secondary="r"),
        'i DECam SDSS c0003 7835.0 1470.0': Colorterm(primary="i", secondary="i"),
        'z DECam SDSS c0004 9260.0 1520.0': Colorterm(primary="z", secondary="z"),
    }),
    "sdss*": ColortermDict(data={
        'g DECam SDSS c0001 4720.0 1520.0': Colorterm(primary="g", secondary="r", c0=-0.008015, c1=-0.089869, c2=-0.018398), # For -1.0 < g-r < 1.8
        'r DECam SDSS c0002 6415.0 1480.0': Colorterm(primary="r", secondary="i", c0=-0.0077434, c1=-0.202615, c2=0.016042), # For -1.0 < r-i < 2.2
        'i DECam SDSS c0003 7835.0 1470.0': Colorterm(primary="i", secondary="z", c0=0.00018887, c1=-0.2748281, c2=-0.029417), # For -1.0 < i-z < 1.2
        'z DECam SDSS c0004 9260.0 1520.0': Colorterm(primary="z", secondary="i", c0=-0.0059858, c1=0.1131192, c2=0.0156471), # For -1.0 < z-i < 0.5
        'N540 DECam c0014 5403.2 210.0': Colorterm(primary="g", secondary="r", c0=-0.03359776, c1=-0.57665033, c2=-0.01510509), # For -1.0 < g-r < 1.5
        'N708 DECam c0012 7080.0 400.0': Colorterm(primary="r", secondary="i", c0=-0.01428724, c1=-0.71755905, c2=0.08959316), # For -1.0 < r-i < 2.0
    }),
    "hsc*": ColortermDict(data={
        'g DECam SDSS c0001 4720.0 1520.0': Colorterm(primary="g", secondary="r", c0=0.0000509, c1=-0.0152487, c2=-0.0029937), # For -1.0 < g-r < 1.4
        'r DECam SDSS c0002 6415.0 1480.0': Colorterm(primary="r", secondary="i", c0=-0.0078995, c1=-0.1695323, c2=0.0251978), # For -1.0 < r-i < 2.2
        'i DECam SDSS c0003 7835.0 1470.0': Colorterm(primary="i", secondary="z", c0=0.0010196, c1=-0.1314031, c2=0.0054605), # For -1.0 < i-z < 1.0
        'z DECam SDSS c0004 9260.0 1520.0': Colorterm(primary="z", secondary="y", c0=-0.0013244, c1=-0.2846684, c2=-0.1229817), # For -1.0 < z-y < 0.5
        'N540 DECam c0014 5403.2 210.0': Colorterm(primary="g", secondary="r", c0=-0.03015158, c1=-0.53715834, c2=-0.00202415), # For -1.0 < g-r < 1.5
        'N708 DECam c0012 7080.0 400.0': Colorterm(primary="r", secondary="i", c0=-0.01978413, c1=-0.64368838, c2=0.09132738), # For -1.0 < r-i < 2.0
    }),
    "ps1*": ColortermDict(data={
        'g DECam SDSS c0001 4720.0 1520.0': Colorterm(primary="g", secondary="r", c0=0.006388, c1=0.045875, c2=-0.004484), # For -1.0 < g-r < 1.2
        'r DECam SDSS c0002 6415.0 1480.0': Colorterm(primary="r", secondary="i", c0=-0.006775, c1=-0.187304, c2=0.018928), # For -1.0 < r-i < 2.2
        'i DECam SDSS c0003 7835.0 1470.0': Colorterm(primary="i", secondary="z", c0=0.0012204, c1=-0.282956, c2=-0.011321), # For -1.0 < i-z < 1.4
        'z DECam SDSS c0004 9260.0 1520.0': Colorterm(primary="z", secondary="y", c0=-0.0087868, c1=-0.5204795, c2=-0.057955), # For -1.0 < z-y < 1.0
        'N540 DECam c0014 5403.2 210.0': Colorterm(primary="g", secondary="r", c0=-0.02635164, c1=-0.50968428, c2=-0.00958104), # For -1.0 < g-r < 1.5
        'N708 DECam c0012 7080.0 400.0': Colorterm(primary="r", secondary="i", c0=-0.01508987, c1=-0.69377675, c2=0.09079348), # For -1.0 < r-i < 2.0
    }),
}
