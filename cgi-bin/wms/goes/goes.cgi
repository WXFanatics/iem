#!/bin/sh

MS_MAPFILE=/opt/iem/data/wms/goes/goes.map
export MS_MAPFILE

/opt/iem/cgi-bin/mapserv/mapserv
