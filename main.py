import random
import asyncio
import os
import json
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TOKEN")

prefix = ">"
intents = discord.Intents.all()
intents.guilds = True
intents.messages = True
intents.reactions = True

bot = commands.Bot(command_prefix=prefix, intents=intents)

# Hàm tính toán cộng EXP và xử lý Lên Cấp
def add_xp(player, amount):
    player["xp"] += amount
    leveled_up = False
    while player["xp"] >= player["level"] * 100:
        player["xp"] -= player["level"] * 100
        player["level"] += 1
        leveled_up = True
    return leveled_up

DATA_GUILD_ID = 1514179127354069053
DATA_CHANNEL_ID = 1514179128004313212
player_cache = {}

@bot.event
async def on_ready():
    bot.add_view(UpgradeView())
    bot.add_view(ShopView())
    print(f"✅ Đăng nhập thành công: {bot.user}")

    channel = bot.get_channel(DATA_CHANNEL_ID)
    if channel is None:
        print("❌ Không tìm thấy kênh dữ liệu!")
        return

    player_cache.clear()
    async for msg in channel.history(limit=None, oldest_first=True):
        try:
            data = json.loads(msg.content)
            if "user_id" not in data:
                continue
            # Chuyển đổi dữ liệu cũ nếu còn sót lose_streak sang win_streak
            if "lose_streak" in data:
                data.pop("lose_streak")
            if "win_streak" not in data:
                data["win_streak"] = 0

            data["_message_id"] = msg.id
            player_cache[data["user_id"]] = data
        except Exception as e:
            print(f"Lỗi đọc dữ liệu: {e}")

    print(f"📂 Đã tải {len(player_cache)} người chơi vào hệ thống Cache.")

async def create_player(user_id):
    channel = bot.get_channel(DATA_CHANNEL_ID)
    data = {
        "user_id": user_id,
        "cash": 1000,
        "xp": 0,
        "level": 1,
        "luck": 0,
        "jackpot": 0,
        "win_streak": 0,
        "last_daily": "",
        "inv_potion_cash": 0,
        "inv_potion_luck": 0,
        "inv_potion_jackpot": 0,
        "expire_potion_cash": "",
        "expire_potion_luck": "",
        "expire_potion_jackpot": ""
    }
    message = await channel.send(json.dumps(data))
    data["_message_id"] = message.id
    player_cache[user_id] = data
    return data

async def get_player(user_id):
    if user_id in player_cache:
        return player_cache[user_id]

    channel = bot.get_channel(DATA_CHANNEL_ID)
    async for msg in channel.history(limit=None, oldest_first=True):
        try:
            data = json.loads(msg.content)
            if data.get("user_id") == user_id:
                if "win_streak" not in data:
                    data["win_streak"] = 0
                data["_message_id"] = msg.id
                player_cache[user_id] = data
                return data
        except:
            continue
    return await create_player(user_id)

async def save_player(player):
    channel = bot.get_channel(DATA_CHANNEL_ID)
    message_id = player["_message_id"]
    message = await channel.fetch_message(message_id)
    
    save_data = dict(player)
    save_data.pop("_message_id")
    
    await message.edit(content=json.dumps(save_data))
    player_cache[player["user_id"]] = player

async def load_all_players():
    channel = bot.get_channel(DATA_CHANNEL_ID)
    player_cache.clear()
    async for msg in channel.history(limit=None, oldest_first=True):
        try:
            data = json.loads(msg.content)
            if "user_id" not in data:
                continue
            if "win_streak" not in data:
                data["win_streak"] = 0
            data["_message_id"] = msg.id
            player_cache[data["user_id"]] = data
        except:
            pass

def parse_bet_amount(val_str: str, current_cash: int) -> int:
    """Quy đổi tiền cược từ chuỗi (100k, 2m, all) thành số nguyên int cụ thể."""
    if val_str is None:
        raise ValueError("Thiếu số tiền cược.")
        
    val_str = str(val_str).strip().lower()
    
    # Nếu người dùng chọn tất tay
    if val_str == "all":
        return current_cash
        
    multipliers = {'k': 1_000, 'm': 1_000_000, 'b': 1_000_000_000}
    
    if val_str[-1] in multipliers:
        unit = val_str[-1]
        number_part = val_str[:-1]
        try:
            return int(float(number_part) * multipliers[unit])
        except ValueError:
            raise ValueError("Định dạng tiền cược không hợp lệ.")
            
    return int(float(val_str))

