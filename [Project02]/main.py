"""음성 식재료 메뉴 추천. 장치 없는 규칙도 이 파일에서 검사할 수 있다."""
import argparse
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from vision import INGREDIENT_NAMES

# 어느 폴더에서 실행하든 main.py가 있는 폴더를 기준으로 파일을 찾는다.
PROJECT_ROOT = Path(__file__).parent
CLARIFY = '그래서 뭘 드시나요? 알려주세요!'
NO_MENUS = '추천할 메뉴가 없어요'
# 사용자에게 익숙한 계란말이·계란볶음밥을 대표 표기로 쓴다. 달걀 표기도 같은 음식으로 비교한다.
ALIASES = {'계란말이': '계란말이', '달걀말이': '계란말이',
           '계란볶음밥': '계란볶음밥', '달걀볶음밥': '계란볶음밥'}
# 재료의 영어 ID·한국어 이름·별칭을 같은 ID로 연결한다. 음식 별칭과는 별개다.
INGREDIENT_ALIASES = {**{k: k for k in INGREDIENT_NAMES},
                      **{v: k for k, v in INGREDIENT_NAMES.items()}, '계란': 'egg', '달걀': 'egg'}

# 선택 문장 판정과 동사 제거에 같은 패턴을 사용해 두 규칙이 어긋나지 않게 한다.
SELECTION_END = r'(?:먹자|먹을게요?|먹을래요?|먹겠습니다|먹기로\s*하자)[.!\s]*$'


# 표시·저장용 이름 정리. 문자열인지 검사하고, 공백을 정리하고, 등록된 음식 별칭을 바꾼다.
def clean_name(value):
    if not isinstance(value, str):
        raise ValueError('이름은 문자열이어야 합니다.')
    # NFKC는 전각 영문 같은 호환 문자 표기를 통일한다. split/join은 줄바꿈·연속 공백을 정리한다.
    value = ' '.join(unicodedata.normalize('NFKC', value).split()).strip()
    if not value or len(value) > 100:
        raise ValueError('이름 길이가 올바르지 않습니다.')
    # 사용자 선호에 따라 계란찜 등 다른 메뉴명에도 익숙한 ‘계란’ 표기를 적용한다.
    value = value.replace('달걀', '계란')
    return ALIASES.get(value.replace(' ', '').casefold(), value)


# 중복 비교용으로는 공백과 영문 대소문자 차이도 없앤다. 등록되지 않은 동의어까지 알지는 못한다.
def normalize_name(value):
    return clean_name(value).replace(' ', '').casefold()


# 한 추천 이벤트의 임시 메모리이며 파일로 저장하지 않는다.
# active: 진행 여부 / ingredients: 관측 재료 / shown: 안내한 음식 이름 전체(set)
# last_menus: 가장 최근 안내한 1~2개 메뉴. “둘 다 먹자”를 해석할 때 사용한다.
def new_state():
    return {'active': False, 'ingredients': [], 'shown': set(), 'last_menus': []}


# 같은 딕셔너리 안을 비우고 채워 이 객체를 전달받은 쪽에도 초기화가 반영되게 한다.
def clear_state(state):
    state.clear()
    state.update(new_state())


# 시스템 시간대와 관계없이 한국 날짜를 사용한다.
def korean_today():
    return datetime.now(ZoneInfo('Asia/Seoul')).date()


