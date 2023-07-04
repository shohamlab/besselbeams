import tkinter as tk
import numpy as np
import random
from numba import jit
import time
import cv2


def generate_mask(parameters: dict) -> np.ndarray:
    ellip_radians = (
        parameters['mask-ellipticity'][0] * np.pi / 180,
        parameters['mask-ellipticity'][1] * np.pi / 180
    )
    ax1 = axicon_mask(
            parameters['slm-dimensions'],
            parameters['period-1'],
            ellip_radians,
            parameters['mask-offset']
    )
    return ax1
    
def axicon_mask(dimensions: np.ndarray, period: int, alpha: tuple, offset: tuple) -> np.ndarray:
    mask = np.zeros(dimensions).astype(np.uint16)
    _axicon_mask(mask, period, *alpha, *offset)
    mask = ((mask / np.max(mask)) * 255).astype(np.uint16)
    return mask

@jit
def _axicon_mask(mask: np.ndarray, period: int, alpha_x: float, alpha_y: float, offset_x: int, offset_y: int):
    holo_x: int = mask.shape[0] // 2
    holo_y: int = mask.shape[1] // 2
    b2_x = np.cos(alpha_x)**2
    b2_y = np.cos(alpha_y)**2
    for i, x in enumerate(np.linspace(-holo_x, holo_x, mask.shape[0]).astype(np.float32)):
        for j, y in enumerate(np.linspace(-holo_y, holo_y, mask.shape[1]).astype(np.float32)):
            mask[i, j] = period - int(np.sqrt(b2_x * (x + offset_x)**2 + b2_y * (y + offset_y)**2)) % period

class BesselGui(tk.Tk):
    
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title('BesselGUI v0.1')
        self.iconbitmap('icon.ico')
        # self.resizable(False, False)
        
        self._statusbar = StatusBar(self)
        self._statusbar.pack(expand=True, fill=tk.BOTH)
        self._statusbar.set('Starting...')
        
        self._frame_left = AxiconParamFrame(self)

        self._frame_right = tk.Frame(self)
        
        self._bmp_display = BmpDisplay(self._frame_right)
        
        self._frame_buttons = tk.Frame(self._frame_right)
        self._btn_upload = tk.Button(self._frame_buttons, text='Upload')
        self._btn_upload.pack(side=tk.LEFT)
        self._btn_export = tk.Button(self._frame_buttons, text='Export')
        self._btn_export.pack(side=tk.LEFT)
        self._frame_buttons.pack(side=tk.BOTTOM)
        self._bmp_display.pack()
            
        self._frame_left.pack(side=tk.LEFT)
        self._frame_right.pack(side=tk.RIGHT)
        
        # TODO load from JSON to save state
        self._frame_left.insert_params({
            'slm-dimensions': (1152, 960),
            'period-1': 30,
            'axicon-2-enabled': False,
            'period-2': 32,
            'mask-offset': (0, 0),
            'mask-ellipticity': (0.0, 0.0),
        })
        self.update()
        
    def update(self):
        try:
            start = time.time()
            mask = generate_mask(self._frame_left.get_parameters())
            self._statusbar.set('Generated phase mask in {} s.'.format(str(time.time() - start)[0:5]))
            self._bmp_display.set_image(mask)
        except AttributeError:
            pass # Callback not set up yet
        


class StatusBar(tk.Frame):
    
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.label = tk.Label(self)
        self.label.pack(side=tk.LEFT)
        self.pack(side=tk.BOTTOM, fill=tk.X)
        
    def set(self, newText):
        self.label.config(text=newText)

    def clear(self):
        self.label.config(text="")


