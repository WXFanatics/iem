"""
 Search for NWS Text, return JSON
"""
import datetime
import json

from paste.request import parse_formvars
from pyiem.util import get_dbconn, html_escape, utc
from pymemcache.client import Client


def run(sts, ets, awipsid):
    """Actually do some work!"""
    dbconn = get_dbconn("afos")
    cursor = dbconn.cursor()

    res = {"results": []}
    pillimit = "pil"
    if len(awipsid) == 3:
        pillimit = "substr(pil, 1, 3) "
    cursor.execute(
        f"""
    SELECT data,
    to_char(entered at time zone 'UTC', 'YYYY-MM-DDThh24:MIZ'),
    source, wmo from products WHERE
    entered >= %s and entered < %s and {pillimit} = %s
    ORDER by entered ASC
    """,
        (sts, ets, awipsid),
    )
    for row in cursor:
        res["results"].append(
            dict(ttaaii=row[3], utcvalid=row[1], data=row[0], cccc=row[2])
        )
    return json.dumps(res)


def application(environ, start_response):
    """Answer request."""
    headers = [("Content-type", "application/json")]
    if environ.get("REQUEST_METHOD") != "GET":
        start_response("405 Method Not Allowed", headers)
        return ['{"error": "Only HTTP GET Supported"}'.encode("utf8")]
    fields = parse_formvars(environ)
    awipsid = fields.get("awipsid", "AFDDMX")[:6]
    sts = fields.get("sts", "2019-10-03T00:00Z")
    ets = fields.get("ets", f"{utc():%Y-%m-%dT%H:%M}")
    cb = fields.get("callback", None)

    mckey = f"/json/nwstext_search/{sts}/{ets}/{awipsid}?callback={cb}"
    mc = Client("iem-memcached:11211")
    res = mc.get(mckey)
    if not res:
        sts = datetime.datetime.strptime(sts[:16], "%Y-%m-%dT%H:%M")
        sts = sts.replace(tzinfo=datetime.timezone.utc)
        ets = datetime.datetime.strptime(ets[:16], "%Y-%m-%dT%H:%M")
        ets = ets.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=datetime.timezone.utc)
        cacheexpire = 0 if ets < now else 120

        res = run(sts, ets, awipsid)
        mc.set(mckey, res, cacheexpire)
    else:
        res = res.decode("utf-8")
    mc.close()

    if cb is not None:
        res = f"{html_escape(cb)}({res})"

    start_response("200 OK", headers)
    return [res.encode("ascii")]
