# BookInfo 微服务实验 - Agent 提示词

你是一个自动化实验执行 Agent。你需要在 GitHub Codespaces（Linux 环境）中完成以下两个实验，并生成完整的实验文档（`实验记录.md`），**每一步都需要截图保存到 `screenshots/` 目录**。

## 前置准备

### 安装 playwright-mcp
用于在无头浏览器中截图：
```bash
npm install -g @anthropic-ai/claude-mcp-playwright
# 或者
npx playwright install chromium
```

### 安装基础工具
```bash
# Docker（Codespaces 通常已预装）
docker --version

# kind（创建本地 K8s 集群）
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# istioctl
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.24.3 sh -
export PATH=$PWD/istio-1.24.3/bin:$PATH
```

---

## 实验一：Docker + K8s 部署 BookInfo

详细要求参见 `要求1.md`。

### 步骤 1：创建 Kind 集群
使用仓库中的 `kind-config.yaml`（1 控制面 + 4 工作节点）：
```bash
kind create cluster --config kind-config.yaml --name bookinfo
```
**截图**：`kubectl get nodes` 输出

### 步骤 2：YAML 部署 BookInfo
```bash
kubectl create namespace bookinfo
kubectl label namespace bookinfo istio-injection=enabled
kubectl apply -f https://raw.githubusercontent.com/istio/istio/master/samples/bookinfo/platform/kube/bookinfo.yaml -n bookinfo
```
等待所有 Pod 变为 Running 状态。
**截图**：`kubectl get pods -n bookinfo -o wide` 输出

### 步骤 3：验证服务
```bash
kubectl port-forward svc/productpage 9080:9080 -n bookinfo &
```
用 playwright 截图 `http://localhost:9080/productpage` 页面。
**截图**：BookInfo 产品页面

### 步骤 4：源码部署 BookInfo
```bash
git clone https://github.com/istio/istio.git
cd istio/samples/bookinfo/src
```

对 4 个微服务（details, productpage, ratings, reviews）分别执行：
```bash
cd <service_dir>
docker build -t ghcr.io/kkeygen/<service>:v1 .
docker push ghcr.io/kkeygen/<service>:v1
```

注意 reviews 需要构建 v1, v2, v3 三个版本。

然后修改 `bookinfo.yaml` 中的 image 字段指向 `ghcr.io/kkeygen/` 前缀的镜像，部署到 `bookinfo-src` 命名空间：
```bash
kubectl create namespace bookinfo-src
kubectl apply -f bookinfo-custom.yaml -n bookinfo-src
```
**截图**：`kubectl get pods -n bookinfo-src` 输出

---

## 实验二：微服务运维

详细要求参见 `要求2.md`。

### 步骤 1：安装 Kuboard
```bash
kubectl apply -f https://addons.kuboard.cn/kuboard/kuboard-v3.yaml

# 为 control-plane 节点添加标签
CONTROL_PLANE=$(kubectl get nodes --selector=node-role.kubernetes.io/control-plane -o jsonpath='{.items[0].metadata.name}')
kubectl label node $CONTROL_PLANE k8s.kuboard.cn/role=etcd
kubectl label node $CONTROL_PLANE node-role.kubernetes.io/master=

# 等待 Kuboard 就绪
kubectl rollout status deployment/kuboard-v3 -n kuboard --timeout=300s

# 端口转发
kubectl port-forward -n kuboard svc/kuboard-v3 30080:80 &
```
**截图**：
- Kuboard 登录页面 `http://localhost:30080`（用户名 admin / 密码 Kuboard123）
- 集群概览页面
- bookinfo 命名空间下 details 微服务详情
- 节点信息页面
- 安装 metric-scraper 后的 CPU/内存监控页面
- 节点追踪日志

### 步骤 2：安装 Istio 并配置路由
```bash
istioctl install --set profile=demo -y

# 验证
kubectl get pods -n istio-system
kubectl api-resources | grep istio
```

应用路由规则（使用仓库中的 YAML）：
```bash
# 先应用 destination rules
kubectl apply -n bookinfo -f istio-1.24.3/samples/bookinfo/networking/destination-rule-all.yaml

# 应用 virtual services（reviews 20:40:40 权重）
kubectl apply -n bookinfo -f virtual-service-all.yaml

# 验证
kubectl get destinationrule,virtualservice -n bookinfo
```

重启 bookinfo 以注入 sidecar：
```bash
kubectl rollout restart deployment -n bookinfo
# 等待所有 Pod 显示 2/2 READY
kubectl get pods -n bookinfo
```

端口转发访问 `http://localhost:9080/productpage`，多次刷新验证三种评分显示（无评分 / 黑色星 / 彩色星）按权重出现。
**截图**：
- `istioctl install` 输出
- `kubectl get pods -n istio-system` 输出
- `kubectl get destinationrule,virtualservice -n bookinfo` 输出
- productpage 的三种不同评分显示各截一次

