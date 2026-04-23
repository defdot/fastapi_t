# Traefik HTTPS 配置说明

## 当前配置：本地自签名证书（开发环境）

### 1. docker-compose.yml 配置
- 暴露 443 端口（HTTPS）
- 挂载本地证书目录 (`./certs`)
- HTTP 自动重定向到 HTTPS

### 2. traefik/config.yml 配置
- 配置 HTTPS 路由使用本地证书文件
- HTTP 自动重定向到 HTTPS

---

## 开发环境使用步骤

### 1. 生成自签名证书

#### Linux/Mac
```bash
chmod +x generate-cert.sh
./generate-cert.sh
```

#### Windows PowerShell
```powershell
.\generate-cert.ps1
```

#### 手动生成（适用于所有平台）
```bash
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./certs/tls.key \
  -out ./certs/tls.crt \
  -subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1"
```

### 2. 启动服务

```bash
docker compose up -d
```

### 3. 访问

- HTTP: `http://localhost` (自动重定向到 HTTPS)
- HTTPS: `https://localhost`
- Dashboard: `http://localhost:8080`

**注意**: 浏览器会显示安全警告，点击"高级"→"继续访问"即可（自签名证书正常现象）。

### 4. 测试 HTTPS

```bash
# 忽略证书警告测试
curl -k https://localhost
```

---

## 生产环境：使用 Let's Encrypt

当部署到生产环境时，建议使用 Let's Encrypt 自动获取有效证书。

### 1. 修改 docker-compose.yml

```yaml
  traefik:
    image: traefik:v3.3
    command:
      - "--api.insecure=true"
      - "--providers.file.directory=/etc/traefik"
      - "--providers.file.watch=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      # Let's Encrypt 配置
      - "--certificatesresolvers.myresolver.acme.httpchallenge=true"
      - "--certificatesresolvers.myresolver.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.myresolver.acme.email=your-email@example.com"
      - "--certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - ./traefik:/etc/traefik
      - ./letsencrypt:/letsencrypt
```

**重要**: 将 `your-email@example.com` 替换为你的真实邮箱。

### 2. 修改 traefik/config.yml

将 HTTPS 路由的 TLS 配置改为：

```yaml
    # HTTPS 路由
    fastapi-secure:
      rule: "PathPrefix(`/`)"
      entryPoints:
        - websecure
      service: fastapi
      tls:
        certResolver: myresolver
```

### 3. 准备工作

```bash
# 创建证书存储目录
mkdir -p letsencrypt

# 确保域名已解析到服务器
ping yourdomain.com

# 确保 80 和 443 端口开放
# 检查防火墙规则
```

### 4. 启动服务

```bash
docker compose up -d
```

Let's Encrypt 会自动申请证书（首次申请需要 1-2 分钟）。

### 5. 验证

```bash
# 查看证书申请日志
docker compose logs traefik | grep -i acme

# 测试 HTTPS（无需 -k 参数）
curl https://yourdomain.com
```

---

## Let's Encrypt 常见问题

### 证书申请失败

1. **域名未解析**: 确保域名已正确解析到服务器 IP
2. **80 端口未开放**: Let's Encrypt 需要通过 80 端口验证域名所有权
3. **防火墙阻止**: 检查防火墙是否允许 80 和 443 端口
4. **查看日志**: `docker compose logs traefik | grep -i acme`

### 证书申请被限速

Let's Encrypt 有速率限制（每个域名每周最多 5 次失败申请）。可以使用测试环境调试：

```yaml
# 在 docker-compose.yml 中添加
- "--certificatesresolvers.myresolver.acme.caserver=https://acme-staging-v02.api.letsencrypt.org/directory"
```

测试成功后再移除此行使用生产环境。

### 证书自动续期

Let's Encrypt 证书有效期为 90 天，Traefik 会在证书过期前自动续期。

---

## 开发 vs 生产环境快速切换

### 从开发切换到生产

1. 修改 `docker-compose.yml`（添加 Let's Encrypt 配置）
2. 修改 `traefik/config.yml`（使用 `certResolver`）
3. 修改路由规则中的域名（从 localhost 改为实际域名）
4. 重启服务

### 从生产切换到开发

1. 修改 `docker-compose.yml`（移除 Let's Encrypt 配置）
2. 修改 `traefik/config.yml`（使用证书文件）
3. 修改路由规则中的域名（从实际域名改回 localhost）
4. 重启服务

---

## 本地 HTTPS 故障排查

### 证书文件不存在

```bash
# 检查证书文件
ls -la certs/

# 应该看到：
# tls.crt
# tls.key
```

### HTTPS 无法访问

1. 检查 443 端口是否被占用: `netstat -ano | findstr :443` (Windows) 或 `lsof -i :443` (Linux/Mac)
2. 查看 Traefik 日志: `docker compose logs traefik`
3. 检查证书文件权限: 确保 Traefik 容器有读取权限

### 重定向不生效

确认 `traefik/config.yml` 中的 `middlewares` 和 `routers` 配置正确，特别是：
- `fastapi-redirect` 路由使用了 `https-redirect` 中间件
- `fastapi-secure` 路由使用了 `websecure` 入口点

---

## 监控建议

### 开发环境
- 使用浏览器开发者工具检查证书信息
- 定期查看 Traefik Dashboard (http://localhost:8080)

### 生产环境
- 配置证书过期监控（Let's Encrypt 会发送到期提醒邮件）
- 使用外部监控服务检测 HTTPS 证书有效性
- 设置告警，在证书即将过期时收到通知
