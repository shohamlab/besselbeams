import tkinter as tk
import numpy as np
import random


class BesselGui(tk.Tk):
    
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title('BesselGUI v0.1')
        self._frame_params = AxiconParamFrame(self)
        self._frame_params.pack(side=tk.LEFT)

        self._frame_slm = tk.Frame(self)
        self._bmp_display = BmpDisplay(self._frame_slm)
        self._bmp_display.pack()
        self._btn_upload = tk.Button(self._frame_slm, text='Upload')
        self._btn_upload.pack()
        self._btn_clear = tk.Button(self._frame_slm, text='Clear')
        self._btn_clear.pack()
        self._frame_slm.pack(side=tk.RIGHT)

        # TODO load from JSON to save state
        self._frame_params.insert_params({
            'slm-dimensions': (1152, 960),
            'period-1': 30,
            'axicon-2-enabled': False,
            'period-2': 32,
            'mask-offset': (0, 0),
            'mask-ellipticity': (0.0, 0.0),
        })
        print(self._frame_params.get_parameters())

        self._bmp_display.set_image(np.ones([512, 512]) * 255)


class AxiconParamFrame(tk.Frame):

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)

        self._dim_x = tk.IntVar(self, value=920)
        self._dim_y = tk.IntVar(self, value=1152)

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

        self._frame_period1 = tk.Frame(self)
        self._label_period1 = tk.Label(self._frame_period1, text='Axicon 1 period')
        self._label_period1.grid(row=0, column=0)
        self._spinbox_period1 = tk.Spinbox(self._frame_period1, relief=tk.FLAT, width=10, from_=1, to_=2048, textvariable=self._period1)
        self._spinbox_period1.grid(row=0, column=1)
        self._frame_period1.grid(row=1, column=0)

        self._period2 = tk.IntVar(self, value=32)

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

        self._frame_offset = tk.Frame(self)
        self._label_offset = tk.Label(self._frame_offset, text='Center offset')
        self._label_offset.grid(row=0, column=0)
        self._spinbox_offset_x = tk.Spinbox(self._frame_offset, relief=tk.FLAT, width=10, from_=0, to_=2048, textvariable=self._offset_x)
        self._spinbox_offset_x.grid(row=0, column=1)
        self._label_offset2 = tk.Label(self._frame_offset, text=', ')
        self._label_offset2.grid(row=0, column=2)
        self._spinbox_offset_y = tk.Spinbox(self._frame_offset, relief=tk.FLAT, width=10, from_=0, to_=2048, textvariable=self._offset_y)
        self._spinbox_offset_y.grid(row=0, column=3)
        self._frame_offset.grid(row=3, column=0)

        self._ellip_x = tk.DoubleVar(self, value=0)
        self._ellip_y = tk.DoubleVar(self, value=0)

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

    def set_image(self, img: np.ndarray):
        self.width = img.shape[0]
        self.height = img.shape[1]
        self.i = tk.PhotoImage(width=self.width,height=self.height)
        img = img.astype(int).flatten()
        rgb_colors = ([img[j], img[j], img[j]] for j in range(0, self.width * self.height))
        pixels=" ".join(("{"+" ".join(('#%02x%02x%02x' %
            tuple(next(rgb_colors)) for i in range(self.width)))+"}" for j in range(self.height)))
        self.i.put(pixels,(0,0,self.width-1,self.height-1))
        c = tk.Canvas(self, width=self.width, height=self.height); c.pack()
        c.create_image(0, 0, image = self.i, anchor=tk.NW)


if __name__ == '__main__':
    root = BesselGui()
    root.mainloop()
