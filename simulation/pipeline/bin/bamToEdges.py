#!/usr/bin/env python
#
# Convert a SAM file to edge CSV file suitable for importing into Gephi
#
# There is an assumption that read names contain 'fwd' or 'rev' as a suffix.
#
# Eg. frg01fwd or frg9999rev
#
import math
import pysam
import argparse
import re
import sys
import networkx as nx


class Edge:
    """Represents an edge in the network of contigs linked
    by Hi-C read pairs.
    """

    def __init__(self, nodes=[]):
        nodes.sort()
        self.nodes = nodes
        self.weight = 1

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.nodes[0] == other.nodes[0] and self.nodes[1] == other.nodes[1]

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return '{source} {target} {weight} {normweight}'.format(
                source=self.nodes[0].id,
                target=self.nodes[1].id,
                weight=str(self.weight),
                normweight=str(self.norm_weight()))

    def inc_weight(self):
        self.weight += 1

    def get_id(self):
        return self.nodes[0].id + self.nodes[1].id

    def norm_weight(self):
        return self.weight / math.sqrt(self.nodes[0].length * self.nodes[1].length)


class Node:
    """Represents a node in the network
    """

    def __init__(self, id, length, reads):
        self.id = id
        self.length = length
        self.reads = reads

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.id < other.id

    def __gt__(self, other):
        return self.id > other.id

    def __le__(self, other):
        return self.id <= other.id

    def __ge__(self, other):
        return self.id >= other.id

    def __str__(self):
        return '{id} {length} {reads}'.format(
            id=self.id, length=self.length, reads=self.reads)


def update_linkage_map(l):
    """Parse the line for new information about contig linkages. These
    may be self-self linkages or between inter-contig.
    """
    field = l.rstrip('\n').lstrip().split()
    read = field[0][:-3]
    rdir = field[0][-3:]
    contig = field[2]
    linkage = linkage_map.get(read)
    if linkage is None:
        linkage_map[read] = [(contig, rdir)]
    else:
        linkage.append((contig, rdir))


# Filter lines beginning with '@' and any line where the
# subject sequence is listed as '*'.
def filter(line):
    if line.startswith('@'): return True
    fields = line.rsplit()
    if fields[2] == '*': return True
    return False

