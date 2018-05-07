'''
Looks up a phone number and displays information about it.

author:: Brian Bustin <brian@bustin.us>
author:: Nicole Kenaston Bustin <niki@bustin.us>
'''
import sys
if sys.version_info[0] < 3 and sys.version_info[1] < 3:
    raise Exception("Only works with Python 3.3 and above")

import logging
logger = logging.getLogger(__name__)

import phonenumbers
import multiprocessing
import csv
import yaml
import pprint
from regions import RegionCodes
from phonenumbers import geocoder, carrier

DEFAULT_LANGUAGE = 'en'
LOCALES = [locale  for locale in geocoder.LOCALE_DATA]
REGIONS = {}
FIELDNAMES = ["raw_input", "assumed_local_locale", "E164",  "region", "country", "description", "carrier", "comment"]

def parse_multiple_numbers(phone_numbers, locale, output, language=DEFAULT_LANGUAGE, **kwargs):
    '''
    Parses multiple numbers with multiple possible local locales.
    Parallelized using multiple processes to decreae time.
    '''
    pool_size = multiprocessing.cpu_count() * 2
    pool = multiprocessing.Pool(processes=pool_size)
    args = [(phone_number, locale, language) for phone_number in phone_numbers]
    result = pool.starmap(parse_single_number, args, chunksize=1)
    pool.terminate()

    if output:
        with open(output, 'x') as csvfile:
            csvwriter = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            csvwriter.writeheader()
            for row in result:
                csvwriter.writerow(row)
    
    pprint.pprint(result)
    
    return result

def parse_single_number(phone_number,  locale, language=DEFAULT_LANGUAGE, **kwargs):
    '''
    Parses a single number against multiple possible local locales.
    '''
    results = []

    # number may be internationally formatted, so try to parse first with no locale specified
    try:
        results.append(_parse_single_number_single_locale(phone_number, None))
    except (phonenumbers.NumberParseException, ValueError):
        if locale:
            for current_locale in locale:
                try:
                    results.append(_parse_single_number_single_locale(phone_number, current_locale))
                except (phonenumbers.NumberParseException, ValueError):
                    pass

    if len(results) == 0:
        final_result = {'raw_input': phone_number, 'comment': 'Needs manual review'}
        logger.warn("'{}' does not appear to be a valid number for any of the following: {}".format(phone_number, ", ".join([country for country in locale])))
    elif len(results) > 1:
        final_result = {'raw_input': phone_number, 'comment': 'Needs manual review'}
        logger.warn("'{}' could be a valid number in any of the following: {}".format(phone_number, ", ".join([possible_match['assumed_local_locale'] for possible_match in results])))
    else:
        final_result = results[0]
            
    return final_result

def _parse_single_number_single_locale(phone_number, locale, language=DEFAULT_LANGUAGE):
    '''
    Tries to parse number. 

    Raises:
        NumberParseException if the string is not a potentially viable number
        ValueError if the string was for a potentially viable number that is not valid
    '''
    number = phonenumbers.parse(phone_number, locale)

    if not phonenumbers.is_valid_number(number):
        raise ValueError("not a valid number")

    number_details = {}
    number_details['raw_input'] = phone_number
    number_details['E164'] = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    number_details['assumed_local_locale'] = locale
    number_details['region'] = phonenumbers.region_code_for_number(number)
    number_details['country'] = geocoder.country_name_for_number(number, language)
    number_details['description'] = geocoder.description_for_number(number, language)
    number_details['carrier'] = carrier.safe_display_name(number, language)
    number_details['comment'] = ""

    return number_details

def csv_first_column_iterator(path):
    '''
    Creates an iterator from a CSV file that sequentially returns the values from the first column
    '''
    with open(path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            yield row[0]

# what to do if called from the CLI
if __name__ == "__main__":
    import argparse

    logger.setLevel(logging.DEBUG)
    log_console = logging.StreamHandler()
    log_console.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter('%(levelname)s - %(message)s')
    log_console.setFormatter(log_formatter)
    logger.addHandler(log_console)

    REGIONS = RegionCodes(logger=logger).regions #need to do this down here or will not get logging

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-output")
    group_locale = parent_parser.add_mutually_exclusive_group()
    group_locale.add_argument("-region", 
    choices=[region for region in REGIONS],
    help="Specify a user-defined region from regions.yaml and numbers will be checked against the formatting rules of all countries in the region"
    )
    group_locale.add_argument("-locale", 
        choices=LOCALES,
        action="append",
        help="Locale(s) to treat number as dialed from when certain parts are missing")

    parser = argparse.ArgumentParser(prog="Phone Number Parsing Utility", description="Parses phone numbers to try to determine region, country, carrier, and other geographic information such as city and state")

    subparsers = parser.add_subparsers(title="source", dest='source')
    subparsers.required = True

    subparser_cli = subparsers.add_parser("cli", parents=[parent_parser], help="Input one or more numbers from the command line")
    subparser_cli.set_defaults(function=parse_multiple_numbers)
    subparser_cli.add_argument("phone_numbers", action="append", help="Phone number(s) to look up")

    subparser_csv = subparsers.add_parser("csv", parents=[parent_parser], help="command line")
    subparser_csv.set_defaults(function=parse_multiple_numbers)
    subparser_csv.add_argument("-input",
        dest="phone_numbers",
        type=csv_first_column_iterator, 
        required=True,
        help="CSV file with numbers in the first column")

    args = parser.parse_args()

    # can't seem to do this in arparse using type since type is run prior to validating the input against choices
    if not args.locale and args.region:
        args.locale = REGIONS[args.region]

    if 'function' in args:
        args.function(**vars(args))