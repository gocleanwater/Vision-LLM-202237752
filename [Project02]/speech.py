"""06-Vision_LLM_Multimodal_Systems.ipynb의 STT/TTS 명령을 재사용한다."""
from array import array
from collections import deque
import math
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import time
import wave

# 1초에 16,000개 샘플, 샘플당 16비트(2바이트), 모노. 노트북과 같은 녹음 형식이다.
RATE = 16000
# 여기서 frame은 사진이 아니라 20ms 길이의 짧은 음성 조각이다.
FRAME_SECONDS = 0.02
# 16,000 × 0.02 × 2 = 한 프레임에 640바이트.
FRAME_BYTES = int(RATE * FRAME_SECONDS) * 2


# 실제 녹음 전에 오디오 명령과 노트북 모델 경로가 있는지 검사한다.
def check_resources(resource_root):
    for command in ['pasuspender', 'arecord', 'aplay', 'pactl']:
        if shutil.which(command) is None:
            raise FileNotFoundError('Jetson 오디오 명령이 없습니다: ' + command)
    for relative in ['whisper.cpp/build-cpu/bin/whisper-cli', 'whisper.cpp/models/ggml-base.bin',
                     '.piper_venv/bin/python', 'src/models/Piper/ko_KR-kss-medium.onnx',
                     'src/models/Piper/ko_KR-kss-medium.onnx.json']:
        if not (resource_root / relative).is_file():
            raise FileNotFoundError(str(resource_root / relative))


# 우리가 시작한 외부 프로세스만 종료한다. 정상 종료를 기다린 뒤 필요하면 강제 종료한다.
def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
    if process.stdout:
        process.stdout.close()


# PCM 바이트를 16비트 정수로 읽고 RMS(진폭의 제곱 평균의 제곱근)로 음량을 계산한다.
# 큰 값은 큰 음량을 뜻할 뿐, 말소리와 생활 소음을 의미로 구별하는 것은 아니다.
def rms(frame):
    values = array('h', frame)
    if sys.byteorder != 'little':
        values.byteswap()
    return math.sqrt(sum(v * v for v in values) / len(values))


def utterance_frames(frames, threshold=500, silence_seconds=0.8, max_seconds=15):
    """20ms PCM 프레임에서 한 발화를 모은다. 대기 중에는 짧은 버퍼만 유지한다."""
    if threshold <= 0 or silence_seconds <= 0 or max_seconds <= 0:
        raise ValueError('음성 감지 설정은 양수여야 합니다.')
    # 20ms × 15개 = 최대 0.3초. 발화 시작 판정에 쓰는 큰 음량 3프레임도 포함한다.
    preroll = deque(maxlen=15)
    captured = []
    # voiced: 큰 음량 누적 / quiet: 연속 무음 / consecutive: 발화 시작 전 연속 큰 음량.
    voiced = quiet = consecutive = 0
    for frame in frames:
        loud = rms(frame) >= threshold
        # 발화 시작 전에는 짧은 이전 음성만 보관한다. 첫 음절이 잘리는 것을 줄이기 위한 버퍼다.
        if not captured:
            preroll.append(frame)
            consecutive = consecutive + 1 if loud else 0
            if consecutive >= 3:  # 짧은 충격음 하나로 시작하지 않는다.
                captured.extend(preroll)
                voiced = consecutive
                quiet = 0
        else:
            captured.append(frame)
            voiced += int(loud)
            quiet = 0 if loud else quiet + 1
            # 무음이 충분히 이어지거나 최대 길이에 도달하면 한 발화를 마친다.
            if quiet * FRAME_SECONDS >= silence_seconds or len(captured) * FRAME_SECONDS >= max_seconds:
                # 큰 음량 구간이 너무 짧으면 잡음 후보로 버리고 다시 기다린다.
                if voiced * FRAME_SECONDS >= 0.2:
                    return b''.join(captured)
                captured, voiced, quiet, consecutive = [], 0, 0, 0
                preroll.clear()
    raise RuntimeError('마이크 입력이 발화 완료 전에 끝났습니다.')


