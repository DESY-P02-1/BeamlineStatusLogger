import math
import numpy as np

from scipy.signal import convolve2d
from scipy.optimize import least_squares
import scipy.ndimage as scimg
import skimage.measure as skimsr

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse


# Adapted version inspired by agpy gaussfitter
def gauss2d(x, y, h, a, x0, y0, sx, sy, theta):
    """
        A 2d Gaussian.

        Parameters
        ----------
        x, y : array_like or numbers
            Coordinates
        h : number
            Asymptotic height
        a : number
            Amplitude
        x0, y0 : number
            Mean in each direction
        sx, sy : number
            Standard deviations in each direction
        theta : number
            Rotation angle around the center

        Returns
        -------
        number or ndarray
            The value of the Gaussian at the given coordinates

        Notes
        -----
        The function is defined by

        $$

            f(x, y) = h + a*exp\Biggl(-0.5*
                                  \biggl(
                                    \bigl(\frac{x_0' - x'}{\sigma_x}\bigr)^2 +
                                    \bigl(\frac{y_0' - y'}{\sigma_y}\bigr)^2
                                  \biggr)
                                \Biggr)
        $$
        with

        .. math::

            x_0' =  x_0*\cos(\theta) - y_0*\sin(\theta)\\
            y_0' =  x_0*\sin(\theta) + y_0*\cos(\theta)\\
            x' = x*\cos(\theta) - y*\sin(\theta)\\
            y' =  x*\sin(\theta) + y*\cos(\theta).
    """
    cost = np.cos(theta)
    sint = np.sin(theta)
    rx0 = x0 * cost - y0 * sint
    ry0 = x0 * sint + y0 * cost
    rx = x * cost - y * sint
    ry = x * sint + y * cost
    return h + a * np.exp(-(((rx0 - rx)/sx)**2 + ((ry0 - ry)/sy)**2)/2)


def gauss2d_cut(x, y, h, a, x0, y0, sx, sy, theta, cutoff):
    """
        A 2d Gaussian with a cutoff.

        Parameters
        ----------
        x, y : array_like or numbers
            Coordinates
        h : number
            Asymptotic height
        a : number
            Amplitude
        x0, y0 : number
            Mean in each direction
        sx, sy : number
            Standard deviations in each direction
        theta : number
            Rotation angle around the center
        cutoff : number
            All values larger than this are clipped

        Returns
        -------
        number or ndarray
            The value of the Gaussian at the given coordinates

        See Also
        --------
        gauss2d
    """
    res = gauss2d(x, y, h, a, x0, y0, sx, sy, theta)
    res[res > cutoff] = cutoff
    return res


def estimate_background(img):
    # median should be closer to background than mean
    # more accurate background estimators could be found at
    # https://photutils.readthedocs.io/en/stable/index.html
    return np.median(img)


def estimate_noise(I):
    # from https://stackoverflow.com/a/25436112
    H, W = I.shape

    M = [[1, -2, 1],
         [-2, 4, -2],
         [1, -2, 1]]

    sigma = np.sum(np.sum(np.absolute(convolve2d(I, M))))
    sigma = sigma * math.sqrt(0.5 * math.pi) / (6 * (W-2) * (H-2))

    return sigma


def improve_img(img):
    # filter dead pixels and high frequency noise
    # https://stackoverflow.com/questions/18951500/automatically-remove-hot-dead-pixels-from-an-image-in-python # noqa
    img = scimg.median_filter(img, 2)

    return img


def find_threshold(img, background=0):
    # without bright pixels, max should not be too far from the peak value
    max_val = img.max()

    return background + (max_val - background)/2


class FittingError(Exception):
    """Base class for all fitting exceptions"""
    pass


class LargeNoiseError(FittingError):
    """Indicates that the data is too noisy for a reliable fit"""
    pass


class NoRegionError(FittingError):
    """Indicates that no region of interest could be found"""
    pass


class SmallRegionError(FittingError):
    """Indicates that no region of interest could be found"""
    pass


class LeastSquareError(FittingError):
    """Indicates that the least square fit was not successful"""
    pass


