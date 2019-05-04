import requests


class Item:
    def __init__(self, name, tags, label, group_names):
        self.name = name
        self.tags = [tag.lower() for tag in tags]
        self.label = label
        self.group_names = [group_name.lower() for group_name in group_names]

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

        self.by_tag = {}
        self.by_label = {}

        self.load_items()

    def load_items(self):
        params = dict(
            type="Switch",
            recursive="false",
            fields="name,groupNames,label,tags"
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
                item_result['groupNames']
            )

            if item.label is not None:
                self.by_label.setdefault(item.label, []).append(item)

            for tag in item.tags:
                self.by_tag.setdefault(tag, []).append(item)

    def get_relevant_items(self, spoken_item, spoken_room=None):
        spoken_item = spoken_item.lower()

        if spoken_item in self.by_tag:
            items = self.by_tag[spoken_item]
        elif spoken_item in self.by_label:
            items = self.by_label[spoken_item]
        else:
            items = []

        if spoken_room is not None:
            items = [item for item in items if spoken_room.lower() in item.group_names]

        return items

    def send_command_to_devices(self, devices, command):
        for device in devices:
            url = "{0}/rest/items/{1}".format(self.openhab_server_url, device.name)
            requests.post(url, command)
