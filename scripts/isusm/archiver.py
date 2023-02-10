"""
LoggerNet delivers now single files per poll.  This script pieces them back
together and then 1) dumps to LDM and 2) archives off to storage.

run on iem15's crontab
"""
import datetime
import os
import glob
import subprocess
from io import BytesIO
import tempfile
import zipfile

from pyiem.util import logger, utc

LOG = logger()
PATH = "/mesonet/data/isusm"
# run at 6z, so file for previous date
NOW = utc() - datetime.timedelta(days=1)


def save_content(station, content):
    """Send to LDM."""
    epoch = {"MinSI": 0, "DailySI": 0, "HrlySI": 0}
    for key in content:
        ftype = key.split("||")[0]
        if ftype not in epoch:
            LOG.debug("Hmmmm, unknown ftype: %s", ftype)
            continue
        suffix = epoch[ftype] if epoch[ftype] > 0 else ""
        epoch[ftype] += 1
        filename = f"{station}{suffix}_{ftype}_{NOW:%Y%m%d}.dat"
        # send to LDM for archival
        pqstr = f"data a {NOW:%Y%m%d%H%M} bogus raw/isusm/{filename} dat"
        LOG.debug(pqstr)
        with tempfile.NamedTemporaryFile(delete=False) as tmpfd:
            tmpfd.write(content[key].getvalue())
        with subprocess.Popen(
            ["pqinsert", "-i", "-p", pqstr, tmpfd.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        ) as proc:
            (stdout, stderr) = proc.communicate()
        if stdout != b"" or stderr != b"":
            LOG.info("%s stdout: %s stderr: %s", pqstr, stdout, stderr)
        os.unlink(tmpfd.name)


def process(files):
    """Figure out what to do with the data we have."""
    files.sort()
    content = {}
    for fn in files:
        lines = open(fn, "rb").readlines()
        if len(lines) < 4:
            LOG.debug("fn: %s has %s lines, skipping", fn, len(lines))
            continue
        ftype = fn.rsplit("_", 5)[1]
        # build key based on the header
        key = f"{ftype}||{lines[1]}"
        if key not in content:
            content[key] = BytesIO()
            content[key].write(b"".join(lines[:4]))
        for line in lines[4:]:
            if line.strip() == b"":
                continue
            content[key].write(line)
    return content


def zip_and_delete(station, files):
    """zip em off to storage and delete them, gasp."""
    archivedir = f"{PATH}/archived/{NOW.year}/{NOW:%m}"
    if not os.path.isdir(archivedir):
        os.makedirs(archivedir)
    savefn = f"{archivedir}/{station}_{NOW:%Y%m%d}.zip"
    if os.path.isfile(savefn):
        LOG.info("Refusing to overwrite %s", savefn)
        return
    LOG.debug("creating %s", savefn)
    with zipfile.ZipFile(savefn, "w", zipfile.ZIP_DEFLATED) as zfh:
        for fn in files:
            zfh.write(fn)
    for fn in files:
        os.unlink(fn)


def upload_to_staging():
    """Move to staging for google drive upload."""
    rempath = "/stage/iemoffline/isusm/"
    cmd = (
        "rsync -r --no-perms "
        "--remove-source-files --groupmap=*:iem-friends --rsync-path "
        f'"mkdir -p {rempath} && rsync" archived/* '
        f"mesonet@metl60.agron.iastate.edu:{rempath}"
    )
    LOG.debug(cmd)
    subprocess.call(cmd, shell=True)


def main():
    """Go Main Go."""
    os.chdir(PATH)
    files = {}
    for fn in glob.glob("*.dat"):
        station = fn.rsplit("_", 5)[0]
        d = files.setdefault(station, [])
        d.append(fn)
    for station, fns in files.items():
        content = process(fns)
        save_content(station, content)
        zip_and_delete(station, fns)
    upload_to_staging()


if __name__ == "__main__":
    main()
