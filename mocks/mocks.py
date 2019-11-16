import responses
import json
import os

openhab_mock_base = "http://localhost:8080"


def load_mocks() -> None:
    with open(os.path.join(os.path.dirname(__file__), "items.json")) as f:
        data = json.load(f)

    responses.add(
        responses.GET,
        openhab_mock_base + '/rest/items?recursive=false&fields=name%2Clabel%2Ctype%2Ceditable%2Cmetadata&metadata=semantics%2Csynonyms',
        json=data,
        status=200
    )


def add_item_command_mock() -> None:
    responses.add(
        responses.POST,
        openhab_mock_base + '/rest/items/Lampe_Esszimmer'
    )

    responses.add(
        responses.POST,
        openhab_mock_base + '/rest/items/Anlage_An_Aus'
    )


def add_get_state_mock() -> None:
    responses.add(
        responses.GET,
        openhab_mock_base + '/rest/items/Lampe_Bett',
        body='{"link":"http://localhost:8080/rest/items/Lampe_Bett","state":"OFF","editable":false,"type":"Switch","name":"Lampe_Bett","label":"Bettlampe","category":"light","tags":["Light"],"groupNames":["schlafzimmer"]}'
    )


def add_get_temperature_mock() -> None:
    responses.add(
        responses.GET,
        openhab_mock_base + '/rest/items/Temperature_Livingroom',
        body='{"link":"http://localhost:8080/rest/items/Temperature_Livingroom","state":"23.1","stateDescription":{"pattern":"%.1f °C","readOnly":false,"options":[]},"editable":false,"type":"Number","name":"Temperature_Livingroom","label":"Temperatur","category":"temperature","tags":["Measurement","Temperature"],"groupNames":["wohnzimmer"]}'
    )


def add_anlage_an_aus_command_mock() -> None:
    responses.add(
        responses.POST,
        openhab_mock_base + '/rest/items/Anlage_An_Aus'
    )


def add_anlage_volume_command_mock() -> None:
    responses.add(
        responses.POST,
        openhab_mock_base + '/rest/items/Anlage_Volume'
    )


def add_esszimmer_lights_command_mock() -> None:
    responses.add(
        responses.POST,
        openhab_mock_base + '/rest/items/Lampe_Esszimmer'
    )

    responses.add(
        responses.POST,
        openhab_mock_base + '/rest/items/Lampe_Vitrine'
    )


def add_player_command_mock() -> None:
    responses.add(
        responses.POST,
        openhab_mock_base + '/rest/items/Wohnzimmer_Control'
    )
