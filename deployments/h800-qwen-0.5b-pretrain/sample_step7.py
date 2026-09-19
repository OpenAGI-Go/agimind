"""第 7 步：加载加时长后的存档，试生成并在 packed_step7/valid.pt 上算困惑度。"""

import math
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoConfig, AutoTokenizer, Qwen2ForCausalLM

ROOT = Path("/root/autodl-tmp/llm-pretrain")
CKPT_DIR = ROOT / "checkpoints"
CKPT_BEST = CKPT_DIR / "step7_best.pt"
CKPT_LATEST = CKPT_DIR / "step7_latest.pt"
VALID_PT = ROOT / "data" / "packed_step7" / "valid.pt"
MODEL_NAME = "Qwen/Qwen2.5-0.5B"
BATCH_SIZE = 8
MAX_NEW_TOKENS = 80
TEMPERATURE = 0.8

PROMPTS = [
    "北京是",
    "The meaning of life is",
]


def load_model_and_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    ckpt_path = CKPT_BEST if CKPT_BEST.exists() else CKPT_LATEST
    if not ckpt_path.exists():
        raise SystemExit(f"找不到第 7 步存档: {CKPT_BEST} 或 {CKPT_LATEST}")

    config = AutoConfig.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = Qwen2ForCausalLM(config)
    ckpt = torch.load(ckpt_path, map_location="cpu")
    model.load_state_dict(ckpt["model"])
    model = model.to(dtype=torch.bfloat16, device="cuda")
    model.eval()
    print(
        f"loaded {ckpt_path}  step={ckpt.get('step')}  "
        f"train_loss={ckpt.get('loss')}  valid_loss={ckpt.get('valid_loss')}"
    )
    return model, tokenizer


@torch.no_grad()
def generate(model, tokenizer, prompt):
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    out = model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=True,
        temperature=TEMPERATURE,
        pad_token_id=tokenizer.eos_token_id,
    )
    return tokenizer.decode(out[0], skip_special_tokens=False)


@torch.no_grad()
def valid_ppl(model):
    data = torch.load(VALID_PT, map_location="cpu")
    loader = DataLoader(data, batch_size=BATCH_SIZE, shuffle=False, drop_last=True)
    total, n = 0.0, 0
    for batch in loader:
        batch = batch.to("cuda")
        out = model(input_ids=batch, labels=batch)
        total += out.loss.detach().item()
        n += 1
    loss = total / max(1, n)
    return loss, math.exp(min(loss, 20))


def main():
    model, tokenizer = load_model_and_tokenizer()

    for prompt in PROMPTS:
        text = generate(model, tokenizer, prompt)
        print("=" * 60)
        print("prompt:", prompt)
        print("output:", text)

    loss, ppl = valid_ppl(model)
    print("=" * 60)
    print(f"valid loss: {loss:.4f}  ppl: {ppl:.1f}")


if __name__ == "__main__":
    main()
