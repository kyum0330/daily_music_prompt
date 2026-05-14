import json
import random
import os
from datetime import datetime
import requests
import google.generativeai as genai

def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_random_item(data):
    if isinstance(data, dict):
        all_items = []
        for items_in_category in data.values():
            all_items.extend(items_in_category)
        return random.choice(all_items)
    elif isinstance(data, list):
        return random.choice(data)

def get_seoul_weather():
    api_key = os.environ.get("WEATHER_API_KEY") 
    if api_key:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q=Seoul&appid={api_key}&lang=kr"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data['weather'][0]['description']
        except Exception as e:
            print(f"날씨 정보를 가져오는 중 에러 발생: {e}")
    return "날씨 정보가 오류가 생겼음"

def generate_lyrics_with_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ GEMINI_API_KEY가 설정되지 않아 가사를 생성할 수 없습니다."
    
    genai.configure(api_key=api_key)
    
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        target_model = None
        for name in available_models:
            if 'gemini-1.5-flash' in name:
                target_model = name
                break
        if not target_model:
            for name in available_models:
                if 'gemini' in name and 'vision' not in name:
                    target_model = name
                    break
        
        if not target_model:
            return "⚠️ 텍스트 생성을 지원하는 모델을 찾지 못했습니다."
            
        model = genai.GenerativeModel(target_model)
        
        # 큰따옴표 3개(""")를 사용하면 작성한 줄바꿈과 포맷이 제미나이에게 그대로 전달됩니다.
        system_instruction = """너는 감성을 자극하는 세계적인 엔터테인먼트 음반 회사의 천재적인 작사가에요.
독창적이고 음악의 리듬감이 느껴지는 노래 제목과 노래 가사가 필요해요.
다음 주어진 상황, 장르, 감정, 날씨를 바탕으로 
요즘 트렌드를 조사하여 그에 맞는 분위기로 작사를 하고,
그 분위기가 어떤 내용인지 세부 내용으로 알려주세요.
이때, 장르와 Tempo 그리고 Intro와 section과 각종 세부사항(시간,악기 및 분위기 구성)도 적어주세요.
그 후, '작사가의 한마디'를 통해 종합적인 곡의 소개를 부탁합니다.
그리고 세부사항이 가사를 다 적은 후에는 단을 구분하여, 최하단에는 이 노래의 전체적인 곡 내용에 대한 유튜브 노출을 위한 해쉬태그를 #로 나열해서 부탁해요.

[출력 및 포맷 규칙]
1. 노래 정보를 적어줄 때 각 항목 제목에 마크다운 굵게 표기(**)는 절대 사용하지 마세요.
2. 노래 정보는 반드시 아래의 양식으로 정리해줘.
3. 노래 제목과 노래 정보, 작사 배경 및 분위기 구성은 띄어쓰기 포함 총 1000자 이내로 부탁해요.
4. 노래 가사를 적기 전에, 작사가의 한마디를 통해 종합적인 곡 소개를 적어주세요.
5. 노래 가사에서는 각 항목의 구간 시간, 악기 및 분위기 구성을 적어주세요. 이때 가사 외의 데이터는 영어로 <> 속에 넣어서 표현해주세요.
6. 세부 항목이 적힌 노래 가사가 끝난 하단에는 단을 따로 구분하여, **Intro** 와 같은 구분에 대한 것과 세부 항목 없는 노래 가사만을 파트별 단 구분하여 적어주세요.
7. 마지막으로 이 노래의 전체적인 곡 내용과 분위기에 알맞게 유튜브 노출을 위한 해쉬태그를 나열해서 정리 부탁해요.

* 노래 제목(Subject) : 

* 장르(Genre) : 

* Tempo : 

* Key : 

* 악기 구성(Instrument composition) : """

        full_prompt = f"{system_instruction}\n\n[작사 배경]\n{prompt}"
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Gemini API 호출 중 에러 발생: {e}"

