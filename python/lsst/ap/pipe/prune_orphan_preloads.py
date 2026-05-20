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

"""Prune orphan preload quanta from an Alert Production QuantumGraph.

The Alert Production pipeline generates a ``loadDiaCatalogs`` quantum
(keyed by ``group``) for every visit in the data query, regardless of
whether that visit's image-differencing chain produces an
``associateApdb`` quantum downstream. In batch contexts where some
visits lack template coverage, the preload quanta for those visits are
orphans: their outputs are never consumed by any associate quantum.

Their presence breaks BPS visit ordering, because the ordering walk
cannot map their ``group``-keyed data IDs to ``visit`` without a
reachable ``associateApdb`` quantum. Removing the orphan preload
quanta (along with the downstream metric quanta they feed) before BPS
sees the graph sidesteps this entirely.
"""

import argparse
import logging

import networkx as nx

from lsst.pipe.base import QuantumGraph

__all__ = ["prune_orphan_preloads", "main"]

_LOG = logging.getLogger(__spec__.name if __spec__ is not None else __name__)

PRELOAD_LABEL = "loadDiaCatalogs"
ANCHOR_LABEL = "associateApdb"


def _find_task_def(qg, label):
    """Return the TaskDef in ``qg`` whose label matches, or None."""
    for task_def in qg.iterTaskGraph():
        if task_def.label == label:
            return task_def
    return None


def prune_orphan_preloads(qg, preload_label=PRELOAD_LABEL, anchor_label=ANCHOR_LABEL):
    """Return a new QG with orphan preload quanta and their downstream chain removed.

    A preload quantum is considered an orphan if no quantum with
    ``anchor_label`` is reachable along the directed edges of the
    quantum graph from it. Orphan preloads and every descendant quantum
    reachable from them are dropped.

    Parameters
    ----------
    qg : `lsst.pipe.base.QuantumGraph`
        The graph to prune. Not modified.
    preload_label : `str`, optional
        Task label of the preload task whose orphan quanta to remove.
    anchor_label : `str`, optional
        Task label that must appear downstream of a preload quantum
        for that preload to be considered non-orphan.

    Returns
    -------
    pruned : `lsst.pipe.base.QuantumGraph`
        A new graph with the orphan preload quanta and their downstream
        descendants removed. The original ``qg`` is returned unchanged
        if there is nothing to prune.
    """
    preload_task = _find_task_def(qg, preload_label)
    if preload_task is None:
        _LOG.info("No %r task in QG; nothing to prune.", preload_label)
        return qg

    anchor_task = _find_task_def(qg, anchor_label)
    if anchor_task is None:
        anchor_nodes = frozenset()
        _LOG.warning(
            "No %r quanta in QG; every %r quantum will be treated as an orphan.",
            anchor_label,
            preload_label,
        )
    else:
        anchor_nodes = qg.getNodesForTask(anchor_task)

    graph = qg._connectedQuanta

    reachable_from_anchor = set(anchor_nodes)
    for node in anchor_nodes:
        reachable_from_anchor.update(nx.ancestors(graph, node))

    preload_nodes = qg.getNodesForTask(preload_task)
    orphan_preloads = preload_nodes - reachable_from_anchor

    if not orphan_preloads:
        _LOG.info("No orphan %r quanta found; QG unchanged.", preload_label)
        return qg

    to_remove = set(orphan_preloads)
    for node in orphan_preloads:
        to_remove.update(nx.descendants(graph, node))

    descendants_count = len(to_remove) - len(orphan_preloads)
    _LOG.info(
        "Pruning %d orphan %r quanta and %d downstream quanta (%d total).",
        len(orphan_preloads),
        preload_label,
        descendants_count,
        len(to_remove),
    )

    pruned = qg.subset(set(qg) - to_remove)

    # QuantumGraph.subset() does not propagate per-task init input/output
    # refs (see the "TODO: Do we need to copy initInputs/initOutputs?" in
    # pipe_base graph.py). Copy them across by hand so downstream tools
    # like `pipetask update-graph-run` — which BPS invokes whenever the
    # config defines a finalJob — still find init outputs like isr_config.
    surviving_labels = {td.label for td in pruned.iterTaskGraph()}
    pruned._initInputRefs = {
        label: list(refs) for label, refs in qg._initInputRefs.items() if label in surviving_labels
    }
    pruned._initOutputRefs = {
        label: list(refs) for label, refs in qg._initOutputRefs.items() if label in surviving_labels
    }
    return pruned


def main(argv=None):
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Prune loadDiaCatalogs quanta with no downstream associateApdb "
            "quantum (and their downstream chain) from a QuantumGraph file."
        )
    )
    parser.add_argument("input", help="Path to the input QuantumGraph (.qgraph or .qg).")
    parser.add_argument("output", help="Path to write the pruned QuantumGraph.")
    parser.add_argument(
        "--preload-label",
        default=PRELOAD_LABEL,
        help="Task label of the preload task (default: %(default)s).",
    )
    parser.add_argument(
        "--anchor-label",
        default=ANCHOR_LABEL,
        help=(
            "Task label whose presence downstream marks a preload as "
            "non-orphan (default: %(default)s)."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("numexpr").setLevel(logging.WARNING)

    _LOG.info("Loading QG from %s", args.input)
    qg = QuantumGraph.loadUri(args.input)
    _LOG.info("Loaded %d quanta.", len(qg))

    pruned = prune_orphan_preloads(qg, args.preload_label, args.anchor_label)

    _LOG.info("Writing pruned QG (%d quanta) to %s", len(pruned), args.output)
    pruned.saveUri(args.output)


if __name__ == "__main__":
    main()
