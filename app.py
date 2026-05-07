import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
import re
import time
import random
import asyncio

TOKEN = "OTU4MTkyMDQyNTcwMjkzMjg4.GRsQFc.Fi8mcHslTZ8DfmWIAQAygHOxZvErxB0TK-8iqM"
CHZZK_FILE = "chzzk_data.json"
GUILD_ID = 1462439713725091930
CHANNEL_ID = 1462439714958348322
YOUR_USER_ID = 736565395300941854
GAME_CHANNEL_ID = [1473548428654022780, 1472541708385517588, 1472989035688624241, 1413796307746685039]
LOBBY_CHANNEL_ID = [1472946193783853178, 1413796307746685039]
DATA_FILE = "data.json"
COOLDOWN = 60 * 60 * 3 
RACE_CHANNEL_ID = [1472936183523835925, 1472989272389714052, 1413796307746685039]
BLACKJACK_CHANNEL_ID = 1473316758004699157
typing_cooldowns = {}
TYPING_COOLDOWN = 1800

blackjack_games = {}

def draw_card():
    return random.choice([2,3,4,5,6,7,8,9,10,10,10,10,11])

def calculate_total(hand):
    total = sum(hand)
    while total > 21 and 11 in hand:
        hand[hand.index(11)] = 1
        total = sum(hand)
    return total

class BlackjackView(discord.ui.View):
    def __init__(self, ctx, game_data):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.game_data = game_data

    async def interaction_check(self, interaction: discord.Interaction):
        # 본인만 누를 수 있음
        return interaction.user.id == self.ctx.author.id

    @discord.ui.button(label="히트", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(self.ctx.author.id)
        user = get_user(user_id)

        self.game_data["player"].append(draw_card())
        total = calculate_total(self.game_data["player"])
        
        if total > 21:
            user["gold"] -= self.game_data["bet"]
            save_data()
        embed = discord.Embed( title="💥 버스트!", description=f"합: {total}\n❌ 패배 (-{self.game_data['bet']} 골드)", color=discord.Color.red() )
        embed.add_field(name="💰 현재 골드", value=user["gold"])
        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)
        return

        embed = discord.Embed(
            title="🃏 블랙잭 진행중",
            color=discord.Color.green()
        )
        embed.add_field(
            name="👤 당신",
            value=f"{self.game_data['player']} (합 {total})",
            inline=False
        )
        embed.add_field(
            name="🤖 딜러",
            value=f"[{self.game_data['dealer'][0]}, ?]",
            inline=False
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="스탠드", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(self.ctx.author.id)
        user = get_user(user_id)

        player_total = calculate_total(self.game_data["player"])
        dealer_total = calculate_total(self.game_data["dealer"])

        while dealer_total < 17:
            self.game_data["dealer"].append(draw_card())
            dealer_total = calculate_total(self.game_data["dealer"])


        if dealer_total > 21 or player_total > dealer_total:
            reward = int(self.game_data["bet"] * 2.5)
            user["gold"] += reward
            result = f"🎉 승리했습니다! 2.5배인 +{reward} 골드를 드릴게요"
            color = discord.Color.blue()
        elif player_total < dealer_total:
            result = f"❌ 패배! (-{self.game_data['bet']} 골드)"
            color = discord.Color.red()
        else:
            reward = int(self.game_data["bet"] * 1)  # 원금 반환
            result = f"🤝 무승부! +{reward} 골드 반환"
            color = discord.Color.gold()
            

        save_data()

        embed = discord.Embed(
            title="🃏 게임 결과",
            description=result,
            color=color
        )

        embed.add_field(
            name="🤖 딜러",
            value=f"{self.game_data['dealer']} (합 {dealer_total})",
            inline=False
        )

        embed.add_field(
            name="👤 당신",
            value=f"{self.game_data['player']} (합 {player_total})",
            inline=False
        )

        embed.add_field(
            name="💰 현재 골드",
            value=user["gold"],
            inline=False
        )

        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)


horses = ["썬더볼트", "블랙윈드", "골드러쉬", "레드스톰"]
track_length = 20
def check_lobby_channel(ctx):
    if ctx.channel.id != LOBBY_CHANNEL_ID:
        embed = discord.Embed(
            title="🚫 사용 불가 채널",
            description="🎰 해당 명령어는 도박장 로비에서만 사용 가능합니다.",
            color=0xFF5555
        )
        return embed
    return None

users = {} 

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)


# ----------------------------
# 저장 / 로드
# ----------------------------

