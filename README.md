# OpenAI 实时语音聊天应用

这是一个基于 FastAPI 和 WebRTC 的实时语音聊天应用，支持与 OpenAI 进行实时语音对话。

## 功能特点

- 实时语音对话
- 音频可视化效果
- 实时文本显示
- 支持多用户并发连接
- 优雅的错误处理和提示

## 环境要求

- Python 3.8+
- FastAPI
- WebRTC 支持
- 现代浏览器（支持 WebRTC）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 创建 `.env` 文件并添加必要的环境变量：

```env
OPENAI_API_KEY=你的OpenAI API密钥
```

## 启动应用

### 使用 FastAPI 启动（默认模式）

```bash
python app.py
```

应用将在 http://localhost:7860 启动。

### 使用 Gradio UI 启动

```bash
MODE=UI python app.py
```

### 使用 FastPhone 模式启动

```bash
MODE=PHONE python app.py
```

## 使用说明

1. 打开浏览器访问 http://localhost:7860
2. 点击 "Start Conversation" 按钮开始对话
3. 允许浏览器访问麦克风
4. 开始说话，等待 AI 助手回复
5. 点击 "Stop Conversation" 结束对话

## 注意事项

- 确保有稳定的网络连接
- 首次使用需要允许浏览器访问麦克风
- 建议使用 Chrome 或 Firefox 浏览器
- 如果使用 VPN，可能会影响连接速度

## 开发模式

开发模式下，应用会自动监听文件变化并重新加载：

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 7860
```

## Ubuntu 守护进程配置

在 Ubuntu 系统中将应用配置为系统服务，实现开机自启动和自动重启：

1. 创建系统服务配置文件：

```bash
sudo nano /etc/systemd/system/fastrtc.service
```

2. 添加以下配置内容：

```ini
[Unit]
Description=FastRTC Server
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/fastrtc-server
Environment="PATH=/home/ubuntu/fastrtc-server/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/ubuntu/fastrtc-server/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 7860 --workers 4
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

3. 启动和管理服务：

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start fastrtc

# 设置开机自启
sudo systemctl enable fastrtc

# 查看服务状态
sudo systemctl status fastrtc
```

4. 常用管理命令：

```bash
# 停止服务
sudo systemctl stop fastrtc

# 重启服务
sudo systemctl restart fastrtc

# 查看实时日志
sudo journalctl -u fastrtc -f

# 查看最近的日志
sudo journalctl -u fastrtc -n 100
```

注意：请根据实际情况修改配置文件中的路径和用户名。




