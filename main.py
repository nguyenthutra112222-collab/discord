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

bot.remove_command("help")

@bot.command(name="help")
async def help_command(ctx):

    prefix = ">"

    embed = discord.Embed(
        title="📖 TRUNG TÂM TRỢ GIÚP",
        description=(
            f"Xin chào {ctx.author.mention}!\n"
            f"Dưới đây là toàn bộ lệnh hiện có của **{bot.user.name}**."
        ),
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    # ================= KINH TẾ =================

    embed.add_field(
        name="💰 KINH TẾ",
        value=
        f"☀️ `{prefix}daily`\n"
        f"Nhận thưởng điểm danh mỗi 12 giờ.\n\n"
        f"🛒 `{prefix}shop`\n"
        f"Mua thuốc tăng sức mạnh.\n\n"
        f"⚙️ `{prefix}start`\n"
        f"Mở bảng nâng cấp Luck & Jackpot.",
        inline=False
    )

    # ================= CỜ BẠC =================

    embed.add_field(
        name="🎰 TRÒ CHƠI",
        value=
        f"🎲 `{prefix}roll <tiền>`\n"
        f"Đổ xúc xắc nhận thưởng x2 ~ x10.\n\n"
        f"🎰 `{prefix}slot <tiền>`\n"
        f"Máy quay Jackpot với nhiều cấp thưởng.\n\n"
        f"💡 Hỗ trợ:\n"
        f"`1000`, `100k`, `1m`, `all`",
        inline=False
    )

    # ================= HỒ SƠ =================

    embed.add_field(
        name="👤 HỒ SƠ",
        value=
        f"📋 `{prefix}profile`\n"
        f"Xem hồ sơ của bản thân.\n\n"
        f"👥 `{prefix}profile @user`\n"
        f"Xem hồ sơ người khác.\n\n"
        f"🏆 `{prefix}toplvl`\n"
        f"Xem BXH Level toàn server.",
        inline=False
    )

    # ================= THUỐC =================

    embed.add_field(
        name="🧪 DƯỢC PHẨM",
        value=
        "💰 X2 Cash\n"
        "→ Nhân đôi tiền thắng.\n\n"
        "🍀 X2 Luck\n"
        "→ Tăng tỷ lệ thắng.\n\n"
        "🎰 X2 Jackpot\n"
        "→ Tăng tỷ lệ nổ Jackpot.\n\n"
        "⏳ Thời gian: 15 phút.",
        inline=False
    )

    # ================= THÔNG TIN =================

    embed.add_field(
        name="🤖 HỆ THỐNG",
        value=
        f"ℹ️ `{prefix}botinfo`\n"
        f"Xem trạng thái và phiên bản bot.",
        inline=False
    )

    # ================= MẸO =================

    embed.add_field(
        name="📚 MẸO CHƠI",
        value=
        "🍀 Luck càng cao → tỷ lệ thắng càng lớn.\n"
        "🎰 Jackpot càng cao → dễ nổ hũ hơn.\n"
        "🔥 Chuỗi thắng càng dài → EXP thưởng càng nhiều.\n"
        "🧪 Kết hợp thuốc để tối đa hóa lợi nhuận.",
        inline=False
    )

    embed.set_footer(
        text=f"Yêu cầu bởi {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)
    
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

async def create_player(user_id):
    channel = bot.get_channel(DATA_CHANNEL_ID)
    data = {
        "user_id": user_id,
        "cash": 1000,
        "xp": 0,
        "level": 1,
        "luck": 1,
        "jackpot": 1,
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
        return await ctx.send(
            "🎲 **Cách dùng:**\n"
            "`>roll 1000`\n"
            "`>roll 100k`\n"
            "`>roll all`"
        )

    try:
        bet_amount = parse_bet_amount(bet, player["cash"])
    except:
        return await ctx.send("❌ Số tiền cược không hợp lệ!")

    if bet_amount <= 0:
        return await ctx.send("❌ Tiền cược phải lớn hơn 0!")

    if player["cash"] < bet_amount:
        return await ctx.send(f"❌ Bạn chỉ còn **{player['cash']:,} Cash**")

    # Trừ tiền đặt cược trước
    player["cash"] -= bet_amount

    now = datetime.now(timezone.utc)

    # ================= THUỐC (KIỂM TRA THỜI GIAN) =================
    has_cash_potion = bool(
        player.get("expire_potion_cash")
        and now < datetime.fromisoformat(player["expire_potion_cash"])
    )

    has_luck_potion = bool(
        player.get("expire_potion_luck")
        and now < datetime.fromisoformat(player["expire_potion_luck"])
    )

    has_jackpot_potion = bool(
        player.get("expire_potion_jackpot")
        and now < datetime.fromisoformat(player["expire_potion_jackpot"])
    )

    # ================= CHỈ SỐ GỐC =================
    luck = player.get("luck", 1)
    jackpot = player.get("jackpot", 1)

    # Nếu có thuốc hoạt động -> Tiến hành nhân đôi chỉ số
    if has_luck_potion:
        luck *= 2

    if has_jackpot_potion:
        jackpot *= 2

    # ================= TỶ LỆ HỆ THỐNG =================
    jackpot_rate = 2 + (jackpot * 0.2)
    win_rate = 45 + (luck * 0.5)

    # Bảo hiểm người nghèo trợ vốn tân thủ
    if player["cash"] <= 1000:
        win_rate += 15

    # Giới hạn mốc trần tỷ lệ tối đa (Anti-bug chỉ số quá cao)
    jackpot_rate = min(jackpot_rate, 25)
    win_rate = min(win_rate, 80)

    # Thiết lập phân đoạn tỷ lệ nối đuôi độc lập
    jackpot_limit = jackpot_rate
    win_limit = jackpot_limit + win_rate

    # ================= HIỆU ỨNG ANIMATION =================
    msg = await ctx.send("🎲 Đang lắc xúc xắc...")

    frames = [
        "🎲 ⚪⚪⚪",
        "🎲 🔴⚪⚪",
        "🎲 🔴🔴⚪",
        "🎲 🔴🔴🔴"
    ]

    for frame in frames:
        await asyncio.sleep(0.5)
        await msg.edit(content=frame)

    # Quay số ngẫu nhiên từ 0 đến 100
    rng = random.uniform(0, 100)

    potion_text = ""
    if has_cash_potion:
        potion_text = "\n✨ *Thuốc x2 Cash đang hoạt động*"

    # ================= XỬ LÝ PHÂN ĐOẠN PHẦN THƯỞNG =================

    # 1. TRÚNG JACKPOT (Từ 0 -> jackpot_limit)
    if rng <= jackpot_limit:
        reward = bet_amount * 10

        if has_cash_potion:
            reward *= 2
    
        player["cash"] += reward
        player["win_streak"] += 1

        bonus_xp = 0
        if player["win_streak"] >= 3:
            bonus_xp = player["win_streak"] * 5
    
        total_xp = 25 + bonus_xp
        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} đã xuất sắc thăng lên Level {player['level']}!")

        return await msg.edit(
            content=
            f"💥 **JACKPOT** 💥\n\n"
            f"🎉 {ctx.author.mention}\n"
            f"💰 +{reward:,} Cash\n"
            f"✨ +{total_xp} EXP\n"
            f"🔥 Chuỗi thắng: {player['win_streak']}"
            f"{potion_text}"
        )

    # 2. TRÚNG THẮNG THƯỜNG (Từ jackpot_limit -> win_limit)
    elif rng <= win_limit:
        multiplier = random.choice([2.0, 2.5, 3.0])
        reward = int(bet_amount * multiplier)

        if has_cash_potion:
            reward *= 2

        player["cash"] += reward
        player["win_streak"] += 1

        bonus_xp = 0
        if player["win_streak"] >= 3:
            bonus_xp = player["win_streak"] * 5
    
        total_xp = 20 + bonus_xp
        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} đã xuất sắc thăng lên Level {player['level']}!")

        return await msg.edit(
            content=
            f"🎉 **THẮNG!**\n\n"
            f"🎲 Hệ số: x{multiplier}\n"
            f"💰 +{reward:,} Cash\n"
            f"✨ +{total_xp} EXP\n"
            f"🔥 Chuỗi thắng: {player['win_streak']}"
            f"{potion_text}"
        )

    # 3. THUA CUỘC (Các số còn lại lớn hơn win_limit)
    else:
        player["win_streak"] = 0

        if player["cash"] < 100:
            player["cash"] = 100  # Bảo hiểm tài khoản tránh phá sản

        leveled_up = add_xp(player, 15)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} đã xuất sắc thăng lên Level {player['level']}!")
    
        return await msg.edit(
            content=
            f"💀 **THUA CUỘC!**\n\n"
            f"💸 -{bet_amount:,} Cash tiền cược.\n"
            f"📉 Chuỗi thắng đã bị bẻ gãy!"
        )

