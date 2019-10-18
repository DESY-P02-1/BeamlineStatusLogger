import BeamlineStatusLogger.utils as utils
import scipy.ndimage as scimg
import pytest
from pytest import approx
from glob import glob
import numpy as np


def eccentricity(sx, sy):
    if sx < sy:
        sx, sy = sy, sx
    return np.sqrt(1 - sy**2/sx**2)


class TestUtils:
    @pytest.mark.parametrize('repeat', range(20))
    def test_get_peak_parameters(self, repeat):
        utils.np.random.seed(1234*repeat)

        # ensure strong enough signal without large eccentricity
        h, a, x0, y0, sx, sy, theta, img_gauss, cutoff, s_noise = [0]*10
        while (cutoff-h) <= 4*s_noise or eccentricity(sx, sy) > 0.95:
            img_gauss, p, cutoff, s_noise = utils.create_test_image()
            h, a, x0, y0, sx, sy, theta = p

        p_fit = utils.get_peak_parameters(img_gauss)
        h_f, a_f, x0_f, y0_f, sx_f, sy_f, theta_f, cutoff_f = p_fit

        rel = max(s_noise/cutoff, 1e-2)

        assert x0_f == approx(x0, rel=1e-3)
        assert y0_f == approx(y0, rel=1e-3)
        assert h_f == approx(h, rel=rel, abs=2*s_noise)  # rather inaccurate
        assert a_f == approx(a, rel=3*a/cutoff*rel,
                             abs=2*s_noise)  # inaccurate if a >> cutoff
        assert sx_f == approx(sx, rel=0.1)
        assert sy_f == approx(sy, rel=0.1)
        if sx == approx(sy, rel=0.05):
            assert theta_f == approx(theta, abs=1)
        elif sx == approx(sy, rel=0.1):
            assert theta_f == approx(theta, abs=0.2)
        else:
            assert theta_f == approx(theta, abs=0.05)
        assert cutoff_f == approx(cutoff, rel=rel,
                                  abs=3*s_noise)   # inaccurate due to filter

    @pytest.mark.parametrize('repeat', range(20))
    def test_get_peak_parameters_no_peak(self, repeat):
        utils.np.random.seed(1234*repeat)

        img, p, cutoff, s_noise = utils.create_test_image(peak=False)

        with pytest.raises(utils.LargeNoiseError):
            utils.get_peak_parameters(img)

    @pytest.mark.parametrize('file, params', [
        ("tests/images/beam/LM10_2018-3-14_21-14-17.png",
            (13.51, 247.12, 314.11, 288.07, 20.66, 22.193, 1.0328, 255)),
        ("tests/images/beam/LM3.png",
            (78.316, 655.73, 130.09, 157.46, 27.939, 19.276, 1.5176, 255)),
        ("tests/images/beam/LM10_2018-6-7_14-26-15.png",
            (14.946, 284.68, 298.22, 198.68, 21.177, 23.381, 0.069193, 255)),
        ("tests/images/beam/LM10-27-Sep-2016_11-00-17.png",
            (45.41, 14181, 180.62, 274.5, 1.3969, 2.1836, 0.05895, 225.93)),
        ("tests/images/beam/LM21-27-Sep-2016_13-50-35.png",
            (75.387, 4.85e6, 219.43, 225.38, 3.0152, 2.0316, 0.02649, 225.93)),
        ("tests/images/beam/LM11_2018-3-14_21-14-52.png",
            (6.1846, 214.61, 301.67, 410.65, 9.5374, 11.89, 0.18241, 255)),
        ("tests/images/beam/LM2.png",
            (1.8008, 340.11, 145.77, 124.16, 39.369, 34.156, 0.17977, 255)),
        ("tests/images/beam/LM10_real.png",
            (25.174, 385.16, 685.95, 501.86, 9.3628, 10.282, 1.313, 255)),
        ("tests/images/beam/LM10_Aarhus.png",
            (14.117, 265.31, 279.44, 184.46, 16.711, 20.66, 0.15514, 255)),
        ("tests/images/beam/LM11_Aarhus.png",
            (12.151, 327.19, 256.49, 218.51, 11.254, 18.302, 0.066, 255)),
        ("tests/images/beam/LM11_real.png",
            (10.625, 446.87, 271.32, 312.47, 4.8546, 8.1719, 0.045686, 255)),
        ("tests/images/beam/LM11-27-Sep-2016_10-54-21.png",
            (81.536, 61850, 184.91, 417.37, 1.3636, 3.6289, 0.0368, 225.93)),
        ("tests/images/beam/LM11_2018-6-7_14-23-57.png",
            (9.8899, 282, 368.15, 198.91, 12.238, 18.76, 0.055975, 255)),
        ("tests/images/beam/LM10-27-Sep-2016_10-49-46.png",
            (44.575, 11164, 185.58, 274.52, 1.4547, 2.2507, 0.032892, 225.93)),
        ("tests/images/beam/LM12_2018-3-14_21-15-24.png",
            (14.006, 385.92, 242.04, 484.14, 12.156, 15.391, 0.09851, 255))
    ])
    def test_get_peak_parameters_images(self, file, params):
        img = scimg.imread(file, flatten=True)

        h, a, x0, y0, sx, sy, theta, cutoff = params

        p_fit = utils.get_peak_parameters(img)
        h_f, a_f, x0_f, y0_f, sx_f, sy_f, theta_f, cutoff_f = p_fit

        s_noise = 1  # representative for the noise of most images
        rel = max(s_noise/cutoff, 1e-2)

        assert x0_f == approx(x0, rel=1e-3)
        assert y0_f == approx(y0, rel=1e-3)
        assert h_f == approx(h, rel=rel, abs=2*s_noise)  # rather inaccurate
        assert a_f == approx(a, rel=3*a/cutoff*rel,
                             abs=2*s_noise)  # inaccurate if a >> cutoff
        assert sx_f == approx(sx, rel=0.1)
        assert sy_f == approx(sy, rel=0.1)
        if sx == approx(sy, rel=0.05):
            assert theta_f == approx(theta, abs=1)
        elif sx == approx(sy, rel=0.1):
            assert theta_f == approx(theta, abs=0.2)
        else:
            assert theta_f == approx(theta, abs=0.05)
        assert cutoff_f == approx(cutoff, rel=rel,
                                  abs=3*s_noise)   # inaccurate due to filter

    @pytest.mark.parametrize('file', [
        "tests/images/no_beam/LM10_no_beam.png",
        "tests/images/no_beam/LM11_no_beam.png",
        "tests/images/no_beam/LM12_no_beam.png"
    ])
    def test_get_peak_parameters_images_no_beam(self, file):
        img = scimg.imread(file, flatten=True)

        with pytest.raises((utils.LargeNoiseError, utils.SmallRegionError)):
            utils.get_peak_parameters(img)

    @pytest.mark.parametrize('file', glob("tests/images/beam/*.npy"))
    def test_get_peak_parameters_images_beam_raw(self, file):
        img = np.load(file)

        p_fit = utils.get_peak_parameters(img)
        assert p_fit

    @pytest.mark.parametrize('file', glob("tests/images/no_beam/*.npy"))
    def test_get_peak_parameters_images_no_beam_raw(self, file):
        img = np.load(file)

        with pytest.raises((utils.LargeNoiseError, utils.SmallRegionError)):
            utils.get_peak_parameters(img)
