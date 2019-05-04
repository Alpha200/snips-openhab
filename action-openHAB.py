#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
from hermes_python.hermes import Hermes
from hermes_python.ffi.utils import MqttOptions
from openhab import OpenHAB
import io


CONFIGURATION_ENCODING_FORMAT = "utf-8"
CONFIG_INI = "config.ini"
USER_PREFIX = "Alpha200"


def user_intent(intent_name):
    return "{0}:{1}".format(USER_PREFIX, intent_name)


class SnipsConfigParser(configparser.SafeConfigParser):
    def to_dict(self):
        return {
            section: {option_name: option for option_name, option in self.items(section)} for section in self.sections()
        }


def read_configuration_file(configuration_file):
    try:
        with io.open(configuration_file, encoding=CONFIGURATION_ENCODING_FORMAT) as f:
            conf_parser = SnipsConfigParser()
            conf_parser.read_file(f)
            return conf_parser.to_dict()
    except (IOError, configparser.Error):
        return dict()


def get_item_and_room(intent_message):
    if len(intent_message.slots.device) == 0:
        return None, None

    if len(intent_message.slots.room) > 0:
        room = intent_message.slots.room.first().value
    else:
        room = None

    return intent_message.slots.device.first().value, room


UNKNOWN_DEVICE = "Ich habe nicht verstanden, welches Gerät du einschalten möchtest."


def generate_switch_result_sentence(devices, command):
    if command == "ON":
        command_spoken = "eingeschaltet"
    elif command == "OFF":
        command_spoken = "ausgeschaltet"
    else:
        command_spoken = ""

    if len(devices) == 1:
        return "Ich habe dir das Gerät {0} {1}.".format(devices[0].description(), command_spoken)
    else:
        return "Ich habe dir die Geräte {0} {1}.".format(
            ", ".join(device.description() for device in devices[:len(devices) - 1]) + " und " + devices[
                len(devices) - 1].description(),
            command_spoken
        )


def intent_callback(hermes, intent_message):
    intent_name = intent_message.intent.intent_name

    if intent_name not in [user_intent("switchDeviceOn"), user_intent("switchDeviceOff")]:
        return

    conf = read_configuration_file(CONFIG_INI)
    openhab = OpenHAB(conf['secret']['openhab_server_url'])

    if intent_name in [user_intent("switchDeviceOn"), user_intent("switchDeviceOff")]:
        device, room = get_item_and_room(intent_message)

        if room is None:
            if intent_message.site_id == "default":
                room = conf['secret']['room_of_device_default']
            else:
                room = intent_message.site_id

        if device is None:
            hermes.publish_end_session(intent_message.session_id, UNKNOWN_DEVICE)
            return

        relevant_devices = openhab.get_relevant_items(device, room)

        if len(relevant_devices) == 0:
            hermes.publish_end_session(intent_message.session_id, UNKNOWN_DEVICE)
            return

        command = "ON" if intent_name == user_intent("switchDeviceOn") else "OFF"

        openhab.send_command_to_devices(relevant_devices, command)
        result_sentence = generate_switch_result_sentence(relevant_devices, command)
        hermes.publish_end_session(intent_message.session_id, result_sentence)


if __name__ == "__main__":
    mqtt_opts = MqttOptions()
    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intents(intent_callback)
        h.start()
