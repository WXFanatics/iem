"""Generate some line charts from ISU Frost Model Output"""
from io import BytesIO
import os
import datetime

import numpy as np
import pytz
import matplotlib.dates as mdates
from paste.request import parse_formvars
from pyiem.util import ncopen, convert_value
from pyiem.plot.use_agg import plt


def get_latest_time(model):
    """Figure out the latest model runtime"""
    utc = datetime.datetime.utcnow()
    utc = utc.replace(tzinfo=pytz.UTC)
    utc = utc.replace(hour=12, minute=0, second=0, microsecond=0)
    limit = 24
    while not os.path.isfile(
        utc.strftime(
            ("/mesonet/share/frost/" + model + "/%Y%m%d%H%M_iaoutput.nc")
        )
    ):
        utc -= datetime.timedelta(hours=12)
        limit -= 1
        if limit < 0:
            return None
    return utc


def get_times(nc):
    """Return array of datetimes for the time array"""
    tm = nc.variables["time"]
    sts = datetime.datetime.strptime(
        tm.units.replace("minutes since ", ""), "%Y-%m-%d %H:%M:%S"
    )
    sts = sts.replace(tzinfo=pytz.utc)
    res = []
    for t in tm[:]:
        res.append(sts + datetime.timedelta(minutes=float(t)))
    return res


def get_ij(lon, lat, nc):
    """Figure out the closest grid cell"""
    dist = (
        (nc.variables["lon"][:] - lon) ** 2
        + (nc.variables["lat"][:] - lat) ** 2
    ) ** 0.5
    return np.unravel_index(np.argmin(dist), dist.shape)


def add_labels(fig):
    """Create a legend for the condition variable"""
    fig.text(0.85, 0.8, "Frost", color="red")
    fig.text(0.85, 0.75, "Ice/Snow", color="orange")
    fig.text(0.85, 0.7, "Wet", color="green")
    fig.text(0.85, 0.65, "Dew", color="brown")
    fig.text(0.85, 0.6, "Frz Rain", color="purple")


def get_icond_color(model, val):
    """Get the color for this Model and icond

    METRO: 1-8 dry, wet, ice/snow, mix, dew, melting snow, blk ice, icing rain
    BRIDGET: 0-5 dry, frosty, icy/snowy, melting, freezing, wet
    """
    if val is None or val < 0 or np.ma.is_masked(val):
        return "none"
    if model == "metro":
        colors = [
            "white",
            "white",
            "green",
            "orange",
            "orange",
            "brown",
            "blue",
            "orange",
            "purple",
        ]
    else:
        colors = ["white", "tan", "orange", "blue", "purple", "green"]
    if val > (len(colors) - 1):
        return "none"
    return colors[val]


def get_ifrost_color(val):
    """Which color to use"""
    if val is None or val == -1:
        return "none"
    colors = ["#EEEEEE", "r"]
    try:
        return colors[val]
    except Exception:
        return "none"


def process(model, lon, lat):
    """Generate a plot for this given combination"""
    fig = plt.figure()
    ax = fig.add_axes([0.1, 0.1, 0.7, 0.8])
    modelts = get_latest_time(model)
    if modelts is None:
        ax.text(0.5, 0.5, "No Data Found to Plot!", ha="center")
        return
    nc = ncopen(
        modelts.strftime(
            ("/mesonet/share/frost/" + model + "/%Y%m%d%H%M_iaoutput.nc")
        )
    )
    times = get_times(nc)
    (i, j) = get_ij(lon, lat, nc)

    ax.plot(
        times,
        convert_value(nc.variables["bdeckt"][:, i, j], "degK", "degF"),
        color="k",
        label="Bridge Deck Temp" if model == "bridget" else "Pavement",
    )
    ax.plot(
        times,
        convert_value(nc.variables["tmpk"][:, i, j], "degK", "degF"),
        color="r",
        label="Air Temp",
    )
    ax.plot(
        times,
        convert_value(nc.variables["dwpk"][:, i, j], "degK", "degF"),
        color="g",
        label="Dew Point",
    )
    # ax.set_ylim(-30,150)
    ax.set_title(
        (
            "ISUMM5 %s Timeseries\n"
            "i: %s j:%s lon: %.2f lat: %.2f Model Run: %s"
        )
        % (
            model,
            i,
            j,
            nc.variables["lon"][i, j],
            nc.variables["lat"][i, j],
            modelts.astimezone(pytz.timezone("America/Chicago")).strftime(
                "%-d %b %Y %-I:%M %p"
            ),
        )
    )

    ax.xaxis.set_major_locator(
        mdates.DayLocator(interval=1, tz=pytz.timezone("America/Chicago"))
    )
    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%d %b\n%Y", tz=pytz.timezone("America/Chicago"))
    )
    ax.axhline(32, linestyle="-.")
    ax.grid(True)
    ax.set_ylabel(r"Temperature $^\circ$F")

    ymax = ax.get_ylim()[1]

    for i2, ifrost in enumerate(nc.variables["ifrost"][:-1, i, j]):
        ax.barh(
            ymax - 1,
            1.0 / 24.0 / 4.0,
            left=times[i2],
            fc=get_ifrost_color(ifrost),
            ec="none",
        )
    for i2, icond in enumerate(nc.variables["icond"][:-1, i, j]):
        ax.barh(
            ymax - 2,
            1.0 / 24.0 / 4.0,
            left=times[i2],
            fc=get_icond_color(model, icond),
            ec="none",
        )

    # Shrink current axis's height by 10% on the bottom
    box = ax.get_position()
    ax.set_position(
        [box.x0, box.y0 + box.height * 0.1, box.width, box.height * 0.9]
    )
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        fancybox=True,
        shadow=True,
        ncol=3,
    )
    add_labels(fig)


def application(environ, start_response):
    """Go Main Go"""
    form = parse_formvars(environ)
    if "lon" in form and "lat" in form:
        process(
            form.get("model"), float(form.get("lon")), float(form.get("lat"))
        )

    start_response("200 OK", [("Content-type", "image/png")])
    bio = BytesIO()
    plt.savefig(bio)
    return [bio.getvalue()]
