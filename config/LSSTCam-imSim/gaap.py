# This file is part of ap_pipe.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.

# This file was copied from obs_lsst as part of DM-31063. Feel free to modify
# this file to better reflect the needs of AP; however, when it comes time to
# permanently remove the obs_* configs, we should check that none of the
# changes made there since April 12, 2022 would be useful here.

import lsst.meas.extensions.gaap  # noqa: Load GAaP algorithm
config.plugins.names.add("ext_gaap_GaapFlux")
config.plugins["ext_gaap_GaapFlux"].sigmas = [0.5, 0.7, 1.0, 1.5, 2.5, 3.0]
# Enable PSF photometry after PSF-Gaussianization in the `ext_gaap_GaapFlux` plugin
config.plugins["ext_gaap_GaapFlux"].doPsfPhotometry = True
