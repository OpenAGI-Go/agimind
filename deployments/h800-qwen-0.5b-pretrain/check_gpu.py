import torch

print("cuda:", torch.cuda.is_available())
print("gpu:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
print("bf16:", torch.cuda.is_bf16_supported())
x = torch.randn(2, 4, device="cuda", dtype=torch.bfloat16)
print("tensor ok:", x.shape, x.dtype)