class AxiconParamFrame(tk.Frame):

    def __init__(self, *args, **kwargs):
        
        if type(args[0]).__name__ != 'BesselGui':
            raise Exception('AxiconParamFrame must be a child of BesselGui object')
        self.parent = args[0]
        
        tk.Frame.__init__(self, *args, **kwargs)

        self._dim_x = tk.IntVar(self, value=920)
        self._dim_y = tk.IntVar(self, value=1152)
        self._dim_x.trace_add('write', callback=self.update)
        self._dim_y.trace_add('write', callback=self.update)

        self._frame_dim = tk.Frame(self)
        self._label_dim = tk.Label(self._frame_dim, text='SLM dimensions')
        self._label_dim.grid(row=0, column=0)
        self._spinbox_dim_x = tk.Spinbox(self._frame_dim, relief=tk.FLAT, width=10, from_=1, to_=2048, textvariable=self._dim_x)
        self._spinbox_dim_x.grid(row=0, column=1)
        self._label_dim2 = tk.Label(self._frame_dim, text=' x ')
        self._label_dim2.grid(row=0, column=2)
        self._spinbox_dim_y = tk.Spinbox(self._frame_dim, relief=tk.FLAT, width=10, from_=1, to_=2048, textvariable=self._dim_y)
        self._spinbox_dim_y.grid(row=0, column=3)
        self._frame_dim.grid(row=0, column=0)

        self._period1 = tk.IntVar(self, value=30)
        self._period1.trace_add('write', callback=self.update)

        self._frame_period1 = tk.Frame(self)
        self._label_period1 = tk.Label(self._frame_period1, text='Axicon 1 period')
        self._label_period1.grid(row=0, column=0)
        self._spinbox_period1 = tk.Spinbox(self._frame_period1, relief=tk.FLAT, width=10, from_=1, to_=2048, textvariable=self._period1)
        self._spinbox_period1.grid(row=0, column=1)
        self._frame_period1.grid(row=1, column=0)

        self._period2 = tk.IntVar(self, value=32)
        self._period2.trace_add('write', callback=self.update)

        self._frame_period2 = tk.Frame(self)
        self._axicon_2_is_enabled = tk.IntVar(self, value=False)
        self._checkbox_period2 = tk.Checkbutton(self._frame_period2, text='Enable Axicon 2', var=self._axicon_2_is_enabled)
        self._checkbox_period2.grid(row=0, columnspan=2)
        self._label_period2 = tk.Label(self._frame_period2, text='Axicon 2 period')
        self._label_period2.grid(row=1, column=0)
        self._spinbox_period2 = tk.Spinbox(self._frame_period2, relief=tk.FLAT, width=10, from_=1, to_=2048, textvariable=self._period2)
        self._spinbox_period2.grid(row=1, column=1)
        self._frame_period2.grid(row=2, column=0)

        self._offset_x = tk.IntVar(self, value=0)
        self._offset_y = tk.IntVar(self, value=0)
        self._offset_x.trace_add('write', callback=self.update)
        self._offset_y.trace_add('write', callback=self.update)
        

        self._frame_offset = tk.Frame(self)
        self._label_offset = tk.Label(self._frame_offset, text='Center offset')
        self._label_offset.grid(row=0, column=0)
        self._spinbox_offset_x = tk.Spinbox(self._frame_offset, relief=tk.FLAT, width=10, from_=-1024, to_=1024, textvariable=self._offset_x)
        self._spinbox_offset_x.grid(row=0, column=1)
        self._label_offset2 = tk.Label(self._frame_offset, text=', ')
        self._label_offset2.grid(row=0, column=2)
        self._spinbox_offset_y = tk.Spinbox(self._frame_offset, relief=tk.FLAT, width=10, from_=-1024, to_=1024, textvariable=self._offset_y)
        self._spinbox_offset_y.grid(row=0, column=3)
        self._frame_offset.grid(row=3, column=0)

        self._ellip_x = tk.DoubleVar(self, value=0)
        self._ellip_y = tk.DoubleVar(self, value=0)
        self._ellip_x.trace_add('write', callback=self.update)
        self._ellip_y.trace_add('write', callback=self.update)

        self._frame_ellip = tk.Frame(self)
        self._label_ellip = tk.Label(self._frame_ellip, text='Ellipticity (α)')
        self._label_ellip.grid(row=0, column=0)
        self._spinbox_ellip_x = tk.Spinbox(self._frame_ellip, relief=tk.FLAT, width=10, from_=0, to_=120, increment=0.1, textvariable=self._ellip_x)
        self._spinbox_ellip_x.grid(row=0, column=1)
        self._label_ellip2 = tk.Label(self._frame_ellip, text=', ')
        self._label_ellip2.grid(row=0, column=2)
        self._spinbox_ellip_y = tk.Spinbox(self._frame_ellip, relief=tk.FLAT, width=10, from_=0, to_=120, increment=0.1, textvariable=self._ellip_y)
        self._spinbox_ellip_y.grid(row=0, column=3)
        self._frame_ellip.grid(row=4, column=0)

    def update(self, var, index, mode):
        self.parent.update()

    def get_parameters(self) -> dict:
        return {
            'slm-dimensions': (int(self._dim_x.get()), int(self._dim_y.get())),
            'period-1': int(self._period1.get()),
            'axicon-2-enabled': bool(self._axicon_2_is_enabled.get()),
            'period-2': int(self._period2.get()),
            'mask-offset': (int(self._offset_x.get()), int(self._offset_y.get())),
            'mask-ellipticity': (float(self._ellip_x.get()), float(self._ellip_y.get())),
        }
    
    def insert_params(self, params: dict):
        self._dim_x.set(params['slm-dimensions'][0])
        self._dim_y.set(params['slm-dimensions'][1])
        self._period1.set(params['period-1'])
        self._axicon_2_is_enabled.set(params['axicon-2-enabled'])
        self._period2.set(params['period-2'])
        self._offset_x.set(params['mask-offset'][0])
        self._offset_y.set(params['mask-offset'][1])
        self._ellip_x.set(float(params['mask-ellipticity'][0]))
        self._ellip_y.set(float(params['mask-ellipticity'][1]))


class BmpDisplay(tk.Frame):

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.width=0
        self.height=0
        self.canvas = tk.Canvas(self)
        self.image = tk.PhotoImage(width=self.width, height=self.height)
        self._container = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image)
        self.canvas.pack()

    def set_image(self, img: np.ndarray, downsample_factor=4):
        img = img[0::downsample_factor, 0::downsample_factor]
        self.width = img.shape[0]
        self.height = img.shape[1]
        self.image = tk.PhotoImage(width=self.width, height=self.height)
        img = img.astype(int).flatten(order='F')
        rgb_colors = ([img[j], img[j], img[j]] for j in range(0, len(img)))
        pixels=" ".join(("{"+" ".join(('#%02x%02x%02x' %
            tuple(next(rgb_colors)) for i in range(self.width)))+"}" for j in range(self.height)))
        self.image.put(pixels, (0, 0, self.width - 1, self.height - 1))
        self.canvas.itemconfig(self._container, image=self.image)


if __name__ == '__main__':
    root = BesselGui()
    root.mainloop()
