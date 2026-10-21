# 太初 AI 加速器系统软件平台方案

> 文档定位：把岗位 JD 当作一份业务需求，反向设计一套可交付、可演进、可验收的 AI 加速器系统软件平台；最后再把方案映射到我的能力、证据和面试策略。  
> 版本：v0.1，2026-09-08。  
> 证据边界：SDAA 软件栈来自公开文档；T2 Ultra/HCU 的细节主要来自公开报道，只作为下一代架构假设，不代表太初内部实现。

---

## 0. 执行摘要

这份 JD 要解决的并不是“写一个驱动”或“适配一个框架”，而是下面这个平台级问题：

> 如何把一代持续演进的异构众核芯片，通过 Driver、Runtime、通信库、编程模型、编译器和开发工具，稳定地交付给大模型训练、推理与 HPC 用户，并同时做到高性能、高扩展、高可靠、易开发和跨代兼容？

这意味着岗位真正的产出有五个：

1. **稳定的软件—硬件契约**：Queue、Doorbell、Interrupt、MMU、DMA、RMA、同步、Reset 等接口有版本、有不变量、有错误语义。
2. **统一的执行与内存语义**：应用能理解 Stream/Event、异步执行、内存可见性、地址空间和数据搬运，而不必猜硬件行为。
3. **从单卡到大规模集群的性能闭环**：不仅看峰值 FLOPS/TOPS，还看端到端吞吐、P99 延迟、扩展效率、通信重叠和稳定运行时间。
4. **开发者可用的软件生态**：PyTorch、DeepSpeed、vLLM、算子库、SDAA C、调试和性能工具形成一致体验。
5. **跨芯片代际演进能力**：通过 PCX、Capability Discovery、稳定 ABI 和兼容策略，避免每一代硬件都重写上层软件。

方案采用“契约优先、机制分层、指标闭环、分阶段交付”的方法。最先冻结的不是代码，而是执行模型、内存模型、错误模型和兼容边界；最先建设的也不是漂亮的峰值 Benchmark，而是端到端可观测、可复现、可回归的最小系统闭环。

---

## 1. 把 JD 翻译成业务需求

### 1.1 需求方

平台至少服务六类内部和外部客户：

- **芯片架构团队**：需要软件在流片前给出接口约束、仿真负载、性能模型和可调试性要求。
- **Driver/Runtime 团队**：需要稳定的硬件接口、用户态 ABI、资源模型和故障恢复边界。
- **编译器与算子库团队**：需要明确 ISA/PCX 能力、存储层级、同步原语和 Kernel Launch 契约。
- **框架与模型团队**：需要稳定的 Device Backend、算子覆盖、Fallback、分布式训练和推理能力。
- **集群与运维团队**：需要设备发现、遥测、隔离、升级、故障定位和大规模作业恢复。
- **最终开发者**：需要低迁移成本、可预测性能、清晰错误信息和完善工具。

### 1.2 核心场景

平台不能用一个 Benchmark 代表全部负载，应覆盖：

- 大模型训练：大 GEMM、Collective、Checkpoint、长时间稳定运行；
- 大模型推理：Prefill/Decode、KV Cache、连续批处理、量化与多卡并行；
- HPC/AI4S：FP64、稀疏/不规则访存、MPI/通信、长任务；
- 多进程与多租户：资源共享、地址空间隔离、QoS、公平性；
- 自主计算与加速器模式：若下一代产品确实支持双模式，需要统一而非复制两套软件；
- 跨代部署：旧应用、旧模型和旧二进制在新硬件上的兼容与性能退化控制。

### 1.3 功能需求

根据 JD，可归纳为八组能力：

1. 设备发现、初始化、上下文和生命周期管理；
2. Queue/Stream、Command、Event、同步和任务调度；
3. 虚拟地址、内存分配、映射、一致性、DMA/RMA 和数据迁移；
4. Kernel 编程、编译、装载、Launch 和 Capability 查询；
5. 单机多卡、跨机集合通信和通信计算重叠；
6. 多进程隔离、资源配额、优先级、抢占与公平调度；
7. 错误检测、超时、Reset、故障隔离和恢复；
8. Profiling、Tracing、Debug、Telemetry 和自动化回归。

### 1.4 非功能需求

- **性能**：低提交开销、高内存有效带宽、高计算利用率、高通信重叠。
- **扩展性**：单卡机制不阻碍多卡，多卡协议不阻碍跨机扩展。
- **可靠性**：错误有归属、可隔离、可恢复，不能默认“异常就整卡重启”。
- **兼容性**：API、ABI、PCX、Driver/Firmware/Runtime 版本具有明确矩阵。
- **可维护性**：机制与策略分离，公共能力不在每个框架 Backend 中重复实现。
- **可观测性**：每一次性能下降和故障都能沿 Framework—Runtime—Driver—Hardware 关联。
- **开发者体验**：安装、迁移、报错、调试和性能分析不依赖内部专家。

### 1.5 非目标

本方案 v0.1 不试图：

- 根据公开资料猜测未披露的微架构实现；
- 用 CUDA API 一比一复制替代真正的 SDAA 语义设计；
- 在没有硬件规格、仿真器和内部基线时承诺绝对性能数字；
- 把所有框架、算子和芯片代际一次性纳入首个里程碑；
- 用峰值算力、单个算子或 Demo 跑通代替产品级验收。

---

## 2. 公开事实、合理推断与待确认项

### 2.1 公开可确认的软件栈

