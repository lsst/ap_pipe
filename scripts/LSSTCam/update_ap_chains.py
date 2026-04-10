#!/usr/bin/env python3

import argparse
import datetime

from lsst.daf.butler import Butler, CollectionType


def get_last_night():
    """Return last night's date in YYYYMMDD format UTC."""
    today = datetime.datetime.utcnow()
    last_night = today - datetime.timedelta(days=1)
    return last_night.strftime("%Y%m%d")


def main(args):
    day_obs = args.day_obs
    butler = Butler(args.repo, writeable=True)

    prompt_chain = f"LSSTCam/runs/prompt-{day_obs}"
    daytime_chain = f"LSSTCam/runs/daytimeAP-{day_obs}"

    daytime_prefix = f"LSSTCam/runs/daytimeAP/{day_obs}"
    collections = butler.collections.query(
        daytime_prefix, flatten_chains=True, collection_types=CollectionType.RUN
    )
    runs = [col for col in collections if col.startswith(daytime_prefix)]

    if not runs:
        print(
            f"No runs found matching prefix '{daytime_prefix}'"
        )
        return

    print(f"Prepending runs to chain {prompt_chain}:")
    for run in runs:
        print(f"  {run}")
    butler.collections.prepend_chain(prompt_chain, runs)
    butler.collections.register(daytime_chain, type=CollectionType.CHAINED)
    butler.collections.redefine_chain(daytime_chain, runs)
    print(f"Chain {daytime_chain} is defined.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepend Daytime AP runs to prompt chain and create daytimeAP chain."
    )
    parser.add_argument(
        "--day_obs",
        "-d",
        default=get_last_night(),
        help="Day observation date in YYYYMMDD (default: last night UTC)",
    )
    parser.add_argument(
        "--repo", "-r", default="embargo", help="Repo location (default: 'embargo')"
    )
    args = parser.parse_args()
    main(args)
