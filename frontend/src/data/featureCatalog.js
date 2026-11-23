/**
 * 功能大厅静态数据
 * 与 docs/user-guide/feature-catalog.md 保持一致；上线新功能时两处同步更新。
 * 数据内置在前端，随部署一起更新（决策记录：REQ-2026-003）。
 */

export const FEATURE_GROUPS = [
  {
    key: 'dashboard',
    name: '看数据：数据驾驶舱',
    features: [
      { name: '总览驾驶舱', desc: '一屏看全校关键数据：学生、德育、教学总体情况', audience: '校领导' },
      { name: '班级驾驶舱', desc: '看某个班的各类数据与趋势', audience: '班主任' },
      { name: '年级驾驶舱', desc: '看整个年级的对比和趋势', audience: '年级组长' },
      { name: '德育驾驶舱', desc: '看德育记录、处分、预警的整体情况', audience: '学发、校领导' },
      { name: '教学驾驶舱', desc: '看教学相关数据', audience: '教务、校领导' },
      { name: '监考驾驶舱', desc: '看监考安排的整体情况', audience: '教务' },
      { name: '系统驾驶舱', desc: '看系统运行状态', audience: '系统管理员' },
      { name: '教师工作台', desc: '老师一进来就能看到自己的待办、相关数据', audience: '全体老师' }
    ]
  },
  {
    key: 'moral',
    name: '管学生：德育管理',
    features: [
      { name: '日常表现记录', desc: '记录学生日常好坏表现（加分/扣分），支持批量录入', audience: '班主任、任课老师' },
      { name: '点滴记录', desc: '随手记录学生的闪光瞬间或小问题', audience: '班主任、任课老师' },
      { name: '校级事件', desc: '登记全校性的表彰或违纪事件', audience: '学发' },
      { name: '德育任务', desc: '布置德育任务并记录完成情况', audience: '班主任、学发' },
      { name: '处分管理', desc: '登记、管理、撤销学生处分', audience: '学发' },
      { name: '德育评价', desc: '自动算学生德育分，出评价结果', audience: '班主任、学发' },
      { name: '学期评价', desc: '学期末的综合德育评定', audience: '班主任、学发' },
      { name: '集体评价', desc: '班级等集体的德育评价', audience: '学发' },
      { name: '学生画像', desc: '生成单个学生的综合表现画像', audience: '班主任、心理老师' },
      { name: '一生一册', desc: '学生在校期间的全程成长档案', audience: '班主任、学发' },
      { name: '生日提醒', desc: '学生生日提醒，方便送祝福', audience: '班主任' },
      { name: 'AI 诊疗', desc: '针对学生问题，AI 辅助分析原因、给教育建议', audience: '班主任、心理老师' },
      { name: '导师制', desc: '给学生分配导师，记录谈心谈话', audience: '导师、班主任' },
      { name: '预警名单', desc: '自动筛出需要重点关注的学生', audience: '班主任、学发' },
      { name: '升级规则', desc: '设置问题升级的自动规则（如多次违纪自动上报）', audience: '学发' }
    ]
  },
  {
    key: 'teaching',
    name: '管教学：课程与班级事务',
    features: [
      { name: '课程表', desc: '查看班级/教师课表', audience: '全体老师' },
      { name: '实时课程', desc: '看当前正在上什么课', audience: '全体老师' },
      { name: '更新课表', desc: '上传/更新课表文件', audience: '教务' },
      { name: '班级作业', desc: '发布、查看班级作业', audience: '任课老师、班主任' },
      { name: '班级信息', desc: '维护班级基本信息', audience: '班主任' },
      { name: '班级学生', desc: '查看、管理本班学生名单', audience: '班主任' },
      { name: '班级公告', desc: '发布班级通知公告', audience: '班主任' },
      { name: '延时申请', desc: '学生延时服务申请与审批', audience: '班主任、家长' },
      { name: '请假记录', desc: '学生请假登记与记录', audience: '班主任' },
      { name: '随机点名', desc: '课堂随机点名，活跃气氛', audience: '任课老师' },
      { name: '大声PK', desc: '课堂朗读音量比拼小游戏', audience: '任课老师' }
    ]
  },
  {
    key: 'exam',
    name: '管考试：监考安排',
    features: [
      { name: '监考安排', desc: '排监考表，支持手动排和 Excel 导入，含主监/副监', audience: '教务' },
      { name: '变更通知', desc: '安排有变动时，一键微信通知相关老师（新增/取消/换监）', audience: '教务' },
      { name: '自动提醒', desc: '开考前自动给监考老师发微信提醒（考前 30 分钟起，每 5 分钟一次，共 2 次）', audience: '系统自动' },
      { name: '工作量报表', desc: '导出教师监考工作量（主监/副监场次分开，可按权重折算）', audience: '教务' },
      { name: '权重设置', desc: '设置主监/副监的工作量折算权重', audience: '教务、管理员' }
    ]
  },
  {
    key: 'office',
    name: '帮老师办公：个人事务',
    features: [
      { name: '我的待办', desc: '个人待办事项，到点微信提醒', audience: '全体老师' },
      { name: '待办分组', desc: '按分组管理待办', audience: '全体老师' },
      { name: '教师消息', desc: '接收系统/学校消息', audience: '全体老师' },
      { name: '文件上传/我的文件', desc: '上传、管理自己的文件', audience: '全体老师' },
      { name: '文件管理/已查阅', desc: '收齐并查阅老师提交的文件', audience: '教务' },
      { name: '需求中心', desc: '看系统已有功能（功能大厅）、提交功能建议、跟踪处理进度', audience: '全体老师' }
    ]
  },
  {
    key: 'system',
    name: '管系统：后台管理',
    features: [
      { name: '教师管理', desc: '维护教师账号与信息', audience: '管理员' },
      { name: '成员管理', desc: '管理用户与角色', audience: '管理员' },
      { name: '权限管理', desc: '配置各角色能用哪些功能', audience: '管理员' },
      { name: '系统监控', desc: '查看系统运行与访问情况', audience: '管理员' },
      { name: '系统设置', desc: '全局参数配置', audience: '管理员' }
    ]
  }
]

export const FEATURE_CATALOG_UPDATED = '2026-11-23'
