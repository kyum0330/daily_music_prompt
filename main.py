import json
import random
import os
from datetime import datetime
import requests

def load_data(file_path):
    """JSON 파일에서 데이터를 읽어오는 함수"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_random_item(data):
    """데이터가 단순 리스트인지, 카테고리형 딕셔너리인지 파악해서 랜덤 추출하는 함수"""
    if isinstance(data, dict):
        all_items = []
        for items_in_category in data.values():
            all_items.extend(items_in_category)
        return random.choice(all_items)
    elif isinstance(data, list):
        return random.choice(data)

def get_seoul_weather():
    """현재 서울 날씨를 가져오는 함수"""
    # GitHub Secrets에 등록될 API 키를 불러옵니다.
    api_key = os.environ.get("WEATHER_API_KEY") 
    
    if api_key:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q=Seoul&appid={api_key}&lang=kr"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                # OpenWeatherMap에서 한국어 날씨 설명(예: '맑음', '튼구름' 등)을 가져옵니다.
                return data['weather'][0]['description']
            else:
                print(f"날씨 API 호출 실패: 상태 코드 {response.status_code}")
        except Exception as e:
            print(f"날씨 정보를 가져오는 중 에러 발생: {e}")
            
    # API 키가 아직 없거나, 서버 오류로 날씨를 못 가져왔을 때의 임시 기본값입니다.
    print("⚠️ 날씨 API 키가 설정되지 않았거나 오류가 발생하여 임시 날씨를 사용합니다.")
    return "비 오는"

def main():
    # 1. JSON 데이터 불러오기
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

    # 2. 무작위 추출하기
    selected_genre = get_random_item(genres)
    selected_time = get_random_item(times)
    selected_emotion1 = get_random_item(emotions1)
    selected_action = get_random_item(actions)
    selected_place = get_random_item(places)
    selected_emotion2 = get_random_item(emotions2)

    # 3. 실시간 정보 가져오기 (날짜 & 날씨)
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    current_weather = get_seoul_weather()

    # 4. 프롬프트 문장 조합
    final_prompt = (
        f"글로벌한 유명한 대형 기획사의 작곡,작사가로서 노래를 만드는 입장이에요.\n"
        f"'{selected_genre} 장르의 {current_date} {selected_time}의 "
        f"{selected_emotion1} {selected_action} {selected_place}에서의 "
        f"{selected_emotion2} {current_weather} 날'의 느낌으로 한국어 가사를 작성해줘."
    )

    print("✨ 오늘의 자동 생성 음악 프롬프트 ✨")
    print(final_prompt)

if __name__ == "__main__":
    main()
