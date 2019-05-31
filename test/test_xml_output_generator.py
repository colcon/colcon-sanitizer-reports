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

from typing import Dict

from colcon_sanitizer_reports._sanitizer_section_part_stack_trace import (
    SanitizerSectionPartStackTrace
)
from colcon_sanitizer_reports.sanitizer_log_parser import SanitizerLogParserOutputPrimaryKey
from colcon_sanitizer_reports.xml_output_generator import XmlOutputGenerator

_ERROR_MAP = {
    SanitizerLogParserOutputPrimaryKey('package1', 'data-race', 'key1',): 1,
    SanitizerLogParserOutputPrimaryKey('package2', 'lock-order-inversion', 'key2',): 2,
    SanitizerLogParserOutputPrimaryKey('package1', 'data-race', 'key3',): 3,
    SanitizerLogParserOutputPrimaryKey('package3', 'signal-handler-spoils-errno', 'key4',): 4,
}

_STACK_TRACE_MAP = {
    SanitizerLogParserOutputPrimaryKey('package1', 'data-race', 'key1',):
        SanitizerSectionPartStackTrace(('  #1 0x7f in key1 /ros2',)),
    SanitizerLogParserOutputPrimaryKey('package2', 'lock-order-inversion', 'key2',):
        SanitizerSectionPartStackTrace(('  #2 0x7f in key2 /ros2',)),
    SanitizerLogParserOutputPrimaryKey('package1', 'data-race', 'key3',):
        SanitizerSectionPartStackTrace(('  #1 0x7f in key1 /ros2',)),
    SanitizerLogParserOutputPrimaryKey('package3', 'signal-handler-spoils-errno', 'key4',):
        SanitizerSectionPartStackTrace(('  #3 0x7f in key3 /ros2',)),
}

_EMPTY_MAP = {}  # type: Dict


def test_get_unique_packages():
    packages = XmlOutputGenerator(_ERROR_MAP, _STACK_TRACE_MAP).packages
    assert len(packages) == 3
    for key in _ERROR_MAP.keys():
        assert key[0] in packages

    packages = XmlOutputGenerator(_EMPTY_MAP, _STACK_TRACE_MAP).packages
    assert len(packages) == 0


def test_xml_tree_structure():
    tree = XmlOutputGenerator(_ERROR_MAP, _STACK_TRACE_MAP).xml_tree
    testcases = tree.findall('testcase')
    assert len(testcases) == 3
    assert tree.get('tests') == '3'

    for testcase in testcases:
        assert testcase.get('name') in [key[0] for key in _ERROR_MAP.keys()]
        assert len(testcase.findall('error')) > 0
        for error in testcase.findall('error'):
            assert error.get('message') in [key[1] for key in _ERROR_MAP.keys()]
            assert error.get('key') in [key[2] for key in _ERROR_MAP.keys()]
            assert error.get('count') in [str(value) for value in _ERROR_MAP.values()]
            assert error.text in [
                '\n'.join(value.lines) for value in _STACK_TRACE_MAP.values()]

    tree = XmlOutputGenerator(_EMPTY_MAP, _STACK_TRACE_MAP).xml_tree
    testcases = tree.findall('testcase')
    assert len(testcases) == 0
    assert tree.get('tests') == '0'


def test_xml_string_encoding():
    string = XmlOutputGenerator(_ERROR_MAP, _STACK_TRACE_MAP).xml_string
    assert isinstance(string, str)
