from nestly import Nest, stripext
from nestly.scons import SConsWrap, name_targets
import os
import os.path
import appconfig

config = appconfig.read('config.yaml')

nest = Nest()
wrap = SConsWrap(nest, config['map_folder'])
env = Environment(ENV=os.environ)

# Used for resolving what type of execution environment will be used.
exec_env = appconfig.ExecutionEnvironment(ARGUMENTS, supported_env=['pbs', 'sge'])

# Constant
wrap.add('refseq', [config['community']['seq']], create_dir=False)

# Variation
genomes = appconfig.find_files(config['community']['folder'], config['community']['seq'])
# For testing - restrict to only star topology
#commPaths = [os.path.dirname(pn) for pn in genomes if 'ladder' not in pn]
commPaths = [os.path.dirname(pn) for pn in genomes]
wrap.add('community', commPaths)

tableFolder = os.path.join(config['reference']['folder'], config['reference']['table_folder'])
tablePaths = appconfig.get_files(tableFolder, 'table')
wrap.add('comm_table', tablePaths, label_func=os.path.basename)

wrap.add('wgs_xfold', config['wgs_xfold'])


@wrap.add_target('make_ctg2ref')
@name_targets
def make_ctg2ref(outdir, c):
    com = c['community']
    tbl = os.path.basename(c['comm_table'])

    query = os.path.join(
                os.path.abspath(config['wgs_folder']), com, tbl,
                str(c['wgs_xfold']), config['wgs_asmdir'],
                '{0[wgs_base]}.contigs.fasta'.format(config))

    subject = os.path.join(config['community']['folder'], com, config['community']['seq'])

    source = [subject, query]
    target = os.path.join(outdir, config['ctg2ref'])

    action = exec_env.resolve_action({
        'pbs': 'bin/pbsrun_LAST.sh $SOURCES.abspath $TARGET.abspath',
        'sge': 'bin/sgerun_LAST.sh $SOURCES.abspath $TARGET.abspath'
    })

    return 'output', env.Command(target, source, action)

@wrap.add_target('make_truth')
@name_targets
def make_truth(outdir, c):
    source = str(c['make_ctg2ref']['output'])
    target = os.path.join(outdir, config['truth_table'])

    action = exec_env.resolve_action({

        'pbs': 'bin/pbsrun_MKTRUTH.sh '
               '{1[ctg_afmt]} {1[ctg_ofmt]} {1[ctg_minlen]} {1[ctg_mincov]} {1[ctg_minid]} '
               '$SOURCES.abspath $TARGET.abspath'.format(c, config),

        'sge': 'bin/sgerun_MKTRUTH.sh '
               '{1[ctg_afmt]} {1[ctg_ofmt]} {1[ctg_minlen]} {1[ctg_mincov]} {1[ctg_minid]} '
               '$SOURCES.abspath $TARGET.abspath'.format(c, config)
    })

    return 'output', env.Command(target, source, action)


@wrap.add_target('make_wgs2ctg')
@name_targets
def make_wgs2ctg(outdir, c):
    com = c['community']
    tbl = os.path.basename(c['comm_table'])

    # TODO find a better way to obtain the path to WGS reads
    query = appconfig.get_wgs_reads(
                os.path.join(os.path.abspath(config['wgs_folder']),
                com, tbl, str(c['wgs_xfold'])),
                config)

    # TODO likewise
    subject = os.path.join(
                os.path.abspath(config['wgs_folder']),
                com, tbl, str(c['wgs_xfold']), config['wgs_asmdir'],
                '{0[wgs_base]}.contigs.fasta'.format(config))

    target = os.path.join(outdir, config['wgs2ctg'])
    source = [subject] + query

    action = exec_env.resolve_action({
        'pbs': 'bin/pbsrun_MAP.sh $SOURCES.abspath $TARGET.abspath',
        'sge': 'bin/sgerun_MAP.sh $SOURCES.abspath $TARGET.abspath'
    })

    return 'output', env.Command(target, source, action)


wrap.add('hic_n_frag', config['hic_n_frag'])

