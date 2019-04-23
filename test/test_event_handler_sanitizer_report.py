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
from colcon_sanitizer_reports.event_handlers.sanitizer_report import SanitizerReportEventHandler
from mock import patch


def test_event_handler_asan_report():
    extension = SanitizerReportEventHandler()
    with patch(
        'colcon_sanitizer_reports.event_handlers.sanitizer_report.'
        'SanitizerReportEventHandler._handle'
    ) as handler:
        event = JobEnded(['test_communication'], 0)
        extension((event, None))
        assert handler.call_count == 1

        handler.reset_mock()
        event = JobEnded(['test_rclcpp'], 0)
        extension((event, None))
        assert handler.call_count == 1

        # Unknown event types will not be handled.
        handler.reset_mock()
        extension(('unknown', None))
        assert handler.call_count == 0
