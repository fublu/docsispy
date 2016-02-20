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
    parser = argparse.ArgumentParser(description="Produces one CSV line giving the status of one modem.")
    parser.add_argument('--verbose', '-v', action='count', help='Verbose output.')
    parser.add_argument('--debug',   '-d', action='count', help='Debug output with kind of traces.')
    parser.add_argument('--no-usage','-u', dest="usage", action="store_false", help="""
        Do not compute usage in bytes. By default it computes the usage by 
        comparing the current counter value with the previous one. If the flag 
        is set, it will not store the fetched value in cache neither.""")
    parser.add_argument('--config',  '-c', dest="config_file", help="""
        configuration file to use. By default, it looks for docsispy.conf in 
        the current directory.""")
    parser.set_defaults(usage=True)
    parser.set_defaults(config_file="../conf/docsispy.conf")
    parser.add_argument('ip', help="private ip address of the modem to query")
    parser.add_argument('mac', help="""
        mac address of the modem. Example: dc537c19bc89. The provided MAC is 
        compared with the one fetched from the modem.""")
    parser.add_argument('bpid', help="""
        Unique customer reference. 
        Only used to add it on the result line.""")

    args = parser.parse_args()
    return args

    
if __name__ == "__main__":
        
    args = manage_cli_arguments()
    config = load_json_config(args.config_file)
    pollbotrc = config["pollbot"]
    
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
