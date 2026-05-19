# 启动脚本使用说明

## 目录结构

```
scripts/
├── package.sh        # 打包脚本 (macOS/Linux)
│
├── windows/          # Windows 平台脚本
│   ├── install.bat       # 安装依赖
│   ├── start-backend.bat # 启动后端
│   ├── start-frontend.bat# 启动前端
│   ├── start-all.bat     # 启动全部
│   └── stop-all.bat      # 停止全部
│
└── unix/             # macOS/Linux 平台脚本
    ├── install.sh        # 安装依赖
    ├── start-backend.sh  # 启动后端
    ├── start-frontend.sh # 启动前端
    ├── start-all.sh      # 启动全部
    └── stop-all.sh       # 停止全部
```

## 打包部署

```bash
# 在 macOS/Linux 上打包，生成 Windows 部署包
./scripts/package.sh [版本号]

# 示例
./scripts/package.sh              # 自动使用时间戳作为版本号
./scripts/package.sh v1.0.0       # 指定版本号

# 输出文件: release/honghuanghou_<版本号>.zip
```

打包内容：
- `lesson/` 后端代码（不含数据库、日志、缓存、测试）
- `frontend/` 前端源码（不含 node_modules）
- `scripts/*.bat` Windows 启动脚本
- `部署说明.txt` 部署指南

## Windows 使用方法

```powershell
# 1. 安装依赖
scripts\windows\install.bat

# 2. 启动服务
scripts\windows\start-all.bat

# 或单独启动
scripts\windows\start-backend.bat   # 后端
scripts\windows\start-frontend.bat  # 前端

# 3. 停止服务
scripts\windows\stop-all.bat
```

## macOS/Linux 使用方法

```bash
# 1. 安装依赖
./scripts/unix/install.sh

# 2. 启动服务
./scripts/unix/start-all.sh

# 或单独启动
./scripts/unix/start-backend.sh   # 后端
./scripts/unix/start-frontend.sh  # 前端

# 3. 停止服务
./scripts/unix/stop-all.sh
```

## 端口说明

| 服务 | 端口 |
|------|------|
| 后端 API | 14600 |
| 前端开发服务 | 3333 |

## 配置文件

部署前请修改以下配置文件：

1. `lesson/config/lesson.yaml` - 配置数据存储路径
2. `lesson/config/wechat.yaml` - 配置 API 地址和管理员

## 日志

- Unix 平台日志保存在 `logs/` 目录
- Windows 平台日志直接在控制台窗口显示