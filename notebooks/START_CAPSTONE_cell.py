# START CAPSTONE
# One-time notebook settings: approved private dataset, T4, Internet, API Secret.
from pathlib import Path
from hashlib import sha256
from urllib.request import urlopen
import sys
import importlib
COMMIT = "fd50258cbd6a50fb76630ab85ed0cb0ffbe040c3"
HASHES = {'capstone_discovery.py': '619403fe1b071dc3a48a327947e6c94ca34a6312e943138bf1a5d40c447b82af', 'capstone_kaggle.py': '95d29ca5d026fed3c14ef1027a7cdd7fbb0a4039a4cd6b8a5485b678bb416ad3'}
SUPPORT = Path("/kaggle/working/capstone-entry")
SUPPORT.mkdir(exist_ok=True)
try:
    for name, expected in HASHES.items():
        url = f"https://raw.githubusercontent.com/mark-juswa/CometicsAI/{COMMIT}/scripts/{name}"
        with urlopen(url, timeout=30) as response:
            raw = response.read(65537)
        if len(raw) > 65536 or sha256(raw).hexdigest() != expected:
            raise RuntimeError("Pinned startup support hash mismatch")
        (SUPPORT / name).write_bytes(raw)
    sys.path.insert(0, str(SUPPORT))
    import capstone_discovery
    importlib.reload(capstone_discovery)
    import capstone_kaggle
    importlib.reload(capstone_kaggle)
    capstone_kaggle.main()
except Exception as error:
    print("CAPSTONE_STARTUP_FAILED stage=startup_support", type(error).__name__)
    print("Check Internet and imported notebook version. No GPU worker was started by this entry failure.")
