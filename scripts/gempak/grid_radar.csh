#!/bin/csh

set tstamp="`date -u +'%y%m%d/%H%M'`"

source /mesonet/nawips/Gemenviron

# need to override default RAD
setenv RAD /mnt/nexrad3/nexrad

gddelt << EOF >& /tmp/gddelt.out
 GDFILE        = /mesonet/data/gempak/radar.gem
 GDATTIM = ALL
 GLEVEL        = ALL
 GVCORD        = ALL
 GFUNC        = ALL
 list
 run

 exit
EOF

gdradr << EOF >& /tmp/gridRADAR_gdradr.out
 GRDAREA  = 38.25;-99;45.75;-88
 PROJ     = MER
 KXKY     = 720;500
 GDPFUN   = N0R
 GDFILE   = /mesonet/data/gempak/radar.gem
 RADTIM   = $tstamp
 RADDUR   = 30
 RADFRQ   = 
 RADMODE  = PC
 CPYFIL   =  
 STNFIL   = nexrad.tbl
 MAXGRD   = 2
 list
 run

 exit
EOF