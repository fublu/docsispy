#!/usr/bin/python3
# vim: set fileencoding=utf-8
# (c) © 2016-2017 Xavier Lüthi xavier@luthi.eu

from easysnmp import Session, exceptions
from datetime import datetime
import logging
from binascii import hexlify
import ipaddress
import json
import os # getpid() for debug traces

class ch6643e(object):
    """
    This object represents one Compal CH6643e cable modem.

    For multiprocessing SNMP queries, this object must be pickable. As a consequence:
     - it cannot have easysnmp.Session as parent, but Session must be created
       on the fly.
     - logging file (traces) must not be kept as instance attribute.

    :param bpid: Business partner ID. Only relevant for Voo
    :param community: SNMP v2 community string
    :param timeout: SNMP query timeout - seconds before retry
    :param hostname: IP address of the modem (private one - aka HFC IP)
    :param retries: SNMP retries before failure
    :param state: status of the query: init, completed, nocounter, timeout, error
    :param hfc_mac: HFC mac address of the modem
    :param uptime: seconds since the last reboot of the modem
    :param boot_time: /not used anymore/ (but still present in cache.py)
    :param wan_dl: bytes downloaded since last reboot
    :param wan_ul: bytes uploaeded since last reboot
    :param ds_power: list of Rx level for every DS channel
    :param ds_snr: list of *signal noise ratio* for every DS channel
    :param us_power: list of Tx level for every US channel
    :param config_file: DOCSIS configuration file name and path
    :param oper_status: DOCSIS operating status
    :param boot_status: DOCSIS boot status
    :param fw_version: modem firmware verion
    :param fw_filename: modem firmware file name
    :param wan_address: WAN IP address (public IP)
    :param wan_gateway: WAN gateway (CMTS public IP address)
    :param timestamp: date & time at the creation of the object
    :param dl_delta: WAN download traffic counter (calculated with the cache)
    :param ul_delta: WAN upload traffic counter (calculated with the cache)
    """
    def __init__(self, hostname='localhost', community='public', timeout=7,
        retries=1, bpid = '', mac = ''):

        self.bpid        = bpid
        self.community   = community
        self.timeout     = timeout
        self.hostname    = hostname
        self.retries     = retries

        # Not strictly required, but help to describe the data model
        self.state       = 'init'
        self.hfc_mac     = mac
        self.uptime      = -1
        self.boot_time   = 0
        self.wan_dl      = -1
        self.wan_ul      = -1
        self.ds_power    = []
        self.ds_snr      = []
        self.us_power    = []
        self.config_file = ''
        self.oper_status = ''
        self.boot_status = ''
        self.fw_version  = ''
        self.fw_filename = ''
        self.wan_address = ''
        self.wan_gateway = ''

        # Latest datetime when a query has been performed.
        self.timestamp = datetime.today()

        # Traffic counters calculation
        self.dl_delta = 0
        self.ul_delta = 0


    def __debug(self,msg):
        """
        Log a specific line in the 'traces' file, with DEBUG level.

        param: msg (str): the message to be logged.
        """
        logging.getLogger('traces').debug("PID {} - {}".format(os.getpid(),msg))

    def query_all(self):
        """
        Query the modem and get all information available.
        This is the main method to be used to activate SNMP query.
        """
        session =  Session(hostname=self.hostname, version=2,
                           community=self.community, timeout=self.timeout,
                           retries=self.retries, use_numeric=True)
        try:
            self.state = 'completed'
            self.get_counters(session)
            self.get_configdata(session)
            self.get_signals(session)
        except exceptions.EasySNMPTimeoutError as e:
            self.__debug("SNMP timeout (ip: {}, mac: {})".format(self.hostname, self.hfc_mac))
            self.state = 'timeout'
        except:
            logging.getLogger('traces').critical("Generic exception catched! (ip: {}, mac: {})".format(self.hostname, self.hfc_mac), exc_info=True)
            self.state = "error"
        self.__debug("query_all for IP {} completed with status '{}'".format(self.hostname, self.state))

    def get_counters(self, session):
        """
        Query with one single SNMP GET operation the following OID:
        ["HFC MAC address",      "IF-MIB::ifPhysAddress.2",                ".1.3.6.1.2.1.2.2.1.6.2"],
        ["System uptime",        "DISMAN-EVENT-MIB::sysUpTimeInstance",    ".1.3.6.1.2.1.1.3.0"],
        ["Inbound WAN traffic",  "IF-MIB::ifHCInOctets.2",                 ".1.3.6.1.2.1.31.1.1.1.6.2"],
        ["Outbound WAN traffic", "IF-MIB::ifHCOutOctets.2",                ".1.3.6.1.2.1.31.1.1.1.10.2"]

        param: session (easysnmp.Session): SNMP session used for the query.
        """
        oid = [".1.3.6.1.2.1.2.2.1.6.2",
               ".1.3.6.1.2.1.1.3.0",
               ".1.3.6.1.2.1.31.1.1.1.6.2",
               ".1.3.6.1.2.1.31.1.1.1.10.2"]

        res = session.get(oid)

        self.hfc_mac = hexlify(res[0].value.encode('latin-1')).decode()
        self.uptime  = int(res[1].value)
        try:
            self.wan_dl  = int(res[2].value)
            self.wan_ul  = int(res[3].value)
        except ValueError as e:
            logging.getLogger('traces').error("Error converting traffic counters (ip: {}, mac: {})".format(self.hostname, self.hfc_mac))
            self.state = 'nocounter'
            self.wan_dl = ''
            self.wan_ul = ''

    def get_configdata(self, session):
        """
        Query with one single SNMP GET operation the following OID:
        ["Configuration file path", "DOCS-CABLE-DEVICE-MIB::docsDevServerConfigFile.0", ".1.3.6.1.2.1.69.1.4.5.0"],
        ["Operational status",      "DOCS-CABLE-DEVICE-MIB::docsDevSwOperStatus.0",     ".1.3.6.1.2.1.69.1.3.4.0"],
        ["Boot status",             "DOCS-CABLE-DEVICE-MIB::docsDevServerBootState.0",  ".1.3.6.1.2.1.69.1.4.1.0"],
        ["Firmware version",        "DOCS-CABLE-DEVICE-MIB::docsDevSwCurrentVers.0",    ".1.3.6.1.2.1.69.1.3.5.0"],
        ["Firmware file name",      "DOCS-CABLE-DEVICE-MIB::docsDevSwFilename.0",       ".1.3.6.1.2.1.69.1.3.2.0"],
        ["WAN address",             "CBN-CM-GATEWAY-MIB::cmGwWanInetAddress.0",         ".1.3.6.1.4.1.35604.1.19.52.1.1.5.0"],
        ["WAN gateway",             "CBN-CM-GATEWAY-MIB::cmGwWanRouter.0",              ".1.3.6.1.4.1.35604.1.19.52.1.1.10.0"]

        param: session (easysnmp.Session): SNMP session used for the query.
        """
        oid = [".1.3.6.1.2.1.69.1.4.5.0",
               ".1.3.6.1.2.1.69.1.3.4.0",
               ".1.3.6.1.2.1.69.1.4.1.0",
               ".1.3.6.1.2.1.69.1.3.5.0",
               ".1.3.6.1.2.1.69.1.3.2.0",
               ".1.3.6.1.4.1.35604.1.19.52.1.1.5.0",
               ".1.3.6.1.4.1.35604.1.19.52.1.1.10.0"]

        res = session.get(oid)

        self.config_file = res[0].value
        self.oper_status = res[1].value
        self.boot_status = res[2].value
        self.fw_version  = res[3].value
        self.fw_filename = res[4].value
        try:
            self.wan_address = str(ipaddress.IPv4Address(res[5].value.encode('latin-1')))
            self.wan_gateway = str(ipaddress.IPv4Address(res[6].value.encode('latin-1')))
        except ipaddress.AddressValueError:
            # No wan received
            self.wan_address = 'no_WAN'
            self.wan_gateway = 'no_WAN'

    def get_signals(self, session):
        """
        Many SNMP GET_BULK operations to fetch the following OIDs:
        ["Downstream powers",    "DOCS-IF-MIB::docsIfDownChannelPower",    ".1.3.6.1.2.1.10.127.1.1.1.1.6"],
        ["Downstream SNR",       "DOCS-IF-MIB::docsIfSigQSignalNoise",     ".1.3.6.1.2.1.10.127.1.1.4.1.5"],
        ["Upstream power",       "DOCS-IF3-MIB::docsIf3CmStatusUsTxPower", ".1.3.6.1.4.1.4491.2.1.20.1.2.1.1"]

        param: session (easysnmp.Session): SNMP session used for the query.
        """

        # list of tuple (id, value)
        self.ds_power = self._get_bulk(session, ".1.3.6.1.2.1.10.127.1.1.1.1.6", 9)
        self.ds_snr   = self._get_bulk(session, ".1.3.6.1.2.1.10.127.1.1.4.1.5", len(self.ds_power) + 1)
        self.us_power = self._get_bulk(session, ".1.3.6.1.4.1.4491.2.1.20.1.2.1.1", 5)

    def _get_bulk(self, session, oid, max_repetitions = 9):
        """
        Many SNMP GET BULK operations to mimic an SNMP WALK.  This could be
        considered as a "BULK WALK" operation.

        The principle is the following:
        1. starting at the *oid* provided, we perform an SNMP GET BULK operation
           asking *max_repetitions* returned values.
        2. For every returned value, we check if the OID is still a descendant of
           the *oid* provided. If yes, we store the value in the output list, if
           not, we stop the operation and return.
        3. If we are still a descendant of the provided *oid*, we perform again
           an SNMP GET BULK operation with *oid* equal to the latest retrieved.
        4. We repeat 1 to 3 up to when we are no more a descendant of the originally
           provided *oid*.

        In order to have an efficient operation, *max_repetitions* should be equal
        to 1 plus the expected number of OID.  That way, only one SNMP query will
        be actually executed.

        param: session (easysnmp.Session): SNMP session used for the query.
        param: oid (str): OID to start with.
        param: max_repetitions (int): maximal number of OID values to return for
               each "SNMP GET BULK" operation (see above for hints for this value).
        :return: a list of SNMPVariable objects containing the values that
                 were retrieved via SNMP
        """

        this_tree = oid
        in_this_tree = True
        var_list = []
        while ( in_this_tree ):
            res = session.get_bulk(oids=this_tree, non_repeaters=0, max_repetitions=max_repetitions)

            for s in res:
                # self.__debug(s)
                if s.oid == oid:
                    var_list.append( (s.oid_index, s.value) )
                else:
                    # self.__debug("Did not match this_tree. End of get_bulk.")
                    in_this_tree = False
                    break
                if s.snmp_type == 'ENDOFMIBVIEW':
                    in_this_tree = False
                    break

            this_tree = res[-1].oid

        return var_list

    def get_legacy_csv_line(self):
        """
        :return: a CSV line with the same format as the legacy SNMP pollbot.
        """
        if self.bpid == '':
            self.bpid = self.hfc_mac
        if self.state in ('completed', 'nocounter'):
            ds = len(self.ds_power)
            us = len(self.us_power)
            result = ';'.join ([self.timestamp.strftime('%Y%m%d-%H%M%S'),
                        self.bpid,
                        self.hfc_mac,
                        self.hostname,
                        self.config_file,
                        self.oper_status,
                        self.boot_status,
                        str(ds),
                        ':'.join([str(int(x[1])/10) for x in self.ds_power]),
                        str(ds),
                        ':'.join([str(int(x[1])/10) for x in self.ds_snr]),
                        str(us),
                        ':'.join([str(int(x[1])/10) for x in self.us_power]),
                        '{}-{}'.format(ds, us),
                        self.fw_version,
                        self.fw_filename,
                        self.wan_gateway,
                        self.wan_address,
                        str(self.uptime),
                        str(self.wan_ul),
                        str(self.ul_delta),
                        str(self.wan_dl),
                        str(self.dl_delta)])
        else:
            result = ';'.join([self.timestamp.strftime('%Y%m%d-%H%M%S'),
                        self.bpid,
                        self.hfc_mac,
                        self.hostname,
                        'timeout;;;;;;;;;;;;;;;'])
        return result

# The following is only to test the class itself. Could be seen as an example too.
if __name__ == '__main__':
    import argparse
    from pprint import pformat
    parser = argparse.ArgumentParser(
        description="Test for ch6643e class",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('ip', help='HFC ip of the modem to query')
    parser.add_argument('-c', '--community', help='SNMP community', default='public')
    parser.add_argument('--debug',   '-d', action='count', help=
        'Debug output with kind of traces.')
    parser.add_argument('--mac', help='HFC mac of the modem to query')
    args = parser.parse_args()
    traces = logging.getLogger('traces')
    if args.debug:
        traces.setLevel(logging.DEBUG)
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        traces.addHandler(sh)
        traces.debug("Debug mode activated")

    modem = ch6643e(hostname = args.ip, community = args.community, bpid='dummy_bpid', mac = args.mac)
    modem.query_all()
    traces.debug(pformat(vars(modem)))
    print(modem.get_legacy_csv_line())
