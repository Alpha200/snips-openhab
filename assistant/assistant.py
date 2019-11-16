from assistant.config import read_configuration_file
import toml
from hermes_python.hermes import Hermes
from hermes_python.ontology import MqttOptions
from hermes_python.ontology.injection import InjectionRequestMessage, AddFromVanillaInjectionRequest
from hermes_python.ontology.tts import RegisterSoundMessage
from os import environ, path


class TestIntent:
    def __init__(self, intent_name):
        self.intent_name = intent_name


class TestValue:
    def __init__(self, value):
        self.value = value


class TestSlot:
    def __init__(self, values):
        self.values = values

    def first(self):
        if len(self.values) > 0:
            return self.values[0]
        else:
            return None

    def all(self):
        return self.values

    def __len__(self):
        return len(self.values)


class TestSlots:
    def __init__(self, slots):
        self.slots = slots

    def __getattr__(self, item):
        if item in self.slots:
            return self.slots[item]
        else:
            return []


class TestIntentMessage:
    def __init__(self, intent, slots, site_id="default"):
        self.intent = intent
        self.slots = slots
        self.site_id = site_id


class TestAssistant:
    def __init__(self):
        self.intents = {}
        self.conf = dict(
            secret=dict(room_of_device_default='schlafzimmer')
        )

    def add_callback(self, intent_name, callback):
        self.intents[intent_name] = callback

    def register_sound(self, sound_name, sound_data):
        pass

    def callback(self, intent_message):
        intent_name = intent_message.intent.intent_name

        if intent_name in self.intents:
            success, message = self.intents[intent_name](self, intent_message, self.conf)
            return success, message

    def inject(self, entities):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_val, trace):
        if not exception_type:
            return self
        return False

    def start(self):
        pass


class Assistant:
    def __init__(self):
        self.intents = {}
        self.last_message = None

        snips_config = toml.load('/etc/snips.toml')

        mqtt_username = None
        mqtt_password = None
        mqtt_broker_address = "localhost:1883"

        if 'mqtt' in snips_config['snips-common'].keys():
            mqtt_broker_address = snips_config['snips-common']['mqtt']
        if 'mqtt_username' in snips_config['snips-common'].keys():
            mqtt_username = snips_config['snips-common']['mqtt_username']
        if 'mqtt_password' in snips_config['snips-common'].keys():
            mqtt_password = snips_config['snips-common']['mqtt_password']

        mqtt_opts = MqttOptions(username=mqtt_username, password=mqtt_password, broker_address=mqtt_broker_address)

        self.hermes = Hermes(mqtt_options=mqtt_opts)
        self.conf = read_configuration_file()

        if 'OPENHAB_SERVER_URL' in environ:
            self.conf['secret']['openhab_server_url'] = environ.get('OPENHAB_SERVER_URL')
        if 'OPENHAB_ROOM_OF_DEVICE_DEFAULT' in environ:
            self.conf['secret']['room_of_device_default'] = environ.get('OPENHAB_ROOM_OF_DEVICE_DEFAULT')
        if 'OPENHAB_SOUND_FEEDBACK' in environ:
            self.conf['secret']['sound_feedback'] = environ.get('OPENHAB_SOUND_FEEDBACK')

        self.sound_feedback = self.conf['secret']["sound_feedback"] == "on"

    def add_callback(self, intent_name, callback):
        self.intents[intent_name] = callback

    def register_sound(self, sound_name, sound_data):
        self.hermes.register_sound(RegisterSoundMessage(sound_name, sound_data))

    def callback(self, intent_message):
        intent_name = intent_message.intent.intent_name

        if intent_name in self.intents:
            success, message = self.intents[intent_name](self, intent_message, self.conf)

            self.last_message = message

            if self.sound_feedback:
                if success is None:
                    self.hermes.publish_end_session(intent_message.session_id, message)
                elif success:
                    self.hermes.publish_end_session(intent_message.session_id, "[[sound:success]]")
                else:
                    # TODO: negative sound
                    self.hermes.publish_end_session(intent_message.session_id, message)
            else:
                self.hermes.publish_end_session(intent_message.session_id, message)

    def inject(self, entities):
        self.hermes.request_injection(InjectionRequestMessage([
            AddFromVanillaInjectionRequest(entities)
        ]))

    def __enter__(self):
        self.hermes.connect()
        return self

    def __exit__(self, exception_type, exception_val, trace):
        if not exception_type:
            self.hermes.disconnect()
            return self
        return False

    def start(self):
        def helper_callback(hermes, intent_message):
            self.callback(intent_message)

        with open(path.join(path.dirname(__file__), 'success.wav'), 'rb') as f:
            self.register_sound("success", bytearray(f.read()))

        self.hermes.subscribe_intents(helper_callback)
        self.hermes.start()
