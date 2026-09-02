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

# SAP Mode mappings (index values correspond to mode numbers)
SAP_MODES = [
    "manual",      # 0
    "auto",        # 1
    "sleep",       # 2
    "turbo",       # 3
    "focus",       # 4
    "baby",        # 5
    "meeting",     # 6
    "smoke",       # 7
    "home",        # 8
    "deodorize",   # 9
    "pet",         # 10
]

# SAP startup modes
SAP_SMODES = [
    "default_on",  # 0
    "memory",      # 1
]

# SAP indicator light options
SAP_LS_OPTIONS = [
    "off",    # 0 - all off
    "panel",  # 1 - panel light only
    "air",    # 2 - air quality light only
    "all",    # 3 - all on
]

# SAP speed levels
SAP_SPEED_COUNT = 3  # 1=low, 2=medium, 3=high
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