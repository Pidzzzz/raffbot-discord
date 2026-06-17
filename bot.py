import os
import sys
import io
import asyncio
import zipfile
import re
import shutil

# Configure console output to support unicode/emojis on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load configuration
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Setup Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=["!", "/"], intents=intents, help_command=None)

# Import local modules
from src import storage
from src import ranks
from src import image_generator
from src import pdf_ops
from src import converter
from src import pdf_export
from src import gemini_client
from src.scheduler import scheduler, restore_reminders
from src import welcome_config as wc
from src import chat_xp

# Directory config
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)


async def update_hunter_roles(member: discord.Member, total_entries: int) -> discord.Role | None:
    guild = member.guild
    if not guild.me.guild_permissions.manage_roles:
        return None
        
    is_owner = await bot.is_owner(member)
    current_rank = ranks.get_rank(total_entries, is_owner=is_owner)
    target_role_name = current_rank["title"]
    
    colors_map = {
        "E-Rank Hunter": discord.Color.from_rgb(160, 165, 175),
        "D-Rank Hunter": discord.Color.from_rgb(185, 150, 130),
        "C-Rank Hunter": discord.Color.from_rgb(140, 175, 155),
        "B-Rank Hunter": discord.Color.from_rgb(135, 165, 185),
        "A-Rank Hunter": discord.Color.from_rgb(170, 150, 185),
        "S-Rank Hunter": discord.Color.from_rgb(200, 135, 135),
        "National Level Hunter": discord.Color.from_rgb(195, 165, 120),
        "God Mode": discord.Color.from_rgb(255, 215, 0) # Gold color for God Mode
    }
    
    icons_map = {
        "E-Rank Hunter": "🛡️",
        "D-Rank Hunter": "⚔️",
        "C-Rank Hunter": "🏹",
        "B-Rank Hunter": "🔮",
        "A-Rank Hunter": "⚡",
        "S-Rank Hunter": "🔥",
        "National Level Hunter": "🌌",
        "God Mode": "👑"
    }
    
    all_rank_names = list(colors_map.keys())
    
    target_role = discord.utils.get(guild.roles, name=target_role_name)
    if not target_role:
        try:
            role_icon = icons_map.get(target_role_name)
            kwargs = {
                "name": target_role_name,
                "color": colors_map[target_role_name],
                "hoist": True,
                "reason": "Monarch RPG Rank Role Creation"
            }
            if guild.premium_tier >= 2 and role_icon:
                kwargs["display_icon"] = role_icon
            target_role = await guild.create_role(**kwargs)
        except Exception as e:
            print(f"Failed to create role {target_role_name}: {e}")
            return None
    else:
        try:
            role_icon = icons_map.get(target_role_name)
            if guild.premium_tier >= 2 and role_icon and str(target_role.icon) != role_icon:
                await target_role.edit(display_icon=role_icon)
        except Exception as e:
            print(f"Failed to update role icon for {target_role_name}: {e}")
            
    roles_to_remove = [r for r in member.roles if r.name in all_rank_names and r.name != target_role_name]
    has_role = discord.utils.get(member.roles, name=target_role_name)
    
    if roles_to_remove or not has_role:
        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Hunter Promotion Clean")
            if not has_role:
                await member.add_roles(target_role, reason="Hunter Rank Up Promotion")
            return target_role
        except Exception as e:
            print(f"Failed to update roles for {member.name}: {e}")
            return None
            
    return target_role


async def check_and_promote(guild, user, total_entries: int, channel=None):
    if not guild or not channel:
        return
    try:
        member = guild.get_member(user.id)
        if not member:
            member = await guild.fetch_member(user.id)
            
        if member:
            is_owner = await bot.is_owner(member)
            old_rank = ranks.get_rank(total_entries - 1, is_owner=is_owner) if total_entries > 0 else None
            new_rank = ranks.get_rank(total_entries, is_owner=is_owner)
            
            target_role = await update_hunter_roles(member, total_entries)
            
            if old_rank and old_rank["rank"] != new_rank["rank"] and target_role:
                embed = discord.Embed(
                    title="🎉 HUNTER PROMOTION!",
                    description=f"⚡ {member.mention} telah membangkitkan kekuatan baru dan dipromosikan menjadi **{target_role.name}**!",
                    color=target_role.color
                )
                await channel.send(embed=embed)
    except Exception as e:
        print(f"Error checking/promoting hunter: {e}")


@bot.event
async def on_ready():
    print(f"==================================================")
    print(f"[Raffbot-priv] ONLINE!")
    print(f"Logged in as: {bot.user.name}#{bot.user.discriminator} ({bot.user.id})")
    print(f"Discord.py version: {discord.__version__}")
    print(f"==================================================")
    
    # Start scheduler & restore reminders
    try:
        scheduler.start()
        restore_reminders(bot)
        print("Scheduler started and active reminders restored.")
    except Exception as e:
        print(f"Error starting scheduler: {e}")
        
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands globally.")
        
        # Also copy and sync instantly to each guild the bot is in
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"Instantly synced commands to guild: {guild.name} ({guild.id})")
            except Exception as ge:
                print(f"Could not instantly sync to guild {guild.name}: {ge}")
    except Exception as e:
        print(f"Error syncing slash commands: {e}")


# ==========================================
# WELCOME / GOODBYE SYSTEM
# ==========================================

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    config = wc.get_guild_config(guild.id)
    channel_id = config.get("welcome_channel")

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        try:
            channel = await guild.fetch_channel(channel_id)
        except Exception:
            return

    # Build member count for display
    member_count = guild.member_count or len(guild.members)

    # Create welcome image card
    try:
        avatar_bytes = None
        if member.avatar:
            avatar_bytes = await member.avatar.read()
        elif member.display_avatar:
            avatar_bytes = await member.display_avatar.read()

        card_data = image_generator.generate_welcome_image(
            member_name=member.display_name,
            guild_name=guild.name,
            member_count=member_count,
            avatar_bytes=avatar_bytes
        )
        file = discord.File(io.BytesIO(card_data), filename="welcome_card.png")
    except Exception:
        file = None

    # Build embed
    custom_msg = config.get("welcome_message")
    if custom_msg:
        desc = custom_msg.replace("{user}", member.mention).replace("{name}", member.display_name).replace("{server}", guild.name)
    else:
        desc = f"Selamat datang {member.mention}! Semoga betah di {guild.name} 🎉"

    embed = discord.Embed(
        title=f"👋 Selamat Datang!",
        description=desc,
        color=discord.Color.from_rgb(194, 168, 120)
    )
    embed.set_footer(text=f"Member ke-{member_count} • #ARISE")

    try:
        if file:
            await channel.send(file=file, embed=embed)
        else:
            await channel.send(embed=embed)
    except Exception as e:
        print(f"[welcome] Failed to send welcome: {e}")


@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild
    config = wc.get_guild_config(guild.id)
    channel_id = config.get("goodbye_channel")

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        try:
            channel = await guild.fetch_channel(channel_id)
        except Exception:
            return

    member_count = guild.member_count or len(guild.members)

    try:
        card_data = image_generator.generate_goodbye_image(
            member_name=member.display_name,
            guild_name=guild.name,
            member_count=member_count
        )
        file = discord.File(io.BytesIO(card_data), filename="goodbye_card.png")
    except Exception:
        file = None

    custom_msg = config.get("goodbye_message")
    if custom_msg:
        desc = custom_msg.replace("{user}", member.mention).replace("{name}", member.display_name).replace("{server}", guild.name)
    else:
        desc = f"{member.display_name} telah meninggalkan server. Sampai jumpa!"

    embed = discord.Embed(
        title="👋 Sampai Jumpa!",
        description=desc,
        color=discord.Color.from_rgb(142, 142, 147)
    )
    embed.set_footer(text=f"Tersisa {member_count} anggota • #UNTIL_NEXT_TIME")

    try:
        if file:
            await channel.send(file=file, embed=embed)
        else:
            await channel.send(embed=embed)
    except Exception as e:
        print(f"[goodbye] Failed to send goodbye: {e}")


# ==========================================
# WELCOME CONFIGURATION COMMANDS
# ==========================================

class WelcomeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, config_type: str):
        self.config_type = config_type
        super().__init__(
            placeholder="Pilih channel untuk welcome/goodbye...",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        guild_id = interaction.guild_id

        if self.config_type == "welcome":
            wc.set_welcome_channel(guild_id, channel.id)
        else:
            wc.set_goodbye_channel(guild_id, channel.id)

        label = "Welcome" if self.config_type == "welcome" else "Goodbye"
        sel = self.view
        for child in sel.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"✅ **{label} channel** berhasil diatur ke {channel.mention}!",
            view=sel
        )


class WelcomeConfigSelectView(discord.ui.View):
    def __init__(self, config_type: str):
        super().__init__(timeout=60.0)
        self.add_item(WelcomeChannelSelect(config_type))


@bot.hybrid_command(name="welcome", description="Atur channel dan pesan welcome")
async def welcome_cmd(ctx, action: str = None, *, value: str = None):
    if not ctx.guild:
        await ctx.send("❌ Perintah ini hanya bisa digunakan di dalam server.")
        return

    if not action:
        # Show current config
        config = wc.get_guild_config(ctx.guild.id)
        wc_id = config.get("welcome_channel")
        wc_ch = f"<#{wc_id}>" if wc_id else "❌ Belum diatur"
        embed = discord.Embed(
            title="👋 Welcome System Config",
            color=discord.Color.gold()
        )
        embed.add_field(name="Channel Welcome", value=wc_ch, inline=False)
        if config.get("welcome_message"):
            embed.add_field(name="Pesan Kustom", value=config["welcome_message"], inline=False)
        embed.set_footer(text="Gunakan: /welcome channel | /welcome message <teks> | /welcome reset")
        await ctx.send(embed=embed)
        return

    action = action.lower()

    if action == "channel":
        view = WelcomeConfigSelectView("welcome")
        await ctx.send("📌 **Pilih channel** untuk welcome message:", view=view)

    elif action == "message":
        if not value:
            await ctx.send("❌ Masukkan pesan kustom. Gunakan `{user}` untuk mention, `{name}` untuk nama, `{server}` untuk nama server.")
            return
        wc.set_welcome_message(ctx.guild.id, value)
        await ctx.send(f"✅ **Pesan welcome kustom** berhasil diatur!\n```{value}```")

    elif action == "reset":
        wc.reset_welcome_config(ctx.guild.id)
        await ctx.send("✅ **Konfigurasi welcome** berhasil direset!")

    else:
        await ctx.send("❌ Aksi tidak valid. Gunakan: `channel`, `message <teks>`, atau `reset`")


