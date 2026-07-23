import json
import random
import os
import re
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

# [기존 유지 항목]: 날씨 정보를 가져오는 함수
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
    return "날씨 정보 오류"

# [업데이트 항목]: 원하지 않는 장르 조합 확인
def is_unwanted_combination(genre1, genre2):
    """ 원하지 않는 장르 조합인지 확인하는 함수입니다. 순서에 상관없이 매칭되도록 검사합니다. """
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
    
def generate_lyrics_with_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("🚨 GEMINI_API_KEY가 설정되지 않았습니다.")
        return {}
    
    genai.configure(api_key=api_key)
    
    # [업데이트 항목]: 더욱 디테일해진 메타태그 및 프롬프트
    system_instruction = """[멜로디 및 사운드 디자인 (Meta Tags) 강제 규칙]
너는 감성을 자극하는 세계적인 엔터테인먼트 음반 회사의 천재적인 작사가 뿐 아니라 곡의 다이내믹을 설계하는 총괄 프로듀서에요.
요즘 트렌드를 조사한 후에, 제시된 [장르], [시간], [장소], [감정], [행동], [날씨] 데이터를 활용해, 선택된 두 장르의 비트감과 감정선이 가장 매력적으로 어우러지는 세련된 곡을 만들어야 해요.
이때, 가사는 한 문장들이 너무 길지 않지만 중독성이 있고, 트랜디한 느낌으로 작성을 해주세요.

[작사 핵심 및 메타 태그 규칙]
1. 보컬 및 페르소나: [Smooth alto female vocal, deep calm voice, low octave, subdued pitch, clean natural voice, clear diction, effortless singing, gentle resonance, subtle vocal runs, relaxed delivery, mellow dynamics, soft instrumentation, chill R&B, Solo]. 
Suno AI가 흔한 중-고음 소프라노를 출력하지 않도록, 과도한 기교 없이 담백하고 매력적인 중저음 보컬 톤을 강제해요. 보컬과 코러스 부분에 대해서는 다음 내용을 참고해주세요.

    1-1. 메타 태그 적용 (Lyrics 영역)
        곡이 고조되는 코러스(후렴구)나 브릿지 부분에 단순히 [Chorus]라고만 적으면 AI가 마음대로 소리를 내지를 확률이 높습니다. 이럴 때는 대괄호 안에 보컬의 창법을 직접 제한해 주세요. 상황에 맞게 아래 태그 중 하나를 선택하여 적용하십시오.
        
- [Soft Chorus]: 부드럽게 부르는 후렴구
- ​[Clear Smooth Falsetto]: 공기 소리를 줄이고 목소리의 선명도를 높인 맑고 부드러운 가성
- ​[Warm Gentle High Notes]: 쨍하지 않고 따뜻하게 감싸듯 올라가는 편안한 고음
- ​[Controlled Vocal]: 감정은 담되 에너지가 과하지 않게 절제된 보컬
- [mellow dynamics]: 튀는 구간 없이 차분하고 부드러운 다이내믹
- [soft vocal delivery]: 처음부터 끝까지 부드럽게 내뱉는 보컬 표현
- [laid-back]: 여유롭고 힘을 뺀 스타일
- [intimate vocal]: 귀에 대고 속삭이듯 가까운 느낌의 보컬

    1-2. 음악 스타일 제한 (Style of Music 영역 - 보컬)
        곡 전체의 스타일을 지정하는 칸에도 보컬의 에너지를 낮춰주는 긍정형 키워드를 추가하여 AI가 과호흡을 하지 않도록 진정시켜야 합니다. 아래 키워드를 조합하여 사용하십시오.
- mellow dynamics: 튀는 구간 없이 차분하고 부드러운 다이내믹
- soft vocal delivery: 처음부터 끝까지 부드럽게 내뱉는 보컬 표현
- laid-back: 여유롭고 힘을 뺀 스타일
- intimate vocal: 귀에 대고 속삭이듯 가까운 느낌의 보컬

    1-3. 악기 및 장르의 에너지 조절 (Style of Music 영역 - 반주)
        보컬이 쨍해지는 또 다른 결정적인 이유는 반주(악기) 소리가 너무 크거나 강하기 때문입니다. 
        배경 음악이 웅장하고 시끄러워지면 보컬이 악기 소리에 묻히지 않기 위해 자동으로 소리를 지르게끔 설계되어 있습니다.
        이를 방지하기 위해 아래 키워드를 추가하여 반주의 에너지를 살짝 낮춰주십시오.
- chill, lo-fi, soft instrumentation, minimalist 

    1-4. 고음이 들어가는 부분에서는 단어 사이 사이에 ',', '.'를 삽입하여 의도적으로 숨을 고르게 만들게 합니다.

    1-5. 고음부에서 AI가 쨍하게 소리를 내지르는 현상(Belting)을 방지하고 싶다면, 아래의 규칙을 엄격히 적용하여 프롬프트를 자동 생성하십시오.

- 말하듯 힘을 완전히 빼는 파트: [Subdued Vocal]
- 코러스/고음 진입 파트 (에너지 억제): [Controlled Alto Vocal] (음역대를 높이지 않고 중저음역대 안에서 에너지만 살짝 조절하도록 지시합니다.)
              
2. 비트 및 다이내믹 : "R&B, Electro Pop, Moombahton, Synth Pop, Baltimore Club, UK Garage, Hip Hop, Jersey Club, Liquid Drum & Bass, Favela Funk, House, Contemporary R&B, Miami Bass, Old-school Hip Hop, City Pop, New Jack Swing" 중에서 선택된 두 개의 Genre에 알맞게 하단의 비트 및 다이내믹을 참고하여 비트 및 다이내믹을 적용해주면 좋겠어요. 이때 두 개의 장르가 선택되므로, 두 장르의 특징을 하이브리드 형태로 신선하게 믹스하거나, Verse와 Chorus에 각각의 장르적 매력이 교차(예: Verse는 R&B 무드, Chorus는 House 비트)되도록 가사 속 메타 태그([])를 창의적으로 조합해 주세요.

(비트 및 다이내믹 세부내용은 기존과 동일하게 유지 - 분량상 생략 없이 모두 내부 지시어로 인지할 것)

3. 이스터 에그 (행동 교차 룰): Verse 파트 중 한 곳에 반드시 '~할 겸' (예: 바람 쐴 겸, 생각 지울 겸 등)이라는 표현을 딱 한 번 자연스럽게 삽입해서 주인공의 무심하고 여유로운 태도를 연출해요.

4. 곡 중간(Bridge 이후 등)에 해당 장르를 가장 잘 나타내는 **<Instrumental Solo> (악기 솔로 구간)**를 최소 1회 이상 강제로 삽입해요.

5. 전체적으로 매 가사 부분마다 보컬에 대한 상세한 내용을 []을 통해서 최대한 상세하게 표현합니다. 이때 [한국어 가사 전용 규칙 - 로마자 표기 절대 금지]
   - 모든 한국어 가사를 작성할 때, 가사 뒤나 옆에 알파벳으로 된 발음 표기(예: Romanization, (Neuj-eun o-hu-ui...))를 절대, 절대로 추가하지 마십시오.
   - 오직 순수한 한국어 문장과 의도된 영단어 훅(Hook)으로만 가사를 구성해야 하며, 괄호 묶음이나 주석 형태의 영어 발음 기호는 완전히 배제하십시오.

6. [장르]별 시그니처 멜로디 패턴 강제
주어진 [장르]의 정체성을 보여주는 '핵심 악기 + 보컬 스타일' 세트를 반드시 곡 전반에 깔아둬요. 이때 가사에 작성할때는 영어로 작성해주고, 그 해당 내용을 ()를 통해 부가설명은 하지않도록 해요.

6-1. Dance Pop
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (4/4 댄스 그루브 설계): 
- Verse 파트에서는 스네어를 가볍게 쓰고 묵직한 베이스 라인만으로 미니멀한 공간감을 열어줘. <Punchy synth bass, light percussion>
- Chorus 파트에서는 꽉 찬 4/4 정박자 킥 드럼과 화려한 리드 신스를 터뜨려 에너지를 극대화해. <Four-on-the-floor kick, energetic dance pop drop>
- 악기에 묻히지 않도록 보컬의 딕션을 명확히 살리고, 후렴구에서는 반복적이고 타격감 있는 단어를 배치해.

6-2. Alternative Pop
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (변칙적 팝 리듬 설계): 
- Verse 파트에서는 둔탁한 힙합 드럼이나 어쿠스틱 기타 하나만 배치해 일상적이고 쓸쓸한 무드를 잡아. <Muffled drum loop, raw acoustic guitar>
- Chorus 파트에서는 예상치 못한 타이밍에 거친 신스와 베이스가 쏟아지며 다이내믹을 반전시켜. <Unexpected heavy synth drop, alternative pop climax>
- 가사는 시적인 은유보다 말하듯 툭툭 던지는 대화체(Conversational)로 구성하여 진솔함을 강조해.

6-3. Folk
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (어쿠스틱 서사 설계): 
- Verse 파트에서는 타악기를 완전히 배제하고 섬세한 통기타 핑거피킹 하나만으로 화자를 집중시켜. <Minimalist fingerpicking, no drums>
- Chorus 파트에서는 기타 스트로크가 넓어지고 부드러운 코러스 화음이 합류해 따뜻하게 감싸줘. <Warm acoustic strumming, gentle vocal harmonies>
- 보컬이 호흡을 길게 가져가며 한 편의 서사시를 담담하게 읽어내려갈 수 있도록 가사에 충분한 여유 공간을 둬.

6-4. Indie
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (로파이 밴드 사운드 설계): 
- Verse 파트에서는 공간감 있는 리버브가 걸린 빈티지 일렉 기타로 몽환적이고 날것의 바이브를 연출해. <Vintage indie guitar, atmospheric reverb>
- Chorus 파트에서는 심벌즈와 둔탁한 드럼 사운드가 넓게 퍼지며 벅차오르는 인디 팝 에너지를 만들어. <Crash cymbals, expansive indie pop energy>
- 가사는 개인적이고 독특한 단어들을 조합해, 가성(Falsetto)으로 읊조리듯 부유하는 보컬 톤을 유도해.

6-5. Ballad
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (오케스트라 빌드업 설계): 
- Verse 파트에서는 오직 피아노 선율만으로 시작하여 보컬의 숨소리와 감정선에 귀 기울이게 해. <Solo emotional piano, quiet vocal intro>
- Chorus 파트에서는 웅장한 스트링(현악기)과 리얼 드럼이 한꺼번에 터지며 감정을 폭발시켜. <Grand orchestral strings, powerful ballad climax>
- 가사는 기승전결이 확실하게 폭발적인 고음을 뿜어낼 수 있는 긴 모음(ex: 아, 오)을 후렴구 끝에 배치해.

6-6. Hip Hop
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (붐뱁 & 808 그루브 설계): 
- Verse 파트에서는 일정한 드럼 루프와 깊은 808 베이스 위에 타이트한 랩이 끊기지 않고 이어지게 해. <Heavy 808 bass, steady hip-hop loop>
- Chorus 파트에서는 브라스 샘플이나 강렬한 신스를 얹어 훅(Hook)의 무게감과 존재감을 키워. <Brass sample cuts, catchy hip-hop chorus>
- 멜로디보다는 라임(Rhyme)과 펀치라인의 타격감이 곡을 이끌어갈 수 있도록 단어의 운율을 촘촘히 쪼개.

6-7. Trap
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (하이햇 롤링 & 서브 베이스 설계): 
- Verse 파트에서는 음산한 패드(Pad) 신스와 함께 하이햇을 잘게 쪼개어 긴장감을 극도로 끌어올려. <Fast rolling hi-hats, dark synth pad>
- Chorus 파트에서는 거대하고 묵직한 서브 베이스가 지진처럼 울리며 압도적인 폭발력을 보여줘. <Deep sub-bass drop, aggressive trap energy>
- 오토튠이 걸린 보컬이 스타카토처럼 끊어 치는 셋잇단음표(Triplet) 플로우를 탈 수 있게 단어를 짧게 구성해.

6-8. R&B
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (텐션 & 레이백 그루브 설계): 
- Verse 파트에서는 끈적한 EP(일렉트릭 피아노) 화음과 여백 있는 드럼으로 관능적인 무드를 열어. <Smooth Rhodes piano, laid-back groove>
- Chorus 파트에서는 묵직한 베이스 라인과 화려한 보컬 레이어링(애드리브)을 통해 세련된 공간감을 채워. <Rich vocal layers, groovy R&B bassline>
- 정박자보다 살짝 늦게 부르는 레이백(Layback) 보컬의 유연함을 위해 가사의 모음을 부드럽고 이어지도록 설계해.

6-9. Soul
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (빈티지 아날로그 폭발력 설계): 
- Verse 파트에서는 따뜻한 해먼드 오르간과 핑거스냅만으로 소울풀하고 절제된 감정을 끌어올려. <Warm Hammond organ, subtle finger snaps>
- Chorus 파트에서는 리얼 브라스 섹션과 코러스 콰이어가 가세해 영혼을 토해내는 듯한 에너지를 터뜨려. <Rich brass section, passionate soulful belting>
- 화려한 기교보다 흉성을 활용한 진한 감정선이 중요하므로, 가사에 호소력 있는 외침(Oh, Yeah)을 자연스럽게 섞어.

6-10. Blues
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (12마디 슬로우 셔플 설계): 
- Verse 파트에서는 무겁게 걷는 워킹 베이스와 하이햇으로 쓸쓸하고 건조한 블루스 스케일을 깔아줘. <Slow blues shuffle, walking bassline>
- Chorus 파트에서는 마치 보컬의 아픔에 대답하듯 일렉 기타 솔로가 흐느끼며 다이내믹을 장악해. <Weeping guitar solo, gritty blues energy>
- 삶의 고달픔을 토해내는 거친 톤(Raspy)을 연출할 수 있도록, 가사를 대화하듯 길고 늘어지게 뱉어내.

6-11. Electronic
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (인공적 공간감 & 질감 설계): 
- Verse 파트에서는 아날로그 악기를 완전히 배제하고 차가운 신디사이저 아르페지오로 우주적인 여백을 만들어. <Cold analog synthesizer, spacey arpeggios>
- Chorus 파트에서는 복잡하게 얽힌 전자음 레이어와 묵직한 디지털 킥이 입체적인 클럽 사운드를 터뜨려. <Complex electronic layers, heavy digital kick>
- 보컬에 보코더(Vocoder)나 공간계 이펙트가 깊게 걸려 하나의 악기처럼 들리도록 가사를 기계적으로 반복시켜.

6-12. EDM
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (빌드업 & 빅룸 드롭 설계): 
- Verse 파트에서는 공간을 여는 패드 사운드로 시작해, 점차 스네어 롤(Snare Roll)이 빨라지며 극도의 긴장감(Build-up)을 줘. <Rising snare roll build-up, sweeping filters>
- Chorus(Drop) 파트에서는 가사를 멈추고 거대한 리드 신스와 킥 드럼만으로 페스티벌의 열광을 터뜨려. <Massive big-room drop, explosive EDM lead>
- 코러스 돌입 직전 보컬이 단 하나의 결정적인 캐치프레이즈(Pre-drop Vocal)를 던지며 에너지를 점화하게 가사를 짜.

6-13. House
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (4/4 Four-on-the-floor 그루브 설계): 
- Verse 파트에서는 리드미컬한 하이햇과 퍼커션으로 가볍게 발을 구르게 만드는 그루브를 시작해. <Rhythmic hi-hats, light percussion>
- Chorus 파트에서는 심장 박동처럼 정확한 120 BPM 4/4 킥 드럼과 반복적인 펑키 베이스라인이 곡을 지배해. <Four-on-the-floor kick drum, groovy house bass>
- 깊은 감정 묘사보다는 대중들이 하나 되어 뛰어놀 수 있도록 후렴구에 매우 단순하고 최면적인 단어를 반복해.

6-14. Deep House
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (다크 & 서브 베이스 설계): 
- Verse 파트에서는 뮤트된 재즈 코드와 최소한의 킥 드럼으로 몽환적이고 심연 같은 새벽 무드를 연출해. <Muted synth chords, minimalistic beat>
- Chorus 파트에서는 바닥을 구르는 무거운 서브 베이스(Sub-bass)가 부드럽게 밀려와 공간을 완전히 장악해. <Deep rolling sub-bass, atmospheric deep house>
- 보컬이 고음을 내지 않고 속삭이듯 낮게 깔리도록 가사의 자음을 부드럽고 관능적인 단어들로 구성해.

6-15. Disco
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (옥타브 베이스 & 레트로 댄스 설계): 
- Verse 파트에서는 16비트로 찰랑거리는 펑키 기타 스트로크와 경쾌한 리듬으로 레트로한 도입부를 만들어. <Funky guitar comping, bright disco rhythm>
- Chorus 파트에서는 옥타브를 쉴 새 없이 오르내리는 화려한 베이스라인과 오케스트라 스트링이 파티 분위기를 터뜨려. <Octave disco bassline, sweeping string section>
- 남녀노소 즐길 수 있는 화려한 가성과 떼창(Chorus)이 돋보이도록 가사에 반짝이고 긍정적인 단어를 쏟아내.

6-16. Hyperpop
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (금속성 글리치 & 과잉 자극 설계): 
- Verse 파트에서는 기괴하게 피치(Pitch)가 변하는 보컬과 불규칙한 디지털 노이즈로 불안정하고 장난스러운 텐션을 잡아. <Erratic glitchy beats, distorted noise>
- Chorus 파트에서는 고막을 찌르는 극단적인 금속성 신스와 깨질 듯한 베이스 디스토션을 과부하(Overload)시켜. <Overloaded metallic synth, extreme distortion>
- 오토튠이 한계치까지 걸려 소리가 기계처럼 찢어지도록 가사를 과장되고 초현실적인 감정들로 채워 넣어.

6-17. UK Garage
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (투스텝(2-Step) 쪼개기 설계): 
- Verse 파트에서는 130 BPM 이상의 빠른 템포 속에서 따뜻한 EP 사운드와 함께 R&B 스타일의 여유로운 멜로디를 깔아. <Warm chords, fast underlying tempo>
- Chorus 파트에서는 스네어와 킥이 정박을 교묘하게 피하는 당김음(Syncopation) 투스텝 비트를 터뜨려 바운스를 유도해. <Fast 2-step garage rhythm, wobbly bassline>
- 비트는 빠르지만 보컬은 조급해하지 않고 무심하게(Chill) 박자를 타도록 가사에 세련된 영단어 훅을 섞어.

6-18. Jersey Club
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (5-Kick 바운스 & 샘플 촙 설계): 
- Verse 파트에서는 침대 스프링이 튀는 듯한 사운드나 잘게 썰린(Chopped) 보컬 샘플만으로 리드미컬한 여백을 줘. <Chopped vocal samples, bed squeak sound>
- Chorus 파트에서는 심장을 때리는 특유의 '쿵-쿵-쿵-쿵쿵' 하는 저지 클럽 킥 패턴을 폭발시켜 무조건 춤추게 만들어. <Bouncy Jersey Club kick pattern, heavy sub-bass>
- 긴 문장보다 짧게 끊어지는 '찰진' 단어들을 배치해 보컬이 드럼의 일부처럼 쫀득한 스타카토로 들리게 해.

6-19. Dubstep
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (하프타임 워블 베이스 설계): 
- Verse 파트에서는 극도로 느리고 서늘한 하프타임(Halftime) 리듬 속에 음산한 앰비언트 사운드를 깔아 폭풍 전야를 표현해. <Slow halftime drum, dark ambient intro>
- Chorus(Drop) 파트에서는 금속이 갈리는 듯한 공격적이고 기괴한 워블 베이스(Wobble Bass)가 포효하며 에너지를 찢어버려. <Aggressive wobble bass drop, heavy screeching synth>
- 후렴구에 노래가 거의 없이, 보컬 샘플을 괴성이나 효과음처럼 컷(Cut)하여 비트와 함께 박살 나도록 연출해.

6-20. Industrial
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (기계 소음 & 메탈릭 비트 설계): 
- Verse 파트에서는 공장의 쇳덩이가 부딪히는 소리나 건조한 기계 파열음을 드럼 비트 대신 사용해 억압적인 무드를 줘. <Cold metallic noise beat, grinding industrial ambiance>
- Chorus 파트에서는 왜곡(Distortion)된 드럼과 찢어지는 베이스가 무자비하게 짓누르며 아방가르드한 파괴력을 보여. <Heavy bass distortion, crushing mechanical beat>
- 보컬이 멜로디를 부르기보다 감정을 거세한 채 차갑고 건조하게 읊조리거나(Monotone) 샤우팅하도록 철학적 가사를 써.

6-21. Jazz
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (어쿠스틱 스윙 & 즉흥 연주 설계): 
- Verse 파트에서는 드럼 브러시의 부드러운 사운드와 업라이트 베이스의 워킹(Walking) 라인으로 유연한 공간을 열어. <Soft brushed drums, smooth walking bassline>
- Chorus 파트에서는 브라스(트럼펫, 색소폰)가 메인 테마를 유니즌(Unison)으로 연주하며 경쾌한 스윙 리듬을 터뜨려. <Catchy brass section, upbeat swing feel>
- 정해진 박자를 넘어 보컬이 자유롭게 박자를 밀고 당기는(Rubato) 스캣(Scatting)을 할 수 있도록 가사에 리듬감 있는 의성어를 넣어.

6-22. Operatic Pop
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (팝 퍼커션 & 시네마틱 오케스트라 설계): 
- Verse 파트에서는 현대적인 팝 비트 위에 잔잔한 피아노와 첼로를 얹어 고전적이고 서정적인 도입부를 만들어. <Modern pop percussion, subtle cello and piano>
- Chorus 파트에서는 대편성 오케스트라와 장엄한 합창(Choir)이 결합되어 한 편의 영화 클라이맥스처럼 웅장하게 터져. <Grand orchestral arrangement, cinematic choir swell>
- 보컬이 팝의 가성과 성악의 벨칸토(강력한 두성/흉성)를 오가며 운명적이고 장엄한 서사를 뿜어내도록 단어를 극적으로 써.

6-23. Lo-fi
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (더스티 바이닐 & 칠아웃 설계): 
- Verse 파트에서는 LP판의 타닥거리는 노이즈(Vinyl Crackle)와 필터가 걸려 뭉툭해진 킥 드럼으로 포근한 여백을 줘. <Dusty vinyl crackle, muffled lo-fi beat>
- Chorus 파트에서는 따스하게 먹먹한 EP 피아노 화음이 느슨하게 얹히며 나른하고 편안한 칠아웃(Chill-out) 무드를 완성해. <Warm EP chords, relaxed 70BPM tempo>
- 긴장감을 완전히 빼고 화자가 혼잣말을 하듯 허밍(Humming)하거나 속삭이도록 일상적이고 쓸쓸한 가사로 여백을 채워.

6-24. Afrobeat
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (폴리리듬 & 최면적 그루브 설계): 
- Verse 파트에서는 서아프리카 토속 타악기들이 겹겹이 쌓인 폴리리듬(Polyrhythm)으로 본능적인 텐션을 끓어올려. <Polyrhythmic percussion, driving tribal rhythm>
- Chorus 파트에서는 반복적이고 끈적한 일렉 기타 리프와 두터운 베이스라인이 합류해 최면을 거는 듯한 그루브를 터뜨려. <Hypnotic electric guitar, deep afrobeat bassline>
- 복잡한 멜로디 전개보다는 대중이 축제처럼 따라 부를 수 있는 단순하고 챈팅(Chanting, 다 같이 외침)하기 좋은 가사를 반복해.

6-25. Afro-Latin
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (아프로 그루브 & 라틴 브라스 설계): 
- Verse 파트에서는 아프로비트의 타악기 베이스에 라틴 음악의 클라베(Clave) 리듬을 섞어 경쾌한 댄스 스텝을 유도해. <Afro-Latin clave rhythm, upbeat percussion>
- Chorus 파트에서는 화려한 쿠반 브라스(트럼펫, 트롬본) 섹션이 폭발하며 한여름 밤의 정열적인 카니발을 완성해. <Festive Cuban brass section, energetic carnival vibe>
- 리듬을 타며 섹시하고 활기차게 밀어붙일 수 있도록 가사에 라틴어 추임새나 역동적인 리듬 단어들을 밀도 있게 배치해.

6-26. Latin
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (콩가 퍼커션 & 플라멩코 기타 설계): 
- Verse 파트에서는 빠르고 화려한 스패니시 어쿠스틱 기타와 최소한의 콩가 리듬으로 관능적이고 정열적인 긴장감을 줘. <Acoustic flamenco guitar, passionate conga rhythm>
- Chorus 파트에서는 풀 밴드의 타악기가 쏟아지며 라틴 댄스의 극적인 다이내믹과 에너지를 강렬하게 발산해. <Explosive Latin percussion, dramatic dance energy>
- 보컬이 'R' 발음을 강렬하게 굴리거나(Rolling Rs) 뜨겁게 외칠 수 있도록, 정열적이고 치명적인 사랑을 노래하는 단어를 써.

6-27. Latin Pop
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (레게톤 베이스 & 메인스트림 신스 설계): 
- Verse 파트에서는 대중적인 팝 신시사이저 아래에 묵직한 뎀보우(Dembow)/레게톤 비트를 깔아 세련된 그루브를 유지해. <Modern synth pad, reggaeton dembow beat>
- Chorus 파트에서는 훅(Hook) 멜로디를 강조하는 브라이트 신스와 타격감 있는 클럽 베이스가 터지며 대중성을 극대화해. <Catchy bright synth, heavy Latin club bass>
- 라틴 특유의 섹시함은 유지하되, 글로벌 팝 차트에서 통할 수 있도록 보컬이 매끄럽고 리드미컬하게 소화할 수 있는 영어/스페인어 믹스 훅을 줘.

6-28. Reggae
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (스캥크 기타 & 두꺼운 베이스라인 설계): 
- Verse 파트에서는 정박을 비우고 엇박에만 악기가 들어가는 스캥크(Skank) 기타와 림샷으로 느긋한 자메이카 무드를 만들어. <Off-beat skank guitar, relaxed rimshot drum>
- Chorus 파트에서는 가슴을 울리는 극도로 두껍고 부드러운 베이스라인이 곡 전체를 느릿느릿 끌고 가는 그루브를 완성해. <Thick heavy reggae bassline, laid-back groove>
- 박자에 쫓기지 않고 보컬이 정박보다 미세하게 늦게 부르는 여유(Layback)를 가질 수 있도록, 평화롭고 영적인 가사를 넉넉히 배치해.

6-29. Bossa Nova
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (나일론 기타 & 소프트 삼바 설계): 
- Verse 파트에서는 드럼 브러시로 긁는 약한 리듬 위에 클래식 나일론 기타의 당김음(Syncopation) 화음을 부드럽게 얹어. <Soft nylon guitar syncopation, gentle brushed snare>
- Chorus 파트에서는 고급스러운 재즈 코드의 EP 피아노나 가벼운 플루트 선율이 더해져 해변의 산뜻한 바람 같은 다이내믹을 줘. <Sophisticated jazz chords, light flute melody>
- 보컬이 감정을 폭발시키지 않고, 귓가에 조용히 ASMR처럼 읊조릴 수 있도록(Whispering) 아련하고 부드러운 단어로 가사를 채워.

6-30. Funk
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (슬랩 베이스 & 16비트 촙 기타 설계): 
- Verse 파트에서는 베이스 기타 줄을 뜯고 때리는 강력한 슬랩(Slap) 연주와 16비트의 날카로운 촙(Chop) 기타로 텐션을 확 잡아채. <Heavy slap bass groove, sharp 16-bit guitar chops>
- Chorus 파트에서는 리드미컬하게 찌르는 브라스 컷과 파워풀한 킥 드럼이 합쳐져 무조건 몸을 흔들게 만드는 디스코/펑크 파티를 터뜨려. <Punchy brass cuts, explosive funk dance rhythm>
- 보컬이 마치 베이스 기타처럼 스타카토로 글자를 짧게 끊어 부를 수 있도록, 파찰음(ㅋ, ㅌ, ㅍ 등)이 포함된 찰진 영단어 훅을 써.

6-31. Country
[작사 핵심 및 메타 태그 규칙]
1. 비트 및 다이내믹 (밴조 & 어쿠스틱 드라이빙 설계): 
- Verse 파트에서는 단순하고 정직한 4/4박자 드럼 위에 경쾌한 어쿠스틱 기타 스트로크를 깔아 소박하고 편안한 시골길 무드를 줘. <Brisk acoustic guitar strumming, simple 4/4 beat>
- Chorus 파트에서는 밝은 밴조(Banjo) 핑거피킹과 피들(Fiddle/바이올린)이 합류하며 가슴 벅차고 따뜻한 에너지를 터뜨려. <Bright banjo picking, driving country energy>
- 화려한 은유보다는 친구에게 이야기하듯 친근한 스토리텔링(고향, 맥주, 트럭 등 일상 소재)이 담백한 보컬로 전달되게 가사를 써.

###DETAIL###
이 칸에는 노래 제목(Subject), 장르(Genre), Tempo, Key, 악기 구성을 포함한 정보와 작사 배경 및 분위기 구성을 적어주세요. (띄어쓰기 포함 총 800자 이내) 이때 노래 제목은 소재의 나열보다는 키워드 위주로 한개 또는 두개의 단어로 표현해주세요.
* 제목 및 정보 항목에 마크다운 굵게(**)는 절대 사용하지 마요.

###PURPOSE###
이 칸에는 '작사가의 한마디'를 통해 이 곡의 기획 의도와 종합적인 곡 소개를 적어주세요.

###SUNO###
위 DETAIL 부분에 작성한 '장르, Tempo, 악기 구성, 분위기'를 음악 생성 AI(Suno)의 'Style of Music' 란에 바로 복사해 넣을 수 있도록, 영어 키워드 위주로 700~850자로 번역 및 요약해주세요.
* [절대 규칙]: Suno의 Style 입력 한계는 1000자입니다. 따라서 띄어쓰기 포함하여 무조건 800자~900자 사이로 작성하고, 절대 1000자를 넘기지 마세요.
이때, 보컬에 관련된 내용은 작성하지 마세요. (예: Melodic Electronic, Progressive House, 123 BPM, warm synth pad, emotional lead)

###EXCLUDE_STYLES###
이 칸에는 Suno AI가 곡을 생성할 때 절대 사용하지 말아야 할(피해야 할) 요소들을 영어 키워드로 쉼표로 구분하여 작성해주세요. (예: high pitch vocal, belting, screaming, loud brass, aggressive drums). 이 곡의 장르와 분위기에 방해되는 요소들을 200자 이내로 명확히 나열하세요.

###VOCAL###
이 칸에는 해당 노래에 어울리는 보컬 스타일을 영어로 작성해주세요. 이때 톤과 스타일에 대해서는 자세하게 적어주세요.
형식: [성별], [톤], [스타일], [솔로/듀엣/그룹 여부]
* 예시: Female vocal, extremely low-pitched, dark contralto, very heavy chest voice, deep androgynous tone, resonant bassy female voice, husky and thick vocal, Solo.
* 전체 내용은 250~280자로 구체적으로 작성할 것.

###LYRICS###
섹션별 가사: 곡의 구조는 반드시 [Intro] - [Verse 1] - [Pre-Chorus 1] - [Chorus 1] - [Verse 2] - [Pre-Chorus 2] - [Chorus 2] - [Bridge] - [Guitar Solo] - [Chorus 3] - [Outro]의 11개 섹션으로 구성해요. 섹션 표시에 마크다운 굵게(**)는 절대 사용하지 마요. 가사 외의 정보(구간 시간, 악기/분위기)는 반드시 영어로 [ ] 속에 넣어 표현해주세요. 
가사 내 지시어 (Meta Tags) 예시: [Extremely low vocal], [Heavy and dark contralto singing]
* 주의: 한국어 가사 구절 옆에 (U-ri-neun yak-sok...) 같은 로마자 발음 표기나 영어 번역을 절대 덧붙이지 마세요. 오직 순수 한국어와 영어 훅 조합으로만 채워야 합니다.
* [절대 규칙]: Suno의 Lyrics 입력 한계는 5000자입니다. 글자 수 초과를 막기 위해 전체 내용은 띄어쓰기와 지시어, 가사를 모두 포함하여 총 3500자 ~ 4500자 사이로 작성하세요. 절대 4900자를 넘기지 마세요. 최소한 3500자 이상으로 세세하게 작성해야 합니다.
가사가 반복되더라도 축약하지 말고 모든 텍스트를 온전히 다 적어주세요.

###CLEAN_LYRICS###
클린 가사: 위 세부 항목이나 음악 구조(< > 부분) 및 [ ] 메타태그가 모두 제외된, 순수 가사 내용만 복사하기 쉽게 적어주세요. 당연히 알파벳 발음 표기나 괄호 설명 등은 일절 포함되어서는 안 됩니다.

###TAG###
이 곡과 어울리는 유튜브 노출용 트렌디 해쉬태그를 이용해서 한글과 영어 섞어서 정확히 30개 작성해줘요. 이때 번갈아가며 나오도록 하고, 해당 태크마다','를 붙여주고, 노출 가능성이 큰 순서대로 나열해주세요. (예: #하우스, #새벽감성, ...)

###UPLOAD###
유튜브 업로드용 요약 양식으로 작성해주세요. 
형식: [해쉬태그 5개] + [날짜와 감정 기반 짧은 소개글(한글)] + [날짜와 감정 기반 짧은 한글 소개글 영어로 번역] [곡 정보 요약(제목, 장르, Tempo, Key, 악기)] 순서로 가독성 있게 작성해줘요.
"""

    full_prompt = f"{system_instruction}\n\n[작사 배경]\n{prompt}"
    text = ""
    
    # [업데이트 항목]: 동적 API 모델 전환 로직
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print(f"🧐 [참고] 사용 가능한 모델 총 {len(available_models)}개 확인 완료")
        
        preferred_models = [
            'models/gemini-2.5-flash',       
            'models/gemini-1.5-flash',
            'models/gemini-flash-latest'
        ]
        
        success = False
        for model_name in preferred_models:
            matched = [m for m in available_models if model_name.split('/')[-1] in m]
            
            if matched:
                target = matched[0]
                try:
                    print(f"🚀 [{target}] 모델로 생성을 시도합니다...")
                    model = genai.GenerativeModel(target)
                    response = model.generate_content(full_prompt)
                    text = response.text
                    print(f"✅ {target} 생성 성공!")
                    success = True
                    break 
                except Exception as e:
                    print(f"⚠️ {target} 실패 (사유: 할당량 초과 등) -> 다음 모델로 넘어갑니다.")
            else:
                print(f"⚠️ {model_name} 모델은 현재 목록에 없어 건너뜁니다.")
                
        if not success:
            print("❌ 준비된 모든 대체 모델이 할당량 초과로 실패했습니다. 자정이 지나길 기다리거나 결제 연동이 필요합니다.")
            return {}
            
    except Exception as api_e:
        print(f"❌ API 모델 리스트를 불러오지 못했습니다: {api_e}")
        return {}

    try:
        # [업데이트 항목]: 파싱 키워드에 EXCLUDE_STYLES 추가
        markers_base = ["DETAIL", "PURPOSE", "SUNO", "EXCLUDE_STYLES", "VOCAL", "LYRICS", "CLEAN_LYRICS", "TAG", "UPLOAD"]
        for m in markers_base:
            text = re.sub(r'[*_]*#+\s*' + m + r'\s*#*[*_]*', f'###{m}###', text, flags=re.IGNORECASE)

        markers = [f"###{m}###" for m in markers_base]
        extracted = {m.lower(): "" for m in markers_base}
        extracted["image"] = ""

        for marker in markers:
            if marker in text:
                part = text.split(marker)[1]
                min_idx = len(part)
                for other_marker in markers:
                    if other_marker != marker:
                        idx = part.find(other_marker)
                        if idx != -1 and idx < min_idx:
                            min_idx = idx
                
                key = marker.replace("#", "").lower()
                extracted[key] = part[:min_idx].strip()
        
        extracted["image"] = (
            f"이 노래에 맞는 16:9 의 영상 제작에 맞는 썸네일 하나 트랜디한 느낌을 살려서 사람들의 시선을 끌 수 있게 제작 부탁할게요. 인물을 생성해야 한다면, 수수하고 트랜디한 한국 20대 연예인 스타일로 만들어주세요. 이때, 노래에 대한 제목과 설명은 글로 표현하지 말아주세요.\n\n"
            f"[곡 상세 정보]\n{extracted.get('detail', '')}\n\n"
            f"[기획 의도]\n{extracted.get('purpose', '')}"
        )

        print("\n[4] 파싱된 섹션별 글자 수 (0이면 AI가 생성을 빼먹은 것입니다):")
        for k, v in extracted.items():
            print(f" - {k}: {len(v)}자")

        return extracted
        
    except Exception as e:
        print(f"Gemini 데이터 파싱 에러: {e}")
        return {}

