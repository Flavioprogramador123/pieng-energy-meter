from dotenv import load_dotenv
load_dotenv(override=True)
from app.core.config import settings
import tinytuya, socket

_orig = socket.getaddrinfo
def gai(host, port, family=0, type=0, proto=0, flags=0):
    return _orig(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = gai

TARGET = "eb9a1c787c60d712fazces"
print("access_id=", settings.tuya_access_id)
print("region=", settings.tuya_api_region)
print("project_code_esperado=p1788913030419stmcva")

cloud = tinytuya.Cloud(
    apiRegion=settings.tuya_api_region or "us",
    apiKey=settings.tuya_access_id,
    apiSecret=settings.tuya_access_secret,
)
print("token_ok=", bool(cloud.token))

# status iot-03
st = cloud.getstatus(TARGET)
print("iot03_status=", {k: st.get(k) for k in st if k != "result"} if isinstance(st, dict) else st)

# status v1.0
st2 = cloud._tuyaplatform(f"devices/{TARGET}/status")
print("v1_status=", {k: st2.get(k) for k in st2 if k != "result"} if isinstance(st2, dict) else st2)

# device info
dev = cloud._tuyaplatform(f"devices/{TARGET}")
print("device=", {k: dev.get(k) for k in dev if k != "result"} if isinstance(dev, dict) else dev)
if isinstance(dev, dict) and isinstance(dev.get("result"), dict):
    r = dev["result"]
    print("  name=", r.get("name"), "online=", r.get("online"), "owner_id=", r.get("owner_id"), "uid=", r.get("uid"))
