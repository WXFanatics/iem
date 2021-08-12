"""Fetch NASA GPM data.

IMERG-Early has at most 4 hour latency.


IMERG-Late has about 14 hours.

Replace HHE with HHL

IMERG-Final is many months delayed

Drop L in the above.

2001-today

RUN from RUN_20AFTER.sh for 5 hours ago.
"""
import subprocess
import json
import datetime
import os
import sys
import tempfile

from PIL import Image
import numpy as np
import requests
from pyiem import mrms
from pyiem.util import utc, ncopen, logger

LOG = logger()


def compute_source(valid):
    """Which source to use."""
    utcnow = utc()
    if (utcnow - valid) < datetime.timedelta(hours=24):
        return "E"
    if (utcnow - valid) < datetime.timedelta(days=120):
        return "L"
    return ""


def main(argv):
    """Go Main Go."""
    valid = utc(*[int(a) for a in argv[1:6]])
    source = compute_source(valid)
    routes = "ac" if len(argv) > 6 else "a"
    LOG.debug("Using source: `%s` for valid: %s[%s]", source, valid, routes)
    tmp = tempfile.NamedTemporaryFile(delete=False)
    url = valid.strftime(
        "https://gpm1.gesdisc.eosdis.nasa.gov/thredds/ncss/aggregation/"
        f"GPM_3IMERGHH{source}.06/%Y/GPM_3IMERGHH{source}"
        ".06_Aggregation_%Y%03j.ncml.ncml?"
        "var=precipitationCal&time=%Y-%m-%dT%H%%3A%M%%3A00Z&accept=netcdf4"
    )
    req = requests.get(url, timeout=120)
    if req.status_code != 200:
        LOG.info("failed to fetch %s using source %s", valid, source)
        LOG.debug(url)
        return
    tmp.write(req.content)
    tmp.close()
    with ncopen(tmp.name) as nc:
        # x, y
        pmm = nc.variables["precipitationCal"][0, :, :] / 2.0  # mmhr to 30min
        pmm = np.flipud(pmm.T)
    os.unlink(tmp.name)

    if np.max(pmm) > 102:
        LOG.warning("overflow with max(%s) value > 102", np.max(pmm))
    # idx: 0-200 0.25mm  -> 50 mm
    # idx: 201-253 1mm -> 50-102 mm
    img = np.where(pmm >= 102, 254, 0)
    img = np.where(
        np.logical_and(pmm >= 50, pmm < 102),
        201 + (pmm - 50) / 1.0,
        img,
    )
    img = np.where(np.logical_and(pmm > 0, pmm < 50), pmm / 0.25, img)
    img = np.where(pmm < 0, 255, img)

    png = Image.fromarray(img.astype("u1"))
    png.putpalette(mrms.make_colorramp())
    png.save(f"{tmp.name}.png")

    ISO = "%Y-%m-%dT%H:%M:%SZ"
    metadata = {
        "start_valid": (valid - datetime.timedelta(minutes=15)).strftime(ISO),
        "end_valid": (valid + datetime.timedelta(minutes=15)).strftime(ISO),
        "units": "mm",
        "source": "F" if source == "" else source,  # E, L, F
        "generation_time": utc().strftime(ISO),
    }
    with open(f"{tmp.name}.json", "w") as fp:
        fp.write(json.dumps(metadata))
    pqstr = (
        "pqinsert -i -p 'plot %s %s "
        "gis/images/4326/imerg/p30m.json GIS/imerg/p30m_%s.json json' "
        "%s.json"
    ) % (
        routes,
        valid.strftime("%Y%m%d%H%M"),
        valid.strftime("%Y%m%d%H%M"),
        tmp.name,
    )
    subprocess.call(pqstr, shell=True)
    os.unlink(f"{tmp.name}.json")

    with open(f"{tmp.name}.wld", "w") as fp:
        fp.write("\n".join(["0.1", "0.0", "0.0", "-0.1", "-179.95", "89.95"]))
    pqstr = (
        "pqinsert -i -p 'plot %s %s "
        "gis/images/4326/imerg/p30m.wld GIS/imerg/p30m_%s.wld wld' "
        "%s.wld"
    ) % (
        routes,
        valid.strftime("%Y%m%d%H%M"),
        valid.strftime("%Y%m%d%H%M"),
        tmp.name,
    )
    subprocess.call(pqstr, shell=True)
    os.unlink(f"{tmp.name}.wld")

    pqstr = (
        "pqinsert -i -p 'plot %s %s "
        "gis/images/4326/imerg/p30m.png GIS/imerg/p30m_%s.png png' "
        "%s.png"
    ) % (
        routes,
        valid.strftime("%Y%m%d%H%M"),
        valid.strftime("%Y%m%d%H%M"),
        tmp.name,
    )
    subprocess.call(pqstr, shell=True)
    os.unlink(f"{tmp.name}.png")


if __name__ == "__main__":
    main(sys.argv)