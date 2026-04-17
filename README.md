# BookInfo 微服务实验

本仓库包含两个实验的完整要求和配置文件，用于在 GitHub Codespaces 中自动化完成 BookInfo 微服务的部署与运维实验。

## 仓库结构

```
├── PROMPT.md              # AI Agent 提示词（核心）
├── 要求1.md               # 实验一：Docker + K8s 部署 BookInfo
├── 要求2.md               # 实验二：微服务运维（Kuboard/Istio/Jaeger/Prometheus/Chaos Mesh）
├── kind-config.yaml       # Kind 集群配置（1 控制面 + 4 工作节点）
├── virtual-service-all.yaml  # Istio 路由规则（reviews 20:40:40）
├── tracing.yaml           # Istio Jaeger tracing provider 配置
├── enable_tracing.yaml    # Istio 100% 采样率 Telemetry 配置
├── yaml/
│   ├── network-partition.yaml  # Chaos Mesh 网络隔离实验
│   ├── cpu-stress.yaml         # Chaos Mesh CPU 压力实验
│   └── rbac.yaml               # Chaos Mesh RBAC 配置
├── scripts/
│   └── prometheus_monitor.py   # Prometheus 监控脚本
├── screenshots/           # 截图输出目录
└── 实验记录.md            # 实验文档（由 Agent 生成）
```

## 使用方式

1. 在 GitHub Codespaces 中打开本仓库
2. 安装 playwright-cli 用于浏览器截图
3. 按照 PROMPT.md 中的指示执行实验
