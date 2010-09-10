"""
Module with the DashboardBundle model.
"""

from launch_control.models.test_run import TestRun
from launch_control.utils.json import PlainOldData


class DashboardBundle(PlainOldData):
    """
    Model representing the stand-alone document that can store arbitrary
    test runs.

    For useful methods related to the bundle see api module
    """
    # Default format name. If you are working on a fork/branch that is
    # producing incompatible documents you _must_ change the format
    # string. Dashboard Server will be backwards-compatible with all
    # past formats. This format is the _default_ format for new
    # documents.
    # Note: Current format was selected during Linaro 10.11 Cycle.
    FORMAT = "Dashboard Bundle Format 1.0"

    __slots__ = ('format', 'test_runs')

    def __init__(self, format=None, test_runs=None):
        if format is None:
            format = self.FORMAT
        if test_runs is None:
            test_runs = []
        self.format = format
        self.test_runs = test_runs

    @classmethod
    def get_json_attr_types(cls):
        return {'test_runs': [TestRun]}