def fitnd(func, y, p0):
    """
        N-dimensional function fitting

        Fit an nd function `func` to the nd array `y`using
        scipy.optimize.least_squares.

        Parameters
        ----------
        func : callable
            The function of n arguments to be fitted to the data.
            It must accept the parameters as one keyword argument
        y : array_like
            The data
        p0 : array_like
            The initial parameters

        Returns
        -------
        out : dict
            Returns the result of scipy.optimize.least_squares
    """
    def cost(p):
        res = np.fromfunction(func, y.shape, p=p) - y
        return np.ravel(res)  # must return vector for least_squares

    return least_squares(cost, p0)


def fit_gauss2d_cut(img, p0, cutoff):
    def f(x, y, p=p0):
        return gauss2d_cut(y, x, *p, cutoff)

    return fitnd(f, img, p0)


def fit_gauss2d_cut_stable(img, h, a, x0, y0, sx, sy, rot, cutoff):
    """
        Fit a 2d Gaussian with cutoff to an image

        This function ensures that the result is unique, i.e., the rotation
        angle θ is always in [0, π/2).

        Parameters
        ----------
        img : array_like
            A 2d image
        h, a, x0, y0, sx, sy, rot : number
            The initial guess for the parameters
        cutoff : number
            The cutoff has to be fixed and is not fitted to the data

        Returns
        -------
        h, a, x0, y0, sx, sy, rot : number
            The fitted parameters

        Raises
        ------
        LeastSquareError
            If the `least_squares` result does not indicate success

        See Also
        --------
        gauss2d_cut
    """
    p0_new = (h, a, x0, y0, sx, sy, rot)
    res = fit_gauss2d_cut(img, p0_new, cutoff)
    if not res.success:
        raise LeastSquareError(res.message)

    h, a, x0, y0, sx, sy, rot = res.x
    sx = abs(sx)
    sy = abs(sy)
    rot = rot % np.pi
    if rot >= np.pi/2:
        rot -= np.pi/2
        sx, sy = sy, sx

    return h, a, x0, y0, sx, sy, rot


def find_roi(img, thresh, min_size=10):
    """
        Find the roi in an image with one or more Gaussian like peaks

        Only considers peaks higher than `thresh` and larger than `min_size`
        pixels. From all remaining peaks the one closest to the center of mass
        is returned.

        Parameters
        ----------
            img : array_like
                A 2d image
            thresh : number
                The threshold
            min_size : number
                Minimum number of pixels above `thresh`

        Returns
        -------
        region : A region object from skimage

        Raises
        ------
        NoRegionError
            If no pixel value is higher than `thresh`

        SmallRegionError
            If no peak has more than `min_size` pixels with values higher than
            `thresh`

        See Also
        --------
        skimage.measure.label
        skimage.measure.regionprops
    """
    img2 = img.copy()

    # if the peak is significantly smaller than max, it will be missed
    img2[img2 <= thresh] = 0
    img2[img2 > thresh] = 1

    # find connected regions with max intensity
    label_img = skimsr.label(img2)
    regions = skimsr.regionprops(label_img)

    if not regions:
        raise NoRegionError("No regions of interest found")

    # skip small regions
    regions = [r for r in regions if r.area > 10]

    if not regions:
        raise SmallRegionError("No sufficiently large regions of interest " +
                               "found")

    # choose region closest to the center of mass
    com = scimg.center_of_mass(img2)
    com = np.asarray(com)

    def dist(r):
        rc = np.asarray(r.centroid)
        return np.linalg.norm(rc - com)

    region = min(regions, key=dist)
    return region