@wrap.add_target('make_hic2ctg')
@name_targets
def make_hic2ctg(outdir, c):
    com = c['community']
    tbl = os.path.basename(c['comm_table'])

    query = os.path.join(os.path.abspath(config['hic_folder']), com, tbl,
                         str(c['hic_n_frag']), '{0[hic_base]}.fasta'.format(config))
    subject = os.path.join(
                os.path.abspath(config['wgs_folder']), com, tbl,
                str(c['wgs_xfold']), config['wgs_asmdir'],
                '{0[wgs_base]}.contigs.fasta'.format(config))
    source = [subject, query]
    target = os.path.join(outdir, config['hic2ctg'])

    action = exec_env.resolve_action({
        'pbs': 'bin/pbsrun_MAP.sh $SOURCES.abspath $TARGET.abspath',
        'sge': 'bin/sgerun_MAP.sh $SOURCES.abspath $TARGET.abspath'
    })

    return 'output', env.Command(target, source, action)


wrap.add('hic_min_cov', [0, 0.5, 0.95])
wrap.add('hic_min_qual', [0, 30, 60])


@wrap.add_target('filter_hic2ctg')
@name_targets
def filter_hic(outdir, c):
    source = str(c['make_hic2ctg']['output'])
    target = os.path.join(outdir, config['hic2ctg'])
    action = exec_env.resolve_action({
        'pbs': 'bin/pbsrun_BAMFILTER.sh {0[hic_min_cov]} {0[hic_min_qual]} $SOURCE $TARGET'.format(c),
        'sge': 'bin/sgerun_BAMFILTER.sh {0[hic_min_cov]} {0[hic_min_qual]} $SOURCE $TARGET'.format(c)
    })
    return 'output', env.Command(target, source, action)


""" MOVING ALL OF THESE TO SEPARATE MAKE FILE

@wrap.add_target('make_graph')
@name_targets
def make_graph(outdir, c):
    hic_bam = str(c['filter_hic2ctg']['output'])
    wgs_bam = str(c['make_wgs2ctg']['output'])

    sources = [hic_bam, wgs_bam]
    target = prepend_paths(outdir, ['edges.csv', 'nodes.csv'])

    action = 'bin/pbsrun_GRAPH.sh $SOURCES.abspath $TARGETS.abspath'

    return 'edges', 'nodes', env.Command(target, sources, action)

#
#  Everything below here is MCL specific but should be made agnostic of algorithm
#  or deal with multiple algorithms in "cluster_method".
#
wrap.add('cluster_method', ['mcl', 'oclustr'])

@wrap.add_target('make_cluster_input')
@name_targets
def make_cluster_input(outdir, c):

    source = [str(c['make_graph']['edges']), str(c['make_graph']['nodes'])]
    target = prepend_paths(outdir, config['cluster']['input'])

    if c['cluster_method'] == 'mcl':
        action = 'bin/pbsrun_MKMCL.sh {1[ctg_minlen]} $SOURCES.abspath $TARGET.abspath'.format(c, config)

    elif c['cluster_method'] == 'oclustr':
        action = 'bin/edgeToMetis.py -m {1[ctg_minlen]} -f graphml $SOURCES.abspath $TARGET.abspath'.format(c, config)

    return 'output', env.Command(target, source, action)

mcl_param = config['cluster']['mcl_infl']
wrap.add('mcl_inflation', numpy.linspace(mcl_param['min'], mcl_param['max'], mcl_param['steps']))

@wrap.add_target('do_mcl')
@name_targets
def do_mcl(outdir, c):
    # TODO run over both weighted/unweighted?
    source = c['make_cluster_input']['output']
    target = prepend_paths(outdir, config['cluster']['output'])

    action = 'bin/pbsrun_MCL.sh {0[mcl_inflation]} $SOURCE.abspath $TARGET.abspath'.format(c)

    return 'output', env.Command(target, source, action)


@wrap.add_target('do_score')
def do_score(outdir, c):
    #cl_out = os.path.join(outdir, config['cluster']['output'])
    cl_out = c['do_mcl']['output']
    ttable = c['make_truth']['output']
    # this target consumes truth table and clustering output
    source = [ttable, cl_out]
    # this target creates 3 output files
    target = ['{0}.{1}'.format(cl_out, suffix) for suffix in ['f1', 'vm', 'bc']]

    action = 'bin/pbsrun_SCORE.sh $SOURCES.abspath'

    return env.Command(target, source, action)
"""

wrap.add_controls(Environment())
