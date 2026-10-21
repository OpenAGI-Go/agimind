# RISC-V 固件与 BRS 理解笔记

> 目的：系统记录对 RISC-V 服务器固件、BRS、Server Platform 及相关 Arm 对照经验的理解。  
> 状态：持续更新。从零基础到能规划「RVA23 服务器引导生态」为止。  
> 规范仓库（本地）：`/Users/max/workdir/AGI/riscv/agent-cpu/riscv-brs/`（fork: maxonxie/riscv-brs；upstream: riscv-non-isa/riscv-brs）  
> 正式文档站点：https://docs.riscv.org/reference/brs/v1.0/

---

## 0. 怎么读这份笔记

建议顺序：

1. 先建立「分层总图」（§1）
2. 再弄清启动链上谁跑、叫什么（§2）
3. 然后读 BRS / BRS-I（§3）和 Server Platform（§4）
4. 需要对照 Arm 经验时看 §5
5. 工程与生态规划看 §6–§7
6. 名词表 §8 随时查

文中「待补」表示已知缺口，读规范或做实验后再填。

---

## 1. 分层总图：这些规范各管什么

一台 RISC-V 服务器要「通用 OS 镜像能装」，约定是一层层叠起来的：

```text
┌─────────────────────────────────────────────────────────┐
│  测试 / 认证（ACS、证书）—— RISC-V 侧仍不完整              │
├─────────────────────────────────────────────────────────┤
│  Server Platform Spec                                      │
│  「合格服务器」总规范：核 + SoC + 外设 + 固件 + 安全 + BMC │
├─────────────────────────────────────────────────────────┤
│  BRS（Boot and Runtime Services）                          │
│  「固件 ↔ OS」契约；服务器走 BRS-I                         │
├─────────────────────────────────────────────────────────┤
│  Server SoC Spec —— 片上硬件接口（中断、PCIe、IOMMU…）      │
├─────────────────────────────────────────────────────────┤
│  ISA Profile（RVA20 / RVA23…）—— CPU 指令与特权能力        │
└─────────────────────────────────────────────────────────┘
```

| 层级 | 回答的问题 | 典型规范 |
|------|------------|----------|
| ISA Profile | 这份二进制依赖哪些指令/扩展？ | RVA23S64 |
| Server SoC | 片上系统硬件接口长什么样？ | Server SoC v1.0 |
| BRS | 固件和 OS 怎么交接、怎么发现硬件？ | BRS v1.0（BRS-I / BRS-B） |
| Server Platform | 整机还要哪些外设、安全、管理？ | Server Platform v1.0 |
| 认证 | 如何证明实现符合上述规范？ | Arm: ACS + SystemReady；RISC-V: 测试规范草稿中 |

**一句话**：Server Platform = 整机总规范；BRS-I = 其中「固件怎么跟操作系统说话」的独立细化版。

---

## 2. 启动链：从上电到 Linux

### 2.1 典型路径（服务器 / BRS-I 方向）

```text
上电
  → BootROM / 硬件信任根（验签、最小初始化）
  → M-mode 平台固件（内存控制器、地址译码、安全相关）
  → OpenSBI（提供 SBI；常驻更高特权）
  → EDK2 / UEFI（Boot Services：枚举、加载、启动菜单）
  → ExitBootServices()
  → OS Loader（GRUB 等） / 内核
  → 运行中仍可调用 UEFI Runtime Services（少量接口）
```

说明：

- **BRS 几乎不规定** M-mode / 信任根怎么实现；那是平台与 Server Platform 安全章的事。
- Guidance 写明：UEFI 驱动与 OS loader 跑在 **supervisor**（S / VS / HS）。实现可从 M-mode 起步，进入 Boot/Runtime Services 前必须切到 supervisor。
- 这与 Arm 上「ATF(BL1–BL31) 做安全与大量硬件初始化，BL33=UEFI 跑非安全世界」是同一类切分，但组件名字不同。

### 2.2 Boot Services vs Runtime Services

