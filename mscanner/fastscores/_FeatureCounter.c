/* Calculate the number of occurrences of each feature within a 
specified date range.

Usage:

./featcounts \
[citations] \
[numdocs] \
[numfeats] \
[mindate] \
[maxdate] \
> feature_socres

  The [citations] file consists of [numcites] records, which are
  binary records, which can be expressed as the structure::

  struct {
    unsigned int pmid; // PubMed ID of citation
    unsigned int date; // Record completion date
    unsigned short nfeatures; // Number of features
    unsigned short features[nfeatures]; // Feature vector
  };

  The output is a list of [numfeats] integers representing the
  feature counts.
  
Copyright (C) 2007 Graham Poulter
*/

/* This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>. */

#include <stdio.h>
#include <stdlib.h>


// Search sorted array A of length N for needle.
// Return 1 if we find the needle, 0 if we do not
// http://en.wikipedia.org/wiki/Binary_search
int binary_search(int *A, int N, int needle) {
    int low = 0;
    int high = N-1;
    int mid = 0;
    while (low <= high) {
        mid = (low + high) / 2;
        if (A[mid] > needle) {
            high = mid - 1;
        } else if (A[mid] < needle) {
            low = mid + 1;
        } else {
            return 1;
        }
    }
    return 0;
}


int main (int argc, char **argv)
{
    // Parameters
    char *cite_filename = argv[1];    // Name of citations file
    int numcites = atoi (argv[2]);    // Number of citations
    int numfeats = atoi (argv[3]);    // Number of features
    int mindate = atoi (argv[4]);     // Minimum date to consider
    int maxdate = atoi (argv[5]);     // Maximum date to consider
    int numexcluded = atoi (argv[6]); // Number of excluded citations
    
    // Loop variables
    FILE *citefile = NULL; // File with citation scores
    int pi = 0; // Loop variable: number of PubMed ID's so far
    int fi = 0; // Loop variable: index into feature vector
    int date = 0; // Date of the current citation
    int pmid = 0; // PubMed ID of the current citation
    int ndocs = 0; // Number of documents counted
    unsigned short featvec_size = 0; // Size of current feature vector
    unsigned short featvec[1000]; // Maximum of 1000 features per citation

    // Allocate space for excluded PMIDs 
    int *excluded = (int*) malloc (numexcluded * sizeof(int));
    
    // Allocate space for feature counts 
    int *featcounts = (int*) malloc (numfeats * sizeof(int));

    // Read excluded PMIDs from input
    fread(excluded, sizeof(int), numexcluded, stdin);

    // Initialise feature counts to zero
    for(fi = 0; fi < numfeats; fi++) featcounts[fi] = 0;

    // Calculate citation scores
    citefile = fopen(cite_filename, "rb");
    for(pi = 0; pi < numcites; pi++) {
        // Read feature vector from the binary file
        fread(&pmid, sizeof(unsigned int), 1, citefile);
        fread(&date, sizeof(unsigned int), 1, citefile);
        fread(&featvec_size, sizeof(unsigned short), 1, citefile);
        fread(featvec, sizeof(unsigned short), featvec_size, citefile);
        // Don't bother if the date is outside the range
        if ((date < mindate) || (date > maxdate)) {
            continue;
        }
        // Don't bother if it is a member of exclude
        if (binary_search(excluded, numexcluded, pmid) == 1) {
            continue;
        }
        // Add up the feature scores
        for(fi = 0; fi < featvec_size; fi++)
            featcounts[featvec[fi]]++;
        // Counted features for one more document
        ndocs++;
    }
    fclose(citefile);

    // Print number of docs, feature counts before returning from main
    fwrite(&ndocs, sizeof(int), 1, stdout);
    fwrite(featcounts, sizeof(int), numfeats, stdout);
    return 0;
}
