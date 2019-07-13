from itertools import chain

import requests


def load_properties(filepath, sep='=', comment_char='#'):
    """
    Read the file passed as parameter as a properties file.
    """
    props = {}
    with open(filepath, "rt") as f:
        for line in f:
            l = line.strip()
            if l and not l.startswith(comment_char):
                key_value = l.split(sep)
                key = key_value[0].strip()
                value = sep.join(key_value[1:]).strip().strip('"')
                props[key] = value
    return props


class Item:
    def __init__(self, name, label, item_type):
        self.name = name
        self.label = label
        self.item_type = item_type
        self.semantics = None
        self.has_location = None
        self.has_points = []
        self.is_point_of = None
        self.is_part_of = None
        self.relates_to = None
        self.synonyms = []

        if self.label is not None:
            self.label = self.label.lower()

    def is_point(self):
        return self.semantics.startswith("Point")

    def is_location(self):
        return self.semantics.startswith("Location")

    def is_equipment(self):
        return self.semantics.startswith("Equipment")

    def __str__(self):
        return self.name

    def __repr__(self):
        return '{{ Item {} }}'.format(self.__str__())

    def description(self):
        if self.label is not None:
            return self.label
        else:
            return self.name


class OpenHAB:
    def __init__(self, openhab_server_url, lang="de"):
        self.openhab_server_url = openhab_server_url
        self.lang = lang
        self.items = {}
        self.additional_synonyms = None
        self.reversed_additional_synonyms = {}

        self.load_items()
        self.load_synonyms()
        self.fix_inverse_relations()

    def load_synonyms(self):
        self.additional_synonyms = {
            k: [synonym.lower() for synonym in v.split(',')] for k, v in
            load_properties("tags/tags_{language}.properties".format(language=self.lang)).items()
        }

        for tag, synonyms in self.additional_synonyms.items():
            for synonym in synonyms:
                self.reversed_additional_synonyms.setdefault(synonym, []).append(tag)

    def get_location(self, spoken_location):
        location = None

        if spoken_location in self.reversed_additional_synonyms:
            tags = self.reversed_additional_synonyms[spoken_location]
            location = next((
                location for location in self.items.values() if
                location.is_location() and location.semantics in tags
            ), None)

        if location is None:
            location = next((
                location for location in self.items.values() if
                location.is_location() and (spoken_location.lower() in location.synonyms or
                                            spoken_location.lower() == location.label)
            ), None)

        return location

    def item_is_part_of_location(self, item, location):
        if item.has_location is not None:
            if location.name == item.has_location or self.item_is_part_of_location(
                    self.items[item.has_location],
                    location
            ):
                return True
        elif item.is_point_of is not None and self.item_is_part_of_location(self.items[item.is_point_of], location):
            return True
        elif item.is_part_of is not None:
            if item.is_part_of == location.name or self.item_is_part_of_location(self.items[item.is_part_of], location):
                return True

        return False

    def fix_inverse_relations(self):
        for item in self.items.values():
            if item.is_point_of is not None and item.name not in self.items[item.is_point_of].has_points:
                self.items[item.is_point_of].has_points.append(item.name)

    def load_items(self):
        params = dict(
            recursive="false",
            fields="name,label,type,editable,metadata",
            metadata="semantics,synonyms"
        )

        url = "{0}/rest/items".format(self.openhab_server_url)

        result = requests.get(url=url, params=params)
        result.raise_for_status()

        items = result.json()
        items_with_semantics = [item for item in items if "metadata" in item and "semantics" in item["metadata"]]

        for item_result in items_with_semantics:
            item = Item(
                item_result['name'],
                item_result.get('label', None),
                item_result['type']
            )

            semantics = item_result["metadata"]["semantics"]
            item.semantics = semantics["value"]

            if "config" in semantics:
                semantic_config = semantics["config"]

                if "hasLocation" in semantic_config:
                    item.has_location = semantic_config["hasLocation"]

                if "relatesTo" in semantic_config:
                    item.relates_to = semantic_config["relatesTo"]

                if "isPartOf" in semantic_config:
                    item.is_part_of = semantic_config["isPartOf"]

                if "isPointOf" in semantic_config:
                    item.is_point_of = semantic_config["isPointOf"]

                if "hasPoint" in semantic_config:
                    item.has_points = semantic_config["hasPoint"].split(',')

            if "synonyms" in item_result["metadata"]:
                item.synonyms = [synonym.strip() for synonym in item_result["metadata"]["synonyms"]["value"].split(",")]

            self.items[item.name] = item

    def get_injections(self):
        item_names = set(chain.from_iterable(
            (item.synonyms for item in self.items.values() if not item.is_location())
        )).union(
            (item.label for item in self.items.values() if not item.is_location() and item.label is not None)
        ).union(
            chain.from_iterable((v for k, v in self.additional_synonyms.items()
                                 if k.startswith("Property") or k.startswith("Equipment")
                                 ))
        )

        location_names = set(
            chain.from_iterable((item.synonyms for item in self.items.values() if item.is_location()))
        ).union(
            (item.label for item in self.items.values() if item.is_location() and item.label is not None)
        ).union(set(
            chain.from_iterable((v for k, v in self.additional_synonyms.items() if k.startswith("Location"))))
        )

        return list(item_names), list(location_names)

    def filter_by_location(self, items, location):
        return set((item for item in items if self.item_is_part_of_location(item, location)))

    def get_items_with_attributes(self, point_type, esm_property=None, is_part_of_equipment=None, location=None,
                                  item_type=None):
        items_found = [item for item in self.items.values() if
                       item.semantics == point_type and
                       (esm_property is None or esm_property == item.relates_to) and
                       (is_part_of_equipment is None or is_part_of_equipment == item.is_point_of) and
                       (item_type is None or item.item_type == item_type)
                       ]

        if location is not None:
            return [item for item in items_found if self.item_is_part_of_location(item, location)]
        else:
            return items_found

    def get_relevant_items(self, spoken_items, location=None, item_type=None):
        items_found = set()

        if isinstance(spoken_items, list):
            for spoken_item in spoken_items:
                items_found = items_found.union(self.get_relevant_items(spoken_item, location))

            return items_found
        else:
            spoken_item = spoken_items.lower()

            if spoken_item in self.reversed_additional_synonyms:
                tags_to_search_for = self.reversed_additional_synonyms[spoken_item]

                for tag in tags_to_search_for:
                    if tag.startswith("Property"):
                        items_found = items_found.union(set((
                            item for item in self.items.values() if
                            tag == item.relates_to and (item_type is None or item.item_type == item_type)
                        )))
                    elif tag.startswith("Equipment"):
                        items_found = items_found.union(set((
                            item for item in self.items.values() if
                            item.semantics == tag and (item_type is None or item.item_type == item_type)
                        )))

                if location is not None:
                    items_found = self.filter_by_location(items_found, location)

            if len(items_found) > 0:
                return items_found
            else:
                return items_found.union(set((
                    item for item in self.items.values() if
                    item.label == (spoken_item or spoken_item in item.synonyms) and
                    (item_type is None or item.item_type == item_type))
                ))

    def send_command_to_devices(self, devices, command):
        for device in devices:
            url = "{0}/rest/items/{1}".format(self.openhab_server_url, device.name)
            requests.post(url, command)

    def get_state(self, item):
        url = "{0}/rest/items/{1}".format(self.openhab_server_url, item.name)
        result = requests.get(url)

        if result.status_code != 200:
            return None

        data = result.json()
        state = data['state']

        if state == "NULL":
            state = None

        return state
