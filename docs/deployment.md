# 生产部署说明

> 更新：2026-10-26。当前生产采用「FastAPI 单服务」架构：后端同时提供 API 和前端页面，
> 不再运行 Vite dev server，也不使用 nginx。

## 一、架构与访问地址

```
浏览器（校内）──► http://172.27.60.120:14600        ──┐
浏览器（校外）──► frp 隧道 http://47.123.6.147:14600 ──┤
微信机器人 ────► 推送 http://47.123.6.147:14600/     ──┤
                                                    ▼
                          FastAPI 单服务（lesson/main.py，端口 14600）
                          ├── /api/*        后端接口
                          ├── /static/*     附件
                          └── /*            frontend/dist 静态页面（GET / 兜底 index.html）
```

- **端口**：由服务器 `lesson/config/lesson.yaml` 的 `server_port` 配置，**默认 14600**
  （2026-10-27 决定：生产统一回到 14600 单端口明文，与微信机器人/frp 链路完全兼容；
  校内访问 `http://172.27.60.120:14600`）
- **HTTPS**：lesson.yaml 配 `use_https: true` 启用，uvicorn 原生 TLS；
  自签名证书在首次启动时自动生成到 `lesson/ssl/`（不入库），浏览器首次访问需信任一次。
  **生产保持默认 false（明文 HTTP）**——微信机器人回传与 frp 链路均按明文设计（2026-10-27 决定）
- **前端路由**：Vue history 模式，深链接刷新由后端 SPA 回退兜底

## 二、配置键速查（lesson/config/lesson.yaml，服务器私有文件，不进 git）

| 键 | 默认 | 说明 |
|----|------|------|
| `server_port` | `14600` | 后端监听端口（生产统一入口）；本地开发机 vite dev 占用 3333 时不受影响 |
| `use_https` | `false` | `true` 时以 HTTPS 监听，证书自动生成；生产保持 false（微信机器人链路按明文设计） |
| `wx_listen_port` | `0`（关闭） | 备用：若未来主服务必须开 HTTPS，配此端口起明文迷你服务专接微信机器人回传（见下节） |
| `demo_mode` | `false` | `true` 时使用 `databases/demo/` 演示库（仅教程录制机） |
| `log_retention_days` | `1095` | 日志保留天数（文件与 access.db 同用），启动时自动清理过期记录 |

### 微信机器人链路（与迁移前完全一致）

云端机器人（mtx 工具）把消息**推送到公网服务器 G**（`47.123.6.147:14600`），该端口在机器人侧
**不可更改**。生产为 14600 单端口明文 HTTP，frp 单隧道透传，机器人/frp/附件链接全部零配置：

```toml
# S 上的 frpc 配置
[lesson]
type = tcp
local_port = 14600       # S 主服务（HTTP 明文）
remote_port = 14600      # 公网 http://47.123.6.147:14600
```

- 机器人管理面板回调：`http://47.123.6.147:14600/`（无需改动）
- `wechat.yaml` 的 `static_url`：`http://47.123.6.147:14600/static/`（无需改动）

> 历史教训（2026-10-26/27）：曾尝试主服务开 HTTPS + 端口统一 3333，但 frp 是原始 TCP 隧道
> 不改协议，机器人的 HTTP 明文推到 TLS 端口会被拒（日志表现为 `Invalid HTTP request received`）。
> 若未来确需 HTTPS，必须用 `wx_listen_port` 给机器人保留一条端到端明文链路（双隧道方案，
> 公网 14600 整口让给机器人，浏览器另开新端口）。

## 三、部署流程（deploy-pack 增量部署）

1. **打包**（开发机）：对 Claude 说「打包部署」，或手动：
   ```bash
   python3 .claude/skills/deploy-pack/scripts/pack_changes.py \
     --files /tmp/deploy_files.txt --out deploy_<主题>_<日期>.zip --note "变更说明"
   ```
   - 前端有改动时：本地 `npm run build`，**把 `frontend/dist/` 一起打进包**
   - 不要在服务器上 build 前端（服务器源码不保证完整，会悄悄漏功能）
2. **服务器**：解压 ZIP → 进入 `_deploy/` 运行 `deploy.bat D:\projects\honghuanghou`
   （自动备份旧文件 → 二次确认 → 覆盖）
3. **重启后端**（`python main.py`，端口/HTTPS 由 lesson.yaml 决定）
4. 回滚：备份目录里的 `restore.bat`

## 四、注意事项

- **日志体系（2026-10-27 起）**：`lesson/logs/` 按模块分文件——`app_日期.log`（应用主文件）、
  `wxbot_日期.log`（微信机器人）、`access_日期.log`（访问记录：IP/用户/路径/状态/耗时）、
  `error_日期.log`（全模块错误汇聚）。保留 `log_retention_days` 天（lesson.yaml 配置，默认 1095），
  启动时自动清理过期文件。访问日志同时入 `databases/access.db`，管理后台「访问日志」页可查（仅 admin）。
  生产库需一次性执行权限/菜单 INSERT（见部署包说明）。

- **数据库禁止覆盖**：`lesson/databases/` 严禁从开发机拷贝覆盖服务器；
  schema 变更靠启动自动迁移或手工 `ALTER TABLE`
- **frp**：frpc 常驻，`[lesson]` 段 `local_port` 须与 `server_port` 一致（当前 3333），
  `remote_port` 14600 对公网。不要映射其他本地端口到公网（曾有 vite dev 暴露公网被扫描的事故）
- **API 权限**：新增/修改接口后需在数据库 `api_permission_config` 表补权限行（后台「API权限配置」页可改）
- **Windows 防火墙**：入站需放行 3333/tcp
- 历史方案 `nginx-https-config.md` 为备用参考，当前未采用
