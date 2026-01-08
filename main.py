import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv
import mysql.connector
import os
import random

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
connection = mysql.connector.connect(user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'), database=os.getenv('DB_NAME'), port=int(os.getenv('DB_PORT')))

print(connection)

intents = discord.Intents.all()
intents.messages = True
intents.members = True

bot = commands.Bot(command_prefix=',', intents=intents)

@bot.command()
async def register(ctx):
    user_id = ctx.author.id
    username = str(ctx.author)
    
    cursor = connection.cursor()
    
    # Verificar si el usuario ya existe
    cursor.execute("SELECT id FROM usuarios WHERE id = %s", (user_id,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        await ctx.send(f"{ctx.author.mention} ya te has registrado!")
        cursor.close()
        return
    
    # Registrar nuevo usuario con elo inicial de 0
    cursor.execute("INSERT INTO usuarios (id, nombre, elo) VALUES (%s, %s, %s)", (user_id, username, 0))
    connection.commit()
    cursor.close()
    
    await ctx.send(f"{ctx.author.mention} te has registrado exitosamente con ELO inicial de 0!")

@bot.command()
async def match(ctx, user1: discord.Member, user2: discord.Member, resultado1: int, resultado2: int):
    print(f"Usuario 1 ID: {user1.id} - Resultado: {resultado1}")
    print(f"Usuario 2 ID: {user2.id} - Resultado: {resultado2}")
    
    cursor = connection.cursor()
    
    # Verificar que ambos usuarios estén registrados
    cursor.execute("SELECT id, nombre, elo FROM usuarios WHERE id = %s", (user1.id,))
    user1_data = cursor.fetchone()
    
    cursor.execute("SELECT id, nombre, elo FROM usuarios WHERE id = %s", (user2.id,))
    user2_data = cursor.fetchone()
    
    if not user1_data:
        await ctx.send(f"{user1.mention} no está registrado! Usa ,register primero.")
        cursor.close()
        return
    
    if not user2_data:
        await ctx.send(f"{user2.mention} no está registrado! Usa ,register primero.")
        cursor.close()
        return
    
    # Determinar el ganador
    if resultado1 > resultado2:
        ganador_id = user1.id
        perdedor_id = user2.id
        ganador_mention = user1.mention
        perdedor_mention = user2.mention
        elo_ganador = user1_data[2]
        elo_perdedor = user2_data[2]
    elif resultado2 > resultado1:
        ganador_id = user2.id
        perdedor_id = user1.id
        ganador_mention = user2.mention
        perdedor_mention = user1.mention
        elo_ganador = user2_data[2]
        elo_perdedor = user1_data[2]
    else:
        await ctx.send(f"Empate entre {user1.mention} y {user2.mention}")
        cursor.close()
        return
    
    # Generar puntos aleatorios entre 19 y 25
    puntos = random.randint(19, 25)
    
    # Calcular nuevo ELO
    nuevo_elo_ganador = elo_ganador + puntos
    nuevo_elo_perdedor = max(0, elo_perdedor - puntos)  # No puede ser negativo
    
    # Actualizar ELO en la base de datos
    cursor.execute("UPDATE usuarios SET elo = %s WHERE id = %s", (nuevo_elo_ganador, ganador_id))
    cursor.execute("UPDATE usuarios SET elo = %s WHERE id = %s", (nuevo_elo_perdedor, perdedor_id))
    connection.commit()
    cursor.close()
    
    await ctx.send(
        f"Match finalizado: {ganador_mention} ganó contra {perdedor_mention}\n"
        f"**Puntos:** {puntos}\n"
        f"{ganador_mention}: {elo_ganador} → {nuevo_elo_ganador} (+{puntos})\n"
        f"{perdedor_mention}: {elo_perdedor} → {nuevo_elo_perdedor} (-{puntos})"
    )

@bot.command()
async def user(ctx):
    user_id = ctx.author.id
    
    cursor = connection.cursor()
    cursor.execute("SELECT nombre, elo FROM usuarios WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    
    if not user_data:
        await ctx.send(f"{ctx.author.mention} no estás registrado! Usa ,register primero.")
        return
    
    nombre = user_data[0]
    elo_puntos = user_data[1]
    
    await ctx.send(f"**{nombre}**\nELO: {elo_puntos}")

@bot.command()
async def top(ctx):
    cursor = connection.cursor()
    cursor.execute("SELECT nombre, elo FROM usuarios ORDER BY elo DESC LIMIT 10")
    top_players = cursor.fetchall()
    cursor.close()
    
    if not top_players:
        await ctx.send("No hay jugadores registrados aún.")
        return
    
    mensaje = "🏆 **TOP 10 MEJORES JUGADORES** 🏆\n\n"
    for i, (nombre, elo) in enumerate(top_players, 1):
        if i == 1:
            emoji = "🥇"
        elif i == 2:
            emoji = "🥈"
        elif i == 3:
            emoji = "🥉"
        else:
            emoji = f"{i}."
        mensaje += f"{emoji} **{nombre}** - {elo} ELO\n"
    
    await ctx.send(mensaje)

bot.run(TOKEN)