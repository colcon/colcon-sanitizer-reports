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

import re
from typing import Tuple


# Key comes from a line of ros2 code and matches the following pattern.
_FIND_KEY_REGEX = re.compile(r'^\s+#\d+ (0x[\da-f]+ in|)\s*(?P<key>.*/ros2.*)\s*$')

# Parts of a key that are changeable between otherwise identical stack trace can be found and masked
# with the following pattern.
_FIND_KEY_SUB_REGEX = re.compile(r'0x[\da-f]+')


class SanitizerSectionPartStackTrace:
    """Parses key from a single sanitizer section part stack trace and stores stack trace lines.

    A sanitizer section part stack trace is a group of contiguous lines in a sanitizer section part
    that make a typical stack trace.

    Examples from sanitizer output include:
        ==5584==ERROR: LeakSanitizer: detected memory leaks

        Direct leak of 64 byte(s) in 1 object(s) allocated from:
            #0 in operator new(unsigned long) (/usr/lib/x86_64-linux-gnu/libasan.so)
            #1 in rclcpp::NodeOptions::get_rcl_node_options() const (/ros2/rclcpp/lib/librclcpp.so)
            <snip stack trace lines 2-13>
            #14 in main (/ros2/test_communication/test_publisher_subscriber_cpp)
            #15 in __libc_start_main (/lib/x86_64-linux-gnu/libc.so)

        SUMMARY: AddressSanitizer: 64 byte(s) leaked in 1 allocation(s).

    This examples shows a stack trace with fifteen lines.

    After initialization, SanitizerSectionPartStackTrace includes the following data members.

    key:
        Key parsed from the first line in the stack trace that comes from ros2 code (#1 in the
        example above). Some information is masked or omitted in the key so that keys of multiple
        stack traces that are reproductions of each other are guaranteed to match.

    lines:
        The lines that make up the stack trace.
    """

    @property
    def key(self) -> str:
        """Key parsed from first line in the stack trace that comes from ros2 code."""
        return self._key

    @property
    def lines(self) -> Tuple[str, ...]:
        """Lines that make up the stack trace."""
        return self._lines

    def __init__(self, lines: Tuple[str, ...]) -> None:
        """Find and assign stack trace key."""
        key = None
        for line in lines:
            match = _FIND_KEY_REGEX.match(line)
            if match is not None:
                key = _FIND_KEY_SUB_REGEX.sub('0xX', match.groupdict()['key'])
                break

        assert key is not None, 'Could not find key in given stack trace lines.'

        self._key = key
        self._lines = lines