这里的 **Runtime 不是** 编程语言运行时（JVM / Python / 容器 runtime）。

| | Boot Services | Runtime Services |
|--|---------------|------------------|
| 何时有效 | `ExitBootServices()` **之前** | **之后**仍可用 |
| 典型能力 | 分配内存、枚举设备、加载镜像 | Get/SetTime、变量、ResetSystem、Capsule 更新等 |
| 类比 | 装修队还在工地 | 交房后留下的物业电话 |

BRS 全称含义：

- **Boot**：怎么启动、怎么交接  
- **Runtime Services**：OS 起来后固件还提供哪些可调用接口  
- 再加上 ACPI / SBI / SMBIOS 等发现与管理约定  

Linux 侧能碰到的例子：`efibootmgr` / EFI 变量、部分 reboot 路径、`fwupd` 与 capsule。

### 2.3 与「设备树启动」的差别

| 路径 | 硬件怎么描述 | 典型场景 |
|------|--------------|----------|
| U-Boot + Device Tree | DT | 板级定制、嵌入式 |
| BRS-B | ACPI **或** DT（二选一） | 定制发行版 / 嵌入式富 OS |
| **BRS-I** | **ACPI 必选**；DT 最多做 hand-off 空壳（如 initrd 地址） | 服务器、通用桌面 |

从嵌入式习惯转到服务器时，最大的心态切换：**发现硬件走 ACPI，不再靠板级 DTB。**

---

## 3. BRS 规范

- 全称：RISC-V Boot and Runtime Services Specification  
- 版本：v1.0 于 **2025-08-29** ratified（BoD 批准）  
- 仓库：`riscv-non-isa/riscv-brs`；本地：`/Users/max/workdir/AGI/riscv/agent-cpu/riscv-brs/`  
- 当前 `main` 在攒 **v1.1**（已从 Server Platform 回灌部分规则）  
- 性质：**固件↔OS 契约**，不是微架构规范，也不是可运行代码仓（AsciiDoc 出 PDF/HTML）

### 3.1 两套 Recipe

| | BRS-I（Interoperable） | BRS-B（Bespoke） |
|--|------------------------|------------------|
| 场景 | 服务器、桌面、笔记本等通用机 | 手机、实时、定制发行版 |
| 目标 | **一张通用 OS 镜像**能启动 | 板级定制软件能启动 |
| UEFI | ≥ 2.10 | EBBR ≥ 2.1 |
| ACPI | ≥ 6.6 **必选** | 可选 |
| DT | 可选；**不得**用真硬件描述替代 ACPI | 与 ACPI **二选一** |
| SMBIOS | ≥ 3.7.0 必选 | 可选 |
| SBI | ≥ 2.0 | ≥ 2.0 |
| Profile 底线 | RVA20S64 | RVA20S64 |

**服务器必须走 BRS-I**（Server Platform FIRM_010）。

BRS-I 的「成功启动」定义（规范类比）：像 2000 年代初 x86 主板——能装系统，但部分 I/O 可能还要再装驱动。要求的是基本配置够发现设备，**不是**所有设备开箱即用。额外能力不能让通用 OS 出现莫名不稳定；这类行为默认关，只能 opt-in。

### 3.2 Hart 与 SBI

**Hart（HR_010）**  
应用核至少 RVA20S64。BRS 对微架构几乎不规定。

**SBI（两条 recipe 共用）**

| 规则 | 要求 |
|------|------|
| SBI_010 | ≥ 2.0 |
| SBI_020 | 必须有 **HSM**（起停从核） |
| SBI_030 | 无 Sstc → 必须有 TIME |
| SBI_040/050 | 无 IMSIC → 必须有 sPI、RFNC |
| SBI_060 | 无 Sscsrind/Ssccfg → 必须有 PMU |
| SBI_070 | SPCR Interface Type 0x15 → 必须有 DBCN |

逻辑：**硬件能直接做的，就不强制走 SBI；硬件缺了，固件用 SBI 补上。**

