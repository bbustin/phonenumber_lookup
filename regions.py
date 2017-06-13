"""
Maps geographic regions to the ISO 3166-1 alpha-2 codes for each country in the region

If a user-defined mapping file named regions.yaml does not exist, one will be generated
automatically using the following sources:

- United Nations M49 geographic region groupings:  https://unstats.un.org/unsd/methodology/m49/
- ISO 3166-1 alpha-2 codes: https://en.wikipedia.org/wiki/ISO_3166-1

Since the sources are being screen-scraped and can change at any time, it is recommended
that a regions.yaml file be distributed with the source. To generate a new regions.yaml file
rename or delete your existing regions.yaml file

TODO: Add debug logging
"""

import logging
import requests
import yaml
from lxml import etree

logger = logging.getLogger(__name__)

REGIONS_FILE_PATH = "regions.yaml"

class RegionCodes():
    def __init__(self, regions_file_path=REGIONS_FILE_PATH, logger=logger):
        """
        :param regions_file_path: Optional path to regions yaml file. If it does not exist, it will be created.
        :param logger: Optional logger object.
        """
        self.logger = logger
        self.regions_file_path = regions_file_path

    def __getattr__(self, name):
        """
        Provides a way to get attributes that do not yet exist. The first time
        the attribute is retrieved, it will be set on the object. Subsequent
        accesses will not go through this method.

        :param name: attribute to get which does not get exist
        """
        attribute_to_method_mapping = {}
        attribute_to_method_mapping['regions'] = self._get_regions

        if name not in attribute_to_method_mapping:
            raise AttributeError(name)

        result = attribute_to_method_mapping[name]()
        self.__dict__[name] = result

        return result

    def _get_regions(self):
        try:
            result = self._load_regions()
        except Exception as ex:
            self.logger.warn("could not load regions file: {}".format(ex))
            result = self._generate_regions()

        return result

    def _load_regions(self):
        self.logger.debug('loading regions from {}'.format(self.regions_file_path))
        with open(self.regions_file_path, 'r') as regions_file:
            return yaml.safe_load(regions_file)

    def _save_regions(self, regions):
        self.logger.debug('saving regions to {}'.format(self.regions_file_path))
        with open(self.regions_file_path, 'w') as regions_file:
            yaml.safe_dump(regions, regions_file)

    def _generate_regions(self):
        self.logger.info("Generating regions")
        alpha_2_codes = self._scrape_alpha_2_codes()
        result = self._scrape_regions(alpha_2_codes)
        self._save_regions(result)
        return result

    def _scrape_alpha_2_codes(self):
        """
        Scrapes the ISO_3166-1 Alpha-2 codes
        """
        page = requests.get('https://en.wikipedia.org/wiki/ISO_3166-1')
        tree = etree.HTML(page.content)

        table = tree.xpath('//*[@id="Current_codes"]/following::table[1]')[0]

        alpha3_to_alpha2 = {}

        for row in table.iter('tr'):
            cells = []
            for cell in row.iter('td'):
                if cell.text:
                    cells.append(cell.text)
                else:
                    for element in cell.iter('a', 'span'):
                        if element.text:
                            cells.append(element.text)
                            break #sometimes there is more than 1 span. We only want the first
            try:
                alpha3_to_alpha2[cells[2]] = cells[1]
            except IndexError:
                pass

        return alpha3_to_alpha2

    def _scrape_regions(self, alpha_2_codes):
        """
        Scrapes regions as defined by the UN. Adds in the  ISO_3166-1 Alpha-2
        codes for each country so this data can be used by the phonenumbers library.
        """
        def parse_table_to_list():
            page = requests.get('https://unstats.un.org/unsd/methodology/m49/')
            tree = etree.HTML(page.content)

            table = tree.xpath('//*[@id="GeoGroupsENG"]')[0]

            row_iterator = table.iter('tr')

            headers = []
            for header in next(row_iterator).iter('th'):
                headers.append(header.text)

            rows = []

            for row in row_iterator:
                cells = []
                for cell in row.iter('td'):
                    cells.append(cell.text)
                row_dict = dict(zip(headers, cells))
                row_dict['id'] = row.get('data-tt-id')
                row_dict['parent_id'] = row.get('data-tt-parent-id')

                try:
                    row_dict['ISO-alpha2'] = alpha_2_codes[row_dict['ISO-alpha3 code']]
                except KeyError:
                    row_dict['ISO-alpha2'] = None

                rows.append(row_dict)

            return rows

        def list_to_tree(rows):
            out = {
                'root': { 'id': 0, 'parent_id': 0, 'name': "Root node", 'ISO-alpha2': None, 'children': [] }
            }
            for item in rows:
                pid = item['parent_id'] or 'root'
                out.setdefault(pid, { 'children': [] })
                out.setdefault(item['id'], { 'children': [] })
                out[item['id']].update(item)
                out[pid]['children'].append(out[item['id']])
            return out['root']

        def get_all_regions_data(region_list):
            region_data = {}

            for region in region_list:
                if len(region['children']) > 0:
                    region_data.update(get_all_regions_data(region['children']))
                    region_data[region['Country or Area']] = get_country_codes_for(region)

            return region_data

        def get_country_codes_for(data_subtree):
            country_codes = []
            if data_subtree['ISO-alpha2']:
                country_codes.append(data_subtree['ISO-alpha2'])
            if len(data_subtree['children']) > 0:
                for child in data_subtree['children']:
                    country_codes.extend(get_country_codes_for(child)) #extend instead of append so we do not get lists of lists
            return country_codes

        world_tree = list_to_tree(parse_table_to_list())['children'][0]

        return get_all_regions_data(world_tree['children'])