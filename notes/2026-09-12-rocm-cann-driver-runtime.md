# ROCm vs CANN：开源 Driver / Runtime 设计对照

日期：2026-09-12  
承接：[`2026-09-08-tecorigin-ai-accelerator-system-software-plan.md`](../thoughts/2026-09-08-tecorigin-ai-accelerator-system-software-plan.md)  
代码树：[`AI-Chip-Driver-Runtime/`](../../infra/chips/AI-Chip-Driver-Runtime/)

先前会话把太初栈映射成「SDAADriver ≈ 设备驱动层、SDAARuntime ≈ CUDA/HIP Runtime」。本笔记用 **AMD ROCm** 与 **华为 CANN** 两套已开源的 Driver/Runtime，把那张概念图钉到真实模块与提交流程上。

---

## 1. 两套栈的分层（可直接对照太初六层）

```text
应用 / 框架
    │
    ├─ ROCm: HIP API 头 (projects/hip)
    │         CLR hipamd + rocclr
    │         ROCr HSA runtime
    │         libhsakmt (thunk)
    │         amdkfd + amdgpu (kernel)
    │         CP/MES/SDMA firmware  ← 仍多为 blob
    │
    └─ CANN: ACL (aclrt*)
              runtime core (rt* / Device/Stream/Task)
              ascend_hal (hal* / drvHdc*)
              sdk_driver (chrdev / trsdrv / hdc / svm)
              设备侧 TSD / AICPU schedule
              固件 / TS  ← 不在开源仓热路径里完整展开
```

与太初文档 §2.1 的近似映射：

| 太初概念 | ROCm 锚点 | CANN 锚点 |
|---|---|---|
| SDAADriver | amdgpu + amdkfd +（部分）libhsakmt | sdk_driver + ascend_hal |
| SDAARuntime | ROCr + CLR/HIP | runtime core + ACL |
| TCCL | RCCL（本目录未拉） | cann-hccl + RoCE Lite |
| TCML / SMI | amdsmi | DCMI / DSMI / DMS |
| 调试维测 | rocprofiler 系（systems 内另有） | runtime/dfx：msprof、adump、log |

---

## 2. ROCm：用户态 ring + doorbell

**控制面 / 数据面分离**很干净：

- 创建队列、映射内存、SVM、事件 → KFD ioctl（`libhsakmt` → `amdkfd`）
- 稳态 kernel dispatch → 用户态写 **AQL** 包到 ring，敲 **doorbell**，不再每包 ioctl

证据链（本地路径）：

1. `clr/hipamd`：`hipLaunchKernel` → `ihipLaunchKernelCommand` → `enqueue`
2. `clr/rocclr/device/rocm`：`VirtualGPU::submitKernel` → 填 `hsa_kernel_dispatch_packet_t` → `dispatchAqlPacket`
3. `rocr-runtime/.../amd_aql_queue.cpp` + `libhsakmt/.../queues.c`：队列生命周期
4. `ROCK-Kernel-Driver/.../amdkfd`：`AMDKFD_IOC_CREATE_QUEUE` 等

关键抽象：Agent、AQL Queue、Signal、Memory Pool / aperture（GPUVM、LDS、Scratch、SVM）。  
HIP 是 CUDA 形 API；真正可移植的设备模型在 **HSA**；OS 边界在 **thunk**。

开源边界：用户态几乎全开；**CP/MEC/MES/SDMA/PSP** 等调度与异常语义大量在 firmware。

---

## 3. CANN：Task → SQE → `halSqTaskSend`，另挂 HDC/TSD

同样有「用户态构造硬件包 + 驱动发送」的味道，但控制面更重：

- 计算热路径：ACL → `rt*` → Stream/Task → **SQE** → `halSqTaskSend`（SQCQ）
- 控制旁路：**HDC**（Host–Device 会话）拉起 **TSD**，再管设备侧 aicpu_schedule / 包加载
- 通信旁路：**RoCE Lite** 供 HCCL，与 Runtime SQ 路径并列

证据链：

1. `runtime/src/acl/.../kernel.cpp`：`aclrtLaunchKernel*` → `rtLaunchKernel*`
2. `runtime/src/runtime/core/src/stream/`、`task/`：`SubmitTask`、`task_to_sqe`
3. `runtime/.../task_submit/`：调用 `halSqTaskSend`
4. `driver/pkg_inc/ascend_hal*.h`、`hal_pkg/trs_pkg.h`：HAL / SQCQ 面
5. `runtime/src/tsd/`：`TsdOpen*`，经 HDC 与 tsdaemon 交互

Driver 仓显式切三块：**DCMI**（管理面）、**ascend_hal**（用户态 HAL）、**sdk_driver**（内核适配 / HDC / TRS / SVM）。  
Runtime 仓则是 **ACL 稳定面 + 多代引擎后端**（v100/v200/David/Stars）+ DFX。

相对 CUDA/HIP：SQE 布局更「硬件合同化」；TSD/AICPU 双轨超出「单一 Host Driver」模型——HostFunc / 自定义算子依赖设备侧 CPU 调度进程。

---

## 4. 对「另一家加速器系统软件」可直接拿走的设计题

结合太初方案里的六大机制，两边开源实现共同暗示：

1. **提交模型要先定合同**  
   ROCm 选 AQL；CANN 选 SQE。太初需等价物（与 PCX / 队列门铃语义对齐），不能只停留在「有个 Runtime API」。

2. **控制面与数据面拆开**  
   ioctl/HDC 做资源与守护进程；doorbell/SQ 发送做热路径。混在一起会把延迟和 ABI 稳定性一起搞砸。

3. **内存空间要显式**  
   VRAM / Host-mapped / SVM / Scratch（或 SPM）分 aperture 与粒度；异步 DMA/RMA 完成要用 event/signal，而不是「kernel 返回即可见」。

4. **集合通信不要塞进 Runtime 核心**  
   HCCL ↔ RoCE、RCCL ↔ 驱动 RDMA 原语：算法库与传输原语分层，和太初文档里 TCCL 独立一层一致。

5. **管理面旁路**  
   amdsmi / DCMI：监控、RAS、拓扑与 compute runtime 解耦，对应 TCML/TecoSMI。

6. **开源不等于固件语义开放**  
   验收时仍要问：队列背压、抢占、异常 recovery、虚拟化隔离，哪些在开源驱动可测，哪些锁在固件/闭源 TS。

---

## 5. 本目录仓库说明

| 仓库 | 备注 |
|---|---|
| `rocm/rocm-systems` | sparse：`rocr-runtime`、`clr`、`hip`、`amdsmi` |
| `rocm/ROCK-Kernel-Driver` | 整棵内核树约 2GB；研读重点 `drivers/gpu/drm/amd/{amdgpu,amdkfd}` |
| `cann/driver` | 2025-12 起公开；含 A5 等近期芯片路径 |
| `cann/runtime` | ACL + runtime + TSD + DFX |
| `cann/cann-hccl` | 集合通信 |

未拉但相关：RCCL、TheRock 构建系统、CANN 编译器/图编译仓（不在本轮 Driver/Runtime 范围）。

---

## 6. 建议的下一刀代码阅读

- 并读：`rocvirtual.cpp`（AQL 填充）vs `task_to_sqe.cc` + `halSqTaskSend`（SQE 下发）  
- 并读：`libhsakmt` queues/svm vs `ascend_hal` queue/svm + `sdk_driver` hdc  
- 并读：HIP stream/event vs `aclrt` stream/event，画一张「异步依赖」对照表  
- 若磁盘紧：把 `ROCK-Kernel-Driver` 收成仅 `drivers/gpu/drm/amd` 的 sparse 树
