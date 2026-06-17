import os
import io
import math
from PIL import Image, ImageDraw, ImageFont

# Minimalist Aesthetic Dark Theme Colors
COLOR_BG = (15, 15, 17)           # Clean charcoal black
COLOR_CARD = (23, 23, 26)         # Deep dark grey panel
COLOR_BORDER = (40, 40, 44)       # Subtle, thin border
COLOR_TEXT_WHITE = (245, 245, 247) # Soft white
COLOR_TEXT_MUTED = (142, 142, 147) # Muted Apple-like grey
COLOR_ACCENT = (194, 168, 120)    # Minimalist Champagne Gold
COLOR_GREEN = (46, 204, 113)
COLOR_RED = (231, 76, 60)

RANK_COLORS = {
    "E": (160, 165, 175),         # Muted Pewter
    "D": (185, 150, 130),         # Warm Sand
    "C": (140, 175, 155),         # Soft Sage Green
    "B": (135, 165, 185),         # Dusty Blue
    "A": (170, 150, 185),         # Muted Lavender
    "S": (200, 135, 135),         # Soft Terracotta
    "National": (195, 165, 120)    # Antique Gold
}

def get_font(font_name="segoeui.ttf", size=16):
    try:
        font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", font_name)
        if not os.path.exists(font_path):
            font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
        return ImageFont.truetype(font_path, size)
    except IOError:
        return ImageFont.load_default()

def draw_background_grid(draw, width, height):
    # Minimalist look uses a clean, solid background. Grid is disabled.
    pass

def draw_hexagon(draw, cx, cy, r, fill, outline, width=1):
    points = []
    for i in range(6):
        angle = math.radians(i * 60 - 30) # vertical alignment
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=fill, outline=outline, width=width)

def draw_hud_design(draw, width, height, glow_color=COLOR_BORDER):
    # Single elegant thin border
    draw.rectangle([15, 15, width - 16, height - 16], outline=COLOR_BORDER, width=1)
    
    # Minimalist neat corner brackets
    bracket_len = 15
    # Top-Left
    draw.line([15, 15, 15 + bracket_len, 15], fill=glow_color, width=2)
    draw.line([15, 15, 15, 15 + bracket_len], fill=glow_color, width=2)
    # Top-Right
    draw.line([width - 16, 15, width - 16 - bracket_len, 15], fill=glow_color, width=2)
    draw.line([width - 16, 15, width - 16, 15 + bracket_len], fill=glow_color, width=2)
    # Bottom-Left
    draw.line([15, height - 16, 15 + bracket_len, height - 16], fill=glow_color, width=2)
    draw.line([15, height - 16, 15, height - 16 - bracket_len], fill=glow_color, width=2)
    # Bottom-Right
    draw.line([width - 16, height - 16, width - 16 - bracket_len, height - 16], fill=glow_color, width=2)
    draw.line([width - 16, height - 16, width - 16, height - 16 - bracket_len], fill=glow_color, width=2)

