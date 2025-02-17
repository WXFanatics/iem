"""Download an hour worth of ERA5.

Run from RUN_0Z.sh for 5 days ago.
"""
import os
import sys
from datetime import timedelta

import cdsapi
import numpy as np
import pygrib
from pyiem import iemre
from pyiem.util import logger, ncopen, utc

LOG = logger()
CDSVARS = (
    "10m_u_component_of_wind 10m_v_component_of_wind 2m_dewpoint_temperature "
    "2m_temperature soil_temperature_level_1 soil_temperature_level_2 "
    "soil_temperature_level_3 soil_temperature_level_4 "
    "surface_solar_radiation_downwards total_evaporation total_precipitation "
    "volumetric_soil_water_layer_1 volumetric_soil_water_layer_2 "
    "volumetric_soil_water_layer_3 volumetric_soil_water_layer_4"
).split()


def ingest(grbfn, valid):
    """Consume this grib file."""
    ncfn = f"/mesonet/data/era5/{valid.year}_era5land_hourly.nc"
    grbs = pygrib.open(grbfn)
    ames_i = int((-93.61 - iemre.WEST) * 10)
    ames_j = int((41.99 - iemre.SOUTH) * 10)
    # Eh
    tidx = iemre.hourly_offset(valid)
    with ncopen(ncfn, "a") as nc:
        nc.variables["uwnd"][tidx, :, :] = np.flipud(grbs[1].values)
        LOG.info("uwnd %s", nc.variables["uwnd"][tidx, ames_j, ames_i])
        nc.variables["vwnd"][tidx, :, :] = np.flipud(grbs[2].values)
        LOG.info("vwnd %s", nc.variables["vwnd"][tidx, ames_j, ames_i])
        nc.variables["dwpk"][tidx, :, :] = np.flipud(grbs[3].values)
        LOG.info("dwpf %s", nc.variables["dwpk"][tidx, ames_j, ames_i])
        nc.variables["tmpk"][tidx, :, :] = np.flipud(grbs[4].values)
        LOG.info("tmpk %s", nc.variables["tmpk"][tidx, ames_j, ames_i])
        nc.variables["soilt"][tidx, 0, :, :] = np.flipud(grbs[5].values)
        nc.variables["soilt"][tidx, 1, :, :] = np.flipud(grbs[6].values)
        nc.variables["soilt"][tidx, 2, :, :] = np.flipud(grbs[7].values)
        nc.variables["soilt"][tidx, 3, :, :] = np.flipud(grbs[8].values)
        LOG.info("soilt %s", nc.variables["soilt"][tidx, :, ames_j, ames_i])
        # -- Solar Radiation is accumulated since 0z
        rsds = nc.variables["rsds"]
        p01m = nc.variables["p01m"]
        evap = nc.variables["evap"]
        val = np.flipud(grbs[9].values)
        if valid.hour == 0:
            tidx0 = iemre.hourly_offset((valid - timedelta(hours=24)))
            # Special 1 Jan consideration
            if valid.month == 1 and valid.day == 1 and valid.year > 1950:
                with ncopen(
                    (f"/mesonet/data/era5/{valid.year - 1}_era5land_hourly.nc")
                ) as nc2:
                    tsolar = (
                        np.sum(nc2.variables["rsds"][(tidx0 + 1) :], 0)
                        * 3600.0
                    )
                    tp01m = np.sum(nc2.variables["p01m"][(tidx0 + 1) :], 0)
                    tevap = np.sum(nc2.variables["evap"][(tidx0 + 1) :], 0)
            else:
                tsolar = np.sum(rsds[(tidx0 + 1) : tidx], 0) * 3600.0
                tp01m = np.sum(p01m[(tidx0 + 1) : tidx], 0)
                tevap = np.sum(evap[(tidx0 + 1) : tidx], 0)
        elif valid.hour > 1:
            tidx0 = iemre.hourly_offset(valid.replace(hour=1))
            tsolar = np.sum(rsds[tidx0:tidx], 0) * 3600.0
            tp01m = np.sum(p01m[tidx0:tidx], 0)
            tevap = np.sum(evap[tidx0:tidx], 0)
        else:
            tsolar = np.zeros(val.shape)
            tp01m = np.zeros(val.shape)
            tevap = np.zeros(val.shape)
        # J m-2 to W/m2
        newval = (val - tsolar) / 3600.0
        nc.variables["rsds"][tidx, :, :] = np.where(newval < 0, 0, newval)
        LOG.info(
            "rsds nc:%s tsolar:%s grib:%s",
            nc.variables["rsds"][tidx, ames_j, ames_i],
            tsolar[ames_j, ames_i],
            val[ames_j, ames_i],
        )
        # m to mm
        val = np.flipud(grbs[10].values)
        nc.variables["evap"][tidx, :, :] = (val * 1000.0) - tevap
        LOG.info(
            "evap %s grib:%s",
            nc.variables["evap"][tidx, ames_j, ames_i],
            val[ames_j, ames_i],
        )
        # m to mm
        val = np.flipud(grbs[11].values)
        accum = (val * 1000.0) - tp01m
        nc.variables["p01m"][tidx, :, :] = np.where(accum < 0, 0, accum)
        LOG.info(
            "p01m %s grib:%s",
            nc.variables["p01m"][tidx, ames_j, ames_i],
            val[ames_j, ames_i],
        )
        val = np.flipud(grbs[12].values)
        nc.variables["soilm"][tidx, 0, :, :] = val
        nc.variables["soilm"][tidx, 1, :, :] = grbs[13].values
        nc.variables["soilm"][tidx, 2, :, :] = grbs[14].values
        nc.variables["soilm"][tidx, 3, :, :] = grbs[15].values
        LOG.info(
            "soilm %s grib1:%s",
            nc.variables["soilm"][tidx, :, ames_j, ames_i],
            val[ames_j, ames_i],
        )


def run(valid):
    """Run for the given valid time."""
    LOG.info("Running for %s", valid)
    grbfn = f"{valid:%Y%m%d%H}.grib"

    cds = cdsapi.Client(quiet=True)

    cds.retrieve(
        "reanalysis-era5-land",
        {
            "variable": CDSVARS,
            "year": f"{valid.year}",
            "month": f"{valid.month}",
            "day": f"{valid.day}",
            "time": f"{valid:%H}:00",
            "area": [
                iemre.NORTH,
                iemre.WEST,
                iemre.SOUTH,
                iemre.EAST,
            ],
            "format": "grib",
        },
        grbfn,
    )
    ingest(grbfn, valid)
    os.unlink(grbfn)


def main(argv):
    """Go!"""
    valid = utc(*[int(a) for a in argv[1:]])
    offsets = []
    if len(argv) == 5:
        offsets = [0]
    elif len(argv) == 4:
        # Best to run for 1z through 0z as 0z has the 24hr sum to consider
        offsets = range(1, 25)
    for offset in offsets:
        run(valid + timedelta(hours=offset))


if __name__ == "__main__":
    main(sys.argv)
