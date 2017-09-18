"""Maps PubMed IDs to feature vectors"""

from bsddb import db
import numpy as nx
import logging
import struct


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


class FeatureDatabase:
    """Database for which PubMed ID is the key and array of Feature IDs are values
    """
    
    def __init__(self, filename=None, flags='c', mode=0660, dbenv=None, txn=None, dbname=None, ftype=nx.uint16):
        """Initialise database

        @param filename: Path to database file
        @param flags: Opening flags (r,rw,w,c,n)
        @param mode: Numeric file permissions
        @param dbenv: Optional database environment
        @param txn: Optional database transaction
        @param dbname: Logical database name
        @param ftype: Numpy numeric feature type
        """
        self.ftype = ftype
        if isinstance(flags, basestring):
            if flags == 'r':
                flags = db.DB_RDONLY
            elif flags == 'rw':
                flags = 0
            elif flags == 'w':
                flags = db.DB_CREATE
            elif flags == 'c':
                flags = db.DB_CREATE
            elif flags == 'n':
                flags = db.DB_TRUNCATE | db.DB_CREATE
            else:
                raise db.DBError("Flag %s is not in 'r', 'rw', 'w', 'c' or 'n'"  % str(flags))
        self.db = db.DB(dbenv)
        self.db.open(filename, dbname, db.DB_HASH, flags, mode, txn=txn)


    def close(self):
        """Close the database.  Do not use this object after doing so"""
        self.db.close()
    __del__ = close


    def getitem(self, key, txn=None):
        """Return an ndarray object of values for a given key"""
        buf = self.db.get(str(key), txn=txn)
        if buf is None:
            raise KeyError("Record %d not found in feature database" % key)
        return nx.fromstring(buf, self.ftype)


    def setitem(self, key, features, txn=None):
        """Associate integer key with an ndarray object of values"""
        if features.dtype != self.ftype:
            raise ValueError("array type mismatch: " + 
                             str(features.dtype) + " for key " + str(key))
        try:
            self.db.put(str(key), features.tostring(), txn=txn)
        except ValueError, e:
            logging.error("Failed to add to db " + str(key) + " : " +  str(features))
            raise


    def delitem(self, key, txn=None):
        """Delete a given key from the database"""
        self.db.delete(str(key), txn=txn)


    # Bunch of dictionary-like methods

    def __getitem__(self, key):
        return self.getitem(key)


    def __setitem__(self, key, values):
        self.setitem(key, values)


    def __len__(self):
        """Fast way to check number of items in database"""
        return self.db.stat()["ndata"]


    def __contains__(self, key):
        """Test for document ID membership.  Converts ID to a string first."""
        return self.db.has_key(str(key))


    def keys(self):
        """Return list of PubMed IDs in the database"""
        return [ k for k in self ]


    def __iter__(self):
        """Iterate over PubMed IDs in the database"""
        cur = self.db.cursor()
        rec = cur.first(dlen=0, doff=0)
        while rec is not None:
            yield rec[0]
            rec = cur.next(dlen=0, doff=0)
        cur.close()


    def iteritems(self):
        """Iterate over (PMID, ndarray) pairs in the database"""
        cur = self.db.cursor()
        rec = cur.first()
        while rec is not None:
            yield rec[0], nx.fromstring(rec[1],self.ftype)
            rec = cur.next()
        cur.close()



