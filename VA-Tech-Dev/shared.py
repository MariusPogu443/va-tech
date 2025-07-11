# shared.py
import json

# Charger la config
with open("config.json") as f:
    config = json.load(f)

# Objets globaux
db_cfg = config["db"]
ftp_path = config["ftp_path"]

# Dictionnaires partagés
link_codes = {}       # { code : discord_id }
linked_users = {}     # { roblox_id : discord_id } si tu veux en cache aussi