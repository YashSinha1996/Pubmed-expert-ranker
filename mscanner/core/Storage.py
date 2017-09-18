"""Dictionary subclasses supporting dotted access"""


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



class Storage(dict):
    """Dictionary supporting d.foo attribute access to keys.
    
    Raises AttributeError instead of KeyError when attribute-style access
    fails."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k

    def __setattr__(self, key, value): 
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k

    def __str__(self):
        return "Storage(\n" + \
               "\n".join("   " + k + " = " + repr(v) + "," 
                         for k, v in self.iteritems()) + "\n)"

    def __repr__(self):     
        return '<Storage ' + dict.__repr__(self) + '>'



class RCStorage(Storage):
    """Dictionary with attribute access and auto-calling of stored functions.
    
    @note: d.foo returns d.foo() if d['foo'] is callable

    Example::
        rc = RCStorage()
        rc.bar = 2
        rc.foo = lambda: rc.bar + 2
        rc.foo == 4
        rc.bar = 3
        rc.foo == 5
    """

    def __getattr__(self, key):
        v = Storage.__getattr__(self, key)
        return (v() if hasattr(v, "__call__") else v)

    def __str__(self):
        result = "RCStorage("
        for k, v in self.iteritems():
            if hasattr(v, "__call__"):
                v = v()
            result += "\n   " + k + " = " + str(v) + ","
        return result+"\n)"
