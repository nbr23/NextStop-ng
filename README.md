# NextStop-ng

## Description
This tool allows train, bus, tram stops lookups for the Parisian RATP
transportation system.

This is an improved version of [NextStop](https://github.com/nbr23/NextStop),
which used the http://wap.ratp.fr/ website as reference.

This tool is based on the RATP's API, and was built using the gracefully
provided documentation:
[Api Documentation](http://apixha.ixxi.net/APIX), thus providing better
accuracy and higher data quality.

## Usage

###Static information
In order to refrain from refering to the API for mostly static information
such as transport lines, destinations, stop names, etc, NextStop-ng stores
it in a local database which needs to be initialized and filled as such before
any usage is possible:

`./src/nextstop.py -i database.db -u`

###Station list
`./src/nextstop.py -i database.db -l line`

Will display the list of stops the line makes.

###Stop lookup
`./src/nextstop.py -i database.db -l line -s stop`

Will display the time of the next couple stops of the selected line at the
station
