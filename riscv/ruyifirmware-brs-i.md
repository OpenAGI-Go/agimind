# 学习记录：ruyifirmware 与 BRS-I

> 本笔记记录一次阅读过程：看开源 [ruyifirmware](https://github.com/openRuyi-Project/ruyifirmware)，对照 [BRS](https://github.com/riscv-non-isa/riscv-brs) 的 **BRS-I**，弄清数据中心场景下「固件 ↔ OS」契约和板级工程差在哪。  
> 相关：[firmware-brs.md](./firmware-brs.md)

本地树：`AGI/riscv/agent-cpu/ruyifirmware`（浅克隆；已看过 `coreboot` / `opensbi` / `edk2-ruyi`）。

---

## 1. 这次在想什么

数据中心关心的是通用 OS 镜像能否互操作，规范落在 **BRS-I**（Server Platform 里固件这一层）。  
ruyifirmware 是板级工程（当前文档写的是 SpacemiT K3 Pico ITX），拿来看分层和代码落点，方便对照「板级常见怎么做」和「BRS-I 原文要求什么」。

---

## 2. BRS-I 原文里记下的要点

`recipes` 总表（BRS-I）：

| Profile | UEFI | ACPI | DT | SBI | SMBIOS |
|---------|------|------|-----|-----|--------|
| ≥ RVA20S64 | ≥ 2.10 | ≥ 6.6 | optional, ≥ v0.3 | ≥ 2.0 | ≥ 3.7.0 |

- **`UEFI_080`**：给 OS 的 Device Tree **只能**在「没有真实硬件描述」时使用（dummy，例如 initrd hand-off）。  
- **SBI**：≥ 2.0；**HSM**（Hart State Management，起停/查询 secondary hart）必须——不是密码学那个 HSM。  
- BRS-B 节另有一句：ACPI 与 DT 描述硬件 **二选一、不可同时**。BRS-I 则是 ACPI 在总表里必选，DT 受限。

自己用的口诀（只概括「硬件怎么交给 OS」，不是全表缩写）：

```text
给 OS 的硬件描述：板级常见 → 完整 DT；  BRS-I → ACPI（DT 至多 dummy）
BRS-I 完整配方：UEFI + ACPI + SBI(+HSM) + SMBIOS
```

---

## 3. ruyifirmware 里看到的启动链与落点

```text
BootROM / SPI
  → coreboot（SoC + 板级，可按 CPU mode 改 DT）
  → OpenSBI（PLATFORM=generic + spacemit/k3）
  → EDK2（edk2-ruyi / SpacemitPlatformPkg）
  → OS（配置表里的完整硬件 DT）
```

| 层 | 路径（印象） |
|----|----------------|
| SoC / 早启 | `coreboot/.../soc/spacemit/k3/`、`mainboard/.../k3-pico-itx/`（含 `cpu_config.c`） |
| OpenSBI | `platform/generic/spacemit/k3*.c`、HSM 等 utils；`docs/platform/spacemit-k3.md` |
| UEFI 平台包 | `edk2-ruyi/SpacemitPlatformPkg/`（`PicoItx.dsc`、各类 `K3*Dxe` / Library） |
| DT 输入 | `linux/.../dts/spacemit/k3-pico-itx.dts` → `make dtb` 进 CBFS |

---

## 4. DT 有没有描述硬件？

有。`FdtDxe` 从 handoff 取出 FDT，改 MAC / CPU compatible / QSPI status 等后  
`InstallConfigurationTable(&gFdtTableGuid, …)` 交给 OS。  
树里有 `spacemit,k3`、`spacemit,x100` / `a100`、网卡、QSPI 等——是**完整硬件描述**，不是 BRS-I 允许的 dummy DT。

工程里也能看到 OpenSBI、板级 SMBIOS、UEFI 形态；和 BRS-I 的主要分叉仍在 **给 OS 的硬件描述通道（DT vs ACPI）**。

---

## 5. 对照时记下的对应关系

| 能力 | 样本里大致在哪 | BRS-I 侧怎么要求（原文印象） |
|------|----------------|------------------------------|
| 早启 / DDR / 时钟 | coreboot soc + mainboard | 规范不管内部实现 |
| hart 起停 | OpenSBI spacemit + HSM | SBI HSM 必须 |
| 硬件真相给 OS | 完整 DT（`FdtDxe`） | ACPI；DT 不得描述硬件 |
| PCIe / 外设发现 | UEFI 驱动 + DT compatible | MCFG + AML 等 |
| 库存信息 | 板级 SMBIOS | SMBIOS ≥ 3.7 等细则 |

---

## 6. 参考链接

| 资源 | URL |
|------|-----|
| ruyifirmware | https://github.com/openRuyi-Project/ruyifirmware |
| edk2-ruyi | https://github.com/openRuyi-Project/edk2-ruyi |
| BRS | https://github.com/riscv-non-isa/riscv-brs |
| BRS 文档 | https://docs.riscv.org/reference/brs/v1.0/ |
| Server Platform | https://github.com/riscv-non-isa/riscv-server-platform |

---

## 状态栏

| 日期 | 记下的变化 |
|------|------------|
| 2026-10-22 | 读 ruyi 与 BRS-I，记启动链、DT 行为、配方总表与 `UEFI_080` |
| 2026-10-22 | 收紧口诀：分叉点=硬件描述；BRS-I 全表含 SBI/SMBIOS |
| 2026-10-22 | 改回学习过程记录，去掉路径指导/验收式写法 |
