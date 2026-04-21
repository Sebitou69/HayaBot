import discord
from discord import app_commands
from discord.ext import commands
from database import cargar_datos, guardar_datos

class Personajes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- COMANDOS: OCUPADOS (PO) ---

    @app_commands.command(name="po_add", description="[Admin] Vincula un personaje a un usuario")
    @app_commands.checks.has_permissions(administrator=True)
    async def po_add(self, interaction: discord.Interaction, personaje: str, usuario: discord.Member):
        datos = cargar_datos()
        pj_formateado = personaje.title()
        user_id = str(usuario.id)
        
        # Verificar si el personaje ya está ocupado
        for uid, pj in datos["ocupados"].items():
            if pj == pj_formateado:
                return await interaction.response.send_message(
                    f"⚠️ ¡No se pudo procesar! **{pj_formateado}** ya lo tiene <@{uid}>.", 
                    ephemeral=True
                )
                
        # Lógica de wishlist (deseados)
        mencion_interesado = ""
        if pj_formateado in datos.get("deseados", {}):
            nombre_guardado = datos["deseados"][pj_formateado]
            miembro_encontrado = discord.utils.get(interaction.guild.members, display_name=nombre_guardado)
            
            if miembro_encontrado:
                mencion_interesado = f"\n🔔 {miembro_encontrado.mention}, ¡el personaje que esperabas ha sido asignado!"
            else:
                mencion_interesado = f"\n🔔 (Deseado por **{nombre_guardado}**, pero no lo encontré)."
            
            del datos["deseados"][pj_formateado]

        datos["ocupados"][user_id] = pj_formateado
        guardar_datos(datos)
        
        # Cambio de apodo
        try:
            await usuario.edit(nick=pj_formateado)
            status_nick = f"✅ Apodo actualizado a **{pj_formateado}**."
        except discord.Forbidden:
            status_nick = "⚠️ No pude cambiar el apodo (Permisos insuficientes)."
        except Exception as e:
            status_nick = f"⚠️ Error al cambiar apodo: {e}"

        await interaction.response.send_message(
            f"🎭 **{pj_formateado}** asignado a {usuario.mention}.\n{status_nick}{mencion_interesado}"
        )

    @app_commands.command(name="po_del", description="[Admin] Elimina un personaje de la lista de ocupados")
    @app_commands.checks.has_permissions(administrator=True)
    async def po_del(self, interaction: discord.Interaction, personaje: str):
        datos = cargar_datos()
        pj_formateado = personaje.title()
        usuario_a_borrar = None
        
        for uid, pj in datos["ocupados"].items():
            if pj == pj_formateado:
                usuario_a_borrar = uid
                break
                
        if usuario_a_borrar:
            del datos["ocupados"][usuario_a_borrar]
            guardar_datos(datos)
            
            status_nick = ""
            try:
                miembro = await interaction.guild.fetch_member(int(usuario_a_borrar))
                await miembro.edit(nick=None) 
                status_nick = f"\n✅ Se ha restablecido el apodo de {miembro.mention}."
            except Exception:
                status_nick = "\n(Usuario no encontrado o sin permisos para el nick)."
                
            await interaction.response.send_message(f"🗑️ **{pj_formateado}** ha sido liberado.{status_nick}")
        else:
            await interaction.response.send_message(f"⚠️ **{pj_formateado}** no está ocupado.", ephemeral=True)

    @app_commands.command(name="po_list", description="Muestra todos los personajes ocupados")
    async def po_list(self, interaction: discord.Interaction):
        datos = cargar_datos()
        if not datos["ocupados"]:
            await interaction.response.send_message("No hay ningún personaje ocupado todavía.")
        else:
            lista = "\n".join([f"• **{pj}** (Usuario: <@{uid}>)" for uid, pj in datos["ocupados"].items()])
            await interaction.response.send_message(f"**🎭 Personajes Ocupados:**\n{lista}")

    # --- COMANDOS: DESEADOS (LL) ---

    @app_commands.command(name="ll_add", description="Añade un personaje a la lista de deseados")
    async def ll_add(self, interaction: discord.Interaction, personaje: str, usuario: discord.Member):
        datos = cargar_datos()
        pj = personaje.title()
        if pj in datos["ocupados"].values():
            return await interaction.response.send_message(f"⚠️ {pj} ya está ocupado.", ephemeral=True)
        
        datos["deseados"][pj] = usuario.display_name
        guardar_datos(datos)
        await interaction.response.send_message(f"✨ **{pj}** añadido a la Wishlist (Deseado por: {usuario.display_name}).")

    @app_commands.command(name="ll_list", description="Muestra la lista de deseados")
    async def ll_list(self, interaction: discord.Interaction):
        datos = cargar_datos()
        if not datos.get("deseados"):
            return await interaction.response.send_message("La lista de deseados está vacía.")
        
        lineas = [f"• **{pj}** (Deseado por {nombre})" for pj, nombre in datos["deseados"].items()]
        await interaction.response.send_message("**✨ Personajes Buscados:**\n" + "\n".join(lineas))

    @app_commands.command(name="ll_del", description="Elimina un personaje de la lista de deseados")
    async def ll_del(self, interaction: discord.Interaction, personaje: str):
        datos = cargar_datos()
        pj = personaje.title()
        if pj in datos["deseados"]:
            del datos["deseados"][pj]
            guardar_datos(datos)
            await interaction.response.send_message(f"🗑️ {pj} eliminado de la Wishlist.")
        else:
            await interaction.response.send_message(f"⚠️ {pj} no estaba en la lista.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Personajes(bot))

#upd