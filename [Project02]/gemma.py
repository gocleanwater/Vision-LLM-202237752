import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from vision import INGREDIENT_NAMES


# 코드 블록으로 감싼 JSON이면 앞뒤 표시만 제거한다.
def parse_json(content):
    content = content.strip()
    if content.startswith('```'):
        lines = content.splitlines()
        if lines[-1].strip() != '```':
            raise ValueError('닫히지 않은 JSON 코드 블록')
        content = '\n'.join(lines[1:-1])
    return json.loads(content)


# 다른 가상환경에서 Gemma를 실행하고, 한 번 올린 모델을 계속 재사용한다.
class Gemma:
    def __init__(self, resource_root, python=None, timeout=180):
        self.resource_root = Path(resource_root)
        self.python = str(python) if python else sys.executable
        self.timeout = timeout
        self.process = None
        self.response_file = Path(__file__).parent / 'runtime/gemma_response.json'

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            self.process.stdin.close()
            self.process = None
        self.response_file.unlink(missing_ok=True)
        Path(str(self.response_file) + '.tmp').unlink(missing_ok=True)

    def request(self, payload):
        self.response_file.parent.mkdir(parents=True, exist_ok=True)
        # 새 요청이 실패했을 때 지난 답변 파일을 읽지 않도록 먼저 지운다.
        self.response_file.unlink(missing_ok=True)
        if self.process is None:
            self.process = subprocess.Popen(
                [self.python, '-u', str(Path(__file__)), '--worker',
                 str(self.resource_root), str(self.response_file)],
                stdin=subprocess.PIPE, text=True,
            )
        try:
            self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + '\n')
            self.process.stdin.flush()
            # 모델이 완성한 JSON 파일을 기다린다. 무한히 기다리지는 않는다.
            start = time.monotonic()
            while not self.response_file.exists():
                if self.process.poll() is not None:
                    raise RuntimeError('Gemma 프로세스가 종료됐습니다. 환경·모델 경로를 확인하세요.')
                if time.monotonic() - start >= self.timeout:
                    raise TimeoutError('Gemma 응답 제한 시간 초과')
                time.sleep(0.05)
            with self.response_file.open(encoding='utf-8') as stream:
                response = json.load(stream)
            if 'error' in response:
                raise RuntimeError(response['error'])
            return parse_json(response['content'])
        except ValueError:
            # 모델의 JSON 형식만 잘못되면 같은 모델에 보완 요청할 수 있다.
            raise
        except BaseException:
            self.close()
            raise
        finally:
            self.response_file.unlink(missing_ok=True)

    # 텍스트 메뉴 생성 요청. 재료·제외 메뉴·보완 지시를 보내며 사진은 보내지 않는다.
    # feedback은 첫 요청에서 비어 있고 검증 실패 후 보완할 때만 채운다.
    def recommend(self, available, excluded, feedback):
        # 한국어 재료명을 ID 자리에 쓰지 않도록 실제 보유 ID로 예시를 만든다.
        example = {'menus': [{'dish_name': '메뉴명',
                             'available_ingredients': available[:1],
                             'additional_ingredients': []}]}
        prompt = (
            '한국어 음식 메뉴를 자유롭게 최대 2개 추천하세요. 요리 방법과 이유는 쓰지 마세요. '
            '같은 음식은 하나만, 제외 메뉴는 공백·계란/달걀 별칭이 달라도 추천하지 마세요. '
            '보유 재료를 한 종류 이상 활용하세요. 여러 종류를 조합해도 됩니다. '
            '상시 보유 양념은 가정하지 마세요. 필요한 다른 재료는 추가 재료로 명시하세요. '
            '추가 재료는 쉽게 준비할 법한 재료를 적게 제안하세요. 매장 재고·가격은 주장하지 마세요. '
            '보유 재료와 추가 재료를 혼동하지 마세요. 가능한 메뉴가 하나면 하나, 없으면 빈 목록을 반환하세요. '
            'available_ingredients에는 아래 available의 영어 키만 넣으세요. 한국어 이름을 넣지 마세요. '
            'dish_name과 additional_ingredients는 한국어로 쓰세요. '
            '설명 없이 JSON만 반환하세요. 출력 예시: '
            + json.dumps(example, ensure_ascii=False) + '\n'
            + json.dumps({'available': {k: INGREDIENT_NAMES[k] for k in available},
                          'excluded_dishes': sorted(excluded), 'correction': feedback}, ensure_ascii=False)
        )
        return self.request({'prompt': prompt})

    # 특정 요리의 전체 필요 재료를 제안한다. 현재 보유 목록과의 차집합은 main.py에서 계산한다.
    def required_ingredients(self, dish, available, feedback):
        prompt = (
            '요청한 음식 한 가지를 만드는 데 필요한 전체 재료 이름을 한국어로 제안하세요. '
            'dish_name은 requested_dish의 표기를 그대로 복사하세요. '
            '보유 재료도 빼지 말고 전체 목록에 넣으세요. 기본 양념도 자동 보유로 가정하지 마세요. '
            '수량, 조리 순서, 이유, 다른 메뉴, 매장 재고와 가격은 쓰지 마세요. '
            '이름만 나열하고 같은 재료는 중복하지 마세요. 지원 클래스 밖 재료도 허용합니다. '
            '설명 없이 정확한 JSON만 반환하세요: '
            '{"dish_name":"요청한 메뉴명","ingredients":["전체 필요 재료명"]}.\n'
            + json.dumps({'requested_dish': dish,
                          'observed': {key: INGREDIENT_NAMES[key] for key in available},
                          'correction': feedback}, ensure_ascii=False)
        )
        return self.request({'prompt': prompt})

    # 이미지 확인 요청. 전체 장면 대신 후보 번호가 붙은 콜라주 한 장을 보낸다.
    def check_candidates(self, image_path, candidates):
        prompt = (
            '사진은 YOLO 후보 영역을 잘라 번호별로 모은 것입니다. 각 번호의 재료를 확인하세요. '
            '허용된 재료 중 하나로 정정하거나 불확실하면 null을 반환하세요. '
            '후보마다 한 번씩만 반환하고 없는 번호를 추가하지 마세요. 설명 없이 JSON만 반환하세요. '
            '형식: {"checks":[{"detection_id":"d1","ingredient_id":"egg"}]}.\n'
            + json.dumps({'allowed': INGREDIENT_NAMES,
                          'candidates': [{'detection_id': c['detection_id'], 'yolo_guess': c['ingredient_id']} for c in candidates]}, ensure_ascii=False)
        )
        return self.request({'prompt': prompt, 'image_path': str(image_path)})


