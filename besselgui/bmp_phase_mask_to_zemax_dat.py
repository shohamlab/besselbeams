# -*- coding: utf-8 -*-
"""
Created on Thu Dec 14 16:30:51 2023

@author: tuckes06
"""

import os
import numpy
import imageio
import numpy as np

def bmp_to_dat(path_to_bmp: str, output_dat_path=None, pixel_size_um=15):
    if os.path.exists(path_to_bmp):
        if output_dat_path is None:
            output_dat_path = path_to_bmp.split('.')[0] + '.dat'
        im = imageio.v2.imread(path_to_bmp)
        if len(im.shape) > 2:
            z = im[:, :, 0]
        else:
            z = im
        n = z.size  # Lines in resulting dat file
        print('Saving file to', output_dat_path)
        with open(output_dat_path, 'w') as f:
            f.write('{} {} {} {} 0.0 0.0\n'.format(z.shape[0], z.shape[1], pixel_size_um * 10**-3, pixel_size_um * 10**-3))
            for i, dp in enumerate(z.flatten()):
                v = (dp / 255) * np.pi 
                f.write('{} 0.0 0.0 0.0 0\n'.format(v))
                            
                
if __name__ == "__main__":
    bmp_to_dat(r"R:\shohas01lab\shohas01labspace\Darnel\Holography\SLM\holograms\1st_order_spots\spots456.bmp", output_dat_path='spots456.dat')
    # bmp_to_dat(r"R:\shohas01lab\shohas01labspace\Darnel\Holography\SLM\holograms\1st_order_spots\spots264.bmp", output_dat_path='spots264.dat')