# 임시 파일을 완성한 뒤 기존 파일과 한 번에 교체한다. 쓰기 실패로 기존 기록이 깨지는 것을 줄인다.
# 두 메뉴를 선택했을 때도 함께 저장하거나 함께 실패한다.
def write_meals(path, meals):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump({'meals': meals}, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            # Python 버퍼를 비우고 fsync로 저장 장치에 반영을 요청한 뒤 파일을 교체한다.
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


# 형식을 검사하고 오늘·어제·그저께 기록만 반환한다. 개수 제한은 없다.
# 파일이 없으면 최초 생성하지만 손상된 기존 파일은 예외를 내고 그대로 둔다.
def load_recent(path, today):
    path = Path(path)
    if not path.exists():
        write_meals(path, [])
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or set(payload) != {'meals'} or not isinstance(payload['meals'], list):
        raise ValueError('식사 기록 형식 오류')
    rows = []
    for row in payload['meals']:
        if not isinstance(row, dict) or set(row) != {'dish_name', 'selected_on'}:
            raise ValueError('식사 항목 형식 오류')
        name = clean_name(row['dish_name'])
        selected = datetime.strptime(row['selected_on'], '%Y-%m-%d').date()
        if selected.isoformat() != row['selected_on']:
            raise ValueError('날짜 형식 오류')
        # 예: 오늘이 11월 7일이면 5·6·7일. 과거 72시간을 계산하는 방식은 아니다.
        if today - timedelta(days=2) <= selected <= today:
            rows.append({'dish_name': name, 'selected_on': selected.isoformat()})
    return rows


# Gemma 응답의 형식·보유 재료 ID·제외 메뉴를 검사한다.
# available은 보유 재료 ID 목록, excluded는 제외할 음식 이름 집합이다.
# 전체 구조가 잘못되면 예외, 개별 항목이 잘못되면 해당 항목만 제외한다.
def validate_menus(payload, available, excluded):
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict) or set(payload) != {'menus'}:
        raise ValueError('menus 키가 필요합니다.')
    candidates = payload['menus']
    if not isinstance(candidates, list) or len(candidates) > 2:
        raise ValueError('메뉴는 최대 2개입니다.')
    # set은 포함 여부 검사와 중복 제거에 쓴다. 통과한 메뉴도 seen에 추가해 응답 내 중복을 막는다.
    result, seen = [], {normalize_name(n) for n in excluded}
    for item in candidates:
        try:
            if not isinstance(item, dict) or set(item) != {'dish_name', 'available_ingredients', 'additional_ingredients'}:
                continue
            name = clean_name(item['dish_name'])
            key = normalize_name(name)
            # owned: 실제 보유한 영어 재료 ID / extra: 추가로 준비할 재료의 한국어 이름.
            owned, extra = item['available_ingredients'], item['additional_ingredients']
            if not isinstance(owned, list) or not owned or not all(isinstance(v, str) and v in available for v in owned):
                continue
            if not isinstance(extra, list) or key in seen:
                continue
            # 이미 보유한 재료가 구매 목록에도 들어 있다면 알려진 재료 별칭으로 찾아 제거한다.
            purchases = []
            for value in extra:
                value = clean_name(value)
                if INGREDIENT_ALIASES.get(value.casefold()) not in available and value not in purchases:
                    purchases.append(value)
            result.append({'dish_name': name, 'available_ingredients': list(dict.fromkeys(owned)),
                           'additional_ingredients': purchases})
            seen.add(key)
        except (ValueError, TypeError):
            continue
    return result