太初公开软件栈可抽象为：

```text
TecoPyTorch / TecoDeepSpeed / TecoInferenceEngine / Teco-vLLM
                              ↓
       TecoDNN / TecoBLAS / TecoRAND / TCCL
                              ↓
                 SDAA C / TecoCC / PCX
                              ↓
                        SDAARuntime
                              ↓
                         SDAADriver
                              ↓
                    太初异构并行计算硬件
```

与业界概念的近似映射是：

- SDAADriver 对应设备 Kernel Driver 层；
- SDAARuntime 对应 CUDA Runtime/HIP Runtime 所处的用户态运行时层；
- SDAA C 对应面向设备 Kernel 的异构编程入口；
- TecoDNN、TecoBLAS、TecoRAND 分别承担 DNN、线性代数和随机数加速库角色；
- TCCL 承担 NCCL/RCCL 类集合通信角色；
- TSight、TecoGDB 承担性能分析与异构调试角色；
- TCML、TecoSMI 承担设备管理库与系统管理工具角色；
- PCX 是与硬件架构解耦的虚拟指令集，PCXAC 将 PCX 转换到具体芯片机器指令。

这个映射只用于帮助理解层次，不代表 API、执行语义或硬件机制与 CUDA/ROCm 完全相同。

### 2.2 公开编程与硬件抽象

SDAA C 公开资料体现出几个关键特征：

- 使用 C/C++ 与少量异构扩展；
- 采用 SPMD 编程范式；
- 同时提供更易用的阻塞接口和面向极致性能的非阻塞接口；
- 硬件抽象包含 SPA、SPE、SPE 私有 SPM 以及 SPA 内共享 Global 空间；
- Global 与 SPM、不同 SPE 的 SPM 之间存在 DMA/RMA/Broadcast 等显式数据传输方式；
- 性能优化需要考虑 Tiling、SPM 容量、双缓冲、异步搬运和矩阵单元供数。

由此可以推导：Runtime 与编译器必须共同表达异步依赖、存储空间、数据布局和搬运完成语义，仅靠“发一个 Kernel”不足以释放硬件性能。

### 2.3 下一代平台假设

公开报道把 T2 Ultra 描述为基于 HCU 异构融合架构、支持自主计算与加速计算双模式，并强调 CPU 与 XPA 算力阵列协同、共享分级存储和大规模互联。

这些信息对系统软件提出了合理但仍需确认的假设：

- 芯片可能不再只是传统 Host—Device 从设备；
- 片上通用核可能承担启动、调度、通信、数据处理或用户态计算；
- 自主模式与加速模式可能需要统一进程模型、设备模型和部署模型；
- 共享或统一寻址不等于天然缓存一致，需要明确可见性、原子性和 Fence；
- 大规模互联要求通信、RAS、拓扑发现和遥测在架构早期进入设计。

面试中应把这些作为设计问题提出，而不能说成已知内部事实。

---

## 3. 目标平台架构

```mermaid
flowchart TB
  subgraph appLayer [应用与框架层]
    workloads["LLM训练 / LLM推理 / HPC / AI4S"]
    frameworks["PyTorch / DeepSpeed / vLLM / 推理引擎"]
  end

  subgraph accelerationLayer [加速与编译层]
    graph["Graph / Operator / Distributed Backend"]
    libraries["DNN / BLAS / RAND / Collective"]
    compiler["SDAA C / TecoCC / PCX / PCXAC"]
  end

  subgraph runtimeLayer [用户态系统层]
    runtime["Context / Stream / Event / Module / Memory"]
    scheduler["Submission / Scheduling / QoS / Capability"]
    tools["Profiler / Debugger / Device Management"]
  end

  subgraph kernelLayer [内核与固件层]
    driver["Device / VM / Queue / Interrupt / RAS"]
    transport["DMA / RMA / RDMA / Peer Transport"]
    firmware["Firmware / Boot / Health / Recovery"]
  end

  subgraph hardwareLayer [硬件层]
    hcu["Host或片上CPU / SPA / SPE / SPM"]
    fabric["Memory / PCIe / On-chip Fabric / Scale-up"]
  end

  workloads --> frameworks
  frameworks --> graph
  graph --> libraries
  graph --> compiler
  libraries --> runtime
  compiler --> runtime
  runtime --> scheduler
  scheduler --> driver
  driver --> transport
  driver --> firmware
  transport --> hcu
  firmware --> hcu
  hcu --> fabric
  tools -.-> frameworks
  tools -.-> runtime
  tools -.-> driver
```

### 3.1 三条纵向主链

**执行链**

```text
Framework Op/Graph
→ Library 或 Compiled Kernel
→ Runtime Stream/Command
→ Driver Queue/Command Buffer
→ Doorbell
→ Device Scheduler
→ SPE/Matrix/Vector 执行
→ Completion/Event
```

**内存链**

```text
Process VA
→ Runtime Allocation
→ Driver VM/IOMMU Mapping
→ Device Global Memory
→ DMA 到 SPM
→ Compute
→ RMA/Broadcast 或 DMA 回写
→ Fence 后对下一消费者可见
```

**通信链**

```text
Framework Collective
→ TCCL Planner
→ Topology/Algorithm Selection
→ P2P 或 RDMA Transport
→ Device DMA/Network Engine
→ Completion/Error Propagation
```

### 3.2 四个横切面

