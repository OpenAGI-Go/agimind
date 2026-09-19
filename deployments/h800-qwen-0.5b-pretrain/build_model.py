from transformers import AutoConfig, AutoTokenizer, Qwen2ForCausalLM
import torch

name = "Qwen/Qwen2.5-0.5B"
tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

config = AutoConfig.from_pretrained(name, trust_remote_code=True)
model = Qwen2ForCausalLM(config)  # 随机初始化，不是加载官方权重
model = model.to(dtype=torch.bfloat16, device="cuda")

n = sum(p.numel() for p in model.parameters())
print("params(M):", round(n / 1e6, 1))
