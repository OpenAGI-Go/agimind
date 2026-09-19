"""第 7 步：从 100 步存档接着训，读写 packed_step7 和 step7 存档，不覆盖冒烟文件。"""

import math
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoConfig, Qwen2ForCausalLM

ROOT = Path("/root/autodl-tmp/llm-pretrain")
TRAIN_PT = ROOT / "data" / "packed_step7" / "train.pt"
VALID_PT = ROOT / "data" / "packed_step7" / "valid.pt"
CKPT_DIR = ROOT / "checkpoints"
RESUME_CKPT = CKPT_DIR / "smoke100.pt"
LATEST_CKPT = CKPT_DIR / "step7_latest.pt"
BEST_CKPT = CKPT_DIR / "step7_best.pt"
MODEL_NAME = "Qwen/Qwen2.5-0.5B"

SEQ_LEN = 2048
BATCH_SIZE = 8
GRAD_ACCUM = 4
MAX_STEPS = 16000  # 冒烟 100 步约 34 秒 → 16000 步大约 1.5 小时
BASE_LR = 3e-4
WEIGHT_DECAY = 0.1
CLIP = 1.0
LOG_EVERY = 50
EVAL_EVERY = 2000


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
    config = AutoConfig.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = Qwen2ForCausalLM(config)
    return model.to(dtype=torch.bfloat16, device="cuda")


def save_ckpt(path, model, optimizer, step, loss, vloss=None):
    torch.save(
        {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "step": step,
            "loss": loss,
            "valid_loss": vloss,
        },
        path,
    )
    print(f"saved: {path}", flush=True)


@torch.no_grad()
def valid_loss(model, batch_size):
    data = torch.load(VALID_PT, map_location="cpu")
    loader = DataLoader(data, batch_size=batch_size, shuffle=False, drop_last=True)
    model.eval()
    total, n = 0.0, 0
    for batch in loader:
        batch = batch.to("cuda")
        out = model(input_ids=batch, labels=batch)
        total += out.loss.detach().item()
        n += 1
    model.train()
    return total / max(1, n)


def infinite_batches(loader):
    while True:
        for batch in loader:
            yield batch


def main():
    CKPT_DIR.mkdir(parents=True, exist_ok=True)

    train = torch.load(TRAIN_PT, map_location="cpu")
    print("train:", tuple(train.shape), train.dtype, flush=True)
    print("train[0, :20]:", train[0, :20].tolist(), flush=True)

    loader = DataLoader(train, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
    model = build_model()
    n = sum(p.numel() for p in model.parameters())
    print("params(M):", round(n / 1e6, 1), flush=True)

    if RESUME_CKPT.exists():
        ckpt = torch.load(RESUME_CKPT, map_location="cpu")
        model.load_state_dict(ckpt["model"])
        print(
            f"resume weights from {RESUME_CKPT}  old_step={ckpt.get('step')}  old_loss={ckpt.get('loss')}",
            flush=True,
        )
    else:
        print("no smoke checkpoint, start from random init", flush=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=BASE_LR, weight_decay=WEIGHT_DECAY)
    optimizer.zero_grad(set_to_none=True)
    model.train()

    last_raw_loss = None
    best_vloss = float("inf")
    t0 = time.time()
    run_t0 = time.time()
    tokens_window = 0

    for step, batch in enumerate(infinite_batches(loader), start=1):
        batch = batch.to("cuda")
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
            elapsed = (time.time() - run_t0) / 60
            print(
                f"step {step:6d}  loss {last_raw_loss:.4f}  lr {lr:.2e}  "
                f"tokens/s {tokens_window / dt:.0f}  mem {mem:.2f}G  elapsed {elapsed:.1f}min",
                flush=True,
            )
            t0 = time.time()
            tokens_window = 0

        if step % EVAL_EVERY == 0 or step == MAX_STEPS:
            vloss = valid_loss(model, BATCH_SIZE)
            print(f"valid loss: {vloss:.4f}  ppl: {math.exp(min(vloss, 20)):.1f}", flush=True)
            save_ckpt(LATEST_CKPT, model, optimizer, step, last_raw_loss, vloss)
            if vloss < best_vloss:
                best_vloss = vloss
                save_ckpt(BEST_CKPT, model, optimizer, step, last_raw_loss, vloss)

        if step >= MAX_STEPS:
            break

    elapsed = (time.time() - run_t0) / 60
    print(f"done. steps={MAX_STEPS}  elapsed={elapsed:.1f}min  best_valid={best_vloss:.4f}", flush=True)


if __name__ == "__main__":
    main()
