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

from collections import ChainMap, defaultdict
import re
from typing import List, Mapping, Pattern, Tuple

from colcon_sanitizer_reports._sanitizer_section_part_stack_trace import (
    SanitizerSectionPartStackTrace
)


_FIND_RELEVANT_STACK_TRACE_BEGIN_REGEXES_BY_ERROR_NAME: Mapping[str, Tuple[Pattern[str], ...]] = (
    ChainMap({
        # There are two relevant stack traces involved in a "data race" section part. Their headers
        # match the following patterns.
        'data race': (
            re.compile(r'^\s+(Read|Write) of size \d+ at 0x[\da-f]+ .*$'),
            re.compile(r'^\s+Previous (read|write) of size \d+ at 0x[\da-f]+ .*$'),
        ),
        # There is one relevant stack trace in a "detected memory leaks" section part. Its header
        # matches the following pattern.
        'detected memory leaks': (
            re.compile(r'^Direct leak of \d+ byte\(s\) in \d+ object\(s\) allocated from:$'),
        ),
        # There are two relevant stack traces involved in one "lock-order-inversion" error section
        # part. Both of their headers match the same pattern.
        'lock-order-inversion': (
            re.compile(r'^\s+Mutex M\d+ acquired here while holding mutex M\d+ in .*$'),
            re.compile(r'^\s+Mutex M\d+ acquired here while holding mutex M\d+ in .*$'),
        ),
        # Remaining sanitizer errors have the only/most relevant stack trace first in a section
        # part, so we place no restrictions on the pattern of the header. We just find the first
        # stack trace.
    }, defaultdict(lambda: (re.compile(r'^.*$'),)))
)

# Stack trace lines follow a "stack trace begin" line and match the following pattern.
_FIND_STACK_TRACE_LINE_REGEX = re.compile(r'^\s+#\d+\s+.*$')


class SanitizerSectionPart:
    """Parses relevant stack traces from log lines of a single sanitizer section part.

    A sanitizer section part is a group of contiguous lines in a sanitizer section starting with a
    single non-indented line followed by all the indented lines until the next non-indented line.

    Examples from sanitizer output include:
        WARNING: ThreadSanitizer: lock-order-inversion (potential deadlock) (pid=26542)
          Cycle in lock order graph: M28001314164204480 <snip>

          Mutex M3363081369841140 acquired here while holding mutex M2800131416420448 in thread T5:
            <snip relevant stack trace>

          Mutex M2800131416420448 acquired here while holding mutex M3363081369841140 in thread T5:
            <snip relevant stack trace>

          Thread T5 (tid=26553, running) created by main thread at:
            <snip irrelevant stack trace>

        SUMMARY: ThreadSanitizer: lock-order-inversion (potential deadlock) <snip>
    or
        ==5504==ERROR: LeakSanitizer: detected memory leaks

        Direct leak of 1 byte(s) in 1 object(s) allocated from:
            <snip relevant stack trace>

        Indirect leak of 1 byte(s) in 1 object(s) allocated from:
            <snip irrelevant stack trace>

        SUMMARY: AddressSanitizer: 554924 byte(s) leaked in 6385 allocation(s).

    The first example has two section parts. Part one starts with the lock-order-inversion line and
    includes all the indented lines until the summary line. It includes two relevant and one
    irrelevant stack traces to report. Part two is the summary line.

    The second example has four section parts. Part one is just the summary line. Parts two starts
    with the non-indented "Direct leak" line and includes the following stack trace that is relevant
    to report. Part three starts with the non-indented "Indirect leak" line and includes the
    following stack trace that is irrelevant to report. The final part is the summary line.

    See _FIND_RELEVANT_STACK_TRACE_BEGIN_REGEXES_BY_ERROR_NAME for stack trace header search
    patterns that determine which stack traces are relevant. Different error/warning names have
    different relevant stack traces.

    After initialization, SanitizerSectionPart includes the following data member.

    relevant_stack_traces:
        Stack traces from the section part that are relevant for generating the report.
    """

    @property
    def relevant_stack_traces(self) -> Tuple[SanitizerSectionPartStackTrace, ...]:
        """Stack traces from the section part that are relevant for generating the report."""
        return self._relevant_stack_traces

    def __init__(self, *, error_name: str, lines: Tuple[str, ...]) -> None:
        """Gather relevant sanitizer stack traces."""
        relevant_stack_traces: List[SanitizerSectionPartStackTrace] = []
        find_relevant_stack_trace_begin_regexes = (
            _FIND_RELEVANT_STACK_TRACE_BEGIN_REGEXES_BY_ERROR_NAME[error_name]
        )

        # Iterating through lines with an index and slices is easier than with an iterator in this
        # case. The line that triggers the stop condition at the end of the following loop may be
        # the same line that should trigger the start condition at the beginning of the following
        # iteration. With an iterator, it's difficult to evaluate the same line in both places.
        line_i = 0

        # Find all the relevant stack traces from given lines.
        for find_relevant_stack_trace_begin_regex in find_relevant_stack_trace_begin_regexes:

            # Find the line that begins the relevant stack trace.
            for line_i, line in enumerate(lines[line_i:], start=line_i):
                match = find_relevant_stack_trace_begin_regex.match(line)
                if match is not None:
                    break

            # Starting with the next line, gather lines that match the stack trace pattern until one
            # doesn't match.
            relevant_stack_trace_lines: List[str] = []
            for line_i, line in enumerate(lines[line_i + 1:], start=line_i + 1):
                match = _FIND_STACK_TRACE_LINE_REGEX.match(line)
                if match is not None:
                    relevant_stack_trace_lines.append(line)
                else:
                    # Note that if this line happens to be a stack_trace_begin line, we won't miss
                    # it on the next iteration of the outer loop. It will be checked since line_i
                    # will still be the index for this line.
                    break

            # If we gathered any stack trace lines, store the relevant stack trace.
            if relevant_stack_trace_lines:
                relevant_stack_traces.append(
                    SanitizerSectionPartStackTrace(lines=tuple(relevant_stack_trace_lines))
                )

        self._relevant_stack_traces = tuple(relevant_stack_traces)
