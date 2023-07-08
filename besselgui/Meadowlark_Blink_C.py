# -*- coding: utf-8 -*-
"""
Created on Sat Jul  8 13:16:07 2023

This is a wrapper around software created by Meadowlark Optics (https://www.meadowlark.com/).

@author: sstucker
"""

import numpy as np
import ctypes

class Blink():
    
    def __init__(self, path_to_api: str):
        self.connected = False
        self.api_loaded = False
        self._lib = ctypes.cdll.LoadLibrary(path_to_api)
        self._lib.Create_SDK.argtypes = [
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p        
        ]
        self._lib.Load_LUT_file.argtypes = [
            ctypes.c_int,  # Hardware ID (should be 1)
            ctypes.c_char_p  # Path to .lut file
        ]
        self._lib.Write_image.argtypes = [
                ctypes.c_int,  # Board ID
                np.ctypeslib.ndpointer(ctypes.c_uint8, flags="C_CONTIGUOUS"), # Image buffer
                ctypes.c_uint32,  # Image size (width * height)
                ctypes.c_int,  # Wait for trigger
                ctypes.c_int,  # External pulse
                ctypes.c_uint32  # Trigger timeout (ms)
        ]
        self._lib.Read_SLM_temperature.argtypes = [ctypes.c_int]
        self._lib.Read_SLM_temperature.restype = ctypes.c_double
        self._lib.Get_image_width.argtypes = [ctypes.c_int]
        self._lib.Get_image_height.argtypes = [ctypes.c_int]
        self.api_loaded = True
        
    def Create_SDK(self, slm_bitness=12):
        if self.api_loaded:
            n_boards_found = ctypes.c_uint32()
            status = ctypes.c_int()
            try:
                self._lib.Create_SDK(
                    ctypes.c_uint32(slm_bitness),
                    ctypes.byref(n_boards_found),
                    ctypes.byref(status),
                    1,
                    1,
                    0,
                    10,  # From manual's recommendation
                    ctypes.c_char_p()  # Null calibration
                );
            except OSError:
                return -1, -1
            return n_boards_found.value, status.value
        raise Exception('Library not successfully loaded')
    
    def Load_LUT_file(self, lut_file: str):
        if self.api_loaded:
            try:
                return self._lib.Load_LUT_file(
                    1,
                    lut_file.encode('utf-8')
                );
            except OSError:
                return -1
        raise Exception('Library not successfully loaded')
        
    def Write_image(self, phase_mask):
        if self.api_loaded:
            try:
                return self._lib.Write_image(
                    1,
                    phase_mask.astype(np.uint8),
                    phase_mask.size,
                    0,
                    0,
                    5000  # 5 second timeout. Might block this long
                );
            except OSError:
                return -1
        raise Exception('Library not successfully loaded')
        
    def Read_SLM_temperature(self) -> float:
        if self.api_loaded:
            try:
                return self._lib.Read_SLM_temperature(1)
            except OSError:
                return -1
        raise Exception('Library not successfully loaded')
        
    def Read_SLM_dimensions(self) -> (int, int):
        if self.api_loaded:
            try:
                return (self._lib.Get_image_width(1), self._lib.Get_image_height(1))
            except OSError:
                return (-1, -1)
        raise Exception('Library not successfully loaded')
