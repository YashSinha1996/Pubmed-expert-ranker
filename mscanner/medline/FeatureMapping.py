"""Provides a mapping between features and integer IDs"""

from __future__ import with_statement
import codecs
import numpy as nx


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


class FeatureMapping:
    """Persistent mapping between string features and feature IDs

    Feature types used with L{__getitem__}, L{get_type_mask} and
    L{add_article} are "mesh", "qual", "issn". A feature string could have more
    than one type.
    
    This is really a table with columns (id,type,name,count), and keys of id
    and (type,name).

    @ivar featfile: Path to text file with list of terms

    @ivar featfile_new: Temporary feature file used while writing
    
    @ivar numdocs: Number of documents used in creating the mapping
    
    @ivar features: List, such that features[id] == (name,type)
    
    @ivar feature_ids: Mapping, such that feature_ids[type][name] == id
    
    @ivar counts: List, such that counts[id] == number of occurrences.  For
    score calculation this is the only column needed.
    """

    def __init__(self, featfile=None):
        """Initialise the database, setting L{featfile}"""
        self.featfile = featfile
        if self.featfile is not None:
            self.featfile_new = featfile+".new"
        self.numdocs = 0
        self.features = []
        self.feature_ids = {}
        self.counts = []
        if featfile is not None and self.featfile.exists():
            self.load()
        
    def load(self):
        """Load feature mapping mapping from file as a tab-separated
        table for tuples (feature, type, count) with ID being the
        0-based index in the file.
        """
        self.features = []
        self.feature_ids = {}
        with codecs.open(self.featfile, "rb", "utf-8") as f:
            self.numdocs = int(f.readline().strip())
            for fid, line in enumerate(f):
                feat, ftype, count = line.strip().split("\t")
                self.features.append((feat,ftype))
                self.counts.append(int(count))
                if ftype not in self.feature_ids:
                    self.feature_ids[ftype] = {feat:fid}
                else:
                    self.feature_ids[ftype][feat] = fid

    def dump(self):
        """Write the feature mapping to disk as a table of
        (name, type, count) where line number is ID+1"""
        if self.featfile is None:
            return
        with codecs.open(self.featfile_new, "wb", "utf-8") as f:
            f.write("%s\n" % self.numdocs)
            for (feat, ftype), count in zip(self.features, self.counts):
                f.write(feat+"\t"+ftype+"\t"+str(count)+"\n")
        if self.featfile.isfile():
            self.featfile.remove()
        self.featfile_new.rename(self.featfile)

    def __getitem__(self, key):
        """Given a feature ID, return (feature, feature type). Given (feature,
        feature type), returns feature ID"""
        if isinstance(key, int):
            return self.features[key]
        elif isinstance(key, tuple) and len(key) == 2:
            return self.feature_ids[key[1]][key[0]]
        else:
            raise KeyError("Invalid key: %s" % str(key))

    def __len__(self):
        """Return number of distinct features"""
        return len(self.features)

    def get_type_mask(self, exclude_types):
        """Get a mask for excluded features

        @param exclude_types: Types of features to exclude

        @return: Boolean array for excluded features (but returns None if
        exclude_types is None) 
        """
        if not exclude_types:
            return None
        exclude_feats = nx.zeros(len(self.features), nx.bool)
        for ftype in exclude_types:
            for fid in self.feature_ids[ftype].itervalues():
                exclude_feats[fid] = True
        return exclude_feats

    def add_article(self, **kwargs):
        """Add an article, given lists of features of different types.
        
        @note: Dynamically creates new features IDs and feature types as necessary.
        
        @param kwargs: Mapping from feature types to lists of features for that
        type. e.g. C{mesh=["Term A","Term B"]}
        
        @return: Numpy array of uint16 feature IDs
        """
        result = []
        self.numdocs += 1
        for ftype, fstrings in kwargs.iteritems():
            if ftype not in self.feature_ids:
                self.feature_ids[ftype] = {}
            fdict = self.feature_ids[ftype]
            for feat in fstrings:
                if feat not in fdict:
                    featid = len(self.features)
                    self.features.append((feat,ftype))
                    self.counts.append(1)
                    fdict[feat] = featid
                else:
                    self.counts[fdict[feat]] += 1
                result.append(fdict[feat])
        return nx.array(result, nx.uint16)
