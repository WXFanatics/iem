"""Use data provided by ACIS to replace climodat data."""
import sys
import datetime
import time

import requests
import pandas as pd
from pandas.io.sql import read_sql
from pyiem.network import Table as NetworkTable
from pyiem.util import get_dbconn, logger
from pyiem.reference import TRACE_VALUE, ncei_state_codes

LOG = logger()
SERVICE = "http://data.rcc-acis.org/StnData"


def safe(val):
    """Hack"""
    if pd.isnull(val):
        return None
    if val in ["M", "S"]:
        return None
    if val == "T":
        return TRACE_VALUE
    # Multi-day we can't support
    if isinstance(val, str) and val.endswith("A"):
        return None
    try:
        return float(val)
    except ValueError:
        LOG.info("failed to convert %s to float, using None", repr(val))


def compare(row, colname):
    """Do we need to update this column?"""
    oldval = safe(row[colname])
    newval = safe(row[f"a{colname}"])
    if oldval is None and newval is not None:
        return True
    if newval is not None and oldval != newval:
        return True
    return False


def do(station, acis_station, interactive):
    """Do the query and work

    Args:
      station (str): IEM Station identifier ie IA0200
      acis_station (str): the ACIS identifier ie 130197
    """
    table = "alldata_%s" % (station[:2],)
    today = datetime.date.today()
    fmt = "%Y-%m-%d"
    payload = {
        "sid": acis_station,
        "sdate": "1850-01-01",
        "edate": today.strftime(fmt),
        "elems": [
            {"name": "maxt", "add": "t"},
            {"name": "mint", "add": "t"},
            {"name": "pcpn", "add": "t"},
            {"name": "snow", "add": "t"},
            {"name": "snwd", "add": "t"},
        ],
    }
    if not interactive:
        payload["sdate"] = (today - datetime.timedelta(days=365)).strftime(fmt)
    LOG.debug("Call ACIS server for: %s to update: %s", acis_station, station)
    req = requests.post(SERVICE, json=payload)
    if req.status_code != 200:
        LOG.info("Got status_code %s for %s", req.status_code, acis_station)
        # Give server some time to recover from transient errors
        time.sleep(60)
        return
    try:
        j = req.json()
    except Exception as exp:
        LOG.exception(exp)
        return
    if "data" not in j:
        LOG.info("No Data!, content=%s", req.content)
        return
    acis = pd.DataFrame(
        j["data"],
        columns="day ahigh alow aprecip asnow asnowd".split(),
    )
    for col in "ahigh alow aprecip asnow asnowd".split():
        acis[[col, f"{col}_hour"]] = pd.DataFrame(
            acis[col].tolist(),
            index=acis.index,
        )
    LOG.debug("Loaded %s rows from ACIS", len(acis.index))
    acis["day"] = pd.to_datetime(acis["day"])
    acis = acis.set_index("day")
    pgconn = get_dbconn("coop")
    obs = read_sql(
        f"SELECT day, high, low, precip, snow, snowd from {table} WHERE "
        "station = %s ORDER by day ASC",
        pgconn,
        params=(station,),
        index_col="day",
    )
    LOG.debug("Loaded %s rows from IEM", len(obs.index))
    obs["dbhas"] = 1
    cursor = pgconn.cursor()
    # join the tables
    df = acis.join(obs, how="left")
    inserts = 0
    updates = 0
    minday = None
    maxday = None
    for day, row in df.iterrows():
        work = []
        args = []
        for col in ["high", "low", "precip", "snow", "snowd"]:
            if not compare(row, col):
                continue
            work.append(f"{col} = %s")
            args.append(safe(row[f"a{col}"]))
            if col in ["high", "precip"]:
                work.append(
                    f"{'temp' if col == 'high' else 'precip'}_hour = %s"
                )
                args.append(row[f"a{col}_hour"])
        if not work:
            continue
        if minday is None:
            minday = day
        maxday = day
        if row["dbhas"] != 1:
            inserts += 1
            cursor.execute(
                f"INSERT into {table} (station, day, sday, year, month) "
                "VALUES (%s, %s, %s, %s, %s)",
                (station, day, day.strftime("%m%d"), day.year, day.month),
            )
        # LOG.debug("%s -> %s %s", day, work, args)
        cursor.execute(
            f"UPDATE {table} SET {','.join(work)} WHERE station = %s and "
            "day = %s",
            (*args, station, day),
        )
        updates += 1

    LOG.info(
        "%s[%s-%s] Updates: %s Inserts: %s",
        station,
        minday,
        maxday,
        updates,
        inserts,
    )
    cursor.close()
    pgconn.commit()


def main(argv):
    """Do what is asked."""
    interactive = sys.stdout.isatty()
    if len(argv) == 2:
        state = argv[1]
        # Only run cron job for online sites
        nt = NetworkTable(f"{state}CLIMATE", only_online=not interactive)
        for sid in nt.sts:
            if sid[2] in ["T", "C"] or sid[2:] == "0000":
                continue
            acis_station = ncei_state_codes[state] + sid[2:]
            do(sid, acis_station, interactive)
    else:
        (station, acis_station) = argv[1], argv[2]
        do(station, acis_station, interactive)


if __name__ == "__main__":
    main(sys.argv)
