"""随机初始化 Qwen2.5-0.5B 结构，用 packed train.pt 手写循环跑 100 步。"""

import math
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoConfig, Qwen2ForCausalLM

ROOT = Path("/root/autodl-tmp/llm-pretrain")
TRAIN_PT = ROOT / "data" / "packed" / "train.pt"
VALID_PT = ROOT / "data" / "packed" / "valid.pt"
CKPT_DIR = ROOT / "checkpoints"
MODEL_NAME = "Qwen/Qwen2.5-0.5B"

SEQ_LEN = 2048
BATCH_SIZE = 8
GRAD_ACCUM = 4
MAX_STEPS = 100
BASE_LR = 3e-4
WEIGHT_DECAY = 0.1
CLIP = 1.0
LOG_EVERY = 10


def lr_at(step, max_steps, base_lr=BASE_LR, warmup_ratio=0.02):
    warmup = max(1, int(max_steps * warmup_ratio))
    if step < warmup:
        return base_lr * step / warmup
    progress = (step - warmup) / max(1, max_steps - warmup)
    return base_lr * 0.5 * (1.0 + math.cos(math.pi * progress))


def set_lr(optimizer, lr):
    for group in optimizer.param_groups:
        group["lr"] = lr


def build_model():
    # 只要图纸，不要官方权重
    config = AutoConfig.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = Qwen2ForCausalLM(config)
    return model.to(dtype=torch.bfloat16, device="cuda")


@torch.no_grad()
def valid_loss(model, batch_size):
    data = torch.load(VALID_PT, map_location="cpu")
    loader = DataLoader(data, batch_size=batch_size, shuffle=False, drop_last=True)
    model.eval()
    total, n = 0.0, 0
    for batch in loader:
        batch = batch.to("cuda")
        out = model(input_ids=batch, labels=batch)
        total += float(out.loss)
        n += 1
    model.train()
    return total / max(1, n)


def main():
    CKPT_DIR.mkdir(parents=True, exist_ok=True)

    train = torch.load(TRAIN_PT, map_location="cpu")
    print("train:", tuple(train.shape), train.dtype)
    print("train[0, :20]:", train[0, :20].tolist())

    loader = DataLoader(train, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
    model = build_model()
    n = sum(p.numel() for p in model.parameters())
    print("params(M):", round(n / 1e6, 1))

    optimizer = torch.optim.AdamW(model.parameters(), lr=BASE_LR, weight_decay=WEIGHT_DECAY)
    optimizer.zero_grad(set_to_none=True)
    model.train()

    last_raw_loss = None
    t0 = time.time()
    tokens_window = 0

    for step, batch in enumerate(loader, start=1):
        batch = batch.to("cuda")
        # labels 和 input 一样，模型内部会右移；不要自己再移一次
        out = model(input_ids=batch, labels=batch)
        last_raw_loss = out.loss.detach().item()
        (out.loss / GRAD_ACCUM).backward()
        tokens_window += BATCH_SIZE * SEQ_LEN

        if step % GRAD_ACCUM == 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)

        lr = lr_at(step, MAX_STEPS)
        set_lr(optimizer, lr)

        if step % LOG_EVERY == 0:
            dt = max(time.time() - t0, 1e-6)
            mem = torch.cuda.max_memory_allocated() / 1024**3
            print(
                f"step {step:4d}  loss {last_raw_loss:.4f}  lr {lr:.2e}  "
                f"tokens/s {tokens_window / dt:.0f}  mem {mem:.2f}G"
            )
            t0 = time.time()
            tokens_window = 0

        if step >= MAX_STEPS:
            break

    ckpt = CKPT_DIR / "latest.pt"
    torch.save(
        {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "step": MAX_STEPS,
            "loss": last_raw_loss,
        },
        ckpt,
    )
    print("saved:", ckpt)

    vloss = valid_loss(model, BATCH_SIZE)
    print(f"valid loss: {vloss:.4f}  ppl: {math.exp(min(vloss, 20)):.1f}")


if __name__ == "__main__":
    main()