# 🔹 유저 데이터 로드
def load_data():
    if not os.path.isfile("users.json"):
        return {}

    try:
        with open("users.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_data():
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

# ----------------------------
# 숲 저장 / 로드
# ----------------------------
        
# ----------------------------
# 치지직 저장 / 로드
# ----------------------------
def load_chzzk():
    default_data = {
        "notify_channel_id": None,
        "streamers": {},
        "live_state": {}
    }

    if not os.path.exists(CHZZK_FILE):
        return default_data

    try:
        with open(CHZZK_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        for key in default_data:
            if key not in loaded:
                loaded[key] = default_data[key]

        return loaded

    except (json.JSONDecodeError, FileNotFoundError):
        return default_data

# 🔹 치지직 데이터 저장
def save_chzzk(d):
    with open(CHZZK_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


# 🔥 실제 데이터 불러오기 (전역 초기화)
users = load_data()
chzzk_data = load_chzzk()


# ----------------------------
# 기타 유틸
# ----------------------------

def extract_channel_id(url_or_id: str):
    url_or_id = url_or_id.strip()
    if "chzzk.naver.com" in url_or_id:
        return url_or_id.split("/")[-1]
    return url_or_id

# 🔹 유저 정보 가져오기
def get_user(user_id):
    user_id = str(user_id)

    if user_id not in users:
        users[user_id] = {
            "gold": 0,
            "last_claim": 0
        }
        save_data()

    # 🔥 기존 유저인데 last_claim 없는 경우 보정
    if "last_claim" not in users[user_id]:
        users[user_id]["last_claim"] = 0
        save_data()
        
    if "compensation" not in users[user_id]:
        users[user_id]["compensation"] = False

    return users[user_id]

def board_to_string(board):
    return "\n".join(" ".join(row) for row in board)
# ----------------------------
# 숲 라이브 체크 (v2 API)
# ----------------------------

# ----------------------------
# 치지직 라이브 체크 (v2 API)
# ----------------------------
async def get_chzzk_channel_name(channel_id: str):
    api_url = f"https://api.chzzk.naver.com/service/v1/channels/{channel_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://chzzk.naver.com/",
        "Origin": "https://chzzk.naver.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(api_url) as resp:
                if resp.status != 200:
                    return None

                data_json = await resp.json()

        content = data_json.get("content")
        if not content:
            return None

        return content.get("channelName")

    except:
        return None


async def check_chzzk_live(channel_id: str):
    """
    반환: (is_live, title, url, thumbnail, raw)
    """
    page_url = f"https://chzzk.naver.com/{channel_id}"
    api_url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": page_url,
        "Origin": "https://chzzk.naver.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Connection": "keep-alive",
    }

    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(api_url) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    return False, None, page_url, None, f"API_HTTP {resp.status}\n{text[:200]}"

                data_json = await resp.json()

        content = data_json.get("content")
        if content is None:
            return False, None, page_url, None, "NO_CONTENT"

        # status: OPEN이면 방송중
        status = content.get("status")
        is_live = (status == "OPEN")

        title = content.get("liveTitle")
        thumbnail = content.get("liveImageUrl") or content.get("thumbnailUrl")

        return is_live, title, page_url, thumbnail, f"API_OK status={status}"

    except Exception as e:
        return False, None, page_url, None, f"ERROR: {e}"

async def send_live_notification(channel_id, title, url, thumbnail):
    global chzzk_data

    notify_channel_id = chzzk_data.get("notify_channel_id")
    if not notify_channel_id:
        return

    channel = bot.get_channel(int(notify_channel_id))
    if not channel:
        return

    streamer_name = chzzk_data["streamers"].get(channel_id, {}).get("name", channel_id)

    embed = discord.Embed(
        title=f"📢 {streamer_name} 님이 방송을 시작했습니다!",
        description=f"**{title or '방송 중!'}**\n\n🔗 {url}",
        color=0x00ff99
    )

    if thumbnail:
        embed.set_image(url=thumbnail)

    await channel.send(embed=embed)

# ----------------------------
# 자동 체크 루프
# ----------------------------
@tasks.loop(seconds=60)
async def live_check_loop():
    global chzzk_data  # 전역 변수를 사용하겠다고 명시

    if not chzzk_data.get("notify_channel_id"):
        return

    streamers = list(chzzk_data.get("streamers", {}).keys())
    if not streamers:
        return

    for channel_id in streamers:
        is_live, title, url, thumbnail, raw = await check_chzzk_live(channel_id)
        print(f"[치지직 체크] {channel_id} live={is_live} raw={raw}")

        last_state = chzzk_data["live_state"].get(channel_id, False)

        if is_live and not last_state:
            await send_live_notification(channel_id, title, url, thumbnail)

        # 상태 업데이트
        chzzk_data["live_state"][channel_id] = is_live
    
    # 루프 한 주기가 끝나면 저장
    save_chzzk(chzzk_data)

# ==========================
# 숲
# ==========================

# ==========================
# 🎰 슬롯 설정
# ==========================
# 기호 설정 (별 제외, 보물/6 추가)
SYMBOLS = ["🍒", "🍋", "🔔", "💎", "7️⃣", "🍀", "🧰", "6️⃣"]

# 💰 기호별 추가 보너스 금액
SYMBOL_BONUS = {
    "🍒": 500, "🍋": 500, "🔔": 8500, "🍀": 8500,
    "🧰": 25000, "💎": 25000, "7️⃣": 77777, "6️⃣": 0
}

# 📈 모든 패턴 설정 (이름, 배율, 확률-확률은 생성시 참고용)
# 📈 패턴 배율 설정 (리스트 대신 딕셔너리로 교체 필수!)
PATTERNS_DATA = {
    "가로": 2.0,
    "세로": 2.0,
    "대각선": 2.0,
    "가로 - L": 3.0,
    "가로 - XL": 3.5,
    "지그": 4.5,
    "재그": 4.5,
    "지상": 5.0,
    "천상": 5.0,
    "눈": 6.6,
    "잭팟": 777,
    "666": 0
}


def check_all_wins(board):
    wins = []
    # 1. 가로 (XL, L, horizontal)
    for r in range(3):
        row = board[r]
        if len(set(row)) == 1: wins.append(("가로 - XL", row[0])) # [0] 추가해서 문자열로 추출
        elif len(set(row[0:4])) == 1: wins.append(("가로 - L", row[0]))
        elif len(set(row[1:5])) == 1: wins.append(("가로 - L", row[1]))
        else:
            for c in range(3):
                if len(set(row[c:c+3])) == 1:
                    wins.append(("가로", row[c]))
                    break
    # 2. 세로 (vertical)
    for c in range(5):
        col = [board[r][c] for r in range(3)]
        if len(set(col)) == 1: wins.append(("세로", col[0])) # [0] 추가
    # 3. 대각선 (diagonal)
    for r in range(1):
        for c in range(5):
            if c + 2 < 5 and board[r][c] == board[r+1][c+1] == board[r+2][c+2]:
                wins.append(("대각선", board[r][c]))
            if c - 2 >= 0 and board[r][c] == board[r+1][c-1] == board[r+2][c-2]:
                wins.append(("대각선", board[r][c]))
    # 4. 특수 패턴
    specials = {
        "지그": [(0,2),(1,1),(1,3),(2,0),(2,4)], "재그": [(0,0),(0,4),(1,1),(1,3),(2,2)],
        "지상": [(0,2),(1,1),(1,3),(2,0),(2,1),(2,2),(2,3),(2,4)],
        "천상": [(2,2),(1,1),(1,3),(0,0),(0,1),(0,2),(0,3),(0,4)],
        "눈": [(0,1),(0,2),(0,3),(1,0),(1,1),(1,3),(1,4),(2,1),(2,2),(2,3)],
        "잭팟": [(r,c) for r in range(3) for c in range(5)]
    }
    for p_name, coords in specials.items():
        syms = [board[r][c] for r, c in coords]
        if len(set(syms)) == 1: wins.append((p_name, syms[0])) # [0] 추가
    return wins

def board_to_string(board):
    return "\n".join(" ".join(row) for row in board)

# ----------------------------
# 이벤트
# ----------------------------
@bot.event
async def on_ready():
    print(f"✅ 로그인 완료: {bot.user}")
    if not live_check_loop.is_running():
        live_check_loop.start()
        print("✅ live_check_loop 시작됨!")

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"❌ 오류: {error}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # DM인지 확인 + 특정 유저만 허용
    if isinstance(message.channel, discord.DMChannel) and message.author.id == YOUR_USER_ID:
        guild = bot.get_guild(GUILD_ID)
        channel = guild.get_channel(CHANNEL_ID)

        if channel:
            # 텍스트 전송
            if message.content:
                await channel.send(message.content)

            # 파일/이미지 전송
            if message.attachments:
                files = []
                for attachment in message.attachments:
                    file = await attachment.to_file()
                    files.append(file)

                await channel.send(files=files)

    await bot.process_commands(message)


# ----------------------------
# 명령어
# ----------------------------

@bot.command()
@commands.has_permissions(manage_messages=True)
async def 청소(ctx, amount: int = 10):
    if amount < 1:
        return await ctx.send("❌ 1개 이상 입력해줘!")

    if amount > 100:
        return await ctx.send("❌ 한 번에 최대 100개까지만 삭제 가능해!")

    # amount + 1 = 명령어(.청소 ...) 메시지도 같이 삭제
    deleted = await ctx.channel.purge(limit=amount + 1)

    # 삭제 완료 안내 메시지 (3초 후 자동 삭제)
    msg = await ctx.send(f"🧹 {len(deleted)-1}개 메시지 삭제 완료!")
    await msg.delete(delay=3)

@bot.command()
async def 치지직알림채널(ctx, channel_arg: str):
    global chzzk_data # 전역 변수 사용 명시
    channel_arg = channel_arg.replace("\u2060", "").strip()

    match = re.match(r"<#(\d+)>", channel_arg)
    if match:
        channel_id = int(match.group(1))
    else:
        if not channel_arg.isdigit():
            return await ctx.send("❌ 채널 멘션(#채널) 또는 채널 ID 숫자만 입력해줘!")
        channel_id = int(channel_arg)

    channel = bot.get_channel(channel_id)
    if channel is None:
        return await ctx.send("❌ 채널을 찾을 수 없어요. 같은 서버 채널인지 확인해줘!")

    # 수정: chzzk_data에 저장 및 save_chzzk 호출
    chzzk_data["notify_channel_id"] = channel.id
    save_chzzk(chzzk_data)
    await ctx.send(f"✅ 치지직 알림 채널이 <#{channel.id}> 로 설정되었습니다!")

@bot.command()
async def 치지직등록(ctx, url_or_id: str, *, display_name: str = None):
    global chzzk_data
    channel_id = extract_channel_id(url_or_id)

    if display_name is None:
        await ctx.send("🔎 치지직 채널명 가져오는 중...")
        channel_name = await get_chzzk_channel_name(channel_id)
        display_name = channel_name if channel_name else channel_id

    # 수정: chzzk_data 구조에 맞게 저장
    chzzk_data["streamers"][channel_id] = {"name": display_name}
    chzzk_data["live_state"][channel_id] = False
    save_chzzk(chzzk_data)

    await ctx.send(
        "✅ 등록 완료!\n"
        f"- 채널ID: `{channel_id}`\n"
        f"- 표시이름: `{display_name}`"
    )

@bot.command()
async def 치지직삭제(ctx, url_or_id: str):
    global chzzk_data
    channel_id = extract_channel_id(url_or_id)

    if channel_id in chzzk_data["streamers"]:
        del chzzk_data["streamers"][channel_id]
        chzzk_data["live_state"].pop(channel_id, None)
        save_chzzk(chzzk_data)
        await ctx.send(f"🗑️ 삭제 완료: `{channel_id}`")
    else:
        await ctx.send("❌ 등록되지 않은 스트리머입니다.")

@bot.command()
async def 치지직목록(ctx):
    # 전역 chzzk_data 사용
    streamers = chzzk_data.get("streamers", {})
    if not streamers:
        return await ctx.send("📭 등록된 스트리머가 없습니다.")

    msg = "📌 등록된 스트리머 목록:\n"
    for cid, info in streamers.items():
        msg += f"- {info.get('name', cid)} (`{cid}`)\n"

    await ctx.send(msg)

@bot.command()
async def 치지직체크(ctx, url_or_id: str):
    # 이 명령어는 조회용이라 저장로직 수정 불필요
    await ctx.send("🔎 치지직 체크 시작...")
    channel_id = extract_channel_id(url_or_id)
    is_live, title, url, thumbnail, raw = await check_chzzk_live(channel_id)

    await ctx.send(
        "✅ 체크 결과\n"
        f"방송중: `{is_live}`\n"
        f"제목: `{title}`\n"
        f"URL: {url}\n"
        f"썸네일: {thumbnail}\n"
        f"RAW: ```{raw}```"
    )

    
@bot.command(name="도움")
async def 도움(ctx):

    embed = discord.Embed(
        title="✨ 게임 시스템 도움말",
        description="아래 명령어를 사용해보세요!",
        color=0x00FFCC
    )

    embed.add_field(
        name="송금",
        value="다른 사람에게 멘션으로 송금 가능하며 1원이상 가능",
        inline=False
    )

    embed.add_field(
        name="잔액",
        value="현재 본인과 멘션으로 다른 사람의 골드 확인",
        inline=False
    )

    embed.add_field(
        name="랭킹",
        value="서버 부자 순위 top 10",
        inline=False
    )

    embed.add_field(
        name="돈벌기",
        value="돈을 벌어보자",
        inline=False
    )

    embed.add_field(
        name="게임",
        value="도박 게임 리스트",
        inline=False
    )

    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_footer(text="💡 명령어는 지정 채널에서만 사용 가능합니다.")

    await ctx.send(embed=embed)

@bot.command(name="돈벌기")
async def 돈벌기(ctx):

    embed = discord.Embed(
        title="✨ 게임 시스템 도움말",
        description="아래 명령어를 사용해보세요!",
        color=0x00FFCC
    )

    embed.add_field(
        name="돈받기",
        value="3시간마다 50,000G 지급",
        inline=False
    )

    embed.add_field(
        name="명언타자",
        value="30초 안에 치면 10000 골드\n20초 안에 치면 20000 골드\n10초 안에 치면 30000 골드\n5초 안에 치면 50000 골드이며 30분마다 가능합니다",
        inline=False
    )

    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_footer(text="💡 명령어는 지정 채널에서만 사용 가능합니다.")

    await ctx.send(embed=embed)

@bot.command(name="게임")
async def 게임(ctx):

    embed = discord.Embed(
        title="✨ 게임 시스템 도움말",
        description="아래 명령어를 사용해보세요!",
        color=0x00FFCC
    )

    embed.add_field(
        name="슬롯",
        value="배팅금액은 1원 이상부터 가능이며 확률표는 [여기](<https://docs.google.com/document/d/1DdyI1nAR2gOW7C0ty_oy9gwQjB-1PoYB9vMDRMinrdQ/edit?usp=sharing>)에 있습니다",
        inline=False
    )

    embed.add_field(
        name="경마",
        value="배팅금액은 1원 이상부터 가능이며\n1번말 썬더볼트\n2번말 블랙윈드\n3번말 골드러쉬\n4번말 레드스톰\n이렇게 있으며 성공하시면 배팅 금액의 10배를 얻습니다\n 하는법은 .경마 말번호(숫자만) 배팅금액 입니다 ",
        inline=False
    )
    embed.add_field(
        name="블랙잭",
        value="카드 합을 21에 가깝게 만들되 초과하지 마세요.\n 히트 → 카드 1장 추가\n스탠드 → 멈추기\n딜러보다 높으면 승리\n21 초과 시 패배\n같으면 무승부\n승리 시 2.5배"
    )

    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_footer(text="💡 명령어는 지정 채널에서만 사용 가능합니다.")

    await ctx.send(embed=embed)

# ==========================
# 💰 수급
# ==========================
@bot.command()
async def 돈받기(ctx):
    if ctx.channel.id not in LOBBY_CHANNEL_ID:
        return

    user = get_user(ctx.author.id)

    user = get_user(ctx.author.id)
    now = time.time()

    if now - user["last_claim"] < COOLDOWN:

        remaining = int(COOLDOWN - (now - user["last_claim"]))

        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60

        embed = discord.Embed(
            title="⏳ 수급 대기 중",
            color=0xFF5555
        )

        embed.add_field(
            name="남은 시간",
            value=f"🕒 {hours}시간 {minutes}분 {seconds}초",
            inline=False
        )

        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        return await ctx.send(embed=embed)

    user["gold"] += 50000
    user["last_claim"] = now
    save_data()

    embed = discord.Embed(
        title="💰 수급 완료!",
        color=0x00FF99
    )

    embed.add_field(name="획득 금액", value="✨ 50,000G", inline=True)
    embed.add_field(name="현재 잔액", value=f"🏦 {user['gold']:,}G", inline=True)

    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command()
async def 명언타자(ctx):
    if ctx.channel.id not in LOBBY_CHANNEL_ID:
        return

    user = get_user(ctx.author.id)

    user_id = str(ctx.author.id)
    now = time.time()

    # 🔒 쿨타임 체크
    if user_id in typing_cooldowns:
        remaining = int(TYPING_COOLDOWN - (now - typing_cooldowns[user_id]))
        if remaining > 0:
            minutes = remaining // 60
            seconds = remaining % 60
            return await ctx.send(
                f"⏳ 아직 쿨타임입니다.\n남은 시간: {minutes}분 {seconds}초"
            )

    # ✍ 랜덤 긴 문장 리스트
    sentences = [
        "동해 물과 백두산이 마르고 닳도록 하느님이 보우하사 우리나라 만세",
        "격언은 결코 새로운 이야기는 아니지만 항상 위안을 준다",
        "배우면서 생각하지 않으면 이득이 없고, 생각하되 배움이 없으면 위험하다",
        "신은 지식 그 자체를 인간에게 주지 않고 지식의 씨앗을 우리에게 주었다",
        "힘에 있어서 신과 같아지려고 한 천사는 법을 어기고 떨어졌고, 지식에 있어서 신과 같아지려고 한 인간은 법을 깨고 떨어졌다",
        "우리가 알았고 알고 알게 될 모든 지식은 우리가 절대 알지 못할 것에 비하면 아무것도 아니다",
        "지식욕은 보편적인 것을 추구할 때는 학구심이라 불리고, 개별적인 것을 추구할 때는 호기심이라 불린다",
        "나는 보았다, 알았다, 믿었다, 눈을 떴다",
        "내가 아는 모든 것은 아무 것도 모른다는 것이다",
        "진정으로 웃으려면 고통을 참아야하며 , 나아가 고통을 즐길 줄 알아야 해",
        "성공의 비결은 단 한 가지, 잘할 수 있는 일에 광적으로 집중하는 것이다",
        "만약 우리가 할 수 있는 일을 모두 한다면 우리들은 우리자신에 깜짝 놀랄 것이다",
        "모든것들에는 나름의 경이로움과 심지어 어둠과 침묵이 있고 , 내가 어떤 상태에 있더라도 나는 그속에서 만족하는 법을 배운다",
        "직접 눈으로 본 일도 오히려 참인지 아닌지 염려스러운데 더구나 등뒤에서 남이 말하는 것이야 어찌 이것을 깊이 믿을 수 있으랴",
        "이미끝나버린 일을 후회하기 보다는 하고 싶었던 일들을 하지못한 것을 후회하라",
        "되찾을 수 없는게 세월이니 시시한 일에 시간을 낭비하지 말고 순간순간을 후회 없이 잘 살아야 한다",
        "우리는 두려움의 홍수에 버티기 위해서 끊임없이 용기의 둑을 쌓아야 한다",
        "네 자신의 불행을 생각하지 않게 되는 가장 좋은 방법은 일에 몰두하는 것이다",
        "인생을 다시 산다면 다음번에는 더 많은 실수를 저지르리라",
    ]

    sentence = random.choice(sentences)

    embed = discord.Embed(
        title="⌨️ 타자 속도 도전!",
        description=f"아래 문장을 정확히 입력하세요!\n\n```{sentence}```\n⏱ 제한 시간: 30초",
        color=0x00C3FF
    )

    await ctx.send(embed=embed)

    start_time = time.time()

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", timeout=30, check=check)
    except asyncio.TimeoutError:
        return await ctx.send("❌ 30초 초과! 실패!")

    end_time = time.time()
    elapsed = end_time - start_time

    if msg.content != sentence:
        return await ctx.send("❌ 문장이 정확하지 않습니다!")

    # 💰 보상 계산
    reward = 0

    if elapsed <= 5:
        reward = 50000
    elif elapsed <= 10:
        reward = 30000
    elif elapsed <= 20:
        reward = 20000
    elif elapsed <= 30:
        reward = 10000

    if reward == 0:
        return await ctx.send("❌ 시간 초과!")

    users[user_id]["gold"] += reward
    typing_cooldowns[user_id] = time.time()
    save_data()

    result_embed = discord.Embed(
        title=f"🎉 {ctx.author.display_name}님의 타자 성공!",
        color=0x00FF99
    )

    result_embed.add_field(
        name="⏱ 기록",
        value=f"{elapsed:.2f}초",
        inline=False
    )

    result_embed.add_field(
        name="💰 획득 골드",
        value=f"{reward:,}G",
        inline=False
    )

    result_embed.add_field(
        name="🏦 현재 잔액",
        value=f"{users[user_id]['gold']:,}G",
        inline=False
    )

    await ctx.send(embed=result_embed)


@bot.command()
async def 잔액(ctx, member: discord.Member = None):
    if ctx.channel.id not in LOBBY_CHANNEL_ID:
        return

    user = get_user(ctx.author.id)

    target = member or ctx.author
    user = get_user(target.id)

    embed = discord.Embed(
        title="🏦 골드 잔액 조회",
        color=0xFFD700
    )

    embed.add_field(
        name="유저",
        value=target.mention,
        inline=False
    )

    embed.add_field(
        name="현재 보유 골드",
        value=f"💰 {user['gold']:,}G",
        inline=False
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def 송금(ctx, member: discord.Member, amount: int):
    if ctx.channel.id not in LOBBY_CHANNEL_ID:
        return

    user = get_user(ctx.author.id)

    if ctx.author.id == member.id:
        return await ctx.send("❌ 자기 자신에게는 송금 불가")

    if amount <= 0:
        return await ctx.send("❌ 1G 이상만 가능")

    sender = get_user(ctx.author.id)
    receiver = get_user(member.id)

    if sender["gold"] < amount:
        return await ctx.send("❌ 잔액 부족")

    sender["gold"] -= amount
    receiver["gold"] += amount
    save_data()

    embed = discord.Embed(
        title="💸 골드 송금 완료",
        color=0x00C3FF
    )

    embed.add_field(
        name="보낸 사람",
        value=f"{ctx.author.mention}\n잔액: {sender['gold']:,}G",
        inline=True
    )

    embed.add_field(
        name="받은 사람",
        value=f"{member.mention}\n잔액: {receiver['gold']:,}G",
        inline=True
    )

    embed.add_field(
        name="송금 금액",
        value=f"✨ {amount:,}G",
        inline=False
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command()
async def 랭킹(ctx):
    if ctx.channel.id not in LOBBY_CHANNEL_ID:
        return

    user = get_user(ctx.author.id)

    if not users:
        return await ctx.send("📭 데이터 없음")

    ranking_list = []

    for user_id, info in users.items():
        gold = info.get("gold", 0)

        member = ctx.guild.get_member(int(user_id))

        # 🔥 캐시 없을 경우 fetch로 다시 시도
        if not member:
            try:
                member = await ctx.guild.fetch_member(int(user_id))
            except:
                continue  # 🔥 서버에 없는 유저는 랭킹 제외

        ranking_list.append((member.display_name, gold))

    if not ranking_list:
        return await ctx.send("📭 표시할 유저가 없습니다.")

    # 정렬
    ranking_list.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 서버 골드 랭킹 TOP 10",
        color=0xFFD700
    )

    for i, (name, gold) in enumerate(ranking_list[:10], start=1):
        embed.add_field(
            name=f"{i}위 - {name}",
            value=f"{gold:,}G",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command()
async def 슬롯(ctx, bet: int):
    if ctx.channel.id not in GAME_CHANNEL_ID:
        return

    user = get_user(ctx.author.id)

    if bet <= 0:
        return await ctx.send("❌ 올바른 배팅 금액을 입력해줘!")

    if user["gold"] < bet:
        return await ctx.send(f"❌ 잔액 부족! (보유: {user['gold']:,}G)")

    user["gold"] -= bet
    save_data()

    # 🎰 심볼 가중치
    weighted_symbols = (
        ["🍒"]*20 + ["🍋"]*19 + ["🔔"]*15 +
        ["🍀"]*15 + ["💎"]*12 + ["🧰"]*12 +
        ["7️⃣"]* 7
    )

    # 1️⃣ 결과 생성
    final_board = [[random.choice(weighted_symbols) for _ in range(5)] for _ in range(3)]

    # 2️⃣ 🔥 6️⃣ 위치 보정 (중앙 가로 3칸만 허용)
    allowed_positions = [(1,1), (1,2), (1,3)]

    # 기존 6 제거
    for r in range(3):
        for c in range(5):
            if final_board[r][c] == "6️⃣":
                final_board[r][c] = random.choice(weighted_symbols)

    # 확률적으로 6 생성
    six_count = random.choices([0,1,2,3], weights=[73,15,10,2])[0]
    random.shuffle(allowed_positions)

    for i in range(six_count):
        r, c = allowed_positions[i]
        final_board[r][c] = "6️⃣"

    # 3️⃣ 애니메이션 시작
    display_board = [["⬛" for _ in range(5)] for _ in range(3)]

    embed = discord.Embed(title="🎰 슬롯 머신 돌아가는 중...", color=0xFFAA00)
    embed.add_field(
        name="[ RESULT ]",
        value=f"```\n{board_to_string(display_board)}\n```",
        inline=False
    )
    embed.set_footer(text=f"👤 {ctx.author.display_name} | 배팅금: {bet:,}G")

    msg = await ctx.send(embed=embed)

    # 🎞 릴 순차 정지
    for c in range(5):
        for _ in range(4):
            for r in range(3):
                display_board[r][c] = random.choice(weighted_symbols)
            embed.set_field_at(
                0,
                name="[ RESULT ]",
                value=f"```\n{board_to_string(display_board)}\n```",
                inline=False
            )
            await msg.edit(embed=embed)
            await asyncio.sleep(0.08)

        # 최종 값 고정
        for r in range(3):
            display_board[r][c] = final_board[r][c]

        embed.set_field_at(
            0,
            name="[ RESULT ]",
            value=f"```\n{board_to_string(display_board)}\n```",
            inline=False
        )
        await msg.edit(embed=embed)

        # 마지막 릴 + 666일 경우 느리게
        if c == 4 and final_board[1][1:4] == ["6️⃣","6️⃣","6️⃣"]:
            await asyncio.sleep(0.8)
        else:
            await asyncio.sleep(0.2)

    # 4️⃣ 💀 666 벌칙 체크
    if final_board[1][1] == "6️⃣" and \
       final_board[1][2] == "6️⃣" and \
       final_board[1][3] == "6️⃣":

        penalty = bet * 6
        user["gold"] -= penalty
        save_data()

        fail_embed = discord.Embed(title="💀 666!! [히히~ 내꺼~ ㅎㅎ]", color=0xFF0000)
        fail_embed.add_field(
            name="[ RESULT ]",
            value=f"```\n{board_to_string(final_board)}\n```",
            inline=False
        )
        fail_embed.add_field(name="💸 벌금", value=f"-{penalty:,} G", inline=True)
        fail_embed.add_field(name="🏦 현재 잔액", value=f"{user['gold']:,} G", inline=True)

        return await msg.edit(embed=fail_embed)

    # 5️⃣ 일반 패턴 검사
    all_wins = check_all_wins(final_board)
    total_win = 0
    match_list = []

    for p_name, s_icon in all_wins:
        bonus = SYMBOL_BONUS.get(s_icon, 0)
        mult = PATTERNS_DATA.get(p_name, 1.0)

        win_amount = int((bet + bonus) * mult)
        total_win += win_amount
        match_list.append(f"✨ {s_icon} {p_name} (+{win_amount:,}G)")

    # 6️⃣ 결과 처리
    if total_win > 0:
        user["gold"] += total_win
        save_data()

        win_embed = discord.Embed(title="🎉 당첨!", color=0x00FF00)
        win_embed.add_field(
            name="[ RESULT ]",
            value=f"```\n{board_to_string(final_board)}\n```",
            inline=False
        )
        win_embed.add_field(
            name="📊 당첨 내역",
            value="\n".join(match_list),
            inline=False
        )
        win_embed.add_field(name="💰 획득 금액", value=f"+{total_win:,} G", inline=True)
        win_embed.add_field(name="🏦 현재 잔액", value=f"{user['gold']:,} G", inline=True)

        await msg.edit(embed=win_embed)

    else:
        lose_embed = discord.Embed(title="💀 꽝!", color=0x444444)
        lose_embed.add_field(
            name="[ RESULT ]",
            value=f"```\n{board_to_string(final_board)}\n```",
            inline=False
        )
        lose_embed.add_field(
            name="🏦 현재 잔액",
            value=f"{user['gold']:,} G",
            inline=False
        )

        await msg.edit(embed=lose_embed)

@bot.command()
async def 경마(ctx, horse_number: int, amount: int):
    if ctx.channel.id not in RACE_CHANNEL_ID:
        return

    user = get_user(ctx.author.id)

    horses = ["썬더볼트", "블랙윈드", "골드러쉬", "레드스톰"]
    track_length = 30

    if horse_number < 1 or horse_number > len(horses):
        return await ctx.send("❌ 잘못된 말 번호입니다.")

    if amount <= 0:
        return await ctx.send("❌ 금액은 0보다 커야 합니다.")

    user_id = str(ctx.author.id)

    if user_id not in users:
        return await ctx.send("❌ 먼저 출석 또는 골드 명령어를 사용하세요.")

    if users[user_id]["gold"] < amount:
        return await ctx.send("❌ 골드가 부족합니다.")

    # 💰 골드 차감
    users[user_id]["gold"] -= amount

    start_embed = discord.Embed(
        title="🐎 경마 시작!",
        description=f"{ctx.author.display_name}님이 "
                    f"**{horses[horse_number-1]}**에 {amount:,}G 베팅했습니다!",
        color=0x00ff99
    )

    race_message = await ctx.send(embed=start_embed)

    positions = [0] * len(horses)

    # 🏁 레이스 진행
    while True:
        await asyncio.sleep(1)

        for i in range(len(horses)):
            positions[i] += random.randint(0, 2)

        race_embed = discord.Embed(
            title="🏁 경주 중...",
            color=0x3498db
        )

        for i, pos in enumerate(positions):
            bar = "─" * pos + "🐎"
            race_embed.add_field(
                name=horses[i],
                value=bar,
                inline=False
            )

        await race_message.edit(embed=race_embed)

        for i, pos in enumerate(positions):
            if pos >= track_length:
                winner = i
                break
        else:
            continue
        break

    await asyncio.sleep(1)

    result_embed = discord.Embed(
        title=f"🏆 {ctx.author.display_name}님의 경마 결과",
        description=f"우승 말: 🐎 **{horses[winner]}**",
        color=0xff0000
    )

    # 🎯 결과 처리
    if winner == horse_number - 1:
        winnings = amount * 10
        users[user_id]["gold"] += winnings
        result_embed.add_field(
            name="🎉 승리!",
            value=f"{winnings:,}G 획득!",
            inline=False
        )
    else:
        result_embed.add_field(
            name="💸 패배",
            value="베팅 실패",
            inline=False
        )

    result_embed.set_footer(
        text=f"현재 보유 골드: {users[user_id]['gold']:,}G"
    )

    await ctx.send(embed=result_embed)
#---------------------------
#블랙잭
#---------------------------

@bot.command()
async def 블랙잭(ctx, amount: int = 0):

    if ctx.channel.id != BLACKJACK_CHANNEL_ID:
        return

    user = get_user(ctx.author.id)

    if amount <= 0:
        await ctx.send("❌ 베팅 금액 오류")
        return

    if user["gold"] < amount:
        await ctx.send("❌ 골드 부족")
        return

    # 🔥 베팅금 먼저 차감
    user["gold"] -= amount
    save_data()

    player = [draw_card(), draw_card()]
    dealer = [draw_card(), draw_card()]

    embed = discord.Embed(
        title="🃏 블랙잭 시작!",
        color=discord.Color.green()
    )

    embed.add_field(
        name="👤 당신",
        value=f"{player} (합 {calculate_total(player)})",
        inline=False
    )
    embed.add_field(
        name="🤖 딜러",
        value=f"[{dealer[0]}, ?]",
        inline=False
    )

    view = BlackjackView(ctx, {
        "bet": amount,
        "player": player,
        "dealer": dealer
    })

    await ctx.send(embed=embed, view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def 골드지급(ctx, member: discord.Member, amount: int):
    if amount == 0:
        return await ctx.send("❌ 0은 지급할 수 없음")

    user = get_user(member.id)
    user["gold"] += amount
    
    save_data()  # 💡 여기서 save_users() 대신 save_data()를 호출해야 합니다!

    if amount > 0:
        await ctx.send(f"💰 {member.mention} 에게 {amount:,}G 지급 완료!")
    else:
        await ctx.send(f"💸 {member.mention} 에게서 {-amount:,}G 차감 완료!")

@bot.command()
async def 보상(ctx):

    user = get_user(ctx.author.id)

    if user["compensation"]:
        await ctx.send("❌ 이미 보상을 받았습니다.")
        return

    reward = 1000000  # ← 여기서 금액 조절

    user["gold"] += reward
    user["compensation"] = True
    save_data()

    embed = discord.Embed(
        title="🎁 운영자 보상 지급!",
        description=f"⏳ 개발 지연 보상으로 **{reward:,} 골드** 지급되었습니다!",
        color=discord.Color.green()
    )

    embed.set_footer(text="앞으로 더 재미있는 기능이 추가됩니다 😎")

    await ctx.send(embed=embed)

# ----------------------------
# 시작
# ----------------------------
data = load_data()
bot.run(TOKEN)
