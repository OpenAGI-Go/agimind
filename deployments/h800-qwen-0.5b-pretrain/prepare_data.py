"""把一小份英文维基切成 2048 一段，存成训练/验证用的 packed 张量。"""

from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoTokenizer

SEQ_LEN = 2048
MIN_CHARS = 50
MODEL_NAME = "Qwen/Qwen2.5-0.5B"
ROOT = Path("/root/autodl-tmp/llm-pretrain")
PACKED_DIR = ROOT / "data" / "packed"


def texts_to_ids(texts, tokenizer):
    """过滤短文，切词，每篇末尾加 eos，再拼成一条超长数字流。"""
    all_ids = []
    n_keep = 0
    for text in texts:
        if not text or len(text.strip()) < MIN_CHARS:
            continue
        ids = tokenizer(text, add_special_tokens=False)["input_ids"]
        if not ids:
            continue
        all_ids.extend(ids)
        all_ids.append(tokenizer.eos_token_id)
        n_keep += 1
    return all_ids, n_keep


def pack(all_ids, seq_len):
    """按 2048 切开。尾巴丢掉，不补 pad。"""
    n_seg = len(all_ids) // seq_len
    if n_seg == 0:
        raise SystemExit(f"token 太少（{len(all_ids)}），切不出一段 {seq_len}")
    used = n_seg * seq_len
    return torch.tensor(all_ids[:used], dtype=torch.long).view(n_seg, seq_len)


def dump_split(name, texts, tokenizer):
    all_ids, n_docs = texts_to_ids(texts, tokenizer)
    packed = pack(all_ids, SEQ_LEN)
    out = PACKED_DIR / f"{name}.pt"
    torch.save(packed, out)
    print(f"[{name}] 文章数: {n_docs}")
    print(f"[{name}] 总 token 数: {len(all_ids)}")
    print(f"[{name}] 切出来多少段: {packed.shape[0]}  形状: {tuple(packed.shape)}")
    print(f"[{name}] 已保存: {out}")
    return packed


def main():
    PACKED_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 老名字 wikitext 没有命名空间，新版 huggingface_hub 会报
    # Repository id must be 'namespace/name'。正式仓库是 Salesforce/wikitext。
    ds = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1")
    dump_split("train", ds["train"]["text"], tokenizer)
    dump_split("valid", ds["validation"]["text"], tokenizer)


if __name__ == "__main__":
    main()