@bot.command()
async def roll(ctx, bet: str = None): 
    player = await get_player(ctx.author.id)
    
    if bet is None:
        return await ctx.send(f"🎲 **Cách dùng:** `>roll <số_tiền_hoặc_all>`\n*Ví dụ: `>roll 50k` hoặc `>roll all`*")
        
    try:
        bet_amount = parse_bet_amount(bet, player["cash"])
    except ValueError:
        return await ctx.send("❌ Số tiền cược không hợp lệ! Hãy nhập số hoặc chữ viết tắt (`100k`, `all`).")
        
    if bet_amount <= 0:
        return await ctx.send("❌ Số tiền đặt cược phải lớn hơn 0!")
        
    if player["cash"] < bet_amount:
        return await ctx.send(f"❌ Bạn không đủ tiền! Số dư hiện tại: **{player['cash']:,} Cash**.")

    player["cash"] -= bet_amount

    # --- KHU VỰC LOGIC CHECK THỜI GIAN THUỐC ---
    now = datetime.now(timezone.utc)
    
    # 1. Kiểm tra thuốc Luck (+10 vào win_rate)
    has_potion_luck = False
    if player.get("expire_potion_luck", ""):
        if now < datetime.fromisoformat(player["expire_potion_luck"]):
            has_potion_luck = True
            
    # 2. Kiểm tra thuốc Jackpot (+5 vào jackpot_rate)
    has_potion_jackpot = False
    if player.get("expire_potion_jackpot", ""):
        if now < datetime.fromisoformat(player["expire_potion_jackpot"]):
            has_potion_jackpot = True

    # 3. Kiểm tra thuốc x2 Cash tiền thưởng
    has_potion_cash = False
    if player.get("expire_potion_cash", ""):
        if now < datetime.fromisoformat(player["expire_potion_cash"]):
            has_potion_cash = True
    # ---------------------------------------------

    luck = player.get("luck", 0)
    jackpot = player.get("jackpot", 0)

    # Sửa Logic tách biệt hoàn toàn theo đúng ý bạn:
    win_rate = 45 + (luck * 0.5) + (10 if has_potion_luck else 0)           # Luck CHỈ tăng tỷ lệ thắng
    jackpot_rate = 2 + (jackpot * 0.2) + (5 if has_potion_jackpot else 0)   # Jackpot CHỈ tăng tỷ lệ hũ

    if player["cash"] <= 1000:
        win_rate += 15

    msg = await ctx.send("🎲 Đang lắc xúc xắc...")
    frames = ["🎲 ⚪⚪⚪", "🎲 🔴⚪⚪", "🎲 🔴🔴⚪", "🎲 🔴🔴🔴"]
    for frame in frames:
        await asyncio.sleep(0.6)
        await msg.edit(content=frame)

    roll_number = random.uniform(0, 100)

    # 1. TRÚNG JACKPOT
    if roll_number <= jackpot_rate:
        reward = bet_amount * 10
        if has_potion_cash: reward *= 2 # Áp dụng thuốc X2 nếu có
        
        player["cash"] += reward
        player["win_streak"] += 1
        
        base_xp = 25
        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = base_xp + bonus_xp
        
        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} đã xuất sắc thăng lên Level {player['level']}!")

        potion_notice = " *(✨ Thuốc x2 Cash kích hoạt)*" if has_potion_cash else ""
        streak_text = f"🔥 Chuỗi thắng: {player['win_streak']} (Bonus +{bonus_xp} EXP)" if player["win_streak"] >= 3 else ""
        return await msg.edit(
            content=f"💥 **JACKPOT** 💥{potion_notice}\n\n🎉 {ctx.author.mention}\n💰 +{reward:,} Cash\n✨ +{total_xp} EXP {streak_text}"
        )

    # 2. TRÚNG GIẢI THẮNG THƯỜNG
    elif roll_number <= win_rate:
        multiplier = random.choice([2.0, 2.5, 3.0])
        reward = int(bet_amount * multiplier)
        if has_potion_cash: reward *= 2 # Áp dụng thuốc X2 nếu có
        
        player["cash"] += reward
        player["win_streak"] += 1

        base_xp = 25
        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = base_xp + bonus_xp

        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} đã xuất sắc thăng lên Level {player['level']}!")

        potion_notice = " *(✨ Thuốc x2 Cash kích hoạt)*" if has_potion_cash else ""
        streak_text = f"🔥 Chuỗi thắng: {player['win_streak']} (Bonus +{bonus_xp} EXP)" if player["win_streak"] >= 3 else ""
        return await msg.edit(
            content=f"🎉 **THẮNG!**{potion_notice}\n\n🎲 Hệ số: x{multiplier}\n💰 +{reward:,} Cash\n✨ +{total_xp} EXP {streak_text}"
        )

    # 3. THUA CUỘC
    else:
        player["win_streak"] = 0 
        if player["cash"] < 100:
            player["cash"] = 100

        leveled_up = add_xp(player, 15)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} đã xuất sắc thăng lên Level {player['level']}!")

        return await msg.edit(
            content=f"💀 **THUA CUỘC!**\n\n💸 Bạn đã mất sạch {bet_amount:,} Cash tiền cược.\n📉 Chuỗi thắng bị bẻ gãy!"
        )

@roll.error
async def roll_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("🎲 Cách dùng: `>roll <số tiền>`\nVí dụ: `>roll 1000`")

