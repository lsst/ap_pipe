# This file was copied from obs_subaru as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

from lsst.pipe.tasks.colorterms import Colorterm, ColortermDict

config.data = {
    "hsc*": ColortermDict(data={
        'HSC-G': Colorterm(primary="g", secondary="g"),
        'HSC-R': Colorterm(primary="r", secondary="r"),
        'HSC-I': Colorterm(primary="i", secondary="i"),
        'HSC-Z': Colorterm(primary="z", secondary="z"),
        'HSC-Y': Colorterm(primary="y", secondary="y"),
    }),
    "sdss*": ColortermDict(data={
        'HSC-G': Colorterm(primary="g", secondary="r", c0=-0.009777, c1=-0.077235, c2=-0.013121),
        'HSC-R': Colorterm(primary="r", secondary="i", c0=-0.000711, c1=-0.006847, c2=-0.035110),
        'HSC-R2': Colorterm(primary="r", secondary="i", c0=-0.000632, c1=-0.011237, c2=-0.038169),
        'HSC-I': Colorterm(primary="i", secondary="z", c0=0.000357, c1=-0.153290, c2=-0.009277),
        'HSC-I2': Colorterm(primary="i", secondary="z", c0=0.001278, c1=-0.213569, c2=-0.012523),
        'HSC-Z': Colorterm(primary="z", secondary="i", c0=-0.005761, c1=0.001317, c2=-0.035334),
        'HSC-Y': Colorterm(primary="z", secondary="i", c0=0.003386, c1=0.428877, c2=0.076738),
        'IB0945': Colorterm(primary="z", secondary="i", c0=0.008117, c1=0.234991, c2=-0.042255),
        'NB0387': Colorterm(primary="u", secondary="g", c0=-0.709229, c1=0.310719, c2=-0.044107),
        'NB0400': Colorterm(primary="u", secondary="g", c0=-0.396264, c1=-0.395133, c2=0.038688),
        'NB0468': Colorterm(primary="g", secondary="r", c0=-0.059159, c1=-0.030881, c2=0.015356),
        'NB0515': Colorterm(primary="g", secondary="r", c0=-0.032510, c1=-0.354440, c2=0.100832),
        'NB0527': Colorterm(primary="g", secondary="r", c0=-0.029400, c1=-0.453037, c2=0.020922),
        'NB0656': Colorterm(primary="r", secondary="i", c0=0.037014, c1=-0.538947, c2=0.052489),
        'NB0718': Colorterm(primary="r", secondary="i", c0=-0.014742, c1=-0.787571, c2=0.237867),
        'NB0816': Colorterm(primary="i", secondary="z", c0=0.012676, c1=-0.660317, c2=0.055566),
        'NB0921': Colorterm(primary="z", secondary="i", c0=0.004619, c1=0.093019, c2=-0.126377),
        'NB0926': Colorterm(primary="z", secondary="i", c0=0.009369, c1=0.130261, c2=-0.119282),
        'NB0973': Colorterm(primary="z", secondary="i", c0=-0.005805, c1=0.220412, c2=-0.249072),
        'NB01010': Colorterm(primary="z", secondary="i", c0=0.015296, c1=0.794152, c2=0.465309),
    }),
    "ps1*": ColortermDict(data={
        'HSC-G': Colorterm(primary="g", secondary="r", c0=0.005728, c1=0.061749, c2=-0.001125),
        'HSC-R': Colorterm(primary="r", secondary="i", c0=-0.000144, c1=0.001369, c2=-0.008380),
        'HSC-R2': Colorterm(primary="r", secondary="i", c0=-0.000032, c1=-0.002866, c2=-0.012638),
        'HSC-I': Colorterm(primary="i", secondary="z", c0=0.000643, c1=-0.130078, c2=-0.006855),
        'HSC-I2': Colorterm(primary="i", secondary="z", c0=0.001625, c1=-0.200406, c2=-0.013666),
        'HSC-Z': Colorterm(primary="z", secondary="y", c0=-0.005362, c1=-0.221551, c2=-0.308279),
        'HSC-Y': Colorterm(primary="y", secondary="z", c0=-0.002055, c1=0.209680, c2=0.227296),
        'IB0945': Colorterm(primary="y", secondary="z", c0=0.005275, c1=-0.194285, c2=-0.125424),
        'NB0387': Colorterm(primary="g", secondary="r", c0=0.427879, c1=1.869068, c2=0.540580),
        'NB0400': Colorterm(primary="g", secondary="r", c0=0.176542, c1=1.127055, c2=0.505502),
        'NB0468': Colorterm(primary="g", secondary="r", c0=-0.042240, c1=0.121756, c2=0.027599),
        'NB0515': Colorterm(primary="g", secondary="r", c0=-0.021913, c1=-0.253159, c2=0.151553),
        'NB0527': Colorterm(primary="g", secondary="r", c0=-0.020641, c1=-0.366167, c2=0.038497),
        'NB0656': Colorterm(primary="r", secondary="i", c0=0.035655, c1=-0.512046, c2=0.042796),
        'NB0718': Colorterm(primary="i", secondary="r", c0=-0.016294, c1=-0.233139, c2=0.252505),
        'NB0816': Colorterm(primary="i", secondary="z", c0=0.013806, c1=-0.717681, c2=0.049289),
        'NB0921': Colorterm(primary="z", secondary="y", c0=0.002039, c1=-0.477412, c2=-0.492151),
        'NB0926': Colorterm(primary="z", secondary="y", c0=0.005230, c1=-0.574448, c2=-0.330899),
        'NB0973': Colorterm(primary="y", secondary="z", c0=-0.007775, c1=-0.050972, c2=-0.197278),
        'NB01010': Colorterm(primary="y", secondary="z", c0=0.003607, c1=0.865366, c2=1.271817),
    }),
}
