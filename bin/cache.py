#!/usr/bin/python3
# vim: set fileencoding=utf-8
# (c) © 2016-2017 Xavier Lüthi xavier@luthi.eu
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# See LICENSE.txt for the full license text.

from ch6643e import ch6643e
import sqlite3
import logging
import os # getpid() for debug traces

class cachedb(object):
    """
    This class represents the database containing the previously fetched values
    for all modems. The values are:
        - hfc_mac
        - wan_dl
        - wan_ul
        - timestamp
    wan_dl and wan_ul are absolute values as fetched from the modem. In order to
    calculate the relative consumption, it calculates the delta between the
    current value and the one in database.
    """
    def __init__(self, file_name = 'docsispy.db'):
        """
        Create or open the SQLite3 database file. If the file doesn't exist,
        it is created with the relevant table.
        :param file_name: file to be used to open or create the database
        """
        self.file_name = file_name
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
        self.traces.debug("PID {} - {}".format(os.getpid(),msg))

    def compute_usage(self, modem):
        """
        This is the main method. For the modem passed as argument, it compute_usage
        its relative consumption, based on the values stored in database.
        If the modem is not in the database yet, it inserts it in the database and
        assume the relative consumption is null.
        If the modem is in the database, it tries to determine if the modem rebooted:
        Condition for considering a reboot:
            1. current WAN_DL is less than the one in DB
         OR 2. current WAN_UL is less than the one in DB
         OR 3. boot_time is newer than boot_time in DB, with 600 seconds
        ps: boot_time is a computed value, it must be calculated by the modem object.

        This method doesn't return any value, but updates the modem object with
        calculated dl_delta and ul_delta.

        :param modem: modem object with SNMP values already polled (ch6643e)
        """
        self.cursor.execute('SELECT * FROM modems WHERE hfc_mac= :hfc_mac ORDER BY timestamp DESC LIMIT 1', 
            {'hfc_mac' : modem.hfc_mac})
        row = self.cursor.fetchone()
        if row is None:
            modem.dl_delta = 0
            modem.ul_delta = 0
        else:
            self.__debug(row)
            (cache_hfc_mac, cache_wan_dl, cache_wan_ul, cache_timestamp, cache_boot_time) = row

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
        """
        Add the provided modem within the database. Normally, it is not called
        directly, but via the compute_usage method.
        :param modem: modem object with SNMP values already polled (ch6643e)
        """
        self.cursor.execute('INSERT OR REPLACE INTO modems VALUES (:hfc_mac, :wan_dl, :wan_ul, :timestamp, :boot_time)',
            {'hfc_mac': modem.hfc_mac, 'wan_dl': modem.wan_dl, 'wan_ul': modem.wan_ul,
             'timestamp': modem.timestamp, 'boot_time': modem.boot_time})
        self.connection.commit()
