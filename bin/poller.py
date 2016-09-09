#!/usr/bin/python3
# vim: set fileencoding=utf-8
# (c) © 2016 Xavier Lüthi xavier@luthi.eu


from ch6643e import ch6643e
from cache import cachedb
from datetime import datetime
import csv
import os
import json
import multiprocessing
from multiprocessing import Pool, Queue
import logging

class poller:
    """
    Based on an ip.txt input file, it query all modems and produce a CSV file
    """
    def __init__(self, ip_file = 'ip.txt', processes = multiprocessing.cpu_count(), 
                 read_community = 'public', cachedb = None, output_file = None):
        self.ip_file   = ip_file
        self.processes   = processes
        self.timestamp = datetime.today()
        
        self.ip_fieldnames      = ['bpid', 'mac', 'ip']
        self.read_community     = read_community
        self.cachedb = cachedb
        self.traces = logging.getLogger('traces')
        if output_file:
            self.out_filename = output_file
        else:
            self.out_filename = 'results_{}.txt'.format(self.timestamp.strftime('%Y%m%d-%H%M%S'))
        
    def __debug(self,msg):
        self.traces.debug(msg)
    
    def _open_output_file(self):
        self.out = open(self.out_filename + '.ongoing' , 'w')
        
    def _close_output_file(self):
        self.out.close()
        os.rename(self.out_filename + '.ongoing', self.out_filename)
    
    def query_all_ip(self):
        """
        Open output file, and query every line of the IP input file
        
        Mono-process
        """
        self.__debug("Start of poller.query_all_ip - mono-process")
        self._open_output_file()
        
        with open(self.ip_file, 'r') as csvfile:
            csvreader = csv.DictReader(csvfile, fieldnames = self.ip_fieldnames, delimiter = ';')
            for line in csvreader:
                entity = { 'read_community': self.read_community, 'ip': line['ip'], 'bpid': line['bpid'], 'mac': line['mac']}
                if (self.cachedb):
                    entity['do_cache'] = self.cachedb.file_name
                self.out.write(query_one_modem(entity))
#                modem = ch6643e(hostname = line['ip'],
#                    community = self.read_community,
#                    bpid = line['bpid'])
#                modem.query_all()
#                self.out.write(modem.get_legacy_csv_line() + '\n')
        
        self._close_output_file()
        
    def query_all_ip_multiprocesses(self):
        """
        Same as method query_all_ip, but with multiprocesses support
        """
        self.__debug("Start of poller.query_all_ip_multiprocesses with {} processes".format(self.processes))
        self._open_output_file()
        in_q= []
        out_q = Queue()
        with open(self.ip_file, 'r') as csvfile:
            csvreader = csv.DictReader(csvfile, fieldnames = self.ip_fieldnames, delimiter = ';')
            for line in csvreader:
                entity = { 'read_community': self.read_community, 'ip': line['ip'], 'bpid': line['bpid'], 'mac': line['mac']}
                if (self.cachedb):
                    entity['do_cache'] = self.cachedb.file_name
                in_q.append(entity)
        self.__debug(in_q)
        worker_pool = Pool(processes = self.processes)
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
        if self.processes > 1:
            return self.query_all_ip_multiprocesses()
        else:
            return self.query_all_ip()
        

# Functions for multiprocessing
def query_one_modem(entity):
    community = entity['read_community']
    ip = entity['ip']
    bpid = entity['bpid']
    mac = entity['mac']
    do_cache = entity['do_cache']

    traces = logging.getLogger('traces')
    traces.debug('query_one_modem (PID {}): for modem {} (mac: {})'.format(os.getpid(), ip, mac))
    modem = ch6643e(hostname = ip, community = community, bpid = bpid, mac = mac)
    modem.query_all()
    if do_cache and modem.state == 'completed':
        cache = cachedb(file_name = do_cache)
        cache.compute_usage(modem)
    
    #output_file.write(modem.get_legacy_csv_line() + '\n')
    return modem.get_legacy_csv_line() + '\n'






