import re
import openai
import os

# ================================================================
#  OpenAI モデル設定
# ================================================================
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ================================================================
#  曖昧表現リスト（AI補足用）
# ================================================================
AMBIGUOUS_NEUTRAL = [
    "ちょっと", "まあまあ", "そこそこ", "そんなに", "なんか", "たぶん",
    "ぼちぼち", "微妙", "まあいい感じ", "なんとなく", "って感じ",
    "どっちとも言えない", "よくわからない", "なんとも言えない",
    "気にしてなかった", "適当", "まあ普通", "悪くはない", "そんなでもない",
]

AMBIGUOUS_UNCERTAIN = [
    "わからない", "覚えてない", "測ってない", "正確にはわからない",
    "ぼんやりしてる", "はっきりしない", "決められない", "判断できない",
    "そういうの考えてない", "どれくらいだろ", "よく思い出せない"
]

AMBIGUOUS_MILD_NEG = [
    "モヤモヤする", "スッキリしない", "微妙な感じ",
    "なんか疲れてる", "よくわかんないけどしんどい",
    "気持ちが落ち着かない", "心がざわつく", "なんかダルい",
    "はっきりしない不調", "何かが違う感じ", "言葉にしにくい",
    "ちょっとつらい気もする", "なんか重い", "気分がのらない",
]

AMBIGUOUS_STRONG_NEG = [
    "うまく言えない", "説明しづらい", "気持ちがまとまらない",
    "なんかうまくいかない", "テンションが乗らない"
]


def detect_ambiguity(text):
    """ユーザー回答の曖昧表現カテゴリを返す"""
    if not text:
        return None
    t = text.lower()

    if any(w in t for w in AMBIGUOUS_NEUTRAL):
        return "neutral"
    if any(w in t for w in AMBIGUOUS_UNCERTAIN):
        return "uncertain"
    if any(w in t for w in AMBIGUOUS_MILD_NEG):
        return "mild_neg"
    if any(w in t for w in AMBIGUOUS_STRONG_NEG):
        return "strong_neg"

    return None

# ================================================================
# トーン別スタイル（AI補足）
# ================================================================
TONE_STYLES = {
    "gentle_female": """
あなたは「優しい女性の医師」として話します。
・語尾は柔らかい（〜しましょうね／〜だと思うわ）
・相手を安心させる
・医学的断定はしない
・1〜2文
""",
    "bright_girl": """
あなたは「明るい女子」として話します。
・テンション高め、友達っぽい
・〜じゃん！〜だよねー！
・軽く励ます
・1〜2文
""",
    "cheerful_friend": """
あなたは「快活な女友達」として話します。
・気さくで明るい
・体育会系の励まし
・一緒に〜しよ！
・1〜2文
""",
    "cool_girl": """
あなたは「冷静で合理的な女子」として話します。
・簡潔、感情少なめ
・〜だ／〜しろ
・効率的な助言
・1〜2文
""",
    "strict_female": """
あなたは「厳しめの年上女性」です。
・指示口調（〜するんだ／〜しておけ）
・最後に少し優しさ
・1〜2文
""",
    "calm_male": """
あなたは「穏やかで上品な男性」です。
・〜じゃないか／〜すると良いだろう
・自然の比喩を軽く
・落ち着いた励まし
・1〜2文
""",
}

# ================================================================
# AI補足生成
# ================================================================
def generate_ai_supplement(tone_id, category, answer_text):
    """トーン別AI補足文を生成する（1〜2文）"""

    if category is None:
        return None

    style = TONE_STYLES.get(tone_id, TONE_STYLES["gentle_female"])

    # カテゴリ別の説明
    if category == "neutral":
        category_inst = "ユーザーは少し曖昧な答え方をしています。安心感を与える短い励ましをください。"
    elif category == "uncertain":
        category_inst = "ユーザーは『よくわからない』という不確かな答え方をしています。無理に正確でなくても良いと伝えてください。"
    elif category == "mild_neg":
        category_inst = "ユーザーは軽度の不調やモヤモヤを表現しています。寄り添うように励ます短い言葉をください。"
    elif category == "strong_neg":
        category_inst = "ユーザーは気持ちの揺らぎを強めに示しています。静かに寄り添う短いメッセージをください。"
    else:
        return None

    system_prompt = (
        "あなたはユーザーの心身状態に寄り添うキャラクターです。"
        "キャラ設定に合わせて日本語で1〜2文の短いメッセージを生成してください。"
        "診断・断定・医療行為は禁止です。"
    )

    user_prompt = f"""
【キャラ設定】
{style}

【ユーザー回答】
「{answer_text}」

【状況】
{category_inst}

【出力条件】
・1〜2文の短い日本語
・ユーザーを否定しない
"""

    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=120,
            temperature=0.7,
        )
        return resp["choices"][0]["message"]["content"].strip()

    except Exception:
        return None

# ================================================================
#  プレイ時間抽出
# ================================================================
def extract_play_minutes(text):
    if not text:
        return None
    m = re.search(r"(\d+)\s*分", text)
    return int(m.group(1)) if m else None