- **Compatibility**：API、ABI、PCX、Capability、版本协商和跨代策略；
- **Reliability**：ECC、Hang、Timeout、Reset、隔离、恢复和升级；
- **Observability**：统一时间线、Correlation ID、硬件计数器和日志；
- **Security/Isolation**：地址空间、权限、内存清零、Firmware 信任与多租户。

---

## 4. 架构原则

### 4.1 契约优先

Driver/Runtime 的核心不是函数数量，而是每个操作的前置条件、完成条件、可见性和错误语义。硬件接口冻结前，应先有：

- Queue 与 Command Buffer 格式；
- Doorbell、Completion Queue 与 Interrupt 语义；
- 地址空间、Page Fault、Pinned Memory 和 Peer Mapping 语义；
- DMA/RMA 的顺序性、原子性和 Fence；
- Timeout、Cancel、Reset 和错误归属；
- Capability、Feature Bit 与版本协商。

### 4.2 机制与策略分离

- Driver 提供安全、稳定的机制；
- Runtime 管理用户态策略和低开销 Fast Path；
- 通信库选择拓扑与算法；
- 框架 Backend 负责图和模型语义；
- 不把调度策略硬编码进 Kernel ABI，也不把硬件细节泄漏到每个框架。

### 4.3 异步优先、同步显式

所有耗时操作默认可以异步，依赖通过 Stream、Event、Fence 或 Future 表达。隐式全局同步只能作为兼容路径，不能成为默认性能路径。

### 4.4 可观测性是架构接口

Command 从框架产生时就分配 Correlation ID，沿 Runtime、Driver、Firmware 到硬件时间戳贯通。没有这条链，性能团队只能在各层分别猜测。

### 4.5 性能优化不能破坏可恢复性

用户态提交、批量 Doorbell、Zero-copy 和通信计算重叠可以降低开销，但必须保留资源记账、超时检测、错误隔离和确定的恢复边界。

---

## 5. 六条核心机制

### 5.1 执行、Queue 与调度

### 目标

在低提交开销下支持多 Stream、多进程、优先级和公平调度，同时让依赖和完成状态可追踪。

### 建议模型

- 一个进程可创建一个或多个 Context；
- Context 拥有独立地址空间、资源配额和错误域；
- Stream 是有序提交域，不同 Stream 默认可并行；
- Command Buffer 描述 Kernel、Memcpy、Barrier 和 Collective；
- Event 表示可跨 Stream 依赖的完成点；
- Queue Pair 包含 Submission Queue 与 Completion Queue；
- Doorbell 只通知新增工作，不承载复杂策略；
- Runtime 负责聚合小命令、减少系统调用和 Doorbell；
- Driver 负责验证、映射、资源隔离和调度机制；
- Firmware/Device Scheduler 负责硬件可见队列和执行分发。

### 关键不变量

1. 同一 Stream 内按定义顺序观察；
2. Event 完成前，其生产者写入不能被消费者当作已可见；
3. Context A 不能读写 Context B 的地址或 Queue；
4. Command 错误必须能关联到 Context、Queue、Command 和设备时间；
5. 调度器不能因单一低优先级长任务无限阻塞控制任务。

### 需要软硬件共同定义

- 是否支持 Preemption，粒度是 Command、Kernel、Workgroup 还是指令；
- 是否有多级硬件 Queue；
- Queue 状态是否由设备内存、Host 内存或片上 SRAM 保存；
- Doorbell 是否需要 MMIO Ordering；
- Hang Detection 由 Firmware、Driver 还是 Runtime 主导；
- 自主模式与加速器模式是否复用同一执行模型。

### 验证

- 空 Kernel Launch 与批量 Launch 延迟；
- 多 Stream 并发与依赖正确性；
- 多进程公平性、优先级反转和饥饿测试；
- 长 Kernel、坏 Command、Queue Overflow 与 Cancel；
- Fork/Exec/Process Exit 下资源回收；
- 设备 Reset 前后句柄和错误语义。

### 5.2 内存、一致性与数据搬运

### 目标

给开发者一个清晰、可优化、可验证的内存模型，既支持易用路径，也支持 SPM/DMA 显式优化。

### 建议分层

- **Host Pageable Memory**：易用但需要 Staging；
- **Host Pinned Memory**：用于高吞吐异步 H2D/D2H；
- **Device Global Memory**：Runtime 分配、Driver 建立设备映射；
- **Peer Memory**：多卡 P2P 或通信库直接访问；
- **Shared/Unified Address**：如果硬件支持，只统一地址表达，不模糊一致性；
- **SPE Private SPM**：编译器或 Kernel 显式管理的高带宽本地存储；
- **SPA Shared Global**：SPE 共享、容量更大但延迟和带宽特征不同。

### 必须写入规范的语义

- 分配、映射、Pin、Unmap 和 Free 的生命周期；
- CPU、设备、DMA、RMA 对同一地址的可见性；
- Cache Flush/Invalidate 的责任主体；
- Acquire/Release、Fence、Event Completion 的关系；
- 原子操作的作用域：SPE、SPA、Device、System；
- Page Fault、Oversubscription 和 Migration 是否存在；
- Unified Address、Unified Virtual Address 和 Cache Coherence 的区别。

### DMA/RMA Pipeline

高性能 Kernel 应表达：

```text
DMA tile N+1 到 SPM buffer B
与
计算 tile N 在 SPM buffer A
并行
→ Event/Fence
→ 交换 A/B
```

编译器负责 Tiling、Lifetime 与静态依赖，Runtime/Driver 负责传输资源、地址合法性和完成语义，硬件负责并行传输和计数器。