@bot.hybrid_command(name="goodbye", description="Atur channel dan pesan goodbye")
async def goodbye_cmd(ctx, action: str = None, *, value: str = None):
    if not ctx.guild:
        await ctx.send("❌ Perintah ini hanya bisa digunakan di dalam server.")
        return

    if not action:
        config = wc.get_guild_config(ctx.guild.id)
        gc_id = config.get("goodbye_channel")
        gc_ch = f"<#{gc_id}>" if gc_id else "❌ Belum diatur"
        embed = discord.Embed(
            title="👋 Goodbye System Config",
            color=discord.Color.from_rgb(142, 142, 147)
        )
        embed.add_field(name="Channel Goodbye", value=gc_ch, inline=False)
        if config.get("goodbye_message"):
            embed.add_field(name="Pesan Kustom", value=config["goodbye_message"], inline=False)
        embed.set_footer(text="Gunakan: /goodbye channel | /goodbye message <teks>")
        await ctx.send(embed=embed)
        return

    action = action.lower()

    if action == "channel":
        view = WelcomeConfigSelectView("goodbye")
        await ctx.send("📌 **Pilih channel** untuk goodbye message:", view=view)

    elif action == "message":
        if not value:
            await ctx.send("❌ Masukkan pesan kustom. Gunakan `{user}` untuk mention, `{name}` untuk nama, `{server}` untuk nama server.")
            return
        wc.set_goodbye_message(ctx.guild.id, value)
        await ctx.send(f"✅ **Pesan goodbye kustom** berhasil diatur!\n```{value}```")

    else:
        await ctx.send("❌ Aksi tidak valid. Gunakan: `channel` atau `message <teks>`")


# ==========================================
# JOURNAL & RPG SYSTEM VIEWS & COMMANDS
# ==========================================

async def _send_main_hud(channel, user):
    """Kirim ulang HUD utama ke channel (digunakan oleh tombol Kembali)."""
    all_entries = storage.get_all_entries()
    total = len(all_entries)
    stats = storage.get_stats()
    is_owner = await bot.is_owner(user)
    rank = ranks.get_rank(total, is_owner=is_owner)
    card_data = image_generator.generate_welcome_card(
        hunter_name=user.name,
        rank_letter=rank["rank"],
        rank_title=rank["title"],
        total_entries=total,
        active_days=stats["days"]
    )
    file = discord.File(io.BytesIO(card_data), filename="welcome_hud.png")
    view = JournalMenuView(user.id)
    new_msg = await channel.send("=== **SOLO LEVELING JOURNAL SYSTEM** ===", file=file, view=view)
    storage.set_last_hud_message(channel.id, new_msg.id)
    return new_msg


class BackToMenuView(discord.ui.View):
    """View tombol Kembali yang dilampirkan pada setiap hasil menu."""
    def __init__(self, user_id: int):
        super().__init__(timeout=300.0)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bukan menu Anda.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🏠 Kembali ke Menu", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Hapus pesan ephemeral hasil (bersihkan tampilan)
        await interaction.response.edit_message(content="-# ✅ Kembali ke menu...", attachments=[], embed=None, view=None)
        # Kirim ulang HUD utama ke channel
        await _send_main_hud(interaction.channel, interaction.user)


class JournalMenuView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300.0)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Tombol AI Scan Nutrisi boleh digunakan siapa saja
        if interaction.data.get("custom_id") == "ai_scan_nutrisi_btn":
            return True
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Hanya pemilik menu ini yang bisa menggunakannya.", ephemeral=True
            )
            return False
        return True

    async def _dismiss_hud(self, interaction: discord.Interaction):
        """Hapus pesan HUD (mirip Telegram: menu hilang setelah diklik)."""
        try:
            await interaction.message.delete()
        except Exception:
            pass

    @discord.ui.button(label="⚔️ Status", style=discord.ButtonStyle.blurple)
    async def status_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self._dismiss_hud(interaction)

        all_entries = storage.get_all_entries()
        total = len(all_entries)
        stats = storage.get_stats()
        is_owner = await bot.is_owner(interaction.user)
        rank = ranks.get_rank(total, is_owner=is_owner)
        xp = ranks.get_xp_progress(total, is_owner=is_owner)
        streak = ranks.get_streak_info(all_entries)

        card_data = image_generator.generate_status_card(
            hunter_name=interaction.user.name,
            rank_letter=rank["rank"],
            rank_title=rank["title"],
            xp_percent=xp["percent"],
            streak_days=streak["streak"],
            streak_title=streak["milestone"]["title"] if streak["milestone"] else "",
            total_entries=total,
            active_days=stats["days"]
        )
        file = discord.File(io.BytesIO(card_data), filename="status_window.png")
        await interaction.followup.send(file=file, view=BackToMenuView(interaction.user.id), ephemeral=True)

    @discord.ui.button(label="📅 Daily Agenda", style=discord.ButtonStyle.green)
    async def agenda_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self._dismiss_hud(interaction)

        today_str = datetime.now().strftime("%Y-%m-%d")
        cleared_quests = storage.get_today()
        import src.scheduler as sc
        active_quests = []
        try:
            active_quests = sc.get_reminders()
        except Exception:
            pass

        card_data = image_generator.generate_agenda_card(
            date_str=today_str,
            active_quests=active_quests,
            cleared_quests=cleared_quests
        )
        file = discord.File(io.BytesIO(card_data), filename="agenda_board.png")
        await interaction.followup.send(file=file, view=BackToMenuView(interaction.user.id), ephemeral=True)

    @discord.ui.button(label="📊 Stats", style=discord.ButtonStyle.secondary)
    async def stats_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self._dismiss_hud(interaction)

        stats = storage.get_stats()
        card_data = image_generator.generate_stats_card(
            total_entries=stats["total"],
            active_days=stats["days"],
            first_date=stats["first_date"],
            last_date=stats["last_date"]
        )
        file = discord.File(io.BytesIO(card_data), filename="system_stats.png")
        await interaction.followup.send(file=file, view=BackToMenuView(interaction.user.id), ephemeral=True)

    @discord.ui.button(label="📄 Export PDF", style=discord.ButtonStyle.primary)
    async def export_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self._dismiss_hud(interaction)

        pdf_path = os.path.join(TEMP_DIR, f"journal_export_{interaction.user.id}.pdf")
        pdf_export.generate_pdf(output_path=pdf_path)

        if os.path.exists(pdf_path):
            file = discord.File(pdf_path, filename="Raffbot_Journal_Report.pdf")
            await interaction.followup.send(
                "Berikut adalah arsip dokumen log harian Anda:",
                file=file,
                view=BackToMenuView(interaction.user.id),
                ephemeral=True
            )
            try:
                os.remove(pdf_path)
            except Exception:
                pass
        else:
            await interaction.followup.send(
                "❌ Gagal mengekspor jurnal.",
                view=BackToMenuView(interaction.user.id),
                ephemeral=True
            )

    @discord.ui.button(label="🛡️ Hunter Ranks", style=discord.ButtonStyle.secondary)
    async def ranks_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self._dismiss_hud(interaction)

        embed = discord.Embed(
            title="🛡️ Hunter Ranks & Roles System",
            description="Kumpulkan Quest Logs harian Anda untuk naik level dan dapatkan role eksklusif di server ini!",
            color=discord.Color.gold()
        )
        embed.add_field(name="⬜ E-Rank Hunter",        value="Persyaratan: `0+ Quest` (Rank Pemula)", inline=True)
        embed.add_field(name="🟫 D-Rank Hunter",        value="Persyaratan: `10+ Quest` (Rank Menengah-Bawah)", inline=True)
        embed.add_field(name="🟩 C-Rank Hunter",        value="Persyaratan: `30+ Quest` (Rank Menengah)", inline=True)
        embed.add_field(name="🟦 B-Rank Hunter",        value="Persyaratan: `75+ Quest` (Rank Tinggi)", inline=True)
        embed.add_field(name="🟪 A-Rank Hunter",        value="Persyaratan: `150+ Quest` (Rank Sangat Tinggi)", inline=True)
        embed.add_field(name="🟥 S-Rank Hunter",        value="Persyaratan: `300+ Quest` (Rank Monarch)", inline=True)
        embed.add_field(name="⬛ National Level Hunter", value="Persyaratan: `500+ Quest` (Rank Terkuat)", inline=False)
        embed.add_field(name="👑 God Mode",             value="Persyaratan: `1000+ Quest` _(Owner Only)_", inline=False)
        embed.set_footer(text="💡 Tip: Pastikan role 'Raffbot-priv' diposisikan paling atas di Server Settings → Roles agar sinkronisasi lancar!")
        await interaction.followup.send(embed=embed, view=BackToMenuView(interaction.user.id), ephemeral=True)

    @discord.ui.button(label="🍳 AI Scan Nutrisi", style=discord.ButtonStyle.primary, custom_id="ai_scan_nutrisi_btn")
    async def ai_scan_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Tombol ini bisa digunakan siapa saja — tidak hapus HUD milik orang lain
        await interaction.response.send_message(
            "📸 **Silakan upload/kirim foto makanan Anda langsung ke chat.**\n"
            "Setelah gambar terkirim, tombol **🍳 Analisis Gizi (AI)** akan otomatis muncul "
            "di bawah gambar tersebut untuk melihat analisis makronutrisinya!",
            ephemeral=True
        )


