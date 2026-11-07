"""06 노트북의 llama_cpp/Gemma4ChatHandler 호출. 지정한 Python에서 모델 재사용."""
import base64
from contextlib import redirect_stdout
import json
from pathlib import Path
import selectors
import subprocess
import sys
import time

from vision import INGREDIENT_NAMES


# JSON이 Markdown 코드 블록에 들어 있으면 포장만 벗겨 해석한다.
# 설명문까지 임의로 잘라 맞추지는 않는다. 잘못된 JSON은 예외로 반환한다.
def parse_json(content):
    content = content.strip()
    if content.startswith('```'):
        lines = content.splitlines()
        if lines[-1].strip() != '```':
            raise ValueError('닫히지 않은 JSON 코드 블록')
        content = '\n'.join(lines[1:-1])
    return json.loads(content)


# 메인 프로그램 쪽의 연결 객체다. 실제 모델은 아래 worker 프로세스에서 실행한다.
# 다른 가상환경을 쓸 수 있고, 같은 모델을 여러 질문에 재사용할 수 있다.
class Gemma:
    def __init__(self, resource_root, python=None, timeout=180):
        self.resource_root = Path(resource_root).expanduser().resolve()
        # venv/bin/python 링크를 풀면 가상환경을 잃을 수 있어 resolve() 대신 absolute()를 쓴다.
        self.python = str(Path(python).expanduser().absolute()) if python else sys.executable
        self.timeout = timeout
        self.process = None
        # 프로세스에서 읽은 바이트가 정확히 JSON 한 줄로 나뉘지 않을 수 있어 버퍼가 필요하다.
        self.pending = bytearray()

    def __enter__(self):
        # 첫 이미지 확인/메뉴 요청 때 시작한다. 확실한 재료 조회만 하면 로딩하지 않는다.
        return self

    # with 블록이 끝나거나 예외가 생겼을 때 자동으로 호출되는 정리 함수다.
    def __exit__(self, *unused):
        self.close()

    # 연결과 자신이 만든 프로세스만 정리한다. 다른 학습·모델 프로세스는 건드리지 않는다.
    def close(self):
        if self.process:
            from speech import stop_process
            stop_process(self.process)
            if self.process.stdin:
                self.process.stdin.close()
            self.process = None
        self.pending.clear()

    # 부모 → 자식 stdin으로 JSON 한 줄 전송, 자식 stdout에서 JSON 한 줄 수신.
    # stdin/stdout을 키보드·화면 대신 두 프로그램을 잇는 통로(PIPE)로 사용한다.
    def request(self, payload):
        import os
        if self.process is None:
            # 같은 gemma.py를 --worker로 실행하면 아래 worker()가 동작한다.
            # -u는 Python 출력 버퍼링을 꺼 응답이 즉시 전달되게 한다.
            self.process = subprocess.Popen(
                [self.python, '-u', str(Path(__file__).resolve()), '--worker', str(self.resource_root)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0,
            )
        try:
            # JSON을 UTF-8 바이트로 바꿔 보낸다. 끝의 줄바꿈은 한 요청의 경계다.
            self.process.stdin.write((json.dumps(payload, ensure_ascii=False) + '\n').encode('utf-8'))
            self.process.stdin.flush()
            # 단조 시계는 시스템 날짜가 바뀌어도 경과 시간을 안정적으로 잰다.
            # 시간을 기록하려는 것이 아니라 응답 제한 시간을 계산하는 용도다.
            deadline = time.monotonic() + self.timeout
            with selectors.DefaultSelector() as selector:
                selector.register(self.process.stdout, selectors.EVENT_READ)
                # 줄바꿈까지 모이면 JSON 한 줄이 완성된 것이다. 그때까지 필요한 만큼 읽는다.
                while b'\n' not in self.pending:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(timeout=remaining):
                        raise TimeoutError('Gemma 응답 제한 시간 초과')
                    chunk = os.read(self.process.stdout.fileno(), 65536)
                    if not chunk:
                        raise RuntimeError('Gemma 프로세스가 종료됐습니다. 환경·모델 경로를 확인하세요.')
                    self.pending.extend(chunk)
                    if len(self.pending) > 1024 * 1024:
                        raise ValueError('Gemma 응답 크기 초과')
            # 완성된 첫 줄만 해석하고 뒤에 남은 바이트는 다음 읽기를 위해 보관한다.
            line, _, remainder = self.pending.partition(b'\n')
            self.pending = bytearray(remainder)
            response = json.loads(line)
            if 'error' in response:
                raise RuntimeError(response['error'])
            # JSON 자체가 잘못되면 호출자는 한 번 수정 요청할 수 있다.
            return parse_json(response['content'])
        except ValueError:
            raise
        # Ctrl+C도 포함해 통신을 중단하면 모델 프로세스를 정리하고 예외를 다시 전달한다.
        except BaseException:
            self.close()
            raise

    # 텍스트 메뉴 생성 요청. 재료·제외 메뉴·보완 지시를 보내며 사진은 보내지 않는다.
    # feedback은 첫 요청에서 비어 있고 검증 실패 후 보완할 때만 채운다.
    def recommend(self, available, excluded, feedback):
        prompt = (
            '한국어 음식 메뉴를 자유롭게 최대 2개 추천하세요. 요리 방법과 이유는 쓰지 마세요. '
            '같은 음식은 하나만, 제외 메뉴는 공백·계란/달걀 별칭이 달라도 추천하지 마세요. '
            '보유 재료를 한 종류 이상 활용하세요. 여러 종류를 조합해도 됩니다. '
            '상시 보유 양념은 가정하지 마세요. 필요한 다른 재료는 추가 재료로 명시하세요. '
            '추가 재료는 쉽게 준비할 법한 재료를 적게 제안하세요. 매장 재고·가격은 주장하지 마세요. '
            '보유 재료와 추가 재료를 혼동하지 마세요. 가능한 메뉴가 하나면 하나, 없으면 빈 목록을 반환하세요. '
            '설명 없이 JSON만 반환하세요. 정확한 형식: '
            '{"menus":[{"dish_name":"메뉴명","available_ingredients":["영문 보유 ID"],'
            '"additional_ingredients":["추가로 준비할 재료의 한국어 이름"]}]}.\n'
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
        return self.request({'prompt': prompt, 'image_path': str(image_path.resolve())})


# 자식 프로세스의 진입점. 모델을 한 번 로딩한 뒤 요청을 차례로 처리한다.
def worker(resource_root):
    # 모델의 출력 로그가 JSON 통신용 stdout에 섞이지 않게 한다.
    with redirect_stdout(sys.stderr):
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Gemma4ChatHandler
        model_path = resource_root / 'src/models/Gemma4/google_gemma-4-E2B-it-Q4_K_M.gguf'
        mmproj_path = resource_root / 'src/models/Gemma4/mmproj-google_gemma-4-E2B-it-f16.gguf'
        for path in [model_path, mmproj_path]:
            if not path.is_file():
                raise FileNotFoundError(str(path))
        # mmproj로 이미지 정보를 언어 모델에 연결한다. 06 노트북과 같은 호출 방식이다.
        chat_handler = Gemma4ChatHandler(clip_model_path=str(mmproj_path))
        # 노트북의 GPU·컨텍스트·배치 설정을 유지한다. 실제 Jetson 메모리 검증은 별도다.
        llm = Llama(model_path=str(model_path), chat_handler=chat_handler,
                    n_gpu_layers=-1, n_ctx=2048, n_batch=32, n_ubatch=32, verbose=False)
    # 부모가 보낸 한 줄이 한 요청이다. 같은 llm 객체로 반복 처리한다.
    for line in sys.stdin:
        try:
            request = json.loads(line)
            content = [{'type': 'text', 'text': request['prompt']}]
            if request.get('image_path'):
                # JPEG 바이트를 base64 문자열로 바꿔 노트북의 image_url 입력 형식으로 넣는다.
                image_data = 'data:image/jpeg;base64,' + base64.b64encode(Path(request['image_path']).read_bytes()).decode('utf-8')
                content.append({'type': 'image_url', 'image_url': {'url': image_data}})
            with redirect_stdout(sys.stderr):
                result = llm.create_chat_completion(
                    messages=[{'role': 'system', 'content': '요청한 JSON 형식을 정확히 지키세요.'},
                              {'role': 'user', 'content': content}],
                    # JSON 메뉴를 담도록 출력 토큰 한도를 늘리고 무작위성을 낮춘 시작값이다.
                    max_tokens=600, temperature=0.3,
                )
            response = {'content': result['choices'][0]['message']['content']}
        except Exception as error:
            response = {'error': str(error)}
        # stdout에는 통신용 JSON만 보낸다. flush=True로 부모가 바로 읽게 한다.
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]))
    else:
        raise SystemExit('main.py를 실행하세요.')
