import os
import discord
from discord.ext import commands
import firebase_admin
from firebase_admin import credentials, firestore
import json

# ---------------------------------------------------------
# Firebase 接続（Render / ローカル両対応）
# ---------------------------------------------------------

firebase_json = os.getenv("FIREBASE_CREDENTIALS")

if firebase_json:
    try:
        cred_dict = json.loads(firebase_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("Firebase initialized from environment variable.")
    except Exception as e:
        print("Firebase JSON 読み込みエラー:", e)
        raise
else:
    print("FIREBASE_CREDENTIALS が設定されていません。")
    raise ValueError("Firebase credentials missing.")

db = firestore.client()

# ---------------------------------------------------------
# Discord Bot 設定
# ---------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# トーン（性格）
# ---------------------------------------------------------

TONE_CHOICES = {
    "1": "gentle_female",
    "2": "bright_girl",
    "3": "cheerful_friend",  # ← 修正済（気さくで快活な女子）
    "4": "cool_girl",
    "5": "strict_female",
    "6": "calm_male"
}

TONE_LABELS = {
    "gentle_female": "やさしい女性",
    "bright_girl": "明るい女の子",
    "cheerful_friend": "気さくで快活な女子",
    "cool_girl": "クールな女性",
    "strict_female": "厳しめの女性",
    "calm_male": "落ち着いた男性"
}

# ---------------------------------------------------------
# 質問内容（仕様書ベース）
# ---------------------------------------------------------

QUESTIONS = {
    "Q1": "今日の体調はどう？",
    "Q2": "睡眠時間はどれくらい？",
    "Q3": "ゲーム中に疲れは感じた？",
    "Q4": "今の気分を一言で教えて！"
}

# ---------------------------------------------------------
# トーン別フィードバック（1行に最適化）
# ---------------------------------------------------------

FEEDBACK = {
    "gentle_female": "無理しないでね。ゆっくり休んで体を大事にしようね。",
    "bright_girl": "よしよし！今できる範囲で元気取り戻そっ！",
    "cheerful_friend": "なるほどね！じゃあ無理しすぎず行こ！",
    "cool_girl": "了解。状態を客観的にみて次に備えよう。",
    "strict_female": "体調管理も実力のうちよ。しっかり整えて。",
    "calm_male": "ふむ、落ち着いて整えていこう。焦らずにね。"
}

# ---------------------------------------------------------
# Firestore 操作
# ---------------------------------------------------------

COLLECTION_NAME = "user_health"

def get_user_state(user_id):
    ref = db.collection(COLLECTION_NAME).document(str(user_id))
    doc = ref.get()
    return doc.to_dict() if doc.exists else None

def set_user_state(user_id, data):
    ref = db.collection(COLLECTION_NAME).document(str(user_id))
    ref.set(data, merge=True)

# ---------------------------------------------------------
# トリガー判定
# ---------------------------------------------------------

TRIGGER_WORDS = ["体調チェック", "たいちょう", "check"]
CHANGE_TONE_WORDS = ["トーン変更", "性格変更", "キャラ変更"]

def contains(text, words):
    return any(w in text for w in words)

# ---------------------------------------------------------
# DM：初回ガイド
# ---------------------------------------------------------

GUIDE_TEXT = """\
こんにちは！私はあなたの“ゲーム健康サポート相棒”です。

【使い方】
・「体調チェック」 と送ると健康チェックを開始します
・最初だけ“相棒の性格（トーン）”を選んでもらいます
・途中で変えたいときは「トーン変更」と送ってね！

それでは、準備ができたら「体調チェック」と送ってね！
"""

# ---------------------------------------------------------
# チャット応答メイン
# ---------------------------------------------------------

user_session = {}  # Q の進行管理

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    content = message.content

    # ---------------------------
    # トーン変更コマンド
    # ---------------------------
    if contains(content, CHANGE_TONE_WORDS):
        await message.channel.send("新しいトーンを選んでください：\n1. やさしい女性\n2. 明るい女の子\n3. 気さくで快活な女子\n4. クールな女性\n5. 厳しめ女性\n6. 落ち着いた男性")
        user_session[message.author.id] = {"mode": "choose_tone"}
        return

    # ---------------------------
    # 体調チェックトリガー
    # ---------------------------
    if contains(content, TRIGGER_WORDS):

        # 初回ガイド DM
        if not get_user_state(message.author.id):
            try:
                await message.author.send(GUIDE_TEXT)
            except:
                pass  # DM 拒否時は無視

        # トーン未選択
        state = get_user_state(message.author.id)
        if not state or "tone" not in state:
            await message.channel.send("相棒の性格を選んでください：\n1. やさしい女性\n2. 明るい女の子\n3. 気さくで快活な女子\n4. クールな女性\n5. 厳しめ女性\n6. 落ち着いた男性")
            user_session[message.author.id] = {"mode": "choose_tone"}
            return

        # 通常チェック開始
        user_session[message.author.id] = {"mode": "Q1"}
        await message.channel.send("Q1: " + QUESTIONS["Q1"])
        return

    # ---------------------------
    # セッション進行（Q1〜Q4）
    # ---------------------------
    if message.author.id in user_session:
        session = user_session[message.author.id]

        # トーン選択中
        if session["mode"] == "choose_tone":
            if content not in TONE_CHOICES:
                await message.channel.send("1〜6 の番号で選んでください！")
                return
            tone = TONE_CHOICES[content]
            set_user_state(message.author.id, {"tone": tone})
            await message.channel.send(f"了解、あなたの相棒は **{TONE_LABELS[tone]}** だよ！")
            del user_session[message.author.id]
            return

        # 質問進行
        if session["mode"] in ["Q1", "Q2", "Q3", "Q4"]:
            current_q = session["mode"]
            set_user_state(message.author.id, {current_q: content})

            if current_q == "Q4":
                # 完了 → フィードバック
                user_state = get_user_state(message.author.id)
                tone = user_state.get("tone", "gentle_female")
                reply = FEEDBACK[tone]
                await message.channel.send(reply)
                del user_session[message.author.id]
                return

            # 次の質問
            next_q = "Q" + str(int(current_q[1]) + 1)
            user_session[message.author.id]["mode"] = next_q
            await message.channel.send(f"{next_q}: {QUESTIONS[next_q]}")
            return

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
