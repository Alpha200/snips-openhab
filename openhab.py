import requests


class Item:
    def __init__(self, name, tags, label, group_names, item_type):
        self.name = name
        self.tags = [tag.lower() for tag in tags]
        self.label = label
        self.group_names = group_names
        self.item_type = item_type
        self.is_location = False
        self.aliases = []

        if self.label is not None:
            self.label = self.label.lower()

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
    def __init__(self, openhab_server_url):
        self.openhab_server_url = openhab_server_url

        self.items = []
        self.locations = {}

        self.load_items()

    def find_location(self, spoken_location):
        return next((location for location in self.locations.values() if spoken_location in location.aliases), None)

    def group_is_location_in_location(self, group, location):
        if group == location.name:
            return True

        if group in self.locations:
            current_location = self.locations[group]

            for parent in current_location.group_names:
                if self.group_is_location_in_location(parent, location):
                    return True

        return False

    def item_is_in_location(self, item, location):
        for group in item.group_names:
            if self.group_is_location_in_location(group, location):
                return True

        return False

    def load_items(self):
        attribute_result = requests.get("{0}/rest/habot/attributes".format(self.openhab_server_url))
        attribute_result.raise_for_status()

        attributes = attribute_result.json()

        params = dict(
            recursive="false",
            fields="name,groupNames,label,tags,type"
        )

        url = "{0}/rest/items".format(self.openhab_server_url)

        result = requests.get(url=url, params=params)
        result.raise_for_status()

        items = result.json()

        for item_result in items:
            item = Item(
                item_result['name'],
                item_result['tags'],
                item_result.get('label', None),
                item_result['groupNames'],
                item_result['type']
            )

            if item.name in attributes:
                item_attributes = attributes[item.name]
                item.aliases = [attribute['value'].lower() for attribute in item_attributes]
                item.is_location = any((item_attribute['type'] == "LOCATION" for item_attribute in item_attributes))

            if item.item_type == "Group" and item.is_location:
                self.locations[item.name] = item

            self.items.append(item)

    def get_relevant_items(self, spoken_item, spoken_room=None, item_type="Switch"):
        if isinstance(spoken_item, list):
            spoken_items = set([item.lower() for item in spoken_item])
            items = [item for item in self.items if spoken_items.issubset(set(item.aliases))]
        else:
            spoken_item = spoken_item.lower()
            items = [item for item in self.items if spoken_item in item.aliases and item.item_type == item_type]

        if spoken_room is not None:
            location = self.find_location(spoken_room.lower())

            if location is None:
                return []

            items = [item for item in items if self.item_is_in_location(item, location)]

        return items

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
