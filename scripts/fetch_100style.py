"""
Fetch only the 100STYLE clips FLV uses (forward walk + idle of 14 styles) out of the 1.5 GB zip on
Zenodo, reading just those bytes with HTTP range requests. CC BY 4.0: "The 100STYLE Dataset – Ian Mason".

    python3 scripts/fetch_100style.py                     # the clips the film uses -> assets/mocap/100style
    python3 scripts/fetch_100style.py --library           # idle, forward walk and turn of all 100 styles
                                                          # -> assets/mocap/library/100style (not in Git)
Plain Python 3, no extra packages. Clips already there are skipped.
"""
import http.client
import io
import urllib.request
import zipfile
from pathlib import Path

URL = "https://zenodo.org/records/8127870/files/100STYLE.zip"
STYLES = ("Old Tiptoe InTheDark Followed Crouched Depressed Rushed Stiff Proud ArmsBehindBack "
          "WalkingStickLeft Heavyset Neutral Angry").split()
OUT = Path(__file__).resolve().parent.parent / "assets" / "mocap" / "100style"
HEADERS = {"User-Agent": "FLV-MocapFetcher/1.0"}


def get_range(start, end):
    request = urllib.request.Request(URL, headers={**HEADERS, "Range": f"bytes={start}-{end}"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read(), response.headers.get("Content-Range", "")
        except (OSError, http.client.HTTPException):     # dropped connections: retry
            if attempt == 4:
                raise


class RemoteFile(io.RawIOBase):
    """Read-only, seekable view of a remote file; every read is one HTTP range request."""

    def __init__(self):
        self.pos = 0
        self.size = int(get_range(0, 0)[1].rsplit("/", 1)[1])     # "bytes 0-0/<size>"

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = (offset, self.pos + offset, self.size + offset)[whence]
        return self.pos

    def readinto(self, buffer):
        if self.pos >= self.size:
            return 0
        data, _ = get_range(self.pos, min(self.pos + len(buffer), self.size) - 1)
        buffer[:len(data)] = data
        self.pos += len(data)
        return len(data)


def main():
    import sys
    library = "--library" in sys.argv
    out = OUT.parent / "library" / "100style" if library else OUT
    out.mkdir(parents=True, exist_ok=True)
    kinds = ("ID", "FW", "TR1") if library else ("FW", "ID")
    with zipfile.ZipFile(io.BufferedReader(RemoteFile(), buffer_size=1 << 20)) as archive:
        names = [info.filename.rsplit("/", 1)[-1] for info in archive.infolist()]
        styles = sorted({n.rsplit("_", 1)[0] for n in names if n.endswith("_ID.bvh")}) if library else STYLES
        wanted = {f"{s}_{kind}.bvh" for s in styles for kind in kinds}
        for info in archive.infolist():
            name = info.filename.rsplit("/", 1)[-1]
            if name in wanted:
                wanted.discard(name)
                target = out / name
                if target.exists():
                    print(f"have  {target.name}")
                    continue
                target.write_bytes(archive.read(info))
                print(f"get   {target.name}  ({info.file_size / 1e6:.1f} MB)")
    if wanted:
        raise SystemExit(f"not in the zip: {sorted(wanted)}")


if __name__ == "__main__":
    main()
