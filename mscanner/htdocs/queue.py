#!/usr/bin/env python

"""Queueing facility for the web frontend

Queueing program checks queue directory every second for new descriptor files,
and starts a query or validation operation. When the operation completes, the
descriptor file is moved to the output.

Example descriptor file for query::
    #operation = query
    #dataset = Whatever
    #limit = 500
    #threshold = 10.3
    #submitted = 23424123.3
    804133
    3214241
    ...
    
Example descriptor file for validation::
    #operation = validate
    #dataset = Whatever
    #numnegs = 100000
    #alpha = 0.5
    #submitted = 23424123.3
    804133
    3214241
    ...
"""

from __future__ import with_statement
from __future__ import division

import logging
import math
import os
from path import path
import sys
import time

from mscanner.configuration import rc
from mscanner.medline.Databases import Databases
from mscanner.core.QueryManager import QueryManager
from mscanner.core.ValidationManager import CrossValidation
from mscanner.core import iofuncs
from mscanner.scripts import update


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


def parsebool(s):
    """Handler for converting strings to booleans"""
    if isinstance(s, basestring):
        s = s.strip()
        if s == "0" or s == "False":
            return False
        elif s == "1" or s == "True":
            return True
        else:
            raise ValueError("Failed to parse boolean: %s" % s)
    else:
        return bool(s)


descriptor_keys = dict(
    captcha=str,      # Captcha value in the form
    dataset=str,      # Name of the input corpus
    delcode=str,      # MD5 of deletion code
    hidden=parsebool, # Whether to hide the output
    limit=int,        # Upper limit on number of results
    mindate=int,      # Minimum date to consider
    minscore=float,   # Minimum classifier score to predict relevance
    numnegs=int,      # Number of irrelevant articles for CV
    operation=str,    # "retrieval" or "validation"
    prevalence=float, # Estimated fraction of relevant articles in Medline
    submitted=float,  # Timestamp when the task was submitted
    )


def read_descriptor(fpath):
    """Reads a descriptor file, returning a dictionary of parameters.

    Each line is '#key = value'. We stops at the first line that not starting
    with '#'.  Valid keys are in L{descriptor_keys}. The same file can be used
    with read_pmids, which will ignores the lines beginning with '#'.

    @return: Storage object, with additional '_filename' containing fpath."""
    from mscanner.core.Storage import Storage
    result = Storage()
    with open(fpath, "r") as f:
        line = f.readline()
        while line.startswith("#"):
            key, value = line[1:].split(" = ",1)
            value = value.strip()
            if value == "None": 
                value = None
            else:
                value = descriptor_keys[key](value.strip())
            result[key] = value
            line = f.readline()
        result["_filename"] = fpath
    return result


def write_descriptor(fpath, pmids, params):
    """Write parameters and PubMed IDs to the descriptor file.
    @param fpath: File to write
    @param pmids: List of PubMed IDs, may be None
    @param params: Dictionary to write. Values are converted with str(). Only
    keys from descriptor_keys are used."""
    with open(fpath, "w") as f:
        fpath.chmod(0777)
        for key, value in params.iteritems():
            if key in descriptor_keys: 
                f.write("#" + key + " = " + str(value) + "\n")
        if pmids is not None:
            for pmid in pmids:
                f.write(str(pmid)+"\n")


class QueueStatus:
    """Describes the current state of the queue
    
    @ivar tasklist: Descriptors of tasks in the queue, oldest first.
    
    @ivar running: First member of L{tasklist}, which is being processed.
    
    @ivar donelist: Completed tasks, oldest first.
    
    @ivar status: Mapping from dataset to status code (DONE, RUNNING, WAITING)
    
    @ivar _tasks: Mapping from dataset to task object
    """
    
    DONE = "done"
    RUNNING = "running"
    WAITING = "waiting"
    
    def __init__(self, with_done=True):
        """Constructor for the status
        
        @param with_done: Set this to False if you don't need L{donelist}."""
        self._load_tasklist()
        self.donelist = []
        if with_done: self._load_donelist()
        self._load_maps()

    
    def _load_tasklist(self):
        """Populate L{tasklist}.
        
        @note: We only load files that are older than 1/20th second. Without
        this we sometimes catch files half-written by the web interface. This
        in turn means query_logic.py has to wait 0.05 seconds before going to
        the status page, so that the task shows up.
        """
        current_time = time.time()
        eligible_files = [f for f in rc.queue_path.files() \
                          if f.mtime < current_time-0.05]
        self.tasklist = [read_descriptor(f) for f in eligible_files]
        self.tasklist.sort(key=lambda x:x.submitted)
        self.running = self.tasklist[0] if self.tasklist else None


    def _load_donelist(self):
        """Populate L{donelist}"""
        self.donelist = []
        for fpath in rc.web_report_dir.dirs():
            if (fpath/rc.report_descriptor).exists():
                self.donelist.append(
                    read_descriptor(fpath/rc.report_descriptor))
        self.donelist.sort(key=lambda x:x.submitted)


    def _load_maps(self):
        """Calculate the L{status} and L{_tasks} mapping"""
        self.status = {}
        self._tasks = {}
        for task in self.tasklist:
            self.status[task.dataset] = self.WAITING
            self._tasks[task.dataset] = task
        for task in self.donelist:
            self.status[task.dataset] = self.DONE
            self._tasks[task.dataset] = task
        if self.tasklist:
            self.status[self.running.dataset] = self.RUNNING

    
    def __getitem__(self, dataset):
        """Retrieve the task descriptor for a given data set."""
        return self._tasks.__getitem__(dataset)


    def __contains__(self, dataset):
        """Return whether given dataset exists"""
        return self._tasks.__contains__(dataset)


    def position(self, dataset):
        """Return distance of dataset from front of queue."""
        for idx, d in enumerate(self.tasklist):
            if d.dataset == dataset:
                return idx
        return None

    
    

