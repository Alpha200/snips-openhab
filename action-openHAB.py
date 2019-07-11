#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from assistant import Assistant
from openhab import OpenHAB
from genderdeterminator import GenderDeterminator, Case

USER_PREFIX = "Alpha200"

UNKNOWN_DEVICE = "Ich habe nicht verstanden, welches Gerät du {} möchtest."
UNKNOWN_TEMPERATURE = "Die Temperatur {} ist unbekannt."
UNKNOWN_PROPERTY = "Ich habe nicht verstanden, welche Eigenschaft verändert werden soll."
FEATURE_NOT_IMPLEMENTED = "Diese Funktionalität ist aktuell nicht implementiert."

gd = GenderDeterminator()
openhab = None


def inject_items(assistant):
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
    l_devices = list(devices)

    if command == "ON":
        command_spoken = "eingeschaltet"
    elif command == "OFF":
        command_spoken = "ausgeschaltet"
    else:
        command_spoken = ""

    if len(l_devices) == 1:
        return "Ich habe dir {} {}.".format(gd.get(l_devices[0].description(), Case.ACCUSATIVE), command_spoken)
    else:
        return "Ich habe dir {} {}.".format(
            ", ".join(gd.get(device.description(), Case.ACCUSATIVE) for device in l_devices[:len(l_devices) - 1])
            + " und " + gd.get(l_devices[len(l_devices) - 1].description(), Case.ACCUSATIVE),
            command_spoken
        )


def get_room_for_current_site(intent_message, default_room):
    if intent_message.site_id == "default":
        return default_room
    else:
        return intent_message.site_id


def repeat_last_callback(assistant, intent_message, conf):
    return None, assistant.last_message


def switch_on_off_callback(assistant, intent_message, conf):
    devices, spoken_room = get_items_and_room(intent_message)

    if spoken_room is not None:
        room = openhab.get_location(spoken_room)

        if room is None:
            return False, "Ich habe keinen Ort mit der Bezeichnung {location} gefunden".format(location=spoken_room)
    else:
        room = None

    command = "ON" if intent_message.intent.intent_name == user_intent("switchDeviceOn") else "OFF"

    if devices is None:
        return False, UNKNOWN_DEVICE.format("einschalten" if command == "ON" else "ausschalten")

    relevant_devices = openhab.get_relevant_items(devices, room)

    # The user is allowed to ommit the room if the request matches exactly one device in the users home (e.g.
    # if there is only one tv) or if the request contains only devices of the current room
    if room is None and len(relevant_devices) > 1:
        print("Request without room matched more than one item. Requesting again with current room.")

        room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])
        relevant_devices = openhab.get_relevant_items(devices, room)

        if len(relevant_devices) == 0:
            return False, "Deine Anfrage war nicht eindeutig genug"

    if len(relevant_devices) == 0:
        return False, "Ich habe kein Gerät gefunden, welches zu deiner Anfrage passt"

    devices = set()

    for device in relevant_devices:
        if device.item_type in ("Switch", "Dimmer"):
            devices.add(device)
        elif device.item_type == "Group" and device.is_equipment():
            for point in device.has_points:
                point_item = openhab.items[point]

                if point_item.semantics == "Point_Control_Switch":
                    devices.add(point_item)

    openhab.send_command_to_devices(devices, command)
    result_sentence = generate_switch_result_sentence(relevant_devices, command)

    return True, result_sentence


def get_temperature_callback(assistant, intent_message, conf):
    # TODO: Generalize this case as get property

    if len(intent_message.slots.room) > 0:
        spoken_room = intent_message.slots.room.first().value
    else:
        spoken_room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

    room = openhab.get_location(spoken_room)

    if room is None:
        return False, "Ich habe keinen Ort mit der Bezeichnung {location} gefunden".format(location=spoken_room)

    items = openhab.get_items_with_attributes("Point_Measurement", "Property_Temperature", location=room)

    if len(items) > 0:
        state = openhab.get_state(items[0])

        if state is None:
            return None, UNKNOWN_TEMPERATURE.format(add_local_preposition(spoken_room))

        formatted_temperature = state.replace(".", ",")
        return None, "Die Temperatur {} beträgt {} Grad.".format(
            add_local_preposition(spoken_room), formatted_temperature
        )
    else:
        return False, "Ich habe keinen Temperatursensor {} gefunden.".format(add_local_preposition(spoken_room))


