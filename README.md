#ASan/TSan Tools

This repository contains tools that help us analyze ASan/TSan result better.

To test parsing a `.xml` report into a .csv file, run the following command
```
sudo chmod +x ./utilies/xml_to_csv_parser.py
./utilities/xml_to_csv_parser.py -i ./examples/test_tsan_xml_report.xml
```

When you are ready, run the following command to generate a `.csv` report and export it into a equip document
```
./utilities/xml_to_csv_parser.py -i <name-of-xml-result->.xml -o <name-of-output-csv>.csv
```
