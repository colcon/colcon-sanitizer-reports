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

from csv import DictReader
import os
from typing import Dict, Optional

from colcon_sanitizer_reports.sanitizer_log_parser import (
    SanitizerLogParser, SanitizerLogParserOutputPrimaryKey
)
import pytest

# Directory names of resources in test/resources. Directories should include 'input.log' and
# 'expected_output.csv'.
_RESOURCE_NAMES = (
    'data_race_and_lock_order_inversion_interleaved_output',
    'data_race_different_keys',
    'detected_memory_leaks_multiple_subsections_direct_and_indirect_leaks',
    'lock_order_inversion_same_key',
    'no_errors',
    'segv',
)


class SanitizerLogParserFixture:

    def __init__(self, resource_name: str) -> None:
        self.resource_name = resource_name
        self._sanitizer_log_parser: Optional[SanitizerLogParser] = None

    @property
    def resource_path(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'resources', self.resource_name
        )

    @property
    def input_log_path(self) -> str:
        return os.path.join(self.resource_path, 'input.log')

    @property
    def expected_output_csv_path(self) -> str:
        return os.path.join(self.resource_path, 'expected_output.csv')

    @property
    def sanitizer_log_parser(self) -> SanitizerLogParser:
        if self._sanitizer_log_parser is None:
            parser = SanitizerLogParser()
            parser.set_package(self.resource_name)
            with open(self.input_log_path, 'r') as input_log_f_in:
                for line in input_log_f_in.readlines():
                    parser.parse_line(line)

            self._sanitizer_log_parser = parser

        return self._sanitizer_log_parser

    @property
    def report_csv(self) -> DictReader:
        return DictReader(self.sanitizer_log_parser.get_csv().split('\n'))

    @property
    def expected_csv(self) -> DictReader:
        with open(self.expected_output_csv_path, 'r') as expected_output_csv_f_in:
            return DictReader(expected_output_csv_f_in.read().split('\n'))


@pytest.fixture(params=_RESOURCE_NAMES)
def sanitizer_log_parser_fixture(request) -> SanitizerLogParserFixture:
    return SanitizerLogParserFixture(request.param)


def make_output_primary_key(line: Dict[str, str]) -> SanitizerLogParserOutputPrimaryKey:
    return SanitizerLogParserOutputPrimaryKey(**{
        k: v for k, v in line.items()
        if k in SanitizerLogParserOutputPrimaryKey._fields
    })


def test_csv_has_expected_line_count(
        sanitizer_log_parser_fixture: SanitizerLogParserFixture
) -> None:
    assert len(list(sanitizer_log_parser_fixture.report_csv)) == \
        len(list(sanitizer_log_parser_fixture.expected_csv))


@pytest.mark.parametrize('field_name', SanitizerLogParserOutputPrimaryKey._fields)
def test_csv_has_expected_output_primary_key_field(
        sanitizer_log_parser_fixture: SanitizerLogParserFixture, field_name: str
) -> None:
    expected_line_by_key = {
        make_output_primary_key(line): line for line in sanitizer_log_parser_fixture.expected_csv
    }

    for line in sanitizer_log_parser_fixture.report_csv:
        expected_line = expected_line_by_key.pop(make_output_primary_key(line))
        assert line[field_name] == expected_line[field_name]


def test_csv_has_any_sample_stack_trace(
        sanitizer_log_parser_fixture: SanitizerLogParserFixture
) -> None:
    for line in sanitizer_log_parser_fixture.report_csv:
        sample_stack_trace_text = line['sample_stack_trace']
        assert sample_stack_trace_text and not sample_stack_trace_text.isspace()


def test_csv_sample_stack_trace_lines_look_like_stack_trace(
        sanitizer_log_parser_fixture: SanitizerLogParserFixture
) -> None:
    # Check that each line in the sample_stack_trace field looks like a stack trace, eg. starts with
    # a '#' character.
    for line in sanitizer_log_parser_fixture.report_csv:
        for sample_stack_trace_line in line['sample_stack_trace'].split('\n'):
            assert sample_stack_trace_line.lstrip().startswith('#')