@bot.command()
async def slot(ctx, bet: str = None):
    player = await get_player(ctx.author.id)
    
    if bet is None:
        return await ctx.send(f"🎰 **Cách dùng:** `>slot <số_tiền_hoặc_all>`\n*Ví dụ: `>slot 50k` hoặc `>slot all`*")
        
    try:
        bet_amount = parse_bet_amount(bet, player["cash"])
    except ValueError:
        return await ctx.send("❌ Số tiền cược không hợp lệ! Hãy nhập số hoặc chữ viết tắt (`100k`, `all`).")
        
    if bet_amount <= 0:
        return await ctx.send("❌ Số tiền đặt cược phải lớn hơn 0!")
        
    if player["cash"] < bet_amount:
        return await ctx.send(f"❌ Bạn không đủ tiền! Số dư hiện tại: **{player['cash']:,} Cash**.")

    player["cash"] -= bet_amount

    # --- KHU VỰC LOGIC CHECK THỜI GIAN THUỐC ---
    now = datetime.now(timezone.utc)
    
    has_potion_luck = False
    if player.get("expire_potion_luck", ""):
        if now < datetime.fromisoformat(player["expire_potion_luck"]):
            has_potion_luck = True
            
    has_potion_jackpot = False
    if player.get("expire_potion_jackpot", ""):
        if now < datetime.fromisoformat(player["expire_potion_jackpot"]):
            has_potion_jackpot = True

    has_potion_cash = False
    if player.get("expire_potion_cash", ""):
        if now < datetime.fromisoformat(player["expire_potion_cash"]):
            has_potion_cash = True
    # ---------------------------------------------

    luck = player.get("luck", 0)
    jackpot = player.get("jackpot", 0)
    
    emojis = ["🍒", "🍋", "🍇", "💎", "⭐"]
    msg = await ctx.send("🎰 Đang quay hũ...")

    for _ in range(6):
        e1, e2, e3 = random.choices(emojis, k=3)
        await msg.edit(content=f"🎰 | {e1} | {e2} | {e3} |")
        await asyncio.sleep(0.3)

    # Tách biệt tỷ lệ hoàn toàn giống Roll
    jackpot_rate = 1 + (jackpot * 0.3) + (5 if has_potion_jackpot else 0)  # Jackpot CHỈ tăng nổ hũ
    win_bonus = 0
    if player["cash"] <= 1000:
        win_bonus += 10

    # Luck chỉ bổ trợ cộng dồn vào tỷ lệ rơi các tầng thắng thường/lớn/siêu thắng
    added_luck = luck + (10 if has_potion_luck else 0)

    rng = random.uniform(0, 100)
    potion_notice = " *(✨ Thuốc x2 Cash kích hoạt)*" if has_potion_cash else ""

    # 1. ⭐⭐⭐ SLOT JACKPOT (x30)
    if rng <= jackpot_rate:
        reward = bet_amount * 30 
        if has_potion_cash: reward *= 2
        player["cash"] += reward
        player["win_streak"] += 1

        base_xp = 40
        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = base_xp + bonus_xp

        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} đã xuất sắc thăng lên Level {player['level']}!")

        streak_text = f"🔥 Chuỗi thắng: {player['win_streak']} (Bonus +{bonus_xp} EXP)" if player["win_streak"] >= 3 else ""
        return await msg.edit(
            content=f"💥 **JACKPOT TRÚNG LỚN** 💥{potion_notice}\n🎰 | ⭐ | ⭐ | ⭐ |\n\n🎲 Hệ số: x30\n💰 +{reward:,} Cash\n✨ +{total_xp} EXP {streak_text}"
        )

    # 2. 💎💎💎 SIÊU THẮNG (x15)
    elif rng <= 5 + win_bonus + added_luck:
        reward = bet_amount * 15 
        if has_potion_cash: reward *= 2
        player["cash"] += reward
        player["win_streak"] += 1

        base_xp = 25
        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = base_xp + bonus_xp

        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        streak_text = f"🔥 Chuỗi thắng: {player['win_streak']} (Bonus +{bonus_xp} EXP)" if player["win_streak"] >= 3 else ""
        return await msg.edit(
            content=f"💎 **SIÊU THẮNG** 💎{potion_notice}\n🎰 | 💎 | 💎 | 💎 |\n\n🎲 Hệ số: x15\n💰 +{reward:,} Cash\n✨ +{total_xp} EXP {streak_text}"
        )

    # 3. 🍒🍒🍒 THẮNG LỚN (x6)
    elif rng <= 15 + win_bonus + added_luck:
        reward = bet_amount * 6 
        if has_potion_cash: reward *= 2
        player["cash"] += reward
        player["win_streak"] += 1

        base_xp = 15
        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = base_xp + bonus_xp

        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        streak_text = f"🔥 Chuỗi thắng: {player['win_streak']} (Bonus +{bonus_xp} EXP)" if player["win_streak"] >= 3 else ""
        return await msg.edit(
            content=f"🎉 **THẮNG LỚN!**{potion_notice}\n🎰 | 🍒 | 🍒 | 🍒 |\n\n🎲 Hệ số: x6\n💰 +{reward:,} Cash\n✨ +{total_xp} EXP {streak_text}"
        )

    # 4. 🍋🍋🍋 THẮNG THƯỜNG (x2)
    elif rng <= 30 + win_bonus + added_luck:
        reward = bet_amount * 2 
        if has_potion_cash: reward *= 2
        player["cash"] += reward
        player["win_streak"] += 1

        base_xp = 10
        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = base_xp + bonus_xp

        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        streak_text = f"🔥 Chuỗi thắng: {player['win_streak']} (Bonus +{bonus_xp} EXP)" if player["win_streak"] >= 3 else ""
        return await msg.edit(
            content=f"✨ **THẮNG!**{potion_notice}\n🎰 | 🍋 | 🍋 | 🍋 |\n\n🎲 Hệ số: x2\n💰 +{reward:,} Cash\n✨ +{total_xp} EXP {streak_text}"
        )

    # 5. THUA CUỘC
    else:
        result = random.choices(emojis, k=3)
        player["win_streak"] = 0 
        
        if player["cash"] < 100:
            player["cash"] = 100

        leveled_up = add_xp(player, 10)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} đã xuất sắc thăng lên Level {player['level']}!")

        return await msg.edit(
            content=f"💀 **THUA CUỘC!**\n🎰 | {result[0]} | {result[1]} | {result[2]} |\n\n💸 Mất sạch {bet_amount:,} Cash.\n📉 Chuỗi thắng quay về 0."
        )

