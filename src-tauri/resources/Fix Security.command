#!/bin/bash
# 移除 macOS 安全限制（quarantine 属性）
# 双击此文件即可修复 Vocistant 无法打开的问题

APP_PATH="/Applications/Vocistant.app"

if [ ! -d "$APP_PATH" ]; then
    echo "错误：未找到 $APP_PATH，请先将 Vocistant 拖入 Applications 文件夹。"
    read -p "按回车键关闭..."
    exit 1
fi

echo "正在移除安全限制..."
xattr -cr "$APP_PATH"
echo "完成！现在可以正常打开 Vocistant 了。"
sleep 2
