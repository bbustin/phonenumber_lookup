'''
Looks up a phone number and displays information about it.

Must have the phonenumbers library installed (pip install phonenumbers)
'''
import phonenumbers
from phonenumbers import geocoder, carrier

locale = "en"

def parse_number(args):
	number = phonenumbers.parse(args.phone_number, args.locale)
	print("E164: {}, Country: {}, City: {}, Carrier: {}".format(
		phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164),
		geocoder.country_name_for_number(number, locale), 
		geocoder.description_for_number(number, locale), 
		carrier.name_for_number(number, locale)))
	print()

# what to do if called from the CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parses phone numbers to try to determine Countey, City, and Carrier")
    parser.set_defaults(function=parse_number)
    parser.add_argument("phone_number", help="Phone number to look up")
    parser.add_argument("locale", 
    	choices=[locale  for locale in geocoder.LOCALE_DATA],
    	help="Locale to treat number as dialed from when certain parts are missing")

    args = parser.parse_args()
    args.function(args)