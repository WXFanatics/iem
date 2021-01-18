"""I produce the hourly analysis used by IEMRE"""
import sys
import datetime

import numpy as np
import pandas as pd
from pandas.io.sql import read_sql
from metpy.units import masked_array
from metpy.interpolate import inverse_distance_to_grid
from pyiem import iemre
from pyiem import meteorology
import pyiem.datatypes as dt
from pyiem.util import get_dbconn, ncopen, utc, logger

# stop RuntimeWarning: invalid value encountered in greater
np.warnings.filterwarnings("ignore")
LOG = logger()
MEMORY = {"ts": datetime.datetime.now()}


def grid_wind(df, domain):
    """
    Grid winds based on u and v components
    @return uwnd, vwnd
    """
    # compute components
    u = []
    v = []
    for _station, row in df.iterrows():
        (_u, _v) = meteorology.uv(
            dt.speed(row["sknt"], "KT"), dt.direction(row["drct"], "DEG")
        )
        u.append(_u.value("MPS"))
        v.append(_v.value("MPS"))
    df["u"] = u
    df["v"] = v
    ugrid = generic_gridder(df, "u", domain)
    vgrid = generic_gridder(df, "v", domain)
    return ugrid, vgrid


def grid_skyc(df, domain):
    """Hmmmm"""
    v = []
    for _station, row in df.iterrows():
        _v = max(row["max_skyc1"], row["max_skyc2"], row["max_skyc3"])
        v.append(_v)
    df["skyc"] = v
    return generic_gridder(df, "skyc", domain)


def generic_gridder(df, idx, domain):
    """Generic gridding algorithm for easy variables"""
    df2 = df[pd.notnull(df[idx])]
    xi, yi = np.meshgrid(iemre.XAXIS, iemre.YAXIS)
    res = np.ones(xi.shape) * np.nan
    # set a sentinel of where we won't be estimating
    res = np.where(domain > 0, res, -9999)
    # do our gridding
    grid = inverse_distance_to_grid(
        df2["lon"].values, df2["lat"].values, df2[idx].values, xi, yi, 1.5
    )
    # replace nan values in res with whatever now is in grid
    res = np.where(np.isnan(res), grid, res)
    # Do we still have missing values?
    if np.isnan(res).any():
        # very aggressive with search radius
        grid = inverse_distance_to_grid(
            df2["lon"].values, df2["lat"].values, df2[idx].values, xi, yi, 5.5
        )
        # replace nan values in res with whatever now is in grid
        res = np.where(np.isnan(res), grid, res)
    # replace sentinel back to np.nan
    # replace sentinel back to np.nan
    res = np.where(res == -9999, np.nan, res)
    return np.ma.array(res, mask=np.isnan(res))


