import responses
import unittest
from openhab.openhab import OpenHAB, Item
from mocks.mocks import load_mocks, openhab_mock_base, add_item_command_mock, add_get_state_mock


class TestOpenHAB(unittest.TestCase):
    @responses.activate
    def test_get_location_by_tag(self):
        load_mocks()
        oh = OpenHAB(openhab_mock_base)
        location = oh.get_location("schlafzimmer")

        self.assertIsInstance(location, Item)
        self.assertTrue(location.is_location())
        self.assertFalse(location.is_equipment())
        self.assertFalse(location.is_point())

    @responses.activate
    def test_send_command(self):
        load_mocks()
        add_item_command_mock()
        oh = OpenHAB("http://localhost:8080")
        light_dining = oh.items["Lampe_Esszimmer"]
        stereo = oh.items["Anlage_An_Aus"]

        oh.send_command_to_devices([
            light_dining,
            stereo
        ], "OFF")

    @responses.activate
    def test_get_state(self):
        load_mocks()
        add_get_state_mock()
        oh = OpenHAB(openhab_mock_base)

        state = oh.get_state(oh.items['Lampe_Bett'])
        self.assertEqual("OFF", state)

    @responses.activate
    def test_get_relevant_item(self):
        load_mocks()
        oh = OpenHAB(openhab_mock_base)

        light_apartment = oh.get_relevant_items("Licht", oh.get_location("wohnung"))

        self.assertIsInstance(light_apartment, set)
        self.assertEqual(len(light_apartment), 3)
        self.assertIn(oh.items["Lampe_Esszimmer"], light_apartment)
        self.assertIn(oh.items["Lampe_Vitrine"], light_apartment)
        self.assertIn(oh.items["Lampe_Bett"], light_apartment)

        light_diningroom = oh.get_relevant_items("Licht", oh.get_location("esszimmer"))

        self.assertIsInstance(light_diningroom, set)
        self.assertEqual(len(light_diningroom), 2)
        self.assertIn(oh.items["Lampe_Esszimmer"], light_diningroom)
        self.assertIn(oh.items["Lampe_Vitrine"], light_diningroom)

        stereo = oh.get_relevant_items("Anlage", None)

        self.assertIsInstance(stereo, set)
        self.assertEqual(len(stereo), 1)
        self.assertIn(oh.items["Anlage"], stereo)

        light_and_stereo = oh.get_relevant_items(["Licht", "Anlage"], oh.get_location("schlafzimmer"))

        self.assertIsInstance(light_and_stereo, set)
        self.assertEqual(len(light_and_stereo), 2)
        self.assertIn(oh.items["Lampe_Bett"], light_and_stereo)
        self.assertIn(oh.items["Anlage"], light_and_stereo)

    @responses.activate
    def test_get_items_with_attributes(self):
        load_mocks()
        oh = OpenHAB(openhab_mock_base)

        items = oh.get_items_with_attributes(
            "Point_Measurement",
            "Property_Temperature",
            location=oh.get_location("wohnzimmer")
        )

        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 1)
        self.assertIn(oh.items["Temperature_Livingroom"], items)

    @responses.activate
    def test_get_not_existing_location(self):
        load_mocks()
        oh = OpenHAB(openhab_mock_base)
        location = oh.get_location("NotExisting")

        self.assertIsNone(location)

    @responses.activate
    def test_get_injections(self):
        load_mocks()
        oh = OpenHAB(openhab_mock_base)
        injections = oh.get_injections()

        self.assertIsInstance(injections, tuple)
        self.assertEqual(len(injections), 2)

        items, locations = injections

        self.assertIsInstance(items, list)
        self.assertIsInstance(locations, list)

        self.assertIn("fernseher", items)
        self.assertNotIn("fernseher", locations)

        self.assertIn("schlafzimmer", locations)
        self.assertNotIn("schlafzimmer", items)