### 步骤 3：安装 Jaeger 并配置 Tracing
```bash
kubectl apply -f istio-1.24.3/samples/addons/jaeger.yaml

# 应用 tracing provider 配置
istioctl install -f tracing.yaml --skip-confirmation

# 启用 100% 采样率
kubectl apply -f enable_tracing.yaml

# 重启 bookinfo 以注入 envoy sidecar
kubectl rollout restart deployment -n bookinfo

# 验证 Pod 显示 2/2
kubectl get pods -n bookinfo
```

启动 Jaeger Dashboard：
```bash
kubectl port-forward -n istio-system svc/tracing 16686:80 &
# 或
istioctl dashboard jaeger &
```

手动刷新几次 productpage，然后在 Jaeger `http://localhost:16686` 查看 trace。
**截图**：
- Jaeger 首页
- productpage 的 trace 瀑布图

### 步骤 4：安装 Prometheus
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus-operator prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace

# 验证
kubectl get svc -n monitoring
kubectl get pods -n monitoring

# 端口转发
kubectl port-forward svc/prometheus-operator-kube-p-prometheus 9090:9090 -n monitoring &
```

运行 Python 监控脚本：
```bash
pip install requests
python scripts/prometheus_monitor.py
```
**截图**：
- `kubectl get pods -n monitoring` 输出
- Prometheus 首页 `http://localhost:9090`
- Python 脚本运行输出

### 步骤 5：安装 Chaos Mesh 并进行故障注入
```bash
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# 注意：kind 使用 containerd，必须加以下两个 --set
helm install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace chaos-mesh --create-namespace \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
  --version 2.7.0

# 验证
kubectl get pods -n chaos-mesh

# 端口转发 Dashboard
kubectl port-forward -n chaos-mesh svc/chaos-dashboard 2333:2333 &
```

配置 Chaos Mesh Token：
```bash
kubectl apply -f yaml/rbac.yaml
kubectl create token account-default-manager-auiln -n default
```
使用 token 登录 Chaos Dashboard `http://localhost:2333`。

#### 网络故障实验
```bash
kubectl apply -f yaml/network-partition.yaml
```
访问 productpage，reviews 区域应显示 "Sorry, product reviews are currently unavailable"。
在 Jaeger 查看异常 trace。
**截图**：
- productpage 显示 reviews 不可用
- Jaeger 中的异常 trace

#### CPU 压力实验
```bash
kubectl apply -f yaml/cpu-stress.yaml
```
在 Kuboard 中观察 productpage 所在节点的 CPU 飙升。
**截图**：
- Kuboard 中 CPU 飙升的截图
- `kubectl delete -f yaml/cpu-stress.yaml` 后 CPU 恢复正常的截图

---

## 文档要求

生成的 `实验记录.md` 应包含：
1. 每一步的命令和输出
2. 对应的截图引用（`![描述](screenshots/xxx.png)`）
3. 简要的步骤说明
4. 最终生成一份完整的、可作为实验报告提交的文档

## 截图约定

所有截图保存到 `screenshots/` 目录，命名格式：
- `01-cluster-nodes.png`
- `02-bookinfo-pods.png`
- `03-productpage.png`
- `04-bookinfo-src-pods.png`
- `05-kuboard-login.png`
- `06-kuboard-cluster-overview.png`
- `07-kuboard-details-service.png`
- `08-kuboard-node-info.png`
- `09-kuboard-metrics.png`
- `10-kuboard-logs.png`
- `11-istio-install.png`
- `12-istio-pods.png`
- `13-istio-routing-rules.png`
- `14-productpage-no-rating.png`
- `15-productpage-black-stars.png`
- `16-productpage-red-stars.png`
- `17-jaeger-home.png`
- `18-jaeger-trace.png`
- `19-prometheus-pods.png`
- `20-prometheus-home.png`
- `21-prometheus-script-output.png`
- `22-chaos-mesh-pods.png`
- `23-chaos-dashboard.png`
- `24-network-partition-error.png`
- `25-jaeger-error-trace.png`
- `26-cpu-stress-kuboard.png`
- `27-cpu-stress-recovered.png`

## 注意事项

- Codespaces 环境是 Linux (Ubuntu)，所有命令用 bash
- 如果镜像拉取慢，可以用镜像源 `docker.snakekiss.com` 作为 Docker Hub 加速
- 源码部署时镜像推送到 `ghcr.io/kkeygen/` 下
- 截图使用 playwright-mcp 在无头浏览器中完成
- 每个端口转发命令后加 `&` 放到后台运行
- 网络故障实验结束后记得清理：`kubectl delete -f yaml/network-partition.yaml`