def classify_play_time(minutes):
    if minutes <= 30:
        return "short"
    elif minutes <= 120:
        return "normal"
    elif minutes <= 240:
        return "long"
    else:
        return "very_long"

# ================================================================
#  タグ分類（あなたの元コードそのまま維持）
# ================================================================

def classify_tags(answer):
    if not answer:
        return []

    tags = []

    a = answer.lower()

    if any(k in a for k in ["疲", "しんど", "だる", "倦怠"]):
        tags.append("fatigue")
    if any(k in a for k in ["痛", "頭", "肩", "腰"]):
        tags.append("pain")
    if any(k in a for k in ["眠", "寝不足", "ねむ"]):
        tags.append("sleep")
    if any(k in a for k in ["ストレス", "不安", "焦り", "つら"]):
        tags.append("stress")
    if any(k in a for k in ["最高", "元気", "良い", "快調"]):
        tags.append("good")

    return tags


# ================================================================
# トーン別フィードバックテンプレ（あなたの既存テンプレ構造を維持）
# ================================================================

TEMPLATES = {
    "gentle_female": {
        "Q1": {
            "short": "短めに遊べていたようね。無理のない範囲で続けましょうね。",
            "normal": "ちょうど良い時間ね。自分を労わりながら楽しめたのは良いことだわ。",
            "long": "少し長くなっていたみたい。体のサインも気にしながらね。",
            "very_long": "だいぶ長時間だったわね。今日はしっかり休んであげてほしいわ。"
        },
        "Q2": {
            "fatigue": "疲れが出ているようね。まずは深呼吸して休みましょうね。",
            "pain": "どこかに痛みがあるのね。無理せず労わってあげて。",
            "sleep": "眠気が気になるようね。今日は早めに休めると良いわ。",
            "stress": "心が張っているみたいね。少し落ち着ける時間を作りましょう。",
            "good": "良い調子みたいで安心したわ。"
        },
        "Q3": {
            "fatigue": "気持ちにも少し疲れがあるみたい。あなたのペースで大丈夫よ。",
            "stress": "心の負担を感じているようね。ここにいるから、安心してね。",
            "good": "前向きな気持ちを保てていて素敵ね。",
        },
        "Q4": {
            "sleep_low": "睡眠が短めのようね。今日は少しでも休めるといいわ。",
            "sleep_ok": "睡眠は取れているみたいね。良い調子よ。",
            "sleep_high": "よく眠れたみたいね。その調子を大切にしましょう。"
        }
    },

    # ------------------------------------------------------------
    # 以下、他5トーンも既存構造をそのまま維持（長いため割愛）
    # 実際のファイルには全トーンをペースト済であることを前提にしています。
    # ------------------------------------------------------------
}

# ================================================================
#  Q4 — 睡眠分類
# ================================================================
def classify_sleep(text):
    if not text:
        return "sleep_ok"
    if any(k in text for k in ["少ない", "短い", "寝不足", "眠れ"]):
        return "sleep_low"
    if any(k in text for k in ["寝すぎ", "長い"]):
        return "sleep_high"
    return "sleep_ok"

# ================================================================
#  メインロジック：最終フィードバック生成
# ================================================================
def generate_health_reply(tone_id, answers):
    """
    answers = {
        "Q1": "〜",
        "Q2": "〜",
        "Q3": "〜",
        "Q4": "〜",
    }
    """

    tone = TEMPLATES.get(tone_id, TEMPLATES["gentle_female"])

    # ---- Q1
    minutes = extract_play_minutes(answers.get("Q1", ""))
    if minutes is None:
        q1_key = "short"
    else:
        q1_key = classify_play_time(minutes)
    q1_text = tone["Q1"][q1_key]

    # ---- Q2
    tags_q2 = classify_tags(answers.get("Q2", ""))
    q2_key = tags_q2[0] if tags_q2 else "good"
    q2_text = tone["Q2"].get(q2_key, tone["Q2"]["good"])

    # ---- Q3
    tags_q3 = classify_tags(answers.get("Q3", ""))
    q3_key = tags_q3[0] if tags_q3 else "good"
    q3_text = tone["Q3"].get(q3_key, list(tone["Q3"].values())[0])

    # ---- Q4
    q4_key = classify_sleep(answers.get("Q4", ""))
    q4_text = tone["Q4"][q4_key]

    # ============================================================
    # AI補足生成（必要な場合のみ）
    # ============================================================
    supplements = []

    for qkey in ["Q1", "Q2", "Q3", "Q4"]:
        user_answer = answers.get(qkey, "")
        amb = detect_ambiguity(user_answer)
        ai_text = generate_ai_supplement(tone_id, amb, user_answer)
        if ai_text:
            supplements.append(ai_text)

    # ============================================================
    # 最終文章
    # ============================================================

    result = (
        f"● プレイ時間：{q1_text}\n"
        f"● 体調：{q2_text}\n"
        f"● 気分：{q3_text}\n"
        f"● 睡眠：{q4_text}\n"
    )

    if supplements:
        result += "\n---\n【AIのひとこと補足】\n" + "\n".join(f"- {s}" for s in supplements)

    return result