class LogModal(discord.ui.Modal, title="Quest Log Registry"):
    log_text = discord.ui.TextInput(
        label="Rincian Kegiatan (Quest Info)",
        style=discord.TextStyle.paragraph,
        placeholder="Tuliskan aktivitas atau tugas yang diselesaikan...",
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        entry = storage.add_entry(self.log_text.value)
        total = storage.get_entry_count()
        is_owner = await bot.is_owner(interaction.user)
        xp = ranks.get_xp_progress(total, is_owner=is_owner)
        
        embed = discord.Embed(
            title="🛡️ Quest Log Cleared!",
            description=f"Kegiatan berhasil dicatat sebagai Quest #{entry['id']}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Aktivitas", value=self.log_text.value, inline=False)
        embed.add_field(name="Hunter XP", value=f"Progress level selanjutnya: `{ranks.format_progress_bar(xp['percent'])}` ({xp['percent']}%)", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await check_and_promote(interaction.guild, interaction.user, total, interaction.channel)


# Command Helpers
@bot.hybrid_command(name="start", description="Menampilkan Menu Utama Solo Leveling Journal")
async def start(ctx):
    # Defer immediately so Discord doesn't time out (3s limit for slash commands)
    # ephemeral=False so the HUD is visible to everyone
    if ctx.interaction:
        await ctx.interaction.response.defer()

    # Collect all messages to delete FIRST before sending new HUD
    to_delete = []
    try:
        async for msg in ctx.channel.history(limit=100):
            # Collect old bot HUD messages detected by content or attachment filename
            if msg.author == bot.user:
                if (msg.content.startswith("=== **SOLO LEVELING JOURNAL SYSTEM** ===") or
                    (msg.attachments and any(
                        a.filename == "welcome_hud.png" for a in msg.attachments
                    ))):
                    to_delete.append(msg)
            # Collect user's !start / /start trigger text messages
            elif msg.author == ctx.author and msg.content.strip().lower() in ("!start", "/start"):
                to_delete.append(msg)
    except Exception as e:
        print(f"[start] Error scanning channel history: {e}")

    # Bulk delete all old messages atomically before sending new HUD
    if to_delete:
        try:
            if (ctx.guild and
                ctx.channel.permissions_for(ctx.guild.me).manage_messages and
                len(to_delete) > 1):
                await ctx.channel.delete_messages(to_delete)
            else:
                await asyncio.gather(*[m.delete() for m in to_delete], return_exceptions=True)
        except Exception as e:
            print(f"[start] Bulk delete failed, trying one by one: {e}")
            for m in to_delete:
                try:
                    await m.delete()
                except Exception:
                    pass

    # Build and send the new HUD
    all_entries = storage.get_all_entries()
    total = len(all_entries)
    stats = storage.get_stats()
    is_owner = await bot.is_owner(ctx.author)
    rank = ranks.get_rank(total, is_owner=is_owner)

    card_data = image_generator.generate_welcome_card(
        hunter_name=ctx.author.name,
        rank_letter=rank["rank"],
        rank_title=rank["title"],
        total_entries=total,
        active_days=stats["days"]
    )

    file = discord.File(io.BytesIO(card_data), filename="welcome_hud.png")
    view = JournalMenuView(ctx.author.id)

    if ctx.interaction:
        # Use followup after defer for slash commands
        new_msg = await ctx.interaction.followup.send(
            "=== **SOLO LEVELING JOURNAL SYSTEM** ===", file=file, view=view
        )
    else:
        # Prefix command (!start) — send normally
        new_msg = await ctx.send("=== **SOLO LEVELING JOURNAL SYSTEM** ===", file=file, view=view)

    storage.set_last_hud_message(ctx.channel.id, new_msg.id)

    if ctx.guild:
        asyncio.create_task(update_hunter_roles(ctx.author, total))


@bot.hybrid_command(name="log", description="Mencatat kegiatan harian Anda")
async def log(ctx, *, kegiatan: str = None):
    if kegiatan:
        entry = storage.add_entry(kegiatan)
        total = storage.get_entry_count()
        is_owner = await bot.is_owner(ctx.author)
        xp = ranks.get_xp_progress(total, is_owner=is_owner)
        
        embed = discord.Embed(
            title="🛡️ Quest Log Cleared!",
            description=f"Berhasil dicatat sebagai Quest #{entry['id']}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Aktivitas", value=kegiatan, inline=False)
        embed.add_field(name="Hunter XP", value=f"Level Progress: `{ranks.format_progress_bar(xp['percent'])}` ({xp['percent']}%)", inline=False)
        await ctx.send(embed=embed)
        await check_and_promote(ctx.guild, ctx.author, total, ctx.channel)
    else:
        # Show modal if run as slash command
        if ctx.interaction:
            await ctx.interaction.response.send_modal(LogModal())
        else:
            await ctx.send("Format salah! Gunakan: `!log <rincian kegiatan>`")


@bot.hybrid_command(name="rank", description="Melihat Status Window Hunter")
async def rank(ctx):
    all_entries = storage.get_all_entries()
    total = len(all_entries)
    stats = storage.get_stats()
    is_owner = await bot.is_owner(ctx.author)
    rank = ranks.get_rank(total, is_owner=is_owner)
    xp = ranks.get_xp_progress(total, is_owner=is_owner)
    streak = ranks.get_streak_info(all_entries)
    
    card_data = image_generator.generate_status_card(
        hunter_name=ctx.author.name,
        rank_letter=rank["rank"],
        rank_title=rank["title"],
        xp_percent=xp["percent"],
        streak_days=streak["streak"],
        streak_title=streak["milestone"]["title"] if streak["milestone"] else "",
        total_entries=total,
        active_days=stats["days"]
    )
    
    file = discord.File(io.BytesIO(card_data), filename="status_window.png")
    await ctx.send(file=file)
    
    if ctx.guild:
        asyncio.create_task(update_hunter_roles(ctx.author, total))


@bot.hybrid_command(name="agenda", description="Melihat papan Quest Board Hari Ini")
async def agenda(ctx):
    today_str = datetime.now().strftime("%Y-%m-%d")
    cleared_quests = storage.get_today()
    active_quests = [] # Placeholder (reminders list)
    
    card_data = image_generator.generate_agenda_card(
        date_str=today_str,
        active_quests=active_quests,
        cleared_quests=cleared_quests
    )
    
    file = discord.File(io.BytesIO(card_data), filename="agenda_board.png")
    await ctx.send(file=file)


@bot.hybrid_command(name="today", description="Melihat catatan jurnal hari ini")
async def today(ctx):
    entries = storage.get_today()
    if not entries:
        await ctx.send("📭 Belum ada kegiatan dicatat hari ini. Tuliskan dengan `!log <kegiatan>`.")
        return
        
    embed = discord.Embed(title="📅 Quest Logs - Hari Ini", color=discord.Color.blue())
    for e in entries:
        embed.add_field(name=f"Quest #{e['id']} ({e['time'][:5]})", value=e["text"], inline=False)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="yesterday", description="Melihat catatan jurnal kemarin")
async def yesterday(ctx):
    entries = storage.get_yesterday()
    if not entries:
        await ctx.send("📭 Tidak ada catatan kegiatan kemarin.")
        return
        
    embed = discord.Embed(title="📅 Quest Logs - Kemarin", color=discord.Color.dark_grey())
    for e in entries:
        embed.add_field(name=f"Quest #{e['id']} ({e['time'][:5]})", value=e["text"], inline=False)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="del", description="Menghapus kegiatan berdasarkan ID")
async def delete_log(ctx, id: int):
    if storage.delete_entry(id):
        await ctx.send(f"✅ Quest Log #{id} berhasil dihapus.")
    else:
        await ctx.send(f"❌ Quest Log #{id} tidak ditemukan.")


@delete_log.autocomplete('id')
async def delete_log_autocomplete(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[int]]:
    entries = storage.get_all_entries()
    choices = []
    for e in reversed(entries):
        label = f"#{e['id']} [{e['date']}] {e['text']}"
        if len(label) > 100:
            label = label[:97] + "..."
        if current.lower() in str(e['id']) or current.lower() in e['text'].lower():
            choices.append(discord.app_commands.Choice(name=label, value=e['id']))
        if len(choices) >= 25:
            break
    return choices


@bot.hybrid_command(name="clear", description="Menghapus log hari ini secara interaktif")
async def clear(ctx):
    entries = storage.get_today()
    if not entries:
        await ctx.send("📭 Tidak ada catatan kegiatan hari ini.")
        return
        
    embed = discord.Embed(
        title="🗑️ Hapus Log Hari Ini",
        description="Pilih quest log dari dropdown di bawah untuk dihapus, atau klik tombol untuk menghapus semua.",
        color=discord.Color.red()
    )
    for e in entries:
        embed.add_field(name=f"Quest #{e['id']} ({e['time'][:5]})", value=e["text"], inline=False)
        
    view = ClearLogsView(ctx.author.id, entries)
    await ctx.send(embed=embed, view=view)


@bot.hybrid_command(name="date", description="Melihat catatan jurnal tanggal tertentu (YYYY-MM-DD)")
async def date_cmd(ctx, tanggal: str):
    entries = storage.get_by_date(tanggal)
    if not entries:
        await ctx.send(f"📭 Tidak ada catatan kegiatan pada tanggal {tanggal}.")
        return
    
    embed = discord.Embed(title=f"📅 Quest Logs - {tanggal}", color=discord.Color.blue())
    for e in entries:
        embed.add_field(name=f"Quest #{e['id']} ({e['time'][:5]})", value=e["text"], inline=False)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="search", description="Mencari catatan jurnal berdasarkan kata kunci")
