#!/usr/bin/env python

"""Performs queries using datasets from the MScanner paper

Usage::

    python query.py <dataset> [ <dataset> ... ]

Example::

    python query.py pg07 radiology aids
"""

__copyright__ = "2007 Graham Poulter"
__author__ = "Graham Poulter <http://graham.poulter.googlepages.com>"
__license__ = """This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>."""

import sys

from mscanner.configuration import rc
from mscanner.core import iofuncs
from mscanner.core.QueryManager import QueryManager
from mscanner.medline.Databases import Databases


dataset_map = {
    "aidsbio"     : "Paper/aidsbio.txt",
    "pg07"        : "Paper/pg07_full.txt",
    "radiology"   : "Paper/radiology.txt",
    "gdsmall"     : "Test/gdsmall.txt",
    "invalid"     : "Test/invalid.txt",
}
"""Mapping from dataset code to input file"""


def do_query(*datasets):
    env = Databases()
    for dataset in datasets:
        if dataset not in dataset_map:
            raise ValueError("Invalid Data Set %s" % dataset)
        QM = QueryManager(rc.working / "query" / dataset, dataset, limit=500,
                          env=env, threshold=0, prior=None)
        QM.query(rc.corpora / dataset_map[dataset])
        QM.write_report()
    env.close()
    

if __name__ == "__main__":
    iofuncs.start_logger()
    do_query(*sys.argv[1:])
    