def generate_welcome_card(hunter_name: str, rank_letter: str, rank_title: str, total_entries: int, active_days: int) -> bytes:
    width, height = 600, 390
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    draw_background_grid(draw, width, height)
    accent_color = RANK_COLORS.get(rank_letter, COLOR_ACCENT)
    draw_hud_design(draw, width, height, glow_color=accent_color)
    
    # Fonts
    font_title = get_font("segoeuib.ttf", 24)
    font_subtitle = get_font("segoeuii.ttf", 13)
    font_section = get_font("segoeuib.ttf", 12)
    font_bold = get_font("segoeuib.ttf", 18)
    font_reg = get_font("segoeui.ttf", 15)
    
    # Title & Headers
    draw.text((300, 45), "MONARCH SYSTEM", fill=COLOR_TEXT_WHITE, font=font_title, anchor="mm")
    draw.text((300, 72), "HUNTER ACTIVITY REGISTER", fill=COLOR_TEXT_MUTED, font=font_subtitle, anchor="mm")
    draw.line([50, 88, 550, 88], fill=COLOR_BORDER, width=1)
    
    # Outer Panel card
    draw.rounded_rectangle([40, 105, 560, 345], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    # Hexagonal Rank Shield
    draw_hexagon(draw, 115, 195, 48, fill=COLOR_BG, outline=accent_color, width=1)
    draw.text((115, 195), rank_letter, fill=accent_color, font=get_font("segoeuib.ttf", 42), anchor="mm")
    draw.text((115, 260), "RANK", fill=COLOR_TEXT_MUTED, font=font_section, anchor="mm")
    
    # Information Box
    x_offset = 200
    draw.text((x_offset, 130), "CODENAME / HUNTER NAME", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.text((x_offset, 150), hunter_name.upper(), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((x_offset, 185), "CURRENT TITLE", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.text((x_offset, 205), rank_title, fill=accent_color, font=font_reg)
    
    # Bottom Stats Bar
    draw.line([200, 240, 520, 240], fill=COLOR_BORDER, width=1)
    
    # Left Stat
    draw.text((x_offset, 255), "LOGS RECORDED", fill=COLOR_TEXT_MUTED, font=font_subtitle)
    draw.text((x_offset, 275), str(total_entries), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    # Right Stat
    draw.text((380, 255), "DAYS ACTIVE", fill=COLOR_TEXT_MUTED, font=font_subtitle)
    draw.text((380, 275), str(active_days), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    # Small status indicator tag (Pill style with a green dot)
    draw.rounded_rectangle([445, 125, 535, 145], radius=10, fill=(28, 28, 30))
    draw.ellipse([457, 132, 463, 138], fill=COLOR_GREEN)
    draw.text((498, 135), "ONLINE", fill=COLOR_TEXT_WHITE, font=get_font("segoeuib.ttf", 9), anchor="mm")
    
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

def generate_status_card(hunter_name: str, rank_letter: str, rank_title: str, xp_percent: int, streak_days: int, streak_title: str, total_entries: int, active_days: int) -> bytes:
    width, height = 600, 770
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    draw_background_grid(draw, width, height)
    accent_color = RANK_COLORS.get(rank_letter, COLOR_ACCENT)
    draw_hud_design(draw, width, height, glow_color=accent_color)
    
    # Fonts
    font_header = get_font("segoeuib.ttf", 24)
    font_section = get_font("segoeuib.ttf", 13)
    font_bold = get_font("segoeuib.ttf", 18)
    font_reg = get_font("segoeui.ttf", 15)
    font_small = get_font("segoeui.ttf", 13)
    
    # Header Window
    draw.text((300, 45), "STATUS WINDOW", fill=COLOR_TEXT_WHITE, font=font_header, anchor="mm")
    draw.line([50, 75, 550, 75], fill=COLOR_BORDER, width=1)
    
    # 1. Profile Block
    draw.rounded_rectangle([40, 95, 560, 225], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    # Hexagonal Rank Shield
    draw_hexagon(draw, 105, 160, 48, fill=COLOR_BG, outline=accent_color, width=1)
    draw.text((105, 160), rank_letter, fill=accent_color, font=get_font("segoeuib.ttf", 40), anchor="mm")
    
    # Profile labels & values
    x_prof = 180
    draw.text((x_prof, 115), "CODENAME:", fill=COLOR_TEXT_MUTED, font=font_small)
    draw.text((x_prof + 95, 113), hunter_name, fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((x_prof, 145), "HUNTER RANK:", fill=COLOR_TEXT_MUTED, font=font_small)
    draw.text((x_prof + 95, 143), f"{rank_letter}-Rank", fill=accent_color, font=font_bold)
    
    draw.text((x_prof, 175), "CLASS / TITLE:", fill=COLOR_TEXT_MUTED, font=font_small)
    draw.text((x_prof + 95, 173), rank_title, fill=COLOR_TEXT_WHITE, font=font_reg)
    
    # 2. Stats Block
    draw.text((45, 250), "JOURNAL STATISTICS", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.rounded_rectangle([40, 275, 560, 420], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y_stats = 295
    # Stats Items
    draw.text((70, y_stats), "Cleared Quest Logs:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((480, y_stats), str(total_entries), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((70, y_stats + 35), "Days Active in System:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((480, y_stats + 35), str(active_days), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((70, y_stats + 70), "Active Streak Buff:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((480, y_stats + 70), f"{streak_days} Days", fill=COLOR_ACCENT if streak_days > 0 else COLOR_TEXT_WHITE, font=font_bold)
    
    # 3. Level & XP Progress Block
    level = (total_entries // 10) + 1
    draw.text((45, 445), f"LEVEL & PROGRESSION (Lv. {level})", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.rounded_rectangle([40, 470, 560, 580], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    # XP text labels
    draw.text((70, 490), "Monarch System Sync:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((480, 490), f"{xp_percent}%", fill=accent_color, font=font_bold)
    
    # Modern Segmented Progress Bar (Thin style is more premium)
    bar_x1, bar_y1, bar_x2, bar_y2 = 70, 525, 530, 532
    draw.rounded_rectangle([bar_x1, bar_y1, bar_x2, bar_y2], radius=3, fill=(30, 30, 35), outline=COLOR_BORDER, width=1)
    
    bar_width = int((bar_x2 - bar_x1) * xp_percent / 100)
    if bar_width > 0:
        draw.rounded_rectangle([bar_x1, bar_y1, bar_x1 + bar_width, bar_y2], radius=3, fill=accent_color)
        
    # 4. Buff & Title Milestones
    draw.text((45, 605), "SYSTEM PASSIVE BUFFS", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.rounded_rectangle([40, 630, 560, 715], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    if streak_days > 0:
        draw_hexagon(draw, 80, 672, 20, fill=COLOR_BG, outline=COLOR_ACCENT, width=1)
        draw.text((80, 672), "B", fill=COLOR_ACCENT, font=get_font("segoeuib.ttf", 15), anchor="mm")
        
        draw.text((120, 648), "Active Buff: Streak Monarch", fill=COLOR_ACCENT, font=font_bold)
        draw.text((120, 675), f"Title unlocked: {streak_title}", fill=COLOR_TEXT_WHITE, font=font_small)
    else:
        draw.text((300, 672), "No active streak buffs. Log daily to level up your titles!", fill=COLOR_TEXT_MUTED, font=font_small, anchor="mm")
        
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

def generate_agenda_card(date_str: str, active_quests: list, cleared_quests: list) -> bytes:
    width, height = 600, 780
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    draw_background_grid(draw, width, height)
    draw_hud_design(draw, width, height, glow_color=COLOR_ACCENT)
    
    font_header = get_font("segoeuib.ttf", 24)
    font_section = get_font("segoeuib.ttf", 15)
    font_bold = get_font("segoeuib.ttf", 16)
    font_reg = get_font("segoeui.ttf", 14)
    font_small = get_font("segoeui.ttf", 12)
    
    # Header
    draw.text((300, 45), "DAILY QUEST BOARD", fill=COLOR_TEXT_WHITE, font=font_header, anchor="mm")
    draw.text((300, 72), f"TARGET DATE: {date_str}", fill=COLOR_TEXT_MUTED, font=font_small, anchor="mm")
    draw.line([50, 88, 550, 88], fill=COLOR_BORDER, width=1)
    
    # 1. Active Quests (Reminders)
    draw.text((45, 105), "⚔️ ACTIVE QUESTS (Reminders)", fill=COLOR_ACCENT, font=font_section)
    draw.rounded_rectangle([40, 130, 560, 380], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y = 155
    if not active_quests:
        draw.text((300, 255), "No pending active quests. Safe Zone.", fill=COLOR_TEXT_MUTED, font=font_reg, anchor="mm")
    else:
        for q in active_quests[:6]:
            q_time = q.get("remind_at", "").split("T")[1][:5] if "T" in q.get("remind_at", "") else q.get("remind_at", "")[:5]
            q_text = q.get("text", "")
            if len(q_text) > 42:
                q_text = q_text[:39] + "..."
            
            # Draw a sleek, thin tech-style check box
            draw.rectangle([55, y+2, 69, y+16], outline=COLOR_BORDER, width=1)
            draw.text((85, y), f"[{q_time}] {q_text}", fill=COLOR_TEXT_WHITE, font=font_reg)
            y += 35
            
    # 2. Cleared Quests (Logs)
    draw.text((45, 415), "🛡️ CLEARED QUESTS (Daily Logs)", fill=COLOR_GREEN, font=font_section)
    draw.rounded_rectangle([40, 440, 560, 740], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y = 465
    if not cleared_quests:
        draw.text((300, 590), "No activities recorded. Awaiting quest inputs...", fill=COLOR_TEXT_MUTED, font=font_reg, anchor="mm")
    else:
        for l in cleared_quests[:7]:
            l_time = l.get("time", "")[:5]
            l_text = l.get("text", "")
            if len(l_text) > 42:
                l_text = l_text[:39] + "..."
                
            # Draw green checkmark symbol
            draw.text((55, y), "✓", fill=COLOR_GREEN, font=font_bold)
            draw.text((85, y), f"[{l_time}] {l_text}", fill=COLOR_TEXT_MUTED, font=font_reg)
            y += 35
            
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

def generate_stats_card(total_entries: int, active_days: int, first_date: str, last_date: str) -> bytes:
    width, height = 600, 480
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    draw_background_grid(draw, width, height)
    draw_hud_design(draw, width, height, glow_color=COLOR_ACCENT)
    
    font_header = get_font("segoeuib.ttf", 24)
    font_section = get_font("segoeuib.ttf", 13)
    font_bold = get_font("segoeuib.ttf", 18)
    font_reg = get_font("segoeui.ttf", 15)
    
    # Header
    draw.text((300, 45), "SYSTEM STATISTICS", fill=COLOR_TEXT_WHITE, font=font_header, anchor="mm")
    draw.line([50, 75, 550, 75], fill=COLOR_BORDER, width=1)
    
    # Outer Panel
    draw.rounded_rectangle([40, 95, 560, 440], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y = 125
    draw.text((70, y), "Total Completed Entries:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), str(total_entries), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    y += 50
    draw.text((70, y), "Monarch Active Days:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), str(active_days), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    y += 50
    draw.text((70, y), "Initial Sync Date:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), str(first_date or "-"), fill=COLOR_TEXT_WHITE, font=font_reg)
    
    y += 50
    draw.text((70, y), "Last Sync Date:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), str(last_date or "-"), fill=COLOR_TEXT_WHITE, font=font_reg)
    
    y += 65
    draw.line([60, y, 540, y], fill=COLOR_BORDER, width=1)
    
    # Level Estimation
    level = (total_entries // 10) + 1
    y += 20
    draw.text((70, y), "Estimated Hunter Level:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), f"Lv. {level}", fill=COLOR_ACCENT, font=font_bold)
    
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

COLOR_PURPLE_GLOW = (255, 0, 255)
COLOR_DARK_PURPLE = (25, 0, 50)

def generate_welcome_image(member_name: str, guild_name: str, member_count: int, avatar_bytes: bytes = None) -> bytes:
    width, height = 960, 540
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Load reference background
    ref_path = os.path.join(ASSETS_DIR, "welcome_ref.png")
    try:
        bg = Image.open(ref_path).convert("RGB")
        # Resize bg to cover entire card, then center-crop
        scale = max(width / bg.width, height / bg.height)
        new_w = int(bg.width * scale)
        new_h = int(bg.height * scale)
        bg = bg.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        bg = bg.crop((left, top, left + width, top + height))
        img.paste(bg, (0, 0))
    except Exception:
        # fallback: dark purple gradient
        for y in range(height):
            ratio = y / height
            r = int(25 + ratio * 10)
            g = int(0 + ratio * 0)
            b = int(50 + ratio * 20)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Dark overlay for text readability
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    # Left side darkening
    for x in range(width // 3):
        alpha = int(180 * (1 - x / (width // 3)))
        overlay_draw.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))
    # Right side darkening
    for x in range(width * 2 // 3, width):
        alpha = int(140 * ((x - width * 2 // 3) / (width // 3)))
        overlay_draw.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))
    # Bottom darkening
    for y in range(height * 2 // 3, height):
        alpha = int(100 * ((y - height * 2 // 3) / (height // 3)))
        overlay_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Fonts
    font_huge = get_font("segoeuib.ttf", 80)
    font_member = get_font("segoeuib.ttf", 32)
    font_sub = get_font("segoeui.ttf", 18)
    font_badge = get_font("segoeuib.ttf", 13)
    font_server = get_font("segoeuib.ttf", 22)
    font_hash = get_font("segoeuii.ttf", 14)

    # --- Avatar (left area) ---
    if avatar_bytes:
        try:
            av_size = 120
            avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            avatar_img = avatar_img.resize((av_size, av_size), Image.LANCZOS)

            mask = Image.new("L", (av_size, av_size), 0)
            ImageDraw.Draw(mask).ellipse([(0, 0), (av_size, av_size)], fill=255)

            avatar_canvas = Image.new("RGBA", (av_size, av_size), (0, 0, 0, 0))
            avatar_canvas.paste(avatar_img, (0, 0), mask)

            # Glow ring around avatar
            glow_size = av_size + 20
            glow_img = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_img)
            glow_draw.ellipse([(0, 0), (glow_size, glow_size)], outline=(255, 0, 255, 100), width=3)

            img.paste(glow_img, (100, height // 2 - glow_size // 2), glow_img)
            img.paste(avatar_canvas, (110, height // 2 - av_size // 2), avatar_canvas)
        except Exception:
            pass

    # --- Main "WELCOME" text (right side, large) ---
    welcome_text = "WELCOME"
    # Draw glow behind text
    for offset in [3, 2, 1]:
        alpha = 40 * offset
        draw.text((width - 140, 80), welcome_text, fill=(255, 0, 255, alpha), font=font_huge, anchor="mm")
    draw.text((width - 140, 80), welcome_text, fill=(255, 255, 255, 240), font=font_huge, anchor="mm")

    # --- Member name ---
    name_display = member_name if len(member_name) <= 22 else member_name[:20] + ".."
    draw.text((width - 140, 170), name_display, fill=(0, 0, 0, 200), font=font_member, anchor="mm")

    # --- Separator line ---
    draw.line([(width - 300, 200), (width - 10, 200)], fill=(255, 0, 255, 80), width=1)

    # --- Server name ---
    draw.text((width - 140, 235), f"Selamat datang di {guild_name}", fill=(200, 200, 220, 200), font=font_sub, anchor="mm")

    # --- Member count badge ---
    badge_text = f"# ARISE | Member ke-{member_count}"
    badge_w = draw.textlength(badge_text, font=font_badge) + 30
    badge_x = width - 140 - int(badge_w) // 2
    badge_y = 280
    draw.rounded_rectangle([badge_x, badge_y, badge_x + int(badge_w), badge_y + 30], radius=15, fill=(255, 0, 255, 50), outline=(255, 0, 255, 120), width=1)
    draw.text((width - 140, badge_y + 15), badge_text, fill=(255, 255, 255, 220), font=font_badge, anchor="mm")

    bio = io.BytesIO()
    img = img.convert("RGB")
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()


def generate_goodbye_image(member_name: str, guild_name: str, member_count: int) -> bytes:
    width, height = 960, 400
    img = Image.new("RGB", (width, height), color=(10, 0, 20))
    draw = ImageDraw.Draw(img)

    # Use same reference but with heavier dark overlay
    ref_path = os.path.join(ASSETS_DIR, "welcome_ref.png")
    try:
        bg = Image.open(ref_path).convert("RGB")
        scale = max(width / bg.width, height / bg.height)
        new_w = int(bg.width * scale)
        new_h = int(bg.height * scale)
        bg = bg.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        bg = bg.crop((left, top, left + width, top + height))

        # Desaturate + darken for goodbye vibe
        from PIL import ImageEnhance
        bg = ImageEnhance.Color(bg).enhance(0.3)
        bg = ImageEnhance.Brightness(bg).enhance(0.4)
        img.paste(bg, (0, 0))
    except Exception:
        for y in range(height):
            ratio = y / height
            r = int(10 + ratio * 15)
            g = int(0)
            b = int(20 + ratio * 10)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Heavy overlay
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([0, 0, width, height], fill=(0, 0, 0, 100))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    font_huge = get_font("segoeuib.ttf", 72)
    font_name = get_font("segoeuib.ttf", 36)
    font_sub = get_font("segoeui.ttf", 18)
    font_footer = get_font("segoeuii.ttf", 13)

    # --- "GOODBYE" main text ---
    for offset in [3, 2, 1]:
        alpha = 30 * offset
        draw.text((width // 2, 80), "GOODBYE", fill=(160, 100, 180, alpha), font=font_huge, anchor="mm")
    draw.text((width // 2, 80), "GOODBYE", fill=(200, 200, 220, 220), font=font_huge, anchor="mm")

    # --- Member name ---
    draw.text((width // 2, 160), member_name, fill=(200, 140, 220, 230), font=font_name, anchor="mm")

    # --- Separator ---
    draw.line([(width // 2 - 140, 200), (width // 2 + 140, 200)], fill=(160, 100, 180, 60), width=1)

    # --- Server info ---
    draw.text((width // 2, 230), f"Telah meninggalkan {guild_name}", fill=(180, 180, 200, 180), font=font_sub, anchor="mm")
    draw.text((width // 2, 265), f"Tersisa {member_count} anggota", fill=(150, 150, 170, 160), font=font_sub, anchor="mm")

    # --- Footer ---
    draw.text((width // 2, height - 25), "# UNTIL NEXT TIME", fill=(120, 120, 140, 140), font=font_footer, anchor="mm")

    bio = io.BytesIO()
    img = img.convert("RGB")
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()
