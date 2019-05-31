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
from typing import List, Tuple

from colcon_sanitizer_reports._sanitizer_section_part import SanitizerSectionPart


# Error name for the sanitizer section is in the header line and matches the following pattern.
_FIND_ERROR_NAME_REGEX = re.compile(r'^.*Sanitizer: (?P<error_name>.+?)( \(| 0x[\da-f]+|\s*$)')

# Section parts begin with non-indented lines and match the following pattern.
_FIND_SECTION_PART_BEGIN_REGEX = re.compile(r'^\S.*$')


class SanitizerSection:
    """Parses error name and sub section parts from log lines of a single sanitizer section.

    A sanitizer section includes all the sanitizer output lines including

        1. A single Error/Warning header line
        2. Many log lines, the Contents of the error/warning including stack traces.
        3. A single SUMMARY line

    Examples from sanitizer output include:
        WARNING: ThreadSanitizer: lock-order-inversion (potential deadlock) (pid=26542)
        <snip ThreadSanitizer warning output contents>
        SUMMARY: ThreadSanitizer: lock-order-inversion (potential deadlock)
    or
        ==5054==ERROR: AddressSanitizer: SEGV on unknown address 0x60304d80008f
        <snip AddressSanitizer error output contents>
        SUMMARY: AddressSanitizer: SEGV (/lib/x86_64-linux-gnu/libc.so.6+0x18e5a0)

    SanitizerSection is initialized with a tuple of all lines from a sanitizer output section
    including the header, contents, and summary.

    After initialization, SanitizerSection includes two data members.

    error_name:
        Error name parsed from the header. From the examples above, this would be
        'lock-order-inversion' or 'SEGV on unknown address'.

    parts:
        Sanitizer section parts parsed from lines. See SanitizerSectionPart for definition of a
        sanitizer section part.
    """

    @property
    def error_name(self) -> str:
        """Error name parsed from the header."""
        return self._error_name

    @property
    def parts(self) -> Tuple[SanitizerSectionPart, ...]:
        """Sanitizer section parts parsed from lines."""
        return self._parts

    def __init__(self, *, lines: Tuple[str, ...]) -> None:
        """Construct the sanitizer section."""
        # Section error name comes after 'Sanitizer: ', and before any open paren or hex number.
        match = _FIND_ERROR_NAME_REGEX.match(lines[0])
        assert match is not None, (
            'Could not find error name in section header: {lines[0]}'.format(**locals())
        )
        self._error_name = match.groupdict()['error_name']

        # Divide into parts. Subsections begin with a line that is not indented.
        part_lines = []  # type: List[str]
        sub_sections = []  # type: List[SanitizerSectionPart]
        for line in lines:
            # Check if this the beginning of a new part and we collected lines for a previous part.
            # If so, create the previous part and start collecting for the new part.
            match = _FIND_SECTION_PART_BEGIN_REGEX.match(line)
            if match is not None and part_lines:
                sub_sections.append(
                    SanitizerSectionPart(error_name=self.error_name, lines=tuple(part_lines))
                )
                part_lines = []

            part_lines.append(line)

        if part_lines:
            sub_sections.append(
                SanitizerSectionPart(error_name=self.error_name, lines=tuple(part_lines))
            )

        self._parts = tuple(sub_sections)
