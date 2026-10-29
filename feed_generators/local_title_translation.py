"""Small local OPUS-MT model: no API tokens, no remote text transmission."""

import hashlib
import zipfile
from pathlib import Path

import requests

MODEL_URL = "https://argos-net.com/v1/translate-en_zh-1_9.argosmodel"
MODEL_SHA256 = "433e7c4f034d87fbe2353161e05f18646d7999452f801a4e1f0378522b9850ab"


class LocalTitleTranslator:
    def __init__(self):
        import ctranslate2
        import sentencepiece

        cache = Path(__file__).resolve().parents[1] / ".cache/translation"
        cache.mkdir(parents=True, exist_ok=True)
        archive_path = cache / "en-zh.argosmodel"
        model_root = cache / "translate-en_zh-1_9"
        if not (model_root / "model/model.bin").exists():
            if not archive_path.exists():
                response = requests.get(MODEL_URL, timeout=(10, 60))
                response.raise_for_status()
                temporary = cache / "download.tmp"
                temporary.write_bytes(response.content)
                if hashlib.sha256(temporary.read_bytes()).hexdigest() != MODEL_SHA256:
                    temporary.unlink()
                    raise ValueError("Translation model checksum mismatch")
                temporary.replace(archive_path)
            if hashlib.sha256(archive_path.read_bytes()).hexdigest() != MODEL_SHA256:
                raise ValueError("Translation model checksum mismatch")
            with zipfile.ZipFile(archive_path) as archive:
                for name in archive.namelist():
                    if not (cache / name).resolve().is_relative_to(cache.resolve()):
                        raise ValueError("Unsafe translation model archive path")
                archive.extractall(cache)
        self.processor = sentencepiece.SentencePieceProcessor(model_file=str(model_root / "sentencepiece.model"))
        self.translator = ctranslate2.Translator(str(model_root / "model"), device="cpu", compute_type="int8")

    def translate(self, text):
        tokens = self.processor.encode(text, out_type=str)
        result = self.translator.translate_batch([tokens], beam_size=4)[0]
        translated = self.processor.decode(result.hypotheses[0]).replace("▁", "").strip()
        if not translated:
            raise ValueError("Local translation returned empty output")
        # Keep product names recognizable when the model translates them literally.
        if "DeepSeek" in text:
            translated = translated.replace("深层搜索", "DeepSeek").replace("深度搜索", "DeepSeek")
        return translated
