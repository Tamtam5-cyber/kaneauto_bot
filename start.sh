#!/bin/bash
echo "Cập nhật hệ thống..."
sudo apt update && sudo apt upgrade -y

echo "Cài đặt Python và thư viện cần thiết..."
sudo apt install python3 python3-pip -y
pip3 install -r requirements.txt

echo "Chạy bot..."
python3 bot.py
