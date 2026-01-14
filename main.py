import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv
import psycopg2
import os
import random

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
connection = psycopg2.connect(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    sslmode=os.getenv('PGSSLMODE')
)

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
    cursor.execute("SELECT id_de_discord FROM usuarios WHERE id_de_discord = %s", (user_id,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        await ctx.send(f"{ctx.author.mention} ya te has registrado!")
        cursor.close()
        return
    
    # Registrar nuevo usuario con elo inicial de 0
    cursor.execute("INSERT INTO usuarios (id_de_discord, usuario, elo) VALUES (%s, %s, %s)", (user_id, username, 0))
    connection.commit()
    cursor.close()
    
    await ctx.send(f"{ctx.author.mention} te has registrado exitosamente con ELO inicial de 0!")

@bot.command()
async def match(ctx, user1: discord.Member, user2: discord.Member, resultado1: int, resultado2: int):
    print(f"Usuario 1 ID: {user1.id} - Resultado: {resultado1}")
    print(f"Usuario 2 ID: {user2.id} - Resultado: {resultado2}")
    
    cursor = connection.cursor()
    
    # Verificar que ambos usuarios estén registrados
    cursor.execute("SELECT id_de_discord, usuario, elo FROM usuarios WHERE id_de_discord = %s", (user1.id,))
    user1_data = cursor.fetchone()
    
    cursor.execute("SELECT id_de_discord, usuario, elo FROM usuarios WHERE id_de_discord = %s", (user2.id,))
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
    
    # Solicitar confirmación de ambos usuarios
    await ctx.send(
        f"⚠️ **Confirmación de Match**\n"
        f"{user1.mention} vs {user2.mention}\n"
        f"Resultado: {resultado1} - {resultado2}\n"
        f"Ganador: {ganador_mention}\n\n"
        f"**Ambos jugadores deben escribir `1` para confirmar o `0` para cancelar.**"
    )
    
    confirmaciones = {user1.id: False, user2.id: False}
    
    def check(message):
        return (
            message.author.id in [user1.id, user2.id] and 
            message.content in ["1", "0"] and 
            message.channel == ctx.channel
        )
    
    import asyncio
    
    try:
        while not all(confirmaciones.values()):
            mensaje = await bot.wait_for('message', timeout=60.0, check=check)
            
            # Si alguien escribe 0, cancelar
            if mensaje.content == "0":
                await ctx.send(f"❌ {mensaje.author.mention} ha cancelado el match.")
                cursor.close()
                return
            
            if not confirmaciones[mensaje.author.id]:
                confirmaciones[mensaje.author.id] = True
                await ctx.send(f"✅ {mensaje.author.mention} ha confirmado!")
                
                if not all(confirmaciones.values()):
                    pendiente = user1 if not confirmaciones[user1.id] else user2
                    await ctx.send(f"⏳ Esperando confirmación de {pendiente.mention}...")
    
    except asyncio.TimeoutError:
        await ctx.send("❌ Tiempo de confirmación agotado. El match ha sido cancelado.")
        cursor.close()
        return
    
    # Generar puntos aleatorios entre 19 y 25
    puntos = random.randint(19, 25)
    
    # Calcular nuevo ELO
    nuevo_elo_ganador = elo_ganador + puntos
    nuevo_elo_perdedor = max(0, elo_perdedor - puntos)  # No puede ser negativo
    
    # Actualizar ELO en la base de datos
    cursor.execute("UPDATE usuarios SET elo = %s WHERE id_de_discord = %s", (nuevo_elo_ganador, ganador_id))
    cursor.execute("UPDATE usuarios SET elo = %s WHERE id_de_discord = %s", (nuevo_elo_perdedor, perdedor_id))
    connection.commit()
    cursor.close()
    
    await ctx.send(
        f"✅ **Match confirmado y registrado!**\n"
        f"{ganador_mention} ganó contra {perdedor_mention}\n"
        f"**Puntos:** {puntos}\n"
        f"{ganador_mention}: {elo_ganador} → {nuevo_elo_ganador} (+{puntos})\n"
        f"{perdedor_mention}: {elo_perdedor} → {nuevo_elo_perdedor} (-{puntos})"
    )

@bot.command()
async def user(ctx, member: discord.Member = None):
    # Si no se menciona a nadie, mostrar el perfil del autor
    if member is None:
        member = ctx.author
    
    user_id = member.id
    
    cursor = connection.cursor()
    cursor.execute("SELECT usuario, elo FROM usuarios WHERE id_de_discord = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    
    if not user_data:
        await ctx.send(f"{member.mention} no está registrado! Usa ,register primero.")
        return
    
    usuario = user_data[0]
    elo_puntos = user_data[1]
    
    # Crear el embed
    embed = discord.Embed(
        title="📊 Perfil de Jugador",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Jugador", value=f"**{usuario}**", inline=False)
    embed.add_field(name="ELO", value=f"**{elo_puntos}** puntos", inline=False)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    if (user_id == 609812507845984326):
        embed.add_field(name="", value="*El Femboy supremo*", inline=False)
    embed.set_footer(text=f"Solicitado por {ctx.author.name}")
    
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    cursor = connection.cursor()
    cursor.execute("SELECT usuario, elo FROM usuarios ORDER BY elo DESC LIMIT 10")
    top_players = cursor.fetchall()
    cursor.close()
    
    if not top_players:
        await ctx.send("No hay jugadores registrados aún.")
        return
    
    # Crear el embed
    embed = discord.Embed(
        title="🏆 TOP 10 MEJORES JUGADORES 🏆",
        description="Ranking de los mejores jugadores por ELO",
        color=discord.Color.gold()
    )
    
    # Agregar los jugadores
    ranking = ""
    for i, (usuario, elo) in enumerate(top_players, 1):
        if i == 1:
            emoji = "🥇"
        elif i == 2:
            emoji = "🥈"
        elif i == 3:
            emoji = "🥉"
        else:
            emoji = f"**{i}.**"
        ranking += f"{emoji} {usuario} - **{elo}** ELO\n"
    
    embed.add_field(name="Rankings", value=ranking, inline=False)
    
    await ctx.send(embed=embed)

bot.run(TOKEN)