import json
import random
import os
import re
import time
from datetime import datetime
import requests
from google import genai
from google.genai import types

# ─────────────────────────────────────────────
# 설정값
# ─────────────────────────────────────────────
MAX_OUTPUT_TOKENS = 16384   # 사고(thinking) 토큰 포함 모델 대비 넉넉하게 설정
TEMPERATURE = 1.0           # Gemini 3.x 이상 계열 권장 기본값
MAX_RETRIES = 3

# 프로젝트 API 할당량(텍스트 출력 모델, RPD > 0) 기준 우선순위
PREFERRED_MODELS = [
    # 1군: 고품질 메인 (각 RPD 20, 총 100회)
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-4-hydrogen",
    "gemini-3-flash",
    "gemini-2.5-flash",
    # 2군: 대용량 백업 (각 RPD 500, 총 1,000회)
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    # 3군: 보조 백업 (RPD 20) 및 자동 별칭
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

MARKERS_BASE = ["DETAIL", "PURPOSE", "SUNO", "EXCLUDE_STYLES", "VOCAL", "IMAGE", "LYRICS", "TAG", "UPLOAD"]

REQUIRED_SECTIONS = [
    "Intro", "Verse 1", "Pre-Chorus 1", "Chorus 1", "Verse 2", "Pre-Chorus 2",
    "Chorus 2", "Bridge", "Instrumental Solo", "Chorus 3", "Outro",
]
REQUIRED_FIELDS = ["detail", "purpose", "suno", "vocal", "lyrics", "tag", "upload"]

_MODEL_CACHE = None  # list_models() 결과 재사용


# ─────────────────────────────────────────────
# 데이터 로드 및 시드 추출
# ─────────────────────────────────────────────
def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def clean_seed(text):
    return text.replace("_", " ").strip()


def get_random_item(data):
    if isinstance(data, dict):
        all_items = []
        for items_in_category in data.values():
            all_items.extend(items_in_category)
        return clean_seed(random.choice(all_items))
    elif isinstance(data, list):
        return clean_seed(random.choice(data))
    return ""


def get_two_distinct_emotions(emotions_dict):
    """서로 다른 감정 카테고리에서 Verse용, Chorus용 감정을 하나씩 추출 (같은 단어 제외)"""
    categories = list(emotions_dict.keys())
    if len(categories) >= 2:
        for _ in range(20):
            cat1, cat2 = random.sample(categories, 2)
            emo1 = clean_seed(random.choice(emotions_dict[cat1]))
            emo2 = clean_seed(random.choice(emotions_dict[cat2]))
            if emo1.lower() != emo2.lower():
                return (cat1, emo1), (cat2, emo2)
    emo1 = get_random_item(emotions_dict)
    emo2 = get_random_item(emotions_dict)
    return ("Emotion", emo1), ("Emotion", emo2)


def get_seoul_weather():
    """서울 날씨 조회. 실패 시 None 반환 (프롬프트에서 자동 생략)"""
    api_key = os.environ.get("WEATHER_API_KEY")
    if api_key:
        try:
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": "Seoul", "appid": api_key, "lang": "kr"},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                return data['weather'][0]['description']
            print(f"⚠️ 날씨 API 응답 코드 {response.status_code} (날씨 시드 생략)")
        except Exception as e:
            print(f"⚠️ 날씨 정보를 가져오는 중 에러 발생 (날씨 시드 생략): {type(e).__name__}")
    return None


def is_unwanted_combination(genre1, genre2):
    if genre1 == genre2:
        return True
    unwanted_pairs = {
        ("Folk", "Dubstep"), ("Country", "Hyperpop"), ("Bossa Nova", "Industrial"),
        ("Operatic Pop", "Jersey Club"), ("Blues", "EDM"), ("Ballad", "Afrobeat"),
        ("Jazz", "Hyperpop"), ("Reggae", "Industrial"), ("Lo-fi", "Trap"),
        ("Operatic Pop", "Trap"), ("Folk", "Hyperpop"), ("Country", "Industrial"),
        ("Bossa Nova", "Dubstep"), ("Ballad", "Jersey Club"), ("Blues", "Hyperpop"),
        ("Lo-fi", "Dubstep"), ("Soul", "Industrial"), ("Jazz", "Dubstep"),
        ("Reggae", "Hyperpop"), ("Operatic Pop", "UK Garage"), ("Country", "Deep House"),
        ("Folk", "Jersey Club"), ("Bossa Nova", "Trap"), ("Ballad", "Industrial"), ("Indie", "EDM")
    }
    return (genre1, genre2) in unwanted_pairs or (genre2, genre1) in unwanted_pairs


# ─────────────────────────────────────────────
# 후처리 및 검증
# ─────────────────────────────────────────────
def build_clean_lyrics(raw_lyrics):
    """LYRICS에서 [...]와 <...> 태그를 제거해 순수 가사 생성"""
    cleaned = re.sub(r'\[[^\]]*\]', '', raw_lyrics)
    cleaned = re.sub(r'<[^>]*>', '', cleaned)
    lines = [re.sub(r'[ \t]{2,}', ' ', ln).strip() for ln in cleaned.split('\n')]
    cleaned = '\n'.join(lines)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def post_process_data(extracted):
    """사소한 포맷 오류를 파이썬에서 자동 보정"""
    lyrics = extracted.get("lyrics", "")
    lyrics = lyrics.replace("**", "")
    lyrics = re.sub(r'<([^>]+)>', r'[\1]', lyrics)
    extracted["lyrics"] = lyrics.strip()

    extracted["clean_lyrics"] = build_clean_lyrics(extracted["lyrics"])

    raw_tag = extracted.get("tag", "").replace("#", "")
    tags, seen = [], set()
    for t in raw_tag.split(","):
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            tags.append(t)
    extracted["tag"] = ", ".join(tags[:30])

    if not extracted.get("image", "").strip():
        extracted["image"] = (
            "16:9 비율의 트렌디한 유튜브 뮤직 썸네일 이미지를 만들어 주세요. "
            "이미지 안에 어떤 글자도 넣지 말고(no text, no typography), 곡의 분위기를 시네마틱하게 표현해 주세요.\n\n"
            f"[곡 상세 정보]\n{extracted.get('detail', '')}"
        )

    return extracted


def has_section(lyrics, name):
    """[Verse 1], [Verse 1: ...] 형태 및 [Saxophone Solo] 같은 솔로 변형 허용"""
    if name == "Instrumental Solo":
        return re.search(r'\[[^\]]*\bsolo\b[^\]]*\]', lyrics, re.IGNORECASE) is not None
    return re.search(r'\[\s*' + re.escape(name) + r'\b', lyrics, re.IGNORECASE) is not None


def validate_result(extracted, vocal_type=None):
    """
    반환: (fatal_issues, warnings)
    - fatal_issues: 재생성이 필요한 치명적 오류
    - warnings: 로그 및 Notion 본문 메모만 남기고 재시도하지 않는 경미한 이슈
    """
    fatal, warnings = [], []

    lyrics = extracted.get("lyrics", "")
    clean_lyrics = extracted.get("clean_lyrics", "")
    suno_len = len(extracted.get("suno", ""))
    lyrics_len = len(lyrics)

    # ── 치명적 오류 ──
    empty_fields = [f for f in REQUIRED_FIELDS if not extracted.get(f, "").strip()]
    if empty_fields:
        fatal.append(f"비어 있는 필드(잘림 의심): {', '.join(empty_fields)}")

    if suno_len >= 1000:
        fatal.append(f"Style(Suno) 1000자 초과 ({suno_len}자)")
    if lyrics_len and lyrics_len < 900:
        fatal.append(f"가사(Lyrics) 너무 짧음 ({lyrics_len}자)")
    if lyrics_len > 4800:
        fatal.append(f"가사(Lyrics) 너무 김 ({lyrics_len}자)")

    if lyrics:
        missing = [sec for sec in REQUIRED_SECTIONS if not has_section(lyrics, sec)]
        if missing:
            fatal.append(f"섹션 누락: {', '.join(missing)}")

    # ── 경고 (재시도 없음) ──
    kyeom_count = len(re.findall(r'(?:^|\s)겸(?:\s|$|[,.!?~])', clean_lyrics))
    if clean_lyrics and kyeom_count != 1:
        warnings.append(f"이스터 에그 '~겸' 출현 {kyeom_count}회 (목표 1회)")

    tag_count = len([t for t in extracted.get("tag", "").split(",") if t.strip()])
    if extracted.get("tag", "").strip() and tag_count != 30:
        warnings.append(f"해시태그 {tag_count}개 (목표 30개)")

    if vocal_type == "Mixed Duet" and lyrics:
        if not re.search(r'\[\s*(female|male|duet)', lyrics, re.IGNORECASE):
            warnings.append("Mixed Duet인데 파트 지정 태그([Female Vocal]/[Male Vocal]/[Duet])가 없음")

    return fatal, warnings


# ─────────────────────────────────────────────
# Gemini 호출
# ─────────────────────────────────────────────
def get_available_models(client):
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        _MODEL_CACHE = [
            m.name for m in client.models.list()
            if m.supported_actions and "generateContent" in m.supported_actions
        ]
        print(f"🧐 [참고] 사용 가능한 모델 총 {len(_MODEL_CACHE)}개 확인 완료")
    return _MODEL_CACHE


def find_model_id(available_models, base_name):
    """정확한 모델명 우선 매칭, 없으면 -preview 버전 매칭 (TTS/Live/Image 제외)"""
    candidates = [base_name, f"{base_name}-preview"]
    for cand in candidates:
        for m in available_models:
            if m == cand or m.endswith(f"/{cand}"):
                return m
    return None


def parse_sections(text):
    for m in MARKERS_BASE:
        text = re.sub(r'[*_]*#+\s*' + m + r'\s*#*[*_]*', f'###{m}###', text, flags=re.IGNORECASE)

    markers = [f"###{m}###" for m in MARKERS_BASE]
    extracted = {m.lower(): "" for m in MARKERS_BASE}

    for marker in markers:
        if marker in text:
            part = text.split(marker, 1)[1]
            min_idx = len(part)
            for other_marker in markers:
                if other_marker != marker:
                    idx = part.find(other_marker)
                    if idx != -1 and idx < min_idx:
                        min_idx = idx
            key = marker.replace("#", "").lower()
            extracted[key] = part[:min_idx].strip()

    return post_process_data(extracted)


def generate_lyrics_with_gemini(system_instruction, user_prompt):
    """
    반환: (결과 dict, status)
    status: "ok" | "parse_error" | "api_error" | "no_model" | "no_key"
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("🚨 GEMINI_API_KEY가 설정되지 않았습니다.")
        return {}, "no_key"

    client = genai.Client(api_key=api_key)

    try:
        available_models = get_available_models(client)
    except Exception as api_e:
        print(f"❌ API 모델 리스트 조회 실패: {type(api_e).__name__}")
        return {}, "api_error"

    text = ""
    tried_any = False

    for model_name in PREFERRED_MODELS:
        target = find_model_id(available_models, model_name)
        if not target:
            continue

        tried_any = True
        try:
            print(f"🚀 [{target}] 모델로 생성을 시도합니다...")
            response = client.models.generate_content(
                model=target,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    temperature=TEMPERATURE,
                ),
            )

            finish_reason = ""
            try:
                finish_reason = str(response.candidates[0].finish_reason)
            except Exception:
                pass

            text = response.text or ""
            if not text.strip():
                print(f"⚠️ {target} 빈 응답 (finish_reason={finish_reason or '알 수 없음'}) -> 다음 모델로 전환합니다.")
                continue

            if "MAX_TOKENS" in finish_reason:
                print(f"⚠️ {target} 출력이 토큰 한도에서 잘렸을 수 있습니다 (finish_reason={finish_reason}). 검증 단계에서 확인합니다.")

            print(f"✅ {target} 생성 성공!")
            break

        except Exception as e:
            print(f"⚠️ {target} 실패 ({str(e)[:120]}) -> 다음 모델로 전환합니다.")
            text = ""
            time.sleep(2)

    if not text.strip():
        if not tried_any:
            sample = ", ".join(available_models[:10])
            print(f"❌ PREFERRED_MODELS 중 사용 가능한 모델이 없습니다. (목록 일부: {sample} ...)")
            return {}, "no_model"
        print("❌ 시도한 모든 모델이 할당량 초과 또는 오류로 실패했습니다.")
        return {}, "api_error"

    try:
        extracted = parse_sections(text)

        print("\n[4] 파싱된 섹션별 글자 수:")
        for k, v in extracted.items():
            print(f" - {k}: {len(v)}자")

        return extracted, "ok"

    except Exception as e:
        print(f"❌ Gemini 데이터 파싱 에러: {e}")
        return {}, "parse_error"


# ─────────────────────────────────────────────
# Notion 저장
# ─────────────────────────────────────────────
def get_chunks(text):
    if not text:
        return [{"text": {"content": " "}}]
    return [{"text": {"content": text[i:i+2000]}} for i in range(0, len(text), 2000)]


def save_to_notion(date_str, genre, weather, prompt, data_dict, notes=None):
    notion_token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")

    if not notion_token or not database_id or not data_dict.get("lyrics", "").strip():
        print("❌ 저장할 가사(LYRICS) 데이터가 비어있어 Notion 호출을 취소합니다.")
        return

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    children_blocks = [{
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"text": {"content": "🎶 Gemini 생성 가사 및 곡 구성"}}]}
    }]

    for para in data_dict["lyrics"].split('\n\n'):
        para = para.strip()
        if not para:
            continue
        while len(para) > 2000:
            split_idx = para.rfind('\n', 0, 2000)
            if split_idx == -1:
                split_idx = para.rfind(' ', 0, 2000)
            if split_idx == -1:
                split_idx = 2000
            chunk = para[:split_idx].strip()
            children_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": chunk}}]}
            })
            para = para[split_idx:].strip()
        if para:
            children_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": para}}]}
            })

    children_blocks.append({"object": "block", "type": "divider", "divider": {}})
    children_blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": data_dict.get("tag", "")[:2000] or " "}}]}
    })

    if notes:
        children_blocks.append({"object": "block", "type": "divider", "divider": {}})
        children_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": ("⚠️ 검증 메모: " + " / ".join(notes))[:2000]}}]}
        })

    weather_display = weather if weather else "날씨 정보 없음"

    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Title": {"title": [{"text": {"content": f"{date_str} ({genre})"}}]},
            "Weather": {"rich_text": [{"text": {"content": weather_display}}]},
            "Generated Prompt": {"rich_text": [{"text": {"content": prompt[:2000]}}]},
            "Detail": {"rich_text": [{"text": {"content": data_dict.get("detail", "")[:2000]}}]},
            "Purpose": {"rich_text": [{"text": {"content": data_dict.get("purpose", "")[:2000]}}]},
            "Suno": {"rich_text": [{"text": {"content": data_dict.get("suno", "")[:2000]}}]},
            "Exclude_styles": {"rich_text": [{"text": {"content": data_dict.get("exclude_styles", "")[:2000]}}]},
            "Image": {"rich_text": [{"text": {"content": data_dict.get("image", "")[:2000]}}]},
            "Vocal": {"rich_text": [{"text": {"content": data_dict.get("vocal", "")[:2000]}}]},
            "Lyrics": {"rich_text": get_chunks(data_dict.get("clean_lyrics", ""))},
            "E_Lyrics": {"rich_text": get_chunks(data_dict.get("lyrics", ""))},
            "Tag": {"rich_text": [{"text": {"content": data_dict.get("tag", "")[:2000]}}]},
            "Genre": {"rich_text": [{"text": {"content": genre}}]},
            "Upload": {"rich_text": [{"text": {"content": data_dict.get("upload", "")[:2000]}}]}
        },
        "children": children_blocks
    }

    response = requests.post('https://api.notion.com/v1/pages', headers=headers, json=payload, timeout=30)

    print(f"📊 [결과] HTTP 상태 코드: {response.status_code}")
    if response.status_code == 200:
        print("✅ Notion 저장 성공! 모든 데이터가 들어갔습니다.")
    else:
        print(f"❌ Notion 저장 실패! 상세 사유: {response.text}")


# ─────────────────────────────────────────────
# 프롬프트 구성
# ─────────────────────────────────────────────
def build_prompts(seed):
    g1, g2 = seed["genre1"], seed["genre2"]
    genre = f"{g1}, {g2}"
    vocal_type = seed["vocal_type"]

    system_instruction = f"""너는 감성을 자극하는 음반 회사의 작사가이자 곡의 다이내믹을 설계하는 총괄 프로듀서다.
제시된 시드 데이터를 활용해, 선택된 두 장르({genre})의 비트감과 감정선이 매력적으로 어우러지는 트렌디한 곡을 기획하고 작사하라.
가사는 한 문장이 너무 길지 않으면서도 중독성 있고 세련되게 작성한다.

[우선순위 및 충돌 해결 규칙]
1. 보컬 기본값 vs 장르 룰:
   - 기본 보컬 방향은 과도한 찢어짐(Shrill Belting) 없이 담백하고 매력적인 중저음·절제된 표현(mellow dynamics, controlled vocal, intimate vocal, laid-back)이다.
   - 단, 아래 [장르별 규칙]이 폭발적인 에너지나 특정 창법(예: EDM, Dubstep, Soul, Operatic Pop 등)을 요구해 기본값과 충돌할 경우, **장르별 규칙을 우선** 적용한다.
2. BPM 및 템포 충돌:
   - {g1}의 '권장 템포' 범위 안에서 기준 BPM을 정한다.
   - {g2}는 하프타임/더블타임 또는 리듬·악기 질감으로 융합한다.
3. 시드 충돌:
   - 시간·장소·날씨 시드가 서로 충돌하면 **장소·시간 시드를 우선**하고, 실제 날씨는 분위기 참고용으로만 사용한다.
4. 메타 태그 기호 통일:
   - 가사 내 모든 구조·악기·보컬 지시어는 반드시 대괄호(`[ ]`)만 사용한다. (`< >` 및 마크다운 `**` 사용 금지)
   - 각 섹션 시작 부분에 보컬/악기 지시를 집중 배치하고, 가사 중간에는 과도한 태그 남발을 피한다.
   - 고음이나 호흡 조절이 필요한 구간에만 `,` `.`를 적절히 배치한다.
5. 한국어 가사 규칙:
   - 한국어 발음을 영문 로마자로 표기하지 않는다. 순수 한국어 문장과 자연스러운 영단어 훅(Hook)만 사용한다. (단, Latin 등 장르 특성상 자연스러운 스페인어 추임새·훅은 예외)
6. 이스터 에그:
   - Verse 파트 중 한 곳에 '~할 겸'(예: 바람 쐴 겸, 생각 지울 겸) 표현을 자연스럽게 딱 1회 삽입한다.
7. 장르 융합 구조:
   - Verse와 Pre-Chorus는 메인 장르({g1})의 Verse 지시를, Chorus는 서브 장르({g2})의 Chorus 지시를 기본 뼈대로 삼는다.
   - Bridge와 Chorus 3에서는 두 장르의 요소를 함께 결합해 클라이맥스를 만든다.
   - [보컬·가사]와 [솔로 후보]는 두 장르를 자연스럽게 융합해 적용한다.
8. 보컬 구성 ({vocal_type}):
   - Mixed Duet이면 각 섹션 시작에 `[Female Vocal]`, `[Male Vocal]`, `[Duet]` 중 해당 파트를 대괄호로 지정하고, 줄을 번갈아 부르거나 겹쳐 부르도록 배분한다.
   - Solo이면 첫 섹션에만 성별/보컬 톤을 지정하고 이후에는 필요한 변화만 태그로 표기한다.
9. 가사 작법:
   - 한 줄은 8~16자 안팎으로 쓴다. (랩·스캣 파트는 예외)
   - Chorus의 핵심 훅 문구를 하나 정해 Chorus 1·2·3에서 2~3회 반복한다.
   - 시드의 영어 단어를 그대로 가사에 쓰지 말고, 구체적인 장면과 행동으로 풀어서 표현한다.
   - Verse 1은 장소와 행동이 보이는 구체적인 이미지로 시작하고, Pre-Chorus는 Chorus로 올라가는 상승 장치(짧아지는 줄, 반복, 비워둔 박자)를 둔다.

[장르별 규칙]
- 메인 장르 ({g1}):
{seed["rule1"]}

- 서브 장르 ({g2}):
{seed["rule2"]}

[출력 포맷 — 아래 구분자를 정확히 지켜 출력]

###DETAIL###
제목(Subject: 소재 나열이 아닌 핵심 키워드 1~2단어), 장르(Genre), Tempo(BPM), Key, 악기 구성, 작사 배경 및 분위기 구성을 띄어쓰기 포함 800자 이내로 작성한다.

###PURPOSE###
'작사가의 한마디'로 이 곡의 기획 의도와 감정선 흐름을 자연스럽게 소개한다.

###SUNO###
Suno AI의 'Style of Music' 입력란용 영어 키워드 문자열.
- 핵심 장르, 템포, 시그니처 악기, 사운드 질감 순서로 **중요한 키워드를 앞쪽에 배치**한다.
- 300~500자 권장 (절대 900자 초과 금지).
- **보컬 관련 키워드는 절대 적지 않는다** (보컬은 VOCAL 섹션에 분리).

###EXCLUDE_STYLES###
Suno AI가 피해야 할 요소를 영어 키워드(쉼표 구분)로 작성한다.
- 기본 배제 후보: `shrill soprano, harsh screaming, muddy mix, off-key, excessive reverb`
- 단, 선택된 장르({genre})의 핵심 특징과 충돌하는 키워드는 배제 목록에 넣지 않는다.

###VOCAL###
이 곡에 어울리는 보컬 스타일을 영어로 작성한다. (150~280자)
형식: [성별/구성], [음역 및 톤], [창법 및 감정 전달 스타일] (시드의 보컬 구성을 반영할 것)

###IMAGE###
이 곡의 16:9 유튜브 썸네일 생성용 상세 프롬프트 (한국어, 300~500자).
- "16:9 비율의 유튜브 뮤직 썸네일 이미지를 만들어 주세요."로 문장을 시작한다.
- 구체적인 장면, 색감 팔레트, 조명, 카메라 구도를 묘사한다.
- 인물이 등장한다면 수수하고 트렌디한 한국 20대 스타일로 묘사한다.
- 이미지 안에 노래 제목이나 어떤 텍스트도 넣지 말 것(no text, no typography)을 명시한다.

###LYRICS###
곡 구조는 반드시 아래 11개 섹션으로 구성한다.
`[Intro] - [Verse 1] - [Pre-Chorus 1] - [Chorus 1] - [Verse 2] - [Pre-Chorus 2] - [Chorus 2] - [Bridge] - [Instrumental Solo] - [Chorus 3] - [Outro]`
- `[Instrumental Solo]`는 `[Instrumental Solo: (악기명)]` 형태로 쓰고, 두 장르의 '솔로 후보' 중 하나를 골라 악기명을 적는다.
- EDM/Dubstep처럼 드롭 구간이 핵심인 장르라도 `[Chorus]`에 짧은 훅이나 챈트 가사를 유지해 곡 구조를 완성한다.
- 전체 분량은 대괄호 태그와 가사를 포함해 **1,200자 ~ 2,400자** 사이로 작성하며, 반복 구간도 축약하지 않고 모두 적는다.

###TAG###
유튜브 노출용 트렌디 해시태그를 한글과 영어 섞어서 정확히 30개 작성한다. `#` 없이 쉼표(`, `)로만 구분한다.

###UPLOAD###
유튜브 업로드용 요약 양식으로 작성한다. 괄호 안의 안내문은 이번 곡의 실제 내용으로 바꿔 채우고, 괄호 자체는 출력하지 않는다.
- 해시태그 5개: 제목 단어 제외, 한영 중복 제외, 유튜브 검색 노출 우선 키워드 5개 (`#태그1 #태그2 #태그3 #태그4 #태그5`)
- 빈 줄 후: 작사가의 한마디 (3~5문장)
- 빈 줄 후:
제목: (곡 제목)
장르: (장르)
Tempo: (BPM)
Key: (키)
악기: (주요 악기 구성)
"""

    weather_line = f"- 참고 날씨(서울): {seed['weather']}\n" if seed["weather"] else ""

    user_prompt = f"""<Brainstorming_Seed>
- 장르 조합: {genre} (메인: {g1} / 서브: {g2})
- 기준 날짜 및 시간: {seed["date"]}, {seed["time"]}
{weather_line}- 장소: {seed["place"]}
- 행동·상태: {seed["action"]}
- 감정 아크: Verse({seed["emo1_cat"]} - {seed["emo1"]}) → Chorus({seed["emo2_cat"]} - {seed["emo2"]})
- 보컬 구성: {vocal_type}
</Brainstorming_Seed>

<Action_Steps>
1) 내부적으로 위 시드를 엮은 3가지 스토리라인과 시각 테마를 구상한 뒤 가장 트렌디한 1가지를 확정하라 (내부 추론은 출력하지 말 것).
2) 확정한 아이디어로 시스템 프롬프트의 ###DETAIL### 부터 ###UPLOAD### 까지의 포맷에 맞춰 최종 결과물만 출력하라.
</Action_Steps>"""

    return system_instruction, user_prompt


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def main():
    try:
        genres1 = load_data('data/genres1.json')
        genres2 = load_data('data/genres2.json')
        times = load_data('data/times.json')
        emotions1 = load_data('data/emotions1.json')
        actions = load_data('data/actions.json')
        places = load_data('data/places.json')
        genre_rules = load_data('data/genre_rules.json')
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return

    max_genre_retries = 100
    selected_genre1, selected_genre2 = None, None
    for _ in range(max_genre_retries):
        g1 = get_random_item(genres1)
        g2 = get_random_item(genres2)
        if not is_unwanted_combination(g1, g2):
            selected_genre1, selected_genre2 = g1, g2
            break

    if not selected_genre1:
        print("❌ 유효한 장르 조합을 찾는 데 실패했습니다.")
        return

    (emo1_cat, emo1), (emo2_cat, emo2) = get_two_distinct_emotions(emotions1)

    seed = {
        "genre1": selected_genre1,
        "genre2": selected_genre2,
        "rule1": genre_rules.get(selected_genre1, f"- {selected_genre1}의 특성을 살려 편곡해."),
        "rule2": genre_rules.get(selected_genre2, f"- {selected_genre2}의 특성을 살려 편곡해."),
        "date": datetime.now().strftime("%Y년 %m월 %d일"),
        "time": get_random_item(times),
        "weather": get_seoul_weather(),
        "place": get_random_item(places),
        "action": get_random_item(actions),
        "emo1_cat": emo1_cat, "emo1": emo1,
        "emo2_cat": emo2_cat, "emo2": emo2,
        "vocal_type": random.choice(["Female Solo", "Male Solo", "Female Solo", "Male Solo", "Mixed Duet"]),
    }

    selected_genre = f"{selected_genre1}, {selected_genre2}"
    system_instruction, user_prompt = build_prompts(seed)

    print(f"\n[1] 생성된 시드 프롬프트:\n{user_prompt}\n")

    best = None  # (score, data, fatal, warnings)

    for attempt in range(MAX_RETRIES):
        print(f"\n[2] Gemini 가사 생성 중... (시도 {attempt + 1}/{MAX_RETRIES})")
        result_data, status = generate_lyrics_with_gemini(system_instruction, user_prompt)

        if status in ("no_key", "no_model", "api_error"):
            print("🛑 재시도해도 해결되지 않는 상태라 생성을 중단합니다.")
            break

        if status == "parse_error" or not result_data:
            print("   ⚠️ 결과를 파싱하지 못했습니다. 재시도합니다.")
        else:
            fatal, warnings = validate_result(result_data, seed["vocal_type"])
            for w in warnings:
                print(f"   ℹ️ 경고: {w}")

            score = len(fatal) * 10 + len(warnings)
            if result_data.get("lyrics", "").strip() and (best is None or score < best[0]):
                best = (score, result_data, fatal, warnings)

            if not fatal:
                print("   ✅ 치명적 오류 없음! 검증 통과.")
                break
            print(f"   ⚠️ 검증 미달 ({' / '.join(fatal)})")

        if attempt < MAX_RETRIES - 1:
            print("   ⏳ 10초 대기 후 재시도합니다...")
            time.sleep(10)

    if best is None:
        print("❌ 유효한 데이터를 생성하지 못해 파이프라인을 종료합니다.")
        return

    _, final_data, final_fatal, final_warnings = best
    notes = [f"[오류] {x}" for x in final_fatal] + [f"[경고] {x}" for x in final_warnings]
    if final_fatal:
        print("⚠️ 모든 시도에서 치명적 오류가 남아, 이슈가 가장 적은 결과를 저장합니다.")

    print("\n[3] Notion 저장 시도...")
    save_to_notion(seed["date"], selected_genre, seed["weather"], user_prompt, final_data, notes)


if __name__ == "__main__":
    main()
