import BeamlineStatusLogger.utils as utils
import functools


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
    def __init__(self, key=None):
        self.key = key

    @pass_failures
    def __call__(self, data):
        if self.key:
            img = data.value.pop(self.key)
        else:
            img = data.value

        try:
            p_fit = utils.get_peak_parameters(img)
        except utils.FittingError:
            p_fit = None

        if p_fit:
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
