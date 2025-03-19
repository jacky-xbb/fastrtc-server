# FastRTC 部署指南

本文档介绍如何在 Ubuntu 服务器上部署 FastRTC 应用。

## 1. 安装必要软件

```bash
# 更新包列表
sudo apt update

# 安装 Nginx
sudo apt install nginx

# 安装防火墙（可选）
sudo apt-get install ufw
```

## 2. 配置防火墙（可选）

```bash
# 设置默认规则
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许 SSH（重要！确保不会把自己锁在外面）
sudo ufw allow ssh
sudo ufw allow 22

# 允许 HTTP 和 HTTPS
sudo ufw allow 80
sudo ufw allow 443

# 允许应用端口
sudo ufw allow 7860

# 启用防火墙
sudo ufw enable

# 检查状态
sudo ufw status
```

## 3. 配置 SSL 证书

```bash
# 创建 SSL 目录
sudo mkdir -p /etc/nginx/ssl

# 生成自签名证书（替换 your_server_ip 为你的服务器 IP）
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/private.key \
    -out /etc/nginx/ssl/certificate.pem \
    -subj "/C=CN/ST=YourState/L=YourCity/O=YourOrg/CN=your_server_ip"

# 设置证书权限
sudo chmod 600 /etc/nginx/ssl/private.key
sudo chmod 644 /etc/nginx/ssl/certificate.pem
```

## 4. 配置 Nginx

创建 Nginx 配置文件：
```bash
sudo nano /etc/nginx/sites-available/fastrtc
```

添加以下配置（替换 your_server_ip 为你的服务器 IP）：
```nginx
server {
    listen 80;
    server_name your_server_ip;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your_server_ip;

    ssl_certificate /etc/nginx/ssl/certificate.pem;
    ssl_certificate_key /etc/nginx/ssl/private.key;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    location / {
        proxy_pass http://localhost:7860;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

启用配置：
```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/fastrtc /etc/nginx/sites-enabled/

# 删除默认配置（可选）
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

## 5. 启动 FastAPI 应用

```bash
# 进入项目目录
cd /path/to/your/project

# 启动应用
nohup uvicorn app:app --host 0.0.0.0 --port 7860 > ./logs/fastrtc.log 2>&1 &
```

## 6. 访问应用

- 使用 HTTPS 访问：`https://your_server_ip`（不要加端口号）
- 首次访问时会看到证书警告（因为使用自签名证书）
- 点击"高级"，然后"继续访问"

## 7. 故障排查

### 检查服务状态
```bash
# 检查 Nginx 状态
sudo systemctl status nginx

# 检查应用是否运行
ps aux | grep uvicorn
```

### 查看日志
```bash
# Nginx 访问日志
sudo tail -f /var/log/nginx/access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/error.log

# 应用日志
tail -f ./logs/fastrtc.log
```

### 检查端口
```bash
# 检查监听的端口
sudo netstat -tulpn | grep nginx
sudo netstat -tulpn | grep :7860
```

## 注意事项

1. 确保使用 HTTPS 访问（WebRTC 要求）
2. 不要在 URL 中添加端口号
3. 自签名证书仅用于测试，生产环境建议使用 Let's Encrypt 证书
4. 确保防火墙允许必要的端口访问
5. 生产环境中应该限制 CORS 和其他安全设置 