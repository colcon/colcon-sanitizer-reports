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

from collections import defaultdict
import csv
from io import StringIO
import re
from typing import Dict, List, NamedTuple, Pattern

from colcon_sanitizer_reports._sanitizer_section import SanitizerSection
from colcon_sanitizer_reports._sanitizer_section_part_stack_trace import (
    SanitizerSectionPartStackTrace
)

# The start line of a section can be found with the following regex. Additionally, any prefix that
# is prepended by the logging system can be extracted and be used to lstrip following section lines.
_FIND_SECTION_START_LINE_REGEX = \
    re.compile(r'^(?P<prefix>.*?)(==\d+==|)(WARNING|ERROR):.*Sanitizer:.*$')

# The end line of a section can be found with the following regex. Additionally, any prefix that is
# prepended by the logging system can be extracted and be used to match the common prefix of the
# section to which the end line belongs.
_FIND_SECTION_END_LINE_REGEX = re.compile(r'^(?P<prefix>.*)(SUMMARY: .*Sanitizer: .*)$')


class SanitizerLogParserOutputPrimaryKey(NamedTuple):
    """SanitizerLogParser report output is keyed on these fields.

    This is the primary key of the report. Each unique combination of these fields is reported on
    its own line and no two output lines will have a duplicate combination of these fields.

    After initialization, SanitizerLogParserOutputPrimaryKey includes the following data members.

    package:
        Name of the ros2 package where the error occurred.

    error_name:
        Name of the sanitizer error (such as "data race", "lock-order-inversion", etc). See
        SanitizerSection for more details.

    stack_trace_key:
        The key of a significant stack trace. Note that a single sanitizer error/warning section may
        have multiple significant stack traces, resulting in multiple keys and thus, multiple
        SanitizerLogParserOutputPrimaryKeys. See SanitizerSectionPart and
        SanitizerSectionPartStackTrace for more details.
    """

    package: str
    error_name: str
    stack_trace_key: str


class SanitizerLogParser:
    """Parses sanitizer error and warning sections from a log and generates a summary report.

    The parser works with the output of "colcon test" and reports information about all sanitizer
    (eg. AddressSanitizer or ThreadSanitizer) error and warning output. Every sanitizer error and
    warning occurs during tests for some ros2 package, has a specific error name, and has one or
    more significant stack traces that are helpful for determining the root cause of the error or
    warning.

    Lines from "colcon test" output should be added to the parser one at a time with the
    parse_line() method. When finished, the report can be access from the csv property.

    CSV output columns are "package,error_name,stack_trace_key,count". Package, error_name, and
    stack_trace_key columns make up the primary key for CSV output. See
    SanitizerLogParserOutputPrimaryKey for more details about the primary key.

    CSV output additional columns include:

    count:
        The count of times the fields from the primary key occur while parsing the log.

    sample_stack_trace:
        The full output of one of the stack traces that matched the primary key.
    """

    def __init__(self) -> None:
        """Initialize sanitizer report sections."""
        # Holds count of errors seen for each output key.
        self._count_by_output_primary_key: Dict[SanitizerLogParserOutputPrimaryKey, int] = (
            defaultdict(int)
        )

        self._sample_stack_trace_by_output_primary_key: (
            Dict[SanitizerLogParserOutputPrimaryKey, SanitizerSectionPartStackTrace]
        ) = {}

        # Current package output that is being parsed.
        self._package: str = ''

        # We keep lines for partially-gathered sanitizer sections here. Incoming lines that match
        # one of the find_line_regexes is appended to the associated list of lines.
        self._lines_by_find_line_regex: Dict[Pattern, List[str]] = {}

    def get_csv(self) -> str:
        """Return a csv representation of reported error/warnings."""
        csv_f_out = StringIO()
        writer = csv.writer(csv_f_out)
        writer.writerow([
            *SanitizerLogParserOutputPrimaryKey._fields, 'count', 'sample_stack_trace'
        ])
        for output_primary_key, count in self._count_by_output_primary_key.items():
            sample_stack_trace = self._sample_stack_trace_by_output_primary_key[output_primary_key]
            writer.writerow([*output_primary_key, count, '\n'.join(sample_stack_trace.lines)])

        return csv_f_out.getvalue()

    def set_package(self, package: str) -> None:
        """Set the package name to which each sanitizer error/warning belongs."""
        self._package = package

    def parse_line(self, line: str) -> None:
        """Parse colcon test log file line by line and generate report of errors/warnings."""
        line = line.rstrip()

        # If we have a sanitizer section starting line, start gathering lines for it.
        match = _FIND_SECTION_START_LINE_REGEX.match(line)
        if match is not None:
            # Future lines for this new sanitizer section are sometimes interleaved with unrelated
            # log lines due to multi-threaded logging. The log lines we care about will have the
            # same prefix, so they will match the following pattern with the prefix included.
            prefix = match.groupdict()['prefix']
            find_line_regex = re.compile(r'^{prefix}(?P<line>.*)$'.format(prefix=re.escape(prefix)))
            self._lines_by_find_line_regex[find_line_regex] = []

        # If this line belongs to one of the sections we're currently building, append it to lines
        # for that section.
        for find_line_regex, lines in self._lines_by_find_line_regex.items():
            match = find_line_regex.match(line)
            if match is not None:
                lines.append(match.groupdict()['line'])

                # If this is the last line of a section, create the section and stop gathering lines
                # for it.
                match = _FIND_SECTION_END_LINE_REGEX.match(line)
                if match is not None:
                    section = SanitizerSection(lines=tuple(lines))
                    for part in section.parts:
                        for relevant_stack_trace in part.relevant_stack_traces:
                            output_primary_key = SanitizerLogParserOutputPrimaryKey(
                                package=self._package,
                                error_name=section.error_name,
                                stack_trace_key=relevant_stack_trace.key,
                            )
                            self._count_by_output_primary_key[output_primary_key] += 1
                            self._sample_stack_trace_by_output_primary_key[output_primary_key] = (
                                relevant_stack_trace
                            )
                    del self._lines_by_find_line_regex[find_line_regex]

                break
