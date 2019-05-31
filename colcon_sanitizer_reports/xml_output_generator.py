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
from typing import Dict, Set
import xml.dom.minidom
import xml.etree.cElementTree as eTree


from colcon_sanitizer_reports._sanitizer_section_part_stack_trace import (
    SanitizerSectionPartStackTrace
)
from colcon_sanitizer_reports.sanitizer_log_parser import SanitizerLogParserOutputPrimaryKey


class XmlOutputGenerator:
    """Converts the sanitizer error report into a xUnit compatible xml test report."""

    def __init__(self,
                 error_map: Dict[SanitizerLogParserOutputPrimaryKey, int],
                 stack_trace_map: Dict[SanitizerLogParserOutputPrimaryKey,
                                       SanitizerSectionPartStackTrace]):
        """Convert sanitizer error into xml representation."""
        self._count_by_error = error_map  # type: Dict[SanitizerLogParserOutputPrimaryKey, int]
        self._stack_trace_by_error = stack_trace_map \
            # type: Dict[SanitizerLogParserOutputPrimaryKey, SanitizerSectionPartStackTrace]
        self._packages = self._get_unique_packages()  # type: Set[str]
        testsuite = self._create_error_report(self._create_results_base())  # type: eTree.Element
        self._xml_string = self.encode_and_pretty_print(testsuite)  # type: str

    def _get_unique_packages(self) -> Set[str]:
        return {str(key[0]) for key in self._count_by_error.keys()}

    def _create_results_base(self) -> eTree.Element:
        testsuite = eTree.Element('testsuite', {'tests': str(len(self._packages))})

        # Create elements for each test case (package)
        testcases = {}  # type: Dict[str, eTree.Element]
        for package in self._packages:
            testcases[package] = eTree.SubElement(testsuite, 'testcase', {'name': str(package)})

        return testsuite

    def _create_error_report(self, base_element: eTree.Element) -> eTree.Element:
        error_count_by_package = defaultdict(int)  # type: Dict[str, int]
        testcases = defaultdict()  # type: Dict[str, eTree.Element]
        for case in base_element.findall('testcase'):
            testcases[case.get('name')] = case

        # Gather error details for all packages
        for key, count in self._count_by_error.items():
            error = eTree.SubElement(testcases[key[0]], 'error')
            error.set('message', str(key[1].replace(' ', '-')))
            error.set('key', str(key[2]))
            error.set('count', str(count))
            error.text = '\n'.join(self._stack_trace_by_error[key].lines)
            error_count_by_package[key[0]] += 1

        for package in self._packages:
            testcases[package].set('errors', str(error_count_by_package[package]))

        return base_element

    @staticmethod
    def encode_and_pretty_print(element: eTree.Element) -> str:
        """Return encoded and pretty-printed string representation of xml tree."""
        return xml.dom.minidom.parseString(
            eTree.tostring(element, encoding='UTF-8', method='xml').decode()
        ).toprettyxml()

    @property
    def xml_string(self) -> str:
        """Return string representation."""
        return self._xml_string

    @property
    def packages(self) -> Set[str]:
        """Return packages that are part of the report."""
        return self._packages

    @property
    def xml_tree(self) -> eTree.Element:
        """Return xml representation of the report."""
        return eTree.fromstring(self.xml_string)
