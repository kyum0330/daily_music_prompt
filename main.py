import json
import random
import os
from datetime import datetime
import requests
import google.generativeai as genai # Gemini 라이브러리 불러오기

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
    """Gemini API를 호출하여 작사를 요청하는 함수"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ GEMINI_API_KEY가 설정되지 않아 가사를 생성할 수 없습니다."
    
    # Gemini 세팅
    genai.configure(api_key=api_key)
    
    try:
        # 1. 내 API 키로 당장 사용할 수 있는 모델 목록을 구글 서버에서 모두 가져옵니다.
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
                
        print(f"🔍 [시스템] 현재 사용 가능한 Gemini 모델 목록: {available_models}")
        
        # 2. 목록 중에서 가장 적합한 텍스트 생성 모델을 자동으로 찾아냅니다.
        target_model = None
        
        # 최우선 순위: 빠르고 똑똑한 1.5 flash 계열
        for name in available_models:
            if 'gemini-1.5-flash' in name:
                target_model = name
                break
                
        # 차선책: 그냥 gemini라는 이름이 들어간 텍스트 생성 가능 모델 아무거나!
        if not target_model:
            for name in available_models:
                if 'gemini' in name and 'vision' not in name:
                    target_model = name
                    break
                    
        if not target_model:
            return "⚠️ 텍스트 생성을 지원하는 모델을 찾지 못했습니다."
            
        print(f"🎯 [시스템] 선택된 최적의 모델: {target_model}")
        
        # 3. 자동으로 찾은 모델을 적용하여 실행합니다.
        model = genai.GenerativeModel(target_model)
        
        # 저에게 천재 작사가 역할을 부여합니다!
        system_instruction = (
            "너는 감성을 자극하는 세계적인 엔터테이먼트 음반 회사의 천재적인 작사가에요. "
            "다음 주어진 상황, 장르, 감정, 날씨를 바탕으로 "
            "요즘 트렌드에 대해서 한번 조사를 하여, 그에 맞는 분위기를 맞춰야해요."
            "독창적이고 음악의 리듬감이 느껴지는 노래 제목과 노래 가사를 작성해주세요."
            "이때, 장르와 Tempo 그리고 Intro와 각종 세부사항도 적어주세요."
        )
        full_prompt = f"{system_instruction}\n\n[작사 배경]\n{prompt}"
        
        # Gemini에게 요청 보내고 답변 받기
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Gemini API 호출 중 에러 발생: {e}"

def main():
    try:
        genres = load_data('data/genres.json')
        times = load_data('data/times.json')
        emotions1 = load_data('data/emotions1.json')
        actions = load_data('data/actions.json')
        places = load_data('data/places.json')
        emotions2 = load_data('data/emotions2.json')
    except FileNotFoundError as e:
        print(f"데이터 파일을 찾을 수 없습니다: {e}")
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
        f"'{selected_genre} 장르의 {current_date} {selected_time}의 "
        f"{selected_emotion1} {selected_action} {selected_place}에서의 "
        f"{selected_emotion2} {current_weather} 날'의 느낌으로 가사를 작성해줘."
    )

    print("✨ 1. 오늘의 자동 생성 음악 프롬프트 ✨")
    print(final_prompt)
    print("\n" + "="*50 + "\n")
    
    print("🤖 2. Gemini가 영감을 받아 가사를 작사 중입니다...\n")
    lyrics = generate_lyrics_with_gemini(final_prompt)
    
    print("✨ 3. Gemini가 완성한 가사 ✨")
    print(lyrics)

if __name__ == "__main__":
    main()
