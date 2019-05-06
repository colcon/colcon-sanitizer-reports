# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from colcon_core.event.job import JobEnded
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.location import get_log_path
from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import satisfies_version
from colcon_output.event_handler.log import STDOUT_STDERR_LOG_FILENAME
from colcon_sanitizer_reports.sanitizer_log_parser import SanitizerLogParser

logger = colcon_logger.getChild(__name__)


class SanitizerReportEventHandler(EventHandlerExtensionPoint):
    """Generate a report of all Sanitizer ERRORs and WARNINGs."""

    ENABLED_BY_DEFAULT: bool = False

    def __init__(self) -> None:
        """Initialize sanitizer log parser."""
        super().__init__()
        satisfies_version(EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')
        self.enabled: bool = SanitizerReportEventHandler.ENABLED_BY_DEFAULT
        self._log_parser: SanitizerLogParser = SanitizerLogParser()

    def __call__(self, event) -> None:
        """Handle the colcon event appropriately."""
        data = event[0]

        if isinstance(data, JobEnded):
            self._handle(event)

    def _handle(self, event) -> None:
        """Handle JobEnded event and parse the test log file."""
        job: JobEnded = event[1]
        self._log_parser.set_package(job.identifier)

        try:
            log_f = get_log_path() / job.identifier / STDOUT_STDERR_LOG_FILENAME
            with open(log_f, 'r') as in_file:
                for line in in_file:
                    self._log_parser.parse_line(line)
        except IOError:
            logger.info('Could not open stdout_stderr.log file')

        with open('sanitizer_report.csv', 'w') as report_csv_f_out:
            report_csv_f_out.write(self._log_parser.get_csv())

        with open('test_results.xml', 'w') as report_xml_f_out:
            report_xml_f_out.write(self._log_parser.get_xml())
