import os
import json
import discord
from discord.ext import commands
import firebase_admin
from firebase_admin import credentials, firestore

from engine.check_engine import generate_health_reply  # ← check_engine.py を利用

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
    "3": "cheerful_friend",  # 気さくで快活な女子
    "4": "cool_girl",
    "5": "strict_female",
    "6": "calm_male",
}

TONE_LABELS = {
    "gentle_female": "やさしい女性",
    "bright_girl": "明るい女の子",
    "cheerful_friend": "気さくで快活な女子",
    "cool_girl": "クールな女性",
    "strict_female": "厳しめの女性",
    "calm_male": "落ち着いた男性",
}

# ---------------------------------------------------------
# トーン別：質問テンプレ（Q1〜Q4）
#   ・ユーザーが迷わないように「回答例」を1つだけ添える
# ---------------------------------------------------------

QUESTION_TEMPLATES = {
    "gentle_female": {
        "Q1": "今日もお疲れさま。どれくらい遊んだか教えてくれる？（例：90分くらい）",
        "Q2": "いまの体調はどう？少し疲れているようなら、しっかり休んでね。（例：肩こりが少しある）",
        "Q3": "昨夜はよく眠れたかしら？睡眠はあなたの力になるものよ。（例：5時間でちょっと少なめ）",
        "Q4": "いまの気分はどう？よかったら話してくれるかしら？（例：楽しいけど少し疲れてる）",
    },
    "bright_girl": {
        "Q1": "今日どれくらいやってた？だいたいでいいよ〜！（例：2時間くらい）",
        "Q2": "体調どう？いつもどおり？それともちょっとお疲れ？（例：目が少ししょぼしょぼする）",
        "Q3": "昨日の睡眠はどんな感じ？ぐっすり？それともイマイチ？（例：あんまり眠れなかった）",
        "Q4": "いまの気分はどう？嬉しい？疲れた？なんでも言ってよ！（例：ちょっとモヤモヤしてる）",
    },
    "cheerful_friend": {
        "Q1": "今日はどれくらい遊んでたの？けっこう集中してたみたいだね。（例：3時間くらい）",
        "Q2": "体調はどう？無理しすぎてない？（例：特に問題ない）",
        "Q3": "昨日はぐっすり眠れた？睡眠は大事だからね！（例：しっかり眠れた）",
        "Q4": "今の気持ちはどう？なんでも話して！（例：少し疲れてるけど気分は悪くない）",
    },
    "cool_girl": {
        "Q1": "今日のプレイ時間を教えてくれ。おおよそでいい。（例：120分くらい）",
        "Q2": "体調はどうだ？疲れの兆候が出ていないか確認しよう。（例：腰が少し痛い）",
        "Q3": "睡眠は足りているか？眠気は集中力を奪う。（例：6時間でまあ普通）",
        "Q4": "今の気持ちはどうだ？率直に答えてくれて構わない。（例：ちょっとイライラしている）",
    },
    "strict_female": {
        "Q1": "今日は何時間プレイした？大体でも構わない。（例：4時間くらい）",
        "Q2": "体調はどうだ。不調がないかみてやろう。（例：頭が少し重い）",
        "Q3": "昨夜は眠れたか？睡眠を軽視するなよ。（例：ほとんど眠れなかった）",
        "Q4": "今の気分はどうだ？弱音でも愚痴でも付き合ってやろう。（例：なんとなく落ち込んでいる）",
    },
    "calm_male": {
        "Q1": "今日はどれくらい遊んでいたんだい？ずいぶんと楽しんでいたようだけど。（例：1時間半くらい）",
        "Q2": "体調はどうだい？少しでも違和感があるなら教えてほしい。（例：肩がこっている）",
        "Q3": "昨夜の睡眠はどうだったかな？眠りは心も体も整える大切な時間だね。（例：7時間くらいで良く眠れた）",
        "Q4": "今どんな気持ちでいるのかな？素直に話してもらえると嬉しいんだけれど。（例：そこそこ元気だけど少し不安もある）",
    },
}

