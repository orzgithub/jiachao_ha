"""Constants for Jiachao IoT."""

DOMAIN = "jiachao_ha"

# Config entry keys
CONF_PHONE = "phone"
CONF_COUNTRY_CODE = "country_code"
CONF_CODE = "code"
CONF_TOKEN = "token"
CONF_USER_ID = "user_id"
CONF_ZONE = "zone"
CONF_DEVICES = "devices"

# MQTT topics
MQTT_SUB_TOPIC = "smart/{device_id}/dc/{product_id}/dout/#"
MQTT_PUB_TOPIC = "smart/{device_id}/dc/{product_id}/din/config"

# Default values
DEFAULT_PORT = 8883

# API Endpoints
API_BASE = "https://dc02.iotdreamcatcher.net.cn:12443"
API_SEND_CODE = f"{API_BASE}/v2/user/login/code"
API_LOGIN = f"{API_BASE}/v2/user/code/login"
API_DEVICE_LIST = f"{API_BASE}/v2/user/device/list"
API_HOME_LIST = f"{API_BASE}/v2/group/homes"
API_ROOM_LIST = f"{API_BASE}/v2/group/home/rooms"

# MQTT Commands
CMD_SET_SAP_STAT = "set_sap_stat"
CMD_HOST_CONF = "host_conf"
CMD_GET_SAP_STAT = "get_sap_stat"
CMD_GET_HOST_CONF = "host_conf"  # Note: same as CMD_HOST_CONF, used for querying config

# SAP Mode definitions (value, translation_key)
SAP_MODES = [
    (0, "manual", None),
    (1, "auto", None),
    (2, "sleep", None),
    (3, "turbo", -1),
    (3, "pet", 20),
    # 4 = unknown mode, should enable with a time but didn't show in the offical app UI.
    (5, "focus", None),
    (6, "baby", None),
    (7, "meeting", None),
    (8, "smoke", None),
    (9, "home", None),
    (10, "deodorize", None),
    (11, "scoop", None),
]

SAP_MODE_NAMES = [mode[1] for mode in SAP_MODES]
SAP_MODE_PARAMS = [(mode[0], mode[2]) for mode in SAP_MODES]

# SAP startup modes (smode)
SAP_SMODES = [
    (0, "default_on"),
    (1, "memory"),
]
SAP_SMODE_NAMES = [s[1] for s in SAP_SMODES]
SAP_SMODE_VALUES = [s[0] for s in SAP_SMODES]

# SAP indicator light options (value, translation_key)
SAP_LS_OPTIONS = [
    (0, "off"),
    (1, "panel"),
    (2, "air"),
    (3, "all"),
]
SAP_LS_NAMES = [l[1] for l in SAP_LS_OPTIONS]
SAP_LS_VALUES = [l[0] for l in SAP_LS_OPTIONS]

# SAP speed levels
SAP_SPEED_COUNT = 3
SAP_SPEED_LIST = ["1", "2", "3"]

# Device types
DEVICE_TYPE_SAP = "SAP"
DEVICE_TYPE_IPC = "IPC"
DEVICE_TYPE_SA = "SA"
DEVICE_TYPE_LT = "LT"
DEVICE_TYPE_LS = "LS"
DEVICE_TYPE_SW = "SW"
DEVICE_TYPE_PFD = "PFD"
DEVICE_TYPE_PWT = "PWT"
DEVICE_TYPE_DML = "DML"
DEVICE_TYPE_GDS = "GDS"
DEVICE_TYPE_RV = "RV"
DEVICE_TYPE_WF = "WF"
DEVICE_TYPE_IR = "IR"
DEVICE_TYPE_GW = "GW"