"""Persistent shelf backed by Berkeley DB"""

import bsddb
import cPickle
import os
import unittest
from path import path
from UserDict import DictMixin
import zlib


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


def open(filename, flags='c', mode=0660, dbenv=None, txn=None, dbname=None, compress=True):
    """Open a shelf with Berkeley DB backend

    @param flags: One of 'r','rw','w','c','n'. Optionally specify flags such as
    db.DB_CREATE, db.DB_TRUNCATE, db.DB_RDONLY, db.DB_AUTO_COMMIT. 
    
    @param dbenv: Provides a db.DBEnv environment
    
    @param txn: Optional transaction for the opening operation.
    
    @param dbname: Selects a sub-database from the file.
    
    @param compress: If True, also gzip the pickles in the shelf.
    
    @return: L{Shelf} using the opened database.
    """
    if isinstance(flags, basestring):
        if flags == 'r':
            flags = bsddb.db.DB_RDONLY
        elif flags == 'rw':
            flags = 0
        elif flags == 'w':
            flags = bsddb.db.DB_CREATE
        elif flags == 'c':
            flags = bsddb.db.DB_CREATE
        elif flags == 'n':
            flags = bsddb.db.DB_TRUNCATE | db.DB_CREATE
        else:
            raise bsddb.db.DBError("Flag %s is not in 'r', 'rw', 'w', 'c' or 'n'"  % str(flags))
    database = bsddb.db.DB(dbenv)
    database.open(filename, dbname, bsddb.db.DB_HASH, flags, mode, txn=txn)
    return Shelf(database, txn, compress)

class Shelf(DictMixin):
    """A shelf built upon a bsddb DB object."""

    def __init__(self, database, txn=None, do_compression=True):
        """Initialise shelf with a db.DB object
        
        @param database: Instance of a db database
        
        @param txn: Optional transaction context for shelf operations

        @param do_compression: If True, compress pickles with zlib.
        """
        self.db = database
        self.do_compression = do_compression
        self.set_txn(txn)
        if self.do_compression:
            self.compress = zlib.compress
            self.decompress = zlib.decompress
        else:
            self.compress = lambda x:x
            self.decompress = lambda x:x

    def set_txn(self, txn=None):
        """Set the transaction to use for database operations"""
        self.txn = txn

    def close(self):
        """Close the underlying database.  Shelf must not be used afterwards."""
        self.db.close()

    def __del__(self):
        self.db.close()

    def __len__(self):
        return self.db.stat()["ndata"]

    def __getitem__(self, key):
        v = self.db.get(key, txn=self.txn)
        if v is None: raise KeyError("Key %s not in database" % repr(key))
        return cPickle.loads(self.decompress(v))

    def __setitem__(self, key, value):
        self.db.put(key, self.compress(cPickle.dumps(value, protocol=2)), self.txn)

    def __delitem__(self, key):
        self.db.delete(key, self.txn)

    def keys(self):
        return self.db.keys(self.txn)

    def items(self):
        return list(self.iteritems())

    def values(self):
        return [ v for k,v in self.iteritems() ]

    def __contains__(self, key):
        return self.db.has_key(key, self.txn)

    def iteritems(self):
        cur = self.db.cursor(self.txn)
        rec = cur.first()
        while rec is not None:
            yield rec[0], cPickle.loads(self.decompress(rec[1]))
            rec = cur.next()
        cur.close()
        
    def __iter__(self):
        cur = self.db.cursor(self.txn)
        rec = cur.first(dlen=0, doff=0)
        while rec is not None:
            yield rec[0]
            rec = cur.next(dlen=0, doff=0)
        cur.close()