### 高风险问题

- DMA 写完后矩阵单元何时能看到；
- RMA 对端完成是 Local Completion 还是 Remote Visibility；
- 多个 SPE 对共享 Global 的写冲突如何定义；
- Page Fault 能否发生在 Kernel 执行中；
- Reset 后已分配内存和 Peer Mapping 如何失效；
- Pinned Memory 是否可能耗尽系统内存。

### 验证

- Litmus Test 覆盖 Producer/Consumer、DMA/Compute、RMA/Fence；
- 不同大小、对齐、NUMA 与并发下的有效带宽；
- SPM 双缓冲与单缓冲对比；
- 越界、Use-after-free、非法 Peer Access；
- 压力下 Pin/Unpin、映射回收和内存泄漏；
- ECC、Page Fault 和 Migration 故障注入。

### 5.3 通信与多卡

### 目标

让 TCCL 从“能跑 Collective”演进到“能按拓扑稳定扩展、能与计算重叠、能定位故障”。

### 架构拆分

- **Bootstrap**：Rank、Endpoint、Security Credential；
- **Topology Discovery**：PCIe、NUMA、Switch、NIC、片间互联；
- **Planner**：按消息大小、拓扑和负载选择 Ring、Tree、Hierarchical 等算法；
- **Transport**：P2P、Shared Memory、RDMA/RoCE、自研 Scale-up；
- **Progress Engine**：Host Polling、Interrupt 或 Device-side Progress；
- **Execution**：Collective Kernel、DMA/Network Engine；
- **Reliability**：Timeout、Async Error、Link Degrade、Rank Failure；
- **Telemetry**：每个 Channel、Link、Phase 的吞吐和等待时间。

### 关键设计点

- 小消息看启动延迟，大消息看链路利用率；
- 通信 Stream 与计算 Stream 通过 Event 建立最小依赖；
- 拓扑发现必须考虑 NUMA 和 NIC Affinity；
- 集合通信错误不能只返回“操作失败”，需要定位 Rank、Link、阶段；
- 在大规模场景下，控制面风暴和超时误判与数据面同样重要；
- 自主模式如果允许片上 CPU 参与 Progress，需要明确 Host 与 Device 的责任切换。

### 验证

- AllReduce/AllGather/ReduceScatter 的延迟—带宽曲线；
- 2、8、目标规模卡的扩展效率；
- 通信与计算重叠比例；
- 不同拓扑和跨 NUMA 的算法选择；
- Link 降速、丢包、Rank 退出、设备 Reset；
- 连续长稳训练的 Async Error 与恢复。

### 5.4 多进程、资源管理与隔离

### 目标

把一张卡从“单用户独占设备”变成可安全共享、可计量、可调度的平台资源。

### 资源对象

- Context 与地址空间；
- Queue、Stream、Event；
- Device Memory、Pinned Memory、SPM 配额；
- Compute Partition、DMA Channel、Communication Channel；
- Performance Counter 与 Debug 权限；
- Power/Thermal Budget；
- Firmware 和设备全局操作权限。

### 建议机制

- 每 Context 独立 VMID/PASID 或等价隔离标识；
- IOMMU/SMMU 与设备 MMU 形成统一映射生命周期；
- cgroup/设备控制器或平台资源管理器下发配额；
- 调度策略支持权重、公平、优先级和 Admission Control；
- 设备内存回收前清零，避免跨租户数据泄漏；
- Debug、Counter、Reset 分级授权；
- 对不支持细粒度抢占的硬件提供任务切分和 Admission 约束。

### 验证

- 恶意越界、无效 Command、Doorbell Flood；
- 多租户内存带宽和计算干扰；
- 进程 Crash、Kill -9、容器退出；
- 配额耗尽与资源泄漏；
- 单 Context 故障是否升级为整卡 Reset；
- Reset 后其他租户能否恢复或收到确定错误。

### 5.5 可靠性、RAS 与生命周期

### 错误分级

- **Command 级**：参数错误、非法地址、算子失败；
- **Context 级**：页表损坏、Queue Hang、超时；
- **Engine 级**：单个 DMA/Compute Engine 异常；
- **Device 级**：Firmware Crash、不可纠正 ECC、全局互联异常；
- **Node/Cluster 级**：PCIe Link、NIC、Switch、供电或散热故障。

### 恢复原则

1. 优先最小故障域恢复；
2. 错误必须先 Freeze 和采集现场，再执行 Reset；
3. Reset 有分级：Queue、Context、Engine、Function、Device；
4. 每一级 Reset 都定义影响对象和句柄失效规则；
5. Driver、Runtime、框架与通信库使用统一错误分类；
6. Firmware/Driver/Runtime 升级有兼容矩阵和回滚路径。

### 最小 RAS 产物

- Error Taxonomy 与错误码；
- Health State Machine；
- Watchdog 与 Timeout 预算；
- Crash Dump/Minidump 格式；
- Reset Playbook；
- 故障注入接口；
- 长稳与升级回归套件。

### 5.6 可观测性、调试与性能分析

### 统一时间线

需要关联：

```text
Framework Op
→ Graph/Kernel
→ Runtime API
→ Stream Command
→ Driver Submit
→ Queue Wait
→ DMA/RMA
→ Device Execute
→ Collective
→ Completion
```

每层至少输出：

- Correlation ID；
- Host/Device Timestamp 与时钟校准信息；
- Queue、Context、Process、Device、Rank；
- Kernel/Command 名称和 Shape；
- 等待、搬运、计算、同步时间；
- Error、Retry、Reset 和 Throttle；
- 关键硬件计数器。

