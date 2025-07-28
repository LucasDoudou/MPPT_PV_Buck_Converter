# Written by Tahmid Mahbub
#
# https://www.batronix.com/pdf/Rigol/ProgrammingGuide/DP800_ProgrammingGuide_EN.pdf
#
# First initialize a usb_pyvisa object.
# If there are multiple PSU's connected, use the query method in usb_pyvisa
# and then initialize the specific device.
# Then instantiate this particular power supply by passing in the usb_pyvisa
# object. Example sequency below:
#
#   devices = usb_pyvisa.query()
#   print(devices)  # Now check the addresses and IDNs
#   ADDR1 = # from devices output
#   ADDR2 = # from devices output
#
#   dp832_1 = keysight_n5769a(usb_pyvisa(ADDR1))
#   dp832_2 = keysight_n5769a(usb_pyvisa(ADDR2))


# TODO: Add debug prints

class keysight_n5769a_usb():
    def __init__(self, usb_pyvisa):
        self.usb = usb_pyvisa
        self.num_channels = 1

    def setVoltage(self, value):
        self.usb.write(f":VOLT {value}")

    def readVoltage(self):
        return float(self.usb.read(":MEAS:VOLT?"))

    def setCurrent(self, value):
        self.usb.write(f":CURR {value}")

    def readCurrent(self):
        return float(self.usb.read(":MEAS:CURR?"))

    def activate(self):
        self.usb.write(":OUTP ON")

    def deactivate(self):
        self.usb.write(":OUTP OFF")

    def activateAll(self):
        self.activate()

    def deactivateAll(self):
        self.deactivate()
