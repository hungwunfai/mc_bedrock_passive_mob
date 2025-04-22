import os
import shutil
import requests
import commentjson

def get_nested(data, keys, default=None):
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data

def void_player_filter(filters):
    # Check for a direct filter match
    if (filters.get("test") == "is_family" and 
        filters.get("subject") == "other" and 
        filters.get("value") == "player"):
        filters["value"] = "void"
        return True
    
    modified = False
    sub_filters = []
    # Check for a filter that uses an "any_of" or "all_of" list
    if "any_of" in filters and isinstance(filters["any_of"], list):
        sub_filters = filters["any_of"]
    if "all_of" in filters and isinstance(filters["all_of"], list):
        sub_filters = filters["all_of"]
    for filt in sub_filters:
        modified = void_player_filter(filt) or modified
    return modified

def fetch_and_process_entities():
    api_url = "https://api.github.com/repos/Mojang/bedrock-samples/contents/behavior_pack/entities?ref=v1.21.70.3"
    response = requests.get(api_url)
    if response.status_code != 200:
        print("Failed to fetch file list from GitHub. Status code:", response.status_code)
        return

    files = response.json()
    output_dir = os.path.join(".", "build", "Bouncyriceball_Passive_Mobs", "Bouncyriceball's Passive Mobs", "entities")

    # Clear the output directory if it exists
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    for file in files:
        # Skip files that are not JSON
        if not file.get("name", "").endswith(".json"):
            continue

        download_url = file.get("download_url")
        if not download_url:
            continue

        file_response = requests.get(download_url)
        if file_response.status_code != 200:
            print(f"Failed to fetch {file['name']}. Status code:", file_response.status_code)
            continue

        raw_text = file_response.text

        try:
            data = commentjson.loads(raw_text)
        except Exception as e:
            print(f"Failed to decode JSON for {file['name']}. Error: {e}")
            continue

        description = get_nested(data, ["minecraft:entity", "description"], {})
        spawn_category = description.get("spawn_category", "").lower()
        # Only process if entity is 'monster' and spawnable
        if spawn_category != "monster" or not description.get("is_spawnable", False):
            continue

        identifier = description.get("identifier")
        if not identifier:
            print(f"Identifier not found in {file['name']}")
            continue

        modified = False  # Flag to check if we apply any modifications
        # Enumerate all attributes with name "minecraft:behavior.nearest_attackable_target" under "minecraft:entity"
        # and remove the filter for "is_family" with "subject" as "other" and "value" as "player"
        behavior_components = []
        behavior_component = get_nested(data, ["minecraft:entity", "components", "minecraft:behavior.nearest_attackable_target"], {})
        if behavior_component:
            behavior_components.append(behavior_component)
        for group_name, comp_group in get_nested(data, ["minecraft:entity", "component_groups"], {}).items():
            behavior_component = comp_group.get("minecraft:behavior.nearest_attackable_target", {})
            if behavior_component:
                behavior_components.append(behavior_component)

        for behavior_component in behavior_components:
            orig_entity_types = behavior_component.get("entity_types", [])
            # Normalize to a list if it's a single object.
            if isinstance(orig_entity_types, dict):
                entity_types = [orig_entity_types]
            else:
                entity_types = orig_entity_types

            for et in entity_types:
                filters = et.get("filters", {})  
                if void_player_filter(filters):
                    modified = True

        # Write file only if it was modified
        if modified:
            try:
                output_file = os.path.join(output_dir, file["name"])
                with open(output_file, "w", encoding="utf-8") as f:
                    commentjson.dump(data, f, indent=2)
            except Exception as e:
                print(f"Failed to write {file['name']} to disk. Error: {e}")
                continue
            print(f"Modified: {identifier}")
        else:
            print(f"Unmodified: {identifier}")

if __name__ == '__main__':
    fetch_and_process_entities()
