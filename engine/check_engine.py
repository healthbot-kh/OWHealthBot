import re

# ================================================================
#  プレイ時間抽出
# ================================================================
def extract_play_minutes(text):
    """
    文字列から「◯◯分」を見つけて分(int)を返す。
    見つからなければ None を返す。
    """
    if not text:
        return None

    m = re.search(r"(\d+)\s*分", text)
    if m:
        return int(m.group(1))
    return None


def classify_play_time(minutes):
    """
    minutes: int
    short / normal / long に分類する
    """
    if minutes <= 30:
        return "short"
    elif minutes <= 120:
        return "normal"
    else:
        return "long"


# ================================================================
#  テキスト分類（condition / sleep / mood）
# ================================================================

def classify_tags(text):
    """
    全回答テキストをまとめて渡し、
    condition / sleep / mood をタグで返す。
    優先度：
      condition: pain > eye > posture > fatigue > positive > neutral
      sleep/mood: negative > positive > neutral
    """
    if text is None:
        text = ""
    # 安全のため小文字変換（英語tilt等）
    lower = text.lower()

    # condition
    condition = "neutral"

    # pain
    pain_words = ["痛", "肩", "腰", "頭痛", "しびれ", "指", "腕", "関節", "手", "腱鞘炎", "バネ指", "固まる", "力入る"]
    if any(w in text for w in pain_words):
        condition = "pain"
    else:
        # eye
        eye_words = ["目", "眼", "視", "かすみ", "しょぼしょぼ", "見", "霞む", "見え", "にじむ"]
        if any(w in text for w in eye_words):
            condition = "eye"
        else:
            # posture
            posture_words = ["姿勢", "猫背", "首", "コリ", "凝り", "張り", "背中", "肩甲骨", "体勢", "反り"]
            if any(w in text for w in posture_words):
                condition = "posture"
            else:
                # fatigue
                fatigue_words = ["だる", "疲れ", "倦怠", "しんどい", "熱", "ヘトヘト"]
                if any(w in text for w in fatigue_words):
                    condition = "fatigue"
                else:
                    # positive
                    positive_words = ["元気", "好調", "絶好調", "調子いい"]
                    if any(w in text for w in positive_words):
                        condition = "positive"
                    else:
                        condition = "neutral"

    # sleep
    sleep = "neutral"
    sleep_negative = ["寝れ", "眠れ", "不足", "寝つき", "悪", "途中", "短", "中断", "夜更かし", "朝方", "眠気", "ボーッ", "ぼんやり"]
    sleep_positive = ["よく寝", "ぐっすり", "良", "ちゃんと", "深く眠れ"]
    if any(w in text for w in sleep_negative):
        sleep = "negative"
    elif any(w in text for w in sleep_positive):
        sleep = "positive"
    else:
        sleep = "neutral"

    # mood
    mood = "neutral"
    mood_negative = [
        "つら", "不安", "イライラ", "落ち込", "悲し", "ストレス", "死", "むかつく", "うつ",
        "腹が立つ", "最悪", "ティルト", "無理ゲー", "心折れ", "ブチギレ", "萎え"
    ]
    mood_positive = ["嬉しい", "楽しい", "順調", "最高", "充実", "ワクワク"]

    if "tilt" in lower or any(w in text for w in mood_negative):
        mood = "negative"
    elif any(w in text for w in mood_positive):
        mood = "positive"
    else:
        mood = "neutral"

    return {
        "condition": condition,
        "sleep": sleep,
        "mood": mood,
    }


