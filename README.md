# DOCSISpy#
Yet another *efficient* DOCSIS SNMP poller.

### Introduction ###

*docsispy* provides a tool to query efficiently in SNMP a population of DOCSIS cable modems in the field.  The goal is to fetch as efficiently as possible some important values from the modems like:

* modem uptime
* firmware version and boot status
* SNR and power of all downstream channels
* power of all upstream channels
* WAN traffic consumption (download and upload)
* WAN public IP address and gateway

As a solid foundation, the tool relies on a python SNMP library called [easysnmp](https://github.com/xluthi/easysnmp). It uses this library to build tailor-made SNMP queries.

### How do I get set up? ###

#### Dependencies
*docsispy* depends on [easysnmp](https://github.com/xluthi/easysnmp): it must be compiled and installed beforehand.

*docsispy* works with Python 3 only. Python 2 is not supported.

#### Deployment
A configuration file is required.  Currently, it is only used to define SNMP community strings.  By default, this file is located in `~/.docsispy/docsispy.secret`. An example file is available in the sources in the `conf` folder.

The main executable is `bin/launch_poller.py`. A detailed help is available with the `--help` option.

A typical invocation of the program is:
```
launch_poller.py --parallel 500 --config ~/.docsispy/docsispy.secret --cachedb ~/.docsispy/docsispy.db
```

It can be scheduled via crontab for regular queries.

### Contributing ###

*docsispy* is currently used in production and is considered as stable. However, if you want to use it for your own needs, and want to contribute back to the code, feel free to contact the repository admin, or the author via email (name and email source files).

### Copyright and license ###

`(c) © 2016-2017 Xavier Lüthi xavier@luthi.eu`

```
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
```

See LICENSE.txt for the full license text.
