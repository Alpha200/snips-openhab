#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gettext
from assistant import Assistant
from openhab import OpenHAB
from genderdeterminator import GenderDeterminator, Case

_ = gettext.gettext

USER_PREFIX = "Alpha200"

UNKNOWN_DEVICE = _("I did not understand, which device you wanted to turn {action}.")
UNKNOWN_TEMPERATURE = _("The temperature {room} is unknown.")
UNKNOWN_PROPERTY = _("I did not understand which property you wanted to change.")
FEATURE_NOT_IMPLEMENTED = _("This feature is currently not implemented")

gd = GenderDeterminator()


def inject_items(assistant):
    openhab = OpenHAB(assistant.conf['secret']['openhab_server_url'])
    openhab.load_items()
    items, locations = openhab.get_injections()

    assistant.inject(dict(device=items, room=locations))


def add_local_preposition(noun):
    word = gd.get(noun, Case.DATIVE, append=False)
    word = "im" if word == "dem" else "in der"
    return "{} {}".format(word, noun)


def user_intent(intent_name):
    return "{}:{}".format(USER_PREFIX, intent_name)


def get_items_and_room(intent_message):
    if len(intent_message.slots.device) == 0:
        return None, None

    if len(intent_message.slots.room) > 0:
        room = intent_message.slots.room.first().value
    else:
        room = None

    return [x.value for x in intent_message.slots.device.all()], room


def generate_switch_result_sentence(devices, command):
    if command == "ON":
        command_spoken = _("on")
    elif command == "OFF":
        command_spoken = _("off")
    else:
        command_spoken = ""

    if len(devices) == 1:
        return _("I have turned {device} {action}.").format(
            device=gd.get(devices[0].description(), Case.ACCUSATIVE),
            action=command_spoken
        )
    else:
        return _("I have turned {devices} {action}.").format(
            devices=", ".join(gd.get(device.description(), Case.ACCUSATIVE) for device in devices[:len(devices) - 1])
            + " {} ".format(_("and")) + gd.get(devices[len(devices) - 1].description(), Case.ACCUSATIVE),
            action=command_spoken
        )


def get_room_for_current_site(intent_message, default_room):
    if intent_message.site_id == "default":
        return default_room
    else:
        return intent_message.site_id


def repeat_last_callback(assistant, intent_message, conf):
    return None, assistant.last_message


def switch_on_off_callback(assistant, intent_message, conf):
    openhab = OpenHAB(conf['secret']['openhab_server_url'])

    devices, room = get_items_and_room(intent_message)

    command = "ON" if intent_message.intent.intent_name == user_intent("switchDeviceOn") else "OFF"

    if devices is None:
        return False, UNKNOWN_DEVICE.format(action=_("on") if command == "ON" else _("off"))

    relevant_devices = openhab.get_relevant_items(devices, room, item_filter='or')

    # The user is allowed to ommit the room if the request matches exactly one device in the users home (e.g.
    # if there is only one tv) or if the request contains only devices of the current room
    if room is None and len(relevant_devices) > 1:
        print("Request without room matched more than one item. Requesting again with current room.")

        room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])
        relevant_devices = openhab.get_relevant_items(devices, room, item_filter='or')

        if len(relevant_devices) == 0:
            return False, _("Your request was not clear enough")

    if len(relevant_devices) == 0:
        return False, _("I was not able to find a device that matched your request")

    openhab.send_command_to_devices(relevant_devices, command)
    result_sentence = generate_switch_result_sentence(relevant_devices, command)

    return True, result_sentence


def get_temperature_callback(assistant, intent_message, conf):
    openhab = OpenHAB(conf['secret']['openhab_server_url'])
    # TODO: Generalize this case as get property

    if len(intent_message.slots.room) > 0:
        room = intent_message.slots.room.first().value
    else:
        room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

    items = openhab.get_relevant_items(["temperatur", "messung"], room, "Number")

    if len(items) > 0:
        state = openhab.get_state(items[0])

        if state is None:
            return None, UNKNOWN_TEMPERATURE.format(room=add_local_preposition(room))

        formatted_temperature = state.replace(".", ",")
        return None, _("The temperature {room} measures {temperature} degree.").format(room=add_local_preposition(room), temperature=formatted_temperature)
    else:
        return False, _("I did not find a temperature sensor {room}.").format(room=add_local_preposition(room))


