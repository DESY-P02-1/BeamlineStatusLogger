import BeamlineStatusLogger.processors as procs
from BeamlineStatusLogger.processors import PeakFitter
from BeamlineStatusLogger.sources import Data
import BeamlineStatusLogger.utils as utils
import numpy as np
from datetime import datetime
import os
from unittest.mock import Mock
import pytest


class TestPeakFitter:
    def test_peak_fitter_no_beam(self):
        data = Data(datetime(2018, 8, 28), np.random.randn(600, 800),
                    metadata={"id": 1234})
        pf = PeakFitter()
        proc_data = pf(data)
        assert proc_data.timestamp == data.timestamp
        assert proc_data.value["beam_on"] is False
        assert proc_data.metadata["id"] == 1234

    def test_peak_fitter_beam(self, monkeypatch):
        def mockreturn(img):
                return 0, 1, 2, 3, 4, 5, 6, 7
        monkeypatch.setattr(utils, 'get_peak_parameters', mockreturn)

        data = Data(datetime(2018, 8, 28), np.random.randn(600, 800),
                    metadata={"id": 1234})
        pf = PeakFitter()
        proc_data = pf(data)
        assert proc_data.timestamp == data.timestamp
        assert proc_data.value["beam_on"] is True
        assert proc_data.value["mu_x"] == 2
        assert proc_data.value["mu_y"] == 3
        assert proc_data.value["sigma_x"] == 4
        assert proc_data.value["sigma_y"] == 5
        assert proc_data.value["rotation"] == 6
        assert proc_data.value["z_offset"] == 0
        assert proc_data.value["amplitude"] == 1
        assert proc_data.value["cutoff"] == 7
        assert proc_data.metadata["id"] == 1234

    def test_peak_fitter_beam_key(self, monkeypatch):
        def mockreturn(img):
                return 0, 1, 2, 3, 4, 5, 6, 7
        monkeypatch.setattr(utils, 'get_peak_parameters', mockreturn)

        data = Data(datetime(2018, 8, 28),
                    {"frame": np.random.randn(600, 800), "quality": 0},
                    metadata={"id": 1234})
        pf = PeakFitter("frame")
        proc_data = pf(data)
        assert proc_data.timestamp == data.timestamp
        assert proc_data.value["quality"] == 0
        assert proc_data.value["beam_on"] is True
        assert proc_data.value["mu_x"] == 2
        assert proc_data.value["mu_y"] == 3
        assert proc_data.value["sigma_x"] == 4
        assert proc_data.value["sigma_y"] == 5
        assert proc_data.value["rotation"] == 6
        assert proc_data.value["z_offset"] == 0
        assert proc_data.value["amplitude"] == 1
        assert proc_data.value["cutoff"] == 7
        assert proc_data.metadata["id"] == 1234

    def test_peak_fitter_failure(self):
        ex = Exception("An error occured")
        data = Data(datetime(2018, 8, 28), None, failure=ex,
                    metadata={"id": 1234})
        pf = PeakFitter()
        proc_data = pf(data)
        assert proc_data.timestamp == data.timestamp
        assert proc_data.value is None
        assert proc_data.failure is ex
        assert proc_data.metadata["id"] == 1234

    @pytest.mark.parametrize('do_log', [True, False])
    def test_peak_fitter_log(self, monkeypatch, do_log, tmpdir):
        mocksave = Mock()
        mockplot = Mock()
        mocksavefig = Mock()
        monkeypatch.setattr(procs.np, 'save', mocksave)
        monkeypatch.setattr(procs.utils, 'plot_gauss', mockplot)
        monkeypatch.setattr(procs.plt, 'savefig', mocksavefig)

        params = 0, 1, 2, 3, 4, 5, 6, 7

        def mockreturn(img):
                return params
        monkeypatch.setattr(utils, 'get_peak_parameters', mockreturn)

        img1 = np.random.randn(60, 80)
        data1 = Data(datetime(2018, 8, 28),
                     {"frame": img1, "quality": 0},
                     metadata={"id": 1234})

        if do_log:
            pf = PeakFitter("frame", log_dir=str(tmpdir))
        else:
            pf = PeakFitter("frame")

        pf(data1)

        if do_log:
            h, a, x0, y0, sx, sy, theta, cutoff = params
            assert pf.last_h == h
            assert pf.last_a == a
            assert pf.last_x0 == x0
            assert pf.last_y0 == y0
            assert pf.last_sx == sx
            assert pf.last_sy == sy
            assert pf.last_theta == theta
            assert pf.last_cutoff == cutoff

        params = 10, 11, 12, 13, 14, 15, 16, 17
        params2 = params

        img2 = np.random.randn(60, 80)
        time2 = datetime(2018, 8, 29)
        data2 = Data(time2,
                     {"frame": img2, "quality": 0},
                     metadata={"id": 1234})

        pf(data2)

        if do_log:
            h, a, x0, y0, sx, sy, theta, cutoff = params
            assert pf.last_h == h
            assert pf.last_a == a
            assert pf.last_x0 == x0
            assert pf.last_y0 == y0
            assert pf.last_sx == sx
            assert pf.last_sy == sy
            assert pf.last_theta == theta
            assert pf.last_cutoff == cutoff

        params = 10.1, 11.1, 12.1, 13.1, 14.1, 15.1, 16.1, 17.1

        img3 = np.random.randn(60, 80)
        time3 = datetime(2018, 8, 30)
        data3 = Data(time3,
                     {"frame": img3, "quality": 0},
                     metadata={"id": 1234})

        pf(data3)

        if do_log:
            h, a, x0, y0, sx, sy, theta, cutoff = params
            assert pf.last_h == h
            assert pf.last_a == a
            assert pf.last_x0 == x0
            assert pf.last_y0 == y0
            assert pf.last_sx == sx
            assert pf.last_sy == sy
            assert pf.last_theta == theta
            assert pf.last_cutoff == cutoff

            basename = os.path.join(str(tmpdir), "img_"+time2.isoformat())

            assert mocksave.call_count == 1
            assert mockplot.call_count == 2
            assert mocksavefig.call_count == 2

            (fname, array), kwargs = mocksave.call_args
            assert fname == basename
            assert (array == img2).all()
            assert not kwargs

            (array, p_fit), kwargs = mockplot.call_args_list[0]
            assert (array == img2).all()
            assert p_fit == params2
            assert not kwargs

            (array, p_fit), kwargs = mockplot.call_args_list[1]
            assert (array == img2).all()
            assert p_fit == params2
            assert kwargs == {"zoom": True}

            (fname,), kwargs = mocksavefig.call_args_list[0]
            assert fname == basename + ".png"
            assert not kwargs

            (fname,), kwargs = mocksavefig.call_args_list[1]
            assert fname == basename + "_zoomed.png"
            assert not kwargs
        else:
            assert mocksave.call_count == 0
            assert mockplot.call_count == 0
            assert mocksavefig.call_count == 0