> 待补：main 上拟进 1.1 的 SBI_080（DBTR）、SBI_090（SSE）——来自 Server Platform。

### 3.3 BRS-I UEFI 要点

- 64-bit UEFI；内存缓解满足第三方 CA 要求  
- 默认 `EFI_MEMORY_WB`；页表 identity map；支持 `EFI_MEMORY_ATTRIBUTE_PROTOCOL`  
- Ready-to-Boot 前 **从核必须 offline**，由 OS loader/OS 再拉起  
- 必须声明 UEFI 与 **BRS conformance profile GUID**（声明 = 宣称本节全合规）  
- 有 PCIe：无论是否从 PCIe 启动，都要初始化 RC 并完成资源分配  
- `ResetSystem()` 必做；OS 应优先用它  
- Secure Boot / TPM / UpdateCapsule：有条件 MUST（见规范 USEC_*、UFU_*）  
- PI（Platform Initialization）规范是 MAY，不是 MUST  

### 3.4 BRS-I ACPI 要点

- 纯 64-bit：不要 RSDT；hardware-reduced（不要 FACS）  
- 必有 **PPTT**；无 GOP 则必有 **SPCR**  
- 最小表集合（guidance）：RSDP、XSDT、FADT、DSDT、MADT、**RHCT**、PPTT；按需 MCFG、SPCR、TPM2、SRAT/SLIT、APEI、**RIMT**  
- **AML** = ACPI Machine Language（ASL 编译后的字节码，不是语言 runtime）  
- RISC-V ACPI ID（`RSCV`）：PLIC/APLIC/UART/IOMMU/MPXY/RPMI MSI 等  

### 3.5 BRS-I SMBIOS 要点

- 必有 Type 4（Processor）、Type 44（每 hart）  
- 有条件：IPMI / Redfish / TPM 相关 Type  
- 管理与资产面，不是启动主路径  

### 3.6 测试规范现状

仓库内 `brs_tests.adoc`：按规则号写测试算法。Hart/SBI 有步骤；**UEFI 大量仍是 FIXME**。  
有 ACS 的意图，成熟度远低于正文。这是相对 Arm ServerReady 最大的缺口之一。

### 3.7 仓库关键节点（本地 `riscv/agent-cpu/riscv-brs`）

| 提交/标签 | 意义 |
|-----------|------|
| `v1.0` (874ca6a, 2025-08-29) | BoD 批准，正式可引用 |
| `de710c4` | 初始测试规范草稿 |
| `db8537a` | 从 Server Platform 回灌 DBTR/SSE/RIMT/FCFI 等 → 面向 1.1 |
| `c73be97` | BRS 1.1 conformance GUID |
| `1036cc3` | AML_080 澄清扩至 RSCV0006 |

维护者：Aaron Durbin、Andrei Warkentin、Anup Patel、Sunil V L。

---

## 4. Server Platform 是什么

**RISC-V Server Platform Specification**：定义「一台合格的 RISC-V 服务器」必须具备的能力集合。

它包含：

- 应用核：**RVA23S64** + 规范列出的额外扩展（如 Sv48、Sdtrig、Zkr、Ssaia…）  
- SoC：符合 Server SoC  
- 外设：规定的 UART、RTC、TPM 等  
- 固件：**必须 BRS-I**，并有更高要求（如 SBI 3.0 DBTR 等）  
- 安全：硬件 RoT、Secure Boot、签名更新、生命周期等  
- 管理：BMC、带内/带外（Redfish/IPMI 等）  

版本印象：v1.0 于 2026-05 前后 ratified（以官方 PDF 为准）。  
PDF：https://docs.riscv.org/reference/server-platform/

与 BRS 的关系：

- BRS 底线 profile 写到 RVA20；**服务器 ISA 以 Server Platform 的 RVA23 为准**  
- BRS 管固件↔OS；Server Platform 管整机，并强制引用 BRS-I  
- 1.1 草案正在把部分 Server Platform 固件规则收进 BRS 正文，减少「两份规范来回翻」

