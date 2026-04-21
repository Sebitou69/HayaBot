import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime
import random
from database import cargar_datos, guardar_datos

# --- CONFIGURACIÓN DE IDS ---
ID_CANAL_GENERAL = 1495579886557860032  # Reemplaza con el ID de tu canal general
ID_CANAL_AVISOS = 1495579886557860032   # Canal donde el bot avisa de los 5 y 7 días (puede ser el mismo)

ROLES_NIVELES = {
    10: 123456789012345678,   # Nivel 10: Spark
    20: 123456789012345678,  # Nivel 20: Orbit
    30: 123456789012345678,  # Nivel 30: Comet
    40: 123456789012345678,  # Nivel 40: Supernova
    50: 123456789012345678   # Nivel 50: Zenith
}

# Memoria temporal para el cooldown de XP (se reinicia si el bot se reinicia)
cooldown_xp = {}

class Actividad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.revisar_inactivos.start()

    def cog_unload(self):
        self.revisar_inactivos.cancel()

    # --- MOTOR DE XP Y REGISTRO DE ACTIVIDAD ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.content:
            return
        
        user_id = str(message.author.id)
        ahora = datetime.now()
        datos = cargar_datos()
        
        # 1. Registrar actividad (Anti-purga)
        if "actividad" not in datos:
            datos["actividad"] = {}
        datos["actividad"][user_id] = ahora.isoformat()
        
        # 2. Inicializar niveles si el usuario es nuevo
        if "niveles" not in datos:
            datos["niveles"] = {}
        if user_id not in datos["niveles"]:
            datos["niveles"][user_id] = {"xp": 0, "nivel": 1}

        # 3. Gestión de XP con Cooldown de 60s
        ultimo_xp = cooldown_xp.get(user_id)
        if ultimo_xp is None or (ahora - ultimo_xp).total_seconds() > 60:
            longitud = len(message.content)
            
            # Tiers de XP por longitud del mensaje
            if longitud < 20:
                xp_ganada = random.randint(1, 3)
            elif longitud <= 150:
                xp_ganada = random.randint(15, 25)
            else:
                xp_ganada = random.randint(30, 50)
                
            datos["niveles"][user_id]["xp"] += xp_ganada
            cooldown_xp[user_id] = ahora
            
            # 4. Lógica de Level Up (Nerfeada para meta de 2.5 meses)
            xp_actual = datos["niveles"][user_id]["xp"]
            nivel_actual = datos["niveles"][user_id]["nivel"]
            xp_necesaria = nivel_actual * 75 
            
            if xp_actual >= xp_necesaria and nivel_actual < 50:
                datos["niveles"][user_id]["nivel"] += 1
                nuevo_nivel = datos["niveles"][user_id]["nivel"]
                datos["niveles"][user_id]["xp"] -= xp_necesaria 
                
                # Automatización: Anuncio en el canal
                canal_general = self.bot.get_channel(ID_CANAL_GENERAL)
                if canal_general:
                    await canal_general.send(f"✨ ¡Atención! {message.author.mention} ha ascendido al **Nivel {nuevo_nivel}** por su excelente participación.")
                
                # Automatización: Asignación de roles
                if nuevo_nivel in ROLES_NIVELES:
                    id_rol = ROLES_NIVELES[nuevo_nivel]
                    rol = message.guild.get_role(id_rol)
                    if rol:
                        try:
                            await message.author.add_roles(rol)
                            if canal_general:
                                await canal_general.send(f"🎖️ {message.author.name} ha desbloqueado el rango legendario: **{rol.name}**.")
                        except discord.Forbidden:
                            print(f"❌ Error: HayaBot no tiene permisos o jerarquía para dar el rol {rol.name}")
                        except Exception as e:
                            print(f"❌ Error al asignar rol: {e}")

        # Guardamos todos los cambios en el JSON
        guardar_datos(datos)

    # --- TAREA AUTOMÁTICA (Inactividad) ---
    @tasks.loop(hours=24)
    async def revisar_inactivos(self):
        await self.bot.wait_until_ready()
        datos = cargar_datos()
        if "actividad" not in datos:
            return
            
        canal_avisos = self.bot.get_channel(ID_CANAL_AVISOS)
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
                await canal_avisos.send(f"❌ <@{user_id_str}> ha alcanzado los **7 días** de inactividad. Su personaje queda libre y está sujeto a purga.")

    # --- COMANDOS DE ADMINISTRACIÓN ---
    @app_commands.command(name="check_actividad", description="[Admin] Muestra los días de inactividad de los usuarios")
    @app_commands.checks.has_permissions(administrator=True)
    async def check_actividad(self, interaction: discord.Interaction):
        datos = cargar_datos()
        if "actividad" not in datos or not datos["actividad"]:
            return await interaction.response.send_message("Aún no hay registros de actividad.", ephemeral=True)
            
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

    @app_commands.command(name="purgar", description="[Admin] Expulsa a los usuarios con 7 o más días de inactividad")
    @app_commands.checks.has_permissions(administrator=True)
    async def purgar(self, interaction: discord.Interaction):
        datos = cargar_datos()
        hoy = datetime.now()
        expulsados = []
        
        # Necesitamos iterar sobre una copia de los items porque modificaremos el diccionario
        for user_id, fecha_str in list(datos["actividad"].items()):
            ultima_fecha = datetime.fromisoformat(fecha_str)
            if (hoy - ultima_fecha).days >= 7:
                try:
                    usuario_discord = await interaction.guild.fetch_member(int(user_id))
                    if usuario_discord:
                        await usuario_discord.kick(reason="Inactividad prolongada (7 o más días)")
                    
                    # Limpiamos la base de datos
                    if "ocupados" in datos and user_id in datos["ocupados"]:
                        del datos["ocupados"][user_id]
                    if "niveles" in datos and user_id in datos["niveles"]:
                        del datos["niveles"][user_id]
                    del datos["actividad"][user_id]
                    
                    expulsados.append(user_id)
                except Exception as e:
                    print(f"No se pudo expulsar al ID {user_id}: {e}")
                    
        guardar_datos(datos)
        if expulsados:
            await interaction.response.send_message(f"🔨 Se ha expulsado a {len(expulsados)} usuarios inactivos y se han limpiado sus registros.")
        else:
            await interaction.response.send_message("✅ No hay usuarios que cumplan el criterio de expulsión (7 días).")

    # --- COMANDOS PARA USUARIOS ---
    @app_commands.command(name="rank", description="Muestra tu nivel y XP actual")
    async def rank(self, interaction: discord.Interaction):
        datos = cargar_datos()
        user_id = str(interaction.user.id)
        
        if "niveles" in datos and user_id in datos["niveles"]:
            nivel = datos["niveles"][user_id]["nivel"]
            xp = datos["niveles"][user_id]["xp"]
            xp_necesaria = nivel * 75
            
            await interaction.response.send_message(
                f"📊 **{interaction.user.display_name}**, eres **Nivel {nivel}**.\n"
                f"✨ Experiencia actual: **{xp} / {xp_necesaria} XP** para el siguiente nivel.", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Aún no tienes registros de experiencia. ¡Empieza a escribir en los canales!", ephemeral=True)

# Función vital para que main.py lo cargue dinámicamente
async def setup(bot):
    await bot.add_cog(Actividad(bot))