@roll.error
async def roll_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("🎲 Cách dùng: `>roll <số tiền>`\nVí dụ: `>roll 1000`")

@bot.command()
async def slot(ctx, bet: str = None):
    player = await get_player(ctx.author.id)

    if bet is None:
        return await ctx.send(
            "🎰 **Cách dùng:**\n"
            "`>slot <số_tiền>`\n"
            "`>slot all`"
        )

    try:
        bet_amount = parse_bet_amount(bet, player["cash"])
    except:
        return await ctx.send("❌ Số tiền cược không hợp lệ!")

    if bet_amount <= 0:
        return await ctx.send("❌ Số tiền đặt cược phải lớn hơn 0!")

    if player["cash"] < bet_amount:
        return await ctx.send(f"❌ Bạn chỉ còn **{player['cash']:,} Cash**")

    # Trừ tiền đặt cược trước
    player["cash"] -= bet_amount

    # ================= THUỐC (KIỂM TRA THỜI GIAN) =================
    now = datetime.now(timezone.utc)

    has_potion_cash = bool(
        player.get("expire_potion_cash")
        and now < datetime.fromisoformat(player["expire_potion_cash"])
    )

    has_potion_luck = bool(
        player.get("expire_potion_luck")
        and now < datetime.fromisoformat(player["expire_potion_luck"])
    )

    has_potion_jackpot = bool(
        player.get("expire_potion_jackpot")
        and now < datetime.fromisoformat(player["expire_potion_jackpot"])
    )

    luck_val = player.get("luck", 1)
    jackpot_val = player.get("jackpot", 1)

    # Tính toán tính năng X2 từ dược phẩm bổ trợ
    if has_potion_luck:
        luck_val *= 2

    if has_potion_jackpot:
        jackpot_val *= 2

    # ================= TỶ LỆ MỚI =================
    # Jackpot chỉ ảnh hưởng jackpot
    jackpot_rate = min(1 + (jackpot_val * 0.3), 25)
    
    # Luck chỉ ảnh hưởng các loại thắng thường
    luck_rate = min(20 + luck_val, 70)
    
    if player["cash"] <= 1000:
        luck_rate += 10
    
    luck_rate = min(luck_rate, 70)
    
    # Phân chia các loại thắng
    super_win_rate = luck_rate * 0.15
    big_win_rate = luck_rate * 0.35
    normal_win_rate = luck_rate * 0.50
    
    jackpot_limit = jackpot_rate
    sieu_thang_limit = jackpot_limit + super_win_rate
    thang_lon_limit = sieu_thang_limit + big_win_rate
    thang_thuong_limit = thang_lon_limit + normal_win_rate

    # ================= ANIMATION VÒNG QUAY (ĐÃ TỐI ƯU CHỐNG RATE LIMIT) =================
    emojis = ["🍒", "🍋", "🍇", "💎", "⭐"]
    msg = await ctx.send("🎰 **[ 🟢 STARTING ]** Đang khởi động trục quay...")

    # Chỉ chạy 3 khung hình chuyển động giả lập lăn bánh để triệt tiêu hoàn toàn delay API
    frames = [
        f"🎰 | {random.choice(emojis)} | {random.choice(emojis)} | {random.choice(emojis)} |\n🎰 | 🔄 | 🔄 | 🔄 |",
        f"🎰 | 🔄 | 🔄 | 🔄 |\n🎰 | {random.choice(emojis)} | {random.choice(emojis)} | {random.choice(emojis)} |",
        f"🎰 | {random.choice(emojis)} | {random.choice(emojis)} | {random.choice(emojis)} |\n🎰 | ⚡ | ⚡ | ⚡ |"
    ]

    for frame in frames:
        await msg.edit(content=frame)
        await asyncio.sleep(0.4) # Thời gian nghỉ lý tưởng giữa các khung hình

    # Quay số ngẫu nhiên xác định kết quả
    rng = random.uniform(0, 100)

    potion_notice = ""
    if has_potion_cash: potion_notice += "\n✨ *Thuốc X2 Cash đang hoạt động*"
    if has_potion_luck: potion_notice += "\n🍀 *Thuốc X2 Luck đang hoạt động*"
    if has_potion_jackpot: potion_notice += "\n💎 *Thuốc X2 Jackpot đang hoạt động*"

    # ================= 1. XỬ LÝ JACKPOT (x30) =================
    if rng <= jackpot_limit:
        reward = bet_amount * 30
        if has_potion_cash:
            reward *= 2

        player["cash"] += reward
        player["win_streak"] += 1

        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = 40 + bonus_xp
        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} lên Level {player['level']}!")

        return await msg.edit(
            content=
            f"💥💥 **JACKPOT TRÚNG LỚN** 💥💥\n"
            f"🎰 | ⭐ | ⭐ | ⭐ |\n\n"
            f"💰 +{reward:,} Cash\n"
            f"✨ +{total_xp} EXP\n"
            f"🔥 Chuỗi thắng: {player['win_streak']}"
            f"{potion_notice}"
        )

    # ================= 2. XỬ LÝ SIÊU THẮNG (x15) =================
    elif rng <= sieu_thang_limit:
        reward = bet_amount * 15
        if has_potion_cash:
            reward *= 2

        player["cash"] += reward
        player["win_streak"] += 1

        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = 25 + bonus_xp
        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} lên Level {player['level']}!")

        return await msg.edit(
            content=
            f"💎 **SIÊU THẮNG** 💎\n"
            f"🎰 | 💎 | 💎 | 💎 |\n\n"
            f"💰 +{reward:,} Cash\n"
            f"✨ +{total_xp} EXP\n"
            f"🔥 Chuỗi thắng: {player['win_streak']}"
            f"{potion_notice}"
        )

    # ================= 3. XỬ LÝ THẮNG LỚN (x6) =================
    elif rng <= thang_lon_limit:
        reward = bet_amount * 6
        if has_potion_cash:
            reward *= 2

        player["cash"] += reward
        player["win_streak"] += 1

        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = 15 + bonus_xp
        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} lên Level {player['level']}!")

        return await msg.edit(
            content=
            f"🎉 **THẮNG LỚN!**\n"
            f"🎰 | 🍒 | 🍒 | 🍒 |\n\n"
            f"💰 +{reward:,} Cash\n"
            f"✨ +{total_xp} EXP\n"
            f"🔥 Chuỗi thắng: {player['win_streak']}"
            f"{potion_notice}"
        )

    # ================= 4. XỬ LÝ THẮNG THƯỜNG (x2) =================
    elif rng <= thang_thuong_limit:
        reward = bet_amount * 2
        if has_potion_cash:
            reward *= 2

        player["cash"] += reward
        player["win_streak"] += 1

        bonus_xp = player["win_streak"] * 5 if player["win_streak"] >= 3 else 0
        total_xp = 10 + bonus_xp
        leveled_up = add_xp(player, total_xp)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} lên Level {player['level']}!")

        return await msg.edit(
            content=
            f"✨ **THẮNG!**\n"
            f"🎰 | 🍋 | 🍋 | 🍋 |\n\n"
            f"💰 +{reward:,} Cash\n"
            f"✨ +{total_xp} EXP\n"
            f"🔥 Chuỗi thắng: {player['win_streak']}"
            f"{potion_notice}"
        )

    # ================= 5. XỬ LÝ THUA CUỘC =================
    else:
        while True:
            result = random.choices(emojis, k=3)
            if not (result[0] == result[1] == result[2]):
                break

        player["win_streak"] = 0

        if player["cash"] < 100:
            player["cash"] = 100  

        leveled_up = add_xp(player, 10)
        await save_player(player)

        if leveled_up:
            await ctx.send(f"🎉 {ctx.author.mention} lên Level {player['level']}!")

        return await msg.edit(
            content=
            f"💀 **THUA CUỘC!**\n"
            f"🎰 | {result[0]} | {result[1]} | {result[2]} |\n\n"
            f"💸 -{bet_amount:,} Cash tiền cược.\n"
            f"📉 Chuỗi thắng đã bị reset vế 0."
        )
        
