"""流式ASR可行性测试"""
import numpy as np
import time
from mlx_audio.stt.models.funasr import Model

MODEL_PATH = "models/Fun-ASR-MLT-Nano-2512-4bit"


def test_streaming_basic():
    """测试基本流式转录"""
    model = Model.from_pretrained(MODEL_PATH)

    # 3秒静音测试
    audio = np.zeros(16000 * 3, dtype=np.float32)

    chunks = []
    for chunk in model.generate(audio, stream=True, language="zh"):
        chunks.append(chunk)
        print(f"Chunk: {chunk}")

    print(f"Total chunks: {len(chunks)}")


def test_streaming_realtime():
    """录音后流式转录"""
    import sounddevice as sd

    model = Model.from_pretrained(MODEL_PATH)

    print("Recording 3 seconds...")
    audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype=np.float32)
    sd.wait()
    audio = audio.flatten()

    print("Streaming transcription:")
    start = time.time()
    first_chunk = None

    for chunk in model.generate(audio, stream=True, language="zh"):
        if first_chunk is None:
            first_chunk = time.time() - start
            print(f"First chunk latency: {first_chunk:.3f}s")
        print(f"  -> {chunk}")

    print(f"Total time: {time.time() - start:.3f}s")


if __name__ == "__main__":
    test_streaming_basic()
    print()
    test_streaming_realtime()
