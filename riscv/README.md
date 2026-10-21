# RISC-V · 开源组织与项目跟进

本目录专门跟进 **RISC-V 开源组织、开源规范与开源项目**。  
与 `notes/` 里按日期的杂记不同：这里按主题长期维护，方便对照上游。

## 边界（必读）

**可以写**

- RISC-V International 及 Task Group、已批准规范（Profile、BRS、Server Platform 等）
- 上游开源实现：OpenSBI、EDK2、QEMU、Linux、发行版、合规测试草稿等
- 社区固件 / 发行版项目（如 openRuyi Firmware）
- 开源推理框架在 RISC-V 上的上游进展（vLLM、SGLang 等）
- 公开标准与公开会议材料的摘录、对照笔记

**不要写**

- 任何**公司产品**、商业路线图、客户 PoC、内部 JD / 面试稿
- NDA、未公开芯片细节、某家「Agent CPU」方案私货
- 以推销或选型某一家商用 SoC 为目的的材料

公司/产品相关笔记若有需要，放在本仓以外的工作区目录，**不要放进 `agimind/riscv/`**。

## 目录

| 文件 | 内容 |
|------|------|
| [orgs.md](./orgs.md) | 开源 / 标准组织跟进 |
| [projects.md](./projects.md) | 开源项目与规范仓库清单 |
| [firmware-brs.md](./firmware-brs.md) | 固件与 BRS / Server Platform 理解笔记 |
| [vector-matrix-edge-ai.md](./vector-matrix-edge-ai.md) | 向量 / 矩阵扩展与端侧判断（公开 ISA） |
| [vllm-sglang.md](./vllm-sglang.md) | vLLM / SGLang 上游 RISC-V 跟进 |

## 和本仓其他位置的关系

- `notes/`：按日期的摘录仍可出现 RISC-V 话题；**系统性、长期跟进**迁到本目录
- `resources/`：若以后做纯链接索引，可再链到这里
- GitHub 上本仓可点开的只有本目录内相对链接；勿写工作区兄弟目录的 `../` 路径
