#!/usr/local/bin/python3

import sys, getopt
import csv
import xml.etree.ElementTree as ET

issues = ['data-races', 'lock-order-inversion', 'heap-use-after-free',
          'signal-unsafe-call-inside-signal', 'signal-handler-spoils-errno']


def load_report(input_xml_file):
    # saving the xml file
    tree = ET.parse(input_xml_file)
    return tree.getroot()


def write_to_csv_file(output_csv_file, root):
    if len(output_csv_file) == 0:
        output_csv_file = 'output_csv.csv'

    with open(output_csv_file,'w') as csv_file:
        headers = ['Issue', 'Package Names', 'Stack Trace',
                      'Bug Count', 'Stack-ranking: frequency?',
                      'Stack-ranking: how hard to fix(1 = easy, 10 = hard)?',
                      'Stack-ranking: how critical is this codepath(1 = not important, 10 = very important)',
                      'Stack-ranking: reproducibility(1 = always happens, 10 = almost never happens)',
                      'Stack-ranking Score', 'GitHub Issue']
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        loc_to_issue = {}
        loc_to_packages = {}
        loc_to_issue_count = {}

        associate_issue_w_location_and_bug_count(root, loc_to_issue,
                                                loc_to_packages, loc_to_issue_count)
        row = []
        for location, issue in loc_to_issue.items():
            row.append(issue)
            row.append(', '.join(loc_to_packages[location]))
            row.append(location)
            row.append(loc_to_issue_count[location])
            writer.writerow(row)
            row = []
    csv_file.close()


def associate_issue_w_location_and_bug_count(root, loc_to_issue, loc_to_packages, loc_to_issue_count):
    for package in root.findall('testsuite'):
        name = package.get('suite-name').strip('"')
        for issue in issues:
            bug_count = int(package.find(issue).get('actual-reported'))

            if bug_count == 0:
                continue

            issue_location = ''

            for line in package.find(issue).iter(clean_issue_name(issue)):
                line_str = str(line.get('location')).strip('"')
                if not line_str == 'None':
                    issue_location += line_str + "\n"
            if not len(issue_location) == 0:
                issue_location = issue_location[:-1]

            if issue_location not in loc_to_issue:
                loc_to_issue[issue_location] = issue
                loc_to_packages[issue_location] = [name]
                loc_to_issue_count[issue_location] = bug_count
                continue

            if name not in loc_to_packages[issue_location]:
                loc_to_packages[issue_location].append(name)


def clean_issue_name(issue):
    if issue == 'data-races':
        return 'data-race'
    return issue


def main(argv):
    input_xml_file = ''
    output_csv_file = ''
    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        print('xml_to_csv_parser.py -i <inputfilename> -o <outputfilename>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('xml_to_csv_parser.py -i <inputfilename> -o <outputfilename>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            input_xml_file = arg
        elif opt in ("-o", "--ofile"):
            output_csv_file = arg

    # load .xml report
    root = load_report(input_xml_file)

    # create new csv file
    write_to_csv_file(output_csv_file, root)

if __name__ == "__main__":
    main(sys.argv[1:])
