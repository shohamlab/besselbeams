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
import numpy as np
import matplotlib.pyplot as plt
import time
import datetime
import csv

DEFAULT_MEADOWLARK_API_DIR = r'C:\Program Files\Meadowlark Optics\Blink OverDrive Plus\SDK'
DEFAULT_LINEAR_LUT_PATH = 'linear.lut'


def grating(size, n, gray_level, region='all'):
    if gray_level not in range(256):
        raise ValueError('gray_level must be uint8')
    g = np.zeros(size, dtype=np.uint8)
    for i in range(n):
        g[i::n*2, :] = np.uint8(gray_level)
    if region != 'all' and region in range(64):
        rx = size[0] // 8
        ry = size[1] // 8
        i = region % 8
        j = region // 8
        mask = np.zeros(size)
        mask[rx*i:rx*i+rx, ry*j:ry*j+ry] = 1
        g = g * mask
    return g
    


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
    res = list(filter(lambda s: ('USB' in s), rm.list_resources()))  # List USB resources
    if len(res) is 0:
        rm = visa.ResourceManager()  # Try non pyvisa backend
    res = list(filter(lambda s: ('USB' in s), rm.list_resources()))  # List USB resources
    if len(res) is 0:
        sys.exit('No USB devices detected. Ensure there is a libusb-X.X.dll on your PATH.')
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

    print('Looking for Blink_C_wrapper.dll in', DEFAULT_MEADOWLARK_API_DIR, '...')
    if not os.path.exists(DEFAULT_MEADOWLARK_API_DIR) or 'Blink_C_wrapper.dll' not in os.listdir(DEFAULT_MEADOWLARK_API_DIR):
        api_dir = input("...Couldn't find it. Provide the absolute path to the folder where the DLL can be found: ")
    else:
        api_dir = DEFAULT_MEADOWLARK_API_DIR
    if not os.path.exists(api_dir):
        sys.exit('\nInvalid Meadowlark SDK directory: {}'.format(api_dir))    
    os.environ['path'] += ';' + api_dir
    
    blink = Blink(os.path.join(api_dir, 'Blink_C_wrapper.dll'))
    
    print('...API loaded!')
    
    n_boards, status = blink.Create_SDK()
    print('{} board(s) found (will only use first device), Status Code {}'.format(n_boards, status))
    
    if n_boards <= 0:
        sys.exit('\nFailed to connect to SLM.')
    
    slm_dimensions = blink.Read_SLM_dimensions()
    print('SLM dimensions: ', slm_dimensions)
    
    if not os.path.exists(DEFAULT_LINEAR_LUT_PATH):
        lin_lut = input('Please provide a path to a linear-in-graylevel LUT file.')
    else:
        lin_lut = DEFAULT_LINEAR_LUT_PATH
        
    blink.Load_LUT_file(lin_lut)
    
    # Configure calibration session
    
    lambda_min = int(power_meter.sense.correction.minimum_wavelength)
    lambda_max = int(power_meter.sense.correction.maximum_wavelength)
    
    wavelength = 0
    while wavelength not in range(lambda_min, lambda_max):
        wavelength = int(input('Calibration wavelength (nm)?: '))
        if wavelength not in range(lambda_min, lambda_max):
            print('Power meter wavelength range is {} nm to {} nm.'.format(lambda_min, lambda_max))
    
    power_meter.sense.correction.wavelength = wavelength
    
    if input('Global calibration (g) or regional calibration (r)? ') == 'r':
        regions = range(64)
    else:
        regions = ['all']
    
    g_pitch = int(input('Please select an initial pitch for the calibration grating (in pixels).\nA pitch of 2 to 8 is suitable when using a 100 mm Fourier lens: ') or 4)
    g = grating(slm_dimensions, g_pitch, 255)
    
    print()
    if len(regions) > 1:  # if 1st order measurement
        print('Please configure your optical system for 1st order measurement.')
        print('The light reflected from the SLM should form several spots. Arrange the iris and power meter such that only the spot first from the center is detected.')
        print("NOTE THAT THE SLM MUST BE OVERFILLED COMPLETELY FOR REGIONAL CALIBRATION.")
    else:
        print("Please configure your optical system for 0th order measurement.")
        print('The light reflected from the SLM should form several spots. Arrange the iris and power meter such that only the center spot is detected.')
    
    blink.Write_image(g.flatten(order='F'))
    
    v = None
    while True:
        v = input('\nEnter a number to change the pitch of the grating to suit your needs (larger number -> smaller spacing between spots), or enter "y" when the setup is complete to begin calibration file generation: ')
        if v == 'y':
            break
        if int(v) in range(256):
            g_pitch = int(v)
            g = grating(slm_dimensions, g_pitch, 255)
            blink.Write_image(g.flatten(order='F'))

    date = datetime.datetime.now().strftime("%m-%d-%Y-%H-%M-%S")
    output_dir = 'slm-calib-' + str(wavelength) + 'nm-' + str(date)
    os.mkdir(output_dir)
    print('\rSaving Meadowlark calibration files to', output_dir)
    
    for region in regions:
        print('\n Recording 0th order power for region', region)
        gray_levels = range(256)
        zero_order_pwr = np.empty(256)
        for i, gray_level in enumerate(gray_levels):
            g = grating(slm_dimensions, g_pitch, gray_level, region=region)
            blink.Write_image(g.flatten(order='F'))
            time.sleep(0.05)  # Generous SLM settling time
            pwr = power_meter.read * 1000  # mW
            print("{} - {} {} mW".format(str(gray_level).zfill(3), '|'*int(pwr / 2.5), str(pwr)[0:5]))
            zero_order_pwr[i] = pwr
        if region == 'all':
            rstr = '0'
        else:
            rstr = str(region)
        with open(os.path.join(output_dir, 'Raw{}.csv'.format(rstr)), 'a') as file:
            writer = csv.writer(file)
            for d, p in zip(gray_levels, zero_order_pwr):
                writer.writerow([str(d), str(p)])
    
    print('\rDone! calibration data saved to', output_dir)
    

