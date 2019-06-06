#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
from hermes_python.hermes import Hermes
from hermes_python.ffi.utils import MqttOptions
from openhab import OpenHAB
from genderdeterminator import GenderDeterminator, Case
import io


CONFIGURATION_ENCODING_FORMAT = "utf-8"
CONFIG_INI = "config.ini"
USER_PREFIX = "Alpha200"

gd = GenderDeterminator()


def inject_local_preposition(noun):
    word = gd.get(noun, Case.DATIVE, append=False)
    word = "im" if word == "dem" else "in der"
    return "{} {}".format(word, noun)


def user_intent(intent_name):
    return "{}:{}".format(USER_PREFIX, intent_name)


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


def get_items_and_room(intent_message):
    if len(intent_message.slots.device) == 0:
        return None, None

    if len(intent_message.slots.room) > 0:
        room = intent_message.slots.room.first().value
    else:
        room = None

    return [x.value for x in intent_message.slots.device.all()], room


UNKNOWN_DEVICE = "Ich habe nicht verstanden, welches Gerät du {} möchtest."
UNKNOWN_TEMPERATURE = "Die Temperatur im {} ist unbekannt."
UNKNOWN_PROPERTY = "Ich habe nicht verstanden, welche Eigenschaft verändert werden soll."
FEATURE_NOT_IMPLEMENTED = "Diese Funktionalität ist aktuell nicht implementiert."


def generate_switch_result_sentence(devices, command):
    if command == "ON":
        command_spoken = "eingeschaltet"
    elif command == "OFF":
        command_spoken = "ausgeschaltet"
    else:
        command_spoken = ""

    if len(devices) == 1:
        return "Ich habe dir {} {}.".format(gd.get(devices[0].description(), Case.ACCUSATIVE), command_spoken)
    else:
        return "Ich habe dir {} {}.".format(
            ", ".join(gd.get(device.description(), Case.ACCUSATIVE) for device in devices[:len(devices) - 1])
            + " und " + gd.get(devices[len(devices) - 1].description(), Case.ACCUSATIVE),
            command_spoken
        )


def get_room_for_current_site(intent_message, default_room):
    if intent_message.site_id == "default":
        return default_room
    else:
        return intent_message.site_id


