import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime

# --- BASE DE DATOS ---
DB_FILE = 'data/personajes.json'

def inicializar_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump({"ocupados": {}, "deseados": {}, "actividad": {}}, f, indent=4)
        print(f"✅ Archivo {DB_FILE} creado con éxito.")

def cargar_datos():
    inicializar_db()
    with open(DB_FILE, 'r') as f:
        try:
            datos = json.load(f)
        except:
            datos = {"ocupados": {}, "deseados": {}, "actividad": {}}
    
    # VALIDACIÓN DINÁMICA: Si algo es una lista y debe ser diccionario, lo arreglamos
    if not isinstance(datos.get("ocupados"), dict):
        datos["ocupados"] = {}
    if not isinstance(datos.get("deseados"), dict):
        datos["deseados"] = {}
    if not isinstance(datos.get("actividad"), dict):
        datos["actividad"] = {}
        
    return datos

def guardar_datos(datos):
    with open(DB_FILE, 'w') as f:
        json.dump(datos, f, indent=4)

# --- CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# --- EVENTOS PRINCIPALES ---
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    inicializar_db() 
    if not revisar_inactivos.is_running():
        revisar_inactivos.start()
        print("Módulo de inactividad automático iniciado.")
    try:
        servidor = discord.Object(id=1495565448601927821) 
        bot.tree.copy_global_to(guild=servidor)
        synced = await bot.tree.sync(guild=servidor)
        print(f"Sincronizados {len(synced)} comandos en el servidor.")
    except Exception as e:
        print(f"Error sincronizando: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    datos = cargar_datos()
    if "actividad" not in datos:
        datos["actividad"] = {}
    datos["actividad"][str(message.author.id)] = datetime.now().isoformat()
    guardar_datos(datos)
    await bot.process_commands(message)

# --- TAREA AUTOMÁTICA (Background Loop) ---
@tasks.loop(hours=24)
async def revisar_inactivos():
    await bot.wait_until_ready()
    datos = cargar_datos()
    if "actividad" not in datos:
        return
    canal_avisos = bot.get_channel(1495579886557860032) 
    if not canal_avisos:
        print("Error: No se encontró el canal de avisos.")
        return
    hoy = datetime.now()
    for user_id_str, fecha_str in list(datos["actividad"].items()):
        ultima_fecha = datetime.fromisoformat(fecha_str)
        diferencia = (hoy - ultima_fecha).days
        if diferencia == 5:
            await canal_avisos.send(f"⚠️ <@{user_id_str}>, llevas **5 días** inactivo. ¡Recuerda participar para mantener tu personaje!")
        elif diferencia >= 7:
            await canal_avisos.send(f"❌ <@{user_id_str}> ha alcanzado los **7 días** de inactividad. Su personaje queda libre.")

# --- COMANDOS: ADMIN ---
@bot.tree.command(name="backup", description="[Admin] Descarga el archivo de base de datos")
@commands.has_permissions(administrator=True)
async def backup(interaction: discord.Interaction):
    if os.path.exists(DB_FILE):
        archivo = discord.File(DB_FILE, filename="respaldo_personajes.json")
        await interaction.response.send_message("📦 Aquí tienes el JSON actual:", file=archivo, ephemeral=True)
    else:
        await interaction.response.send_message("❌ El archivo aún no se ha creado.", ephemeral=True)

@bot.tree.command(name="check_actividad", description="[Admin] Muestra los días de inactividad de los usuarios")
@commands.has_permissions(administrator=True)
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
        reporte.append(f"<@{user_id_str}>: inactivo hace **{dias}** días.")
    if not reporte:
        await interaction.response.send_message("✅ Todos los usuarios registrados han estado activos hoy.", ephemeral=True)
    else:
        await interaction.response.send_message("**📊 Reporte de Inactividad:**\n" + "\n".join(reporte), ephemeral=True)

@bot.tree.command(name="purgar", description="[Admin] Expulsa a los usuarios con 7 o más días de inactividad")
@commands.has_permissions(administrator=True)
async def purga_inactivos(interaction: discord.Interaction):
    datos = cargar_datos()
    hoy = datetime.now()
    expulsados = []
    for user_id, fecha_str in list(datos["actividad"].items()):
        ultima_fecha = datetime.fromisoformat(fecha_str)
        if (hoy - ultima_fecha).days >= 7:
            try:
                usuario_discord = await interaction.guild.fetch_member(int(user_id))
                if usuario_discord:
                    await usuario_discord.kick(reason="Inactividad prolongada (7 o más días)")
                if user_id in datos["ocupados"]:
                    del datos["ocupados"][user_id]
                del datos["actividad"][user_id]
                expulsados.append(user_id)
            except Exception as e:
                print(f"No se pudo expulsar al ID {user_id}: {e}")
    guardar_datos(datos)
    if expulsados:
        await interaction.response.send_message(f"🔨 Se ha expulsado a {len(expulsados)} usuarios inactivos y se han liberado sus personajes.")
    else:
        await interaction.response.send_message("✅ No hay usuarios que cumplan el criterio de expulsión (7 días).")

# --- COMANDOS: OCUPADOS (PO) ---
@bot.tree.command(name="po_add", description="[Admin] Vincula un personaje a un usuario")
@commands.has_permissions(administrator=True)
async def po_add(interaction: discord.Interaction, personaje: str, usuario: discord.Member):
    datos = cargar_datos()
    personaje = personaje.title()
    user_id = str(usuario.id)
    datos["ocupados"][user_id] = personaje
    guardar_datos(datos)
    await interaction.response.send_message(f"✅ **{personaje}** ha sido asignado a {usuario.mention}.")

@bot.tree.command(name="po_del", description="Elimina un personaje de la lista de ocupados")
async def po_del(interaction: discord.Interaction, personaje: str):
    datos = cargar_datos()
    personaje = personaje.title()
    usuario_a_borrar = None
    for uid, pj in datos["ocupados"].items():
        if pj == personaje:
            usuario_a_borrar = uid
            break
    if usuario_a_borrar:
        del datos["ocupados"][usuario_a_borrar]
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
        lista = "\n".join([f"• **{pj}** (Usuario: <@{uid}>)" for uid, pj in datos["ocupados"].items()])
        await interaction.response.send_message(f"**🎭 Personajes Ocupados:**\n{lista}")

# --- COMANDOS: DESEADOS (LL) ---
@bot.tree.command(name="ll_add", description="Añade un personaje y quién lo desea")
async def ll_add(interaction: discord.Interaction, personaje: str, usuario: discord.Member):
    datos = cargar_datos()
    pj = personaje.title()
    if pj in datos["ocupados"].values():
        return await interaction.response.send_message(f"⚠️ {pj} ya está ocupado.", ephemeral=True)
    datos["deseados"][pj] = usuario.display_name
    guardar_datos(datos)
    await interaction.response.send_message(f"✨ **{pj}** añadido a la lista (Deseado por: {usuario.display_name}).")

@bot.tree.command(name="ll_list", description="Muestra la lista de deseados")
async def ll_list(interaction: discord.Interaction):
    datos = cargar_datos()
    if not datos.get("deseados"):
        return await interaction.response.send_message("La lista de deseados está vacía.")
    lineas = [f"• **{pj}** (Deseado por {nombre})" for pj, nombre in datos["deseados"].items()]
    await interaction.response.send_message("**✨ Personajes Buscados:**\n" + "\n".join(lineas))

@bot.tree.command(name="ll_del", description="Elimina un personaje de la lista de deseados")
async def ll_del(interaction: discord.Interaction, personaje: str):
    datos = cargar_datos()
    pj = personaje.title()
    if pj in datos["deseados"]:
        del datos["deseados"][pj]
        guardar_datos(datos)
        await interaction.response.send_message(f"🗑️ {pj} ya no está en la Wishlist.")
    else:
        await interaction.response.send_message(f"⚠️ {pj} no estaba en la Wishlist.", ephemeral=True)

# IMPORTANTE 3: Pon tu Token real aquí
token = os.getenv('TOKEN')
bot.run(token)