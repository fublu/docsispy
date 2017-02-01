#!/usr/bin/python3
# vim: set fileencoding=utf-8
# (c) © 2016-2017 Xavier Lüthi xavier@luthi.eu

"""
Main program to launch the poller class

For command line argument, use the "--help" option.
"""

from poller import poller
from cache  import cachedb
import argparse, json, multiprocessing
import logging, logging.handlers
from datetime import datetime
from os.path import expanduser

def init_traces(level):
    """
    Create a generic logger called 'traces'.
    No particular output handler is created (yet).

    :param level: logging level (logging{DEBUG, INFO,...}
    """
    traces = logging.getLogger('traces')
    traces.setLevel(level)

def activate_log_file(level, filename):
    """
    Attach a file Handler to the generic logger 'traces'

    :param filemane: filename to be used.
    :param level: logging level (DEBUG, ERROR...)
    """
    traces = logging.getLogger('traces')
    fh = logging.handlers.RotatingFileHandler(filename,
         mode='a', maxBytes=1024*1024*10, backupCount=10, encoding='utf-8')
    fh.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(filename)s - %(funcName)s() - %(levelname)s: %(message)s')
    fh.setFormatter(formatter)
    traces.addHandler(fh)

def load_json_config(filename):
    """
    Load the JSON configuration file

    :param filename: the configuration filename with path

    :return: an object representing the read configuration.
    """
    with open(filename) as data_file:
        config = json.load(data_file)
    return config

def manage_cli_arguments():
    """
    Command line argument definition and parsing.
    Activate logfile if debug or verbose is set.

    :return: an array with the parsed arguments and values.
    """
    parser = argparse.ArgumentParser(
        description="Produces one CSV line giving the status of one modem.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--verbose', '-v', action='count', help='Verbose output.')
    parser.add_argument('--debug',   '-d', action='count', help=
        'Debug output with kind of traces.')
    parser.add_argument('--no-usage','-u', dest="usage", action="store_false", help="""
        Do not compute usage in bytes. By default it computes the usage by
        comparing the current counter value with the previous one. If the flag
        is set, it will not store the fetched value in cache neither.""")
    parser.add_argument('--config',  '-c', dest="config_file", help="""
        configuration file to use.""")
    parser.add_argument('--parallel', '-p', type=int, help="Number of queries to run in parallel. The default is the number of available CPU")
    parser.add_argument('--cachedb', '-s', help="file to be used for the cache database. It is an sqlite3 database")
    parser.add_argument('--output', '-o', help="Output file")
    parser.add_argument('ipfile', help="""file containing modem to be queried. Format is one modem per line:
          bpid;mac;private_ip.
          Example: 0091000060;5c353bef6106;10.133.28.103""")

    # Default values
    parser.set_defaults(usage=True)
    parser.set_defaults(config_file= "{}/.docsispy/docsispy.secret".format(expanduser("~")))
    parser.set_defaults(parallel = multiprocessing.cpu_count())
    parser.set_defaults(cachedb = "{}/.docsispy/docsispy.db".format(expanduser("~")))
    parser.set_defaults(output = 'results_{}.txt'.format(datetime.today().strftime('%Y%m%d-%H%M%S')) )
    args = parser.parse_args()

    if args.debug:
        activate_log_file(logging.DEBUG, "launch_poller.log")
    if args.verbose:
        traces = logging.getLogger('traces')
        traces.setLevel(logging.DEBUG)
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        traces.addHandler(sh)
        traces.debug("Debug mode activated")
    return args



if __name__ == '__main__':
    init_traces(logging.DEBUG)
    activate_log_file(logging.ERROR, "launch_poller-error.log")
    traces = logging.getLogger('traces')
    args = manage_cli_arguments()
    traces.info("Start of the program")
    config = load_json_config(args.config_file)

    poller = poller(ip_file = args.ipfile, processes = args.parallel,
                read_community = config['read_community'], output_file = args.output)

    if args.usage:
        cache = cachedb(file_name = args.cachedb)
        poller.cachedb = cache

    traces.debug("Config: %s", config)

    poller.query_all()
