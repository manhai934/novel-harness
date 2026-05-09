#!/bin/bash
# setup_cdp_chrome.sh
# 准备带有 CDP（Chrome DevTools Protocol）调试功能的 Chrome 环境。
# 通过此脚本，agent-browser 可以复用用户的 Chrome 登录态。
#
# 用法: bash setup_cdp_chrome.sh [端口号]
#   端口号: CDP 调试端口（默认: 9222）

set -e

CDP_PORT="${1:-9222}"
CHROME_APP="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_DEFAULT_PROFILE="$HOME/Library/Application Support/Google/Chrome"
CHROME_DEBUG_PROFILE="$HOME/chrome-debug-profile"

echo "=== CDP Chrome 环境准备 ==="
echo "CDP 端口: $CDP_PORT"

# 第一步：检查 CDP 端口是否已在监听
if lsof -nP -iTCP:${CDP_PORT} -sTCP:LISTEN &>/dev/null; then
    echo "✅ CDP 端口 $CDP_PORT 已处于活跃状态。"
    # 验证端口是否正常响应
    if curl -s --connect-timeout 3 http://127.0.0.1:${CDP_PORT}/json/version &>/dev/null; then
        echo "✅ CDP 连接已验证，Chrome 就绪。"
        curl -s http://127.0.0.1:${CDP_PORT}/json/version 2>/dev/null | head -5
        exit 0
    else
        echo "⚠️  端口正在监听但无响应，将重启 Chrome。"
    fi
fi

# 第二步：检查 Chrome 默认 profile 是否存在
if [ ! -d "$CHROME_DEFAULT_PROFILE/Default" ]; then
    echo "❌ 未找到 Chrome 默认 profile: $CHROME_DEFAULT_PROFILE/Default"
    echo "   请确保已安装 Google Chrome 并至少使用过一次。"
    exit 1
fi

# 第三步：将 Chrome profile 复制到调试目录（如需要）
if [ ! -d "$CHROME_DEBUG_PROFILE/Default" ]; then
    echo "📋 正在复制 Chrome profile 到调试目录..."
    mkdir -p "$CHROME_DEBUG_PROFILE"
    cp -R "$CHROME_DEFAULT_PROFILE/Default" "$CHROME_DEBUG_PROFILE/Default"
    echo "✅ Profile 已复制到: $CHROME_DEBUG_PROFILE"
else
    echo "✅ 调试用 profile 已存在于: $CHROME_DEBUG_PROFILE"
    # 可选：刷新 Cookie 和登录数据
    echo "📋 正在刷新 Cookie 和登录数据..."
    cp -f "$CHROME_DEFAULT_PROFILE/Default/Cookies" "$CHROME_DEBUG_PROFILE/Default/Cookies" 2>/dev/null || true
    cp -f "$CHROME_DEFAULT_PROFILE/Default/Login Data" "$CHROME_DEBUG_PROFILE/Default/Login Data" 2>/dev/null || true
fi

# 第四步：关闭所有现有的 Chrome 进程
echo "🔄 正在停止已有的 Chrome 进程..."
pkill -9 -f "Google Chrome" 2>/dev/null || true
sleep 3

# 确认所有 Chrome 进程已退出
REMAINING=$(ps aux | grep "[G]oogle Chrome" | wc -l | tr -d ' ')
if [ "$REMAINING" -gt 0 ]; then
    echo "⚠️  等待 Chrome 进程完全退出..."
    sleep 3
    pkill -9 -f "Google Chrome" 2>/dev/null || true
    sleep 2
fi

# 第五步：以 CDP 调试模式启动 Chrome
echo "🚀 正在以 CDP 模式启动 Chrome（端口 $CDP_PORT）..."
"$CHROME_APP" \
    --remote-debugging-port=$CDP_PORT \
    --user-data-dir="$CHROME_DEBUG_PROFILE" \
    &>/dev/null &

# 第六步：等待 Chrome 完全启动并验证 CDP 连接
echo "⏳ 等待 Chrome 启动..."
for i in $(seq 1 15); do
    sleep 2
    if lsof -nP -iTCP:${CDP_PORT} -sTCP:LISTEN &>/dev/null; then
        VERSION=$(curl -s --connect-timeout 3 http://127.0.0.1:${CDP_PORT}/json/version 2>/dev/null)
        if [ -n "$VERSION" ]; then
            echo "✅ Chrome 已成功以 CDP 模式启动（端口 $CDP_PORT）"
            echo "$VERSION" | head -5
            exit 0
        fi
    fi
    echo "   尝试 $i/15..."
done

echo "❌ 30 秒内未能启动 Chrome CDP 环境。"
echo "   可能原因："
echo "   - 当前系统的 Chrome 可能不支持 --remote-debugging-port"
echo "   - 端口 $CDP_PORT 可能已被其他进程占用"
echo "   - user-data-dir 目录可能已损坏"
exit 1