async def search_cmd(ctx, keyword: str):
    results = storage.search(keyword)
    if not results:
        await ctx.send(f"📭 Tidak ditemukan catatan dengan kata kunci: `{keyword}`.")
        return
        
    embed = discord.Embed(
        title=f"🔍 Hasil Pencarian: {keyword}", 
        description=f"Ditemukan {len(results)} catatan:",
        color=discord.Color.gold()
    )
    for e in results[:25]:
        embed.add_field(name=f"Quest #{e['id']} ({e['date']} {e['time'][:5]})", value=e["text"], inline=False)
    
    if len(results) > 25:
        embed.set_footer(text=f"...dan {len(results) - 25} catatan lainnya.")
    await ctx.send(embed=embed)


@bot.hybrid_command(name="all", description="Melihat ringkasan arsip semua tanggal")
async def all_cmd(ctx):
    dates = storage.get_all_dates()
    if not dates:
        await ctx.send("📭 Belum ada catatan jurnal.")
        return
        
    total = storage.get_entry_count()
    embed = discord.Embed(
        title=f"🗂️ Arsip Harian ({total} Quest dicatatkan)",
        description="Daftar tanggal dan jumlah catatan harian:",
        color=discord.Color.purple()
    )
    
    lines = []
    for d, count in dates[:25]:
        lines.append(f"📅 **{d}** — `{count}` Quest")
    
    embed.description = "\n".join(lines)
    if len(dates) > 25:
        embed.set_footer(text=f"...dan {len(dates) - 25} tanggal lainnya.")
    await ctx.send(embed=embed)


@bot.hybrid_command(name="stats", description="Melihat Statistik Hunter lengkap")
async def stats_cmd(ctx):
    if ctx.interaction:
        await ctx.interaction.response.defer()
    
    stats = storage.get_stats()
    card_data = image_generator.generate_stats_card(
        total_entries=stats["total"],
        active_days=stats["days"],
        first_date=stats["first_date"],
        last_date=stats["last_date"]
    )
    
    file = discord.File(io.BytesIO(card_data), filename="system_stats.png")
    if ctx.interaction:
        await ctx.interaction.followup.send(file=file)
    else:
        await ctx.send(file=file)


@bot.hybrid_command(name="remind", description="Mengatur reminder harian (Format waktu: HH:MM)")
async def remind(ctx, waktu: str, *, pesan: str):
    match = re.match(r"^(\d{1,2}):(\d{2})$", waktu)
    if not match:
        await ctx.send("❌ Format waktu salah. Gunakan `HH:MM` (contoh: `09:00` atau `21:30`).")
        return
        
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await ctx.send("❌ Jam harus antara 00-23 dan menit antara 00-59.")
        return
        
    now = datetime.now()
    remind_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if remind_at <= now:
        remind_at += timedelta(days=1)
        
    import src.scheduler as sc
    entry = sc.add_reminder(
        bot=bot,
        target_id=ctx.author.id,
        text=pesan,
        remind_at=remind_at,
        repeat="daily"
    )
    await ctx.send(f"⏰ **Reminder Harian Diatur!**\nSetiap hari pada pukul `{waktu}`: *{pesan}* (Reminder #{entry['id']})")


@bot.hybrid_command(name="remindat", description="Mengatur reminder sekali (Tanggal: YYYY-MM-DD, Waktu: HH:MM)")
async def remindat(ctx, tanggal: str, waktu: str, *, pesan: str):
    try:
        remind_at = datetime.strptime(f"{tanggal} {waktu}", "%Y-%m-%d %H:%M")
    except ValueError:
        await ctx.send("❌ Format salah. Gunakan tanggal `YYYY-MM-DD` dan waktu `HH:MM` (contoh: `2026-06-18 14:30`).")
        return
        
    if remind_at <= datetime.now():
        await ctx.send("❌ Waktu reminder harus di masa depan.")
        return
        
    import src.scheduler as sc
    entry = sc.add_reminder(
        bot=bot,
        target_id=ctx.author.id,
        text=pesan,
        remind_at=remind_at,
        repeat=None
    )
    await ctx.send(f"⏰ **Reminder Diatur!**\nPada `{tanggal} {waktu}`: *{pesan}* (Reminder #{entry['id']})")


@bot.hybrid_command(name="reminders", description="Melihat daftar reminder aktif Anda")
async def reminders_cmd(ctx):
    import src.scheduler as sc
    reminders = sc.get_reminders(ctx.author.id)
    if not reminders:
        await ctx.send("⏰ Anda tidak memiliki reminder aktif.")
        return
        
    embed = discord.Embed(title="⏰ Daftar Reminder Aktif", color=discord.Color.blue())
    for r in reminders:
        repeat_info = " (Harian)" if r["repeat"] == "daily" else ""
        dt = datetime.fromisoformat(r["remind_at"]).strftime("%Y-%m-%d %H:%M")
        embed.add_field(
            name=f"Reminder #{r['id']} — {dt}{repeat_info}",
            value=r["text"],
            inline=False
        )
    embed.set_footer(text="Gunakan /unremind <id> untuk menghapus reminder.")
    await ctx.send(embed=embed)


@bot.hybrid_command(name="unremind", description="Menghapus reminder berdasarkan ID")
async def unremind(ctx, id: int):
    import src.scheduler as sc
    if sc.remove_reminder(id):
        await ctx.send(f"✅ Reminder #{id} berhasil dihapus.")
    else:
        await ctx.send(f"❌ Reminder #{id} tidak ditemukan atau tidak aktif.")


@unremind.autocomplete('id')
async def unremind_autocomplete(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[int]]:
    import src.scheduler as sc
    reminders = sc.get_reminders(interaction.user.id)
    choices = []
    for r in reminders:
        repeat_info = " (Harian)" if r["repeat"] == "daily" else ""
        dt = datetime.fromisoformat(r["remind_at"]).strftime("%m-%d %H:%M")
        label = f"#{r['id']} [{dt}]{repeat_info} {r['text']}"
        if len(label) > 100:
            label = label[:97] + "..."
        if current.lower() in str(r['id']) or current.lower() in r['text'].lower():
            choices.append(discord.app_commands.Choice(name=label, value=r['id']))
        if len(choices) >= 25:
            break
    return choices


@bot.command(name="restart")
@commands.is_owner()
async def restart_bot(ctx):
    await ctx.send("🔄 **Memulai ulang bot... Arise!**")
    await asyncio.sleep(1)
    import subprocess, sys
    cwd = os.path.dirname(os.path.abspath(__file__))
    subprocess.Popen([sys.executable, "bot.py"], cwd=cwd)
    os._exit(0)




