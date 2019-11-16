import unittest
import responses

from assistant.assistant import TestIntentMessage, TestIntent, TestSlots, TestSlot, TestValue
from mocks.mocks import load_mocks, openhab_mock_base, add_anlage_an_aus_command_mock, add_get_temperature_mock, \
    add_anlage_volume_command_mock, add_esszimmer_lights_command_mock, add_player_command_mock

from actions import get_test_assistant, user_intent


class TestAssistant(unittest.TestCase):
    @responses.activate
    def test_switch_on_callback_empty(self):
        load_mocks()
        assistant = get_test_assistant(openhab_mock_base)

        success, message = assistant.callback(
            TestIntentMessage(
                TestIntent(user_intent("switchDeviceOn")),
                TestSlots({})
            )
        )

        self.assertFalse(success)
        self.assertEqual("Ich habe nicht verstanden, welches Gerät du einschalten möchtest.", message)

    @responses.activate
    def test_switch_on_callback_unknown_room(self):
        load_mocks()
        assistant = get_test_assistant(openhab_mock_base)

        success, message = assistant.callback(
            TestIntentMessage(
                TestIntent(user_intent("switchDeviceOn")),
                TestSlots(dict(
                    room=TestSlot([TestValue("blubbzimmer")])
                ))
            )
        )

        self.assertFalse(success)
        self.assertEqual("Ich habe keinen Ort mit der Bezeichnung blubbzimmer gefunden.", message)

    @responses.activate
    def test_switch_on_callback_anlage(self):
        load_mocks()
        add_anlage_an_aus_command_mock()
        assistant = get_test_assistant(openhab_mock_base)

        success, message = assistant.callback(
            TestIntentMessage(
                TestIntent(user_intent("switchDeviceOn")),
                TestSlots(dict(
                    device=TestSlot([TestValue("anlage")])
                ))
            )
        )

        self.assertTrue(success)
        self.assertEqual("Ich habe dir die anlage eingeschaltet.", message)

    @responses.activate
    def test_get_temperature_callback(self):
        load_mocks()
        add_get_temperature_mock()
        assistant = get_test_assistant(openhab_mock_base)

        success, message = assistant.callback(
            TestIntentMessage(
                TestIntent(user_intent("getTemperature")),
                TestSlots(dict(
                    room=TestSlot([TestValue("wohnzimmer")])
                ))
            )
        )

        self.assertIsNone(success)
        self.assertEqual("Die Temperatur im wohnzimmer beträgt 23,1 Grad.", message)

    @responses.activate
    def test_increase_volume(self):
        load_mocks()
        add_anlage_volume_command_mock()
        assistant = get_test_assistant(openhab_mock_base)

        success, message = assistant.callback(
            TestIntentMessage(
                TestIntent(user_intent("increaseItem")),
                TestSlots(dict(
                    property=TestSlot([TestValue("lautstärke")])
                ))
            )
        )

        self.assertTrue(success)
        self.assertEqual("Ich habe die lautstärke im schlafzimmer erhöht.", message)

    @responses.activate
    def test_increase_brightness(self):
        load_mocks()
        add_esszimmer_lights_command_mock()
        assistant = get_test_assistant(openhab_mock_base)

        success, message = assistant.callback(
            TestIntentMessage(
                TestIntent(user_intent("increaseItem")),
                TestSlots(dict(
                    property=TestSlot([TestValue("helligkeit")]),
                    room=TestSlot([TestValue("esszimmer")])
                ))
            )
        )

        self.assertTrue(success)
        self.assertEqual("Ich habe die Helligkeit im esszimmer verstärkt.", message)

    @responses.activate
    def test_play_wohnzimmer(self):
        load_mocks()
        add_player_command_mock()
        assistant = get_test_assistant(openhab_mock_base)

        success, message = assistant.callback(
            TestIntentMessage(
                TestIntent(user_intent("playMedia")),
                TestSlots(dict(
                    room=TestSlot([TestValue("wohnzimmer")])
                ))
            )
        )

        self.assertTrue(success)
        self.assertEqual("Ich habe die Wiedergabe im wohnzimmer fortgesetzt.", message)