# 구매 재료 질문에서 메뉴를 추출한다. 실제 식사 선택과 구분하므로 기록 함수는 부르지 않는다.
def shopping_dish(text):
    if re.search(r'안\s*(?:먹|만들)|않|싫', text):
        return None
    patterns = [
        # 끝의 ‘이’는 떡볶이·달걀말이의 일부일 수 있어 임의로 제거하지 않는다.
        r'(?:^|[.!?])\s*([^.!?]+?)(?:가|을|를)?\s*(?:먹고|만들고)\s*싶',
        r'(?:^|[.!?])\s*([^.!?]+?)(?:을|를)?\s*(?:만들려면|만들려고|만들건데|만들거야|요리하려면)',
        r'(?:^|[.!?])\s*([^.!?]+?)(?:에|의)?\s*(?:필요한|부족한|추가로\s*필요한)\s*재료',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        name = re.sub(r'^(?:(?:나는|나|저는|저|오늘은|오늘|지금|그럼|그래)(?:[,!]\s*|\s+))+', '', match[1]).strip()
        if re.search(r'(?:^|\s)(?:아니면|또는|대신에?|말고)(?:\s|$)', name):
            return None
        if name.replace(' ', '') in {'어떤메뉴', '무슨메뉴', '아무메뉴', '어떤요리', '아무거나', '그거', '이거', '저거'}:
            return None
        try:
            return clean_name(name)
        except ValueError:
            return None
    return None


# 이름을 재료 비교용 키로 바꾼다. 등록된 한영 이름·별칭만 같은 ID로 연결한다.
def ingredient_key(value):
    key = clean_name(value).replace(' ', '').casefold()
    for alias, ident in INGREDIENT_ALIASES.items():
        if alias.replace(' ', '').casefold() == key:
            return ident
    return key


# Gemma는 전체 필요 재료를 제안하고, 보유 재료를 빼는 계산은 코드가 담당한다.
def missing_ingredients(payload, dish, available):
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict) or set(payload) != {'dish_name', 'ingredients'}:
        raise ValueError('필요 재료 JSON 형식 오류')
    if normalize_name(payload['dish_name']) != normalize_name(dish):
        raise ValueError('질문한 메뉴와 다른 메뉴')
    ingredients = payload['ingredients']
    if not isinstance(ingredients, list) or not ingredients:
        raise ValueError('전체 필요 재료 목록이 필요합니다.')
    owned = {ingredient_key(value) for value in available}
    missing, seen = [], set()
    for value in ingredients:
        name = clean_name(value)
        key = ingredient_key(name)
        if key not in owned and key not in seen:
            missing.append(INGREDIENT_NAMES.get(key, name))
            seen.add(key)
    return missing


def selection(text, state):
    """긍정 선택 패턴과 등록된 모호·부정 표현을 검사한다. 모든 자연어 모호성을 판별하지는 못한다."""
    if re.search(r'안\s*먹|않|말자|먹지|먹을까|먹자마자', text) or '?' in text or '？' in text:
        return []
    if not re.search(SELECTION_END, text):
        return []
    # 접두어 뒤에 공백·문장부호가 있어야 제거한다. “그래놀라”의 “그래”는 보존한다.
    text = re.sub(r'^(?:(?:그래서|그래|그럼|오늘은|오늘|나는|추천한|추천해\s*준)(?:[,.!]\s*|\s+))+', '', text).strip()
    name = re.sub(SELECTION_END, '', text).strip()
    if not name or len(name) > 100:
        return []
    # 복합 문장은 먼저 거른다. “주먹밥”처럼 이름에 있는 글자 “먹”만으로 거절하지 않는다.
    if re.search(r'말고(?:\s|$)|(?:^|\s)(?:대신에?|아니면|또는|혹은|안|아니|싫어)(?:\s|$)|먹(?:는|고|을|자고|기로)(?:\s|$)', name):
        return []
    # 이름 부분 전체가 “둘 다”여야 한다. “둘 다 먹는 대신 …”를 이전 메뉴로 연결하지 않는다.
    if re.fullmatch(r'둘\s*다|모두|다', name):
        return [m['dish_name'] for m in state['last_menus']]

    # “그걸로”처럼 지시어에 조사가 붙어도 메뉴 이름으로 기록하지 않는다.
    compact_name = name.replace(' ', '')
    if re.fullmatch(r'(?:그거|이거|저거|그것|이것|저것|그걸|이걸|저걸|뭐|뭔가|무언가|아무거나|둘다|다|모두)(?:으로|로|을|를|은|는)?', compact_name):
        return []
    if re.fullmatch(r'(아무|어떤)(음식|요리|메뉴)(?:이나|나|든지|으로|로|을|를|은|는)?', compact_name):
        return []

    # 이미 아는 메뉴는 원래 이름과 대조해 조사를 떼어낸다. 선택을 이 목록으로 제한하지는 않는다.
    known = [m['dish_name'] for m in state['last_menus']] + list(ALIASES)
    key = normalize_name(name)
    for dish in known:
        if key == normalize_name(dish):
            return [clean_name(dish)]
    for dish in known:
        if any(key == normalize_name(dish + particle) for particle in ['으로', '로', '을', '를', '은', '는']):
            return [clean_name(dish)]

    # 띄어 쓴 조사는 제거한다. 모르는 이름의 붙어 있는 “로”는 “마시멜로”일 수 있어 보존한다.
    name = re.sub(r'\s+(으로|로|을|를|은|는)$', '', name).strip()
    match = re.fullmatch(r'(.+)(을|를|은|는)', name)
    if match:
        base, particle = match.groups()
        last = ord(base[-1])
        if 0xAC00 <= last <= 0xD7A3:
            has_final = (last - 0xAC00) % 28 != 0  # 한글 음절에 받침이 있는지 확인한다.
            if has_final == (particle in {'을', '은'}):
                name = base.strip()
    return [clean_name(name)]


