# 阶段 7 · 玩具请求对比

同一条 `research/toy_inference_example.json`。

| 题 | repro (hard_lr1e5_repro) | 官方 NanoJev-unified | argmax |
|---|---|---|---|
| refund / team | billing 0.614 | billing 0.593 | 相同 |
| refund / paid | false p_true 0.140 | false p_true 0.166 | 相同 |
| refund / impact | level 2 | level 2 | 相同 |
| software / team | technical 0.772 | technical 0.649 | 相同 |
| software / paid | true p_true 0.877 | true p_true 0.890 | 相同 |
| software / impact | level 0 | level 0 | 相同 |

- repro：`decode=0`，热服务约 0.03s  
- 官方：`decode=0`，约 0.30s（含冷一点的路径）  
- 结论：数值略有差别（best_step / run 不同），六道题最终选择一致。
