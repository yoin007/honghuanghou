# 生产部署说明

> 更新：2026-10-26。当前生产采用「FastAPI 单服务」架构：后端同时提供 API 和前端页面，
> 不再运行 Vite dev server，也不使用 nginx。

## 一、架构与访问地址

```
浏览器（校内）──► http(s)://172.27.60.120:3333   ──┐
浏览器（校外）──► frp 隧道(公网 47.123.6.147)      ──┤
                                                    ▼
                          FastAPI 单服务（lesson/main.py）
                          ├── /api/*        后端接口
                          ├── /static/*     附件
                          └── /*            frontend/dist 静态页面（GET / 兜底 index.html）
```

- **端口**：由服务器 `lesson/config/lesson.yaml` 的 `server_port` 配置，**默认 3333**
- **HTTPS**：lesson.yaml 配 `use_https: true` 启用，uvicorn 原生 TLS；
  自签名证书在首次启动时自动生成到 `lesson/ssl/`（不入库），浏览器首次访问需信任一次
- **前端路由**：Vue history 模式，深链接刷新由后端 SPA 回退兜底

## 二、配置键速查（lesson/config/lesson.yaml，服务器私有文件，不进 git）

| 键 | 默认 | 说明 |
|----|------|------|
| `server_port` | `3333` | 后端监听端口；本地开发机与 vite dev 冲突时改 `14600` |
| `use_https` | `false` | `true` 时以 HTTPS 监听，证书自动生成 |
| `demo_mode` | `false` | `true` 时使用 `databases/demo/` 演示库（仅教程录制机） |

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

- **数据库禁止覆盖**：`lesson/databases/` 严禁从开发机拷贝覆盖服务器；
  schema 变更靠启动自动迁移或手工 `ALTER TABLE`
- **frp**：frpc 常驻，`[lesson]` 段 `local_port` 须与 `server_port` 一致（当前 3333），
  `remote_port` 14600 对公网。不要映射其他本地端口到公网（曾有 vite dev 暴露公网被扫描的事故）
- **API 权限**：新增/修改接口后需在数据库 `api_permission_config` 表补权限行（后台「API权限配置」页可改）
- **Windows 防火墙**：入站需放行 3333/tcp
- 历史方案 `nginx-https-config.md` 为备用参考，当前未采用
