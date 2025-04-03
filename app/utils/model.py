def normalize_config_types(config: dict) -> dict:
    for key, value in config.items():
        if isinstance(value, str):
            if value.lower() == "true":
                config[key] = True
            elif value.lower() == "false":
                config[key] = False
    return config
