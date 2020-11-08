def config_validation_errors(errors, filepath=None):
    sp_4 = " " * 4

    as_human = ["Configuration errors", f"{sp_4}File:[{filepath or 'ENV'}]"]

    for _err in errors:
        loc_str = ".".join(map(str, _err["loc"]))
        as_human.append(f"{sp_4}Section: [{loc_str}]: {_err['msg']}")

    return "\n".join(as_human)
