"""Test suite for mscanner.medline.Shelf

@copyright: 2007 Graham Poulter

@license: This source file is free software. It comes without any warranty, to
the extent permitted by applicable law. You can redistribute it and/or modify
it under the Do Whatever You Want Public License. Terms and conditions: 
   0. Do Whatever You Want
"""

from bsddb import db
import logging
from path import path
import tempfile
import unittest

from mscanner.medline import Shelf


class DbshelveTests(unittest.TestCase):
    """Test for Shelf class"""

    def setUp(self):
        self.db = Shelf.open(None)

    def test(self):
        d = self.db
        d["A"] = ("A",2)
        d["B"] = ("B",3)
        self.assertEqual(d["A"],("A",2))
        self.assertEqual(len(d), 2)
        self.assertEqual("B" in d, True)
        self.assertEqual(d.keys(), ["B","A"])
        self.assertEqual(d.items(), [ ("B",("B",3)), ("A",("A",2)) ])
        self.assertEqual(d.values(), [ ("B",3), ("A",2) ])
        self.assertEqual(list(d.iterkeys()), ["B","A"])
        self.assertEqual(list(d.iteritems()), [ ("B",("B",3)), ("A",("A",2)),  ])
        self.assertEqual(list(d.itervalues()), [ ("B",3) , ("A",2), ])
        del d["B"]
        self.assertRaises(KeyError, d.__getitem__, "B")
        self.assertRaises(KeyError, d.__delitem__, "B")



class TransactionTests(DbshelveTests):
    """Test using transactions with L{Shelf}"""

    def setUp(self):
        self.envdir = path(tempfile.mkdtemp(prefix="Shelf-"))
        self.env = db.DBEnv()
        self.env.open(self.envdir, db.DB_INIT_MPOOL|db.DB_INIT_TXN|db.DB_CREATE)
        self.db = Shelf.open(self.envdir/'dbshelf.db', db.DB_CREATE|db.DB_AUTO_COMMIT, dbenv=self.env)

    def tearDown(self):
        if self.txn is not None:
            self.txn.abort()
        self.db.close()
        self.env.close()
        self.envdir.rmtree(ignore_errors=True)

    def test(self):
        # Test aborting
        self.txn = self.env.txn_begin()
        self.db.set_txn(self.txn)
        super(TransactionTests, self).test()
        self.txn.abort()
        self.assertEqual(len(self.db), 0)
        # Test committing
        self.txn = self.env.txn_begin()
        self.db.set_txn(self.txn)
        super(TransactionTests, self).test()
        self.txn.commit()
        self.assertEqual(len(self.db), 1)
        self.txn = None


if __name__ == "__main__":
    unittest.main()
