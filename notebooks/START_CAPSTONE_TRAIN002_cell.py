# START CAPSTONE
# One-time notebook settings: approved private dataset, T4, Internet, API Secret.
from pathlib import Path
from hashlib import sha256
from urllib.request import urlopen
import sys
import importlib
COMMIT = "8009ea46111be63691c0ebe292fdef0dbb6eb099"
HASHES = {'capstone_discovery.py': '98555390828f22939851f28c7e15bdef368b011e0b6ac62b2174cff09ed32e24', 'capstone_kaggle.py': '256cdc00ee2ae6290647b14bff5bbdc50e62751f29936fd73c953e3f0c66ac60'}
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
    capstone_kaggle.main(bundle_name=capstone_discovery.TRAIN002_BUNDLE_NAME, bundle_sha=capstone_discovery.TRAIN002_BUNDLE_SHA)
except Exception as error:
    print("CAPSTONE_STARTUP_FAILED stage=startup_support", type(error).__name__)
    print("Check Internet and imported notebook version. No GPU worker was started by this entry failure.")
