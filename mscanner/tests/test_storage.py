"""Test suite for mscanner.utils.Storage

@copyright: 2007 Graham Poulter

@license: This source file is free software. It comes without any warranty, to
the extent permitted by applicable law. You can redistribute it and/or modify
it under the Do Whatever You Want Public License. Terms and conditions: 
   0. Do Whatever You Want
"""

import unittest
from mscanner.core.Storage import Storage, RCStorage


class StorageModuleTests(unittest.TestCase):
    
    def test_Storage(self):
        # Storage
        s1 = Storage(a = 1, b = 2)
        s1.a = 5
        self.assertEqual(s1.a, 5)
        # RCStorage
        s2 = RCStorage(a = 1)
        s2.b = lambda: s2.a + 1
        self.assertEqual(s2.a, 1)
        self.assertEqual(s2.b, 2)


if __name__ == "__main__":
    unittest.main()