---

## 5. 与 Arm 经验对照

来自此前阅读的公众号与公开材料（ServerReady → SystemReady → T/GCC 3006；ATF；UEFI 董事会等）。

| Arm | RISC-V 大致对应 |
|-----|-----------------|
| SBSA / BSA | Server SoC + Server Platform 硬件章 |
| SBBR | BRS-I（UEFI + ACPI + SMBIOS）+ SBI |
| TF-A（BL1–BL31） | M-mode 平台固件 + OpenSBI + 独立 RoT（切分不完全相同） |
| BL33 = UEFI | EDK2 |
| ACS + ServerReady / SystemReady | BRS 测试草稿；**尚无对等行业证书体系** |
| T/GCC 3006 | SystemReady SR 的中国团体标准本土化（归口 GCC） |

Arm 路径可记成：**规范 → 参考实现 → ACS → 证书 → 招标引用**。  
RISC-V 目前强在前半段规范，弱在 ACS/证书与统一参考平台。

国内团体标准启示（T/GCC 3006）：可等同采用国际规范 + 本地附录（界面语言、商密建议等），但必须同步发布**可跑的测试**，否则厂商无法自测。

开源固件工程参考：openRuyi **Ruyi Firmware**（coreboot + OpenSBI + EDK2，K3 上验证）。工程方法（可构建、刷写、恢复）可学；**板级适配 ≠ 服务器合规基线**。

---

## 6. 工程落地：若做 RVA23 服务器引导

### 6.1 契约优先级

1. 内部规则清单：合并 BRS-I 的 `UEFI_/ACPI_/SBI_/SMBIOS_` 与 Server Platform 的 `RVA_/HSOC_/HPER_/FIRM_/SEC_`  
2. QEMU 黄金参考机 + 同一套固件源（OpenSBI + EDK2）+ 夜间合规测试  
3. 真机 / FPGA：只提交与参考机的差异（内存初始化、ACPI 描述、RoT 挂钩）  
4. 一张**无板级补丁**的发行版镜像能启动  
5. 刷写/恢复流程产品化（可参考 Ruyi 的 normal/recovery、读回校验）  
6. 安全分阶段：启动熵 → 签名更新 → Secure Boot 可开关 → 独立 RoT / 证明  

### 6.2 生态与标准（此前规划摘要）

- 开源：参考平台 upstream（QEMU、OpenSBI、edk2-platforms、Linux）；测试套件与规范版本对齐  
- 锚点客户：1 家 OSV、1 家独立固件厂商、1 家 ODM、1 家云/整机需求方  
- 商业：兼容 / 认证 / 安全增强 三档；中立方发证；国内团体标准若做则引用 BRS-I + Server Platform，本地条款另附  

Agent / 推理 runtime **不进入**引导生态的完成定义；完成标志是：未改过的 OS 镜像在持证机器上能启动。

---

## 7. 文档与规范索引

| 资源 | 链接 / 位置 |
|------|-------------|
| BRS 站点 | https://docs.riscv.org/reference/brs/v1.0/ |
| BRS GitHub | https://github.com/riscv-non-isa/riscv-brs |
| 本地克隆 | `/Users/max/workdir/AGI/riscv/agent-cpu/riscv-brs/` |
| Server Platform PDF | https://docs.riscv.org/reference/server-platform/ |
| RVA23 | https://docs.riscv.org/reference/rva23/ |
| OpenSBI | https://github.com/riscv-software-src/opensbi |
| EDK2 | https://github.com/tianocore/edk2 |
| Ruyi Firmware | https://github.com/openRuyi-Project/ruyifirmware |
| T/GCC 3006 下载 | https://www.gccorg.com/article/69/428.html |

### 7.1 此前收集的微信参考链接

固件/标准相关：

