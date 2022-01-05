import BeamlineStatusLogger.utils as utils
from collections.abc import Mapping
import functools
import os
import numpy as np
# Work around GTK backend issue with pandas, see
# https://github.com/pandas-dev/pandas/issues/23040
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt  # noqa


def pass_failures(func):
    @functools.wraps(func)
    def wrapper(*args):
        if len(args) == 2:
            # wraps class method
            self, data = args
        elif len(args) == 1:
            # wraps function
            data, = args
        else:
            raise ValueError("Wrong number of argumuments, got " + str(args))

        if data.failure:
            # just pass the data object
            return data
        else:
            # call the processor function
            return func(*args)

    return wrapper


def ToString():
    """
        A processor that converts all values to strings
    """
    @pass_failures
    def to_string(data):
        value = data.value
        if isinstance(value, Mapping):
            value = {k: str(v) for k, v in value.items()}
        else:
            value = str(value)
        data.value = value
        return data
    return to_string


class PeakFitter:
    """
        A processor that expects an image and returns the parameters of a
        Gausian fit

        The instance must be called with a `data` object which `value` field
        contains a 2d array. The call returns a `data` object which `value`
        field contains a dict with the following keys:

        beam_on : Boolean
            Indicates the success of the fitting procedure
        mu_x, mu_y : float
            The xy coordinates of the peak maximum
        sigma_x, sigma_y : float
            The standard deviation in x and y direction
        rotation : float
            The rotation angle (counter-clockwise)
        z_offset : float
            An estimate for the background value
        amplitude : float
            An estimate for the amplitude of the peak
        cutoff : float
            The maximum value of the peak
    """
    def __init__(self, key=None, log_dir=None, log_thresh=1):
        """
            Construct a PeakFitter processor instance

            Parameters
            ----------
            key : str
                The key to extract the image from the data.value dict
            log_dir : str, optional
                If given, images will be saved to this directory whenever the
                position or width of the peak changes by more than `log_thresh`
                pixels. The directory must exist
            log_thresh : number, optional
                Threshold for logging peak movements. Only has an effect if
                `log_dir` is given.
        """
        self.key = key
        self.log_dir = log_dir
        self.log_thresh = log_thresh
        self.last_h = None
        self.last_a = None
        self.last_x0 = None
        self.last_y0 = None
        self.last_sx = None
        self.last_sy = None
        self.last_theta = None
        self.last_cutoff = None

        if self.log_dir:
            if not os.path.isdir(self.log_dir):
                raise ValueError(self.log_dir + " is not a directory")

    @pass_failures
    def __call__(self, data):
        if self.key:
            img = data.value.pop(self.key)
        else:
            img = data.value

        if img is None:
            return data

        img = img.astype(np.float64)

        try:
            p_fit = utils.get_peak_parameters(img)
        except utils.FittingError:
            p_fit = None

        if p_fit:
            self.log_frames(data.timestamp, img, p_fit)
            h, a, x0, y0, sx, sy, theta, cutoff = p_fit
            d = {"beam_on": True,
                 "mu_x": x0,
                 "mu_y": y0,
                 "sigma_x": sx,
                 "sigma_y": sy,
                 "rotation": theta,
                 "z_offset": h,
                 "amplitude": a,
                 "cutoff": cutoff
                 }
        else:
            d = {"beam_on": False}

        if self.key:
            data.value.update(d)
        else:
            data.value = d

        return data

    def log_frames(self, time, img, p):
        if self.log_dir:
            h, a, x0, y0, sx, sy, theta, cutoff = p
            if ((self.last_x0 and abs(x0 - self.last_x0) > self.log_thresh) or
               (self.last_y0 and abs(y0 - self.last_y0) > self.log_thresh) or
               (self.last_sx and abs(sx - self.last_sx) > self.log_thresh) or
               (self.last_sy and abs(sy - self.last_sy) > self.log_thresh)):
                filename = os.path.join(self.log_dir,
                                        "img_" + time.isoformat())
                np.save(filename, img)
                utils.plot_gauss(img, p)
                plt.savefig(filename + ".png")
                utils.plot_gauss(img, p, zoom=True)
                plt.savefig(filename + "_zoomed.png")

            self.last_h = h
            self.last_a = a
            self.last_x0 = x0
            self.last_y0 = y0
            self.last_sx = sx
            self.last_sy = sy
            self.last_theta = theta
            self.last_cutoff = cutoff
