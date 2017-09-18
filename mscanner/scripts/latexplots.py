#!/usr/bin/env python

"""
Draws publication-quality plots for use in the paper

The figures are::
    Figure 1. Four score density plots
    Figure 2. ROC curve overlay
    Figure 3. PR curve overlay
    Figure 4. P,R,F1,Fa curve for AIDSBio to demo optimisation

"""

from __future__ import with_statement
from __future__ import division

import logging
from path import path
from pylab import *

from mscanner.configuration import rc as mrc
from mscanner.core import iofuncs
from mscanner.core.Plotter import Plotter, DensityPlotter
from mscanner.core.metrics import PerformanceVectors
from mscanner.scripts import retrievaltest


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

interactive = False
npoints = 400
mscanner_dir = path(r"C:\Documents and Settings\Graham\My Documents\data\MScanner")
source_dir = mscanner_dir / "output"
outdir = path(r"C:\Documents and Settings\Graham\My Documents\temporary")


rc("figure", figsize=(8,6), dpi=100)
rc("figure.subplot", hspace=0.3)
rc("font", family="serif", serif="cmr10", monospace="cmtt10")
rc("legend", axespad=0.04, labelsep=0.015, pad=0.2)
rc("lines", linewidth=1.0)
rc("savefig", dpi=100)
rc("xtick.major", pad=6.0)
rc("ytick.major", pad=6.0)


def smooth(x, y, xn=npoints):
    """Resample a curve (x,y) using interpolation. xn is either a float with the
    new number of x value to evaluate the curve at, or an array of x values.
    """
    X = xn
    if not isinstance(X, arraytype):
        X = linspace(x[0], x[-1], xn)
    import scipy.interpolate
    interpolator = scipy.interpolate.interp1d(x, y, bounds_error=False)
    Y = interpolator(X)
    return X, Y


def read_featscores(indir, dataset):
    """Read feature scores for a dataset"""
    with open(indir/dataset/mrc.report_term_scores, "r") as f:
        f.readline()
        return array([float(s.split(",",1)[0]) for s in f])


def load_stats(indir, dataset, title, alpha=0.5):
    """Read statistics based on score data
    
    @param indir: Directory in which to find data sets
    @param dataset: Subdirectory name for the particular data set
    @param title: Name to put on the graphs (typically same as dataset)
    @param alpha: What alpha to use when recalcing performance
    """
    logging.info("Reading dataset %s", dataset)
    if not (indir/dataset).isdir():
        raise ValueError("Could not directory %s" % (indir/dataset)) 
    pscores = array([s[0] for s in iofuncs.read_scores(
        indir/dataset/mrc.report_positives)])
    nscores = array([s[0] for s in iofuncs.read_scores(
        indir/dataset/mrc.report_negatives)])
    stats = PerformanceVectors(pscores, nscores, alpha)
    stats.title = title
    stats.threshold, idx = stats.threshold_maximising(stats.FMa)
    stats.tuned = stats.metrics_for(idx)
    return stats


def gplot(x, y, ls, label, pos=0.6, usemarker=False):
    """Wraps plot to add a single marker marker instead of lots"""
    if usemarker:
        i = int(pos*len(x))
        plot(x,y,ls[0:2])
        plot([x[i]],[y[i]],ls,label=label)
    else:
        plot(x,y,ls[0:2],label=label)


def custom_show(fname, doshow=interactive, type="eps"):
    """Either shows an interactive plot, or writes to EPS followed by
    convertion to PDF (since matplotlib's PDF backend is buggy)"""
    if interactive: 
        show()
    try:
        fullname = outdir/fname + "." + type
        savefig(fullname)
        if type == "eps":
            from subprocess import call
            call(["epstopdf", fullname], shell=True)
            import os
            os.remove(fullname)
    finally:
        close()