def delete_output(dataset):
    """Delete the output directory for the given task"""
    logging.debug("Attempting to delete output for %s" % dataset)
    dirpath = rc.web_report_dir / dataset
    for fname in dirpath.files():
        fname.remove()
    dirpath.rmdir()



def logit(probability):
    if probability is None:
        return None
    else:
        return math.log(probability/(1-probability))


def mainloop():
    """Look for descriptor files every second"""
    env = None
    try:
        # time.time() of last output-cleaning
        last_clean = 0 
        # time.time() of last database update
        last_update = 0 
        while True:
            # Delete oldest outputs twice daily
            if time.time() - last_clean > 12*3600:  
                logging.info("Looking for old datasets")
                queue = QueueStatus()
                queue.donelist.reverse() # Newest first
                for task in queue.donelist[100:]:
                    try:
                        delete_output(task.dataset)
                    except OSError:
                        pass # Failed to delete output
                last_clean = time.time()
            
            # Update the databases twice daily
            if time.time() - last_update > 12*3600:
                if env is not None: env.close()
                env = None
                update.update_mscanner()
                env = Databases()
                env.article_list # long first load time
                last_update = time.time()
            
            # Perform any queued tasks
            queue = QueueStatus()
            task = queue.running
            if task is not None:
                # The output directory for the task
                outdir = rc.web_report_dir / task.dataset
                logging.info("Starting %s for %s", task.operation, task.dataset)
                # Update task file mod time for the status display
                task._filename.utime(None) 
                try:
                    if task.operation == "retrieval":
                        QM = QueryManager(
                            outdir=outdir, 
                            dataset=task.dataset,
                            limit=task.limit,
                            env=env,
                            threshold=task.minscore,
                            prior=logit(task.prevalence),
                            mindate=task.mindate,
                            maxdate=None,
                            )
                        QM.query(task._filename)
                        time.sleep(5)
                        QM.write_report()
                        QM.__del__()
                    elif task.operation == "validate":
                        VM = CrossValidation(
                            outdir=outdir, 
                            dataset=task.dataset,
                            env=env)
                        VM.validation(task._filename, task.numnegs)
                        VM.report_validation()
                        VM.__del__()
                    task._filename.move(outdir / "descriptor.txt")
                except ValueError, e:
                    logging.exception(e)
            else:
                # Nothing to do so sleep before the next iteration
                time.sleep(1)
    finally:
        if env is not None: env.close()


def populate_test_queue():
    """Place some dummy queue files to test the queue operation"""
    from mscanner.core.Storage import Storage
    pmids = list(iofuncs.read_pmids(rc.corpora / "Test" / "gdsmall.txt"))
    task = Storage(
        captcha = "orange",
        dataset = "gdqtest_valid",
        hidden = False,
        limit = 500,
        mindate = 19700101,
        minscore = 0.0, 
        numnegs = 1000, 
        operation = "validate", 
        prevalence = 0.01,
        submitted = time.time())
    write_descriptor(rc.queue_path/task.dataset, pmids, task)
    task.operation = "retrieval"
    task.dataset = "gdqtest_query"
    task.submitted += 5
    write_descriptor(rc.queue_path/task.dataset, pmids, task)


if __name__ == "__main__":
    iofuncs.start_logger()
    if len(sys.argv) == 2 and sys.argv[1] == "test":
        populate_test_queue()
    try:
        mainloop()
    except KeyboardInterrupt:
        pass
    logging.shutdown()