# ===== CÁC LỆNH HIỂN THỊ & ADMIN =====
# Hàm tính số tiền cần để nâng cấp (Cấp càng cao càng tốn tiền)
def get_upgrade_cost(current_level):
    return (current_level + 1) * 1000

class UpgradeView(discord.ui.View):
    def __init__(self):
        # timeout=None để nút bấm hoạt động vĩnh viễn (Persistent View) khi bot restart
        super().__init__(timeout=None)

    @discord.ui.button(label="🍀 Nâng Cấp Luck", style=discord.ButtonStyle.primary, custom_id="btn_upgrade_luck")
    async def upgrade_luck(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await get_player(interaction.user.id)
        current_luck = player.get("luck", 1)
        cost = get_upgrade_cost(current_luck)

        if player["cash"] < cost:
            return await interaction.response.send_message(
                f"❌ Bạn không đủ tiền! Nâng lên Luck cấp {current_luck + 1} cần **{cost:,} Cash**.", 
                ephemeral=True
            )

        # Trừ tiền và tăng chỉ số
        player["cash"] -= cost
        player["luck"] = current_luck + 1
        await save_player(player)

        # Cập nhật lại giao diện (Embed mới sau khi nâng cấp) mới tinh, thông minh hơn
        embed = create_start_embed(interaction.user, player)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎰 Nâng Cấp Jackpot", style=discord.ButtonStyle.danger, custom_id="btn_upgrade_jackpot")
    async def upgrade_jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await get_player(interaction.user.id)
        current_jackpot = player.get("jackpot", 1)
        cost = get_upgrade_cost(current_jackpot)

        if player["cash"] < cost:
            return await interaction.response.send_message(
                f"❌ Bạn không đủ tiền! Nâng lên Jackpot cấp {current_jackpot + 1} cần **{cost:,} Cash**.", 
                ephemeral=True
            )

        # Trừ tiền và tăng chỉ số
        player["cash"] -= cost
        player["jackpot"] = current_jackpot + 1
        await save_player(player)

        # Cập nhật lại giao diện (Embed mới sau khi nâng cấp) mới tinh, thông minh hơn
        embed = create_start_embed(interaction.user, player)
        await interaction.response.edit_message(embed=embed, view=self)

# Hàm tạo giao diện Embed dùng chung để tối ưu hóa việc cập nhật dữ liệu tự động
def create_start_embed(user, player):
    luck_lvl = player.get("luck", 1)
    jackpot_lvl = player.get("jackpot", 1)
    
    cost_luck = get_upgrade_cost(luck_lvl)
    cost_jackpot = get_upgrade_cost(jackpot_lvl)

    embed = discord.Embed(
        title="⚙️ BẢNG NÂNG CẤP CHỈ SỐ LỚN", 
        description="Sử dụng số Cash tích lũy để gia tăng tỷ lệ chiến thắng vĩnh viễn!",
        color=discord.Color.gold()
    )
    embed.set_author(name=str(user), icon_url=user.display_avatar.url)
    
    # Chỉ hiển thị duy nhất số Cash tài sản của bản thân
    embed.add_field(name="💰 Tài Sản Hiện Có", value=f"**{player['cash']:,} Cash**", inline=False)
    
    # Hiển thị 2 chỉ số Luck và Jackpot kèm chi phí thông minh
    embed.add_field(
        name="🍀 Chỉ số Luck hiện tại", 
        value=f"• Cấp hiện tại: `{luck_lvl}`\n• Chi phí lên cấp tiếp theo: **{cost_luck:,} Cash**", 
        inline=True
    )
    embed.add_field(
        name="🎰 Chỉ số Jackpot hiện tại", 
        value=f"• Cấp hiện tại: `{jackpot_lvl}`\n• Chi phí lên cấp tiếp theo: **{cost_jackpot:,} Cash**", 
        inline=True
    )
    
    embed.set_footer(text="Nhấn vào các nút bên dưới để tiến hành gia tăng sức mạnh!")
    return embed


@bot.command()
async def start(ctx):
    """Lệnh start mở bảng hiển thị tài sản và nâng cấp chỉ số"""
    player = await get_player(ctx.author.id)
    
    # Gọi hàm tạo embed thông minh
    embed = create_start_embed(ctx.author, player)
    
    # Gửi kèm View chứa 2 nút bấm vừa được khôi phục
    await ctx.send(embed=embed, view=UpgradeView())
    
#Profile----------------------------------------------------------------------

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

    @discord.ui.button(label="Dùng X2 Cash", style=discord.ButtonStyle.success, custom_id="use_cash")
    async def use_cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.use_potion(interaction, "potion_cash", "Thuốc X2 Cash")

    @discord.ui.button(label="Dùng x2 Luck", style=discord.ButtonStyle.primary, custom_id="use_luck")
    async def use_luck(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.use_potion(interaction, "potion_luck", "Thuốc x2 Luck")

    @discord.ui.button(label="Dùng x2 Jackpot", style=discord.ButtonStyle.danger, custom_id="use_jackpot")
    async def use_jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.use_potion(interaction, "potion_jackpot", "Thuốc x2 Jackpot")

async def make_profile_embed(member, player):
    need_xp = player["level"] * 100
    now = datetime.now(timezone.utc)

    status_potions = []
    # Đổi text nhãn ở đây thành X2
    for p_type, label in [("potion_cash", "X2 Cash"), ("potion_luck", "X2 Luck"), ("potion_jackpot", "X2 Jackpot")]:
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
    player.setdefault("luck", 1)
    player.setdefault("jackpot", 1)
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
    player["luck"] = 1
    player["jackpot"] = 1
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

# ================= HỆ THỐNG SHOP VẬT PHẨM X2 =================
PRICES = {
    "potion_cash": 5000,       
    "potion_luck": 3000,       
    "potion_jackpot": 6000     
}

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.children[0].label = f"🧪 Thuốc X2 Cash ({PRICES['potion_cash']:,})"
        self.children[1].label = f"🧪 Thuốc X2 Luck ({PRICES['potion_luck']:,})"
        self.children[2].label = f"🧪 Thuốc X2 Jackpot ({PRICES['potion_jackpot']:,})"

    async def buy_potion(self, interaction: discord.Interaction, potion_type: str, price: int, name: str):
        player = await get_player(interaction.user.id)
        if player.get("cash", 1000) < price:
            return await interaction.response.send_message(f"❌ Bạn không đủ tiền! Cần **{price:,} Cash** để mua {name}.", ephemeral=True)
            
        player["cash"] -= price
        db_key = f"inv_{potion_type}"
        player[db_key] = player.get(db_key, 0) + 1
        await save_player(player)
        await interaction.response.send_message(f"🛒 Bạn đã mua thành công 1 bình **{name}**! Gõ `>profile` để sử dụng.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.success, custom_id="shop_buy_cash")
    async def buy_cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_potion(interaction, "potion_cash", PRICES["potion_cash"], "Thuốc X2 Cash (15p)")

    @discord.ui.button(style=discord.ButtonStyle.primary, custom_id="shop_buy_luck")
    async def buy_luck(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_potion(interaction, "potion_luck", PRICES["potion_luck"], "Thuốc X2 Luck (15p)")

    @discord.ui.button(style=discord.ButtonStyle.danger, custom_id="shop_buy_jackpot")
    async def buy_jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_potion(interaction, "potion_jackpot", PRICES["potion_jackpot"], "Thuốc X2 Jackpot (15p)")

@bot.command()
async def shop(ctx):
    """Mở cửa hàng mua thuốc tăng chỉ số"""
    embed = discord.Embed(
        title="🧪 TIỆM THUỐC ĐẠI GIA - SHOP VẬT PHẨM X2",
        description="Mua thuốc tăng sức mạnh để nhân đôi tỷ lệ chiến thắng khi chơi game!\n*Lưu ý: Tất cả các loại thuốc đều có tác dụng trong **15 phút** kể từ lúc sử dụng.*",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Thuốc X2 Cash", value=f"• Giá: `{PRICES['potion_cash']:,} Cash`\n• Tác dụng: Nhân đôi số tiền nhận được khi thắng Roll / Slot.", inline=False)
    embed.add_field(name="🍀 Thuốc X2 Luck", value=f"• Giá: `{PRICES['potion_luck']:,} Cash`\n• Tác dụng: Nhân đôi chỉ số May Mắn (Luck) hiện có khi tính tỷ lệ thắng.", inline=False)
    embed.add_field(name="🎰 Thuốc X2 Jackpot", value=f"• Giá: `{PRICES['potion_jackpot']:,} Cash`\n• Tác dụng: Nhân đôi chỉ số Jackpot hiện có khi tính tỷ lệ nổ hũ.", inline=False)
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
    
    activity = discord.Game(name=">help")
    await bot.change_presence(status=discord.Status.idle, activity=activity)

    print(f"📂 Đã tải {len(player_cache)} người chơi vào hệ thống Cache.")

if token is None:
    print("❌ Lỗi: Không tìm thấy biến TOKEN trong file .env!")
else:
    print("✅ Đang khởi chạy Bot bằng TOKEN tìm thấy...")
    bot.run(token)
