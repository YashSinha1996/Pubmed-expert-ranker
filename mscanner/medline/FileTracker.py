"""A simple persistant set of file names"""

from __future__ import with_statement
from path import path


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


class FileTracker(set):
    """A persistent set for tracking of processed files.
    
    @ivar trackfile: Path for saving/loading the list of precessed files
    """

    def __init__(self, trackfile=None):
        """Constructor - sets L{trackfile}"""
        self.trackfile = trackfile
        if isinstance(trackfile, path) and trackfile.isfile():
            self.update(trackfile.lines(retain=False))

    def dump(self):
        """Write the list of tracked files, one per line"""
        if self.trackfile is None:
            return
        tfnew = self.trackfile + ".new"
        tfnew.write_lines(sorted(self))
        if self.trackfile.isfile():
            self.trackfile.remove()
        tfnew.rename(self.trackfile)

    def add(self, fname):
        """Add fname.basename() to the set"""
        set.add(self, fname.basename())

    def toprocess(self, paths):
        """Filter for files that have not been processed yet
        
        @param paths: List of paths to consider
        
        @return: Those members of L{paths} whose base names are not in the set
        """
        return sorted(f for f in paths if f.basename() not in self)