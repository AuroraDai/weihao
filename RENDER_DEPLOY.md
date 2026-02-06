# Render 部署 FastAPI 后端指南

## 前置要求

1. 注册 Render 账户：https://render.com
2. 连接 GitHub 账户（推荐）或使用 Git 部署
3. 确保后端代码已推送到 GitHub

## 部署步骤

### 1. 创建新的 Web Service

1. 登录 Render Dashboard：https://dashboard.render.com
2. 点击 **"New +"** → **"Web Service"**
3. 选择你的 GitHub 仓库：`AuroraDai/weihao`
4. 如果仓库未连接，点击 **"Connect GitHub"** 连接

### 2. 配置服务设置

#### 基本信息
- **Name**: `finviz-api` (或你喜欢的名称)
- **Region**: 选择离你最近的区域（例如：Singapore）
- **Branch**: `main`
- **Root Directory**: `backend` ⚠️ **重要：必须设置为 `backend`**

#### 构建和启动命令

**Build Command**:
```bash
pip install -r requirements.txt
```

**Start Command**:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

⚠️ **重要**：
- Render 会自动设置 `$PORT` 环境变量
- 必须使用 `0.0.0.0` 作为 host（不是 `127.0.0.1`）
- 必须使用 `$PORT` 而不是固定端口号
- `--workers 1` 确保单进程运行（Free Plan 推荐）

#### 环境变量配置

点击 **"Environment"** 标签，添加以下环境变量：

| Key | Value | 说明 |
|-----|-------|------|
| `FINVIZ_EXPORT_URL` | `https://finviz.com/export.ashx?v=152&c=0,1,2,79,3,4,5,6,7,82,55,56,57,67,69,81,86,87,88,65,66,135,136,137,103,100&auth=eacf5d41-7e96-48e2-8b4a-2219ab605f1f` | 你的 Finviz 导出 URL |

**注意**：
- 将上面的 `FINVIZ_EXPORT_URL` 替换为你自己的 URL
- 如果需要其他环境变量，也可以在这里添加

### 3. 选择计划

- **Free Plan**: 免费，但服务会在 15 分钟无活动后休眠
- **Starter Plan**: $7/月，服务始终运行

对于测试，可以先选择 Free Plan。

### 4. 部署

1. 点击 **"Create Web Service"**
2. Render 会自动开始构建和部署
3. 等待部署完成（通常需要 2-5 分钟）

### 5. 获取后端 URL

部署成功后，你会看到：

- **URL**: `https://finviz-api.onrender.com` (示例)
- 复制这个 URL，这就是你的 `API_BASE`

### 6. 测试后端

在浏览器中访问：
```
https://your-service-name.onrender.com/health
```

应该返回：
```json
{"status":"ok"}
```

### 7. 配置 Streamlit Cloud

在 Streamlit Cloud 的 Secrets 中设置：
```toml
[secrets]
API_BASE = "https://your-service-name.onrender.com"
VITE_APP_PASSWORD = "daiweihao1990"
```

## 常见问题

### 1. 部署失败：ModuleNotFoundError

**原因**: 依赖未正确安装

**解决**:
- 检查 `backend/requirements.txt` 是否存在
- 确保所有依赖都在 requirements.txt 中
- 查看构建日志确认依赖安装成功

### 2. 502 Bad Gateway

**原因**: 应用启动失败

**解决**:
- 检查 Start Command 是否正确
- 确保使用 `0.0.0.0` 和 `$PORT`
- 查看日志：在 Render Dashboard → Logs

### 3. 服务休眠（Free Plan）

**原因**: Free Plan 在 15 分钟无活动后会休眠

**解决**:
- 首次访问会需要 30-60 秒唤醒
- 或者升级到付费计划

### 4. CORS 错误

**原因**: 后端未允许 Streamlit Cloud 的域名访问

**解决**: 检查 `backend/app/main.py` 中的 CORS 配置：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境可以使用 "*"
    # 生产环境建议指定域名：
    # allow_origins=["https://your-streamlit-app.streamlit.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 监控和维护

### 查看日志
- Render Dashboard → 你的服务 → **Logs** 标签
- 可以实时查看应用日志

### 重启服务
- Render Dashboard → 你的服务 → **Manual Deploy** → **Deploy latest commit**

### 更新代码
- 推送代码到 GitHub
- Render 会自动检测并重新部署（如果启用了 Auto-Deploy）

## 文件结构要求

确保你的项目结构如下：
```
trading/
├── backend/
│   ├── app/
│   │   └── main.py
│   └── requirements.txt
└── streamlit_app.py
```

**Root Directory** 必须设置为 `backend`，这样 Render 才能找到 `requirements.txt` 和 `app/main.py`。

## 费用说明

- **Free Plan**: 
  - 免费
  - 服务会在 15 分钟无活动后休眠
  - 首次唤醒需要 30-60 秒
  - 适合测试和低流量应用

- **Starter Plan**: 
  - $7/月
  - 服务始终运行
  - 适合生产环境

## 下一步

部署完成后：
1. 复制后端 URL
2. 在 Streamlit Cloud 配置 `API_BASE`
3. 测试应用是否正常工作

