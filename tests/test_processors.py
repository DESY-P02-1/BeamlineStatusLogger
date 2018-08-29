from BeamlineStatusLogger.processors import PeakFitter
from BeamlineStatusLogger.sources import Data
import BeamlineStatusLogger.utils as utils
import numpy as np
from datetime import datetime


class TestPeakFitter:
    def test_peak_fitter_no_beam(self):
        data = Data(datetime(2018, 8, 28), np.random.randn(600, 800),
                    metadata={"id": 1234})
        pf = PeakFitter()
        proc_data = pf(data)
        assert proc_data.timestamp == data.timestamp
        assert proc_data.value["beam_on"] is False
        assert proc_data.metadata["id"] == 1234

    def test_get_peak_fitter_beam(self, monkeypatch):
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