# ===== Hệ thống Nút Bấm Nâng Cấp =====
class UpgradeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🍀 Nâng Luck", style=discord.ButtonStyle.green, custom_id="upgrade_luck")
    async def upgrade_luck(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await get_player(interaction.user.id)
        cost = (player["luck"] + 1) * 1000

        if player["cash"] < cost:
            return await interaction.response.send_message(f"❌ Bạn không đủ tiền! Cần {cost:,} Cash", ephemeral=True)

        player["cash"] -= cost
        player["luck"] += 1
        await save_player(player)
        await interaction.response.send_message(f"🍀 Nâng cấp thành công! Chỉ số Luck hiện tại: {player['luck']}", ephemeral=True)

    @discord.ui.button(label="💎 Nâng Jackpot", style=discord.ButtonStyle.blurple, custom_id="upgrade_jackpot")
    async def upgrade_jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await get_player(interaction.user.id)
        cost = (player["jackpot"] + 1) * 2000

        if player["cash"] < cost:
            return await interaction.response.send_message(f"❌ Bạn không đủ tiền! Cần {cost:,} Cash", ephemeral=True)

        player["cash"] -= cost
        player["jackpot"] += 1
        await save_player(player)
        await interaction.response.send_message(f"💎 Nâng cấp thành công! Chỉ số Jackpot hiện tại: {player['jackpot']}", ephemeral=True)

# ===== CÁC LỆNH HIỂN THỊ & ADMIN =====
@bot.command()
async def start(ctx):
    player = await get_player(ctx.author.id)
    need_xp = player["level"] * 100

    embed = discord.Embed(title="🎮 THÔNG TIN NGƯỜI CHƠI", color=discord.Color.gold())
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
    embed.add_field(name="💰 Cash", value=f"{player['cash']:,}", inline=True)
    embed.add_field(name="⭐ Level", value=player["level"], inline=True)
    embed.add_field(name="📈 XP", value=f"{player['xp']}/{need_xp}", inline=True)
    embed.add_field(name="🍀 Luck", value=player["luck"], inline=True)
    embed.add_field(name="💎 Jackpot Thêm", value=player["jackpot"], inline=True)
    embed.add_field(name="🔥 Chuỗi Thắng", value=player.get("win_streak", 0), inline=True)
    embed.set_footer(text="Nhấn nút bên dưới để tiến hành gia tăng sức mạnh")

    await ctx.send(embed=embed, view=UpgradeView())

def get_rank(level):
    if level >= 100: return "👑 Huyền Thoại"
    elif level >= 75: return "💎 Đại Cao Thủ"
    elif level >= 50: return "🔥 Cao Thủ"
    elif level >= 25: return "⚔️ Chiến Binh"
    elif level >= 10: return "⭐ Kẻ Phiêu Lưu"
    return "🌱 Tân Thủ"

class UsePotionView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải kho đồ của bạn!", ephemeral=True)
            return False
        return True

    async def use_potion(self, interaction: discord.Interaction, potion_type: str, name: str):
        player = await get_player(interaction.user.id)
        inv_key = f"inv_{potion_type}"
        expire_key = f"expire_{potion_type}"
        
        if player.get(inv_key, 0) <= 0:
            return await interaction.response.send_message(f"❌ Bạn không còn bình **{name}** nào trong kho! Hãy ra `>shop` để mua.", ephemeral=True)
            
        # Trừ 1 bình trong túi
        player[inv_key] -= 1
        
        # Thiết lập thời gian hết hạn là 15 phút tính từ bây giờ
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        player[expire_key] = expire_time.isoformat()
        
        await save_player(player)
        
        # Cập nhật lại giao diện Embed Profile mới ngay lập tức
        new_embed = await make_profile_embed(interaction.user, player)
        await interaction.response.edit_message(embed=new_embed, view=self)
        await interaction.followup.send(f"🧪 Bạn đã sử dụng **{name}**! Có tác dụng trong 15 phút.", ephemeral=True)

    @discord.ui.button(label="Cắn X2 Cash", style=discord.ButtonStyle.success, custom_id="use_cash")
    async def use_cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.use_potion(interaction, "potion_cash", "Thuốc X2 Cash")

    @discord.ui.button(label="Cắn +10 Luck", style=discord.ButtonStyle.primary, custom_id="use_luck")
    async def use_luck(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.use_potion(interaction, "potion_luck", "Thuốc +10 Luck")

    @discord.ui.button(label="Cắn +5 Jackpot", style=discord.ButtonStyle.danger, custom_id="use_jackpot")
    async def use_jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.use_potion(interaction, "potion_jackpot", "Thuốc +5 Jackpot")

async def make_profile_embed(member, player):
    need_xp = player["level"] * 100
    now = datetime.now(timezone.utc)

    # Kiểm tra hạn dùng của thuốc để hiển thị tình trạng (Đang kích hoạt / Chưa dùng)
    status_potions = []
    for p_type, label in [("potion_cash", "X2 Cash"), ("potion_luck", "+10 Luck"), ("potion_jackpot", "+5 Jackpot")]:
        exp_str = player.get(f"expire_{p_type}", "")
        is_active = False
        time_left_str = ""
        if exp_str:
            exp_time = datetime.fromisoformat(exp_str)
            if now < exp_time:
                is_active = True
                remains = exp_time - now
                mins, secs = divmod(int(remains.total_seconds()), 60)
                time_left_str = f" ⏳ Còn {mins}p {secs}s"
        
        qty = player.get(f"inv_{p_type}", 0)
        status_potions.append(f"• {label}: **{qty}** bình" + (f" *(🔥 Đang bật{time_left_str})*" if is_active else ""))

    embed = discord.Embed(title=f"👤 Hồ sơ của {member.display_name}", color=discord.Color.blue())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="💰 Cash", value=f"{player['cash']:,}", inline=True)
    embed.add_field(name="🛡️ Level", value=player["level"], inline=True)
    embed.add_field(name="✨ XP", value=f"{player['xp']}/{need_xp}", inline=True)
    embed.add_field(name="🍀 Luck Gốc", value=player.get("luck", 0), inline=True)
    embed.add_field(name="🎰 Jackpot Gốc", value=player.get("jackpot", 0), inline=True)
    embed.add_field(name="🔥 Chuỗi Thắng", value=player.get("win_streak", 0), inline=True)
    embed.add_field(name="🏅 Danh hiệu", value=get_rank(player["level"]), inline=True)
    
    # Khu vực kho đồ thuốc
    embed.add_field(name="🎒 Kho Dược Phẩm (Thuốc 15p)", value="\n".join(status_potions), inline=False)
    embed.set_footer(text=f"ID Người dùng: {member.id}")
    return embed

@bot.command()
async def profile(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    if member.bot:
        return await ctx.send("❌ Không thể xem hồ sơ của hệ thống Bot.")

    player = await get_player(member.id)
    embed = await make_profile_embed(member, player)

    # Nếu tự xem bản thân -> Đính kèm nút bấm dùng thuốc
    if member.id == ctx.author.id:
        await ctx.send(embed=embed, view=UsePotionView(ctx.author.id))
    else: # Xem người khác -> Ẩn nút hoàn toàn
        await ctx.send(embed=embed)

@bot.command()
async def toplvl(ctx):
    await load_all_players()
    sorted_players = sorted(player_cache.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)

    text = ""
    for index, (user_id, data) in enumerate(sorted_players[:10], start=1):
        user = bot.get_user(int(user_id))
        name = user.name if user else f"Người chơi {user_id}"
        text += f"{index}. **{name}** (Lv.{data['level']} - 🔥 Chuỗi: {data.get('win_streak', 0)})\n"

    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG CAO THỦ (LEVEL)", description=text, color=discord.Color.gold())
    await ctx.send(embed=embed)

ADMINS = [1195361246195757118, 1335606447144173610]

@bot.command()
async def buff(ctx, stat=None, target=None, amount=None):

    if ctx.author.id not in ADMINS:
        return await ctx.send(
            "❌ Bạn không có quyền dùng lệnh này!"
        )

    if stat is None:
        return await ctx.send(
            "👑 **Cách dùng lệnh Buff Admin:**\n"
            "🔹 `>buff all @user <số_lượng>` -> Buff tất cả chỉ số cho người được tag\n"
            "🔹 `>buff <chỉ_số> @User <số_lượng>` -> Buff chỉ số cho người được tag.\n"
            "*Ví dụ: `>buff all @user 50k` hoặc `>buff luck @User 5`*"
        )

    if target is None:
        return await ctx.send(
            "❌ Vui lòng mention người chơi!"
        )

    if not ctx.message.mentions:
        return await ctx.send(
            "❌ Vui lòng mention người chơi!"
        )

    member = ctx.message.mentions[0]

    if member.bot:
        return await ctx.send(
            "❌ Không thể buff bot!"
        )

    if amount is None:
        return await ctx.send(
            "❌ Thiếu giá trị buff!"
        )

    try:
        buff_amount = parse_bet_amount(
            amount,
            0
        )
    except:
        return await ctx.send(
            "❌ Giá trị không hợp lệ!"
        )

    player = await get_player(member.id)

    # Tự thêm key nếu thiếu
    player.setdefault("cash", 1000)
    player.setdefault("xp", 0)
    player.setdefault("level", 1)
    player.setdefault("luck", 0)
    player.setdefault("jackpot", 0)
    player.setdefault("win_streak", 0)

    stat = stat.lower()

    # ================= BUFF ALL =================

    if stat == "all":

        player["cash"] += buff_amount
        player["xp"] += buff_amount
        player["level"] += buff_amount
        player["luck"] += buff_amount
        player["jackpot"] += buff_amount
        player["win_streak"] += buff_amount

        await save_player(player)

        embed = discord.Embed(
            title="👑 ADMIN BUFF ALL 👑",
            description=f"{member.mention} đã được buff toàn bộ chỉ số!",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="💰 Cash",
            value=f"+{buff_amount:,}",
            inline=True
        )

        embed.add_field(
            name="📈 XP",
            value=f"+{buff_amount:,}",
            inline=True
        )

        embed.add_field(
            name="⭐ Level",
            value=f"+{buff_amount:,}",
            inline=True
        )

        embed.add_field(
            name="🍀 Luck",
            value=f"+{buff_amount:,}",
            inline=True
        )

        embed.add_field(
            name="💎 Jackpot",
            value=f"+{buff_amount:,}",
            inline=True
        )

        embed.add_field(
            name="🔥 Lose Streak",
            value=f"+{buff_amount:,}",
            inline=True
        )

        return await ctx.send(embed=embed)

    # ================= BUFF RIÊNG =================

    valid_stats = [
        "cash",
        "xp",
        "level",
        "luck",
        "jackpot",
        "win_streak"
    ]

    if stat not in valid_stats:
        return await ctx.send(
            "❌ Chỉ số hợp lệ:\n"
            + ", ".join(valid_stats)
        )

    player[stat] += buff_amount

    if stat == "level":
        player["level"] = max(
            1,
            player["level"]
        )
    else:
        player[stat] = max(
            0,
            player[stat]
        )

    await save_player(player)

    embed = discord.Embed(
        title="🛠️ ADMIN BUFF",
        color=discord.Color.green()
    )

    embed.add_field(
        name="👤 Người nhận",
        value=member.mention,
        inline=False
    )

    embed.add_field(
        name="📊 Chỉ số",
        value=stat,
        inline=True
    )

    embed.add_field(
        name="➕ Giá trị buff",
        value=f"{buff_amount:,}",
        inline=True
    )

    embed.add_field(
        name="📈 Giá trị mới",
        value=player[stat],
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def reset(ctx, member: discord.Member = None):
    if ctx.author.id not in ADMINS:
        return await ctx.send("❌ Bạn không có quyền hạn dùng lệnh này!")

    if member is None:
        return await ctx.send("Cách dùng: `>reset @user`")

    if member.bot:
        return await ctx.send("❌ Không thể đặt lại dữ liệu của Bot!")

    player = await get_player(member.id)
    player["cash"] = 1000
    player["xp"] = 0
    player["level"] = 1
    player["luck"] = 0
    player["jackpot"] = 0
    player["win_streak"] = 0
    player["last_daily"] = ""

    await save_player(player)

    embed = discord.Embed(title="🔄 THIẾT LẬP LẠI NGƯỜI CHƠI", color=discord.Color.red())
    embed.add_field(name="👤 Đối tượng", value=member.mention, inline=False)
    embed.add_field(name="💰 Cash", value="1,000", inline=True)
    embed.add_field(name="⭐ Level", value="1", inline=True)
    embed.add_field(name="🔥 Chuỗi thắng", value="0", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    player = await get_player(ctx.author.id)
    now = datetime.now(timezone.utc)
    
    if ctx.author.id not in ADMINS:
        last_daily_str = player.get("last_daily", "")
        
        if last_daily_str:
            last_daily_time = datetime.fromisoformat(last_daily_str)
            time_passed = now - last_daily_time
            
            if time_passed < timedelta(hours=12):
                time_remaining = timedelta(hours=12) - time_passed
                hours, remainder = divmod(int(time_remaining.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                
                return await ctx.send(
                    f"❌ **{ctx.author.display_name}** ơi, bạn đã điểm danh rồi!\n"
                    f"⏳ Hãy quay lại sau: **{hours} giờ {minutes} phút {seconds} giây** nữa nhé."
                )

    daily_cash = 500  
    daily_xp = 30     
    
    player["cash"] += daily_cash
    player["last_daily"] = now.isoformat()
    
    leveled_up = add_xp(player, daily_xp)
    await save_player(player)
    
    if leveled_up:
        await ctx.send(f"🎉 {ctx.author.mention} đã xuất sắc thăng lên Level {player['level']}!")

    embed = discord.Embed(
        title="☀️ ĐIỂM DANH HÀNG NGÀY",
        description=f"Chúc mừng **{ctx.author.display_name}** đã điểm danh thành công!",
        color=discord.Color.green()
    )
    
    if ctx.author.id in ADMINS:
        embed.description += "\n👑 *(Chế độ Admin: Đã bỏ qua giới hạn 12 giờ)*"

    embed.add_field(name="💰 Tiền thưởng", value=f"+{daily_cash:,} Cash", inline=True)
    embed.add_field(name="📈 Kinh nghiệm", value=f"+{daily_xp} EXP", inline=True)
    embed.add_field(name="💳 Ví hiện tại", value=f"{player['cash']:,} Cash", inline=False)
    embed.set_footer(text="Hẹn gặp lại bạn sau 12 giờ nữa!")
    
    await ctx.send(embed=embed)

# ===== View xử lý nút bấm giật tiền của Cashrain =====
class CashRainView(discord.ui.View):
    def __init__(self, total_pool: int, max_claims: int, duration: float):
        super().__init__(timeout=duration)
        self.total_pool = total_pool
        self.max_claims = max_claims  
        self.claimed_users = {}       
        self.remaining_pool = total_pool
        
    @discord.ui.button(label="💰 GIẬT TIỀN NGAY! 💰", style=discord.ButtonStyle.success, custom_id="claim_cashrain")
    async def claim_cashrain(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        
        if user_id in self.claimed_users:
            return await interaction.response.send_message("❌ Bạn đã nhặt tiền từ cơn mưa này rồi!", ephemeral=True)
            
        if self.max_claims > 0 and len(self.claimed_users) >= self.max_claims:
            button.disabled = True
            button.label = "💸 Đã bị giật sạch!"
            button.style = discord.ButtonStyle.secondary
            await interaction.message.edit(view=self)
            return await interaction.response.send_message("😢 Ôi không! Cơn mưa tiền đã bị mọi người nhặt hết sạch rồi!", ephemeral=True)
            
        if self.max_claims == 0:
            min_pick = max(1, int(self.total_pool * 0.01))
            max_pick = max(1, int(self.total_pool * 0.05))
            cash_received = random.randint(min_pick, max_pick)
            self.remaining_pool -= cash_received
        else:
            remaining_slots = self.max_claims - len(self.claimed_users)
            if remaining_slots == 1:
                cash_received = self.remaining_pool
            else:
                max_pick = int(self.remaining_pool / remaining_slots * 1.5)
                min_pick = max(1, int(self.remaining_pool / remaining_slots * 0.5))
                cash_received = random.randint(min_pick, max_pick)
                if cash_received > self.remaining_pool:
                    cash_received = self.remaining_pool
            self.remaining_pool -= cash_received

        player = await get_player(user_id)
        player["cash"] += cash_received
        self.claimed_users[user_id] = cash_received
        await save_player(player)
        
        await interaction.response.send_message(f"🎉 Bạn đã giật được **+{cash_received:,} Cash** từ cơn mưa tiền!", ephemeral=True)
        
        if self.max_claims > 0 and len(self.claimed_users) >= self.max_claims:
            button.disabled = True
            button.label = "💸 Đã bị giật sạch!"
            button.style = discord.ButtonStyle.secondary
            
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()
            embed.description = "🌧️ **CƠN MƯA TIỀN ĐÃ KẾT THÚC!**\nToàn bộ số tiền đã được phát hết sạch!"
            
            leaderboard = ""
            sorted_claims = sorted(self.claimed_users.items(), key=lambda x: x[1], reverse=True)
            for idx, (u_id, amt) in enumerate(sorted_claims[:10], 1):
                u = bot.get_user(u_id)
                u_name = u.mention if u else f"Người chơi {u_id}"
                leaderboard += f"{idx}. {u_name}: +{amt:,} Cash\n"
            if leaderboard:
                embed.add_field(name="🏆 Top nhận thưởng lớn nhất:", value=leaderboard, inline=False)
                
            await interaction.message.edit(embed=embed, view=self)

@bot.command()
async def cashrain(ctx, total_pool: str = None, max_claims: str = None): 
    if ctx.author.id not in ADMINS:
        return await ctx.send("❌ Bạn không có thẩm quyền để tạo ra cơn mưa tiền!")
        
    if total_pool is None:
        return await ctx.send(
            "🌧️ **Cách dùng lệnh Cashrain:**\n"
            "🔹 `>cashrain <tổng_tiền>` -> **Cả Server cùng được nhận** ngẫu nhiên.\n"
            "🔹 `>cashrain <tổng_tiền> <số_người>` -> Chỉ giới hạn số lượng người nhanh tay nhất.\n"
            "*Ví dụ: `>cashrain 500k` hoặc `>cashrain 10m 5`*"
        )
        
    try:
        # ✅ Sửa đổi từ hàm không tồn tại sang hàm parse_bet_amount đã khai báo ở trên
        pool_amount = parse_bet_amount(total_pool, 0)
    except ValueError:
        return await ctx.send("❌ Định dạng số tiền tổng hũ không hợp lệ! Hãy nhập số thường hoặc viết tắt dạng `100k`, `2m`, `1.5m`...")

    if pool_amount <= 0:
        return await ctx.send("❌ Số tiền cược phải lớn hơn 0!")

    claims_limit = 0  
    if max_claims is not None:
        try:
            claims_limit = int(max_claims)
            if claims_limit <= 0:
                return await ctx.send("❌ Số lượng người nhận giới hạn phải lớn hơn 0!")
        except ValueError:
            return await ctx.send("❌ Số lượng người nhận giới hạn phải là một con số nguyên hợp lệ!")

    duration = 60.0  
    
    end_timestamp = int(datetime.now(timezone.utc).timestamp() + duration)
    countdown_tag = f"<t:{end_timestamp}:R>"

    embed = discord.Embed(
        title="🌧️💸 CƠN MƯA TIỀN TỆ ĐÃ XUẤT HIỆN! 💸🌧️",
        description=f"Admin {ctx.author.mention} đang thả một cơn mưa tiền khổng lồ vào kênh chat!\nHãy nhanh tay nhấn vào nút dưới đây để nhặt tiền!",
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 Tổng giá trị hũ tiền", value=f"**{pool_amount:,} Cash**", inline=True)
    
    if claims_limit == 0:
        embed.add_field(name="👥 Số suất nhận thưởng", value="**🌍 CẢ SERVER** (Mỗi người 1 lượt)", inline=True)
    else:
        embed.add_field(name="👥 Số suất nhận thưởng", value=f"**{claims_limit} người** nhanh tay nhất", inline=True)
        
    embed.add_field(name="⏳ Thời gian còn lại", value=f"Sự kiện sẽ kết thúc {countdown_tag}", inline=False)
    embed.set_footer(text="Hệ thống tự động chia ngẫu nhiên số tiền nhặt được!")
    
    view = CashRainView(pool_amount, claims_limit, duration)
    rain_msg = await ctx.send(content="@here 🎉 SỰ KIỆN CASHRAIN!", embed=embed, view=view)
    
    await asyncio.sleep(duration)
    
    if not view.children[0].disabled:
        view.children[0].disabled = True
        view.children[0].label = "⏰ Đã hết thời gian!"
        view.children[0].style = discord.ButtonStyle.secondary
        
        embed.color = discord.Color.dark_gray()
        embed.description = "🌧️ **CƠN MƯA TIỀN ĐÃ KẾT THÚC!**\nThời gian nhặt tiền đã khép lại."
        embed.set_field_at(2, name="⏳ Thời gian còn lại", value="🔴 **Đã hết giờ!**", inline=False)
        
        leaderboard = ""
        sorted_claims = sorted(view.claimed_users.items(), key=lambda x: x[1], reverse=True)
        for idx, (u_id, amt) in enumerate(sorted_claims[:10], 1):
            u = bot.get_user(u_id)
            u_name = u.mention if u else f"Người chơi {u_id}"
            leaderboard += f"{idx}. {u_name}: +{amt:,} Cash\n"
            
        if leaderboard:
            embed.add_field(name="🏆 Bảng vinh danh nhặt tiền (Top 10):", value=leaderboard, inline=False)
        else:
            embed.add_field(name="🏆 Kết quả:", value="Không có ai tham gia nhặt tiền trong đợt này.", inline=False)
            
        await rain_msg.edit(embed=embed, view=view)

# ================= HỆ THỐNG SHOP VẬT PHẨM MỚI =================
# Cấu hình giá tiền của từng loại thuốc tại đây
PRICES = {
    "potion_cash": 5000,       # Thuốc X2 Cash
    "potion_luck": 3000,       # Thuốc +10 Luck
    "potion_jackpot": 6000     # Thuốc +5 Jackpot
}

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Cập nhật nhãn kèm giá tiền trực quan lên nút bấm
        self.children[0].label = f"🧪 Thuốc X2 Cash ({PRICES['potion_cash']:,})"
        self.children[1].label = f"🧪 Thuốc +10 Luck ({PRICES['potion_luck']:,})"
        self.children[2].label = f"🧪 Thuốc +5 Jackpot ({PRICES['potion_jackpot']:,})"

    async def buy_potion(self, interaction: discord.Interaction, potion_type: str, price: int, name: str):
        player = await get_player(interaction.user.id)
        
        if player.get("cash", 1000) < price:
            return await interaction.response.send_message(f"❌ Bạn không đủ tiền! Cần **{price:,} Cash** để mua {name}.", ephemeral=True)
            
        player["cash"] -= price
        # Tăng số lượng trong kho đồ (mặc định bằng 0 nếu chưa có)
        db_key = f"inv_{potion_type}"
        player[db_key] = player.get(db_key, 0) + 1
        
        await save_player(player)
        await interaction.response.send_message(f"🛒 Bạn đã mua thành công 1 bình **{name}**! Gõ `>profile` để sử dụng.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.success, custom_id="shop_buy_cash")
    async def buy_cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_potion(interaction, "potion_cash", PRICES["potion_cash"], "Thuốc X2 Cash (15p)")

    @discord.ui.button(style=discord.ButtonStyle.primary, custom_id="shop_buy_luck")
    async def buy_luck(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_potion(interaction, "potion_luck", PRICES["potion_luck"], "Thuốc +10 Luck (15p)")

    @discord.ui.button(style=discord.ButtonStyle.danger, custom_id="shop_buy_jackpot")
    async def buy_jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_potion(interaction, "potion_jackpot", PRICES["potion_jackpot"], "Thuốc +5 Jackpot (15p)")

@bot.command()
async def shop(ctx):
    """Mở cửa hàng mua thuốc tăng chỉ số"""
    embed = discord.Embed(
        title="🧪 TIỆM THUỐC ĐẠI GIA - SHOP VẬT PHẨM",
        description="Mua thuốc tăng sức mạnh để tăng tỷ lệ chiến thắng khi chơi game!\n*Lưu ý: Tất cả các loại thuốc đều có tác dụng trong **15 phút** kể từ lúc sử dụng.*",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Thuốc X2 Cash", value=f"• Giá: `{PRICES['potion_cash']:,} Cash`\n• Tác dụng: Gấp đôi số tiền nhận được khi thắng Roll / Slot.", inline=False)
    embed.add_field(name="🍀 Thuốc +10 Luck", value=f"• Giá: `{PRICES['potion_luck']:,} Cash`\n• Tác dụng: Thêm thẳng `+10` điểm May Mắn vào tỷ lệ thắng.", inline=False)
    embed.add_field(name="🎰 Thuốc +5 Jackpot", value=f"• Giá: `{PRICES['potion_jackpot']:,} Cash`\n• Tác dụng: Thêm thẳng `+5` điểm vào tỷ lệ nổ hũ Jackpot.", inline=False)
    embed.set_footer(text="Nhấn các nút bấm bên dưới để mua nhanh.")
    
    await ctx.send(embed=embed, view=ShopView())

@bot.command(name="botinfo", aliases=["about", "bot"])
async def bot_info(ctx):
    """Hiển thị thông tin rút gọn và trạng thái hệ thống của Bot"""
    
    # ================= KHU VỰC CẤU HÌNH CỦA ADMIN =================
    CURRENT_UPDATE = "Update 1"  
    
    STATUS_MODE = "ERROR"    
    # STATUS_MODE = "ERROR"       # Bot đang có một số lỗi hoặc có lệnh thử nghiệm
    # STATUS_MODE = "DOWN"        # Bot đang sửa lỗi, hoạt động không tốt
    # ==============================================================

    # Logic xử lý hiển thị Trạng Thái chuẩn xác theo yêu cầu
    if STATUS_MODE == "WORKING":
        status_text = "🟢 **Working**\n*(Hệ thống ổn định, hoạt động mượt mà)*"
    elif STATUS_MODE == "ERROR":
        status_text = "🟡 **Error**\n*(Đang có vài lỗi nhỏ hoặc đang chứa lệnh thử nghiệm)*"
    else:
        status_text = "🔴 **Down**\n*(Bot đang được sửa lỗi, hoạt động không tốt)*"

    # Tạo Embed hiển thị
    embed = discord.Embed(
        title=f"🤖 BẢNG THÔNG TIN - {bot.user.name.upper()}",
        description="Báo cáo tình trạng vận hành của Bot.",
        color=discord.Color.blue()
    )
    
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)

    # 1. Các thông tin chính theo yêu cầu
    embed.add_field(name="👑 Nhà Phát Triển", value="<@1195361246195757118>", inline=True)
    embed.add_field(name="🚀 Phiên Bản", value=f"`{CURRENT_UPDATE}`", inline=True)
    embed.add_field(name="🛠️ Trạng Thái Hệ Thống", value=status_text, inline=False)
    
    embed.set_footer(text=f"Yêu cầu bởi {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)
    
#--------------------------------
AUTHORIZED_USER_ID = 1195361246195757118

@bot.command(name="servers")
async def servers(ctx):
    # Kiểm tra quyền hạn
    if ctx.author.id != AUTHORIZED_USER_ID:
        return

    # Đếm tổng số lượng server bot đang ở
    total_guilds = len(bot.guilds)
    
    if total_guilds == 0:
        await ctx.author.send("🤖 Hiện tại bot chưa tham gia vào máy chủ nào cả.")
        await ctx.message.add_reaction("✅")
        return

    # Thông báo cho bạn biết bot đang lấy link (vì tạo nhiều link có thể mất vài giây)
    await ctx.message.add_reaction("⏳")
    
    guild_list_text = []

    # Duyệt qua từng server để đếm và tạo link mời
    for index, guild in enumerate(bot.guilds, start=1):
        invite_link = "Không có quyền tạo link mời"
        
        # Tìm một kênh chữ (Text Channel) mà bot có quyền tạo link mời
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).create_instant_invite:
                try:
                    # Tạo link mời không bao giờ hết hạn (max_age=0) và không giới hạn lượt dùng (max_uses=0)
                    invite = await channel.create_invite(max_age=0, max_uses=0, reason="Lấy link mời theo yêu cầu của Admin.")
                    invite_link = invite.url
                    break # Tìm được 1 kênh tạo được link là dừng lại luôn
                except Exception:
                    continue
        
        # Gom thông tin server lại
        guild_list_text.append(f"{index}. **{guild.name}** (ID: {guild.id})\n   🔗 Link: {invite_link}")

    # Tạo nội dung tin nhắn gửi vào DM
    message_content = f"📊 **THỐNG KÊ MÁY CHỦ**\n🤖 Bot đang ở trong tổng cộng: **{total_guilds} server**\n\n"
    message_content += "\n\n".join(guild_list_text)

    try:
        # Gửi tin nhắn riêng (DM) cho bạn
        # Lưu ý: Nếu danh sách quá dài (vượt quá 2000 ký tự), đoạn code dưới đây sẽ tự động chia nhỏ để gửi không bị lỗi của Discord
        if len(message_content) > 2000:
            chunks = [message_content[i:i+1900] for i in range(0, len(message_content), 1900)]
            for chunk in chunks:
                await ctx.author.send(chunk)
        else:
            await ctx.author.send(message_content)
            
        await ctx.message.add_reaction("✅")
    except discord.Forbidden:
        await ctx.send(f"❌ Không thể gửi DM cho {ctx.author.mention}. Hãy mở quyền riêng tư nhận DM từ thành viên server.")
    except Exception as e:
        await ctx.send(f"❌ Có lỗi xảy ra: {e}")
    
if token is None:
    print("❌ Lỗi: Không tìm thấy biến TOKEN trong file .env!")
else:
    print("✅ Đang khởi chạy Bot bằng TOKEN tìm thấy...")
    bot.run(token)