# ================================================================
#  トーン別テンプレ（質問への返答メッセージ）
#  ※ 既存 check_engine.py の TEMPLATES をベースに、
#    intro/outro を最新版に差し替えたもの
# ================================================================
TEMPLATES = {'gentle_female': {'intro': '今日のあなたの状態をみていきましょうか。',
                   'outro': '無理は禁物よ。今日はあなた自身を労わってあげて。私との約束よ。\n危ないことしてないかみてあげるから、また明日もいらっしゃい。',
                   'Q1': {'short': '短時間で良い楽しみ方ができたようね。',
                          'normal': '無理のないプレイ時間だったみたいね。',
                          'long': '少し長いプレイになっていたようね。身体のことも気にかけてね。'},
                   'Q2': {'positive': '体調は整っているようね。',
                          'pain': 'どこか痛みが出ているみたいね。少し心配だわ。',
                          'fatigue': '疲れが強く出ているみたいね。無理しすぎないで。',
                          'neutral': '体調は大きく崩れていないようね。'},
                   'Q3': {'positive': 'しっかり眠れているのはとても良い兆候よ。',
                          'negative': '睡眠が足りていないのが気になるわ。心も身体も休息が必要よ。',
                          'neutral': '睡眠は大きな問題は無さそうね。'},
                   'Q4': {'positive': '前向きな気分で過ごせているのは本当に素敵ね。',
                          'negative': '気持ちが揺れていたみたいね。そんな日もあるわ。',
                          'neutral': '気分の波は比較的落ち着いているみたいね。'},
                   'complex': {'long_sleep_negative': '長くプレイしたうえに睡眠も不足しているようね。心も身体も負担が大きいわ。今日はしっかり休むことを優先しましょう。',
                               'long_pain': '長く遊んだうえに痛みまで出ているのね。身体がかなり負担を感じているサインよ。',
                               'long_fatigue': '長時間のプレイで疲れが強く出ているようね。今日は無理をしないで。',
                               'short_mood_positive': '短い時間で楽しめて、気分も良さそうね。本当に素敵な状態よ。',
                               'pain_mood_negative': '痛みがあるうえに気持ちも沈んでいるようね…。まずは身体を楽にしてあげて、少し心を落ち着けましょう。',
                               'fatigue_mood_negative': '疲れが強く気持ちも落ち込み気味のようね。しっかり休息を取る時間を作ってね。',
                               'good_condition_sleep_negative': '体調は良いみたいだけれど、睡眠が足りていないのが気になるわ。コンディションを維持するためにも休息を大切にしてね。'}},
 'bright_girl': {'intro': 'よしっ！今日のコンディション、一緒にチェックしてこ〜！',
                 'outro': 'じゃあ今日はここまで！無理せずゆっくりしてね〜！\nまた明日ね～！',
                 'Q1': {'short': '短い時間で遊んだんだね！いい感じに楽しめたみたいじゃん！',
                        'normal': 'ほどよい時間で遊べてるね〜！バランスいいよ！',
                        'long': 'けっこう長く遊んだね！？ちょっと疲れ出てない？'},
                 'Q2': {'positive': '体調バッチリって感じだね！いいじゃんいいじゃん！',
                        'pain': '体つらそうだね？それは休憩がほしいサインじゃない？ちょっとストレッチしよしよ！',
                        'fatigue': '疲れてるみたいだね…ちょっと休んだほうが絶対いいよ〜！',
                        'neutral': '体調は大きな問題なさそうだね！'},
                 'Q3': {'positive': 'ちゃんと寝れてるんだ！睡眠とれてるの最強じゃん！',
                        'negative': '寝不足！？それはヤバいよ〜！今日はちゃんと寝よ寝よ！',
                        'neutral': '睡眠はまあまあって感じかな〜？'},
                 'Q4': {'positive': 'テンション上がってるね～！やる気も上がって無敵モードだね！',
                        'negative': 'なんかモヤっとしてる？あるある〜！話してくれてありがとね！',
                        'neutral': '気分は落ち着いてる感じだね〜！'},
                 'complex': {'long_sleep_negative': 'うわっ、いっぱい遊んでしかも寝不足！？それはヤバいよ〜！今日はもうお休みタイムだね、絶対！',
                             'long_pain': '長時間やって身体痛いの！？それ絶対ムリしすぎだよ〜！今日はケア優先ね、ほんとに！',
                             'long_fatigue': 'いっぱい遊んで疲れちゃった？そりゃそうだよ〜！今日はもう休憩ってことでいこ！',
                             'short_mood_positive': '短い時間で楽しめてテンションいい感じ！？それ最高じゃん！',
                             'pain_mood_negative': '痛いし気分もモヤるって…つらかったね。今日は無理しないで、ほんと休も！',
                             'fatigue_mood_negative': 'つかれてる上にモヤっとしてるって…めちゃくちゃしんどいよね。今日はまず休むの優先ね！',
                             'good_condition_sleep_negative': '体調バッチリなのに寝不足！？それはもったいないよ〜！今日はちゃんと寝てパワー全開にしよ！'}},
 'cheerful_friend': {'intro': '答えてくれてありがとう！じゃあ、わたしと一緒に確かめようか！',
                     'outro': '今日はしっかりケアしてまた一緒にがんばろう！\nまた明日も会いに来てね！',
                     'Q1': {'short': '短く遊んでスッキリできたならいい感じだね！',
                            'normal': 'ちょうどいいプレイ時間だったね！いいバランスだよ！',
                            'long': '結構長く遊んだね！楽しかった分、体もちゃんと休めよう！'},
                     'Q2': {'positive': '体調は悪くなさそうだね！その調子でいこ！',
                            'pain': '痛いところあるんだね…ちょっと心配だよ。今日は無理しないでね！',
                            'fatigue': 'かなり疲れてるみたいだね…。休憩挟んでちゃんと回復しよ！',
                            'neutral': '体調は大きく崩れてないみたいだね！'},
                     'Q3': {'positive': 'ちゃんと眠れてるなら安心だよ！その調子その調子！',
                            'negative': '眠れてないんだね…わかるよ。でも今日は無理しないでね！',
                            'neutral': '睡眠はそこそこって感じかな？'},
                     'Q4': {'positive': '気分も前向きでいい感じだね！一緒にこの調子でいこ！',
                            'negative': '気分落ちちゃってるんだね…今日はゆっくり休んでいいからね。',
                            'neutral': '気持ちは割と落ち着いてるみたいだね。'},
                     'complex': {'long_sleep_negative': '長くプレイしたうえに寝不足なのはキツかったね…！今日は無理しないでしっかり休もう！',
                                 'long_pain': 'がっつり遊んだうえに痛みも出たんだ…！それは流石にしんどいよね。今日はちゃんと休んで回復しよ！',
                                 'long_fatigue': 'たくさんやって疲れちゃったんだ…！今日はムリせず、少し休んで戻そうよ！',
                                 'short_mood_positive': '短く遊んで気分もいいなんて、かなりいい日だね！',
                                 'pain_mood_negative': '痛いし気分も落ちてるなんて…それはほんとしんどかったね。今日は無理せずゆっくり休もう！',
                                 'fatigue_mood_negative': '疲れてるし気分も落ちてたんだね…そりゃツラいよ。今日は休んでリセットしよ、一緒にゆっくりでいいからね！',
                                 'good_condition_sleep_negative': '元気はあるんだね！でも寝不足なのは気になるなぁ。今日は早めに寝て、いい状態キープしよ！'}},
 'cool_girl': {'intro': '今日の状態を確認した。それぞれみていってくれ。',
               'outro': '無駄を省きたいなら、今は休息を優先しろ。\n明日もみてやるから必ず来い。…寂しいわけじゃないからな？',
               'Q1': {'short': '短時間で区切れたのは悪くない判断だ。',
                      'normal': '適度なプレイ時間だ。効率的だな。',
                      'long': '長時間だな。集中力の低下が懸念される。'},
               'Q2': {'positive': '体調は良好のようだ。問題ない。',
                      'pain': '痛みが出ているようだ。無理は効率を落とす。',
                      'fatigue': '疲労が見られる。休息を取るべきだ。',
                      'neutral': '体調は特に問題ないようだ。'},
               'Q3': {'positive': '睡眠は十分のようだ。良い状態だ。',
                      'negative': '睡眠不足は判断の精度を落とす。注意しろ。',
                      'neutral': '睡眠は可もなく不可もなく、といったところだ。'},
               'Q4': {'positive': '気分が良いようだな。その状態をうまく活かせ。',
                      'negative': '気分の揺らぎは判断を鈍らせる。深呼吸しろ。',
                      'neutral': '気分は安定しているな。問題ない。'},
               'complex': {'long_sleep_negative': '長時間のプレイに加え睡眠不足か。効率もパフォーマンスも落ちているはずだ。まず休め。',
                           'long_pain': '長時間に痛みを伴うのは明らかに負担が大きい。効率以前の問題だ。休息が必要だ。',
                           'long_fatigue': '疲労が蓄積している。長時間のプレイは悪手だ。今は休むべきだ。',
                           'short_mood_positive': '短時間で気分良く遊べたのは良い判断だ。効率も調子も悪くない。',
                           'pain_mood_negative': '痛みと気分の落ち込みが重なっている。悪循環になる前に休息を取れ。',
                           'fatigue_mood_negative': '疲労と気分の不調が同時に出ている。今の状態で続けるのは賢明ではない。中断しろ。',
                           'good_condition_sleep_negative': '体調は悪くないようだが、睡眠不足は見逃せない。パフォーマンスを維持したいなら睡眠を優先しろ。'}},
 'strict_female': {'intro': 'よし、今日の状態を報告したようだな。確認しよう。',
                   'outro': '今日はこれで十分だ。明日に向けて休んで整えておけ。いいな？\n明日もまた来るといい。',
                   'Q1': {'short': '短い時間で切り上げたな。判断としては悪くない。',
                          'normal': '適度な時間で済ませたようだな。続けるにはちょうどいい。',
                          'long': '長くやりすぎだ。集中力も落ちているはずだ。'},
                   'Q2': {'positive': '体調は問題なさそうだ。いい状態だな。',
                          'pain': '痛みが出ているようだな。放置して悪化させるな。',
                          'fatigue': '疲れが濃いな。これ以上の無茶はするな。',
                          'neutral': '体調は大崩れしていないようだ。だが油断はするな。'},
                   'Q3': {'positive': 'ちゃんと眠れているようだな。基礎はできている。',
                          'negative': '睡眠不足か。そんな状態で無理を重ねるな。',
                          'neutral': '睡眠は最低限は取れているようだな。だが質は意識しろ。'},
                   'Q4': {'positive': '気分が良いなら、その勢いをうまく活かせ。',
                          'negative': '気持ちが不安定なようだな。無理に踏ん張るな、まず整えろ。',
                          'neutral': '気分は大きく崩れていないようだな。冷静さを保て。'},
                   'complex': {'long_sleep_negative': '長時間のプレイに加え、睡眠不足とはな。そんな状態で続ければ崩れるのは当然だ。すぐに休め。',
                               'long_pain': '長時間のプレイで痛みが出ているな。限界を超えている証拠だ。すぐにやめて休め。',
                               'long_fatigue': '疲労が濃い状態で長く続けるのは愚かだ。今は撤退して整えるべきだ。',
                               'short_mood_positive': '短時間で楽しめて気分も良い。理想的なコンディションだな。',
                               'pain_mood_negative': '痛みがあって気持ちも沈んでいるようだな。その状態で続ける価値はない。休息を最優先しろ。',
                               'fatigue_mood_negative': '疲れと気分の不安定さが重なっているな。まずは体勢を整えろ。',
                               'good_condition_sleep_negative': '体調は悪くないが、睡眠不足は後から響く。今のうちにしっかり休んでおけ。'}},
 'calm_male': {'intro': 'さあ、あなたの心身の調律を整えていこうじゃないか。',
               'outro': '自分を慈しむ時間を持とう。きっと明日へ繋がっていくはずだよ。\n明日もまた会いに来てほしい。楽しみしているよ。',
               'Q1': {'short': '短い時間で区切れたようだね。上手な付き合い方じゃないか。',
                      'normal': 'ちょうど良いくらいの時間で楽しめたようだね。バランスが取れているよ。',
                      'long': '随分と長く遊んでいたようだね…心も体も少し休ませてあげよう。'},
               'Q2': {'positive': '体調は良さそうだね。その調子で自分を大事にしていこう。',
                      'pain': 'どこかに痛みを感じているようだね…無理を重ねると大きな負担になるよ。',
                      'fatigue': '疲れが出てきているみたいだね。少しペースを落として休む時間を作ろう。',
                      'neutral': '大きな不調はなさそうだね。ただ、油断せず自分の感覚に耳を傾けてみよう。'},
               'Q3': {'positive': 'よく眠れているようで安心したよ。睡眠は心と体の土台だからね。',
                      'negative': 'あまり眠れていないようだね…心身のバランスが心配だ。今日はゆっくり休もう。',
                      'neutral': '睡眠は大崩れしていないようだね。ただ、もう少し丁寧に休むことを意識してもいいかもしれない。'},
               'Q4': {'positive': '気持ちも前向きで、とてもいい状態だね。その心地よさを大切にしていこう。',
                      'negative': '心が少し重たくなっているようだね…。そんな時こそ、自分を責めずに優しくしてあげよう。',
                      'neutral': '気持ちは比較的落ち着いているようだね。静かな状態も、とても大事な時間だよ。'},
               'complex': {'long_sleep_negative': 'たくさん遊んだうえに眠りも浅かったようだね…これは心と体が負荷を抱えている状態だよ。今日はゆっくり整えようじゃないか。',
                           'long_pain': 'たくさん遊んで痛みが出てしまったのか…体の調子が崩れているね。今日はしっかり一度リセットしようじゃないか。',
                           'long_fatigue': 'たっぷり遊んで疲れも出てきたようだね…心身のバランスが乱れているよ。今日は整える時間を大切にしようじゃないか。',
                           'short_mood_positive': '短い時間でも気持ちよく楽しめたようだね。それはとても良い付き合い方だよ。',
                           'pain_mood_negative': '痛みと気分の重たさが一緒にのしかかっているようだね…。まずは一度立ち止まって、自分を休ませてあげよう。',
                           'fatigue_mood_negative': '疲れも出ていて、気持ちにも負荷がかかっているようだね…こういう時こそ自分に優しくしよう。今日は整える日だ。',
                           'good_condition_sleep_negative': '体調は悪くないのに眠れていないのは惜しいところだね。今のうちに休む時間を確保して、良い状態を長く保とう。'}}}