def plot_score_density(fname, statlist):
    """Plots four score density plots in a grid

    @param statlist: A tuple of a four PerformanceVectors objects
    """
    logging.info("Plotting score densities to %s", fname)
    for idx, s in enumerate(statlist):
        px, py = DensityPlotter.gaussian_kernel_pdf(s.pscores)
        nx, ny = DensityPlotter.gaussian_kernel_pdf(s.nscores)
        subplot(2,2,idx+1)
        title(s.title)
        line_pos, = plot(px, py, color='red', label=r"Relevant")
        line_neg, = plot(nx, ny, color='blue', label=r"Irrelevant")
        line_threshold = axvline(
            s.uscores[s.bep_index], color='green', linewidth=1, label=r"Threshold")
        if idx == 0 or idx == 2:
            ylabel("Probability density")
        if idx == 2 or idx == 3:
            xlabel("Article score")
        if idx == 0:
            legend(loc="upper left")
    custom_show(fname)



def plot_score_histogram(fname, pscores, nscores):
    """Plot histograms for pos/neg scores, with line to mark threshold"""
    logging.info("Plotting article score histogram to %s", fname)
    ##title("Article Score Histograms")
    xlabel("Article Score")
    ylabel("Article Density")
    p_n, p_bins, p_patches = hist(pscores, bins=Plotter.bincount(pscores), normed=True)
    n_n, n_bins, n_patches = hist(nscores, bins=Plotter.bincount(nscores), normed=True)
    setp(p_patches, 'facecolor', 'r', 'alpha', 0.50, 'linewidth', 0.0)
    setp(n_patches, 'facecolor', 'b', 'alpha', 0.50, 'linewidth', 0.0)
    #p_y = normpdf(p_bins, mean(pscores), std(pscores))
    #n_y = normpdf(n_bins, mean(nscores), std(nscores))
    #p_l = plot(p_bins, p_y, 'r--', label=r"$\rm{Relevants}$")
    #n_l = plot(n_bins, n_y, 'b--', label=r"$\rm{Irrelevant}$")
    custom_show(fname)


def plot_featscore_histogram(fname, fscores):
    """Plot histogram for individual feature scores"""
    logging.info("Plotting feature score histogram to %s", fname)
    ##title("Feature Score Histogram")
    xlabel("Feature Score")
    ylabel("Number of Features")
    fscores.sort()
    n, bins, patches = hist(fscores, bins=Plotter.bincount(fscores))
    setp(patches, 'facecolor', 'r', 'linewidth', 0.0)
    custom_show(fname)


def plot_roc(fname, statlist):
    """Plots ROC curves overlayed"""
    logging.info("Plotting ROC grid to %s", fname)
    figure(figsize=(10,5))
    formats = ["r-s", "b-D", "g-h", "c-"]
    values = [smooth(s.TPR[::-1], s.FPR[::-1]) for s in statlist]
    # Plot complete ROC curve
    subplot(121)
    ##title(r"ROC curves")
    ylabel(r"True Positive Rate (Recall)")
    xlabel(r"False Positive Rate (1-Specificity)")
    for (TPR, FPR), fmt  in zip(values, formats):
        plot(FPR, TPR, fmt[0:2])
    axis([0.0, 1.0, 0.0, 1.0])
    # Plot zoomed in ROC curve
    subplot(122)
    ##title(r"Magnified ROC")
    xlabel(r"False Positive Rate (1-Specificity)")
    for (TPR, FPR), fmt, s  in zip(values, formats, statlist):
        plot(FPR, TPR, fmt[0:2], label=s.title)
    legend(loc="lower right")
    axis([0.0, 0.01, 0, 1.0])
    custom_show(fname)


def plot_precision(fname, statlist):
    """Plots PR curves overlayed"""
    logging.info("Plotting PR curve to %s", fname)
    ##title(r"Precision versus Recall")
    ylabel(r"Precision")
    xlabel(r"Recall")
    # Dotted line for break-even point
    plot([0.0, 1.0], [0.0, 1.0], "k:")
    # Pairs of TPR and PPV vectors for plotting
    formats = ["r-s", "b-D", "g-h", "c-o"]
    for s, fmt in zip(statlist, formats):
        TPR, PPV = smooth(s.TPR[::-1], s.PPV[::-1])
        gplot(TPR, PPV, fmt, label=r"$\rm{"+s.title+r"}$", pos=0.5)
    # Place X marks at threshold
    #plot([s.tuned.TPR for s in statlist], 
    #     [s.tuned.PPV for s in statlist],
    #     "kx", markeredgewidth=2)
    # Draw legends
    legend(loc=(0.5, 0.15))
    axis([0.0, 1.0, 0.0, 1.0])
    custom_show(fname)


