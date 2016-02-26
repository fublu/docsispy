#!/usr/bin/python
import json
import argparse
import netsnmp
from easysnmp import Session
from datetime import datetime

def load_json_config(filename):
    with open(filename) as data_file:
        config = json.load(data_file)
    return config

def manage_cli_arguments():
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
    parser.set_defaults(bot='counters')
    args = parser.parse_args()
    return args


def get_one_ip(botrc, ip = '127.0.0.1', community = 'public'):
    print botrc['oid']
    result_str = ""
#    result_dic = {}
    session = Session(hostname=ip, community=community, version=2)
    get_oid  = []
#    bulk_oid = []
    for arr in pollbotrc["oid"]:
        print "{:20} - {:40}  - {}".format(arr[0], arr[2], arr[3])
        if arr[1] == "get":
            get_oid += [arr[3]]
        elif arr[1] == "table":
            bulk_oid += [arr[3]]
     
    get_res = session.get(get_oid)
#    print get_oid
#    print get_res
#    for x in get_res:
#        result_dic[x.oid] = x.value
    result_str = ';'.join([x.value for x in get_res])
    
#    bulk_res = session.get_bulk(bulk_oid, 0, 10) # TODO: fix default 10 value
#    print bulk_res
    
    return result_str
        
def getbulk_one_ip(oid, ip = '127.0.0.1', community = 'public'):
    pass



if __name__ == "__main__":
        
    args = manage_cli_arguments()
    config = load_json_config(args.config_file)
    pollbotrc = config[args.bot]
    
    oid = []
    for arr in pollbotrc["oid"]:
        print "{:20} - {:40}  - {}".format(arr[0], arr[2], arr[3])
        oid += [arr[3]]
    result = "{};{};{};{}".format(datetime.today().strftime('%Y%m%d-%H%M%S'),
                                  args.bpid, args.mac, args.ip)
    session = Session(hostname= args.ip, community=config['general']['community_ro'], version=2)
    get_res = session.get(oid)
    
    result = result + ';' + ';'.join([x.value for x in get_res])
    #print("OID: {:40} - {}".format(x.oid, x.value))
    print(result)
    
    bulk_res = session.get_bulk([".1.3.6.1.2.1", ".1.3.6.1.2.1.1"], 0, 8)
    for item in bulk_res:
        print '{oid}.{oid_index} {snmp_type} = {value}'.format(
            oid=item.oid,
            oid_index=item.oid_index,
            snmp_type=item.snmp_type,
            value=item.value
        )
    get_one_ip(pollbotrc, args.ip, config['general']['community_ro'])