@bot.hybrid_command(name="projects", description="Melihat proyek/repository GitHub Anda")
async def projects(ctx):
    if ctx.interaction:
        await ctx.interaction.response.defer()
        
    import httpx
    url = "https://api.github.com/users/Pidzzzz/repos"
    headers = {"User-Agent": "Raffbot-priv"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
        if response.status_code != 200:
            msg = "❌ Gagal mengambil data proyek dari GitHub."
            if ctx.interaction:
                await ctx.interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        repos = response.json()
        if not repos:
            msg = "📭 Tidak ada proyek/repository publik ditemukan."
            if ctx.interaction:
                await ctx.interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        embed = discord.Embed(
            title="🐙 GitHub Repositories",
            description="Daftar proyek publik milik **Pidzzzz** di GitHub:",
            color=discord.Color.dark_grey()
        )
        embed.set_thumbnail(url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")
        
        # Limit to 10 repos to avoid hitting embed limits
        for repo in repos[:10]:
            desc = repo["description"] or "Tidak ada deskripsi"
            lang = repo["language"] or "Other"
            stars = repo["stargazers_count"]
            repo_url = repo["html_url"]
            
            embed.add_field(
                name=f"📁 {repo['name']} ({lang})",
                value=f"{desc}\n⭐ Stars: `{stars}` | 🔗 [Tautan Repositori]({repo_url})",
                inline=False
            )
            
        if len(repos) > 10:
            embed.set_footer(text=f"...dan {len(repos) - 10} repositori lainnya.")
            
        if ctx.interaction:
            await ctx.interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
            
    except Exception as e:
        msg = f"❌ Error: {e}"
        if ctx.interaction:
            await ctx.interaction.followup.send(msg)
        else:
            await ctx.send(msg)


# ==========================================
# INTERACTIVE PDF TOOL COMPONENTS & VIEWS
# ==========================================

class PDFPasswordModal(discord.ui.Modal):
    def __init__(self, action: str, file_path: str):
        super().__init__(title="PDF Security Tool")
        self.action = action  # 'lock' or 'unlock'
        self.file_path = file_path
        
        self.pw_input = discord.ui.TextInput(
            label="Masukkan Password PDF",
            style=discord.TextStyle.short,
            placeholder="Ketik password di sini...",
            required=True,
            max_length=50
        )
        self.add_item(self.pw_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        out_name = "secured.pdf" if self.action == "lock" else "unlocked.pdf"
        out_path = os.path.join(TEMP_DIR, f"{interaction.user.id}_{out_name}")
        
        if self.action == "lock":
            res = await pdf_ops.encrypt_pdf(self.file_path, out_path, self.pw_input.value)
        else:
            res = await pdf_ops.decrypt_pdf(self.file_path, out_path, self.pw_input.value)
            
        if res and os.path.exists(out_path):
            file = discord.File(out_path, filename=out_name)
            await interaction.followup.send(content=f"🔒 PDF Berhasil di-{self.action}!", file=file, ephemeral=True)
            try:
                os.remove(out_path)
            except Exception:
                pass
        else:
            await interaction.followup.send("❌ Tindakan gagal. Pastikan password benar.", ephemeral=True)


class WatermarkModal(discord.ui.Modal):
    def __init__(self, file_path: str):
        super().__init__(title="Watermark PDF")
        self.file_path = file_path
        
        self.wm_text = discord.ui.TextInput(
            label="Teks Watermark",
            style=discord.TextStyle.short,
            placeholder="DRAFT / CONFIDENTIAL / MILIK RAFFY...",
            required=True,
            max_length=50
        )
        self.add_item(self.wm_text)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        out_path = os.path.join(TEMP_DIR, f"{interaction.user.id}_watermarked.pdf")
        res = await pdf_ops.add_watermark(self.file_path, out_path, self.wm_text.value)
        
        if res and os.path.exists(out_path):
            file = discord.File(out_path, filename="watermarked.pdf")
            await interaction.followup.send(content="🏷️ Watermark berhasil ditambahkan!", file=file, ephemeral=True)
            try:
                os.remove(out_path)
            except Exception:
                pass
        else:
            await interaction.followup.send("❌ Gagal menambahkan watermark.", ephemeral=True)


class PDFSplitModal(discord.ui.Modal):
    def __init__(self, file_path: str):
        super().__init__(title="Split PDF")
        self.file_path = file_path
        
        self.pages_input = discord.ui.TextInput(
            label="Jumlah halaman per file",
            style=discord.TextStyle.short,
            placeholder="Ketik angka (contoh: 1)...",
            default="1",
            required=True,
            max_length=3
        )
        self.add_item(self.pages_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            pages = int(self.pages_input.value)
        except ValueError:
            await interaction.followup.send("❌ Masukkan angka yang valid.", ephemeral=True)
            return
            
        split_dir = os.path.join(TEMP_DIR, f"split_{interaction.user.id}")
        os.makedirs(split_dir, exist_ok=True)
        
        output_paths = await pdf_ops.split_pdf(self.file_path, split_dir, pages_per_file=pages)
        
        if output_paths:
            # Zip all parts if there are multiple
            zip_path = os.path.join(TEMP_DIR, f"split_results_{interaction.user.id}.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for file in output_paths:
                    zipf.write(file, arcname=os.path.basename(file))
                    
            file = discord.File(zip_path, filename="split_pdf_parts.zip")
            await interaction.followup.send(content="✂️ PDF berhasil dipisahkan!", file=file, ephemeral=True)
            
            # Clean split dir and zip
            shutil.rmtree(split_dir, ignore_errors=True)
            try:
                os.remove(zip_path)
            except Exception:
                pass
        else:
            await interaction.followup.send("❌ Gagal melakukan split PDF.", ephemeral=True)


class PDFToolsView(discord.ui.View):
    def __init__(self, file_path: str, user_id: int):
        super().__init__(timeout=300.0)
        self.file_path = file_path
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Hanya pengunggah file yang bisa memicu aksi ini.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🗜️ Compress", style=discord.ButtonStyle.blurple)
    async def compress_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        out_path = os.path.join(TEMP_DIR, f"{interaction.user.id}_compressed.pdf")
        res = await pdf_ops.compress_pdf(self.file_path, out_path)
        if res and os.path.exists(out_path):
            file = discord.File(out_path, filename="compressed.pdf")
            await interaction.followup.send("🗜️ PDF berhasil dikompresi:", file=file, ephemeral=True)
            try:
                os.remove(out_path)
            except Exception:
                pass
        else:
            await interaction.followup.send("❌ Gagal mengompresi PDF.", ephemeral=True)

    @discord.ui.button(label="📑 Ke Gambar", style=discord.ButtonStyle.green)
    async def image_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        out_dir = os.path.join(TEMP_DIR, f"images_{interaction.user.id}")
        os.makedirs(out_dir, exist_ok=True)
        
        img_paths = await pdf_ops.pdf_to_images(self.file_path, out_dir)
        if img_paths:
            # If 1-3 images, upload them directly, otherwise upload as a zip
            if len(img_paths) <= 3:
                files = [discord.File(p) for p in img_paths]
                await interaction.followup.send("📑 Halaman PDF berhasil diekstrak:", files=files, ephemeral=True)
            else:
                zip_path = os.path.join(TEMP_DIR, f"extracted_images_{interaction.user.id}.zip")
                with zipfile.ZipFile(zip_path, "w") as zipf:
                    for img in img_paths:
                        zipf.write(img, arcname=os.path.basename(img))
                file = discord.File(zip_path, filename="extracted_images.zip")
                await interaction.followup.send("📑 Halaman PDF berhasil diekstrak (ZIP):", file=file, ephemeral=True)
                try:
                    os.remove(zip_path)
                except Exception:
                    pass
            shutil.rmtree(out_dir, ignore_errors=True)
        else:
            await interaction.followup.send("❌ Gagal mengekstrak gambar dari PDF.", ephemeral=True)

    @discord.ui.button(label="🔒 Lock", style=discord.ButtonStyle.red)
    async def lock_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PDFPasswordModal("lock", self.file_path))

    @discord.ui.button(label="🔓 Unlock", style=discord.ButtonStyle.green)
    async def unlock_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PDFPasswordModal("unlock", self.file_path))

    @discord.ui.button(label="🏷️ Watermark", style=discord.ButtonStyle.secondary)
    async def watermark_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WatermarkModal(self.file_path))

    @discord.ui.button(label="✂️ Split", style=discord.ButtonStyle.secondary)
    async def split_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PDFSplitModal(self.file_path))

    @discord.ui.button(label="📝 Word (DOCX)", style=discord.ButtonStyle.primary)
    async def word_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        out_path = os.path.join(TEMP_DIR, f"{interaction.user.id}_converted.docx")
        res = await converter.pdf_to_docx(self.file_path, out_path)
        if res and os.path.exists(out_path):
            file = discord.File(out_path, filename="converted.docx")
            await interaction.followup.send("📝 PDF berhasil dikonversi ke Word (DOCX):", file=file, ephemeral=True)
            try:
                os.remove(out_path)
            except Exception:
                pass
        else:
            await interaction.followup.send("❌ Konversi gagal. Fitur ini memerlukan LibreOffice terinstal di server backend.", ephemeral=True)

    @discord.ui.button(label="📊 Excel (XLSX)", style=discord.ButtonStyle.primary)
    async def excel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        out_path = os.path.join(TEMP_DIR, f"{interaction.user.id}_converted.xlsx")
        res = await converter.pdf_to_xlsx(self.file_path, out_path)
        if res and os.path.exists(out_path):
            file = discord.File(out_path, filename="converted.xlsx")
            await interaction.followup.send("📊 PDF berhasil dikonversi ke Excel (XLSX):", file=file, ephemeral=True)
            try:
                os.remove(out_path)
            except Exception:
                pass



class ClearLogsDropdown(discord.ui.Select):
    def __init__(self, entries):
        options = []
        for e in entries:
            label = f"Quest #{e['id']} ({e['time'][:5]})"
            desc = e['text']
            if len(desc) > 100:
                desc = desc[:97] + "..."
            options.append(discord.SelectOption(label=label, value=str(e['id']), description=desc))
            
        super().__init__(
            placeholder="Pilih quest log untuk dihapus...",
            min_values=1,
            max_values=len(entries),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        deleted_ids = []
        for val in self.values:
            entry_id = int(val)
            if storage.delete_entry(entry_id):
                deleted_ids.append(entry_id)
                
        if deleted_ids:
            self.disabled = True
            await interaction.message.edit(view=self.view)
            await interaction.response.send_message(
                f"✅ Berhasil menghapus Quest Log #{', #'.join(map(str, deleted_ids))}.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Gagal menghapus catatan.", ephemeral=True)


class ClearLogsView(discord.ui.View):
    def __init__(self, user_id: int, entries: list):
        super().__init__(timeout=180.0)
        self.user_id = user_id
        if entries:
            self.add_item(ClearLogsDropdown(entries))
            
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Hanya pemilik log yang bisa menggunakan menu ini.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🗑️ Hapus Semua Hari Ini", style=discord.ButtonStyle.red, row=1)
    async def clear_all_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        today_entries = storage.get_today()
        deleted_count = 0
        for e in today_entries:
            if storage.delete_entry(e["id"]):
                deleted_count += 1
                
        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(view=self)
        await interaction.followup.send(f"✅ Berhasil menghapus {deleted_count} Quest Log hari ini.", ephemeral=True)

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary, row=1)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(view=self)
        await interaction.followup.send("❌ Tindakan dibatalkan.", ephemeral=True)


# ==========================================
# FILE HANDLER AND GENERAL DISPATCHER
# ==========================================

class SaveFoodLogView(discord.ui.View):
    def __init__(self, log_text: str, user_id: int):
        super().__init__(timeout=120.0)
        self.log_text = log_text
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Hanya pemilik log yang bisa menyimpan.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Simpan ke Jurnal", style=discord.ButtonStyle.green)
    async def save_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        entry = storage.add_entry(self.log_text)
        total = storage.get_entry_count()
        is_owner = await bot.is_owner(interaction.user)
        xp = ranks.get_xp_progress(total, is_owner=is_owner)
        
        embed = discord.Embed(
            title="🍳 Jurnal Gizi Tersimpan!",
            description=f"Makanan berhasil dicatat ke Jurnal sebagai Quest #{entry['id']}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Rangkuman", value=self.log_text, inline=False)
        embed.add_field(name="Hunter XP", value=f"Progress level: `{ranks.format_progress_bar(xp['percent'])}` ({xp['percent']}%)", inline=False)
        
        # Disable buttons
        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(view=self)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await check_and_promote(interaction.guild, interaction.user, total, interaction.channel)

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.red)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        # Disable buttons
        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(view=self)
        await interaction.followup.send("❌ Pencatatan makanan dibatalkan.", ephemeral=True)