def split_name(query_name):
    """
    Following our HiC naming convention, split query names into their
    components: (id, direction)

    :param query_name: query name to split
    :return: (id, direction)
    """
    return query_name[:-3], query_name[-3:]

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Create edge and node tables from a HiC bam file')
    parser.add_argument('--recover-alts', action='store_true', default=False,
                        help='Recover the alternate alignments from BAM')

    parser.add_argument('--afmt', choices=['bam', 'psl'], default='bam', help='Alignment file format (bam)')
    parser.add_argument('--minid', type=float, required=False, default=95.0,
                        help='Minimum percentage identity for alignment (95)')
    parser.add_argument('--minlen', type=int, required=False, default=1000,
                        help='Minimum length in bp (1000)')
    parser.add_argument('--mincov', type=float, required=False, default=0.5,
                        help='Minimum coverage of query by alignment (0.5)')

    #parser.add_argument('--wgs', dest='wgs2ctg', metavar='WGS_BAM', nargs=1, help='WGS reads to contigs bam file')
    parser.add_argument('-s', '--add-selfloops', action='store_true', default=False,
                        help='Add self-loops to nodes')
    parser.add_argument('--graphml', nargs=1, help='Write graphml file')
    parser.add_argument('hic2ctg', metavar='HIC_BAM', nargs=1, help='HiC to contigs bam file')
    parser.add_argument('edge_csv', metavar='EDGE_CSV', nargs=1, help='Edges csv output file')
    parser.add_argument('node_csv', metavar='NODE_CSV', nargs=1, help='Nodes csv output file')
    args = parser.parse_args()

    # TODO We dont need to reference this file.
    # TODO If a scaffold does appear in HiC data then it is not correct to introduce it.

    g = nx.Graph()
    linkage_map = {}

    # input is a BAM file
    if args.afmt == 'bam':

        with pysam.AlignmentFile(args.hic2ctg[0], 'rb') as bam_file:
            for n, rn in enumerate(bam_file.references):
                g.add_node(rn, length=bam_file.lengths[n])

        # Read the sam file and build a linkage map
        with pysam.AlignmentFile(args.hic2ctg[0], 'rb') as bam_file:
            iter_bam = bam_file.fetch()
            for mr in iter_bam:

                contig_set = set()

                if mr.reference_id == -1:
                    continue

                # assumed naming convention of HiC simulated reads.
                #read = mr.query_name[:-3]
                #rdir = mr.query_name[-3:]
                read, rdir = split_name(mr.query_name)

                # We depend on read naming from HiC simulator
                # this could be changed if the simulator tool created
                # read names with conventional Illumina FastQ headers.
                if not (rdir == 'fwd' or rdir == 'rev'):
                    raise RuntimeError('Reads in alignment file do not conform to expected convention '
                                        '[a-zA-Z]+[0-9]+(fwd|ref)')

                # contig this alignment line refers to directly
                contig_set.add(bam_file.getrname(mr.reference_id))

                # if requested, add also alternate alignment contigs for linkage map
                if args.recover_alts:
                    try:
                        # XA field contains alternate alignments for read, semi-colon delimited
                        alts_field = mr.get_tag('XA')
                        hit_list = alts_field.split(';')
                        # for each, get the contig name (first element of comma-sep list)
                        for hit in hit_list:
                            hrec = hit.split(',')
                            if len(hrec) != 4:
                                continue
                            contig_set.add(hrec[0])
                    except KeyError:
                        pass

                ctg_assocs = [(ctg, rdir) for ctg in contig_set]

                linkage = linkage_map.get(read)
                if linkage is None:
                    linkage_map[read] = ctg_assocs
                else:
                    linkage.extend(ctg_assocs)

    # input is a PSL file
    elif args.afmt == 'psl':

        if args.recover_alts:
            print 'Recovering alternate alignments is only applicable to BAM file parsing'
            sys.exit(1)

        # line marks a non-header line
        psl_dataline = re.compile(r'^[0-9]+\t')

        with open(args.hic2ctg[0], 'r') as h_in:
            for line in h_in:

                # skip header fields
                if not psl_dataline.match(line):
                    continue

                fields = line.rsplit()

                #qname = fields[9]
                # assumed naming convention of HiC simulated reads.
                read, rdir = split_name(fields[9])

                contig = fields[13]
                alen = int(fields[12]) - int(fields[11]) + 1
                qlen = int(fields[10])

                # Taken from BLAT perl script for calculating percentage identity
                matches = int(fields[0])
                mismatches = int(fields[1])
                repmatches = int(fields[2])
                q_num_insert = int(fields[4])
                perid = (1.0 - float(mismatches + q_num_insert) / float(matches + mismatches + repmatches)) * 100.0

                if not g.has_node(contig):
                    g.add_node(contig, length=int(fields[14]))

                # ignore alignment records which fall below mincov or minid
                # wrt the length of the alignment vs query sequence.
                if float(alen)/float(qlen) < args.mincov or perid < args.minid:
                    continue

                linkage = linkage_map.get(read)
                if linkage is None:
                    linkage_map[read] = [(contig, rdir)]
                else:
                    linkage.append((contig, rdir))

    # From the set of all linkages, convert this information
    # into inter-contig edges, where the nodes are contigs.
    # Count the number of redundant links as a raw edge weight.
    edge_map = {}
    for (insert, linkage) in linkage_map.iteritems():
        for i in range(len(linkage)):
            for j in range(i):

                # networkx based construction
                u, ud = linkage[i]
                v, vd = linkage[j]
                if g.has_edge(u, v):
                    g[u][v]['weight'] += 1
                else:
                    g.add_edge(u, v, weight=1)

    # insure that there is a self-loop to each node.
    if args.add_selfloops:
        for v in g.nodes():
            if not g.has_edge(v, v):
                g.add_edge(v, v, weight=1)

    if args.graphml is not None:
        nx.write_graphml(g, args.graphml[0])

    with open(args.edge_csv[0], 'w') as h_out:
        h_out.write("SOURCE TARGET RAWWEIGHT TYPE\n")
        for u, v, dat in g.edges(data=True):
            h_out.write('{0} {1} {2} UNDIRECTED\n'.format(u, v, dat['weight']))

    with open(args.node_csv[0], 'w') as h_out:
        h_out.write('ID LENGTH\n')
        for v, dat in g.nodes(data=True):
            h_out.write('{0} {1[length]}\n'.format(v, dat))
