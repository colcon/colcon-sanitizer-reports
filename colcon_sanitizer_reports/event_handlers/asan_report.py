# Copyright 2019 Open Source Robotics Foundation
# Licensed under the Apache License, version 2.0

from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.plugin_system import satisfies_version


class ASanReportEventHandler(EventHandlerExtensionPoint):
    """
    Generate a report of all Address Sanitizer output in packages.
    """

    ENABLED_BY_DEFAULT = False

    def __init__(self):
        super().__init__()
        satisfies_version(
            EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def __call__(self, event):
        # TODO
        super().__call__(event)