def increase_decrease_callback(assistant, intent_message, conf):
    increase = intent_message.intent.intent_name == user_intent("increaseItem")

    if len(intent_message.slots.room) > 0:
        spoken_room = intent_message.slots.room.first().value
    else:
        spoken_room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

    room = openhab.get_location(spoken_room)

    if room is None:
        return False, "Ich habe keinen Ort mit der Bezeichnung {location} gefunden".format(location=spoken_room)

    if len(intent_message.slots.property) == 0:
        return False, UNKNOWN_PROPERTY

    device_property = intent_message.slots.property.first().value

    if device_property == "Helligkeit":
        items = openhab.get_items_with_attributes(
            "Point_Control",
            esm_property="Property_Light",
            location=room,
            item_type="Switch"
        )

        if len(items) > 0:
            openhab.send_command_to_devices(items, "ON" if increase else "OFF")
            return True, "Ich habe die Beleuchtung {} {}.".format(
                add_local_preposition(spoken_room),
                "eingeschaltet" if increase else "ausgeschaltet"
            )
    elif device_property == "Temperatur":
        items = openhab.get_items_with_attributes("Point_Control", location=room, item_type="Number")

        if len(items) > 0:
            temperature = float(openhab.get_state(items[0]))
            temperature = temperature + (1 if increase else -1)
            openhab.send_command_to_devices([items[0]], str(temperature))
            return True, "Ich habe die gewünschte Temperatur {} auf {} Grad eingestellt".format(
                add_local_preposition(spoken_room),
                temperature
            )
    else:
        items = openhab.get_relevant_items(device_property, room, item_type="Dimmer")

        if len(items) > 0:
            openhab.send_command_to_devices(items, "INCREASE" if increase else "DECREASE")
            return True, "Ich habe {} {} {}".format(
                gd.get(device_property, Case.ACCUSATIVE),
                add_local_preposition(spoken_room),
                "erhöht" if increase else "verringert"
            )

    if len(items) == 0:
        return False, "Ich habe keine Möglichkeit gefunden, um {} {} zu {}".format(
            gd.get(device_property, Case.ACCUSATIVE),
            add_local_preposition(spoken_room),
            "erhöhen" if increase else "verringern"
        )


def set_value_callback(assistant, intent_message, conf):
    return None, FEATURE_NOT_IMPLEMENTED


def player_callback(assistant, intent_message, conf):
    if len(intent_message.slots.room) > 0:
        spoken_room = intent_message.slots.room.first().value
    else:
        spoken_room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])

    room = openhab.get_location(spoken_room)

    if room is None:
        return False, "Ich habe keinen Ort mit der Bezeichnung {location} gefunden".format(location=spoken_room)

    items = openhab.get_items_with_attributes("Point_Control", location=room, item_type="Player")

    if len(items) == 0:
        return False, "Ich habe kein Gerät gefunden, an dem ich die Wiedergabe ändern kann."

    intent_name = intent_message.intent.intent_name

    if intent_name == user_intent("playMedia"):
        command = "PLAY"
        response = "Ich habe die Wiedergabe {} fortgesetzt".format(add_local_preposition(spoken_room))
    elif intent_name == user_intent("pauseMedia"):
        command = "PAUSE"
        response = "Ich habe die Wiedergabe {} pausiert".format(add_local_preposition(spoken_room))
    elif intent_name == user_intent("nextMedia"):
        command = "NEXT"
        response = "Die aktuelle Wiedergabe wird {} übersprungen".format(add_local_preposition(spoken_room))
    else:
        command = "PREVIOUS"
        response = "{} geht es zurück zur vorherigen Wiedergabe".format(add_local_preposition(spoken_room))

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

        openhab = OpenHAB(a.conf['secret']['openhab_server_url'])

        inject_items(a)
        a.start()
