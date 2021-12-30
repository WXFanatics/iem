"""Hit up ESRIs elevation REST service to compute a station elevation."""
import time
import sys

import requests
from pyiem.util import get_dbconn, logger

LOG = logger()


def get_elevation(lon, lat):
    """Use arcgisonline"""
    req = requests.get(
        f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}",
        timeout=30,
    )
    if req.status_code != 200:
        LOG.info("ERROR: %s", req.status_code)
        return None
    return req.json()["results"][0]["elevation"]


def workflow():
    """Our work"""
    pgconn = get_dbconn("mesosite")
    mcursor = pgconn.cursor()
    mcursor2 = pgconn.cursor()
    mcursor.execute(
        "SELECT network, ST_x(geom) as lon, ST_y(geom) as lat, elevation, id "
        "from stations WHERE (elevation < -990 or elevation is null)"
    )

    for row in mcursor:
        elev = row[3]
        lat = row[2]
        lon = row[1]
        sid = row[4]
        network = row[0]
        newelev = get_elevation(lon, lat)

        print("%7s %s OLD: %s NEW: %.3f" % (sid, network, elev, newelev))
        mcursor2.execute(
            "UPDATE stations SET elevation = %s WHERE id = %s "
            "and network = %s",
            (newelev, sid, network),
        )
        time.sleep(2)

    mcursor2.close()
    pgconn.commit()


def main(argv):
    """Go Main Go"""
    if len(argv) == 1:
        workflow()
    else:
        print(get_elevation(argv[1], argv[2]))


if __name__ == "__main__":
    main(sys.argv)