def intent_callback(hermes, intent_message):
    intent_name = intent_message.intent.intent_name

    if intent_name not in (
        user_intent("switchDeviceOn"),
        user_intent("switchDeviceOff"),
        user_intent("getTemperature"),
        user_intent("increaseItem"),
        user_intent("decreaseItem"),
        user_intent("setValue"),
        user_intent("playMedia"),
        user_intent("pauseMedia")
    ):
        return

    conf = read_configuration_file(CONFIG_INI)
    openhab = OpenHAB(conf['secret']['openhab_server_url'])

    if intent_name in (user_intent("switchDeviceOn"), user_intent("switchDeviceOff")):
        devices, room = get_items_and_room(intent_message)

        command = "ON" if intent_name == user_intent("switchDeviceOn") else "OFF"

        if room is None:
            room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

        if devices is None:
            hermes.publish_end_session(intent_message.session_id, UNKNOWN_DEVICE.format("einschalten" if command == "ON" else "ausschalten"))
            return

        relevant_devices = openhab.get_relevant_items(devices, room, item_filter='or')

        if len(relevant_devices) == 0:
            hermes.publish_end_session(intent_message.session_id, UNKNOWN_DEVICE.format("einschalten" if command == "ON" else "ausschalten"))
            return

        openhab.send_command_to_devices(relevant_devices, command)
        result_sentence = generate_switch_result_sentence(relevant_devices, command)
        hermes.publish_end_session(intent_message.session_id, result_sentence)
    elif intent_name == user_intent("getTemperature"):
        # TODO: Generalize this case as get property

        if len(intent_message.slots.room) > 0:
            room = intent_message.slots.room.first().value
        else:
            room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

        items = openhab.get_relevant_items(["temperatur", "messung"], room, "Number")

        if len(items) > 0:
            state = openhab.get_state(items[0])

            if state is None:
                hermes.publish_end_session(
                    intent_message.session_id,
                    UNKNOWN_TEMPERATURE.format(inject_local_preposition(room))
                )
                return

            formatted_temperature = state.replace(".", ",")
            hermes.publish_end_session(
                intent_message.session_id,
                "Die Temperatur {} beträgt {} Grad.".format(inject_local_preposition(room), formatted_temperature)
            )
        else:
            hermes.publish_end_session(
                intent_message.session_id,
                "Ich habe keinen Temperatursensor {} gefunden.".format(inject_local_preposition(room))
            )
    elif intent_name in (user_intent("increaseItem"), user_intent("decreaseItem")):
        increase = intent_name == user_intent("increaseItem")

        if len(intent_message.slots.room) > 0:
            room = intent_message.slots.room.first().value
        else:
            room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

        if len(intent_message.slots.property) == 0:
            hermes.publish_end_session(intent_message.session_id, UNKNOWN_PROPERTY)
            return

        device_property = intent_message.slots.property.first().value
        items = openhab.get_relevant_items([device_property, "sollwert"], room, "Dimmer")

        if len(items) > 0:
            openhab.send_command_to_devices(items, "INCREASE" if increase else "DECREASE")
            hermes.publish_end_session(
                intent_message.session_id,
                "Ich habe {} {} {}".format(
                    gd.get(device_property, Case.ACCUSATIVE),
                    inject_local_preposition(room),
                    "erhöht" if increase else "verringert"
                )
            )
        elif device_property == "Helligkeit":
            items = openhab.get_relevant_items("Licht", room, "Switch")

            if len(items) > 0:
                openhab.send_command_to_devices(items, "ON" if increase else "OFF")
                hermes.publish_end_session(
                    intent_message.session_id,
                    "Ich habe die Beleuchtung {} {}.".format(
                        inject_local_preposition(room),
                        "eingeschaltet" if increase else "ausgeschaltet"
                    )
                )
        elif device_property == "Temperatur":
            items = openhab.get_relevant_items([device_property, "sollwert"], room, "Number")

            if len(items) > 0:
                temperature = float(openhab.get_state(items[0]))
                temperature = temperature + (1 if increase else -1)
                openhab.send_command_to_devices([items[0]], str(temperature))
                hermes.publish_end_session(
                    intent_message.session_id,
                    "Ich habe die gewünschte Temperatur {} auf {} Grad eingestellt".format(
                        inject_local_preposition(room),
                        temperature
                    )
                )

        if len(items) == 0:
            hermes.publish_end_session(
                intent_message.session_id,
                "Ich habe keine Möglichkeit gefunden, um {} {} zu {}".format(
                    gd.get(device_property, Case.ACCUSATIVE),
                    inject_local_preposition(room),
                    "erhöhen" if increase else "verringern"
                )
            )
    elif intent_name == user_intent("setValue"):
        hermes.publish_end_session(
            intent_message.session_id,
            FEATURE_NOT_IMPLEMENTED
        )
    elif intent_name in [user_intent("playMedia"), user_intent("pauseMedia")]:
        if len(intent_message.slots.room) > 0:
            room = intent_message.slots.room.first().value
        else:
            room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

        items = openhab.get_relevant_items("fernbedienung", room, "Player")
        send_play = intent_name == user_intent("playMedia")

        if len(items) == 0:
            hermes.publish_end_session(
                intent_message.session_id,
                "Ich habe kein Gerät gefunden, auf dem die Wiedergabe geändert werden kann."
            )
            return

        openhab.send_command_to_devices(items, "PLAY" if send_play else "PAUSE")
        hermes.publish_end_session(
            intent_message.session_id,
            "Ich habe die Wiedergabe {} {}".format(
                inject_local_preposition(room), "fortgesetzt" if send_play else "pausiert")
        )


if __name__ == "__main__":
    mqtt_opts = MqttOptions()
    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intents(intent_callback)
        h.start()
