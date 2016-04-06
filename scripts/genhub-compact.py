#!/usr/bin/env python
#
# -----------------------------------------------------------------------------
# Copyright (c) 2016   Daniel Standage <daniel.standage@gmail.com>
# Copyright (c) 2016   Indiana University
#
# This file is part of genhub (http://github.com/standage/genhub) and is
# licensed under the BSD 3-clause license: see LICENSE.txt.
# -----------------------------------------------------------------------------

from __future__ import print_function
from __future__ import division
import argparse
import pandas
import re
import sys
import genhub


def cli():
    """Define the command-line interface of the program."""
    desc = 'Calculate measures of compactness for the specified genome(s).'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-v', '--version', action='version',
                        version='GenHub v%s' % genhub.__version__)
    parser.add_argument('-c', '--cfgdir', default=None, metavar='DIR',
                        help='directory (or comma-separated list of '
                        'directories) from which to load user-supplied genome '
                        'configuration files')
    parser.add_argument('-w', '--workdir', metavar='WD', default='./species',
                        help='working directory for data files; default is '
                        '"./species"')
    parser.add_argument('-l', '--length', metavar='LEN', type=int,
                        default=1000000, help='minimum length threshold; '
                        'default is 1000000 (1Mb)')
    parser.add_argument('species', nargs='+', help='species label(s)')
    return parser


def thresholds(seqid, iloci, iqnt=0.95, gqnt=0.05):
    seqloci = iloci.loc[iloci.SeqID == seqid]
    ithresh = None
    if iqnt:
        iiloci = seqloci.loc[seqloci.LocusClass == 'iiLocus']
        ithresh = int(iiloci['Length'].quantile(iqnt))
    gthresh = None
    if gqnt:
        gilocus_types = ['siLocus', 'ciLocus', 'niLocus']
        giloci = seqloci.loc[seqloci.LocusClass.isin(gilocus_types)]
        gthresh = int(giloci['Length'].quantile(iqnt))
    return ithresh, gthresh


def seqlen(seqid, iloci, ithresh=None, gthresh=None):
    seqloci = iloci.loc[(iloci.SeqID == seqid) &
                        (seqloci.LocusClass != 'fiLocus')]
    effsize = seqloci['EffectiveLength'].sum()
    if ithresh:
        longiiloci = seqloci.loc[(seqloci.LocusClass == 'iiLocus') &
                                 (seqloci.Length > ithresh)]
        effsize -= longiiloci['Length'].sum()
    if gthresh:
        gilocus_types = ['siLocus', 'ciLocus', 'niLocus']
        shortgiloci = seqloci.loc[(seqloci.LocusClass.isin(gilocus_types)) &
                                  (seqloci.Length < gthresh)]
        effsize -= shortgiloci['Length'].sum()
    return effsize


def calc_phi(seqid, iloci, miloci):
    gilocus_types = ['siLocus', 'ciLocus', 'niLocus']
    giloci = iloci.loc[(iloci.SeqID == seqid) &
                       (iloci.LocusClass.isin(gilocus_types))]
    singletons = miloci.loc[(miloci.SeqID == seqid) &
                            (miloci.LocusClass.isin(gilocus_types))]
    if gthresh:
        giloci = giloci.loc[giloci.Length >= gthresh]
        singletons = singletons.loc[singletons.Length >= gthresh]
    merged = len(giloci) - len(singletons)
    return merged / len(giloci)


def main(args):
    print('Species', 'SeqID', 'Sigma', 'Phi', sep='\t')

    registry = genhub.registry.Registry()
    if args.cfgdir:
        for cfgdirpath in args.cfgdir.split(','):
            registry.update(cfgdirpath)
    conf = registry.genomes(args.species)

    for species in args.species:
        config = conf[species]
        db = genhub.genomedb.GenomeDB(species, config, workdir=args.workdir)
        iloci = pandas.read_table(db.ilocustable)
        miloci = pandas.read_table(db.milocustable)
        for seqid in iloci['SeqID']:
            ithresh, gthresh = thresholds(seqid, iloci)
            length = seqlen(seqid, iloci, ithresh, gthresh)
            phi = calc_phi(seqid, iloci, miloci)
            milocus_occ = miloci.loc[miloci.SeqID == seqid]['Length'].sum()
            sigma = milocus_occ / length
            print(species, seqid, sigma, phi, sep='\t')

if __name__ == '__main__':
    main(args=cli().parse_args())