1. https://mp.weixin.qq.com/s/3Ztu6k2vWDLtTZ3b8WIhBg — Ruyi Firmware  
2. https://mp.weixin.qq.com/s/Pc394a_ZY2DAklFLOweAhA — T/GCC 3006  
3. https://mp.weixin.qq.com/s/yUlsCdIcg3W2g3BIDCNvAg — SystemReady 介绍  
4. https://mp.weixin.qq.com/s/QYPHbSpRThkDZShyVkXYUA — BSA / BBR  
5. https://mp.weixin.qq.com/s/KEzDsU_PCLrm8eMkLqRNZQ — ATF / TF-A  
6. https://mp.weixin.qq.com/s/k7fl3oxofQ6yW-F_I3u6fQ — Arm 进 UEFI 董事会  
7. https://mp.weixin.qq.com/s/e4duGiJUzZkYV7pQ07kLqA — ServerReady 发布  

产业背景（非固件标准正文）：

8. https://mp.weixin.qq.com/s/I4eMPrLJ4EZYk6ZHmbEBGA — 高通收购 Akeana  

---

## 8. 名词表（速查）

| 名词 | 含义 |
|------|------|
| ISA | 指令集架构；软硬件契约 |
| Profile / RVA23 | 打包好的必选扩展集合；应用处理器代际 |
| Hart | 硬件线程（逻辑 CPU） |
| SoC | 片上系统 |
| Server Platform | 合格 RISC-V 服务器的总规范 |
| BRS | 固件与 OS 的启动/运行时服务规范 |
| BRS-I / BRS-B | 通用互操作 / 定制 两套 recipe |
| Firmware | 开机最先跑的软件，初始化并交接给 OS |
| UEFI | 固件接口标准（启动与部分运行时服务） |
| Boot Services | ExitBootServices 前的 UEFI 服务 |
| Runtime Services | OS 起来后仍可调用的 UEFI 服务（≠ 语言 runtime） |
| EDK2 | UEFI 的主流开源实现 |
| SBI / OpenSBI | S 态调用更高特权的接口 / 常见实现 |
| ACPI | OS 发现硬件与电源等的表与接口 |
| ASL / AML | ACPI 源码 / 编译后的字节码 |
| SMBIOS | 资产与管理信息表 |
| Device Tree | 板级硬件描述树；BRS-I 下不作主发现路径 |
| EBBR | 嵌入式基线启动要求；BRS-B 使用 |
| PCIe / ECAM | 扩展总线 / 配置空间内存映射访问 |
| IOMMU / RIMT | 设备地址翻译隔离 / 其 ACPI 描述表 |
| PLIC / APLIC / AIA | 中断控制器及高级中断架构 |
| BMC | 基板管理控制器（带外管理） |
| RoT | 信任根 |
| Secure Boot | 启动验签 |
| TPM | 可信平台模块 |
| ACS / SystemReady | Arm 合规测试套件 / 认证计划 |
| GCC（联盟） | Global Computing Consortium，团体标准归口方（≠ 编译器） |

---

## 9. 待深入（学习 backlog）

- [ ] 通读 BRS `v1.0` 标签正文，对照本文 §3 纠错  
- [ ] 通读 Server Platform v1.0，整理 `FIRM_/SEC_/HPER_` 清单  
- [ ] `git diff v1.0..main`：列出 1.1 相对 1.0 的规则变更  
- [ ] 在 QEMU 上跑通一套 OpenSBI + EDK2 + 通用 Linux 镜像  
- [ ] 对照一份真实 ACPI dump（MADT / RHCT / PPTT / SPCR）  
- [ ] 跟踪 `brs_tests.adoc` 与社区测试实现进展  
- [ ] 梳理国内若做「RISC-V SystemReady 类」团体标准时的引用关系  

---

## 10. 修订记录

| 日期 | 变更 |
|------|------|
| 2026-10-21 | 初稿：总图、启动链、BRS/BRS-I、Server Platform、Arm 对照、名词表、参考链接 |
| 2026-10-21 | 迁入 agimind/notes，规范仓路径改为 agent-cpu 下的本地克隆 |
