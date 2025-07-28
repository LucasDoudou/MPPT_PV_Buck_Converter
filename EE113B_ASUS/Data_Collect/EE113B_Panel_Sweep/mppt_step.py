import sys
import os
import signal
from time import sleep, time
import pandas as pd
from matplotlib import pyplot as plt
##################################################
from usb_pyvisa_wrapper import usb_pyvisa
from keysight_n5769a import keysight_n5769a_usb as usb_n5769a
from keysight_el34243a import keysight_el34243a_usb as usb_el34243a
##################################################

# Test parameters:
script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

ELOAD_CH = 2  # Eload channel to connect to

# Define the eload's mode of sweep. The options are:
#   "CURR"  :   constant current
#   "RES"   :   constant resistance
#   "POW"   :   constant power
#   "VOLT"   :  constant voltage
OUTPUT_TYPE = "VOLT"  # "CURR", "RES", "POW" or "VOLT"

# Define how long to let the load run before taking a measurement:
RUNTIME = 1  # measurement taken after this many seconds

SETTLE_TIME = 1  # wait time after changing equipment settings

# Define the names for the output files:
#   log file contains all the data in a csv file
#   img file is the generated png plots
TEST_NAME = "effsweep"  # name for log files
LOG_FILENAME = f"{TEST_NAME}.csv"
IMG_FILENAME = f"{TEST_NAME}.png"
MPPT_FILENAME = "mppt_profile.csv"

# Save directory for the above files
#   Files are saved under SAVE_DIRECTORY
SAVE_DIRECTORY = script_directory

##################################################
# Setup:

# Saves: Vout, Iout, Pout
#   in a csv file
logfile = os.path.abspath(os.path.join(SAVE_DIRECTORY,
                                       f"{LOG_FILENAME}"))

# Saves the generated plots of Iout vs Vout and Pout vs Vout
imgfile = os.path.abspath(os.path.join(SAVE_DIRECTORY,
                                       f"{IMG_FILENAME}"))

mppt_profile_file = os.path.abspath(os.path.join(script_directory,
                                                 f"{MPPT_FILENAME}"))
# Indicates whether devices are initialized:
initialized = False

# Objects for USB-connected PSU and Eload:
usb_psu = None
usb_eload = None


##################################################
# Signal handler and exit routine:
def timeToExit(sig, frame):
    if initialized:
        # Did not catch a signal, so turn off and return
        # to program execution
        usb_eload.deactivate(chan=ELOAD_CH)
        usb_psu.setVoltage(0)
        usb_psu.setCurrent(0.1)
        usb_psu.deactivate()
    if sig is not None or frame is not None:
        # Caught a signal, so exit now
        print(sig, frame)
        sys.exit()


# If Ctrl-C is pressed while the program is running,
# the PSU and eload are turned off before exiting.
signal.signal(signal.SIGINT, timeToExit)
##################################################

# Read in MPPT profile
PV_ISC = 5.21
PV_OCV = 24.3
profile = pd.read_csv(mppt_profile_file)  # t, i
profile_t = profile.t.to_list()
profile_isc_norm = profile.isc.to_list()

# Find connected devices and print them
devices = usb_pyvisa.query()
print(devices)

# We know that 1x N5769A PSU and 1x EL34243A eload are connected.
# Find the address of the connected devices based on the
# part numbers appearing in the IDN string.
psu_addr = usb_pyvisa.getAddrFromIdn("N5769A")
eload_addr = usb_pyvisa.getAddrFromIdn("EL34243A")

# Based on the addresses found, initialize the objects:
usb_psu = usb_n5769a(usb_pyvisa(psu_addr))
usb_eload = usb_el34243a(usb_pyvisa(eload_addr))

# Done with initializing:
initialized = True

# Make sure power supply and eload outputs are off
usb_psu.deactivate()
usb_eload.deactivate(chan=ELOAD_CH)

##################################################

usb_eload.deactivate(chan=ELOAD_CH)

# Set the power supply voltage and current, and turn it on:
usb_psu.setVoltage(PV_OCV)
# usb_psu.setCurrent(PV_ISC)
usb_psu.activate()
usb_eload.setMode(OUTPUT_TYPE, remote_sense=True, chan=ELOAD_CH)
usb_eload.setValue(12, chan=ELOAD_CH)
usb_eload.activate(chan=ELOAD_CH)

print("==========================")
print("  Starting test...")
print("==========================")

# First *slowly* ramp up from 0 to the first defined current in the profile.
# This helps prevent the power supply from oscillating.
t0 = time()
tprev = 0
iprev = 0
power_sum = 0
counter = 0

# Ramp up current:
ref_i = profile_isc_norm[0] * PV_ISC
ref_t = 1
print(f"Ramping up current to {ref_i:.2f} A in {ref_t:.1f} s")
set_i = 1
iprev = 1
i_slope = (ref_i - set_i) / ref_t
while set_i < ref_i:
    current_time = time() - t0
    set_i = iprev + i_slope * current_time
    usb_psu.setCurrent(set_i)
    sleep(0.1)

tprev = 0
iprev = ref_i
t0 = time()

# Now go through the defined currents in the profile:
for t, isc_norm in zip(profile_t, profile_isc_norm):

    # Currents in the profile file are normalized to the panel's rating.
    isc = isc_norm * PV_ISC
    print(f"Step: {t} , {isc_norm} -> {isc:.2f}A")
    current_time = time() - t0
    if current_time >= t:
        usb_psu.setCurrent(isc)
        power_sum += usb_eload.readPower(chan=ELOAD_CH)
        counter += 1
    else:
        # Ramp up the current linearly:
        i_slope = (isc - iprev) / (t - tprev) if t > tprev else 0
        while current_time < t:
            # Ramp up until next defined time point:
            current_time = time() - t0
            iset = iprev + i_slope * (current_time - tprev)
            usb_psu.setCurrent(iset)
            power_sum += usb_eload.readPower(chan=ELOAD_CH)
            counter += 1
    iprev = isc
    tprev = t

    if counter == 0:
        counter = 1
    avg_power = power_sum/counter
    print(f"Avg power = {avg_power:.2f} W")

##################################################
# Close PSU and eload.
# Passing None, None indicates this is not a signal (SIGINT).
timeToExit(None, None)
##################################################