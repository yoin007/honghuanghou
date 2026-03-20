# Nginx HTTPS 重定向配置教程

## 1. 安装 Nginx

### Windows
```powershell
# 下载 nginx
# 访问 http://nginx.org/en/download.html 下载 Windows 版本
# 解压到 C:\nginx

# 或使用 winget
winget install nginx
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install nginx
```

### Linux (CentOS/RHEL)
```bash
sudo yum install epel-release
sudo yum install nginx
```

### macOS
```bash
brew install nginx
```

---

## 2. 获取 SSL 证书

### 方案 A: 自签名证书（内网测试用）

```bash
# Linux/macOS
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/server.key \
  -out /etc/nginx/ssl/server.crt \
  -subj "/CN=172.27.60.120"

# Windows (PowerShell 管理员)
New-Item -ItemType Directory -Force -Path C:\nginx\ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout C:\nginx\ssl\server.key -out C:\nginx\ssl\server.crt -subj "/CN=172.27.60.120"
```

### 方案 B: Let's Encrypt 免费证书（公网域名）

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx  # Ubuntu
sudo yum install certbot python3-certbot-nginx  # CentOS

# 自动获取并配置证书
sudo certbot --nginx -d yourdomain.com
```

---

## 3. Nginx 配置文件

### 配置文件位置

| 系统 | 位置 |
|------|------|
| Linux | `/etc/nginx/nginx.conf` 或 `/etc/nginx/conf.d/*.conf` |
| Windows | `C:\nginx\conf\nginx.conf` |
| macOS | `/usr/local/etc/nginx/nginx.conf` 或 `/opt/homebrew/etc/nginx/nginx.conf` |

### 完整配置示例（多服务共存）

```nginx
# nginx.conf

worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    # gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # ========== 服务1: 红皇后系统 (3333 端口) ==========
    # HTTP 服务 - 重定向到 HTTPS
    server {
        listen 3333;
        server_name 172.27.60.120;

        # 强制跳转 HTTPS
        return 301 https://$host:3334$request_uri;
    }

    # HTTPS 服务
    server {
        listen 3334 ssl;
        server_name 172.27.60.120;

        # SSL 证书配置
        ssl_certificate     /etc/nginx/ssl/server.crt;      # Windows: C:/nginx/ssl/server.crt
        ssl_certificate_key /etc/nginx/ssl/server.key;      # Windows: C:/nginx/ssl/server.key

        # SSL 优化
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # 反向代理到后端服务
        location / {
            proxy_pass http://127.0.0.1:14600;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket 支持
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            # 超时设置
            proxy_connect_timeout 60s;
            proxy_read_timeout 60s;
            proxy_send_timeout 60s;
        }
    }

    # ========== 服务2: 其他 HTTP 服务 (8080 端口) ==========
    # 保持 HTTP，不重定向
    server {
        listen 8080;
        server_name 172.27.60.120;

        location / {
            proxy_pass http://127.0.0.1:8081;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    # ========== 服务3: 另一个 HTTPS 服务 (8443 端口) ==========
    server {
        listen 8443 ssl;
        server_name 172.27.60.120;

        ssl_certificate     /etc/nginx/ssl/server.crt;
        ssl_certificate_key /etc/nginx/ssl/server.key;

        location / {
            proxy_pass http://127.0.0.1:9000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

---

## 4. Windows 专用配置

Windows 路径需要使用正斜杠 `/` 或转义反斜杠 `\\`：

```nginx
# Windows 路径写法
ssl_certificate     C:/nginx/ssl/server.crt;
ssl_certificate_key C:/nginx/ssl/server.key;

# 或
ssl_certificate     C:\\nginx\\ssl\\server.crt;
ssl_certificate_key C:\\nginx\\ssl\\server.key;
```

### Windows 服务管理

```powershell
# 启动
cd C:\nginx
start nginx

# 停止
nginx -s stop

# 重载配置
nginx -s reload

# 测试配置
nginx -t
```

---

## 5. Linux 服务管理

```bash
# 测试配置
sudo nginx -t

# 启动
sudo systemctl start nginx

# 停止
sudo systemctl stop nginx

# 重载配置（不中断服务）
sudo systemctl reload nginx

# 开机自启
sudo systemctl enable nginx

# 查看状态
sudo systemctl status nginx
```

---

## 6. 防火墙配置

### Linux (ufw)
```bash
sudo ufw allow 3333/tcp
sudo ufw allow 3334/tcp
sudo ufw reload
```

### Linux (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=3333/tcp
sudo firewall-cmd --permanent --add-port=3334/tcp
sudo firewall-cmd --reload
```

### Windows
```powershell
# 管理员 PowerShell
New-NetFirewallRule -DisplayName "Nginx HTTP 3333" -Direction Inbound -LocalPort 3333 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Nginx HTTPS 3334" -Direction Inbound -LocalPort 3334 -Protocol TCP -Action Allow
```

---

## 7. 访问测试

```bash
# 测试 HTTP 重定向
curl -I http://172.27.60.120:3333
# 应返回 301 重定向到 https://...

# 测试 HTTPS
curl -k https://172.27.60.120:3334
# -k 跳过证书验证（自签名证书需要）

# 浏览器访问
# http://172.27.60.120:3333  → 自动跳转到 https://172.27.60.120:3334
```

---

## 8. 常见问题

### Q: 浏览器提示证书不安全
A: 自签名证书不被信任，点击"继续访问"即可。生产环境建议使用正式证书。

### Q: WebSocket 连接失败
A: 确保配置了 `proxy_http_version 1.1` 和 `Upgrade` 头。

### Q: 端口被占用
```bash
# Linux 查看端口占用
sudo lsof -i :3333
sudo netstat -tlnp | grep 3333

# Windows 查看端口占用
netstat -ano | findstr :3333
```

### Q: 权限问题 (Linux)
```bash
# 确保 nginx 用户有权限访问证书文件
sudo chown -R nginx:nginx /etc/nginx/ssl/
sudo chmod 600 /etc/nginx/ssl/server.key
```

---

## 9. 同端口 HTTP 重定向到 HTTPS

**使用同一端口 3333，HTTP 自动跳转 HTTPS：**

```nginx
server {
    listen 3333 ssl;
    server_name 172.27.60.120;

    # SSL 证书配置
    ssl_certificate     /etc/nginx/ssl/server.crt;      # Windows: C:/nginx/ssl/server.crt
    ssl_certificate_key /etc/nginx/ssl/server.key;      # Windows: C:/nginx/ssl/server.key

    # 关键：捕获 497 错误并重定向到 HTTPS
    error_page 497 https://$host:$server_port$request_uri;

    location / {
        proxy_pass http://127.0.0.1:14600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**原理：**
- Nginx 端口配置 `ssl` 后，只接受 HTTPS 连接
- HTTP 请求到达时，Nginx 返回 497 错误（HTTP Request Sent to HTTPS Port）
- `error_page 497` 捕获错误并重定向到 HTTPS

**访问流程：**
```
用户访问 http://172.27.60.120:3333
    ↓
Nginx 收到 HTTP 请求但端口要求 HTTPS
    ↓
返回 497 错误
    ↓
error_page 捕获，301 重定向到 https://172.27.60.120:3333
    ↓
正常访问 HTTPS
```

---

## 10. 简化配置（单服务）

如果只有红皇后一个服务，可简化为：

```nginx
server {
    listen 3333;
    server_name 172.27.60.120;
    return 301 https://$host:3334$request_uri;
}

server {
    listen 3334 ssl;
    server_name 172.27.60.120;

    ssl_certificate     /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;

    location / {
        proxy_pass http://127.0.0.1:14600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

访问流程：
```
用户 → http://172.27.60.120:3333 → Nginx 301重定向 → https://172.27.60.120:3334 → Nginx代理 → http://127.0.0.1:14600 (后端)
```