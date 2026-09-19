"""第 7 步：换成更大的 wikitext-103，另存到 data/packed_step7/，不覆盖冒烟数据。"""

from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoTokenizer

SEQ_LEN = 2048
MIN_CHARS = 50
TOKENIZE_BATCH = 512
MODEL_NAME = "Qwen/Qwen2.5-0.5B"
ROOT = Path("/root/autodl-tmp/llm-pretrain")
PACKED_DIR = ROOT / "data" / "packed_step7"


def texts_to_ids(texts, tokenizer):
    kept = [t for t in texts if t and len(t.strip()) >= MIN_CHARS]
    all_ids = []
    eos = tokenizer.eos_token_id
    total = len(kept)
    for i in range(0, total, TOKENIZE_BATCH):
        chunk = kept[i : i + TOKENIZE_BATCH]
        enc = tokenizer(chunk, add_special_tokens=False)
        for ids in enc["input_ids"]:
            if not ids:
                continue
            all_ids.extend(ids)
            all_ids.append(eos)
        done = min(i + TOKENIZE_BATCH, total)
        if done == total or done % 5000 < TOKENIZE_BATCH:
            print(f"  tokenized {done}/{total}", flush=True)
    return all_ids, len(kept)


def pack(all_ids, seq_len):
    n_seg = len(all_ids) // seq_len
    if n_seg == 0:
        raise SystemExit(f"token 太少（{len(all_ids)}），切不出一段 {seq_len}")
    used = n_seg * seq_len
    return torch.tensor(all_ids[:used], dtype=torch.long).view(n_seg, seq_len)


def dump_split(name, texts, tokenizer):
    print(f"[{name}] 开始切词，原始行数 {len(texts)}", flush=True)
    all_ids, n_docs = texts_to_ids(texts, tokenizer)
    packed = pack(all_ids, SEQ_LEN)
    out = PACKED_DIR / f"{name}.pt"
    torch.save(packed, out)
    print(f"[{name}] 文章数: {n_docs}", flush=True)
    print(f"[{name}] 总 token 数: {len(all_ids)}", flush=True)
    print(f"[{name}] 切出来多少段: {packed.shape[0]}  形状: {tuple(packed.shape)}", flush=True)
    print(f"[{name}] 已保存: {out}", flush=True)
    return packed


def main():
    PACKED_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # wikitext-2 只有约 250 万 token，1 小时会把同一份数据翻几十遍。
    # wikitext-103 大约 1 亿 token，下载约几百 MB，打包后大约 1G 出头。
    ds = load_dataset("Salesforce/wikitext", "wikitext-103-raw-v1")
    dump_split("train", ds["train"]["text"], tokenizer)
    dump_split("valid", ds["validation"]["text"], tokenizer)


if __name__ == "__main__":
    main()