# ---------------------------------------------------------
# Firestore 操作
# ---------------------------------------------------------

COLLECTION_NAME = "user_health"


def get_user_state(user_id: int):
    ref = db.collection(COLLECTION_NAME).document(str(user_id))
    doc = ref.get()
    return doc.to_dict() if doc.exists else None


def set_user_state(user_id: int, data: dict):
    ref = db.collection(COLLECTION_NAME).document(str(user_id))
    ref.set(data, merge=True)


def add_log(user_id: int, tone: str, answers: dict, reply: str):
    """
    users/{uid}/logs/{auto_id} にログ保存（簡易版）
    """
    ref = db.collection(COLLECTION_NAME).document(str(user_id)).collection("logs")
    ref.add(
        {
            "tone": tone,
            "Q1": answers.get("Q1", ""),
            "Q2": answers.get("Q2", ""),
            "Q3": answers.get("Q3", ""),
            "Q4": answers.get("Q4", ""),
            "reply": reply,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
    )

# ---------------------------------------------------------
# トリガー判定
# ---------------------------------------------------------

TRIGGER_WORDS = ["体調チェック", "たいちょう", "check"]
CHANGE_TONE_WORDS = ["トーン変更", "性格変更", "キャラ変更"]


def contains(text: str, words):
    return any(w in text for w in words)


# ---------------------------------------------------------
# DM：初回ガイド
# ---------------------------------------------------------

GUIDE_TEXT = """\
こんにちは！私はあなたのゲーム健康サポートボットだよ。

【使い方】
・「体調チェック」と送ると、ゲームの遊びすぎ・疲れすぎを一緒に確認するよ
・最初だけ“相棒の性格（トーン）”を選んでもらいます
・途中で変えたいときは「トーン変更」と送ってね！

それでは、準備ができたら「体調チェック」と送ってね！
"""

# ---------------------------------------------------------
# セッション管理（メモリ上）
# ---------------------------------------------------------

# user_session[user_id] = {
#   "mode": "choose_tone" / "Q1" / "Q2" / "Q3" / "Q4",
#   "after_tone_start_check": True/False
# }
user_session = {}

# ---------------------------------------------------------
# Bot イベント
# ---------------------------------------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):

    # Bot 自身・他 Bot は無視
    if message.author.bot:
        return

    content = message.content.strip()
    user_id = message.author.id

    # すでに Q1〜Q4 / トーン選択の会話中なら、まずセッション処理
    if user_id in user_session:
        handled = await handle_session_message(message, content, user_id)
        if handled:
            return

    # 1) トーン変更トリガー
    if contains(content, CHANGE_TONE_WORDS):
        try:
            dm = message.author
            await dm.send(
                "新しいトーンを選んでください：\n"
                "1. やさしい女性\n"
                "2. 明るい女の子\n"
                "3. 気さくで快活な女子\n"
                "4. クールな女性\n"
                "5. 厳しめの女性\n"
                "6. 落ち着いた男性"
            )
            user_session[user_id] = {
                "mode": "choose_tone",
                "after_tone_start_check": False,
            }
            if message.guild is not None:
                await message.channel.send("トーン変更の案内を DM に送ったよ！")
        except Exception as e:
            print("トーン変更 DM 送信エラー:", e)
        return

    # 2) 体調チェックトリガー
    if contains(content, TRIGGER_WORDS):

        state = get_user_state(user_id)

        # 初回ユーザー → ガイド送付
        if not state or not state.get("seen_guide"):
            try:
                await message.author.send(GUIDE_TEXT)
                set_user_state(user_id, {"seen_guide": True})
            except Exception as e:
                print("GUIDE_TEXT DM 送信エラー:", e)

        state = get_user_state(user_id)
        if not state or "tone" not in state:
            try:
                await message.author.send(
                    "体調チェックを始める前に、相棒の性格を選んでね：\n"
                    "1. やさしい女性\n"
                    "2. 明るい女の子\n"
                    "3. 気さくで快活な女子\n"
                    "4. クールな女性\n"
                    "5. 厳しめの女性\n"
                    "6. 落ち着いた男性"
                )
                user_session[user_id] = {
                    "mode": "choose_tone",
                    "after_tone_start_check": True,
                }
                if message.guild is not None:
                    await message.channel.send("相棒選びの案内を DM に送ったよ！")
            except Exception as e:
                print("トーン選択 DM 送信エラー:", e)
            return

        # トーンが既にある場合 → そのまま Q1 へ
        tone = state.get("tone", "gentle_female")
        q_text = QUESTION_TEMPLATES.get(tone, QUESTION_TEMPLATES["gentle_female"])["Q1"]

        user_session[user_id] = {"mode": "Q1"}
        try:
            await message.author.send(f"Q1：{q_text}")
            if message.guild is not None:
                await message.channel.send("体調チェックを DM に送ったよ！")
        except Exception as e:
            print("Q1 送信エラー:", e)
        return

    # その他コマンド
    await bot.process_commands(message)


# ---------------------------------------------------------
# セッションメッセージ処理
# ---------------------------------------------------------

async def handle_session_message(message: discord.Message, content: str, user_id: int) -> bool:
    """
    return True のときは on_message 側でこれ以上処理しない
    """
    session = user_session.get(user_id)
    if not session:
        return False

    mode = session.get("mode")

    # (A) トーン選択中
    if mode == "choose_tone":
        if content not in TONE_CHOICES:
            await message.author.send("1〜6 の番号で選んでください！（半角数字でOKだよ）")
            return True

        tone = TONE_CHOICES[content]
        set_user_state(user_id, {"tone": tone})
        await message.author.send(f"了解、あなたの相棒は **{TONE_LABELS[tone]}** だよ！")

        if session.get("after_tone_start_check"):
            q_text = QUESTION_TEMPLATES.get(tone, QUESTION_TEMPLATES["gentle_female"])["Q1"]
            user_session[user_id] = {"mode": "Q1"}
            await message.author.send(f"Q1：{q_text}")
        else:
            del user_session[user_id]

        return True

    # (B) Q1〜Q4 進行中
    if mode in ["Q1", "Q2", "Q3", "Q4"]:
        set_user_state(user_id, {mode: content})

        if mode == "Q4":
            user_state = get_user_state(user_id) or {}
            tone = user_state.get("tone", "gentle_female")

            answers = {
                "Q1": user_state.get("Q1", ""),
                "Q2": user_state.get("Q2", ""),
                "Q3": user_state.get("Q3", ""),
                "Q4": user_state.get("Q4", ""),
            }

            try:
                reply = generate_health_reply(tone, answers)
            except Exception as e:
                print("generate_health_reply エラー:", e)
                reply = "ごめんね、うまく解析できなかったみたい…時間をおいてもう一度試してもらえる？"

            try:
                await message.author.send(reply)
            except Exception as e:
                print("最終フィードバック送信エラー:", e)

            try:
                add_log(user_id, tone, answers, reply)
            except Exception as e:
                print("ログ保存エラー:", e)

            if user_id in user_session:
                del user_session[user_id]
            return True

        # Q1〜Q3 → 次の質問へ
        next_q_num = int(mode[1]) + 1
        next_q = f"Q{next_q_num}"

        user_state = get_user_state(user_id) or {}
        tone = user_state.get("tone", "gentle_female")
        q_text = QUESTION_TEMPLATES.get(tone, QUESTION_TEMPLATES["gentle_female"])[next_q]

        user_session[user_id]["mode"] = next_q

        try:
            await message.author.send(f"{next_q}：{q_text}")
        except Exception as e:
            print(f"{next_q} 送信エラー:", e)

        return True

    return False


# ---------------------------------------------------------
# Bot 起動
# ---------------------------------------------------------

bot.run(DISCORD_TOKEN)