### 性能分析方法

从端到端 SLA 逐层下钻，而不是先猜算子：

1. 判断瓶颈在 CPU 提交、Queue、DMA、Compute、Memory 还是 Communication；
2. 用 Roofline 判断算力还是带宽受限；
3. 用 Timeline 判断空洞、串行化和错误同步；
4. 用 Counter 判断占用率、访存效率、SPM 冲突和互联利用率；
5. 用 A/B Benchmark 验证优化收益；
6. 将 Case 固化为 CI Regression。

---

## 6. 编程模型、编译与跨代兼容

### 6.1 SDAA C 的两级体验

建议保留两条路径：

- **Portable Path**：阻塞或高层接口，隐藏 SPM、DMA 和复杂同步，优先正确性和迁移；
- **Performance Path**：非阻塞、显式存储空间、异步 DMA/RMA、Event 和 Tiling，供算子库与性能专家使用。

两者必须共享同一个错误模型、对象生命周期和工具链，避免形成两套不可互查的问题空间。

### 6.2 PCX 的平台角色

PCX 不应只被理解为编译器 IR；它可以成为跨代软件契约的一部分：

```text
Source / Graph
→ Stable PCX Contract
→ PCXAC Target Lowering
→ Device Machine Code
```

要真正承担跨代兼容，需要明确：

- PCX 版本、Feature 与 Deprecation Policy；
- 精度、原子、内存空间和同步语义；
- 未支持能力的合法降级与报错；
- 编译时 Target 与运行时 Capability 的协商；
- AOT、JIT、Cache Key 和签名校验；
- 二进制可移植范围及性能可移植边界；
- PCXAC、Runtime、Driver、Firmware 的兼容矩阵。

### 6.3 Capability Discovery

Runtime 应提供结构化能力，而不是让应用按芯片名写分支：

- 指令/PCX Feature；
- 数据类型与累加精度；
- SPM 容量、对齐和 DMA 能力；
- Queue、Stream、Priority、Preemption；
- P2P、RDMA、Atomic Scope；
- Unified Address/Coherence 能力；
- RAS、Counter、Debug 能力；
- 安全与虚拟化能力。

编译器、算子库、TCCL 和框架都使用同一份 Capability Source of Truth。

---

## 7. 软件—硬件协同设计流程

### 7.1 流片前

- 用真实模型和 Kernel Trace 提炼 Top Workload；
- 建立 Compute、Memory、DMA、Interconnect 性能模型；
- 用 Emulator/Simulator 跑 Driver/Runtime 最小闭环；
- 用 Litmus Test 验证内存模型；
- 评审 Queue、Doorbell、Interrupt、MMU、RAS 和 Counter；
- 明确所有“软件可绕过”的性能成本和长期债务；
- 形成 Hardware/Software Contract v1。

### 7.2 Bring-up

按下面顺序降低排障维度：

1. 设备枚举、BAR、Firmware Boot；
2. 内存分配与最小 DMA；
3. 单 Queue、单 Command、Polling Completion；
4. Interrupt 与 Event；
5. 单 Kernel；
6. 多 Stream 与多 Context；
7. Peer/Collective；
8. Framework 与端到端模型；
9. RAS、Reset、压力和长稳。

### 7.3 上线后

- 性能回归进入每次 Driver/Runtime/Firmware 变更；
- API/ABI/PCX 兼容测试进入 Release Gate；
- 线上遥测反馈到 Hardware Errata 和下一代接口；
- 典型客户问题沉淀成自动化故障注入；
- 发布版本同时提供 Compatibility Matrix、Known Issues 和 Rollback。

---

## 8. 验收体系

具体阈值需要根据芯片、目标负载和当前基线共同冻结。下面定义的是指标体系和建议 Gate，不冒充内部承诺。

### 8.1 正确性

- API Conformance 全通过；
- 内存一致性 Litmus Test 全通过；
- 算子精度满足各数据类型误差规范；
- 多进程隔离测试无越权访问；
- Reset/Process Exit 后无资源泄漏；
- Driver/Runtime/Firmware 兼容矩阵全覆盖。

### 8.2 性能

- 空 Launch、Memcpy、Event、Collective 的延迟—带宽曲线；
- Device Memory、Pinned Memory、P2P、DMA/RMA 有效带宽；
- 代表性 Kernel 的算力、带宽与 SPM 利用率；
- Framework 端到端吞吐、P50/P99 延迟、TTFT/TPOT；
- 目标卡数的扩展效率与通信计算重叠；
- 热稳态而非短时峰值下的性能。

建议以“相对 Roofline、相对硬件理论、相对上一版本、相对竞品基线”四种视角同时验收，避免单一百分比失真。

### 8.3 可靠性

- 24/72 小时及更长长稳；
- 可纠正与不可纠正 ECC 注入；
- Queue/Context/Engine/Device 分级 Reset；
- Link Flap、Rank Failure 和通信 Timeout；
- Firmware Crash 与升级回滚；
- 平均恢复时间、整卡 Reset 率、故障定位成功率。

### 8.4 开发者体验

- 从安装到第一个 Kernel/模型的时间；
- CUDA/主流框架迁移所需代码修改量；
- 报错是否能定位到对象和根因；
- Profiling 是否能解释主要时间占比；
- 文档、示例、版本矩阵和 Known Issues 完整度；
- Unsupported Op/Feature 是否有明确 Fallback 或失败策略。

