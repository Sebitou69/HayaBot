import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime

# --- BASE DE DATOS ---
DB_FILE = 'personajes.json'

# Inicializamos el JSON con la estructura completa si no existe
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w') as f:
        json.dump({"ocupados": [], "deseados": [], "actividad": {}}, f)

def cargar_datos():
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def guardar_datos(datos):
    with open(DB_FILE, 'w') as f:
        json.dump(datos, f, indent=4)

# --- CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.message_content = True # VITAL para leer los mensajes del chat

bot = commands.Bot(command_prefix="!", intents=intents)

# --- EVENTOS PRINCIPALES ---
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    
    # Arranca el bucle de revisión de inactividad
    if not revisar_inactivos.is_running():
        revisar_inactivos.start()
        print("Módulo de inactividad automático iniciado.")
        
    try:
        # IMPORTANTE 1: Reemplaza con el ID de TU servidor
        servidor = discord.Object(id=1495565448601927821) 
        
        bot.tree.copy_global_to(guild=servidor)
        synced = await bot.tree.sync(guild=servidor)
        print(f"Sincronizados {len(synced)} comandos en el servidor.")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message):
    # Ignora a los bots
    if message.author.bot:
        return

    # Registra la fecha exacta del último mensaje del usuario
    datos = cargar_datos()
    if "actividad" not in datos:
        datos["actividad"] = {}

    datos["actividad"][str(message.author.id)] = datetime.now().isoformat()
    guardar_datos(datos)

    # Permite que los comandos de barra sigan funcionando
    await bot.process_commands(message)

# --- TAREA AUTOMÁTICA (Background Loop) ---
@tasks.loop(hours=24)
async def revisar_inactivos():
    await bot.wait_until_ready()
    
    datos = cargar_datos()
    if "actividad" not in datos:
        return
        
    # IMPORTANTE 2: Reemplaza con el ID del canal donde el bot mandará las purgas (ej. #anuncios)
    canal_avisos = bot.get_channel(1495589358852505630) 
    if not canal_avisos:
        print("Error: No se encontró el canal de avisos.")
        return

    hoy = datetime.now()
    
    for user_id_str, fecha_str in list(datos["actividad"].items()):
        ultima_fecha = datetime.fromisoformat(fecha_str)
        diferencia = (hoy - ultima_fecha).days
        
        if diferencia == 7:
            await canal_avisos.send(f"⚠️ <@{user_id_str}>, llevas **7 días** inactivo. ¡Recuerda participar para mantener tu personaje!")
        elif diferencia >= 14:
            await canal_avisos.send(f"❌ <@{user_id_str}> ha alcanzado los **14 días** de inactividad. Su personaje queda libre.")

# --- COMANDOS: OCUPADOS (PO) ---
@bot.tree.command(name="po_add", description="Añade un personaje a la lista de ocupados")
async def po_add(interaction: discord.Interaction, personaje: str):
    datos = cargar_datos()
    personaje = personaje.title() 
    if personaje in datos["ocupados"]:
        await interaction.response.send_message(f"❌ {personaje} ya está ocupado.", ephemeral=True)
    else:
        datos["ocupados"].append(personaje)
        guardar_datos(datos)
        await interaction.response.send_message(f"✅ {personaje} ha sido añadido a los personajes ocupados.")

@bot.tree.command(name="po_del", description="Elimina un personaje de la lista de ocupados")
async def po_del(interaction: discord.Interaction, personaje: str):
    datos = cargar_datos()
    personaje = personaje.title()
    if personaje in datos["ocupados"]:
        datos["ocupados"].remove(personaje)
        guardar_datos(datos)
        await interaction.response.send_message(f"🗑️ {personaje} ha sido liberado.")
    else:
        await interaction.response.send_message(f"⚠️ {personaje} no está en la lista de ocupados.", ephemeral=True)

@bot.tree.command(name="po_list", description="Muestra todos los personajes ocupados")
async def po_list(interaction: discord.Interaction):
    datos = cargar_datos()
    if not datos["ocupados"]:
        await interaction.response.send_message("No hay ningún personaje ocupado todavía.")
    else:
        lista = "\n".join([f"• {p}" for p in datos["ocupados"]])
        await interaction.response.send_message(f"**🎭 Personajes Ocupados:**\n{lista}")

# --- COMANDOS: DESEADOS (LL) ---
@bot.tree.command(name="ll_add", description="Añade un personaje a la lista de deseados")
async def ll_add(interaction: discord.Interaction, personaje: str):
    datos = cargar_datos()
    personaje = personaje.title() 
    if personaje in datos["deseados"]:
        await interaction.response.send_message(f"❌ {personaje} ya está en la lista de deseados.", ephemeral=True)
    elif personaje in datos["ocupados"]:
        await interaction.response.send_message(f"⚠️ {personaje} ya está en uso.", ephemeral=True)
    else:
        datos["deseados"].append(personaje)
        guardar_datos(datos)
        await interaction.response.send_message(f"✨ {personaje} ha sido añadido a la Wishlist.")

@bot.tree.command(name="ll_del", description="Elimina un personaje de la lista de deseados")
async def ll_del(interaction: discord.Interaction, personaje: str):
    datos = cargar_datos()
    personaje = personaje.title()
    if personaje in datos["deseados"]:
        datos["deseados"].remove(personaje)
        guardar_datos(datos)
        await interaction.response.send_message(f"🗑️ {personaje} ya no está en la Wishlist.")
    else:
        await interaction.response.send_message(f"⚠️ {personaje} no estaba en la Wishlist.", ephemeral=True)

@bot.tree.command(name="ll_list", description="Muestra todos los personajes deseados")
async def ll_list(interaction: discord.Interaction):
    datos = cargar_datos()
    if not datos["deseados"]:
        await interaction.response.send_message("La lista de deseados está vacía.")
    else:
        lista = "\n".join([f"⭐ {p}" for p in datos["deseados"]])
        await interaction.response.send_message(f"**✨ Personajes Buscados (Wishlist):**\n{lista}")

# --- COMANDO NUEVO: RASTREADOR MANUAL ---
@bot.tree.command(name="check_actividad", description="[Admin] Muestra los días de inactividad de los usuarios")
@commands.has_permissions(administrator=True) # Solo los admins pueden usarlo
async def check_actividad(interaction: discord.Interaction):
    datos = cargar_datos()
    if "actividad" not in datos or not datos["actividad"]:
        await interaction.response.send_message("Aún no hay registros de actividad.", ephemeral=True)
        return
        
    hoy = datetime.now()
    reporte = []
    
    for user_id_str, fecha_str in datos["actividad"].items():
        ultima_fecha = datetime.fromisoformat(fecha_str)
        dias = (hoy - ultima_fecha).days
        
        if dias > 0:
            reporte.append(f"<@{user_id_str}>: inactivo hace **{dias}** días.")
            
    if not reporte:
        await interaction.response.send_message("✅ Todos los usuarios registrados han estado activos hoy.", ephemeral=True)
    else:
        await interaction.response.send_message("**📊 Reporte de Inactividad:**\n" + "\n".join(reporte), ephemeral=True)

# IMPORTANTE 3: Pon tu Token real aquí
token = os.getenv('TOKEN')
bot.run(token)