# 06 노트북과 같은 Llama·Gemma4ChatHandler 설정으로 모델을 한 번 올린다.
def worker(resource_root, response_file):
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Gemma4ChatHandler

    model_path = resource_root / 'src/models/Gemma4/google_gemma-4-E2B-it-Q4_K_M.gguf'
    mmproj_path = resource_root / 'src/models/Gemma4/mmproj-google_gemma-4-E2B-it-f16.gguf'
    chat_handler = Gemma4ChatHandler(clip_model_path=str(mmproj_path))
    llm = Llama(model_path=str(model_path), chat_handler=chat_handler,
                n_gpu_layers=-1, n_ctx=2048, n_batch=32, n_ubatch=32, verbose=False)

    for line in sys.stdin:
        try:
            request = json.loads(line)
            content = [{'type': 'text', 'text': request['prompt']}]
            if request.get('image_path'):
                image_data = 'data:image/jpeg;base64,' + base64.b64encode(Path(request['image_path']).read_bytes()).decode('utf-8')
                content.append({'type': 'image_url', 'image_url': {'url': image_data}})
            result = llm.create_chat_completion(
                messages=[{'role': 'system', 'content': '요청한 JSON 형식을 정확히 지키세요.'},
                          {'role': 'user', 'content': content}],
                max_tokens=600, temperature=0.3,
            )
            response = {'content': result['choices'][0]['message']['content']}
        except Exception as error:
            response = {'error': str(error)}
        # 작성 중인 파일을 부모가 읽지 않도록, 다 쓴 다음 한 번에 교체한다.
        temporary = Path(str(response_file) + '.tmp')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(response, stream, ensure_ascii=False)
        os.replace(temporary, response_file)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit('main.py를 실행하세요.')
