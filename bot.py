import os
import json
import discord
from discord.ext import commands
import firebase_admin
from firebase_admin import credentials, firestore

from engine.check_engine import generate_health_reply  # ← 既存 check_engine.py を利用

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
# 仕様書・トーン設定ファイルに準拠
# ---------------------------------------------------------

QUESTION_TEMPLATES = {
    "gentle_female": {
        "Q1": "今日もお疲れさま。どれくらい遊んだか教えてくれる？",
        "Q2": "いまの体調はどう？少し疲れているようなら、しっかり休んでね。",
        "Q3": "昨夜はよく眠れたかしら？睡眠はあなたの力になるものよ。",
        "Q4": "いまの気分はどう？よかったら話してくれるかしら？",
    },
    "bright_girl": {
        "Q1": "今日どれくらいやってた？だいたいでいいよ〜！",
        "Q2": "体調どう？いつもどおり？それともちょっとお疲れ？",
        "Q3": "昨日の睡眠はどんな感じ？ぐっすり？それともイマイチ？",
        "Q4": "いまの気分はどう？嬉しい？疲れた？なんでも言ってよ！",
    },
    "cheerful_friend": {
        "Q1": "今日はどれくらい遊んでたの？けっこう集中してたみたいだね。",
        "Q2": "体調はどう？無理しすぎてない？",
        "Q3": "昨日はぐっすり眠れた？睡眠は大事だからね！",
        "Q4": "今の気持ちはどう？なんでも話して！",
    },
    "cool_girl": {
        "Q1": "今日のプレイ時間を教えてくれ。おおよそでいい。",
        "Q2": "体調はどうだ？疲れの兆候が出ていないか確認しよう。",
        "Q3": "睡眠は足りているか？眠気は集中力を奪う。",
        "Q4": "今の気持ちはどうだ？率直に答えてくれて構わない。",
    },
    "strict_female": {
        "Q1": "今日は何時間プレイした？大体でも構わない。",
        "Q2": "体調はどうだ。不調がないかみてやろう。",
        "Q3": "昨夜は眠れたか？睡眠を軽視するなよ。",
        "Q4": "今の気分はどうだ？弱音でも愚痴でも付き合ってやろう。",
    },
    "calm_male": {
        "Q1": "今日はどれくらい遊んでいたんだい？ずいぶんと楽しんでいたようだけど。",
        "Q2": "体調はどうだい？少しでも違和感があるなら教えてほしい。",
        "Q3": "昨夜の睡眠はどうだったかな？眠りは心も体も整える大切な時間だね。",
        "Q4": "今どんな気持ちでいるのかな？素直に話してもらえると嬉しいんだけれど。",
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

def add_log(user_id: int, tone: str, data: dict, reply: str):
    """
    users/{uid}/logs/{auto_id} にログ保存（簡易版）
    """
    ref = db.collection(COLLECTION_NAME).document(str(user_id)).collection("logs")
    ref.add(
        {
            "tone": tone,
            "play_time": data.get("play_time", ""),
            "condition": data.get("condition", ""),
            "sleep": data.get("sleep", ""),
            "mood": data.get("mood", ""),
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
こんにちは！私はあなたの“ゲーム健康サポート相棒”です。

【使い方】
・「体調チェック」と送ると健康チェックを開始します
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

    # =====================================================
    # 1) トーン変更トリガー（例：「トーン変更」）
    # =====================================================
    if contains(content, CHANGE_TONE_WORDS):
        # 変更案内は DM で送付
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
            user_session[user_id] = {"mode": "choose_tone", "after_tone_start_check": False}
            # サーバー上からの操作なら「DMを見てね」と一言返す
            if message.guild is not None:
                await message.channel.send("トーン変更の案内を DM に送ったよ！")
        except Exception as e:
            print("トーン変更 DM 送信エラー:", e)
        return

    # =====================================================
    # 2) 体調チェックトリガー（「体調チェック」等）
    #    → DM に誘導して Q1〜Q4 進行
    # =====================================================
    if contains(content, TRIGGER_WORDS):

        state = get_user_state(user_id)

        # 初回ユーザー → ガイド送付
        if not state or not state.get("seen_guide"):
            try:
                await message.author.send(GUIDE_TEXT)
                set_user_state(user_id, {"seen_guide": True})
            except Exception as e:
                print("GUIDE_TEXT DM 送信エラー:", e)

        # トーン未設定 → まずトーン選択
        state = get_user_state(user_id)  # seen_guide 更新反映
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
                user_session[user_id] = {"mode": "choose_tone", "after_tone_start_check": True}
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

    # =====================================================
    # 3) セッション進行（トーン選択 / Q1〜Q4）
    # =====================================================
    if user_id in user_session:
        session = user_session[user_id]
        mode = session.get("mode")

        # ---------------------------
        # (A) トーン選択中
        # ---------------------------
        if mode == "choose_tone":
            if content not in TONE_CHOICES:
                await message.author.send("1〜6 の番号で選んでください！")
                return

            tone = TONE_CHOICES[content]
            set_user_state(user_id, {"tone": tone})
            await message.author.send(f"了解、あなたの相棒は **{TONE_LABELS[tone]}** だよ！")

            # 「体調チェック」から流入した場合は、そのまま Q1 へ進行
            if session.get("after_tone_start_check"):
                q_text = QUESTION_TEMPLATES.get(tone, QUESTION_TEMPLATES["gentle_female"])["Q1"]
                user_session[user_id] = {"mode": "Q1"}
                await message.author.send(f"Q1：{q_text}")
            else:
                # 単なるトーン変更の場合はここで終わり
                del user_session[user_id]

            return

        # ---------------------------
        # (B) Q1〜Q4 進行中
        # ---------------------------
        if mode in ["Q1", "Q2", "Q3", "Q4"]:
            # 回答を Firestore に保存（Q1〜Q4 で保持）
            set_user_state(user_id, {mode: content})

            # Q1〜Q4 → play_time / condition / sleep / mood へのマッピングは
            # 最後にまとめて行う（Firestore から取得して変換）
            if mode == "Q4":
                # すべての回答取得
                user_state = get_user_state(user_id) or {}
                tone = user_state.get("tone", "gentle_female")

                data = {
                    "play_time": user_state.get("Q1", ""),
                    "condition": user_state.get("Q2", ""),
                    "sleep": user_state.get("Q3", ""),
                    "mood": user_state.get("Q4", ""),
                }

                try:
                    reply = generate_health_reply(data, tone)
                except Exception as e:
                    print("generate_health_reply エラー:", e)
                    reply = "ごめんね、うまく解析できなかったみたい…時間をおいてもう一度試してもらえる？"

                # DM で最終フィードバック送信
                try:
                    await message.author.send(reply)
                except Exception as e:
                    print("最終フィードバック送信エラー:", e)

                # ログ保存（簡易版）
                try:
                    add_log(user_id, tone, data, reply)
                except Exception as e:
                    print("ログ保存エラー:", e)

                # セッション終了
                del user_session[user_id]
                return

            # Q1〜Q3 の場合 → 次の質問へ
            next_q_num = int(mode[1]) + 1  # "Q1" → 2 など
            next_q = f"Q{next_q_num}"

            user_state = get_user_state(user_id) or {}
            tone = user_state.get("tone", "gentle_female")
            q_text = QUESTION_TEMPLATES.get(tone, QUESTION_TEMPLATES["gentle_female"])[next_q]

            user_session[user_id]["mode"] = next_q

            try:
                await message.author.send(f"{next_q}：{q_text}")
            except Exception as e:
                print(f"{next_q} 送信エラー:", e)

            return

    # 他のコマンド処理
    await bot.process_commands(message)

# ---------------------------------------------------------
# Bot 起動
# ---------------------------------------------------------

bot.run(DISCORD_TOKEN)