def get_peak_parameters(img):
    """
        Get the parameters of a Gaussian shaped peak close to the image center

        After improving the image quality, the region of interest around a
        central pronounced peak is determined. Within the roi, a 2d rotated,
        cutoff Gaussian is fitted and its parameters returned.

        Parameters
        ----------
        img : array_like
            A 2d image

        Returns
        -------
        h, a, x0, y0, sx, sy, rot, cutoff : number
            The parameters of the fitted Gaussian with cutoff

        Raises
        ------
        A subclass of FittingError that indicates the failure reason

        See Also
        --------
        find_roi
        fit_gauss2d_cut_stable
    """
    # cut the edges because they often contain artefacts
    offset_x, offset_y = 20, 20
    img = img[offset_x:-offset_x, offset_y:-offset_y]

    img = improve_img(img)

    # remove the background
    bg = estimate_background(img)
    img -= bg

    # estimate remaining noise
    s = estimate_noise(img)

    # estimate a threshold
    thresh = find_threshold(img)
    if thresh < 3*s:
        raise LargeNoiseError("Data too noisy for a reliable fit")

    # else find roi
    roi = find_roi(img, thresh)

    # increase bounding box by a factor of 2
    by_min, bx_min, by_max, bx_max = roi.bbox

    bx_width = bx_max - bx_min
    by_width = by_max - by_min

    y0, x0 = roi.centroid

    bx_min_new = int(max(x0-bx_width, 0))
    bx_max_new = int(min(x0+bx_width, img.shape[1] - 1))
    by_min_new = int(max(y0-by_width, 0))
    by_max_new = int(min(y0+by_width, img.shape[0] - 1))

    # only consider the image within the enlarged bbox
    sliced_img = img[by_min_new:by_max_new, bx_min_new:bx_max_new]
    img[by_max_new, bx_max_new]

    cutoff = sliced_img.max()

    w = roi.major_axis_length
    h = roi.minor_axis_length

    p0 = (0, 2*cutoff, bx_width, by_width, w/4, h/4, roi.orientation)

    p_fit = fit_gauss2d_cut_stable(sliced_img, *p0, cutoff)

    h, a, x0, y0, sx, sy, rot = p_fit

    # restore actual parameters
    x0 += bx_min_new + offset_x
    y0 += by_min_new + offset_y
    h += bg
    cutoff += bg

    return h, a, x0, y0, sx, sy, rot, cutoff


def random_gauss_params():
    h = 10*np.random.rand()
    a = h + 100*np.random.rand()
    x0 = 300 + 50*np.random.randn()
    y0 = 300 + 50*np.random.randn()
    sx = 5 + 10*np.random.rand()
    sy = 5 + 10*np.random.rand()
    theta = np.pi/2*np.random.rand()  # restrict to first quadrant
    return h, a, x0, y0, sx, sy, theta


def create_test_image(peak=True):
    h, a, x0, y0, sx, sy, theta = random_gauss_params()

    cutoff = h + 80*np.random.rand()
    shape = (600, 800)
    n_dead = int(100*np.random.rand())
    s_noise = 2*np.random.rand()

    if peak:
        # can't use gauss2d_cut here as noise would be added on top of cutoff
        def g(x, y):
            return gauss2d(y, x, h, a, x0, y0, sx, sy, theta)

        img_gauss = np.fromfunction(g, shape)
    else:
        img_gauss = np.zeros(shape)

    img_gauss += s_noise*np.random.randn(*shape)

    max_val = img_gauss.max()

    # create random dead pixel
    xi_rand = np.random.randint(0, shape[0], n_dead)
    yi_rand = np.random.randint(0, shape[0], n_dead)
    img_gauss[xi_rand, yi_rand] = a*np.random.rand(n_dead)

    # now the cutoff ensures there is no larger value in the image
    img_gauss[img_gauss > cutoff] = cutoff

    cutoff = min(cutoff, max_val)

    return img_gauss, (h, a, x0, y0, sx, sy, theta), cutoff, s_noise


def setup_axes():
    # Set up the axes with gridspec
    fig = plt.figure()
    grid = plt.GridSpec(4, 4, hspace=0.2, wspace=0.2)
    main_ax = fig.add_subplot(grid[:-1, :-1])
    plt.setp(main_ax.get_xticklabels(), visible=False)
    y_slice = fig.add_subplot(grid[:-1, -1], sharey=main_ax)
    x_slice = fig.add_subplot(grid[-1, 0:-1], sharex=main_ax)
    main_ax.xaxis.tick_top()
    y_slice.yaxis.tick_right()
    return fig, main_ax, y_slice, x_slice


