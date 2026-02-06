# Streamlit Cloud 部署指南

## 架构说明

- **Streamlit** = 前端 UI（只负责展示）
- **FastAPI** = 后端 API（处理所有业务逻辑，需要单独部署）

## 部署步骤

### 1. 先部署 FastAPI 后端

在 Render/Railway/Heroku 等平台部署后端：

**Render 配置示例：**
- Type: Web Service
- Environment: Python 3
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment Variables:
  - `FINVIZ_EXPORT_URL`: 你的 Finviz 导出 URL

获取后端 URL，例如：`https://your-backend.onrender.com`

### 2. 在 Streamlit Cloud 部署前端

1. 访问 https://share.streamlit.io/
2. 连接 GitHub 仓库
3. 选择仓库：`AuroraDai/weihao`
4. 分支：`main`
5. **Main file path**: `streamlit_app.py`

### 3. 配置环境变量（**重要！**）

在 Streamlit Cloud 的 "Settings" → "Secrets" 中添加：

```toml
[secrets]
API_BASE = "https://your-backend.onrender.com"
VITE_APP_PASSWORD = "daiweihao1990"
```

**⚠️ 重要提示**：
- `API_BASE` **必须**是你部署的 FastAPI 后端 URL（例如：`https://your-backend.onrender.com`）
- **不要使用** `http://localhost:8000`（这在 Streamlit Cloud 上不可用）
- 如果未配置 `API_BASE`，应用会默认使用 `localhost:8000`，导致连接错误

**如何获取后端 URL**：
1. 在 Render/Railway/Heroku 等平台部署 FastAPI 后端
2. 获取后端服务的公开 URL（例如：`https://finviz-api.onrender.com`）
3. 将这个 URL 设置为 `API_BASE` 的值（**不要**包含路径，只要基础 URL）

### 4. 本地测试

如果你想在本地测试 Streamlit 前端：

1. 启动 FastAPI 后端：
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

2. 在另一个终端启动 Streamlit：
```bash
pip install streamlit requests python-dotenv pandas
streamlit run streamlit_app.py
```

3. 或者设置环境变量：
```bash
export API_BASE=http://localhost:8000
streamlit run streamlit_app.py
```

## 故障排除

### 502 Bad Gateway 错误

- **原因**: Streamlit 无法连接到后端
- **解决**: 
  1. 检查 `API_BASE` 环境变量是否正确
  2. 确认 FastAPI 后端正在运行
  3. 检查后端 URL 是否可访问

### Connection Error

- **原因**: 后端未运行或 URL 错误
- **解决**: 
  1. 测试后端健康检查：`curl https://your-backend.onrender.com/health`
  2. 确保后端 CORS 允许 Streamlit Cloud 的域名

## 文件说明

- `streamlit_app.py` - Streamlit 前端（只调用 API）
- `requirements.txt` - Streamlit 依赖（只需要 streamlit, requests, pandas）
- `backend/app/main.py` - FastAPI 后端（保持不变）

