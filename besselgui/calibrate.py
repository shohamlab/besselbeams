# -*- coding: utf-8 -*-
"""
Created on Fri Jul  7 23:26:34 2023

@author: sstucker

If this script raises issues about USB backend, ensure a "libusb-X.X.dll"
is on your PATH. The library can be retrieved via pip.

"""

import sys
import os
import usb
import pyvisa as visa
from ThorlabsPM100 import ThorlabsPM100
from Meadowlark_Blink_C import Blink


DEFAULT_MEADOWLARK_API_DIR = r'C:\Program Files\Meadowlark Optics\Blink OverDrive Plus\SDK'


if __name__ == "__main__":
    print('===============================================')
    print('Meadowlark SLM calibration tool')
    print('===============================================')
    print('sstucker@nyu.edu')
    print('July 8 2023\n')
    c="""NOTE: this tool requires the installation of Meadowlark Blink software in
addition to the Python environment specified by requirements.txt. If this script
raises issues about USB backend, ensure a "libusb-X.X.dll" is on your PATH. The
library can be retrieved via pip.
\nPlug in a PM100 type Thorlabs power meter via USB and power on the Meadowlark
SLM prior to running this script."""
    print(c)
    print('===============================================\n')
    
    # Connect to PM100
    
    rm = visa.ResourceManager('@py')
    res = rm.list_resources()
    
    res = list(filter(lambda s: ('USB' in s), res))
    if len(res) is 0:
        sys.exit('No USB devices detected.')
    elif len(res) > 1:
        print('{} USB devices detected: {}.'.format(len(res), res))
        index = input('Identify the PM100 from the list (i.e. "1", "2", ...): ')
        pm_res = res[str(index)]
    else:
        pm_res = res[0]
    
    inst = rm.open_resource(pm_res)
    
    power_meter = ThorlabsPM100(inst=inst)
    inst.timeout = None
    
    print('Power meter connected:', inst.query("*IDN?"))
    power_meter.system.beeper.immediate()
    
    print('Setting mode to POW...')
    power_meter.configure.scalar.power()
    
    print('Setting average count to 100...\n')
    power_meter.sense.average.count = 100
    
    # Connect to SLM

    print('Looking for Blink_C_wrapper.dll in', DEFAULT_MEADOWLARK_API_DIR)
    if input('Will I find it? (y/n) ') in ['n', 'N', 'No', 'NO', 'no', 'nah', 'nope']:
        api_dir = input('Provide the absolute path to the folder where the DLL can be found: ')
    else:
        api_dir = DEFAULT_MEADOWLARK_API_DIR
    if not os.path.exists(api_dir):
        sys.exit('\nInvalid Meadowlark SDK directory: {}'.format(api_dir))    
    os.environ['path'] += ';' + api_dir
    
    blink = Blink(os.path.join(api_dir, 'Blink_C_wrapper.dll'))
    
    n_boards, status = blink.Create_SDK()
    print('{} board(s) found (will only use first device), Status Code {}'.format(n_boards_found, status))
    
    # Configure calibration session
    
    lambda_min = int(power_meter.sense.correction.minimum_wavelength)
    lambda_max = int(power_meter.sense.correction.maximum_wavelength)
    
    wavelength = 0
    while wavelength not in range(lambda_min, lambda_max):
        wavelength = float(input('Calibration wavelength (nm)?: '))
        if wavelength not in range(lambda_min, lambda_max):
            print('Power meter wavelength range is {} nm to {} nm.'.format(lambda_min, lambda_max))
    
    print("Current value    :", power_meter.read)



