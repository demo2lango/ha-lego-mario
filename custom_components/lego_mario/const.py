import logging

DOMAIN = "lego_mario"
LOGGER = logging.getLogger(__package__)

# 乐高 LWP3 协议 UUID
LEGO_SERVICE_UUID = "00001623-1212-efde-1623-785feabcd123"
LEGO_CHARACTERISTIC_UUID = "00001624-1212-efde-1623-785feabcd123"

# 裤子检测 ID 映射表
PANTS_MAP = {
    0: "No Pants",
    1: "Regular Pants (Mario Red)",
    2: "Fire Mario Pants",
    3: "Propeller Mario Pants",
    4: "Cat Mario Pants",
    5: "Builder Mario Pants",
    6: "Penguin Mario Pants",
    7: "Tanooki Mario Pants",
    8: "Frog Mario Pants",
    9: "Bee Mario Pants",
}

# 基础颜色 ID 映射表 (Port 0x01 通道)
COLOR_MAP = {
    19: "White",
    21: "Red (Lava)",
    23: "Blue (Water)",
    24: "Yellow (Sand)",
    37: "Green (Grass)",
    106: "Brown",
    268: "Purple (Poison)",
}
