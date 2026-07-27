import discord
from discord.ext import commands
import os
import re
import time
from collections import defaultdict

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Config ---
LIMITE_MESSAGES = 5
INTERVALLE_SECONDES = 5
LIMITE_MENTIONS = 5
DOMAINES_AUTORISES = ["discord.com", "discord.gg", "tenor.com", "youtube.com", "youtu.be"]
IDS_ROLES_EXEMPTES = [1529522015655170200, 1529522258559766820, 1530160933421449398, 1529522458821001447]

historique_messages = defaultdict(list)

def est_exempte(membre):
    return any(role.id in IDS_ROLES_EXEMPTES for role in membre.roles)

def contient_lien_suspect(texte):
    liens = re.findall(r'https?://\S+', texte)
    for lien in liens:
        if not any(domaine in lien for domaine in DOMAINES_AUTORISES):
            return True
    return False

async def sanctionner(message, raison):
    try:
        await message.delete()
    except discord.NotFound:
        pass
    try:
        await message.author.ban(reason=raison)
        embed = discord.Embed(title="🚫 Ban automatique (Anti-Spam)", color=discord.Color.dark_red())
        embed.add_field(name="Membre", value=str(message.author), inline=True)
        embed.add_field(name="Raison", value=raison, inline=True)
        await message.channel.send(embed=embed)
    except discord.Forbidden:
        await message.channel.send(f"⚠️ Impossible de bannir {message.author.mention} (permissions insuffisantes).")

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    if est_exempte(message.author):
        await bot.process_commands(message)
        return

    # --- Détection flood ---
    maintenant = time.time()
    historique_messages[message.author.id].append(maintenant)
    historique_messages[message.author.id] = [
        t for t in historique_messages[message.author.id] if maintenant - t < INTERVALLE_SECONDES
    ]

    if len(historique_messages[message.author.id]) > LIMITE_MESSAGES:
        await sanctionner(message, "Flood de messages")
        historique_messages[message.author.id] = []
        return

    # --- Détection mentions massives ---
    if len(message.mentions) + len(message.role_mentions) > LIMITE_MENTIONS:
        await sanctionner(message, "Mentions massives (spam)")
        return

    if message.mention_everyone:
        await sanctionner(message, "Utilisation abusive de @everyone/@here")
        return

    # --- Détection liens suspects ---
    if contient_lien_suspect(message.content):
        await sanctionner(message, "Lien non autorisé (spam/pub)")
        return

    await bot.process_commands(message)

bot.run(os.environ["DISCORD_TOKEN"])