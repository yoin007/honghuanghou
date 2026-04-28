# databases 目录数据库梳理与合并记录

## 目标

梳理 `lesson/databases` 目录下的 SQLite 数据库，识别字段和内容重复的表，并将可以统一的数据合并到单一主表，减少后续登录、教师管理、德育、监考、微信通知之间的数据不一致。

## 当前数据库清单

| 数据库 | 主要表 | 处理建议 |
|------|--------|----------|
| `auth.db` | `teacher` | 已合并到 `moral.db.teacher`，后续仅作历史来源 |
| `moral.db` | 德育、学生、班级、教师、评价等 | 保留，教师统一主表在此库 |
| `member.db` | `member`、`permission`、`contacts`、`chatroom`、`chatroom_member` | `member` 已并入 `moral.db.teacher`；其他表保留 |
| `invigilation.db` | 监考项目、安排、通知日志 | 保留，属于独立业务数据 |
| `homework.db` | 作业、晨读、公告 | 保留，业务独立 |
| `inout.db` | 请假/出入校 | 保留，业务独立 |
| `filegather.db` | 文件上传/打印流转 | 保留，业务独立 |
| `messages.db` | 微信消息 | 保留，日志类数据 |
| `queues.db` | 发送队列 | 保留，任务队列数据 |
| `task.db` | 定时任务 | 保留 |
| `daily.db` | 旧日常记录 | 与德育日常表现业务相似，但字段语义不同，暂不自动合并 |
| `notes.db` | 笔记 | 保留 |
| `colleges.db` | 高考/院校数据 | 保留，独立数据集 |
| `lesson.db` | 当前为空 | 可后续评估是否移除 |
| `main.db` | 当前为空 | 可后续评估是否移除 |

## 已合并的数据

### 1. `auth.db.teacher` -> `moral.db.teacher`

两张表都描述教师账号和角色，数据内容高度一致：

| 原字段 `auth.teacher` | 目标字段 `moral.teacher` | 说明 |
|------|------|------|
| `name` | `name` | 教师姓名/登录用户名 |
| `subject` | `subject` | 任教学科展示名 |
| `course` | `course` | 课程字段，已补入 `moral.teacher` |
| `notice` | `notice_enabled` | 通知开关 |
| `pwd` | `password_hash` | 密码或密码哈希 |
| `raw_pwd` | `raw_pwd` | 历史兼容字段，已补入 `moral.teacher` |
| `role` | `role` | 角色，支持 `teacher/cleader` 多角色 |
| `level` | `level` | 等级 |
| `active` | `is_active` | 登录是否启用 |
| `is_password_changed` | `is_password_changed` | 密码是否已修改 |

代码调整：

- `utils.teacher_db` 改为默认读写 `moral.db.teacher`。
- 登录认证 `models.datas_api.auth` 通过 `utils.teacher_db` 自动使用统一表。
- 教师管理 `models.datas_api.teachers` 的新增、更新、删除、改密改为写 `moral.teacher`。
- 管理员密码重置 `models.datas_api.admin` 改为写 `moral.teacher`。
- `create_moral_tables.py` 会自动从 `auth.db.teacher` 同步历史数据。

### 2. `member.db.member` -> `moral.db.teacher`

`member` 表描述微信会员身份，和教师/通知身份有重叠。已将会员身份字段并入 `moral.teacher`。

| 原字段 `member.member` | 目标字段 `moral.teacher` | 说明 |
|------|------|------|
| `uuid` | `uuid` | 会员唯一标识 |
| `wxid` | `wxid` | 微信 ID |
| `alias` | `alias` | 昵称/姓名 |
| `active` | `member_active` | 会员是否启用 |
| `score` | `score` | 积分 |
| `balance` | `balance` | 余额 |
| `level` | `level` | 权限等级 |
| `model` | `model` | 可用模块 |
| `ai_flag` | `ai_flag` | AI 标记 |
| `birthday` | `birthday` | 生日 |
| `priority` | `priority` | 优先级 |
| `note` | `note` | 备注 |

代码调整：

- `Member.member_info()` 改为从 `moral.teacher` 读取并返回旧字段顺序。
- `Member.insert_member()` 改为写入或更新 `moral.teacher`。
- `Member.update_member()` 改为更新 `moral.teacher`。
- `Member.delte_member()` 改为软禁用 `member_active`，不再物理删除旧身份。
- `Member.member_wxid()` 改为从 `moral.teacher` 查找。
- 旧 `/api/members` 接口改为走兼容方法，不再直接 SQL 查询 `member.db.member`。

保留原因：

- `member.db.permission` 是微信指令权限规则，不是教师档案。
- `member.db.contacts` 是微信联系人缓存。
- `member.db.chatroom`、`chatroom_member` 是群聊关系数据。
- 因此 `member.db` 不能整体删除，只是 `member` 身份表不再作为主表。

## 不建议自动合并的相似表

| 表 A | 表 B | 原因 |
|------|------|------|
| `daily.db.daily` | `moral.db.student_daily_record` | 都是日常记录，但旧表字段 `event/sid/style/recorder` 与德育评分、学期、班级快照、事件类型关联不同；应单独做历史导入脚本 |
| `homework.db.announcements` | 其他公告/消息表 | 业务语义不同，一个是班级公告，一个是微信消息或系统通知 |
| `messages.db.messages` | `queues.db.queues` | 都包含消息相关字段，但一个是接收消息日志，一个是发送队列 |
| `moral.db.teacher` | `invigilation.db.invigilation_slot.teacher_*` | 监考表中教师字段是安排快照，不能去掉，否则历史安排会随教师改名变化 |

## 当前统一主表

教师、网页登录账号、微信会员身份的统一主表：

```text
moral.db.teacher
```

该表通过 `identity_type` 区分：

| `identity_type` | 含义 |
|------|------|
| `teacher` | 正式教师/网页登录账号 |
| `member` | 仅微信会员，不是正式教师 |
| `deleted_teacher` | 已删除或禁用的教师账号历史记录 |

## 后续建议

1. 新增教师、修改教师、重置密码都只写 `moral.teacher`。
2. `auth.db.teacher` 后续不再新增数据，可在稳定运行一段时间后改名备份为 `auth_teacher_legacy` 或停止初始化。
3. `member.db.member` 后续不再新增数据，可保留只读备份。
4. 若要合并 `daily.db.daily` 到德育日常表现，应单独制定历史导入规则，不能按字段相似直接并表。
5. 文档和驾驶舱方案里的教师数据来源应统一改为 `moral.db.teacher`。