---

## 9. 分阶段路线图

### Phase 0：需求与基线，0—30 天

### 产物

- Workload 与 SLA 清单；
- 现有 SDAA Driver/Runtime/TCCL/PCX 架构图；
- API/ABI/Hardware Interface 盘点；
- Top 20 性能与可靠性问题；
- Benchmark、Trace 与故障数据基线；
- T100/现有产品到 T2/HCU 假设的差异清单。

### 退出条件

- 团队对目标客户、目标负载和优先级达成一致；
- 每个指标有 Owner、数据源、基线和复现方法；
- 事实、推断和未决架构问题分离。

### Phase 1：架构冻结，31—90 天

### 产物

- Execution Model、Memory Model、Error Model；
- Queue/Command/Doorbell/Completion 契约；
- Context/VM/Resource Model；
- Capability 与版本协商规范；
- Observability Schema；
- 最小 Emulator/Simulator 验证环境；
- Architecture Decision Record 与风险登记册。

### 退出条件

- Driver、Runtime、Compiler、Communication、Hardware 联合评审通过；
- 关键 Litmus Test、异常流和兼容场景有可执行用例；
- 高风险能力在仿真或原型上完成验证。

### Phase 2：最小产品闭环，3—6 个月

### 产物

- 单卡 Device—Driver—Runtime—Kernel 闭环；
- 多 Stream、多 Context、基础 RAS；
- DMA/SPM 双缓冲性能路径；
- PyTorch 或核心推理引擎最小 Backend；
- TSight 统一时间线 MVP；
- Release/Compatibility/Regression Pipeline。

### 退出条件

- 代表性模型正确运行并可解释主要性能时间；
- 单 Context 故障不默认升级为整卡不可恢复；
- 性能、正确性和兼容测试可持续回归。

### Phase 3：规模化，6—12 个月

### 产物

- TCCL 多卡与跨机路径；
- Topology-aware Planner；
- 多租户、配额、QoS 和安全隔离；
- 长稳、故障注入和分级恢复；
- PCX 跨代编译与 Runtime Capability 闭环；
- 训练、推理、HPC 三类 Golden Workload。

### 退出条件

- 在目标规模上达到冻结的扩展效率；
- 通信、计算和数据搬运瓶颈可量化；
- 故障可定位、可隔离、可按策略恢复；
- 旧软件资产在新平台上的兼容行为可预测。

### Phase 4：生态化，12 个月以后

- 扩大算子、框架、模型和行业负载覆盖；
- 建立公开文档、样例、迁移工具和开发者社区反馈闭环；
- 基于线上遥测推动下一代硬件接口；
- 将性能专家经验固化到编译器、算子库和自动调优；
- 逐步减少芯片型号分支和客户定制 Patch。

---

## 10. 关键风险与决策

### 风险 1：把“兼容 CUDA”当成全部产品定义

兼容可以降低迁移成本，但如果底层存储、并行和同步模型不同，机械复制 API 会掩盖硬件优势并产生长期债务。

**对策**：区分 Source Compatibility、API Compatibility、Behavior Compatibility 和 Performance Portability。

### 风险 2：统一寻址被误解为一致性

地址相同只解决“如何指向”，不自动解决“何时可见”和“谁刷新 Cache”。

**对策**：单独发布 Memory Consistency Spec 与 Litmus Test。

### 风险 3：性能问题被层层甩锅

框架、Runtime、Driver、Firmware 和硬件使用不同时间线，最终只能靠专家人工对齐。

**对策**：Correlation ID、统一时间戳和 Counter Schema 作为架构 Gate。

### 风险 4：跨代兼容吞噬性能

虚拟 ISA 可以保持稳定，但旧语义可能无法表达新硬件，或错误地强迫新硬件模拟旧行为。

**对策**：PCX Feature Level、Capability、合法降级、Recompile Policy 与 Deprecation Window。

### 风险 5：单卡成功掩盖规模化问题

多卡放大拓扑、超时、控制面、NUMA、链路和故障概率。

**对策**：从 Phase 0 就加入通信 Trace、故障模型和规模化性能模型。

### 风险 6：架构岗位与实现岗位责任不清

如果只有方案没有代码闭环，架构会失真；如果只救火没有接口权，平台会持续碎片化。

**对策**：岗位应同时拥有核心契约决策权、关键原型实现责任和跨团队 Release Gate。

---

## 11. JD 与我的能力映射

### 11.1 强匹配

### Linux 与系统软件平台

我长期处理 Linux、发行版、多架构处理器、内核与用户态组件的系统集成，能够从生命周期、兼容、升级和故障边界看问题。这直接对应：

- Driver/Runtime 与 OS 的接口治理；
- 进程、内存、I/O 和资源管理；
- 多组件版本与发布质量；
- 系统级性能和故障闭环。

### 国产 CPU/GPU/NPU 生态交付

我做过多家国产加速器 Driver、SDK、框架和发行版的适配与交付闭环。直接价值是：

- 能识别“厂商 Demo 能跑”和“平台可维护交付”的差别；
- 能组织 Driver、Runtime、框架、工具链与应用共同定位；
- 熟悉兼容矩阵、发布标准和客户验收；
- 理解跨芯片平台碎片化的真实成本。

### PCIe、RDMA 与系统性能

这部分可以映射到：

- Host—Device 数据路径；
- NUMA、Pinned Memory 与 DMA；
- 多卡、RDMA 和集合通信；
- 性能测量、瓶颈归因和回归体系。

