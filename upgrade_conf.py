from assistant.config import read_configuration_file, write_configuration_file

CURRENT = "2.0"

if __name__ == "__main__":
    conf = read_configuration_file()
    old = False

    if "static" not in conf:
        old = True
        conf["static"] = {}
        conf["secret"]["sound_feedback"] = "off"

    if old:
        conf["static"]["conf_version"] = CURRENT
        write_configuration_file(conf)
