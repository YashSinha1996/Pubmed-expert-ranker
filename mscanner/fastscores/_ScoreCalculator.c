/* Calculates document scores by iterating over a binary feature stream.
This is about 50x faster than the Python version.

Usage:

./cscore \
[citations] \
[numdocs] \
[numfeats] \
[offset] \
[limit] \
[threshold] \
[mindate] \
[maxdate] \
< feature_scores > results

  The [citations] file consists of [numcites] records, which are
  binary records, which can be expressed as the structure::

  struct {
    unsigned int pmid; // PubMed ID of citation
    unsigned int date; // Record completion date
    unsigned short nfeatures; // Number of features
    unsigned short features[nfeatures]; // Feature vector
  };

  The feature scores from standard input are a list of [numfeats]
  64-bit doubles.

  The output is a list of [limit] citation scores as score_t structures,
  where each citation score has [offset] added to it beforehand.
  
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
#include <math.h>

// Simple tests for ctypes
void double_int(int a, int *b) { 
    *b = a*2; 
}
void double_array(int len, int *a) { 
    int i;
    for(i = 0; i < len; i++) a[i] *= 2; 
}


// Holds PubMed ID and score of a citation
typedef struct {
    float score;
    unsigned int pmid;
} score_t;


// For qsort, to sort the scores in decreasing order
int compare_scores(const void *a, const void *b) {
    return (int)rint(((const score_t *)b)->score - ((const score_t *)a)->score);
}


#ifdef CSCORE
int main (int argc, char **argv)
#else
void cscore(
    // INPUT PARAMETERS
    char *cite_filename,  // File to open for citation stream
    int numcites,         // Number of citations
    int numfeats,         // Number of features
    float offset,         // Amount to add to citation score
    int limit,            // Number of pmid,score pairs to return
    float threshold,      // Minimum score to consider
    int mindate,          // Minimum date to consider
    int maxdate,          // Maximum date to consider
    double *featscores,   // Array of feature scores
    // OUTPUT PARAMETERS
    int *o_numresults,    // Output scalar for number of results
    float *o_scores,      // Output array for scores
    int *o_pmids          // Output array for pmids
    ) 
#endif
{

    #ifdef CSCORE
    // Parameters
    char *cite_filename = argv[1];    // Name of citations file
    int numcites = atoi (argv[2]);    // Number of citations
    int numfeats = atoi (argv[3]);    // Number of features
    float offset = atof (argv[4]);    // Amount to add to scores
    int limit = atoi (argv[5]);       // Number of results to return
    float threshold = atof (argv[6]); // Minimum score to consider
    int mindate = atoi (argv[7]);     // Minimum date to consider
    int maxdate = atoi (argv[8]);     // Maximum date to consider
    #endif
    
    // Loop variables
    FILE *citefile = NULL; // File with citation scores
    int pi = 0; // Loop variable: number of PubMed ID's so far
    int fi = 0; // Loop variable: index into feature vector
    int date = 0; // Date of the current citation
    int numresults = 0; // Number of available results to return
    float tmp_score = 0.0; // Accumulator for calculating record score
    unsigned short featvec_size = 0; // Size of current feature vector
    unsigned short featvec[1000]; // Maximum of 1000 features per citation

    // Scores of all citations 
    score_t *scores = (score_t*) malloc (numcites * sizeof(score_t));

    #ifdef CSCORE
    // Allocate space for scores and read from input
    double *featscores = (double*) malloc (numfeats * sizeof(double));
    fread(featscores, sizeof(double), numfeats, stdin);
    #endif

    // Calculate citation scores
    citefile = fopen(cite_filename, "rb");
    for(pi = 0; pi < numcites; pi++) {
        // Read feature vector from the binary file
        fread(&scores[pi].pmid, sizeof(unsigned int), 1, citefile);
        fread(&date, sizeof(unsigned int), 1, citefile);
        fread(&featvec_size, sizeof(unsigned short), 1, citefile);
        fread(featvec, sizeof(unsigned short), featvec_size, citefile);
        // Don't bother if the date is outside the range
        if ((date < mindate) || (date > maxdate)) {
            // Don't let it sneak in when sorting
            scores[pi].score = -10000.0;
            continue;
        }
        // Start with the offset score
        tmp_score = offset;
        // Add up the adjusted feature scores
        for(fi = 0; fi < featvec_size; fi++) {
            tmp_score += (float)featscores[featvec[fi]];
        }
        scores[pi].score = tmp_score;
        // Count the result if it scores high enough
        if (tmp_score >= threshold) {
            numresults++;
        }
    }
    fclose(citefile);

    // Sort the citations
    qsort(scores, numcites, sizeof(score_t), compare_scores);
    
    // Output the top citations, to a maximum of limit
    if (numresults > limit)
        numresults = limit;

    #ifdef CSCORE
    // Print results and return from main
    fwrite(scores, sizeof(score_t), numresults, stdout);
    return 0;
    #else
    // Store top citations in o_scores and o_pmids
    for(pi = 0; pi < numresults; pi++) {
        o_scores[pi] = scores[pi].score;
        o_pmids[pi] = scores[pi].pmid;
    }
    // Return number of results
    *o_numresults = numresults;
    // Free the scores pointer
    free(scores);
    #endif
}
