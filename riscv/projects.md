# 开源项目与规范仓库

> 跟踪上游仓库与公开文档状态。个人 fork 可在备注一笔带过。  
> `riscv-non-isa` 组织本地浅克隆：`AGI/riscv/agent-cpu/riscv-non-isa/`（约 34 个活跃仓）。

## `riscv-non-isa` 组织地图（按主题）

组织主页：https://github.com/riscv-non-isa — 放 **非 ISA** 规范（平台、固件、ABI、安全、跟踪、嵌入式等）。ISA Profile 等多在别的 org（如 `riscv`）。

### A. 服务器 / 平台互操作（与 Server Platform 最近）

| 仓库 | 角色 |
|------|------|
| [riscv-server-platform](https://github.com/riscv-non-isa/riscv-server-platform) | 服务器总规范（v1.0 ratified） |
| [riscv-server-soc](https://github.com/riscv-non-isa/riscv-server-soc) | Server SoC 硬件接口 |
| [riscv-server-soc-ts](https://github.com/riscv-non-isa/riscv-server-soc-ts) | Server SoC 测试套件 |
| [riscv-brs](https://github.com/riscv-non-isa/riscv-brs) | 固件↔OS：BRS-I / BRS-B |
| [riscv-sbi-doc](https://github.com/riscv-non-isa/riscv-sbi-doc) | SBI |
| [riscv-acpi-rimt](https://github.com/riscv-non-isa/riscv-acpi-rimt) | ACPI RIMT（IOMMU 映射） |
| [riscv-acpi-ffh](https://github.com/riscv-non-isa/riscv-acpi-ffh) | ACPI FFH |
| [riscv-iommu](https://github.com/riscv-non-isa/riscv-iommu) | IOMMU |
| [riscv-rpmi](https://github.com/riscv-non-isa/riscv-rpmi) | 平台管理消息接口（应用核↔微控制器） |
| [riscv-ras-eri](https://github.com/riscv-non-isa/riscv-ras-eri) | RAS 错误记录寄存器接口 |
| [riscv-cbqri](https://github.com/riscv-non-isa/riscv-cbqri) | Cache/内存 QoS 寄存器接口 |
| [riscv-rqsc](https://github.com/riscv-non-isa/riscv-rqsc) | QoS Controllers ACPI 表 |
| [riscv-uefi](https://github.com/riscv-non-isa/riscv-uefi) | UEFI 相关 |
| [riscv-device-tree-doc](https://github.com/riscv-non-isa/riscv-device-tree-doc) | Device Tree（偏 BRS-B / 嵌入式） |

### B. 机密计算 / 安全

| 仓库 | 角色 |
|------|------|
| [riscv-ap-tee](https://github.com/riscv-non-isa/riscv-ap-tee) | AP-TEE |
| [riscv-ap-tee-io](https://github.com/riscv-non-isa/riscv-ap-tee-io) | AP-TEE-IO（机密 VM 设备） |
| [riscv-external-debug-security](https://github.com/riscv-non-isa/riscv-external-debug-security) | 外部调试安全 |
| [riscv-iopmp](https://github.com/riscv-non-isa/riscv-iopmp) | IOPMP |

### C. Trace / 调试可观测

| 仓库 | 角色 |
|------|------|
| [riscv-trace-spec](https://github.com/riscv-non-isa/riscv-trace-spec) | Processor Trace |
| [riscv-e-trace-encap](https://github.com/riscv-non-isa/riscv-e-trace-encap) | E-Trace 封装 |
| [riscv-hart-trace-interface](https://github.com/riscv-non-isa/riscv-hart-trace-interface) | Hart-Trace Interface |
| [riscv-event-trace](https://github.com/riscv-non-isa/riscv-event-trace) | Event Trace |
| [riscv-instrumentation-trace](https://github.com/riscv-non-isa/riscv-instrumentation-trace) | Instrumentation Trace |
| [riscv-nexus-trace](https://github.com/riscv-non-isa/riscv-nexus-trace) | Nexus Trace |
| [riscv-logic-analyzer-trace](https://github.com/riscv-non-isa/riscv-logic-analyzer-trace) | Logic Analyzer Trace |

### D. 工具链 / ABI / 语言

| 仓库 | 角色 |
|------|------|
| [riscv-elf-psabi-doc](https://github.com/riscv-non-isa/riscv-elf-psabi-doc) | ELF psABI |
| [riscv-asm-manual](https://github.com/riscv-non-isa/riscv-asm-manual) | 汇编手册 |
| [riscv-c-api-doc](https://github.com/riscv-non-isa/riscv-c-api-doc) | C API |
| [riscv-rvv-intrinsic-doc](https://github.com/riscv-non-isa/riscv-rvv-intrinsic-doc) | RVV intrinsics |
| [riscv-toolchain-conventions](https://github.com/riscv-non-isa/riscv-toolchain-conventions) | GNU/LLVM 工具链约定 |
| [riscv-semihosting](https://github.com/riscv-non-isa/riscv-semihosting) | Semihosting |
| [riscv-swi](https://github.com/riscv-non-isa/riscv-swi) | Software Interrupts |

### E. 嵌入式 / 微控制器

| 仓库 | 角色 |
|------|------|
| [riscv-microcontroller-subsystem](https://github.com/riscv-non-isa/riscv-microcontroller-subsystem) | MCU 子系统（RVM） |
| [riscv-rvm-csi](https://github.com/riscv-non-isa/riscv-rvm-csi) | RVM-CSI 可移植层 |

### 与 Server Platform 的依赖关系（读规范时）

```text
Server Platform
  ├── Server SoC (+ ts)
  ├── BRS-I ── SBI, UEFI/ACPI 生态
  │             ├── RIMT / FFH / IOMMU
  │             └── Device Tree（非 BRS-I 主路径）
  ├── Platform Security 相关（AP-TEE 等另仓）
  └── 管理 / RAS / QoS：RPMI, RAS-ERI, CBQRI, RQSC
```

## 规范（ratified / 进行中）重点跟进

| 项目 | 仓库 / 文档 | 状态印象 | 备注 |
|------|-------------|----------|------|
| BRS | [riscv-brs](https://github.com/riscv-non-isa/riscv-brs) · [docs v1.0](https://docs.riscv.org/reference/brs/v1.0/) | v1.0 ratified（2025-08）；main 攒 1.1 | 理解笔记：[firmware-brs.md](./firmware-brs.md) |
| Server Platform | [riscv-server-platform](https://github.com/riscv-non-isa/riscv-server-platform) · [docs](https://docs.riscv.org/reference/server-platform/) | v1.0 ratified（2026-05-06） | 强制 BRS-I + RVA23S64 等 |
| RVA23 Profiles | [docs](https://docs.riscv.org/reference/rva23/) | ratified 文档页 | 多在 `riscv` org，不在 non-isa |
| SBI | [riscv-sbi-doc](https://github.com/riscv-non-isa/riscv-sbi-doc) | 持续 | BRS ≥ 2.0；服务器另有更高扩展 |
| Server SoC | [riscv-server-soc](https://github.com/riscv-non-isa/riscv-server-soc) | 仓内仍标 draft 口吻，以官方状态为准 | 被 Server Platform 引用 |
| RIMT | [riscv-acpi-rimt](https://github.com/riscv-non-isa/riscv-acpi-rimt) | 见官方 | IOMMU ACPI 表 |
| IOMMU | [riscv-iommu](https://github.com/riscv-non-isa/riscv-iommu) | 仓内写 Ratified | |

## 固件 / 模拟 / 内核

| 项目 | 仓库 | 跟进点 |
|------|------|--------|
| OpenSBI | [opensbi](https://github.com/riscv-software-src/opensbi) | HSM、DBTR、SSE 等扩展完备度 |
| EDK2 | [edk2](https://github.com/tianocore/edk2) · [edk2-platforms](https://github.com/tianocore/edk2-platforms) | RISC-V 平台包、BRS conformance GUID |
| QEMU | [qemu](https://gitlab.com/qemu-project/qemu) | virt / 服务器向机器模型、ACPI |
| Linux | [torvalds/linux](https://github.com/torvalds/linux) | riscv、ACPI、AIA |
| Ruyi Firmware | [ruyifirmware](https://github.com/openRuyi-Project/ruyifirmware) | 学习笔记：[ruyifirmware-brs-i.md](./ruyifirmware-brs-i.md) |
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
| 2026-10-22 | 梳理 riscv-non-isa 全组织（34 活跃仓浅克隆至 agent-cpu/riscv-non-isa） |
| 2026-10-22 | 增补 ruyifirmware ↔ BRS-I 对照文 [ruyifirmware-brs-i.md](./ruyifirmware-brs-i.md) |
