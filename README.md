# 洪荒后 - 班级数据展示系统

一个功能完整的班级管理平台，支持作业发布、学生管理、课表查询、日常记录等功能。

## 功能特性

- **作业管理** - 发布、编辑、删除作业，支持日常/周末作业分类
- **公告管理** - 班级公告发布与展示
- **学生管理** - 学生信息查看、导入导出
- **课表查询** - 班级课表、教师课表展示
- **日常记录** - 学生请假、外出等记录管理
- **权限控制** - 基于角色的访问控制（管理员/学发部/班主任/教师）

## 技术栈

### 前端
- Vue 3 + Composition API
- Element Plus UI 组件库
- Pinia 状态管理
- Vite 构建工具
- ECharts 图表库

### 后端
- FastAPI 框架
- SQLite 数据库
- Redis 缓存
- WebSocket 实时通信

## 项目结构

```
honghuanghou/
├── frontend/                # 前端项目
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── components/     # 公共组件
│   │   ├── stores/         # Pinia 状态
│   │   ├── api/            # API 接口
│   │   └── router/         # 路由配置
│   └── package.json
│
├── lesson/                  # 后端项目
│   ├── main.py             # 入口文件
│   ├── config/             # 配置文件
│   ├── models/             # 数据模型
│   │   ├── datas_api/      # API 模块（模块化）
│   │   ├── lesson/         # 课程相关
│   │   └── manage/         # 管理模块
│   ├── utils/              # 工具函数
│   └── requirements.txt
│
└── README.md
```

## 快速开始

### 环境要求
- Node.js >= 18
- Python >= 3.10
- Redis >= 6.0

### 后端启动

```bash
cd lesson

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写实际配置

# 启动服务
python main.py
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `JWT_SECRET_KEY` | JWT 密钥 | 是 |
| `REDIS_HOST` | Redis 主机 | 否（默认 localhost） |
| `REDIS_PORT` | Redis 端口 | 否（默认 6379） |
| `CORS_ORIGINS` | 允许的跨域来源 | 否 |

### 用户数据

用户账号密码存储在 `checkTemplate.xlsx` 的 `teachers` 表中：

| 字段 | 说明 |
|------|------|
| `name` | 用户名 |
| `pwd` | 密码（bcrypt 加密） |
| `raw_pwd` | 明文密码 |
| `role` | 角色（admin/teacher/cleader） |
| `active` | 是否激活 |

## API 接口

主要接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/token` | POST | 用户登录 |
| `/api/homework/{class_code}` | GET | 获取班级作业 |
| `/api/class-codes/` | GET | 获取班级列表 |
| `/api/schedule/{class_name}` | GET | 获取班级课表 |
| `/api/teachers` | GET | 获取教师列表 |
| `/api/get_dailies/` | GET | 获取日常记录 |

## 权限说明

| 角色 | 权限 |
|------|------|
| `admin` | 完全访问权限 |
| `teacher/xuefa` | 学发部，可管理所有班级 |
| `cleader` | 班主任，仅管理自己班级 |
| `teacher` | 普通教师，基础访问权限 |

## 开发规范

- **分支策略**: `feature/*` -> `develop` -> `main`
- **提交规范**: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- **代码风格**: 遵循 PEP 8（Python）和 ESLint（JavaScript）

## License

MIT License