def plot_gauss(img, p, axes=None, zoom=False):
    if axes is None:
        f, *axes = setup_axes()
    elif len(axes) == 1:
        a0 = axes[0]
        a1 = None
        a2 = None

    a0, a1, a2 = axes

    h, a, x0, y0, sx, sy, rot, cutoff = p

    fit_img = np.fromfunction(lambda x, y: gauss2d_cut(y, x, *p), img.shape)

    a0.grid()
    a0.imshow(img)

    a0.axvline(x0)
    a0.axhline(y0)

    x1 = x0 + math.cos(rot) * sx
    y1 = y0 - math.sin(rot) * sx
    x2 = x0 - math.sin(rot) * sy
    y2 = y0 - math.cos(rot) * sy

    a0.plot((x0, x1), (y0, y1), '-r', linewidth=2.5)
    a0.plot((x0, x2), (y0, y2), '-r', linewidth=2.5)
    a0.plot(x0, y0, '.g', markersize=15)

    angle = -math.degrees(rot)

    a0.add_patch(Ellipse((x0, y0), width=2*sx, height=2*sy, angle=angle,
                         edgecolor='black',
                         facecolor='none',
                         linewidth=2))

    if a1:
        a1.grid()
        x0_index = np.clip(int(x0), 0, img.shape[1] - 1)
        a1.plot(img[:, x0_index], np.arange(img.shape[0]))
        a1.plot(fit_img[:, x0_index], np.arange(img.shape[0]))

    if a2:
        a2.grid()
        y0_index = np.clip(int(y0), 0, img.shape[0] - 1)
        a2.plot(np.arange(img.shape[1]), img[y0_index, :])
        a2.plot(np.arange(img.shape[1]), fit_img[y0_index, :])

    if zoom:
        width = 8*max(sx, sy)
        height = 6*max(sx, sy)
        a0.set_xlim(x0-width, x0+width)
        a0.set_ylim(y0+height, y0-height)
        a1.set_ylim(y0+height, y0-height)
        a2.set_xlim(x0-width, x0+width)

    return f, (a0, a1, a2)


def plot_roi(img, roi, axes=None):
    # taken from
    # http://scikit-image.org/docs/stable/auto_examples/segmentation/plot_regionprops.html # noqa
    if axes is None:
        f, *axes = setup_axes()
    elif len(axes) == 1:
        a0 = axes[0]
        a1 = None
        a2 = None

    a0, a1, a2 = axes

    a0.grid()
    a0.imshow(img)

    y0, x0 = roi.centroid
    orientation = roi.orientation
    x1 = x0 + math.cos(orientation) * 0.5 * roi.major_axis_length
    y1 = y0 - math.sin(orientation) * 0.5 * roi.major_axis_length
    x2 = x0 - math.sin(orientation) * 0.5 * roi.minor_axis_length
    y2 = y0 - math.cos(orientation) * 0.5 * roi.minor_axis_length

    a0.plot((x0, x1), (y0, y1), '-r', linewidth=2.5)
    a0.plot((x0, x2), (y0, y2), '-r', linewidth=2.5)
    a0.plot(x0, y0, '.g', markersize=15)

    minr, minc, maxr, maxc = roi.bbox
    bx = (minc, maxc, maxc, minc, minc)
    by = (minr, minr, maxr, maxr, minr)
    a0.plot(bx, by, '-b', linewidth=2.5)

    w = roi.major_axis_length
    h = roi.minor_axis_length
    angle = -math.degrees(roi.orientation)

    a0.add_patch(Ellipse((x0, y0), width=w, height=h, angle=angle,
                         edgecolor='black',
                         facecolor='none',
                         linewidth=2))

    if a1:
        a1.grid()
        a1.plot(img[:, int(x0)], np.arange(img.shape[0]))
        a1.axhline(minr)
        a1.axhline(maxr)

    if a2:
        a2.grid()
        a2.plot(np.arange(img.shape[1]), img[int(y0), :])
        a2.axvline(minc)
        a2.axvline(maxc)
