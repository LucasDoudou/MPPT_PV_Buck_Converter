import sys
import os
import signal
import numpy as np
from time import sleep
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

# Program operates by setting one input current limit and then
# sweeping the eload voltage.

# Set the current limit, corresponding to PV panel's ISC. 77% -> 4Amps
SWEEP_INPUT_CURR_LIMIT = 4

# Perform sweep at predefined voltages, from panel's Voc down to 0.
PV_VOC = 24.3
# Range of the inputs SWEEPING
SWEEP_INPUT_VOLTS = np.flip(np.hstack([np.linspace(0.5, 11, 4, endpoint=True),
                                       np.arange(12, 20),
                                       np.arange(20, 22.5, 0.1),
                                       np.arange(22.5, PV_VOC, 0.2),
                                       PV_VOC
                                       ]))

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
TEST_NAME = "ivsweep"  # name for log files
LOG_FILENAME = f"{TEST_NAME}.csv"
IMG_FILENAME = f"{TEST_NAME}.png"

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

# Initialize DataFrame.
# New data will be added to this DataFrame.
data_log = pd.DataFrame({"Vout":    [],
                         "Iout":    [],
                         "Pout":    []
                         })

##################################################
# Run sweeps:
sweep_count = 0

usb_eload.deactivate(chan=ELOAD_CH)

# Set the power supply voltage and current, and turn it on:
usb_psu.setCurrent(SWEEP_INPUT_CURR_LIMIT)
usb_psu.setVoltage(PV_VOC)
usb_psu.activate()

usb_eload.setMode(OUTPUT_TYPE, remote_sense=False, chan=ELOAD_CH)
usb_eload.setValue(PV_VOC, chan=ELOAD_CH)
# usb_eload.setSlew(200, chan=ELOAD_CH)

for input_volts in SWEEP_INPUT_VOLTS:
    sweep_count += 1  # Keep track of test number
    print(f"Sweep {sweep_count}/{len(SWEEP_INPUT_VOLTS)}: {input_volts:.2f} V")

    usb_psu.setCurrent(1)
    sleep(SETTLE_TIME)
    usb_eload.setValue(input_volts, chan=ELOAD_CH)
    usb_eload.activate(chan=ELOAD_CH)
    sleep(SETTLE_TIME)
    usb_psu.setCurrent(SWEEP_INPUT_CURR_LIMIT)

    # Let load run for this long:
    sleep(RUNTIME)

    # Read data from eload:
    vout = usb_eload.readVoltage(chan=ELOAD_CH)
    iout = usb_eload.readCurrent(chan=ELOAD_CH)
    pout = vout * iout

    usb_eload.deactivate(chan=ELOAD_CH)

    # Append results to DataFrame:
    new_data = pd.DataFrame({"Vout":    [vout],
                             "Iout":    [iout],
                             "Pout":    [pout]
                             })

    data_log = pd.concat([data_log, new_data], ignore_index=True)

##################################################
# Close PSU and eload.
# Passing None, None indicates this is not a signal (SIGINT).
timeToExit(None, None)

##################################################
# Save data:
data_log.to_csv(logfile, index=False)
##################################################
# Plot Vout and Efficiency curves:

sweep_v = data_log["Vout"].tolist()
sweep_i = data_log["Iout"].tolist()
sweep_p = data_log["Pout"].tolist()

max_p = max(sweep_p)
max_v = sweep_v[np.argmax(sweep_p)]
print(f"Max power point = {max_p:.1f} W at {max_v:.1f} V")

fig, axV = plt.subplots(figsize=(10, 6))
color = 'tab:blue'
axV.set_xlabel('Voltage [V]')
axV.set_ylabel('Current [A]', color=color)
axV.plot(sweep_v, sweep_i, color=color)
axV.tick_params(axis='y', labelcolor=color)

axP = axV.twinx()

color = 'tab:red'
axP.set_ylabel('Power [W]', color=color)
axP.plot(sweep_v, sweep_p, color=color)
axP.tick_params(axis='y', labelcolor=color)

fig.suptitle('PV sweep', fontweight="bold")

plt.tight_layout()
plt.savefig(imgfile, dpi=200)   # Save plots

##################################################
# Show plot:
plt.show()
