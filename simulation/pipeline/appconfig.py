import yaml
import sys
import os.path
import glob


def read(file_name):
    """
    Read the application configuration file (YAML format), exits
    on IOError.

    :param file_name: configuration file path
    :return: yaml configuration object
    :
    """
    try:
        with open(file_name, 'r') as h_cf:
            return yaml.load(h_cf)
    except IOError as e:
        print e
        sys.exit(e.errno)


def get_communities(config):
    """
    Return the list of community folders
    :param config: application config object
    :return: list of community folders
    """
    return [os.path.abspath(dn) for dn in glob.glob(config['community']['folder'] + '/*')]


def get_wgs_reads(path, config):
    """
    Return the pair of generated WGS files for a given community
    :param path: containing path of WGS reads
    :param config: application config object
    :return: list of read files (R1, R2)
    """
    return [os.path.join(path, '{0}{1}.fq'.format(config['wgs_base'], n)) for n in range(1, 3)]