class ConvertToPDFView(discord.ui.View):
    def __init__(self, file_path: str, user_id: int):
        super().__init__(timeout=180.0)
        self.file_path = file_path
        self.user_id = user_id
        
        # Hide/remove the food analysis button if the file is not an image
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg"):
            self.remove_item(self.food_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Aksi ditolak.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔄 Konversi ke PDF", style=discord.ButtonStyle.success)
    async def convert_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        out_path = os.path.join(TEMP_DIR, f"{interaction.user.id}_output.pdf")
        
        ext = os.path.splitext(self.file_path)[1].lower()
        res = None
        
        if ext in (".png", ".jpg", ".jpeg"):
            res = await converter.image_to_pdf(self.file_path, out_path)
        elif ext == ".docx":
            res = await converter.docx_to_pdf(self.file_path, out_path)
        elif ext == ".xlsx":
            res = await converter.xlsx_to_pdf(self.file_path, out_path)
        elif ext == ".pptx":
            res = await converter.pptx_to_pdf(self.file_path, out_path)
            
        if res and os.path.exists(out_path):
            file = discord.File(out_path, filename="converted.pdf")
            await interaction.followup.send("📄 Konversi ke PDF selesai:", file=file, ephemeral=True)
            try:
                os.remove(out_path)
            except Exception:
                pass
        else:
            await interaction.followup.send("❌ Gagal mengonversi file ke PDF.", ephemeral=True)

    @discord.ui.button(label="🍳 Analisis Gizi (AI)", style=discord.ButtonStyle.primary)
    async def food_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg"):
            await interaction.response.send_message("❌ Fitur analisis gizi hanya mendukung file gambar (PNG/JPG).", ephemeral=True)
            return
            
        # Disable buttons to prevent spamming
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            await interaction.followup.send("❌ **API Key Gemini belum diatur di file .env!**", ephemeral=True)
            return

        import base64
        import re
        import httpx
        
        try:
            with open(self.file_path, "rb") as f:
                img_bytes = f.read()
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            prompt_text = (
                "Anda adalah ahli gizi bersertifikat. Tugas Anda adalah menganalisis makanan pada gambar yang diberikan.\n"
                "1. Identifikasi semua makanan dan minuman yang terlihat.\n"
                "2. Perkirakan berat/porsi masing-masing secara visual.\n"
                "3. Estimasi jumlah Kalori (kcal), Protein (g), Karbohidrat (g), dan Lemak (g) berdasarkan USDA atau TKPI (Tabel Komposisi Pangan Indonesia).\n"
                "4. Berikan total nutrisi.\n"
                "5. Berikan saran/tips singkat tentang gizi makanan tersebut (misal: tinggi protein, tinggi lemak jenuh, kurang serat, dll.).\n\n"
                "PENTING: Tuliskan respon Anda dalam BAHASA INDONESIA dan gunakan format Markdown standar Discord (seperti **tebal**, *miring*, `kode`). "
                "Jangan gunakan tag HTML. Di baris paling pertama/kedua, berikan rangkuman satu baris dalam format yang persis seperti ini:\n"
                "===LOG_SUMMARY===\n"
                "🍳 Makan [nama makanan utama] (~[total_kalori] kcal, [total_protein]g protein)\n"
                "===END_LOG_SUMMARY==="
            )
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt_text},
                            {
                                "inlineData": {
                                    "mimeType": "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png",
                                    "data": img_base64
                                }
                            }
                        ]
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30.0)
                
            if response.status_code != 200:
                raise Exception(f"Gemini API returned status {response.status_code}")
                
            result = response.json()
            candidates = result.get("candidates", [])
            if not candidates:
                raise Exception("No analysis result returned from Gemini.")
                
            content_text = candidates[0]["content"]["parts"][0]["text"]
            
            log_summary = "Makan Porsi Makanan"
            summary_match = re.search(r"===LOG_SUMMARY===\s*(.*?)\s*===END_LOG_SUMMARY===", content_text, re.DOTALL)
            if summary_match:
                log_summary = summary_match.group(1).strip()
                content_text = content_text.replace(summary_match.group(0), "").strip()

            embed = discord.Embed(
                title="🍳 Hasil Analisis Nutrisi AI",
                description=content_text,
                color=discord.Color.green()
            )
            
            view = SaveFoodLogView(log_summary, interaction.user.id)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ **Gagal menganalisis foto:** {e}", ephemeral=True)


@bot.event
async def on_command_error(ctx, error):
    print(f"[Raffbot-priv] Command error from {ctx.author}: {error}")
    # Also notify the user or channel if appropriate
    try:
        await ctx.send(f"❌ **Error:** {error}")
    except Exception:
        pass

@bot.event
async def on_message(message):
    print(f"[Raffbot-priv] Message: '{message.content}' | Author: {message.author} | Channel: {message.channel}")
    if message.author == bot.user:
        return

    # Try to add chat XP
    if not message.author.bot:
        xp_result = chat_xp.try_add_xp(message.author.id)
        if xp_result and xp_result["promoted"] and message.guild:
            old_lvl = xp_result["old_level"]["level"]
            new_lvl = xp_result["level"]["level"]
            embed = discord.Embed(
                title="🎉 CHAT LEVEL UP!",
                description=f"⚡ {message.author.mention} naik ke level **{new_lvl[1]}**! ({xp_result['xp']} XP)",
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"From {old_lvl[1]} → {new_lvl[1]}")
            try:
                await message.channel.send(embed=embed)
            except Exception:
                pass

    # 1. Check if mentioned for Gemini AI Assistant
    if bot.user.mentioned_in(message):
        # Clean up bot mention from content using regex (handles <@id> and <@!id>)
        clean_content = re.sub(rf"<@!?{bot.user.id}>", "", message.content).strip()
        if not clean_content:
            await message.reply("Halo! Ada yang bisa saya bantu? Sebut saya bersama pertanyaan Anda.")
            return
            
        # Check if the user wants to log an activity directly via mention
        lower_content = clean_content.lower()
        is_log_intent = False
        log_text = clean_content
        
        prefixes = ["catat ", "jurnal ", "log ", "tambah agenda ", "tambah jurnal ", "tambah "]
        for prefix in prefixes:
            if lower_content.startswith(prefix):
                is_log_intent = True
                log_text = clean_content[len(prefix):].strip()
                break
                
        if is_log_intent and log_text:
            entry = storage.add_entry(log_text)
            total = storage.get_entry_count()
            is_owner = await bot.is_owner(message.author)
            xp = ranks.get_xp_progress(total, is_owner=is_owner)
            
            embed = discord.Embed(
                title="🛡️ Quest Log Cleared (via Mention)!",
                description=f"Quest berhasil dicatat sebagai Quest #{entry['id']}.",
                color=discord.Color.green()
            )
            embed.add_field(name="Aktivitas", value=log_text, inline=False)
            embed.add_field(name="Hunter XP", value=f"Level Progress: `{ranks.format_progress_bar(xp['percent'])}` ({xp['percent']}%)", inline=False)
            await message.reply(embed=embed)
            await check_and_promote(message.guild, message.author, total, message.channel)
            return
            
        async with message.channel.typing():
            # Call Gemini Client
            sys_inst = (
                "Anda adalah Raffbot-priv, asisten koding dan produktivitas pribadi yang cerdas, asyik, "
                "humoris, dan selalu menjawab dalam Bahasa Indonesia. Panggil pengguna sebagai 'Hunter' atau 'Master'."
            )
            response = await gemini_client.generate_response(
                channel_id=message.channel.id,
                user_message=clean_content,
                system_instruction=sys_inst
            )
            
            # Send response (chunked if > 2000 chars)
            for i in range(0, len(response), 2000):
                await message.reply(response[i:i+2000])
        return

    # 2. Check for uploaded attachments
    if message.attachments:
        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            
            if ext == ".pdf":
                # Save PDF to temp folder
                local_path = os.path.join(TEMP_DIR, f"{message.author.id}_{attachment.filename}")
                await attachment.save(local_path)
                
                embed = discord.Embed(
                    title="📄 Dokumen PDF Terdeteksi!",
                    description=f"File: `{attachment.filename}`\nPilih tindakan yang ingin dilakukan di bawah ini:",
                    color=discord.Color.red()
                )
                view = PDFToolsView(local_path, message.author.id)
                await message.reply(embed=embed, view=view)
                
            elif ext in (".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg"):
                # Save attachment to temp
                local_path = os.path.join(TEMP_DIR, f"{message.author.id}_{attachment.filename}")
                await attachment.save(local_path)
                
                if ext in (".png", ".jpg", ".jpeg"):
                    desc = f"Gambar `{attachment.filename}` terdeteksi. Pilih tindakan di bawah:"
                else:
                    desc = f"File `{attachment.filename}` dapat dikonversi menjadi file PDF."
                    
                embed = discord.Embed(
                    title="📎 File Terdeteksi!",
                    description=desc,
                    color=discord.Color.orange()
                )
                view = ConvertToPDFView(local_path, message.author.id)
                await message.reply(embed=embed, view=view)

    # Process default command prefix handlers
    await bot.process_commands(message)


# Owner command to clear active logs or restart
@bot.command()
@commands.is_owner()
async def clear_logs(ctx):
    storage.clear_all()
    await ctx.send("🧹 Seluruh log jurnal harian Anda telah dibersihkan.")