### 工具链与 AI 推理实践

LLVM/GCC、vLLM/SGLang、FlagOS M5 实验提供了从框架、算子、编译器到指令和性能的连接能力。它不是太初 Runtime 的直接开发经历，但说明我能跨层追踪问题。

### 11.2 中等匹配

- Accelerator Runtime 的对象模型、Queue、Stream、Event 和异步执行；
- 多卡集合通信的系统设计；
- 异构众核编程模型、SPM/DMA 和显式数据搬运；
- RISC-V 系统软件、虚拟化和矩阵/向量扩展；
- 编译器虚拟 ISA 与跨代兼容。

这些方向我具备系统背景和可迁移知识，但需要用设计题、原型和阅读源码证明深度，不能只靠名词。

### 11.3 明确证据缺口

目前不能把下面事项描述成既有事实：

- 我亲自长期开发过某款 GPU/NPU Kernel Driver 核心；
- 我独立设计并实现过完整 Accelerator Runtime；
- 我实现过 NCCL/TCCL 核心算法或 Device Kernel；
- 我与芯片团队冻结过真实产品的 Queue/Doorbell/MMU/Cache Coherence 接口；
- 我有 Linux Kernel、QEMU 或 KVM 上游核心 Maintainer 级贡献；
- 我实现过太初 SDAA、PCX 或 T2 Ultra 内部组件。

正确表达方式是：

> 我做过这些组件的系统集成、兼容治理、性能与故障闭环；对核心机制能够给出架构设计和验证方法。直接代码 Owner 的部分需要如实区分，我会通过关键原型和深入实现快速补齐。

### 11.4 岗位匹配判断

- 如果岗位核心是跨 Driver/Runtime/通信/框架的系统平台架构与技术 Owner，匹配度约 **70%—80%**；
- 如果要求入职即独立承担 Kernel Driver、Runtime 和 TCCL 核心代码，匹配度约 **45%—55%**；
- 最值得确认的不是职级，而是架构决策权、直接编码比例、负责模块和下一代芯片阶段。

---

## 12. 面试陈述

### 12.1 三分钟主陈述

> 我把这份岗位理解成一个平台问题，而不是单点驱动问题：要把异构众核硬件通过 Driver、Runtime、通信库、编程模型和工具稳定交付给训练、推理和 HPC。
>
> 我会先冻结四个跨团队契约：执行模型、内存模型、错误模型和兼容模型。执行上定义 Context、Queue、Stream、Event、Doorbell 和 Completion；内存上定义地址空间、DMA/RMA、SPM、Fence 和可见性；可靠性上定义从 Command 到 Device 的分级故障域；兼容上用 PCX、Capability Discovery 和版本矩阵隔离芯片代际变化。
>
> 交付不会从“大而全”开始。第一个 30 天先用真实负载建立基线和问题清单，90 天内完成软硬件契约及仿真验证，随后做单卡最小闭环，再扩展多卡、TCCL、多租户和长稳。每个阶段都以正确性、P99 延迟、有效带宽、扩展效率、恢复时间和开发者上手成本验收。
>
> 我的优势是 Linux、多架构、国产加速器 Driver/SDK 交付、PCIe/RDMA 和系统问题闭环，能够把芯片、OS、Runtime、框架和客户验收连起来。我的边界是没有把自己包装成某款 Accelerator Runtime 或 TCCL 的原作者；但我能把接口、不变量、失败模式和验证体系讲清楚，并愿意承担关键原型实现。

### 12.2 两张必须会画的图

第一张：软件栈调用图。

```text
PyTorch/vLLM
→ TecoDNN/TecoBLAS/TCCL 或 Compiled Kernel
→ SDAARuntime
→ SDAADriver
→ Queue/DMA/SPE/SPM/Interconnect
```

第二张：异步执行与内存可见性图。

```text
Stream A: DMA Tile → Event E → Compute → Event F
                         ↓
Stream B:           Wait E → RMA/Collective → Wait F
```

画图时必须解释 Event 不只是时间点，还承载依赖与内存可见性。

### 12.3 三类案例模板

每个案例都按“业务影响—证据—定位—根因—修复—回归”讲：

1. **Driver/SDK 兼容问题**：版本、符号、ABI、Kernel、Firmware 或框架边界；
2. **PCIe/RDMA 性能问题**：NUMA、Pinned Memory、链路、队列、包大小、并发；
3. **AI 推理问题**：模型加载、量化、算子、编译、Runtime 和端到端吞吐。

只讲自己真实做过的决策和动作，不把团队结果全部归于个人。

---

## 13. 高概率追问与回答骨架

### 如何设计 Accelerator Driver + Runtime？

从对象和生命周期开始：Device、Context、VM、Queue、Command、Event、Memory、Module。再讲 Fast Path、控制路径、错误路径，最后讲多进程、Reset 和可观测性。不要直接背 CUDA API。

### Stream 与 Event 如何保证正确性？

Stream 定义有序提交域，Event 定义跨域依赖。必须明确 Event Complete 是否意味着设备执行完成、DMA 完成和内存对指定作用域可见。

### 统一内存如何设计？

先区分统一地址、统一虚拟地址、自动迁移和缓存一致性。再说明 Page Fault、Pin、Migration、Fence、Atomic Scope 和 Oversubscription 的选择。

### 多进程如何隔离？

