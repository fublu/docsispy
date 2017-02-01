#!/usr/bin/python3
# vim: set fileencoding=utf-8
# (c) © 2016-2017 Xavier Lüthi xavier@luthi.eu

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

    :param ip_file: name of the ip.txt file to process
    :param processes: how many processes to fire in parallel
    :param timestamp: date and time of the creation of the object
    :param read_community: SNMP community string to use for read-only access
    :param cachedb: cachedb object to use for usage computation
    :param output_file: name of the CSV output file
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
        Open output file, and query every line of the IP input file.

        It is a mono-process query, so it is not meant for production use, but
        rather for debugging purposes.
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
        self._close_output_file()

    def query_all_ip_multiprocesses(self):
        """
        Open output file, and query every line of the IP input file.

        It is a heavily multi-processes query, to be used for production.  A pool
        of self.processes processes is created, each one querying one modem at a
        time.
        The main parent process is taking care of the cachedb management (to avoid
        concurrent access to it), and the genration of the CSV line in the output
        file.
        """
        self.__debug("Start of poller.query_all_ip_multiprocesses with {} processes".format(self.processes))
        self._open_output_file()
        in_q= []
        worker_pool = Pool(processes = self.processes)
        with open(self.ip_file, 'r') as csvfile:
            csvreader = csv.DictReader(csvfile, fieldnames = self.ip_fieldnames, delimiter = ';')
            for line in csvreader:
                entity = { 'read_community': self.read_community, 'ip': line['ip'], 'bpid': line['bpid'], 'mac': line['mac']}
                in_q.append(entity)

        self.__debug("Starting multoprocessing for {} length queue...".format(len(in_q)))
        for modem in worker_pool.imap_unordered(func=query_one_modem, iterable=in_q, chunksize=1):
            if self.cachedb and modem.state == 'completed':
                self.traces.debug('Start do cache'.format(modem.hostname, modem.hfc_mac))
                self.cachedb.compute_usage(modem)
                self.traces.debug('Cache UPDATED for modem {} (mac: {}). '.format(modem.hostname, modem.hfc_mac))
            else:
                self.traces.debug('Cache NOT UPDATED for modem {} (mac: {}). '.format(modem.hostname, modem.hfc_mac))

            line = modem.get_legacy_csv_line() + '\n'
            self.out.write(line)
            self.out.flush()

        self.__debug("Wait for worker_pool to close...")
        worker_pool.close()
        self.__debug("Closed. Waiting for all processes to finish...")
        worker_pool.join()
        self.__debug("Worker_pool finished")
        self._close_output_file()

    def query_all(self):
        """
        This is the method to call in order to query all modems.  Based on the
        number of desired processes, it will launch the correct child method.
        """
        if self.processes > 1:
            return self.query_all_ip_multiprocesses()
        else:
            return self.query_all_ip()

# Functions for multiprocessing
def query_one_modem(entity):
    """
    This is the function to be called in every process.  It should be efficient
    and above all, it must not generate any exception otherwise the concerned
    process will not be usable anymore!
    """
    community = entity['read_community']
    ip = entity['ip']
    bpid = entity['bpid']
    mac = entity['mac']

    traces = logging.getLogger('traces')
    traces.debug('query_one_modem (PID {}): for modem {} (mac: {}) start'.format(os.getpid(), ip, mac))
    modem = ch6643e(hostname = ip, community = community, bpid = bpid, mac = mac)
    try:
        modem.query_all()
        if modem.state == 'error':
            traces.debug('query_one_modem (PID {}): for modem {} (mac: {}). ERROR'.format(os.getpid(), ip, mac))
        else:
            traces.debug('query_one_modem (PID {}): for modem {} (mac: {}). DONE'.format(os.getpid(), ip, mac))
        return modem
    except:
        logging.getLogger('traces').critical("query_one_modem (PID {}): Generic exception catched! (ip: {}, mac: {})".format(os.getpid(), ip, mac), exc_info=True)
        modem.state = 'error'
        return modem