@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 Raffbot-priv Commands",
        description="Daftar perintah yang tersedia pada Raffbot-priv (mendukung `/` Slash command dan `!` prefix):",
        color=discord.Color.gold()
    )
    embed.add_field(name="⚔️ Solo Leveling Journal", value=(
        "`!start` - Membuka Menu Utama Journal (HUD)\n"
        "`!log <kegiatan>` - Mencatat jurnal/kegiatan baru\n"
        "`!rank` - Membuka Status Window Hunter Anda\n"
        "`!agenda` - Melihat Quest Board harian\n"
        "`!today` - Melihat log kegiatan hari ini\n"
        "`!yesterday` - Melihat log kegiatan kemarin\n"
        "`!date <YYYY-MM-DD>` - Melihat log tanggal tertentu\n"
        "`!search <kata kunci>` - Mencari catatan jurnal\n"
        "`!all` - Melihat arsip semua tanggal\n"
        "`!stats` - Statistik Hunter lengkap (Visual Card)\n"
        "`!clear` - Menghapus log hari ini secara interaktif\n"
        "`!del <id>` - Menghapus log berdasarkan ID (dengan autocomplete)"
    ), inline=False)
    embed.add_field(name="⏰ Reminder / Pengingat", value=(
        "`!remind <HH:MM> <pesan>` - Mengatur reminder harian\n"
        "`!remindat <YYYY-MM-DD> <HH:MM> <pesan>` - Mengatur reminder sekali\n"
        "`!reminders` - Melihat daftar reminder aktif Anda\n"
        "`!unremind <id>` - Menghapus reminder by ID (dengan autocomplete)"
    ), inline=False)
    embed.add_field(name="📄 PDF Tools & Converter", value=(
        "Cukup upload file `.pdf` untuk memicu menu interaktif PDF Tools.\n"
        "Cukup upload `.docx`, `.xlsx`, `.pptx`, `.png`, `.jpg` untuk memicu konversi otomatis ke PDF."
    ), inline=False)
    embed.add_field(name="🧠 AI Assistant @Raffbot-priv", value=(
        "Cukup sebut/mention `@Raffbot-priv <pertanyaan>` di obrolan untuk berbicara dengan Gemini AI."
    ), inline=False)
    embed.add_field(name="👋 Welcome & Goodbye", value=(
        "`/welcome channel` - Atur channel welcome\n"
        "`/welcome message <teks>` - Custom pesan welcome\n"
        "`/goodbye channel` - Atur channel goodbye\n"
        "`/goodbye message <teks>` - Custom pesan goodbye\n"
        "Gunakan `{user}`, `{name}`, `{server}` di pesan kustom."
    ), inline=False)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="features", aliases=["fitur", "allfeatures"], description="Melihat semua fitur yang tersedia pada Raffbot-priv")
async def features(ctx):
    embed = discord.Embed(
        title="🛡️ Raffbot-priv — Daftar Fitur Lengkap",
        description="Berikut adalah modul fitur yang siap digunakan Master/Hunter:",
        color=discord.Color.gold()
    )
    embed.add_field(name="⚔️ RPG Journal System", value=(
        "• `/start` : Menu Utama (HUD)\n"
        "• `/rank` : Status Window Hunter\n"
        "• `/myrank` : Ringkasan Profil & XP Hunter\n"
        "• `/agenda` : Papan Quest Board Harian\n"
        "• `/log` : Catat Quest (manual / Form popup)\n"
        "• **Auto Role Sync** : Menyesuaikan role otomatis sesuai Rank (s.d. National, & God Mode khusus Owner)."
    ), inline=True)
    embed.add_field(name="🗑️ Log Management", value=(
        "• `/clear` : Dropdown hapus log harian\n"
        "• `/del <id>` : Hapus log (dengan autocomplete)\n"
        "• `/date <tgl>` : Lihat log tanggal tertentu\n"
        "• `/search <kata>` : Cari log berdasarkan teks\n"
        "• `/all` : Lihat seluruh riwayat arsip harian\n"
        "• `/stats` : Kartu Statistik Hunter lengkap"
    ), inline=True)
    embed.add_field(name="⏰ Reminder System", value=(
        "• `/remind <waktu> <pesan>` : Pengingat harian (DM)\n"
        "• `/remindat <tgl> <waktu> <pesan>` : Pengingat sekali\n"
        "• `/reminders` : List pengingat aktif Anda\n"
        "• `/unremind <id>` : Hapus pengingat (autocomplete)"
    ), inline=True)
    embed.add_field(name="📄 PDF Tools & Document Converter", value=(
        "• Upload `.pdf` untuk memotong, mengompres, mengunci, memberi watermark, mengekstrak ke gambar, atau konversi ke Word/Excel.\n"
        "• Upload `.docx`, `.xlsx`, `.pptx`, atau gambar (`.png`/`.jpg`) untuk langsung dikonversi menjadi file PDF."
    ), inline=False)
    embed.add_field(name="🍳 AI Nutritionist & Gemini Assistant", value=(
        "• Upload foto makanan untuk dianalisis makronutrisinya (kalori, protein, dll.) secara otomatis oleh AI dan simpan langsung ke jurnal.\n"
        "• Tag/sebut `@Raffbot-priv` untuk berdiskusi dengan AI dalam Bahasa Indonesia."
    ), inline=False)
    embed.add_field(name="⚙️ System Utilities", value=(
        "• `/projects` : Memantau repositori GitHub Pidzzzz\n"
        "• `/addrole <member> <role>` : Memberikan role ke member (Admin/Owner)\n"
        "• `/removerole <member> <role>` : Menghapus role dari member (Admin/Owner)\n"
        "• `!restart` : Memulai ulang bot (Owner)"
    ), inline=False)
    embed.add_field(name="👋 Welcome & Goodbye System", value=(
        "• `/welcome channel` : Atur channel untuk welcome message\n"
        "• `/welcome message <teks>` : Set custom welcome message\n"
        "• `/welcome` : Lihat konfigurasi welcome saat ini\n"
        "• `/goodbye channel` : Atur channel untuk goodbye message\n"
        "• `/goodbye message <teks>` : Set custom goodbye message\n"
        "• `/goodbye` : Lihat konfigurasi goodbye saat ini\n"
        "**Gunakan `{user}` untuk mention, `{name}` untuk nama member, `{server}` untuk nama server**"
    ), inline=False)
    await ctx.send(embed=embed)
    

# ==========================================
# CHAT XP SYSTEM COMMANDS
# ==========================================

@bot.hybrid_command(name="chatrank", aliases=["chatxp", "cxp"], description="Lihat status Chat XP Anda")
async def chat_rank_cmd(ctx):
    data = chat_xp.get_user_data(ctx.author.id)
    xp = data["xp"]
    msgs = data.get("messages", 0)
    level = chat_xp.get_level(xp)
    current = level["level"]
    nxt = level["next"]

    if nxt:
        progress = xp - current[0]
        needed = nxt[0] - current[0]
        percent = int(progress / needed * 100)
        bar = chat_xp._load()  # just for import check
        filled = int(10 * percent / 100)
        progress_bar = "█" * filled + "░" * (10 - filled)
    else:
        percent = 100
        progress_bar = "██████████"

    embed = discord.Embed(
        title="💬 Chat XP Profile",
        color=discord.Color.from_rgb(200, 150, 220)
    )
    embed.add_field(name="Level", value=f"{current[2]} {current[1]}", inline=True)
    embed.add_field(name="XP", value=f"`{xp}`", inline=True)
    embed.add_field(name="Messages", value=f"`{msgs}`", inline=True)
    if nxt:
        embed.add_field(name="Progress", value=f"`{progress_bar}` ({percent}%)\n`{xp - current[0]}/{nxt[0] - current[0]}` ke **{nxt[1]}**", inline=False)
    else:
        embed.add_field(name="Progress", value="`██████████` Max Level Reached!", inline=False)
    embed.set_footer(text=f"Cooldown: {chat_xp.COOLDOWN_SECONDS}s | Max harian: {chat_xp.MAX_XP_PER_DAY} XP")
    await ctx.send(embed=embed)


@bot.hybrid_command(name="leaderboard", aliases=["lb", "top"], description="Leaderboard Chat XP di server")
async def leaderboard_cmd(ctx):
    leaders = chat_xp.get_leaderboard(10)
    if not leaders:
        await ctx.send("📭 Belum ada data Chat XP.")
        return

    embed = discord.Embed(
        title="🏆 Chat XP Leaderboard",
        color=discord.Color.gold()
    )
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, entry in enumerate(leaders):
        member = ctx.guild.get_member(entry["user_id"]) if ctx.guild else None
        name = member.display_name if member else f"User#{entry['user_id']}"
        medal = medals[i] if i < 3 else f"**#{i+1}**"
        level = chat_xp.get_level(entry["xp"])
        lvl_info = level["level"]
        lines.append(f"{medal} {name} — {lvl_info[2]} {lvl_info[1]} | `{entry['xp']} XP` | `{entry['messages']} msgs`")

    embed.description = "\n".join(lines)
    embed.set_footer(text=f"XP per pesan: {chat_xp.XP_PER_MESSAGE} | Cooldown: {chat_xp.COOLDOWN_SECONDS}s")
    await ctx.send(embed=embed)


@bot.hybrid_command(name="xphelp", description="Info tentang sistem Chat XP")
async def xp_help_cmd(ctx):
    embed = discord.Embed(
        title="💬 Chat XP System",
        description="Semua pesan di server akan mendapatkan XP otomatis!",
        color=discord.Color.from_rgb(200, 150, 220)
    )
    embed.add_field(name="Cara Kerja", value=(
        f"• Setiap pesan: **+{chat_xp.XP_PER_MESSAGE} XP**\n"
        f"• Cooldown: **{chat_xp.COOLDOWN_SECONDS} detik** antar pesan\n"
        f"• Max XP harian: **{chat_xp.MAX_XP_PER_DAY} XP**\n"
        f"• Level up otomatis saat naik level!"
    ), inline=False)
    embed.add_field(name="Level Table", value="\n".join([f"{lvl[2]} `{lvl[0]}+ XP` → **{lvl[1]}**" for lvl in chat_xp.LEVEL_TABLE]), inline=False)
    embed.add_field(name="Commands", value=(
        "`/chatrank` — Lihat XP & level Anda\n"
        "`/leaderboard` — Top 10 XP di server\n"
        "`/xphelp` — Info ini"
    ), inline=False)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="testwelcome", description="Tes kirim welcome card (seolah-olah member baru)")
