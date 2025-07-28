# Written by Tahmid Mahbub

import pyvisa
# python3 -m pip install zeroconf psutil pyvisa
# https://www.ni.com/en/support/downloads/drivers/download/unpackaged.ni-visa.487530.html


class usb_pyvisa:

    ADDRESS_KEY = "addr"
    IDN_KEY = "idn"

    def __init__(self, addr=None, timeout_sec=3):
        self.addr = None
        self.dev = None
        self.idn = None
        self.initialized = False

        self.initialize(addr, timeout_sec)

    @classmethod
    def query(self):
        rm = pyvisa.ResourceManager()
        devices = []
        inst_list = rm.list_resources()
        # print(f"{inst_list = }")
        for elem in inst_list:
            if elem.find("USB") != -1:
                idn = rm.open_resource(elem).query("*IDN?")
                devices.append(
                    {usb_pyvisa.ADDRESS_KEY: elem,
                     usb_pyvisa.IDN_KEY: idn}
                )
        return devices

    @classmethod
    def getAddrFromIdn(self, idn):
        # Return first match
        devices = usb_pyvisa.query()
        for dev in devices:
            if idn in dev[usb_pyvisa.IDN_KEY]:
                return dev[usb_pyvisa.ADDRESS_KEY]

        return None

    def initialize(self, addr, timeout_sec=3):
        # Initialize device with provided address

        rm = pyvisa.ResourceManager()
        for device in self.query():
            dev_addr = device[self.ADDRESS_KEY]
            dev_idn = device[self.IDN_KEY]
            if addr == dev_addr:
                self.addr = dev_addr
                self.dev = rm.open_resource(dev_addr)
                self.dev.timeout = timeout_sec * 1000  # timeout in ms
                self.idn = dev_idn
                self.initialized = True
                break

        if self.initialized is False:
            raise Exception(f"Couldn't initialize device at {dev_addr}!")

    def write(self, command):
        if self.initialized:
            self.dev.write(command)

    def read(self, query):
        if self.initialized:
            return self.dev.query(query)
