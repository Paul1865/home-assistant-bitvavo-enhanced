from homeassistant.helpers.device_registry import DeviceInfo


def get_device():
    return DeviceInfo(
        identifiers={("bitvavo", "account")},
        name="Bitvavo Account",
        manufacturer="Bitvavo",
        model="Crypto Portfolio",
    )