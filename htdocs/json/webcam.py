"""
JSON webservice providing timestamps of available webcam images
"""
import datetime
import json
from zoneinfo import ZoneInfo

from paste.request import parse_formvars
from pyiem.util import get_dbconn


def dance(cid, start_ts, end_ts):
    """Go get the dictionary of data we need and deserve"""
    dbconn = get_dbconn("mesosite")
    cursor = dbconn.cursor()
    data = {"images": []}
    cursor.execute(
        """
        SELECT valid at time zone 'UTC', drct from camera_log where
        cam = %s and valid >= %s and valid < %s
    """,
        (cid, start_ts, end_ts),
    )
    for row in cursor:
        uri = row[0].strftime(
            "https://mesonet.agron.iastate.edu/archive/"
            f"data/%Y/%m/%d/camera/{cid}/{cid}_%Y%m%d%H%M.jpg"
        )
        data["images"].append(
            {
                "valid": row[0].strftime("%Y-%m-%dT%H:%M:00Z"),
                "drct": row[1],
                "href": uri,
            }
        )

    return data


def application(environ, start_response):
    """Answer request."""
    fields = parse_formvars(environ)
    cid = fields.get("cid", "ISUC-006")
    start_ts = fields.get("start_ts")
    end_ts = fields.get("end_ts")
    date = fields.get("date")
    if date is not None:
        start_ts = datetime.datetime.strptime(date, "%Y%m%d")
        start_ts = start_ts.replace(tzinfo=ZoneInfo("America/Chicago"))
        end_ts = start_ts + datetime.timedelta(days=1)
    else:
        start_ts = datetime.datetime.strptime(start_ts, "%Y%m%d%H%M")
        start_ts = start_ts.replace(tzinfo=ZoneInfo("UTC"))
        end_ts = datetime.datetime.strptime(end_ts, "%Y%m%d%H%M")
        end_ts = end_ts.replace(tzinfo=ZoneInfo("UTC"))

    headers = [("Content-type", "application/json")]
    start_response("200 OK", headers)
    return [json.dumps(dance(cid, start_ts, end_ts)).encode("ascii")]