# arecord의 raw PCM 출력을 조금씩 읽어 한 발화만 WAV 파일에 저장한다.
def record_utterance(audio_file, mic_device='plughw:3,0', threshold=500):
    audio_file = Path(audio_file)
    audio_file.parent.mkdir(parents=True, exist_ok=True)
    audio_file.unlink(missing_ok=True)
    # 노트북의 arecord 포맷 유지. -d 5 대신 raw 스트림을 읽어 발화 끝을 감지한다.
    # pasuspender가 종료돼도 자식 arecord가 남지 않도록 이 녹음 전용 그룹을 정리한다.
    import os
    import signal
    process = subprocess.Popen(['pasuspender', '--', 'arecord', '-q', '-D', mic_device,
                                '-f', 'S16_LE', '-r', str(RATE), '-c', '1', '-t', 'raw'],
                               stdout=subprocess.PIPE, start_new_session=True, bufsize=0)
    try:
        # yield는 프레임을 하나씩 전달한다. 녹음 전체를 미리 메모리에 모으지 않는다.
        def frames():
            # 읽어 온 바이트 수가 프레임 크기와 다를 수 있어 남은 바이트를 모아 둔다.
            pending = bytearray()
            # 데이터 도착을 기다렸다가 읽는다. 녹음 데이터 수신이 멈추면 제한 시간 뒤 오류로 처리한다.
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    if not selector.select(timeout=5):
                        raise RuntimeError('마이크 음성 데이터를 받지 못했습니다.')
                    chunk = os.read(process.stdout.fileno(), FRAME_BYTES)
                    if not chunk:
                        raise RuntimeError('arecord가 멈췄습니다. 마이크를 확인하세요.')
                    pending.extend(chunk)
                    while len(pending) >= FRAME_BYTES:
                        yield bytes(pending[:FRAME_BYTES])
                        del pending[:FRAME_BYTES]
        pcm = utterance_frames(frames(), threshold)
    finally:
        try:
            # 이 녹음 전용 프로세스 그룹만 정리해 자식 arecord가 남지 않게 한다.
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        process.stdout.close()
        # 녹음 그룹을 종료하면 pasuspender의 일시 중지가 남을 수 있어 재생 장치를 복구한다.
        subprocess.run(['pactl', 'suspend-sink', '@DEFAULT_SINK@', '0'],
                       check=True, timeout=5)
    # raw에는 헤더가 없으므로 Whisper가 읽을 수 있는 WAV 헤더를 붙여 저장한다.
    with wave.open(str(audio_file), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(pcm)


# 노트북 방식: 발화 녹음 → whisper-cli 실행 → 인식 문장(stdout) 반환.
def speech_to_text(resource_root, audio_file, mic_device='plughw:3,0', threshold=500):
    record_utterance(audio_file, mic_device, threshold)
    whisper_path = resource_root / 'whisper.cpp/build-cpu/bin/whisper-cli'
    whisper_model = resource_root / 'whisper.cpp/models/ggml-base.bin'
    # 인수 목록으로 실행해 경로·문장을 셸 명령으로 해석하지 않는다.
    # check=True: 실패 시 예외 / capture_output=True: 출력 수집 / text=True: 문자열로 받기.
    result = subprocess.run(
        [str(whisper_path), '-m', str(whisper_model), '-f', str(audio_file),
         '-l', 'ko', '--no-timestamps'],
        text=True, capture_output=True, check=True, timeout=120,
    )
    return result.stdout.strip()


# 노트북 방식: Piper 가상환경의 Python으로 WAV 생성 → aplay 재생.
def text_to_speech(text, resource_root, output_file):
    output_file = Path(output_file)
    # 합성에 실패해도 이전 답변이 재생되지 않도록 예전 음성 파일을 먼저 지운다.
    output_file.unlink(missing_ok=True)
    piper_python = resource_root / '.piper_venv/bin/python'
    piper_model = resource_root / 'src/models/Piper/ko_KR-kss-medium.onnx'
    subprocess.run(
        [str(piper_python), '-m', 'piper', '-m', str(piper_model),
         '-f', str(output_file), '--', text],
        check=True, timeout=120,
    )
    if not output_file.is_file() or output_file.stat().st_size <= 44:
        raise RuntimeError('Piper가 음성 파일을 생성하지 못했습니다.')
    # 재생 완료까지 기다린다. 그 뒤에야 메인 루프가 다시 듣기 시작한다.
    subprocess.run(['aplay', str(output_file)], check=True, timeout=120)
    time.sleep(0.3)  # 짧은 재생 잔향 후 새 arecord를 연다. 실물 조정 필요.
