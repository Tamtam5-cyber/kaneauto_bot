#!/bin/bash
echo "Tạo service systemd cho bot..."

sudo tee /etc/systemd/system/bot_forwarding.service > /dev/null <<EOF
[Unit]
Description=Telegram Forwarding Bot
After=network.target

[Service]
ExecStart=/usr/bin/python3 /root/bot.py
WorkingDirectory=/root/
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

echo "Kích hoạt bot chạy 24/7..."
sudo systemctl daemon-reload
sudo systemctl enable bot_forwarding
sudo systemctl start bot_forwarding
echo "Bot đã chạy nền thành công!" 
