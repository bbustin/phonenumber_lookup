'''
Creates a database of MCC (Mobile Country Codes) and MNC (Mobile Network Codes)
from the "Annex to ITU OB 1111-E" document from the ITU.

Check http://www.itu.int/pub/T-SP-E.212B for the latest version.
'''
import  sys
import csv
from docx.api import Document

if sys.version_info[0] < 3:
    raise Exception("Only works with Python 3")

def parse_document(args):
    document = Document(args.input_file)
    table = document.tables[1]

    with open(args.output_file, 'w') as csvfile:
        writer = csv.writer(csvfile)
        
        for row in table.rows:
            cells = [cell.text for cell in row.cells]
            
            if "" not in cells:
                writer.writerow(cells)

# what to do if called from the CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parses ITU Annex to ITU OB 1111-E  for Geographical Area, MCC, and MNC")
    parser.set_defaults(function=parse_document)
    parser.add_argument("input_file", help=" ITU Annex to ITU OB 1111-E  docx file")
    parser.add_argument("output_file", help="Name of file to write parsed data to")

    args = parser.parse_args()
    args.function(args)
