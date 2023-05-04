"""Download Interface for RWIS data"""
# pylint: disable=abstract-class-instantiated
import datetime
from io import BytesIO, StringIO

import pandas as pd
import pytz
from paste.request import parse_formvars
from pyiem.network import Table as NetworkTable
from pyiem.util import get_sqlalchemy_conn
from sqlalchemy import text

DELIMITERS = {"comma": ",", "space": " ", "tab": "\t"}
EXL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def get_time(form, tzname):
    """Get timestamps"""
    ts = datetime.datetime.utcnow()
    ts = ts.replace(tzinfo=pytz.UTC)
    ts = ts.astimezone(pytz.timezone(tzname))
    y1 = int(form.get("year1"))
    y2 = int(form.get("year2"))
    m1 = int(form.get("month1"))
    m2 = int(form.get("month2"))
    d1 = int(form.get("day1"))
    d2 = int(form.get("day2"))
    h1 = int(form.get("hour1"))
    h2 = int(form.get("hour2"))
    mi1 = int(form.get("minute1", 0))
    mi2 = int(form.get("minute2", 0))
    sts = ts.replace(year=y1, month=m1, day=d1, hour=h1, minute=mi1)
    ets = ts.replace(year=y2, month=m2, day=d2, hour=h2, minute=mi2)
    return sts, ets


def application(environ, start_response):
    """Go do something"""
    form = parse_formvars(environ)
    include_latlon = form.get("gis", "no").lower() == "yes"
    myvars = form.getall("vars")
    myvars.insert(0, "station")
    myvars.insert(1, "obtime")
    delimiter = DELIMITERS.get(form.get("delim", "comma"))
    what = form.get("what", "dl")
    tzname = form.get("tz", "UTC")
    src = form.get("src", "atmos")
    sts, ets = get_time(form, tzname)
    stations = form.getall("stations")
    if not stations:
        start_response("200 OK", [("Content-type", "text/plain")])
        return [b"Error, no stations specified for the query!"]
    if len(stations) == 1:
        stations.append("XXXXXXX")

    tbl = "alldata"
    if src in ["soil", "traffic"]:
        tbl = f"alldata_{src}"
    network = form.get("network", "IA_RWIS")
    nt = NetworkTable(network, only_online=False)
    if "_ALL" in stations:
        stations = list(nt.sts.keys())
    params = {
        "tzname": tzname,
        "ids": tuple(stations),
        "ets": ets,
        "sts": sts,
    }
    sql = text(
        f"SELECT *, valid at time zone :tzname as obtime from {tbl} "
        "WHERE station in :ids and valid BETWEEN :sts and :ets "
        "ORDER by valid ASC"
    )
    with get_sqlalchemy_conn("rwis") as conn:
        df = pd.read_sql(sql, conn, params=params)
    if df.empty:
        start_response("200 OK", [("Content-type", "text/plain")])
        return [b"Sorry, no results found for query!"]
    if include_latlon:
        myvars.insert(2, "longitude")
        myvars.insert(3, "latitude")

        def get_lat(station):
            """hack"""
            return nt.sts[station]["lat"]

        def get_lon(station):
            """hack"""
            return nt.sts[station]["lon"]

        df["latitude"] = [get_lat(x) for x in df["station"]]
        df["longitude"] = [get_lon(x) for x in df["station"]]

    sio = StringIO()
    if what in ["txt", "download"]:
        headers = [
            ("Content-type", "application/octet-stream"),
            ("Content-disposition", "attachment; filename=rwis.txt"),
        ]
        start_response("200 OK", headers)
        df.to_csv(sio, index=False, sep=delimiter, columns=myvars)
        return [sio.getvalue().encode("ascii")]
    if what == "html":
        start_response("200 OK", [("Content-type", "text/html")])
        df.to_html(sio, columns=myvars)
        return [sio.getvalue().encode("ascii")]
    if what == "excel":
        if len(df.index) >= 1048576:
            start_response("200 OK", [("Content-type", "text/plain")])
            return [b"Dataset too large for excel format."]
        bio = BytesIO()
        with pd.ExcelWriter(bio) as writer:
            df.to_excel(writer, "Data", index=False, columns=myvars)

        headers = [
            ("Content-type", EXL),
            ("Content-disposition", "attachment; Filename=rwis.xlsx"),
        ]
        start_response("200 OK", headers)
        return [bio.getvalue()]
    start_response("200 OK", [("Content-type", "text/plain")])
    df.to_csv(sio, sep=delimiter, columns=df.columns.intersection(myvars))
    return [sio.getvalue().encode("ascii")]
