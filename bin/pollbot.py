import json
import argparse

def load_json_config(filename):
    with open('docsispy.conf') as data_file:    
        config = json.load(data_file)
    return config
    
    
if __name__ == "__main__":
        
    parser = argparse.ArgumentParser(description="Produces one CSV line giving the status of one modem.")
    parser.add_argument('--verbose', '-v', action='count', help='Verbose output.')
    parser.add_argument('--debug', '-d', action='count', help='Debug output with kind of traces.')
    parser.add_argument('--no-usage','-u', dest="usage", action="store_false", help="Do not compute usage in bytes. By default it computes the usage by comparing the current counter value with the previous one. If the flag is set, it will not store the fetched value in cache neither.")
    parser.add_argument('--config', '-c', dest="config_file", help='configuration file to use. By default, it looks for docsispy.conf in the current directory.')
    parser.set_defaults(usage=True)
    parser.set_defaults(config_file="docsispy.conf")

    args = parser.parse_args()
    #print args
    
    config = load_json_config(args.config_file)
    
    pollbotrc = config["pollbot"]

    for arr in pollbotrc["oid"]:
        print "{:20} - {}".format(arr[0], arr[2])