def save_to_notion(date_str, genre, weather, prompt, lyrics):
    """노션 저장 함수 (문단 단위 스마트 쪼개기 적용)"""
    notion_token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")

    if not notion_token or not database_id:
        print("❌ Notion 토큰이나 데이터베이스 ID 설정이 누락되었습니다.")
        return

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    page_title = f"{date_str} ({genre})"
    
    # 기본 제목 블록 세팅
    children_blocks = [
        {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": "🎶 Gemini 생성 가사"}}]}}
    ]
    
    # 🌟 핵심 로직: 엔터 두 번(\n\n)을 기준으로 파트/문단을 나눕니다.
    paragraphs = lyrics.split('\n\n')
    
    for para in paragraphs:
        para = para.strip() # 앞뒤 쓸데없는 공백 제거
        if not para:
            continue # 내용이 없는 빈 문단은 건너뜀
            
        # 안전장치: 혹시라도 한 문단이 2000자를 넘으면 단어가 안 잘리게 안전하게 쪼갬
        if len(para) > 2000:
            # 2000자 이내의 가장 가까운 줄바꿈(\n)이나 공백을 찾아 끊어주는 스마트 슬라이싱
            while len(para) > 2000:
                split_idx = para.rfind('\n', 0, 2000)
                if split_idx == -1:
                    split_idx = para.rfind(' ', 0, 2000)
                if split_idx == -1:
                    split_idx = 2000 # 공백도 없으면 어쩔 수 없이 2000자에서 커팅
                
                chunk = para[:split_idx].strip()
                children_blocks.append(
                    {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": chunk}}]}}
                )
                para = para[split_idx:].strip()
                
        # 일반적인 경우: 나누어진 파트 그대로 하나의 노션 문단 블록으로 쏙!
        if para:
            children_blocks.append(
                {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": para}}]}}
            )

    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Title": {"title": [{"text": {"content": page_title}}]},
            "Weather": {"rich_text": [{"text": {"content": weather}}]},
            "Generated Prompt": {"rich_text": [{"text": {"content": prompt}}]}
        },
        "children": children_blocks
    }

    print("🚀 Notion API 호출 중...")
    response = requests.post('https://api.notion.com/v1/pages', headers=headers, json=data)
    
    print(f"📊 [결과] HTTP 상태 코드: {response.status_code}")
    if response.status_code == 200:
        print("✅ Notion 저장 성공!")
    else:
        print(f"❌ Notion 저장 실패! 상세 사유: {response.text}")
        
def main():
    try:
        genres = load_data('data/genres.json')
        times = load_data('data/times.json')
        emotions1 = load_data('data/emotions1.json')
        actions = load_data('data/actions.json')
        places = load_data('data/places.json')
        emotions2 = load_data('data/emotions2.json')
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return

    selected_genre = get_random_item(genres)
    selected_time = get_random_item(times)
    selected_emotion1 = get_random_item(emotions1)
    selected_action = get_random_item(actions)
    selected_place = get_random_item(places)
    selected_emotion2 = get_random_item(emotions2)

    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    current_weather = get_seoul_weather()

    final_prompt = (
        f"{selected_genre} 장르의 {current_date} {selected_time}의 "
        f"{selected_emotion1} 한 {selected_action} 하는 {selected_place}에서의 "
        f"{selected_emotion2} {current_weather} 날'의 느낌으로 가사를 작성해줘요."
        f"Intro, Chorus, Verse1, Verse2, Bridge, Outro 등으로 구분해서 한곡 완성해주세요."
    )

    print(f"\n[1] 생성된 프롬프트: {final_prompt}")
    print("\n[2] Gemini 가사 생성 중...")
    lyrics = generate_lyrics_with_gemini(final_prompt)
    
    print("\n[3] Notion 저장 시도...")
    save_to_notion(current_date, selected_genre, current_weather, final_prompt, lyrics)

if __name__ == "__main__":
    main()
