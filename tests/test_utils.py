import BeamlineStatusLogger.utils as utils
import scipy.ndimage as scimg
import pytest
from pytest import approx


class TestUtils:
    @pytest.mark.parametrize('repeat', range(20))
    def test_get_peak_parameters(self, repeat):
        utils.np.random.seed(1234*repeat)

        # ensure strong enough signal
        h, a, x0, y0, sx, sy, theta, img_gauss, cutoff, s_noise = [0]*10
        while (cutoff-h) <= 4*s_noise:
            img_gauss, p, cutoff, s_noise = utils.create_test_image()
            h, a, x0, y0, sx, sy, theta = p

        p_fit = utils.get_peak_parameters(img_gauss)
        h_f, a_f, x0_f, y0_f, sx_f, sy_f, theta_f, cutoff_f = p_fit

        rel = max(s_noise/cutoff, 1e-2)

        assert x0_f == approx(x0 + 0.5, rel=1e-3)
        assert y0_f == approx(y0 + 0.5, rel=1e-3)
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

        with pytest.raises(utils.FittingError,
                           match=r".*(possible|large) regions of interest.*"):
            utils.get_peak_parameters(img)

    @pytest.mark.parametrize('file, params', [
        ("tests/images/beam/LM10_2018-3-14_21-14-17.png",
            (14.391, 264.54, 314.61, 288.65, 20.492, 21.992, 1.0708, 255)),
        ("tests/images/beam/LM3.png",  # the worst fit
            (87.305, 597.98, 130.62, 158.29, 27.711, 19.438, 1.5126, 255)),
        ("tests/images/beam/LM10_2018-6-7_14-26-15.png",
            (16.335, 318.14, 298.93, 199.17, 20.695, 22.668, 0.050264, 255)),
        ("tests/images/beam/LM10-27-Sep-2016_11-00-17.png",
            (55.316, 33410, 181.19, 275.08, 1.3659, 2.0673, 0.064445, 225.93)),
        ("tests/images/beam/LM21-27-Sep-2016_13-50-35.png",
            (84.384, 2.93e6, 219.89, 225.95, 3.1145, 2.125, 0.025263, 225.93)),
        ("tests/images/beam/LM11_2018-3-14_21-14-52.png",
            (7.7045, 232.83, 302.02, 411.01, 9.511, 11.658, 0.19587, 255)),
        ("tests/images/beam/LM2.png",
            (1.7244, 341.59, 146.13, 124.31, 39.691, 34.692, 0.17227, 255)),
        ("tests/images/beam/LM10_real.png",
            (25.547, 389.29, 686.49, 502.36, 9.4633, 10.421, 1.329, 255)),
        ("tests/images/beam/LM10_Aarhus.png",
            (15.369, 283.51, 279.94, 184.99, 16.747, 20.582, 0.14672, 255)),
        ("tests/images/beam/LM11_Aarhus.png",
            (14.841, 423.07, 257.61, 218.9, 10.782, 16.995, 0.067044, 255)),
        ("tests/images/beam/LM11_real.png",
            (12.11, 483.64, 271.81, 312.95, 4.8759, 8.04, 0.047544, 255)),
        ("tests/images/beam/LM11-27-Sep-2016_10-54-21.png",
            (100.02, 1.89e6, 185.4, 417.85, 1.1811, 2.9826, 0.038967, 225.93)),
        ("tests/images/beam/LM11_2018-6-7_14-23-57.png",
            (11.336, 314.08, 368.74, 199.36, 12.096, 18.429, 0.052396, 255)),
        ("tests/images/beam/LM10-27-Sep-2016_10-49-46.png",
            (55.334, 28815, 186.21, 275.1, 1.3867, 2.1127, 0.055045, 225.93)),
        ("tests/images/beam/LM12_2018-3-14_21-15-24.png",
            (15.185, 454.44, 242.93, 484.95, 11.775, 14.82, 0.1503, 255))
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
            img = scimg.imread(file)

            with pytest.raises(utils.SmallRegionError):
                utils.get_peak_parameters(img)
