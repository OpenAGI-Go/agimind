"""加载第 4 步的存档，试着续写，并在 valid.pt 上算困惑度。"""

import math
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoConfig, AutoTokenizer, Qwen2ForCausalLM

ROOT = Path("/root/autodl-tmp/llm-pretrain")
CKPT = ROOT / "checkpoints" / "latest.pt"
VALID_PT = ROOT / "data" / "packed" / "valid.pt"
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

    # 先按图纸搭空网络，再灌进你自己训的权重，不要 from_pretrained 整模
    config = AutoConfig.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = Qwen2ForCausalLM(config)
    ckpt = torch.load(CKPT, map_location="cpu")
    model.load_state_dict(ckpt["model"])
    model = model.to(dtype=torch.bfloat16, device="cuda")
    model.eval()
    print(f"loaded {CKPT}  step={ckpt.get('step')}  train_loss={ckpt.get('loss')}")
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
    print("100 步后生成几乎一定是乱码，能出字、能加载存档就算成功。")


if __name__ == "__main__":
    main()
