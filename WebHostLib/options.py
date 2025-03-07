import json
import logging
import os
import typing

import yaml
from jinja2 import Template

import Options
from Utils import __version__, local_path
from worlds.AutoWorld import AutoWorldRegister

handled_in_js = {"start_inventory", "local_items", "non_local_items", "start_hints", "start_location_hints",
                 "exclude_locations", "priority_locations"}


def create():
    target_folder = local_path("WebHostLib", "static", "generated")
    yaml_folder = os.path.join(target_folder, "configs")

    Options.generate_yaml_templates(yaml_folder)

    def get_html_doc(option_type: type(Options.Option)) -> str:
        if not option_type.__doc__:
            return "Please document me!"
        return "\n".join(line.strip() for line in option_type.__doc__.split("\n")).strip()

    weighted_settings = {
        "baseOptions": {
            "description": "Generated by https://archipelago.gg/",
            "name": "Player",
            "game": {},
        },
        "games": {},
    }

    for game_name, world in AutoWorldRegister.world_types.items():

        all_options: typing.Dict[str, Options.AssembleOptions] = {
            **Options.per_game_common_options,
            **world.option_definitions
        }

        # Generate JSON files for player-settings pages
        player_settings = {
            "baseOptions": {
                "description": "Generated by https://archipelago.gg/",
                "game": game_name,
                "name": "Player",
            },
        }

        game_options = {}
        for option_name, option in all_options.items():
            if option_name in handled_in_js:
                pass

            elif issubclass(option, Options.Choice) or issubclass(option, Options.Toggle):
                game_options[option_name] = this_option = {
                    "type": "select",
                    "displayName": option.display_name if hasattr(option, "display_name") else option_name,
                    "description": get_html_doc(option),
                    "defaultValue": None,
                    "options": []
                }

                for sub_option_id, sub_option_name in option.name_lookup.items():
                    if sub_option_name != "random":
                        this_option["options"].append({
                            "name": option.get_option_name(sub_option_id),
                            "value": sub_option_name,
                        })
                    if sub_option_id == option.default:
                        this_option["defaultValue"] = sub_option_name

                if not this_option["defaultValue"]:
                    this_option["defaultValue"] = "random"

            elif issubclass(option, Options.Range):
                game_options[option_name] = {
                    "type": "range",
                    "displayName": option.display_name if hasattr(option, "display_name") else option_name,
                    "description": get_html_doc(option),
                    "defaultValue": option.default if hasattr(
                        option, "default") and option.default != "random" else option.range_start,
                    "min": option.range_start,
                    "max": option.range_end,
                }

                if issubclass(option, Options.SpecialRange):
                    game_options[option_name]["type"] = 'special_range'
                    game_options[option_name]["value_names"] = {}
                    for key, val in option.special_range_names.items():
                        game_options[option_name]["value_names"][key] = val

            elif issubclass(option, Options.ItemSet):
                game_options[option_name] = {
                    "type": "items-list",
                    "displayName": option.display_name if hasattr(option, "display_name") else option_name,
                    "description": get_html_doc(option),
                    "defaultValue": list(option.default)
                }

            elif issubclass(option, Options.LocationSet):
                game_options[option_name] = {
                    "type": "locations-list",
                    "displayName": option.display_name if hasattr(option, "display_name") else option_name,
                    "description": get_html_doc(option),
                    "defaultValue": list(option.default)
                }

            elif issubclass(option, Options.VerifyKeys) and not issubclass(option, Options.OptionDict):
                if option.valid_keys:
                    game_options[option_name] = {
                        "type": "custom-list",
                        "displayName": option.display_name if hasattr(option, "display_name") else option_name,
                        "description": get_html_doc(option),
                        "options": list(option.valid_keys),
                        "defaultValue": list(option.default) if hasattr(option, "default") else []
                    }

            else:
                logging.debug(f"{option} not exported to Web Settings.")

        player_settings["gameOptions"] = game_options

        os.makedirs(os.path.join(target_folder, 'player-settings'), exist_ok=True)

        with open(os.path.join(target_folder, 'player-settings', game_name + ".json"), "w") as f:
            json.dump(player_settings, f, indent=2, separators=(',', ': '))

        if not world.hidden and world.web.settings_page is True:
            # Add the random option to Choice, TextChoice, and Toggle settings
            for option in game_options.values():
                if option["type"] == "select":
                    option["options"].append({"name": "Random", "value": "random"})

                    if not option["defaultValue"]:
                        option["defaultValue"] = "random"

            weighted_settings["baseOptions"]["game"][game_name] = 0
            weighted_settings["games"][game_name] = {}
            weighted_settings["games"][game_name]["gameSettings"] = game_options
            weighted_settings["games"][game_name]["gameItems"] = tuple(world.item_names)
            weighted_settings["games"][game_name]["gameLocations"] = tuple(world.location_names)

    with open(os.path.join(target_folder, 'weighted-settings.json'), "w") as f:
        json.dump(weighted_settings, f, indent=2, separators=(',', ': '))