def get_chunks(text):
    return [{"text": {"content": text[i:i+2000]}} for i in range(0, max(1, len(text)), 2000)]

# [혼합 항목]: weather 변수는 살려두고 payload에 'Exclude_styles' 속성을 추가했습니다.
def save_to_notion(date_str, genre, weather, prompt, data_dict):
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

    children_blocks = [{"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": "🎶 Gemini 생성 가사 및 곡 구성"}}]}}]
    
    for para in data_dict["lyrics"].split('\n\n'):
        para = para.strip()
        if not para: continue
        
        if len(para) > 2000:
            while len(para) > 2000:
                split_idx = para.rfind('\n', 0, 2000)
                if split_idx == -1: split_idx = para.rfind(' ', 0, 2000)
                if split_idx == -1: split_idx = 2000 
                
                chunk = para[:split_idx].strip()
                children_blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": chunk}}]}})
                para = para[split_idx:].strip()
                
        if para:
            children_blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": para}}]}})
    
    children_blocks.append({"object": "block", "type": "divider", "divider": {}})
    children_blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": data_dict.get("tag", "")[:2000]}}]}})

    clean_lyrics_content = data_dict.get("clean_lyrics", "")
    clean_lyrics_chunks = [{"text": {"content": clean_lyrics_content[i:i+2000]}} for i in range(0, max(1, len(clean_lyrics_content)), 2000)] if clean_lyrics_content else [{"text": {"content": " "}}]

    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Title": {"title": [{"text": {"content": f"{date_str} ({genre})"}}]},
            "Weather": {"rich_text": [{"text": {"content": weather}}]}, # [기존 유지 항목]
            "Generated Prompt": {"rich_text": [{"text": {"content": prompt}}]},
            "Detail": {"rich_text": [{"text": {"content": data_dict.get("detail", "")[:2000]}}]},
            "Purpose": {"rich_text": [{"text": {"content": data_dict.get("purpose", "")[:2000]}}]},
            "Suno": {"rich_text": [{"text": {"content": data_dict.get("suno", "")[:2000]}}]},
            "Exclude_styles": {"rich_text": [{"text": {"content": data_dict.get("exclude_styles", "")[:2000]}}]}, # [업데이트 항목]
            "Image": {"rich_text": [{"text": {"content": data_dict.get("image", "")[:2000]}}]},   
            "Vocal": {"rich_text": [{"text": {"content": data_dict.get("vocal", "")[:2000]}}]},
            "Lyrics": {"rich_text": clean_lyrics_chunks}, 
            "E_Lyrics": {"rich_text": get_chunks(data_dict.get("lyrics", " "))},
            "Tag": {"rich_text": [{"text": {"content": data_dict.get("tag", "")[:2000]}}]},
            "Genre": {"rich_text": [{"text": {"content": genre}}]},
            "Upload": {"rich_text": [{"text": {"content": data_dict.get("upload", "")[:2000]}}]} 
        },
        "children": children_blocks
    }
    
    response = requests.post('https://api.notion.com/v1/pages', headers=headers, json=payload)
    
    print(f"📊 [결과] HTTP 상태 코드: {response.status_code}")
    if response.status_code == 200:
        print("✅ Notion 저장 성공! 모든 데이터가 들어갔습니다.")
    else:
        print(f"❌ Notion 저장 실패! 상세 사유: {response.text}")