#### FUNCTIONS THAT USE THE ABOVE ####

def do_iedb(fname):
    """Plots retrieval test results for 20% of PharmGKB to see how MScanner
    and PubMed compare at retrieving the remaining 80%.
    """
    logging.info("Plotting Retrieval curve for PG07")
    indir = source_dir / "11.21 IEDB Query"
    iedb_precision = 0.306415
    lines = (indir/"perf_vs_rank.txt").lines()
    N = len(lines)
    precision = zeros(N, Float32)
    recall = zeros(N, Float32)
    ranks = zeros(N, Int32)
    for i, line in enumerate(lines):
        if i == 0: continue
        _rank, _TP, _rec, _prec = line.strip().split(", ")
        #print _rank, _TP, _rec, _prec
        ranks[i] = int(_rank)
        recall[i] = float(_rec)
        precision[i] = float(_prec)
    ylabel(r"Precision, Recall")
    xlabel(r"Rank")
    plot(ranks, recall, "r", label="MScanner recall")
    plot(ranks, precision, "b", label="MScanner precision")
    plot(ranks, ranks/N, 'c', label="IEDB query recall")
    plot(ranks, zeros(N)+iedb_precision, 'g', label="IEDB query precision")
    # Draw legends
    legend(loc=(0.05, 0.7))
    axis([0.0, N, 0.0, 1.0])
    custom_show(fname)


def do_publication():
    """Draws figures for the BMC paper: including densities, ROC curve, PR
    curve, and PRF curve. """
    indir = source_dir / "11.21 Cross Validation"
    aidsbio = load_stats(indir, "aidsbio", "AIDSBio")
    radiology = load_stats(indir, "radiology", "Radiology")
    pg07 = load_stats(indir, "pg07", "PG07")
    control = load_stats(indir, "control", "Control")
    all = (aidsbio, radiology, pg07, control)
    #plot_score_density("fig3_density", all)
    plot_roc("fig4_roc", all)
    #plot_precision("fig5_pr", all)



def do_testplots():
    """Tests the plot functions using some old smaller datasets"""
    global indir
    indir = source_dir / "Old Validation" / "070223 CV10 Daniel 2s"
    if not indir.isdir():
        raise ValueError("Cannot find %s" % indir)
    pg04 = load_stats(indir, "pg04-vs-30k", "PG04")
    pg07 = load_stats(indir, "pg07-vs-30k", "PG07")
    plot_score_density("test_density", (pg04,pg07,pg07,pg04))
    plot_roc("test_roc", (pg04,pg07))
    plot_precision("test_pr", (pg04,pg07))



def do_subdirplots(subdirs):
    """Plots selected graphs for the datasets passed as parameters"""
    statlist = [load_stats(source_dir/path(d), d, d) for d in subdirs]
    fscores = [read_featscores(source_dir/path(d), d) for d in subdirs]
    #plot_score_density("cus_density", stats)
    #plot_roc("cus_roc", statlist)
    #plot_precision("cus_pr", statlist)
    for stats, fscores in zip(statlist, fscores):
        #plot_fmeasure("cus_%s_prf" % stats.title, stats)
        plot_score_histogram(
            "cus_%s_arthist" % stats.title, stats.pscores, stats.nscores)
        plot_featscore_histogram(
            "cus_%s_feathist" % stats.title, fscores)


if __name__ == "__main__":
    iofuncs.start_logger(logfile=False)
    if len(sys.argv) != 2:
        print "Please provide a Python expression"
    else:
        eval(sys.argv[1])
    logging.shutdown()
