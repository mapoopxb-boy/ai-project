#!/usr/bin/env bash
set -euo pipefail

# ==============================================================
# AI 项目一键部署脚本
# 检测 Docker / Docker Compose，自动安装，启动所有服务
# ==============================================================

cd "$(dirname "$0")"
PROJECT_ROOT="$(pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERR]${NC}  $1"; }

# ==============================================================
# 1. 检测 Docker
# ==============================================================
info "检查 Docker 环境……"

if command -v docker &>/dev/null; then
    ok "Docker 已安装 ($(docker --version))"
else
    warn "Docker 未安装，正在自动安装……"
    if [[ "$(uname -s)" == "Linux" ]]; then
        curl -fsSL https://get.docker.com | bash
        sudo usermod -aG docker "$USER" || true
        ok "Docker 安装完成，请重新登录以激活用户组权限"
    else
        err "非 Linux 系统，请手动安装 Docker Desktop"
        err "https://docs.docker.com/get-docker/"
        exit 1
    fi
fi

# ==============================================================
# 2. 检测 Docker Compose（compose plugin 或独立二进制）
# ==============================================================
info "检查 Docker Compose……"

DOCKER_COMPOSE_CMD=""
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
    ok "Docker Compose v2 插件已安装"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
    ok "Docker Compose v1 已安装"
else
    warn "Docker Compose 未安装，正在自动安装……"
    if [[ "$(uname -s)" == "Linux" ]]; then
        COMPOSE_VERSION=$(curl -fsSL https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
        sudo curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        DOCKER_COMPOSE_CMD="docker-compose"
        ok "Docker Compose 安装完成"
    else
        err "非 Linux 系统，请手动安装 Docker Desktop（自带 Compose）"
        err "https://docs.docker.com/compose/install/"
        exit 1
    fi
fi

# ==============================================================
# 3. 检查 .env 配置文件
# ==============================================================
ENV_FILE="$PROJECT_ROOT/backend/.env"
ENV_EXAMPLE="$PROJECT_ROOT/backend/.env.example"

if [[ -f "$ENV_FILE" ]]; then
    ok "backend/.env 已存在"
else
    if [[ -f "$ENV_EXAMPLE" ]]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        info "已从 backend/.env.example 复制为 backend/.env"
        echo -e ""
        echo -e "${YELLOW}⚠️  请编辑 backend/.env，填入真实的配置值：${NC}"
        echo -e "${YELLOW}   vim backend/.env${NC}"
        echo -e "${YELLOW}   或直接在下方命令行中编辑${NC}"
        echo -e ""
        echo -e "${YELLOW}   关键配置项：${NC}"
        sed -n 's/^# ============== /  /p' "$ENV_EXAMPLE" 2>/dev/null || true
        echo -e ""
        read -r -p "是否继续启动？(y/N) " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            info "已取消部署，编辑 backend/.env 后重新运行本脚本即可"
            exit 0
        fi
    else
        err "未找到 backend/.env.example，请确保初始配置存在"
        exit 1
    fi
fi

# ==============================================================
# 4. 启动服务
# ==============================================================
info "启动 Docker Compose 服务……"

$DOCKER_COMPOSE_CMD up -d

echo -e ""
info "等待服务启动……"

# ==============================================================
# 5. 等待健康检查通过
# ==============================================================
MAX_RETRIES=30
RETRY_INTERVAL=5
BACKEND_READY=false

for ((i=1; i<=MAX_RETRIES; i++)); do
    if curl -sf http://localhost:80/api/healthz >/dev/null 2>&1; then
        BACKEND_READY=true
        break
    fi
    if curl -sf http://localhost:8000/api/healthz >/dev/null 2>&1; then
        BACKEND_READY=true
        break
    fi
    echo -ne "\r  等待后端就绪…… (${i}/${MAX_RETRIES})"
    sleep "$RETRY_INTERVAL"
done
echo ""

if [[ "$BACKEND_READY" == "true" ]]; then
    ok "后端服务已就绪！"
else
    warn "后端服务未在预期时间内响应，请检查日志：$DOCKER_COMPOSE_CMD logs backend"
fi

# ==============================================================
# 6. 输出部署信息
# ==============================================================
echo -e ""
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}  ✅ 部署完成！${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e ""

# 获取本机 IP
LOCAL_IP=$(ip route get 1 2>/dev/null | awk '{print $7}' 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo -e "  ${CYAN}访问地址${NC}"
echo -e "  API 服务:    http://$LOCAL_IP:8000"
echo -e "  API 文档:    http://$LOCAL_IP:8000/docs"
echo -e "  Nginx 入口:  http://$LOCAL_IP"
echo -e ""
echo -e "  ${CYAN}默认账号${NC}"
echo -e "  医生端:      用户名 demo_doctor / 密码 123456"
echo -e "  患者端:      手机号 13900001111"
echo -e ""
echo -e "  ${CYAN}管理命令${NC}"
echo -e "  查看日志:    $DOCKER_COMPOSE_CMD logs -f"
echo -e "  停止服务:    $DOCKER_COMPOSE_CMD down"
echo -e "  重启服务:    $DOCKER_COMPOSE_CMD restart"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
