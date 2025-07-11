import discord
from discord.ext import commands
from discord import app_commands
import os, json, mysql.connector, random, string
import shared
import threading
import webserver
from flask import Flask

# Charger config
with open("config.json") as f:
    config = json.load(f)

db_cfg = config["db"]
ftp_path = config["ftp_path"]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    await webserver.start_webserver(bot)
    
    await bot.tree.sync()
    print("✅ Bot prêt et serveur web lancé.")

@bot.tree.command(name="link", description="Lier ton compte Roblox à Discord")
async def link(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    discord_id = interaction.user.id

    try:
        conn = mysql.connector.connect(**db_cfg)
        cur = conn.cursor()

        # 🔍 Vérifie si le user est déjà lié
        cur.execute("SELECT roblox_userid FROM linked_users WHERE discord_id = %s", (discord_id,))
        result = cur.fetchone()

        if result:
            await interaction.followup.send("✅ Ton compte est déjà lié à Roblox (UserID: `{}`) !".format(result[0]), ephemeral=True)
            cur.close()
            conn.close()
            return

        # Sinon, génère un code
        import random, string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # 💾 Stocke le code temporairement
        cur.execute("""
            INSERT INTO linked_users_temp (code, discord_id)
            VALUES (%s, %s)
        """, (code, discord_id))

        conn.commit()
        cur.close()
        conn.close()

        try:
            await interaction.user.send(f"🔗 Ton code de liaison Roblox est : `{code}`\nEntre ce code dans la map Roblox pour terminer la liaison.")
            await interaction.followup.send("📩 Je t'ai envoyé ton code en message privé !", ephemeral=True)
        except:
            await interaction.followup.send("❌ Impossible de t’envoyer un MP. Vérifie tes paramètres de confidentialité.", ephemeral=True)

    except Exception as e:
        print("❌ Erreur BDD /link :", e)
        await interaction.followup.send("❌ Une erreur est survenue lors de la génération du code.", ephemeral=True)

bot.run(config["discord_token"])
