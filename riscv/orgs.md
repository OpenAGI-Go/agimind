# 开源 / 标准组织跟进

> 记组织角色、公开产出与跟进入口。

| 组织 | 角色 | 跟进入口 | 备注 |
|------|------|----------|------|
| [RISC-V International](https://riscv.org/) | ISA 与非 ISA 规范的主标准组织 | [Specs Library](https://docs.riscv.org/) · [GitHub org](https://github.com/riscv) / [riscv-non-isa](https://github.com/riscv-non-isa) | BRS、Server Platform、Profiles 等归这里 |
| BRS Task Group | Boot and Runtime Services | [riscv-brs](https://github.com/riscv-non-isa/riscv-brs) | 固件↔OS 契约；服务器走 BRS-I |
| Server Platform Task Group | 服务器平台总规范 | [docs](https://docs.riscv.org/reference/server-platform/) | 引用 BRS-I + RVA23 等 |
| [TianoCore](https://www.tianocore.org/) | UEFI 开源实现（EDK2） | [edk2](https://github.com/tianocore/edk2) · [edk2-platforms](https://github.com/tianocore/edk2-platforms) | BRS-I 路径的常见 UEFI 实现 |
| [UEFI Forum](https://uefi.org/) | UEFI / ACPI 规范与 SCT | [Specifications](https://uefi.org/specifications) | Arm 侧有 SystemReady；RISC-V 用 BRS + RSCV ACPI ID |
| OpenSBI 维护社区 | SBI 参考实现 | [opensbi](https://github.com/riscv-software-src/opensbi) | M-mode / 更高特权侧常见实现 |
| [openRuyi Project](https://github.com/openRuyi-Project) | 开源 RISC-V 系统 / 固件相关 | [openRuyi](https://github.com/openRuyi-Project/openRuyi) · [ruyifirmware](https://github.com/openRuyi-Project/ruyifirmware) · [文档](https://openruyi.cn) | 社区固件工程参考；≠ 服务器合规基线本身 |
| OERV（中科院软件所相关公开团队） | 开源 RISC-V 生态工程 | 经 openRuyi / 公开推文跟进 | 只记公开项目 |

## 对照用（非 RISC-V 主线，仅作公开标准参照）

| 组织 / 计划 | 为何出现在本表 | 入口 |
|-------------|----------------|------|
| Arm SystemReady / 原 ServerReady | BRS-I / 认证缺口的对照对象 | [SystemReady](https://developer.arm.com/Architectures/Arm%20SystemReady) · [ACS](https://github.com/ARM-software/arm-systemready) |
| Trusted Firmware | Arm TF-A 与启动信任链对照 | [trustedfirmware.org](https://www.trustedfirmware.org/) |

团体标准文本（如 T/GCC 3006）若引用，只作公开标准摘录。详见 [firmware-brs.md](./firmware-brs.md) 链接索引。

## 待补

- [ ] 列全与 Server SoC / AIA / RPMI 相关的 TG 与仓库
- [ ] 记录公开会议 / 邮件列表订阅方式（若有）
