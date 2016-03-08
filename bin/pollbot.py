#!/usr/bin/python3
import json
import argparse
import string
from easysnmp import Session
from datetime import datetime
import logging, logging.handlers
from binascii import hexlify

def init_traces(level):
    """
    Create a log file in the current working directory.
    The logger is called 'traces'
    
    :param level: logging level (logging{DEBUG, INFO,...}
    """
    traces = logging.getLogger('traces')
    traces.setLevel(level)
    fh = logging.handlers.RotatingFileHandler("pollbot.log",
         mode='a', maxBytes=1024*1024, backupCount=5, encoding='utf-8')
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
    parser.add_argument('--bot',     '-b', help="""
        The bot configuration to use. The configuration file may contains many
        bot configuration (daybot, pollbot...).""")
    parser.add_argument('ip', help="private ip address of the modem to query")
    parser.add_argument('mac', help="""
        mac address of the modem. Example: dc537c19bc89. The provided MAC is 
        compared with the one fetched from the modem.""")
    parser.add_argument('bpid', help="""
        Unique customer reference. 
        Only used to add it on the result line.""")

    parser.set_defaults(usage=True)
    parser.set_defaults(config_file="../conf/docsispy.conf")
    parser.set_defaults(bot='default')
    args = parser.parse_args()
    
    if args.debug:
        init_traces(logging.DEBUG)
    elif args.verbose:
        init_traces(logging.INFO)
    return args


def print_mac(src):
    traces = logging.getLogger('traces')
    traces.debug('Entry in print_mac')
    traces.debug('Length of src: {} ({}), type: {}'.format(len(src), src, type(src)))
    rtn = hexlify(src.encode('latin-1')).decode('latin-1')
    traces.debug('Length of rtn: {}, rtn = {}, type = {}'.format(len(rtn), rtn, type(rtn)))
    
    return rtn
    
    
def get_one_ip(botrc, ip = '127.0.0.1', community = 'public'):
    """
    Based on the botrc configuration, it performs ONE snmp get query with
    potentially many OID.
    
    :param botrc: a dict with one key "oids" containing an array of 
                  ["desc", "translated OID", "OID"] values.
    :param ip: the IP address of the SNMP client to query
    :param community: the SNMP read community.
    
    :return: a list of SNMPVariable objets (oid, value, snmp_type)
    """
    traces = logging.getLogger('traces')
    traces.debug("Entry in get_one_ip")
    traces.debug(botrc['oids'])
    session = Session(hostname=ip, community=community, version=2, timeout=10)
    get_oid  = []
    for arr in botrc['oids']:
        traces.debug("{:20} - {}".format(arr[0], arr[2]))
        get_oid += [arr[2]]
     
    get_res = session.get(get_oid)

    if traces.getEffectiveLevel() <= logging.INFO:
        for v in get_res:
            #traces.info("get {:20} --> {}".format(v.oid, v.value))
            traces.info(v)
    result_str = ';'.join([x.value for x in get_res])
    
#    bulk_res = session.get_bulk(bulk_oid, 0, 10) # TODO: fix default 10 value
#    print bulk_res
    
    return get_res
        
def getbulk_one_ip(botrc, ip = '127.0.0.1', community = 'public'):
    """
    For all OID in the botrc configuration, it performs one GetBulkRequest.
    
    :param botrc: a dict with one key "oids" containing an array of 
                  ["desc", "translated OID", "OID"] values.
    :param ip: the IP address of the SNMP client to query
    :param community: the SNMP read community.
    
    :return: a list of SNMPVariableList objets, each SNMPVariableList object
             referring to one input OID.  Every list contains SNMPVariable
             object(s)(oid, value, snmp_type), or even 0 if nothing is present
             in the SNMP tree.
    """
    traces = logging.getLogger('traces')
    traces.debug("Entry in getbulk_one_ip")
    traces.debug(botrc['oids'])
    
    session = Session(hostname=ip, community=community, version=2, timeout=10)
    get_oid  = []
    results = []
    for arr in botrc['oids']:
        traces.debug("{:20} - {}".format(arr[0], arr[2]))
        bulk_res =  session.get_bulk(arr[2], 0, 20)
        

    if traces.getEffectiveLevel() <= logging.INFO:
        for var_list in results:
            for v in var_list:
                traces.info(v)
                traces.info("get {:20} --> {}".format(v.oid, 
                    filter(lambda c: c in string.printable, v.value)))

    return results

def strip_non_printable(value):
    """
    /Copied from EasySNMP code/
    Removes any non-printable characters and adds an indicator to the string
    when binary characters are fonud
    :param value: the value that you wish to strip
    """
    if value is None:
        return None

    # Filter all non-printable characters
    # (note that we must use join to account for the fact that Python 3
    # returns a generator)
    printable_value = ''.join(filter(lambda c: c in string.printable, value))

    if printable_value != value:
        if printable_value:
            printable_value += ' '
        printable_value += '(contains binary)'

    return printable_value

def get_csv(var_list, ip, bpid):
    """
    Produce a CSV string from the input parameters.
    Assumption: first var in var_list is the MAC address.
    """
    result = "{};{};{};{}".format(datetime.today().strftime('%Y%m%d-%H%M%S'),
              bpid, print_mac(var_list[0].value) , ip)
    for v in var_list[1:]:
        if isinstance(v, list):
            if len(v)-2 <= 0:
                # no OID actually fetched
                result += ';0'
            else:
                list_str = "{};".format(len(v)-2)
                for var in v:
                    if var.snmp_type != 'ENDOFMIBVIEW':
                        list_str = list_str + strip_non_printable(var.value) + ':'
                result = result + ';' + list_str [:-1]            
        else:
            result = result + ';' + v.value
    return result
    

if __name__ == "__main__":
    
    traces = logging.getLogger('traces')    
    args = manage_cli_arguments()
    traces.info("Start of the program")
    config = load_json_config(args.config_file)
    
    traces.debug("Config: %s", config)
    
    pollbotrc = config[args.bot]
    
    result = []
    
    # Parse every queries group in turn.
    for query in pollbotrc['queries']:
        if query['type'] == 'get':
            result += get_one_ip(query, args.ip, 
                        config['general']['community_ro'])
        elif query['type'] == 'bulk':
            result += getbulk_one_ip(query, args.ip, 
                        config['general']['community_ro'])
                
    print(get_csv(result, args.ip, args.bpid))

