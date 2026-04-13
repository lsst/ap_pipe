# This file is part of ap_pipe.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
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
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import logging
from argparse import ArgumentParser, RawTextHelpFormatter

from astropy.table import vstack

from lsst.daf.butler import Butler
from lsst.source.injection import utils


def build_argparser():
    parser = ArgumentParser(
        description="""Shard a source injection catalog already ingested
        into the butler repo, but with the htm7 and band indexing for the
        source injection package.

        It reads the catalogs in the specified repo butler and collection using
        the provided dataIds or query parameters.
        """,
        formatter_class=RawTextHelpFormatter,
        epilog="More information is available at https://pipelines.lsst.io.",
        add_help=True,
    )
    # Butler options.
    parser.add_argument(
        "-b",
        "--butler-config",
        type=str,
        help="Location of the butler/registry config file.",
        metavar="TEXT",
    )
    parser.add_argument(
        "-i",
        "--input-collections",
        type=str,
        help="Name of the input collections to read the unsharded injection catalog from.",
        required=True,
        metavar="COLL",
    )
    parser.add_argument(
        "-o",
        "--output-collection",
        type=str,
        help="Name of the output collection to ingest the sharded injection catalog into.",
        required=True,
        metavar="COLL",
    )
    parser.add_argument(
        "-t",
        "--dataset-type-name",
        type=str,
        help="Input dataset type name for the unsharded source injection catalog.",
        metavar="TEXT",
        default="injection_catalog",
    )
    parser.add_argument(
        "-d",
        "--dataquery",
        type=str,
        help="Data query to select the input unsharded injection catalog. ",
        required=False,
        metavar="TEXT",
    )
    return parser


def main():
    """Use this as the main entry point when calling from the command line."""
    # Set up logging.
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    args = build_argparser().parse_args()
    # Instantiate the butler.
    butler = Butler(args.butler_config, writeable=True)
    # Read in the unsharded injection catalog selected by an optional Butler
    # where-expression passed through -d/--dataquery.
    input_collections = [c.strip() for c in args.input_collections.split(",")]
    query_kwargs = dict(datasetType=args.dataset_type_name, collections=input_collections)
    if args.dataquery:
        query_kwargs["where"] = args.dataquery
    datarefs = list(butler.registry.queryDatasets(**query_kwargs))
    if not datarefs:
        logger.warning("No datasets found for dataset type '%s' with query: %s",
                       args.dataset_type_name, args.dataquery)
        return

    catalogs_per_band = {}
    for dataref in datarefs:
        band = dataref.dataId["band"]
        catalogs_per_band.setdefault(band, []).append(butler.get(dataref))

    # stack the tables and split in bands
    for band, catalogs in catalogs_per_band.items():
        # use source injection utils to ingest the sharded injection catalog.
        catalog = vstack(catalogs, metadata_conflicts='silent') if len(catalogs) > 1 else catalogs[0]
        utils.ingest_injection_catalog(
            writeable_butler=butler,
            table=catalog,
            band=band,
            output_collection=args.output_collection,
            log_level=logging.DEBUG,
        )


if __name__ == "__main__":
    main()
