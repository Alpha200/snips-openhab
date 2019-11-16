import configparser
import io

CONFIG_INI = "config.ini"


def write_configuration_file(conf):
    try:
        with io.open(CONFIG_INI, 'w', encoding="utf-8") as f:
            conf.write(f)
    except (IOError, configparser.Error):
        print("Failed to write config file!")


def read_configuration_file():
    try:
        with io.open(CONFIG_INI, encoding="utf-8") as f:
            conf_parser = configparser.ConfigParser()
            conf_parser.read_file(f)
            return conf_parser
    except (IOError, configparser.Error):
        return dict()