def main():
    try:
        # [혼합 항목]: json 파일 로드 (genres1, 2 모두 로드하면서 기존 데이터도 유지)
        genres1 = load_data('data/genres1.json')
        genres2 = load_data('data/genres2.json')
        times = load_data('data/times.json')
        emotions1 = load_data('data/emotions1.json')
        actions = load_data('data/actions.json')
        places = load_data('data/places.json')
        emotions2 = load_data('data/emotions2.json')
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return 
        
    max_retries = 100 
    retry_count = 0
    
    # [업데이트 항목]: 장르 중복/조합 예외 처리 로직 추가
    while retry_count < max_retries:
        selected_genre1 = get_random_item(genres1)
        selected_genre2 = get_random_item(genres2)
        
        if not is_unwanted_combination(selected_genre1, selected_genre2):
            break
            
        retry_count += 1
        print(f"⚠️ 원하지 않는 조합 발생 ({selected_genre1}, {selected_genre2}) -> 다시 뽑습니다.")

    if retry_count == max_retries:
        print("❌ 유효한 장르 조합을 찾는 데 실패했습니다. 원하지 않는 조합(unwanted_pairs) 리스트가 너무 많거나 데이터가 부족한지 확인해 주세요.")
        return

    selected_genre = f"{selected_genre1}, {selected_genre2}"
    selected_time = get_random_item(times)
    selected_emotion1 = get_random_item(emotions1)
    selected_action = get_random_item(actions)
    selected_place = get_random_item(places)
    selected_emotion2 = get_random_item(emotions2)

    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    # [기존 유지 항목]: 날씨 데이터 로드
    current_weather = get_seoul_weather()

    # [혼합 항목]: 날씨 내용 포함 + 액션 스텝 9가지(새로운 프롬프트 구조)
    final_prompt = f"""
<Current_Status>
- 진행 단계: 초기 컨셉 브레인스토밍 및 최종 음원 데이터 완성
- 타겟 결과물: 유튜브 및 오디오 플랫폼 업로드용 기획안 및 가사
</Current_Status>

<Brainstorming_Seed>
- 장르: {selected_genre}
- 배경/시간: {current_date}, {selected_time}
- 날씨: {current_weather}
- 장소 및 상황: {selected_place}에서 {selected_action} 하는 중
- 감정선: {selected_emotion1} 분위기 속에서 느껴지는 {selected_emotion2}
</Brainstorming_Seed>

<Action_Steps>
위의 <Brainstorming_Seed>를 바탕으로 다음 단계를 거쳐 작업을 수행해 줘.

1) [내부 구상]: 이 키워드들을 엮어서 만들 수 있는 매력적인 스토리라인과 시각적 테마를 스스로 3가지 정도 깊이 있게 브레인스토밍 해봐. (이 과정은 너의 내부 추론을 위한 것이며 출력하지 않아도 됨)
2) [최종 도출]: 네가 구상한 아이디어 중 가장 훌륭하고 트렌디한 1가지를 확정해.
3) [포맷 출력]: 확정한 아이디어를 바탕으로, 시스템 프롬프트에서 요구한 ###DETAIL### 부터 ###UPLOAD### 까지의 9가지 필수 구분자 포맷에 맞추어 완벽한 최종 결과물만 출력해.
</Action_Steps>
"""
    
    print(f"\n[1] 생성된 프롬프트: {final_prompt}")
    
    max_retries = 5 
    result_data = {}
    
    for attempt in range(max_retries):
        print(f"\n[2] Gemini 가사 생성 중... (시도 {attempt + 1}/{max_retries})")
        result_data = generate_lyrics_with_gemini(final_prompt)
        
        suno_content = result_data.get("suno", "")
        lyrics_content = result_data.get("lyrics", "")
        
        suno_len = len(suno_content)
        lyrics_len = len(lyrics_content)
        
        print(f"   -> 생성된 Style(Suno) 글자 수: {suno_len}자")
        print(f"   -> 생성된 가사(Lyrics) 글자 수: {lyrics_len}자")
        
        if suno_len < 1000 and 2500 <= lyrics_len <= 4950:
            print("   ✅ 글자 수 한계치 통과! 완벽합니다.")
            break 
        else:
            print("   ⚠️ 글자 수 제한 초과 또는 미달! 다시 생성합니다.")
            if suno_len >= 1000:
                print("      - 사유: Style(Suno) 1000자 초과")
            if lyrics_len > 4950:
                print("      - 사유: 가사(Lyrics) 5000자 초과 위험")
            if lyrics_len < 2500:
                print("      - 사유: 가사(Lyrics)가 너무 짧음 (생략 발생 의심)")
                
    if not result_data.get("lyrics", "").strip():
        print("❌ 유효한 길이의 데이터를 생성하는 데 실패했습니다. 파이프라인을 종료합니다.")
        return

    print("\n[3] Notion 저장 시도...")
    # [기존 유지 항목]: 날씨 변수(current_weather)를 포함하여 노션 함수 호출
    save_to_notion(current_date, selected_genre, current_weather, final_prompt, result_data)

if __name__ == "__main__":
    main()
