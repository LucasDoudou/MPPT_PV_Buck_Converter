import sys
import os
import signal
from time import sleep
import pandas as pd
from matplotlib import pyplot as plt
##################################################
from usb_pyvisa_wrapper import usb_pyvisa
from keysight_n5769a import keysight_n5769a_usb as usb_n5769a
from keysight_el34243a import keysight_el34243a_usb as usb_el34243a
##################################################
PAUSE_BETWEEN_VSTEPS = True

# Test parameters:
script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

ELOAD_CH = 2  # Eload channel to connect to

# Program operates by setting one input current limit and then
# sweeping the eload voltage.

# Set the current limit for the PSU
PSU_CURRENT_LIMIT = 12

# Perform sweep at predefined voltages and powers
SWEEP_INPUT_VOLTS = [16, 18, 20, 22, 24]
SWEEP_OUTPUT_POWERS = [50, 62.5, 75, 87.5, 100]  # , 75, 87.5, 100]
SWEEP_OUTPUT_CURRENTS = [p/12 for p in SWEEP_OUTPUT_POWERS]
SWEEP_PARAMS = SWEEP_OUTPUT_CURRENTS

# Define the eload's mode of sweep. The options are:
#   "CURR"  :   constant current
#   "RES"   :   constant resistance
#   "POW"   :   constant power
#   "VOLT"   :  constant voltage
OUTPUT_TYPE = "CURR"  # "CURR", "RES", "POW" or "VOLT"
unitdict = {"CURR": "A", "RES": "ohm", "POW": "W", "VOLT": "V"}
unit = unitdict[OUTPUT_TYPE]

# Define how long to let the load run before taking a measurement:
RUNTIME = 1  # measurement taken after this many seconds

SETTLE_TIME = 1  # wait time after changing equipment settings

# Define the names for the output files:
#   log file contains all the data in a csv file
#   img file is the generated png plots
TEST_NAME = "effsweep"  # name for log files
LOG_FILENAME = f"{TEST_NAME}.csv"
IMG_FILENAME = f"{TEST_NAME}.png"

# Save directory for the above files
#   Files are saved under SAVE_DIRECTORY
SAVE_DIRECTORY = script_directory

PAUSE_PROMPT = "go"
INP_PROMPT = f"Change duty ratio and then type `{PAUSE_PROMPT}` to proceed... "

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
data_log = pd.DataFrame({"Sweep":   [],
                         "Vin":     [],
                         "Iin":     [],
                         "Pin":     [],
                         "Vout":    [],
                         "Iout":    [],
                         "Pout":    [],
                         "Eff":     []})

##################################################
# Run sweeps:
sweep_count = 0

usb_eload.deactivate(chan=ELOAD_CH)

# Set the power supply voltage and current, and turn it on:
usb_psu.setCurrent(PSU_CURRENT_LIMIT)

print("==========================")
print("  Starting test...")
print("==========================")
usb_eload.setMode(OUTPUT_TYPE, remote_sense=True, chan=ELOAD_CH)
for input_volts in SWEEP_INPUT_VOLTS:
    if PAUSE_BETWEEN_VSTEPS:
        print(f"Input voltage to be set to {input_volts} V")
        inp = input(INP_PROMPT)
        while (inp != PAUSE_PROMPT):
            inp = input(INP_PROMPT)
    sweep_count += 1  # Keep track of test number
    print(f"Sweep {sweep_count}/{len(SWEEP_INPUT_VOLTS)}: {input_volts:.2f} V")

    usb_psu.setVoltage(input_volts)
    usb_psu.activate()
    sleep(SETTLE_TIME)

    for param in SWEEP_PARAMS:
        usb_eload.setValue(param, chan=ELOAD_CH)
        usb_eload.activate(chan=ELOAD_CH)

        # Let load run for this long:
        sleep(RUNTIME)

        # Read data from psu and eload:
        vin = usb_psu.readVoltage()
        iin = usb_psu.readCurrent()
        pin = vin * iin
        vout = usb_eload.readVoltage(chan=ELOAD_CH)
        iout = usb_eload.readCurrent(chan=ELOAD_CH)
        pout = vout * iout

        eff = pout / pin * 100 if pin > 0 else -1

        usb_eload.deactivate(chan=ELOAD_CH)

        # Print current state:
        print(f"  psu: {input_volts :.2f} V, "
              f"eload: {param :.2f} {unit}, "
              f"pin: {pin :.2f},"
              f"pout: {pout :2f},"
              f"{eff = :.2f} %")

        # Append results to DataFrame:
        new_data = pd.DataFrame({"Sweep":   [sweep_count],
                                 "Vin":     [vin],
                                 "Iin":     [iin],
                                 "Pin":     [pin],
                                 "Vout":    [vout],
                                 "Iout":    [iout],
                                 "Pout":    [pout],
                                 "Eff":     [eff]})

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
fig, ax = plt.subplots(1, 2, figsize=(10, 6))
vax = ax[0]     # Vout vs Iout axis
effax = ax[1]   # Eff vs Pout axis

num_sweeps = len(SWEEP_INPUT_VOLTS)
lgd = []
for sweep in [1 + x for x in range(num_sweeps)]:
    # Get data for one sweep:
    res = data_log[data_log["Sweep"] == sweep]
    vin = res.iloc[0]["Vin"]        # Get input voltage
    itgt = res["Iout"].tolist()     # Find output currents
    vouts = res["Vout"].tolist()    # Find output voltages
    effs = res["Eff"].tolist()      # Find efficiencies
    pouts = res["Pout"].tolist()    # Find output powers

    lgd.append(f"Vin = {vin :.1f} V")   # Add Vin info to legend
    vax.plot(itgt, vouts, 'o-', linewidth=2)    # Plot Vout vs Iout
    effax.plot(pouts, effs, 'o-', linewidth=2)  # Plot Eff vs Pout

# Format plots:
vax.set_xlabel("Output Current [A]")
vax.set_ylabel("Output Voltage [V]")
vax.set_title("Voltage across load sweep")
vax.legend(lgd)
effax.set_xlabel("Output power [W]")
effax.set_ylabel("Efficiency [%]")
effax.set_title("Efficiency across load sweep")
effax.legend(lgd)

plt.tight_layout()
plt.savefig(imgfile, dpi=200)   # Save plots

##################################################
# Show plot:
plt.show()