# ================================================================
#  総合フィードバック生成
# ================================================================
def generate_health_reply(data, tone_id):
    """
    data: {
        "play_time": str,
        "condition": str,
        "sleep": str,
        "mood": str
    }
    tone_id: gentle_female / bright_girl / cheerful_friend / cool_girl / strict_female / calm_male
    """

    # 1. プレイ時間タグ
    raw_play = data.get("play_time", "")
    minutes = extract_play_minutes(raw_play)
    if minutes is None:
        minutes = 0
    play_tag = classify_play_time(minutes)  # short / normal / long

    # 2. condition / sleep / mood タグ
    all_text = (data.get("condition") or "") + " " + (data.get("sleep") or "") + " " + (data.get("mood") or "")
    tags = classify_tags(all_text)
    condition_tag = tags["condition"]
    sleep_tag = tags["sleep"]
    mood_tag = tags["mood"]

    # 3. テンプレ取得
    tpl = TEMPLATES.get(tone_id, TEMPLATES["gentle_female"])

    play_text = tpl["Q1"][play_tag]
    cond_text = tpl["Q2"][condition_tag]
    sleep_text = tpl["Q3"][sleep_tag]
    mood_text = tpl["Q4"][mood_tag]

    # 4. complex 判定（既存7種のみ有効）
    complex_key = None
    if play_tag == "long" and sleep_tag == "negative":
        complex_key = "long_sleep_negative"
    elif play_tag == "long" and condition_tag == "pain":
        complex_key = "long_pain"
    elif play_tag == "long" and condition_tag == "fatigue":
        complex_key = "long_fatigue"
    elif play_tag == "short" and mood_tag == "positive":
        complex_key = "short_mood_positive"
    elif condition_tag == "pain" and mood_tag == "negative":
        complex_key = "pain_mood_negative"
    elif condition_tag == "fatigue" and mood_tag == "negative":
        complex_key = "fatigue_mood_negative"
    elif condition_tag == "positive" and sleep_tag == "negative":
        complex_key = "good_condition_sleep_negative"

    complex_text = ""
    if complex_key and "complex" in tpl and complex_key in tpl["complex"]:
        if tpl["complex"][complex_key]:
            complex_text = tpl["complex"][complex_key]

    intro = tpl.get("intro", "")
    outro = tpl.get("outro", "")

    bullet = (
        f"● プレイ時間：{play_text}\n"
        f"● 体調：{cond_text}\n"
        f"● 睡眠：{sleep_text}\n"
        f"● 気分：{mood_text}\n\n"
    )

    lines = []
    if intro:
        lines.append(intro)
        lines.append("")
    lines.append("📊 今日の状態まとめ")
    lines.append("")
    lines.append(bullet.rstrip())
    if complex_text:
        lines.append(complex_text)
        lines.append("")
    if outro:
        lines.append(outro)

    return {
        "reply": "\n".join(lines)
    }