# 한 발화를 처리하고 화면·TTS용 한국어 문장을 반환한다.
# observe와 recommend는 전달받은 함수다. 실제 모델 또는 테스트용 가상 응답을 연결할 수 있다.
def handle_text(text, state, observe, recommend, history_path, today=None, required_ingredients=None):
    text = ' '.join(text.split()).strip()
    if not text:
        return ''
    today = today or korean_today()
    if text.rstrip('.!') in {'그만', '취소', '그만할게', '추천 종료'}:
        clear_state(state)
        return '추천을 마쳤어요.'
    # 1. 의도 구분. 부정·불명확한 선택을 먼저 처리해 “추천”이라는 단어만으로 실행하지 않는다.
    compact = text.replace(' ', '')
    # 특정 메뉴의 구매 재료 조회는 메뉴 추천·선택보다 먼저 분기한다. 현재 사진을 새로 사용한다.
    shopping_query = bool(re.search(r'사와야|사와애|사야|사올|사오|사와|구매|살재료|필요한재료|추가재료|부족한재료', compact)) and ('재료' in text or '뭐사' in compact or '뭘사' in compact)
    dish = shopping_dish(text) if shopping_query else None
    ordinary_recommendation = re.search(r'추천(?:해|좀|부탁|줘)|추천[.!?]*$', compact)
    if shopping_query and (dish or not ordinary_recommendation):
        if re.search(r'알려주지마|알려주지말|안알려', compact):
            return '필요한 재료 안내를 취소했어요.'
        if dish is None:
            return '어떤 메뉴의 재료를 살지 메뉴 이름을 말해 주세요.'
        if required_ingredients is None:
            return '필요한 재료를 확인하지 못했어요. 다시 말씀해 주세요.'
        try:
            available = list(dict.fromkeys(observe()))
            if not available:
                return '식재료를 확인하지 못했어요. 카메라 앞에 재료를 보여 주세요.'
        except Exception:
            logging.exception('구매 재료 조회의 현재 재료 인식 실패')
            return '식재료를 확인하지 못했어요. 카메라와 재료를 확인해 주세요.'
        feedback = ''
        for attempt in range(2):
            try:
                payload = required_ingredients(dish, available, feedback)
                missing = missing_ingredients(payload, dish, available)
                return '지금 사와야 하는 재료는 ' + ', '.join(missing) + '입니다.' if missing else '지금 사와야 하는 재료는 없어요.'
            except (ValueError, TypeError):
                feedback = '질문한 메뉴의 비어 있지 않은 전체 재료 목록을 정확한 JSON 형식으로 반환하세요.'
            except Exception:
                logging.exception('필요 재료 생성 실패')
                return '필요한 재료를 확인하지 못했어요. 다시 말씀해 주세요.'
        return '필요한 재료를 확인하지 못했어요. 다시 말씀해 주세요.'
    if re.search(r'추천(?:은|는)?(?:하지마|하지말|해주지마|해주지말|안해|말자)|추천그만|그만추천', compact):
        clear_state(state)
        return '추천을 마쳤어요.'
    names = selection(text, state)
    choice_phrase = re.search(SELECTION_END, text) or re.search(r'먹지\s*(?:말자|마(?:세요)?)[.!\s]*$', text)
    if not names and choice_phrase:
        return CLARIFY
    alternative = any(w in compact for w in ['딴메뉴', '다른메뉴', '다른거'])
    request = alternative or bool(re.search(r'추천(?:해|좀|부탁|줘)|추천[.!?]*$', compact)) or any(w in compact for w in ['뭐먹', '뭘먹', '무슨요리', '어떤요리', '뭐할까'])
    # “재료로 뭐 먹을까?”는 재료 조회 조건에도 맞을 수 있으므로 추천 의도를 우선한다.
    # 현장 Whisper에서 '식재료'를 '식재로'로 받아 적는 경우도 조회로 처리한다.
    inventory = not request and ('냉장고' in text or '재료' in text or '식재로' in text) and any(w in text for w in ['뭐', '무엇', '무슨', '알려', '있어', '있니'])
    # “추천한 카레 먹자”도 명확한 선택이면 촬영·추천을 건너뛴다.
    if names:
        inventory = request = False
    # 2. 재료 조회: 새 사진을 분석하되 식사 기록과 기존 추천 이벤트는 건드리지 않는다.
    if inventory:
        try:
            # dict.fromkeys는 처음 나온 순서를 유지하면서 중복을 없앤다. 개수는 세지 않는다.
            kinds = list(dict.fromkeys(observe()))
            if not kinds:
                return '식재료를 확인하지 못했어요. 카메라 앞에 재료를 보여 주세요.'
            return '현재 보이는 식재료는 ' + ', '.join(INGREDIENT_NAMES[k] for k in kinds) + '입니다.'
        except Exception:
            logging.exception('식재료 조회 실패')
            return '식재료를 확인하지 못했어요. 카메라와 재료를 확인해 주세요.'
    # 3. 추천: 새 일반 질문이면 새 사진부터 시작한다. 진행 중인 이벤트의 대안 요청만 재료를 재사용한다.
    if request:
        if not alternative or not state['active']:
            clear_state(state)
            try:
                ingredients = list(dict.fromkeys(observe()))
                if not ingredients:
                    return '식재료를 확인하지 못했어요. 카메라 앞에 재료를 보여 주세요.'
                state.update(active=True, ingredients=ingredients)
            except Exception:
                logging.exception('식재료 인식 실패')
                return '식재료를 확인하지 못했어요. 카메라와 재료를 확인해 주세요.'
        try:
            recent = load_recent(history_path, today)
        except Exception:
            logging.exception('식사 기록 읽기 실패')
            return '최근 식사 기록을 읽지 못했어요. 기록 파일을 확인해 주세요.'
        # |는 집합의 합집합이다. 최근 선택 메뉴와 이번 이벤트에서 안내한 이름 전체를 합친다.
        excluded = state['shown'] | {normalize_name(row['dish_name']) for row in recent}
        menus, feedback, format_failed = [], '', False
        # 최초 생성 + 필요할 때 보완 1회. 유효 메뉴가 하나라도 있으면 바로 안내한다.
        for attempt in range(2):
            try:
                payload = recommend(state['ingredients'], excluded, feedback)
                menus = validate_menus(payload, state['ingredients'], excluded)
                parsed = json.loads(payload) if isinstance(payload, str) else payload
                format_failed = False
                if menus or parsed == {'menus': []}:
                    break
                # 제외 조건을 빼도 유효 항목이 없다면 형식·재료 오류로 구분한다.
                format_failed = not bool(validate_menus(payload, state['ingredients'], set()))
                feedback = '금지 메뉴 또는 잘못된 항목뿐입니다. 조건을 지키거나 menus를 빈 목록으로 반환하세요.'
            except (ValueError, TypeError):
                format_failed = True
                feedback = 'JSON 형식이 잘못됐습니다. 정확한 키와 최대 2개의 유효 항목만 반환하세요.'
            except Exception:
                logging.exception('Gemma 메뉴 추천 실패')
                return '메뉴 추천을 처리하지 못했어요. 다시 말씀해 주세요.'
        if not menus:
            clear_state(state)
            return '추천 결과 형식을 확인하지 못했어요. 다시 말씀해 주세요.' if format_failed else NO_MENUS
        # 검증을 통과한 결과만 임시 추천 문맥에 넣는다. 추천 자체로 식사 파일에 저장하지는 않는다.
        state['last_menus'] = menus
        state['shown'].update(normalize_name(m['dish_name']) for m in menus)
        # Gemma 원문 대신 정해진 템플릿으로 답변을 만든다. 레시피나 이유는 읽지 않는다.
        response = '추천 메뉴는 ' + ', '.join(m['dish_name'] for m in menus) + '입니다.'
        for item in menus:
            if item['additional_ingredients']:
                response += ' ' + item['dish_name'] + '의 추가 재료는 ' + ', '.join(item['additional_ingredients']) + '입니다.'
        return response
    if names:
        try:
            rows = load_recent(history_path, today)
            # 4. 명확한 선택은 추천 밖 메뉴라도 저장한다. 촬영·모델 호출은 다시 하지 않는다.
            rows.extend({'dish_name': name, 'selected_on': today.isoformat()} for name in names)
            write_meals(history_path, rows)
        except Exception:
            logging.exception('식사 기록 저장 실패')
            return '메뉴를 저장하지 못했어요. 기록 파일을 확인한 뒤 다시 말씀해 주세요.'
        clear_state(state)
        return '두 메뉴를 기록했어요.' if len(names) == 2 else names[0] + '로 기록했어요.'
    if any(w in text for w in ['먹', '좋아', '둘 다']):
        return CLARIFY
    return '메뉴 추천이나 식재료를 물어보거나, 먹기로 한 메뉴를 말씀해 주세요.'


