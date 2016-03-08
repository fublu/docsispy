#!/usr/bin/python3
# vim: set fileencoding=utf-8
# (c) © 2016 Xavier Lüthi xavier@luthi.eu


from ch6643e import ch6643e
from datetime import datetime
import csv
import os
import json
from multiprocessing import Pool, Queue
import logging

class poller:
    """
    Based on an ip.txt input file, it query all modems and produce a CSV file
    """
    def __init__(self, ip_file = 'ip.txt', threads = os.cpu_count(), read_community = 'public', cachedb = None):
        self.ip_file   = ip_file
        self.threads   = threads
        self.timestamp = datetime.today()
        
        self.ip_fieldnames      = ['bpid', 'mac', 'ip']
        self.read_community     = read_community
        self.cachedb = cachedb
        self.traces = logging.getLogger('traces')
        
    def __debug(self,msg):
        self.traces.debug(msg)
    
    def _open_output_file(self):
        self.out_filename = 'results_{}.txt'.format(self.timestamp.strftime('%Y%m%d-%H%M%S'))
        self.out = open(self.out_filename + '.ongoing' , 'w')
        
    def _close_output_file(self):
        self.out.close()
        os.rename(self.out_filename + '.ongoing', self.out_filename)
    
    def query_all_ip(self):
        """
        Open output file, and query every line of the IP input file
        
        Mono-process
        """
        self.__debug("Start of poller.query_all_ip - mono-thread")
        self._open_output_file()
        
        with open(self.ip_file, 'r') as csvfile:
            csvreader = csv.DictReader(csvfile, fieldnames = self.ip_fieldnames, delimiter = ';')
            for line in csvreader:
                entity = { 'read_community': self.read_community, 'ip': line['ip'], 'bpid': line['bpid'], 'mac': line['mac'], 'cachedb': self.cachedb, 'output_file': self.out }
                query_one_modem(entity)
#                self.out.write(query_one_modem(entity) + '\n')
#                modem = ch6643e(hostname = line['ip'],
#                    community = self.read_community,
#                    bpid = line['bpid'])
#                modem.query_all()
#                self.out.write(modem.get_legacy_csv_line() + '\n')
        
        self._close_output_file()
        
    def query_all_ip_multithread(self):
        """
        Same as method query_all_ip, but with multithread support
        """
        self.__debug("Start of poller.query_all_ip_multithreads with {} processes".format(self.threads))
        self._open_output_file()
        in_q= []
        out_q = Queue()
        with open(self.ip_file, 'r') as csvfile:
            csvreader = csv.DictReader(csvfile, fieldnames = self.ip_fieldnames, delimiter = ';')
            for line in csvreader:
                entity = { 'read_community': self.read_community, 'ip': line['ip'], 'bpid': line['bpid'], 'mac': line['mac'], 'cachedb': self.cachedb}
                in_q.append(entity)
        self.__debug(in_q)
        worker_pool = Pool(processes = self.threads)
        worker_pool.map_async(query_one_modem, in_q, callback = out_q.put)
        self.__debug("Wait for worker_pool to close...")
        worker_pool.close()
        self.__debug("Closed. Waiting for all processes to finish...")
        worker_pool.join()
        self.__debug("Worker_pool finished")

        for line in out_q.get():
            self.out.write(line)
        
        self._close_output_file()
        
    def query_all(self):
        if self.threads > 1:
            return self.query_all_ip_multithread()
        else:
            return self.query_all_ip()
        

# Functions for multiprocessing
def query_one_modem(entity):
    print("query one modem")
    community = entity['read_community']
    ip = entity['ip']
    bpid = entity['bpid']
    mac = entity['mac']
    cachedb = entity['cachedb']

    traces = logging.getLogger('traces')
    traces.debug('query_one_modem: for modem {} (mac: {})'.format(ip, mac))
    modem = ch6643e(hostname = ip, community = community, bpid = bpid, mac = mac)
    modem.query_all()
    if cachedb and modem.state == 'completed':
        cachedb.compute_usage(modem)
    
    #output_file.write(modem.get_legacy_csv_line() + '\n')
    return modem.get_legacy_csv_line() + '\n'






