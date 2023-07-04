import tkinter as tk
import tkinter.filedialog
import numpy as np
import random
from numba import jit
import time
import ctypes
import os


class Meadowlark_Blink_C_wrapper():
    
    def __init__(self, path_to_api: str):
        self.connected = False
        self.api_loaded = False
        try:
            self._lib = ctypes.cdll.LoadLibrary(path_to_api)
        except OSError:
            return
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
    return ax1.astype(np.uint8)
    
def axicon_mask(dimensions: np.ndarray, period: int, alpha: tuple, offset: tuple, greylevel: int = 255) -> np.ndarray:
    mask = np.zeros(dimensions).astype(np.uint16)
    _axicon_mask(mask, period, *alpha, *offset)
    mask = ((mask / np.max(mask)) * min(greylevel, 255)).astype(np.uint16)
    return mask

@jit
def _axicon_mask(mask: np.ndarray, period: int, alpha_x: float, alpha_y: float, offset_x: int, offset_y: int):
    holo_x: int = mask.shape[0] // 2
    holo_y: int = mask.shape[1] // 2
    b2_x: float = np.cos(alpha_x)**2
    b2_y: float = np.cos(alpha_y)**2
    for i, x in enumerate(np.linspace(-holo_x, holo_x, mask.shape[0]).astype(np.float32)):
        for j, y in enumerate(np.linspace(-holo_y, holo_y, mask.shape[1]).astype(np.float32)):
            mask[i, j] = period - int(np.sqrt(b2_x * (x + offset_x)**2 + b2_y * (y + offset_y)**2)) % period


class BesselGui(tk.Tk):
    
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title('BesselGUI v0.1')
        self.iconbitmap('icon.ico')
        self.resizable(False, False)
        
        # -- SLM status -----
        self.connected = False
        self.path_to_meadowlark_lib = None  # TODO generalize to other SLMs... but there are enough SLM apps. Maybe TODO use slmsuite as backend
        self.path_to_calib_file = None
        self.slm_api = None
        # -------------------
        
        self._statusbar = StatusBar(self)
        self._statusbar.pack(expand=True, fill=tk.BOTH)
        self._statusbar.set('Starting...')
        
        self._frame_params = AxiconParamFrame(self)
        self._frame_right = tk.Frame(self)
        
        self._frame_status = tk.Frame(self._frame_right)
        self._btn_connect = tk.Button(self._frame_status, text='Connect to SLM', command=self.connect)
        self._btn_connect.pack(side=tk.LEFT)
        self._label_temp = tk.Label(self._frame_status, text="Not Connected", fg='red')
        self._label_temp.pack(side=tk.RIGHT)
        self._frame_status.grid(row=0)
        
        self._bmp_display = BmpDisplay(self._frame_right)
        self._bmp_display.grid(row=1)
        
#        self._frame_buttons = tk.Frame(self._frame_right)
#        self._btn_upload = tk.Button(self._frame_buttons, text='Upload')
#        self._btn_upload.pack(side=tk.LEFT)
#        self._btn_export = tk.Button(self._frame_buttons, text='Export')
#        self._btn_export.pack(side=tk.LEFT)
#        self._frame_buttons.grid(row=2)
            
        self._frame_params.pack(side=tk.LEFT)
        self._frame_right.pack(side=tk.RIGHT)
        
        # TODO load from JSON to save state
        self._frame_params.insert_params({
            'slm-dimensions': (1920, 1152),
            'period-1': 30,
            'axicon-2-enabled': False,
            'period-2': 32,
            'mask-offset': (0, 0),
            'mask-ellipticity': (0.0, 0.0),
        })
        self.update()
    
    def connect(self):
        api_dir = tk.filedialog.askdirectory(
                title='Select Meadowlark SDK directory',
                initialdir=r'C:\Program Files\Meadowlark Optics\Blink OverDrive Plus\SDK'
        )
        if not os.path.exists(api_dir):
            return
        os.environ['path'] += ';' + api_dir
        self.path_to_meadowlark_lib = os.path.join(api_dir, 'Blink_C_wrapper.dll')
        self._statusbar.set('Loading {}...'.format(self.path_to_meadowlark_lib))
        self.slm_api = Meadowlark_Blink_C_wrapper(self.path_to_meadowlark_lib)
        if self.slm_api.api_loaded:
            self._statusbar.set('SLM Connected!')
        else:
            self._statusbar.set('Failed to load API from {}'.format(self.path_to_meadowlark_lib))
            self.slm_api = None
            return
        n_boards_found, status = self.slm_api.Create_SDK()
        if n_boards_found == -1:
            self._statusbar.set('Failed to connect to SLM. Try reinstalling the SLM via Windows Device Manager.')
            return
        self._statusbar.set('{} board(s) found (will only use first device), Status Code {}'.format(n_boards_found, status))
        self.path_to_calib_file = tk.filedialog.askopenfilename(
                title='Select calibration LUT',
                filetypes=[("Meadowlark LUT files", ".lut .csv")],
                initialdir=r'C:\Program Files\Meadowlark Optics\Blink OverDrive Plus\LUT Files'
        )
        if os.path.exists(self.path_to_calib_file):
            if self.slm_api.Load_LUT_file(self.path_to_calib_file) == 0:
                self._statusbar.set('Loaded calibration LUT from {}'.format(self.path_to_calib_file))
            else:
                self._statusbar.set('Failed to calibrate using {}'.format(self.path_to_calib_file))
        # If dimensions can be retrieved from the SLM, fix the dimension spinboxes
        if self.slm_api.Read_SLM_dimensions()[0] > -1 and self.slm_api.Read_SLM_dimensions()[1] > -1:
            self._frame_params.fix_dims(self.slm_api.Read_SLM_dimensions())
        self.after(1000, self.poll_slm)  # Start polling SLM
        self.update()
        
    def update(self):
        try:
            start = time.time()
            mask = generate_mask(self._frame_params.get_parameters())
            self._statusbar.set('Generated phase mask in {} s.'.format(str(time.time() - start)[0:5]))
            self._bmp_display.set_image(mask)
            if self.slm_api.api_loaded:
                if self.slm_api.Write_image(mask.flatten(order='F')) == 0:
                    print('Phase mask uploaded with Error Code 0')
        except Exception as e:  # TODO something less stupid
            pass # Callback not set up yet
    
    def poll_slm(self):
        """
        Every second, checks on SLM temperature and therefore on connectivity status.
        """
        temp = self.slm_api.Read_SLM_temperature()
        if temp > -1:
            self._label_temp.config(text='SLM Connected ({0:.2f} °C)'.format(temp), fg='blue')
            self.after(1000, self.poll_slm)
        else:
            self._label_temp.config(text='SLM Disconnected', fg='red')
            self._frame_params.unfix_dims()


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
    
    def unfix_dims(self):
        self._spinbox_dim_x.config(state='enable', relief=tk.FLAT)
        self._spinbox_dim_y.config(state='enable', relief=tk.FLAT)
    
    def fix_dims(self, dims: tuple):
        self._dim_x.set(dims[0])
        self._dim_y.set(dims[1])
        self._spinbox_dim_x.config(state='disabled', relief=tk.GROOVE)
        self._spinbox_dim_y.config(state='disabled', relief=tk.GROOVE)
    
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
        self.canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.canvas.pack()

    def set_image(self, img: np.ndarray, downsample_factor=6):
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
