# 开源项目与规范仓库

> 跟踪上游仓库与公开文档状态。个人 fork 可在备注一笔带过。

## 规范（ratified / 进行中）

| 项目 | 仓库 / 文档 | 状态印象 | 备注 |
|------|-------------|----------|------|
| BRS | [riscv-brs](https://github.com/riscv-non-isa/riscv-brs) · [docs v1.0](https://docs.riscv.org/reference/brs/v1.0/) | v1.0 ratified（2025-08）；main 攒 1.1 | 理解笔记：[firmware-brs.md](./firmware-brs.md) |
| Server Platform | [docs](https://docs.riscv.org/reference/server-platform/) | v1.0 ratified（约 2026-05） | 强制 BRS-I + RVA23S64 等 |
| RVA23 Profiles | [docs](https://docs.riscv.org/reference/rva23/) | ratified 文档页 | 服务器应用核 |
| SBI | [riscv-sbi-doc](https://github.com/riscv-non-isa/riscv-sbi-doc) | 持续 | BRS 要求 ≥ 2.0；服务器另有更高扩展要求 |
| Server SoC | [server-soc](https://github.com/riscv-non-isa/server-soc) | 见官方 | 被 Server Platform 引用 |
| RIMT 等 ACPI | [riscv-acpi-rimt](https://github.com/riscv-non-isa/riscv-acpi-rimt) 等 | 见官方 | IOMMU 等表 |

## 固件 / 模拟 / 内核

| 项目 | 仓库 | 跟进点 |
|------|------|--------|
| OpenSBI | [opensbi](https://github.com/riscv-software-src/opensbi) | HSM、DBTR、SSE 等扩展完备度 |
| EDK2 | [edk2](https://github.com/tianocore/edk2) · [edk2-platforms](https://github.com/tianocore/edk2-platforms) | RISC-V 平台包、BRS conformance GUID |
| QEMU | [qemu](https://gitlab.com/qemu-project/qemu) | virt / 服务器向机器模型、ACPI |
| Linux | [torvalds/linux](https://github.com/torvalds/linux) | riscv、ACPI、AIA |
| Ruyi Firmware | [ruyifirmware](https://github.com/openRuyi-Project/ruyifirmware) | coreboot+OpenSBI+EDK2 工程方法；板级 ≠ BRS 基线 |
| BRS 测试草稿 | 仓内 `brs_tests.adoc` | UEFI 项多 FIXME；无对等 ACS |

## 推理框架（上游 RISC-V）

| 项目 | 仓库 | 跟进点 |
|------|------|--------|
| vLLM | [vllm-project/vllm](https://github.com/vllm-project/vllm) | 主干 riscv / RVV 相关路径 |
| SGLang | [sgl-project/sglang](https://github.com/sgl-project/sglang) | PR / 上游合并状态 |

详见 [vllm-sglang.md](./vllm-sglang.md)。

## 个人 fork（可选）

| Fork | 上游 | 用途 |
|------|------|------|
| [maxonxie/riscv-brs](https://github.com/maxonxie/riscv-brs) | riscv-non-isa/riscv-brs | 读规范、提 issue/PR |

## 状态栏（随手改）

| 日期 | 记下的变化 |
|------|------------|
| 2026-10-21 | 建目录；BRS 笔记迁入；列出主规范与固件/推理上游 |