# 실행 옵션 → 자원 준비 → 듣기/STT → 발화 처리 → TTS를 반복하는 진입 함수.
def run():
    # ArgumentParser가 터미널의 --mic-device 같은 실행 인수를 args에 담는다.
    # default는 인수를 생략할 때 쓸 시작값이다. 실제 장치에서 조정할 수 있다.
    parser = argparse.ArgumentParser(description='식재료를 보고 음성으로 메뉴를 추천합니다.')
    parser.add_argument('--mic-device', default='plughw:CARD=Microphone,DEV=0')
    parser.add_argument('--detect-conf', type=float, default=0.15)
    parser.add_argument('--accept-conf', type=float, default=0.65)
    parser.add_argument('--rms-threshold', type=int, default=500)
    args = parser.parse_args()
    # 실행할 때만 관련 모듈을 불러와 --help와 순수 규칙 테스트에 장치가 필요 없게 한다.
    from gemma import Gemma
    from speech import speech_to_text, text_to_speech, check_resources
    from vision import Vision
    # [Project02]를 강의 폴더 안에 두면 상위 폴더의 모델·실행 파일을 그대로 사용한다.
    resource_root = PROJECT_ROOT.parent
    check_resources(resource_root)
    runtime = PROJECT_ROOT / 'runtime'
    runtime.mkdir(exist_ok=True)
    state = new_state()
    # 종료하거나 오류가 나도 finally에서 직접 시작한 모델 프로세스를 정리한다.
    gemma = Gemma(resource_root)
    try:
        vision = Vision(PROJECT_ROOT / 'ingredients_fp32.engine', runtime,
                        gemma.check_candidates, args.detect_conf, args.accept_conf)
        while True:
            print('말씀을 시작해 주세요. (종료: Ctrl+C)', flush=True)
            try:
                # 한 발화 녹음을 끝내고 녹음 프로세스를 닫은 뒤 Whisper를 실행한다.
                text = speech_to_text(resource_root, runtime / 'input.wav', args.mic_device, args.rms_threshold)
                print('STT 결과:', text, flush=True)
                response = handle_text(text, state, vision.observe, gemma.recommend, PROJECT_ROOT / 'recent_meals.json',
                                       required_ingredients=gemma.required_ingredients)
                if response:
                    print(response, flush=True)
                    # 재생이 끝나야 다음 반복에서 다시 녹음한다. 처리·재생 중 새 음성을 모으지 않는다.
                    text_to_speech(response, resource_root, runtime / 'response.wav')
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                print('장치 처리 실패:', error, flush=True)
                break
    finally:
        gemma.close()
        clear_state(state)


# import main으로 불러올 때는 실행하지 않고 python main.py로 실행할 때만 시작한다.
if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        print('\n프로그램을 종료합니다.')
