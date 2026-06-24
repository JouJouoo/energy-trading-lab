#!/bin/bash

if [ -z "$GITHUB_TOKEN" ]; then
    echo "请设置 GITHUB_TOKEN 环境变量"
    echo "export GITHUB_TOKEN=your_personal_access_token"
    exit 1
fi

OWNER="JouJouoo"
REPO="energy-trading-lab"
TAG="v0.1.0"
DMG_FILE="web/src-tauri/target/release/bundle/dmg/Energy_Trading_Lab_0.1.0_aarch64.dmg"

if [ ! -f "$DMG_FILE" ]; then
    echo "DMG 文件不存在: $DMG_FILE"
    exit 1
fi

echo "正在上传 $DMG_FILE 到 GitHub Release $TAG..."

curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Content-Type: application/octet-stream" \
    --data-binary @"$DMG_FILE" \
    "https://uploads.github.com/repos/$OWNER/$REPO/releases/tags/$TAG/assets?name=$(basename "$DMG_FILE")"

if [ $? -eq 0 ]; then
    echo "上传成功！"
    echo "下载地址: https://github.com/$OWNER/$REPO/releases/download/$TAG/$(basename "$DMG_FILE")"
else
    echo "上传失败"
    exit 1
fi