def increase_decrease_callback(assistant, intent_message, conf):
    increase = intent_message.intent.intent_name == user_intent("increaseItem")

    if len(intent_message.slots.room) > 0:
        room = intent_message.slots.room.first().value
    else:
        room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

    if len(intent_message.slots.property) == 0:
        return False, UNKNOWN_PROPERTY

    device_property = intent_message.slots.property.first().value
    openhab = OpenHAB(conf['secret']['openhab_server_url'])
    items = openhab.get_relevant_items([device_property, "sollwert"], room, "Dimmer")

    if len(items) > 0:
        openhab.send_command_to_devices(items, "INCREASE" if increase else "DECREASE")
        return True, _("I have {property} {room} {action}").format(
            property=gd.get(device_property, Case.ACCUSATIVE),
            room=add_local_preposition(room),
            action=_("increased") if increase else _("decreased")
        )
    elif device_property == "Helligkeit":
        items = openhab.get_relevant_items("Licht", room, "Switch")

        if len(items) > 0:
            openhab.send_command_to_devices(items, "ON" if increase else "OFF")
            return True, _("I have turned {action} the lights {room}.").format(
                room=add_local_preposition(room),
                action=_("on") if increase else _("off")
            )
    elif device_property == "Temperatur":
        items = openhab.get_relevant_items([device_property, "sollwert"], room, "Number")

        if len(items) > 0:
            temperature = float(openhab.get_state(items[0]))
            temperature = temperature + (1 if increase else -1)
            openhab.send_command_to_devices([items[0]], str(temperature))
            return True, _("I have set the temperature {room} to {temperature} degree.").format(
                room=add_local_preposition(room),
                temperature=temperature
            )

    if len(items) == 0:
        return False, _("I did not find a way to {action} {property} {room}").format(
            property=gd.get(device_property, Case.ACCUSATIVE),
            room=add_local_preposition(room),
            action="erhöhen" if increase else "verringern"
        )


def set_value_callback(assistant, intent_message, conf):
    return None, FEATURE_NOT_IMPLEMENTED


def player_callback(assistant, intent_message, conf):
    if len(intent_message.slots.room) > 0:
        room = intent_message.slots.room.first().value
    else:
        room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

    openhab = OpenHAB(conf['secret']['openhab_server_url'])
    items = openhab.get_relevant_items("fernbedienung", room, "Player")

    if len(items) == 0:
        return False, _("I did not find a player device.")

    intent_name = intent_message.intent.intent_name

    if intent_name == user_intent("playMedia"):
        command = "PLAY"
        response = _("I have resumed the playback {room}").format(room=add_local_preposition(room))
    elif intent_name == user_intent("pauseMedia"):
        command = "PAUSE"
        response = _("I have paused the playback {room}").format(room=add_local_preposition(room))
    elif intent_name == user_intent("nextMedia"):
        command = "NEXT"
        response = _("I have skipped the playback {room}").format(room=add_local_preposition(room))
    else:
        command = "PREVIOUS"
        response = _("I have switched to the previous media {room}").format(room=add_local_preposition(room))

    openhab.send_command_to_devices(items, command)
    return True, response


if __name__ == "__main__":
    with Assistant() as a:
        a.add_callback(user_intent("switchDeviceOn"), switch_on_off_callback)
        a.add_callback(user_intent("switchDeviceOff"), switch_on_off_callback)

        a.add_callback(user_intent("getTemperature"), get_temperature_callback)

        a.add_callback(user_intent("increaseItem"), increase_decrease_callback)
        a.add_callback(user_intent("decreaseItem"), increase_decrease_callback)

        a.add_callback(user_intent("setValue"), set_value_callback)

        a.add_callback(user_intent("playMedia"), player_callback)
        a.add_callback(user_intent("pauseMedia"), player_callback)
        a.add_callback(user_intent("nextMedia"), player_callback)
        a.add_callback(user_intent("previousMedia"), player_callback)

        a.add_callback(user_intent("repeatLastMessage"), repeat_last_callback)

        inject_items(a)
        a.start()
