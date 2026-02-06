# 部署指南

## Docker 部署

```bash
docker-compose up -d
```

## Systemd 服务

创建 `/etc/systemd/system/package-downloader.service`:

```ini
[Unit]
Description=Offline Package Downloader
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/package-downloader
ExecStart=/usr/bin/python3 backend/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
sudo systemctl enable package-downloader
sudo systemctl start package-downloader
```

## Nginx 反向代理

```nginx
server {
    listen 80;
    server_name packages.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```
