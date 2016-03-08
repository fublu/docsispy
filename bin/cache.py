#!/usr/bin/python3
# vim: set fileencoding=utf-8
# (c) © 2016 Xavier Lüthi xavier@luthi.eu

from ch6643e import ch6643e
import sqlite3
import logging

class cachedb(object):

    def __init__(self, file_name = 'docsispy.db'):
        self.connection = sqlite3.connect(file_name)
        self.cursor = self.connection.cursor()
        
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS modems 
                                (hfc_mac    TEXT PRIMARY KEY ASC, 
                                 wan_dl     INTEGER NOT NULL,
                                 wan_ul     INTEGER NOT NULL,
                                 timestamp  INTEGER NOT NULL,
                                 boot_time  INTEGER NOT NULL)""")
        self.connection.commit()
        self.traces = logging.getLogger('traces')
        
    def __debug(self,msg):
        self.traces.debug(msg)

    def compute_usage(self, modem):
        
        self.cursor.execute('SELECT * FROM modems WHERE hfc_mac= :hfc_mac ORDER BY timestamp DESC LIMIT 1', 
            {'hfc_mac' : modem.hfc_mac})
        row = self.cursor.fetchone()
        if row is None:
            modem.dl_delta = 0
            modem.ul_delta = 0
        else:
            self.__debug(row)
            (cache_hfc_mac, cache_wan_dl, cache_wan_ul, cache_timestamp, cache_boot_time) = row
            # condition for considering a reboot:
            #    1. current WAN_DL is less than the one in DB
            # OR 2. current WAN_UL is less than the one in DB
            # OR 3. boot_time is newer than boot_time in DB, with 600 seconds 
            if modem.wan_dl < cache_wan_dl or \
               modem.wan_ul < cache_wan_ul or \
               modem.boot_time - cache_boot_time > 600:
                
                # modem has been rebooted
                modem.dl_delta = modem.wan_dl
                modem.ul_delta = modem.wan_ul
            else:
                # no reboot --> calculate the delta
                modem.dl_delta = modem.wan_dl - cache_wan_dl
                modem.ul_delta = modem.wan_ul - cache_wan_ul
        
        self.add_modem(modem)
        
        
        
    def add_modem(self, modem):
        self.cursor.execute('INSERT OR REPLACE INTO modems VALUES (:hfc_mac, :wan_dl, :wan_ul, :timestamp, :boot_time)',
            {'hfc_mac': modem.hfc_mac, 'wan_dl': modem.wan_dl, 'wan_ul': modem.wan_ul,
             'timestamp': modem.timestamp, 'boot_time': modem.boot_time})
        self.connection.commit()
        