def grid_hour(ts):
    """
    I proctor the gridding of data on an hourly basis
    @param ts Timestamp of the analysis, we'll consider a 20 minute window
    """
    LOG.debug("grid_hour called...")
    with ncopen(iemre.get_hourly_ncname(ts.year), "a", timeout=300) as nc:
        domain = nc.variables["hasdata"][:, :]
    ts0 = ts - datetime.timedelta(minutes=10)
    ts1 = ts + datetime.timedelta(minutes=10)
    utcnow = utc() - datetime.timedelta(hours=36)

    # If we are near realtime, look in IEMAccess instead of ASOS database
    mybuf = 2.0
    params = (
        iemre.WEST - mybuf,
        iemre.SOUTH - mybuf,
        iemre.WEST - mybuf,
        iemre.NORTH + mybuf,
        iemre.EAST + mybuf,
        iemre.NORTH + mybuf,
        iemre.EAST + mybuf,
        iemre.SOUTH - mybuf,
        iemre.WEST - mybuf,
        iemre.SOUTH - mybuf,
        ts0,
        ts1,
    )
    if utcnow < ts:
        dbconn = get_dbconn("iem", user="nobody")
        sql = """SELECT t.id as station, ST_x(geom) as lon,
        ST_y(geom) as lat,
 max(case when tmpf > -60 and tmpf < 130 THEN tmpf else null end) as max_tmpf,
 max(case when sknt > 0 and sknt < 100 then sknt else 0 end) as max_sknt,
 max(getskyc(skyc1)) as max_skyc1,
 max(getskyc(skyc2)) as max_skyc2,
 max(getskyc(skyc3)) as max_skyc3,
 max(case when phour > 0 and phour < 1000 then phour else 0 end) as phour,
 max(case when dwpf > -60 and dwpf < 100 THEN dwpf else null end) as max_dwpf,
 max(case when sknt >= 0 then sknt else 0 end) as sknt,
 max(case when sknt >= 0 then drct else 0 end) as drct
 from current_log s JOIN stations t on (s.iemid = t.iemid)
 WHERE ST_Contains(
  ST_GeomFromEWKT('SRID=4326;POLYGON((%s %s, %s  %s, %s %s, %s %s, %s %s))'),
  geom) and valid >= %s and valid < %s GROUP by station, lon, lat
         """
    else:
        dbconn = get_dbconn("asos", user="nobody")
        sql = """SELECT station, ST_x(geom) as lon, st_y(geom) as lat,
 max(case when tmpf > -60 and tmpf < 130 THEN tmpf else null end) as max_tmpf,
 max(case when sknt > 0 and sknt < 100 then sknt else 0 end) as max_sknt,
 max(getskyc(skyc1)) as max_skyc1,
 max(getskyc(skyc2)) as max_skyc2,
 max(getskyc(skyc3)) as max_skyc3,
 max(case when p01i > 0 and p01i < 1000 then p01i else 0 end) as phour,
 max(case when dwpf > -60 and dwpf < 100 THEN dwpf else null end) as max_dwpf,
 max(case when sknt >= 0 then sknt else 0 end) as sknt,
 max(case when sknt >= 0 then drct else 0 end) as drct
 from alldata a JOIN stations t on (a.station = t.id) WHERE
 ST_Contains(
  ST_GeomFromEWKT('SRID=4326;POLYGON((%s %s, %s  %s, %s %s, %s %s, %s %s))'),
  geom) and (t.network ~* 'ASOS' or t.network = 'AWOS') and
 valid >= %s and valid < %s GROUP by station, lon, lat"""

    df = read_sql(sql, dbconn, params=params, index_col="station")
    LOG.debug("got database results")
    if df.empty:
        LOG.info("%s has no entries, FAIL", ts)
        return
    ures, vres = grid_wind(df, domain)
    LOG.debug(
        "grid_wind is done. max(ures): %s max(vres): %s",
        np.max(ures),
        np.max(vres),
    )
    if ures is None:
        LOG.debug("Failure for uwnd at %s", ts)
    else:
        write_grid(ts, "uwnd", ures)
        write_grid(ts, "vwnd", vres)

    tmpf = generic_gridder(df, "max_tmpf", domain)
    LOG.debug("grid tmpf is done")
    if tmpf is None:
        LOG.info("Failure for tmpk at %s", ts)
    else:
        dwpf = generic_gridder(df, "max_dwpf", domain)
        LOG.debug("grid dwpf is done")
        # require that dwpk <= tmpk
        mask = ~np.isnan(dwpf)
        mask[mask] &= dwpf[mask] > tmpf[mask]
        dwpf = np.where(mask, tmpf, dwpf)
        write_grid(
            ts, "tmpk", masked_array(tmpf, data_units="degF").to("degK")
        )
        write_grid(
            ts, "dwpk", masked_array(dwpf, data_units="degF").to("degK")
        )

    res = grid_skyc(df, domain)
    LOG.debug("grid skyc is done")
    if res is None:
        LOG.info("Failure for skyc at %s", ts)
    else:
        write_grid(ts, "skyc", res)


def write_grid(valid, vname, grid):
    """Atomic write of data to our netcdf storage

    This is isolated so that we don't 'lock' up our file while intensive
    work is done
    """
    offset = iemre.hourly_offset(valid)
    with ncopen(iemre.get_hourly_ncname(valid.year), "a", timeout=300) as nc:
        LOG.debug(
            "writing %s with min: %s max: %s Ames: %s",
            vname,
            np.ma.min(grid),
            np.ma.max(grid),
            grid[151, 259],
        )
        nc.variables[vname][offset] = grid


def main(argv):
    """Go Main"""
    if len(argv) == 5:
        ts = utc(int(argv[1]), int(argv[2]), int(argv[3]), int(argv[4]))
    else:
        ts = utc().replace(second=0, minute=0)
    grid_hour(ts)


if __name__ == "__main__":
    main(sys.argv)
