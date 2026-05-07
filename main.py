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
        system_instruction = ("너는 감성을 자극하는 세계적인 엔터테이먼트 음반 회사의 천재적인 작사가야. 가사를 작성해줘."
                                "다음 주어진 상황, 장르, 감정, 날씨를 바탕으로 "
                                "요즘 트렌드에 대해서 한번 조사를 하여, 그에 맞는 분위기를 맞춰야해요."
                                "독창적이고 음악의 리듬감이 느껴지는 노래 제목과 노래 가사를 작성해주세요."
                                "이때, 장르와 Tempo 그리고 Intro와 section과 각종 세부사항도 적어주세요.")
        full_prompt = f"{system_instruction}\n\n[작사 배경]\n{prompt}"
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Gemini API 호출 중 에러 발생: {e}"

def save_to_notion(date_str, genre, weather, prompt, lyrics):
    """노션 저장 및 상세 결과 출력 함수"""
    notion_token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")

    print(f"🔍 [디버그] 노션 토큰 존재 여부: {'Yes' if notion_token else 'No'}")
    print(f"🔍 [디버그] 데이터베이스 ID 존재 여부: {'Yes' if database_id else 'No'}")

    if not notion_token or not database_id:
        print("❌ Notion 토큰이나 데이터베이스 ID 설정이 누락되었습니다.")
        return

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    page_title = f"{date_str} ({genre})"
    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Title": {"title": [{"text": {"content": page_title}}]},
            "Weather": {"rich_text": [{"text": {"content": weather}}]},
            "Generated Prompt": {"rich_text": [{"text": {"content": prompt}}]}
        },
        "children": [
            {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": "🎶 Gemini 생성 가사"}}]}},
            {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": lyrics[:2000]}}]}} # 노션 글자수 제한 방지
        ]
    }

    print("🚀 Notion API 호출 중...")
    response = requests.post('https://api.notion.com/v1/pages', headers=headers, json=data)
    
    # 상세 결과 출력
    print(f"📊 [결과] HTTP 상태 코드: {response.status_code}")
    if response.status_code == 200:
        print("✅ Notion 저장 성공!")
        print(f"🔗 생성된 페이지 URL: {response.json().get('url')}")
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
