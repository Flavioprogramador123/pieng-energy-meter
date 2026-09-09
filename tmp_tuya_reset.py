from dotenv import load_dotenv
load_dotenv(override=True)
from app.core.config import settings
import tinytuya, json

TARGET = "eb9a1c787c60d712fazces"
cloud = tinytuya.Cloud(
    apiRegion=settings.tuya_api_region or "us",
    apiKey=settings.tuya_access_id,
    apiSecret=settings.tuya_access_secret,
)

print("=== LIST DEVICES ===")
devs = cloud.getdevices()
items = devs if isinstance(devs, list) else (devs or {}).get("result") or []
print(f"count={len(items)}")
for d in items:
    if isinstance(d, dict):
        name = str(d.get("name") or "").encode("ascii","replace").decode("ascii")
        print(f"  id={d.get('id')} name={name} online={d.get('online')} cat={d.get('category')}")

print("\n=== STATUS PC473 ===")
st = cloud.getstatus(TARGET)
print("meta=", {k: st.get(k) for k in (st or {}) if k != "result"} if isinstance(st, dict) else st)
result = (st or {}).get("result") if isinstance(st, dict) else None
if isinstance(result, list):
    for item in result:
        print(f"  {item.get('code')}={item.get('value')}")

# descobrir funcoes/comandos disponiveis
print("\n=== FUNCTIONS / SPEC ===")
for meth in ["getfunctions", "get_functions", "getdevicefunctions"]:
    fn = getattr(cloud, meth, None)
    if callable(fn):
        try:
            out = fn(TARGET)
            print(f"{meth}=", json.dumps(out, ensure_ascii=True)[:1500])
        except Exception as e:
            print(f"{meth} err={e}")

# tentativas comuns de reset de energia em plugs Tuya
print("\n=== TRY ENERGY RESET COMMANDS ===")
candidates = [
    ("fault", "reset_energy"),
    ("fault", "clear_energy"),
    ("clear_energy", True),
    ("reset_energy", True),
    ("energy_reset", True),
    ("add_ele", 0),
    ("relay_status", "power_off"),
]
# sendcommand / sendcommandraw patterns in tinytuya
for code, value in candidates:
    try:
        # tinytuya Cloud.sendcommand(deviceid, {'commands':[{'code':..,'value':..}]})
        payload = {"commands": [{"code": code, "value": value}]}
        resp = cloud.sendcommand(TARGET, payload)
        print(f"send {code}={value!r} -> {resp}")
    except Exception as e:
        print(f"send {code} err={e}")
