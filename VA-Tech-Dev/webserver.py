from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import json, os, discord, asyncio
from threading import Thread
from shared import db_cfg

with open("config.json") as f:
    config = json.load(f)

ftp_path = config["ftp_path"]
app = Flask(__name__)
CORS(app)  # Autorise toutes les origines (y compris Roblox/Hoppscotch)

bot_reference = None

@app.route("/")
def index():
    return "✅ Webserver actif !"

@app.route("/send", methods=["POST"])
def send():
    data = request.json
    user_id = int(data["discord_id"])
    file_name = data["file_name"]
    path = os.path.join(ftp_path, file_name)

    async def send_file():
        try:
            user = await bot_reference.fetch_user(user_id)
            await user.send("📦 Merci pour ton achat ! Voici ton modèle :", file=discord.File(path))
        except Exception as e:
            print("❌ Erreur lors de l'envoi du MP :", e)

    asyncio.run_coroutine_threadsafe(send_file(), asyncio.get_event_loop())
    return jsonify({"status": "ok"})

@app.route("/link", methods=["POST", "OPTIONS"])
def link_player():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 204

    data = request.json or {}
    print("📨 Requête reçue /link")
    print("➡️ Headers:", dict(request.headers))
    print("➡️ Body brut:", request.data)
    print("➡️ JSON décodé:", data)

    roblox_userid = data.get('roblox_userid')
    code = data.get('code')

    if not code or not roblox_userid:
        return jsonify({"success": False, "message": "Données manquantes"}), 400

    try:
        conn = mysql.connector.connect(**db_cfg)
        cur = conn.cursor()

        # 🔍 Vérifier que le code existe et récupérer l'ID Discord
        cur.execute("SELECT discord_id FROM linked_users_temp WHERE code = %s", (code,))
        row = cur.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Code invalide"}), 400

        discord_id = row[0]

        # ✅ Insérer dans linked_users
        cur.execute("""
            INSERT INTO linked_users (discord_id, roblox_userid, linked_at)
            VALUES (%s, %s, NOW())
        """, (discord_id, roblox_userid))

        # 🧹 Supprimer le code utilisé
        cur.execute("DELETE FROM linked_users_temp WHERE code = %s", (code,))

        conn.commit()
        cur.close()
        conn.close()

        print("✅ Liaison enregistrée pour Discord ID", discord_id)
        return jsonify({"success": True, "message": "Compte lié avec succès"})

    except Exception as e:
        print("❌ Erreur MySQL /link :", e)
        return jsonify({"success": False, "message": "Erreur serveur"}), 500

@app.route("/status")
def check_linked_user():
    roblox_userid = request.args.get("roblox_userid")
    if not roblox_userid:
        return jsonify({"success": False, "message": "User ID manquant"}), 400

    try:
        conn = mysql.connector.connect(**db_cfg)
        cur = conn.cursor()

        cur.execute("SELECT discord_id FROM linked_users WHERE roblox_userid = %s", (roblox_userid,))
        row = cur.fetchone()

        cur.close()
        conn.close()

        if row:
            return jsonify({"success": True, "discord_id": row[0]})
        else:
            return jsonify({"success": False, "message": "Non lié"})
    except Exception as e:
        print("❌ Erreur MySQL /status :", e)
        return jsonify({"success": False, "message": "Erreur serveur"}), 500

from datetime import datetime

@app.route("/models", methods=["GET"])
def get_models():
    try:
        conn = mysql.connector.connect(**db_cfg)
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, name, image_id, gamepass_id, created_at
            FROM products
            WHERE actif = 1
        """)
        rows = cur.fetchall()

        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "name": row["name"],
                "image_url": row["image_id"],  # ou adapte selon ton lien
                "gamepass_id": row["gamepass_id"],
                "uploaded_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
            })

        cur.close()
        conn.close()

        return jsonify({"success": True, "models": result})

    except Exception as e:
        print("❌ Erreur /models :", e)
        return jsonify({"success": False, "message": "Erreur serveur"}), 500


def run_flask():
    print("🟢 run_flask() lancé, démarrage de Flask sur le port 8080")
    app.run(host="0.0.0.0", port=8080)

async def start_webserver(bot):
    global bot_reference
    bot_reference = bot

    Thread(target=run_flask, daemon=True).start()