@commands.has_permissions(manage_guild=True)
async def test_welcome(ctx):
    if not ctx.guild:
        await ctx.send("❌ Hanya bisa di server.")
        return
    if ctx.interaction:
        await ctx.interaction.response.defer()
    config = wc.get_guild_config(ctx.guild.id)
    channel_id = config.get("welcome_channel") or ctx.channel.id
    channel = ctx.guild.get_channel(channel_id) or ctx.channel
    member = ctx.author
    try:
        avatar_bytes = None
        if member.avatar:
            avatar_bytes = await member.avatar.read()
        elif member.display_avatar:
            avatar_bytes = await member.display_avatar.read()
        card_data = image_generator.generate_welcome_image(
            member_name=member.display_name,
            guild_name=ctx.guild.name,
            member_count=ctx.guild.member_count or len(ctx.guild.members),
            avatar_bytes=avatar_bytes
        )
        file = discord.File(io.BytesIO(card_data), filename="test_welcome.png")
    except Exception:
        file = None
    embed = discord.Embed(
        title="🎯 Test Welcome Card",
        description=f"Ini contoh welcome untuk {member.mention}",
        color=discord.Color.from_rgb(194, 168, 120)
    )
    if file:
        await channel.send(file=file, embed=embed)
    else:
        await channel.send(embed=embed)
    if ctx.interaction:
        if channel.id != ctx.channel.id:
            await ctx.interaction.followup.send(f"✅ Test welcome dikirim ke {channel.mention}", ephemeral=True)
        else:
            await ctx.interaction.followup.send("✅ Test welcome berhasil!", ephemeral=True)


@bot.hybrid_command(name="testgoodbye", description="Tes kirim goodbye card (seolah-olah member keluar)")
@commands.has_permissions(manage_guild=True)
async def test_goodbye(ctx):
    if not ctx.guild:
        await ctx.send("❌ Hanya bisa di server.")
        return
    if ctx.interaction:
        await ctx.interaction.response.defer()
    config = wc.get_guild_config(ctx.guild.id)
    channel_id = config.get("goodbye_channel") or ctx.channel.id
    channel = ctx.guild.get_channel(channel_id) or ctx.channel
    member = ctx.author
    try:
        card_data = image_generator.generate_goodbye_image(
            member_name=member.display_name,
            guild_name=ctx.guild.name,
            member_count=(ctx.guild.member_count or len(ctx.guild.members)) - 1
        )
        file = discord.File(io.BytesIO(card_data), filename="test_goodbye.png")
    except Exception:
        file = None
    embed = discord.Embed(
        title="🎯 Test Goodbye Card",
        description=f"Ini contoh goodbye untuk {member.display_name}",
        color=discord.Color.from_rgb(142, 142, 147)
    )
    if file:
        await channel.send(file=file, embed=embed)
    else:
        await channel.send(embed=embed)
    if ctx.interaction:
        if channel.id != ctx.channel.id:
            await ctx.interaction.followup.send(f"✅ Test goodbye dikirim ke {channel.mention}", ephemeral=True)
        else:
            await ctx.interaction.followup.send("✅ Test goodbye berhasil!", ephemeral=True)


@bot.hybrid_command(name="testpromote", description="Menguji promosi rank dan role")
async def test_promote(ctx, rank_letter: str):
    rank_letter = rank_letter.upper()
    is_owner = await bot.is_owner(ctx.author)
    
    if rank_letter in ("GOD", "GOD MODE", "GOD_MODE"):
        rank_letter = "GOD MODE"
        
    valid_ranks = ["E", "D", "C", "B", "A", "S", "NATIONAL"]
    if is_owner:
        valid_ranks.append("GOD MODE")
        
    if rank_letter == "GOD MODE" and not is_owner:
        await ctx.send("❌ Hanya Developer/Owner bot yang diperbolehkan mengakses rank **God Mode**!")
        return
        
    if rank_letter not in valid_ranks:
        await ctx.send(f"❌ Rank tidak valid. Pilih salah satu: {', '.join(valid_ranks)}")
        return
        
    import src.ranks as rk
    min_entries = 0
    for r in rk.RANKS:
        if r["rank"].upper() == rank_letter:
            min_entries = r["min_entries"]
            break
            
    if ctx.guild:
        try:
            member = ctx.guild.get_member(ctx.author.id) or await ctx.guild.fetch_member(ctx.author.id)
            if member:
                target_role = await update_hunter_roles(member, min_entries)
                if target_role:
                    embed = discord.Embed(
                        title="🎉 HUNTER PROMOTION (TEST)!",
                        description=f"⚡ {member.mention} telah dipromosikan menjadi **{target_role.name}**!",
                        color=target_role.color
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Gagal menyinkronkan role. Pastikan bot memiliki izin `Manage Roles` dan posisinya berada di paling atas.")
        except Exception as e:
            await ctx.send(f"❌ Error saat uji coba: {e}")
    else:
        await ctx.send("❌ Uji coba hanya bisa dilakukan di dalam server Discord.")


@bot.hybrid_command(name="myrank", description="Melihat ringkasan status rank dan role Hunter Anda")
async def myrank(ctx):
    all_entries = storage.get_all_entries()
    total = len(all_entries)
    stats = storage.get_stats()
    
    is_owner = await bot.is_owner(ctx.author)
    rank = ranks.get_rank(total, is_owner=is_owner)
    xp = ranks.get_xp_progress(total, is_owner=is_owner)
    streak = ranks.get_streak_info(all_entries)
    
    embed = discord.Embed(
        title=f"🛡️ Hunter Profile — {ctx.author.name}",
        description=f"Status rank dan pencapaian Anda saat ini:",
        color=discord.Color.from_rgb(194, 168, 120)
    )
    
    embed.add_field(name="👑 Rank saat ini", value=f"{rank['emoji']} **{rank['title']}**", inline=True)
    embed.add_field(name="🔥 Streak Buff", value=f"`{streak['streak']} Hari`", inline=True)
    embed.add_field(name="📊 Total Quest", value=f"`{total} Quest Selesai`", inline=True)
    
    if xp["next"]:
        progress_bar = ranks.format_progress_bar(xp["percent"])
        embed.add_field(
            name=f"⚡ Monarch Sync Progress ({xp['percent']}%)",
            value=f"`{progress_bar}`\nButuh `{xp['entries_needed']}` Quest lagi menuju **{xp['next']['title']}**",
            inline=False
        )
    else:
        embed.add_field(name="⚡ Monarch Sync Progress", value="`██████████` (Max Level Reached)", inline=False)
        
    await ctx.send(embed=embed)
    
    if ctx.guild:
        asyncio.create_task(update_hunter_roles(ctx.author, total))


def check_owner_or_manage_roles():
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.guild and ctx.author.guild_permissions.manage_roles:
            return True
        raise commands.MissingPermissions(["manage_roles"])
    return commands.check(predicate)


@bot.hybrid_command(name="addrole", description="Memberikan role kepada seorang member")
@check_owner_or_manage_roles()
async def addrole(ctx, member: discord.Member, role: discord.Role):
    if not ctx.guild:
        await ctx.send("❌ Perintah ini hanya bisa digunakan di dalam server.")
        return
        
    if not ctx.guild.me.guild_permissions.manage_roles:
        await ctx.send("❌ Bot tidak memiliki izin `Manage Roles` (Mengelola Role) di server ini.")
        return
        
    if role >= ctx.guild.me.top_role:
        await ctx.send(f"❌ Gagal: Role **{role.name}** berada di posisi yang sama atau lebih tinggi dari role tertinggi bot saya. Harap naikkan tingkat role bot Anda di server settings.")
        return
        
    is_owner = await bot.is_owner(ctx.author)
    if not is_owner and role >= ctx.author.top_role:
        await ctx.send(f"❌ Gagal: Anda tidak bisa memberikan role **{role.name}** karena posisinya sama atau lebih tinggi dari role tertinggi Anda.")
        return
        
    if role in member.roles:
        await ctx.send(f"⚠️ {member.mention} sudah memiliki role **{role.name}**.")
        return
        
    try:
        await member.add_roles(role, reason=f"Diberikan oleh {ctx.author.name} via /addrole")
        embed = discord.Embed(
            title="✅ Role Berhasil Diberikan",
            description=f"Berhasil memberikan role {role.mention} kepada {member.mention}.",
            color=role.color if role.color.value != 0 else discord.Color.green()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Gagal memberikan role: {e}")


@bot.hybrid_command(name="removerole", description="Menghapus role dari seorang member")
@check_owner_or_manage_roles()
async def removerole(ctx, member: discord.Member, role: discord.Role):
    if not ctx.guild:
        await ctx.send("❌ Perintah ini hanya bisa digunakan di dalam server.")
        return
        
    if not ctx.guild.me.guild_permissions.manage_roles:
        await ctx.send("❌ Bot tidak memiliki izin `Manage Roles` (Mengelola Role) di server ini.")
        return
        
    if role >= ctx.guild.me.top_role:
        await ctx.send(f"❌ Gagal: Role **{role.name}** berada di posisi yang sama atau lebih tinggi dari role tertinggi bot saya.")
        return
        
    is_owner = await bot.is_owner(ctx.author)
    if not is_owner and role >= ctx.author.top_role:
        await ctx.send(f"❌ Gagal: Anda tidak bisa menghapus role **{role.name}** karena posisinya sama atau lebih tinggi dari role tertinggi Anda.")
        return
        
    if role not in member.roles:
        await ctx.send(f"⚠️ {member.mention} tidak memiliki role **{role.name}**.")
        return
        
    try:
        await member.remove_roles(role, reason=f"Dihapus oleh {ctx.author.name} via /removerole")
        embed = discord.Embed(
            title="✅ Role Berhasil Dihapus",
            description=f"Berhasil menghapus role {role.mention} dari {member.mention}.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Gagal menghapus role: {e}")


# Main runner
if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_discord_bot_token_here":
        print("❌ Error: Silakan konfigurasi DISCORD_TOKEN Anda terlebih dahulu di file .env!")
    else:
        bot.run(TOKEN)
