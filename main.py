import json
import random
import os
from datetime import datetime
import requests

def load_data(file_path):
    """JSON 파일에서 데이터를 읽어오는 함수"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_seoul_weather():
    """현재 서울 날씨를 가져오는 함수 (임시 버전)"""
    # 실제 날씨를 가져오려면 OpenWeatherMap 등의 API 키가 필요합니다.
    # 추후 API 키를 발급받으시면 아래 주석을 풀고 사용하시면 됩니다.
    """
    api_key = os.environ.get("WEATHER_API_KEY") # GitHub Secrets에서 가져오기
    if api_key:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Seoul&appid={api_key}&lang=kr"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['weather'][0]['description'] # 예: '맑음', '가벼운 비'
    """
    # 현재는 테스트를 위해 임시로 '비 오는'을 반환합니다.
    return "비 오는"

def main():
    # 1. 500개의 항목이 담긴 JSON 데이터 불러오기
    try:
        genres = load_data('data/genres.json')
        times = load_data('data/times.json')
        emotions1 = load_data('data/emotions1.json')
        actions = load_data('data/actions.json')
        places = load_data('data/places.json')
        emotions2 = load_data('data/emotions2.json')
    except FileNotFoundError as e:
        print(f"데이터 파일을 찾을 수 없습니다. 경로를 확인해주세요: {e}")
        return

    # 2. 각 리스트에서 무작위로 하나씩 추출하기
    selected_genre = random.choice(genres)
    selected_time = random.choice(times)
    selected_emotion1 = random.choice(emotions1)
    selected_action = random.choice(actions)
    selected_place = random.choice(places)
    selected_emotion2 = random.choice(emotions2)

    # 3. 실시간 정보 가져오기
    # GitHub Actions에서 시간을 'Asia/Seoul'로 맞췄기 때문에 현재 날짜가 정확히 들어갑니다.
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    current_weather = get_seoul_weather()

    # 4. 프롬프트 문장 조합 (우겸님 포맷)
    final_prompt = (
        f"노래를 만들기 위해서 아래의 키워드를 바탕으로 가사를 작성해줘.\n"
        f"'{selected_genre} 장르의 {current_date} {selected_time}의 "
        f"{selected_emotion1} {selected_action} {selected_place}에서의 "
        f"{selected_emotion2} {current_weather} 날'의 느낌으로 가사를 작성해줘."
    )

    print("✨ 오늘의 자동 생성 음악 프롬프트 ✨")
    print(final_prompt)

    # (이후 단계: 이 final_prompt를 Gemini API에 보내고, 그 결과를 Notion API로 보내는 코드가 여기에 추가될 예정입니다.)

if __name__ == "__main__":
    main()
