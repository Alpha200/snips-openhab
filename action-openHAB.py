#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from apscheduler.schedulers.background import BackgroundScheduler
from hermes_python.ontology.dialogue import InstantTimeValue
import dateutil.parser
from datetime import datetime

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
scheduler = None


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
    if len(intent_message.slots.room) > 0:
        room = intent_message.slots.room.first().value
    else:
        room = None

    if len(intent_message.slots.device) > 0:
        devices = [x.value for x in intent_message.slots.device.all()]
    else:
        devices = None

    return devices, room


def generate_switch_result_sentence(devices, command, run_date=None):
    l_devices = list(devices)

    if len(l_devices) == 1:
        formatted_devices = gd.get(l_devices[0].description(), Case.ACCUSATIVE)
    else:
        formatted_devices = ", ".join(gd.get(device.description(), Case.ACCUSATIVE)
                                      for device in l_devices[:len(l_devices) - 1]) + \
                            " und " + gd.get(l_devices[len(l_devices) - 1].description(), Case.ACCUSATIVE)

    if run_date is None:
        if command == "ON":
            command_spoken = "eingeschaltet"
        else:
            command_spoken = "ausgeschaltet"

        return "Ich habe dir {devices} {command}".format(devices=formatted_devices, command=command_spoken)
    else:
        if command == "ON":
            command_spoken = "einschalten"
        else:
            command_spoken = "ausschalten"

        if run_date.date() == datetime.now().date():
            date_formatted = run_date.strftime("um %H:%M Uhr")
        else:
            date_formatted = run_date.strftime("am %d.%m. um %H:%M Uhr")

        return "Ich werde dir {devices} {date} {command}".format(
            devices=formatted_devices,
            date=date_formatted,
            command=command_spoken
        )


def get_room_for_current_site(intent_message, default_room):
    if intent_message.site_id == "default":
        return default_room
    else:
        return intent_message.site_id


def what_do_you_know_about_callback(assistant, intent_message, conf):
    devices, spoken_room = get_items_and_room(intent_message)

    if spoken_room is not None:
        room = openhab.get_location(spoken_room)

        if room is None:
            return False, "Ich habe keinen Ort mit der Bezeichnung {location} gefunden".format(location=spoken_room)
    else:
        room = None

    if devices is None and room is not None:
        result = "Der Ort {spoken_room} trägt die Bezeichnung {room_label}. ".format(
            spoken_room=spoken_room, room_label=room.label
        )

        if len(room.synonyms) > 0 or room.semantics is not None:
            synonyms = room.synonyms
            if room.semantics is not None:
                synonyms += openhab.additional_synonyms[room.semantics]

            result += "Ich kenne ihn außerdem unter den Bezeichnungen {synonyms}. ".format(
                synonyms=", ".join(synonyms)
            )

        if room.is_part_of is not None:
            result += "Er liegt im Ort mit der Bezeichnung {other_location}. ".format(
                other_location=openhab.get_location(room.is_part_of).label
            )

        return None, result

    if devices is not None and len(devices) > 0:
        device_spoken = devices[0]

        devices_found = openhab.get_relevant_items(device_spoken, location=room)

        if len(devices_found) > 0:
            device = devices_found.pop()

            result = "Das Gerät {spoken_item} kenne ich unter der Bezeichnung {label}. ".format(
                spoken_item=device_spoken, label=device.label
            )

            if device.is_equipment():
                result += "Es ist vom Typ Equipment. "

            if device.is_point():
                result += "Es ist vom Typ Punkt. "

            if len(device.synonyms) > 0 or device.semantics is not None:
                synonyms = device.synonyms
                if device.semantics is not None:
                    synonyms = synonyms + openhab.additional_synonyms[device.semantics]

                result += "Ich kenne es außerdem unter den Bezeichnungen {synonyms}. ".format(
                    synonyms=", ".join(synonyms)
                )

            if device.is_part_of is not None:
                result += "Es ist Teil eines Equipments mit der Bezeichnung {other_device}. ".format(
                    other_device=openhab.items[device.is_part_of].label
                )

            if device.is_point_of is not None:
                result += "Es ist Teil eines Equipments mit der Bezeichnung {equipment}. ".format(
                    equipment=openhab.items[device.is_point_of].label
                )

            if device.has_location is not None:
                result += "Es liegt im Ort mit der Bezeichnung {location}. ".format(
                    location=openhab.items[device.has_location].label
                )

            if len(device.has_points) > 0:
                result += "Es besitzt außerdem Items mit den Bezeichnungen {items}. ".format(items=", ".join(
                    [openhab.items[item].label for item in device.has_points]
                ))

            return None, result
        else:
            return False, "Ich habe kein Gerät mit der Bezeichnung {device} gefunden.".format(device=device_spoken)

    return None, "Ich habe dich nicht verstanden."


def repeat_last_callback(assistant, intent_message, conf):
    return None, assistant.last_message


def clear_timed_callback(assistant, intent_message, conf):
    scheduler.remove_all_jobs()
    return True, "Ok, ich werde kein Gerät schalten"


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

        spoken_room = get_room_for_current_site(intent_message, conf['secret']['room_of_device_default'])
        room = openhab.get_location(spoken_room)

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

    if len(intent_message.slots.time) > 0:
        tp = intent_message.slots.time.first()
        if isinstance(tp, InstantTimeValue):
            date = dateutil.parser.parse(tp.value)
        else:
            date = dateutil.parser.parse(tp.from_date)

        def switch_items():
            openhab.send_command_to_devices(devices, command)

        scheduler.add_job(
            switch_items,
            'date',
            (),
            id='switch-{command}-{devices}'.format(
                command=command,
                devices='-'.join((device.description() for device in devices))
            ),
            run_date=date,
            replace_existing=True
        )

        result_sentence = generate_switch_result_sentence(relevant_devices, command, date)
    else:
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
            location=room
        )

        if len(items) > 0:
            dimmer_devices = [item for item in items if item.item_type == "Dimmer"]
            switch_devices = [item for item in items if item.item_type == "Switch"]

            if len(dimmer_devices) > 0:
                openhab.send_command_to_devices(dimmer_devices, "INCREASE" if increase else "DECREASE")

            if len(switch_devices) > 0:
                openhab.send_command_to_devices(switch_devices, "ON" if increase else "OFF")

            if len(dimmer_devices) + len(switch_devices) > 0:
                return True, "Ich habe die Helligkeit {} {}.".format(
                    add_local_preposition(spoken_room),
                    "verstärkt" if increase else "verringert"
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
        a.add_callback(user_intent("clearTimed"), clear_timed_callback)

        a.add_callback(user_intent("getTemperature"), get_temperature_callback)

        a.add_callback(user_intent("increaseItem"), increase_decrease_callback)
        a.add_callback(user_intent("decreaseItem"), increase_decrease_callback)

        a.add_callback(user_intent("setValue"), set_value_callback)

        a.add_callback(user_intent("playMedia"), player_callback)
        a.add_callback(user_intent("pauseMedia"), player_callback)
        a.add_callback(user_intent("nextMedia"), player_callback)
        a.add_callback(user_intent("previousMedia"), player_callback)

        a.add_callback(user_intent("repeatLastMessage"), repeat_last_callback)

        a.add_callback(user_intent("whatDoYouKnowAbout"), what_do_you_know_about_callback)

        openhab = OpenHAB(a.conf['secret']['openhab_server_url'])

        scheduler = BackgroundScheduler()
        scheduler.start()

        inject_items(a)
        a.start()