Context 独立地址空间，IOMMU/设备 MMU 校验，Queue 与资源按租户记账，内存回收清零，Reset 尽量限制在最小故障域。

### TCCL 如何优化？

先看拓扑和消息大小，再选择算法；区分小消息启动延迟和大消息带宽；通过独立 Stream、Event 和分块实现通信计算重叠；用每个 Rank/Link/Channel 的遥测定位长尾。

### 如何做跨代兼容？

稳定 API/ABI/PCX，运行时查询 Capability，编译器按 Feature Lowering；定义 Recompile、Fallback、Deprecation 和版本协商，不能把芯片型号判断散落到上层。

### 如何证明系统变快了？

从端到端 SLA 出发，用 Timeline 找空洞，用 Roofline 判断 Compute/Memory，用 Counter 验证微观根因，用 A/B 和长稳回归证明收益没有牺牲正确性与可靠性。

---

## 14. 面试反问

这些问题同时用于判断岗位边界和校验本方案假设：

1. 岗位主要负责现有 SDAA/T100 演进，还是下一代 T2 Ultra/HCU？
2. “主导平台设计与开发”中，架构决策、关键代码和跨团队协调各占多少？
3. Driver、Runtime、TCCL、编译器和工具分别由哪些团队负责，接口由谁最终裁决？
4. 当前最大的业务痛点是单卡性能、多卡扩展、可靠性、开发者体验还是跨代兼容？
5. 自主计算与加速器模式是否复用同一套 Runtime、进程模型和内存语义？
6. 片上通用核承担 Boot/Firmware、调度、通信 Progress，还是开放给用户程序？
7. 公开资料中的 PCX 在新一代平台上承担 AOT、JIT、兼容层还是全部角色？
8. 内存模型是显式 DMA/SPM 为主，还是会加入共享虚拟内存、Page Fault 或缓存一致能力？
9. TCCL 的目标规模、主要互联和当前最难的长尾/故障问题是什么？
10. 新芯片流片前，系统软件团队能否影响 Queue、MMU、DMA、RAS 和 Counter 设计？
11. 岗位入职 3 个月和 12 个月的成功标准分别是什么？
12. 团队如何评价架构工作的价值：文档、核心原型、性能指标、Release 质量还是客户交付？

---

## 15. 入职后的第一组行动

如果由我承担这个岗位，我不会先重写组件，而会先做四件事：

1. **画清现状**：一张调用图、一张内存图、一张故障传播图、一张版本矩阵；
2. **建立基线**：选训练、推理、HPC 各一个 Golden Workload，拿到性能与稳定性数据；
3. **找最贵边界**：定位当前最影响客户的三个跨层问题，而非只看单团队 Backlog；
4. **冻结共同语言**：Execution、Memory、Error、Capability 四份规范先形成 v0.1。

第一个可见成果应该是：

> 任意一个 Golden Workload，都能从框架时间线追到 Runtime、Driver、DMA/Compute/Communication，并能解释主要性能损失与故障归属。

这会成为后续架构重构、硬件协同和团队协作的共同事实基础。

---

## 16. 最终判断

这份 JD 本质上在寻找“系统软件平台技术 Owner”，而不是单一模块专家。解决它的关键不在于掌握多少组件名，而在于能否：

- 把业务负载翻译成软硬件契约；
- 把 Driver、Runtime、Compiler、Communication 和 Framework 组织成一个系统；
- 同时处理 Fast Path、错误路径、升级路径和跨代兼容；
- 用可观测和验收体系把架构判断变成事实；
- 既能做跨团队设计，也能亲自完成关键原型。

对我而言，这个岗位的价值在于它比纯端侧算子适配更贴近既有 OS、多芯片平台和系统交付经验；风险在于底层 Accelerator Driver/Runtime/TCCL 的直接实现证据不足。面试策略不是掩盖缺口，而是用这份方案证明：我知道完整问题是什么、关键不变量在哪里、应该如何分阶段交付，也清楚哪些部分需要进一步深入代码。

---

## 参考资料

### 太初公开资料

- 太初软件栈概览 v2.0.0：<https://docs.tecorigin.com/release/teco_software_overview/v2.0.0/>
- SDAA C 编程文档 v3.0.0：<https://docs.tecorigin.com/release/sdaac/v3.0.0/>
- 太初软件安装与组件入口：<https://docs.tecorigin.com/release/software_installation/>
- SDAA C 与异构并行计算平台介绍：<https://www.tecorigin.com/cn/newsdetails/110/116.html>
- PCX 与 PCXAC 发布说明：<https://www.tecorigin.com/newsdetails/113/201.html>
- 太初技术与产品页面：<https://www.tecorigin.com/cn/technology.html>

### 下一代平台公开报道

- T2 Ultra/HCU 与双模式公开报道：<https://cinic.org.cn/zgzz/xw/1645860.html>
- T2 Ultra 与 HyperIntelliX 报道：<http://www.semi-insights.com/s/bdt/15/50558.shtml>

### 用于架构对照的公开规范

- CUDA Programming Guide：<https://docs.nvidia.com/cuda/cuda-c-programming-guide/>
- CUDA Driver API：<https://docs.nvidia.com/cuda/cuda-driver-api/>
- ROCm/HIP Documentation：<https://rocm.docs.amd.com/>
- Linux IOMMU Userspace API：<https://docs.kernel.org/userspace-api/iommu.html>
- Linux HMM：<https://docs.kernel.org/mm/hmm.html>
- RDMA Core Documentation：<https://docs.kernel.org/infiniband/>
