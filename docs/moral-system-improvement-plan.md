# 德育系统功能完善实施方案

## Context

用户反馈德育系统多个模块需要完善：
1. **学期结转**：缺少人工触发、参数配置、权限调整
2. **德育任务**：时间字段缺失、状态逻辑混乱、得分计算问题
3. **升年级功能**：完全没有实现
4. **一生一册**：筛选布局不合理、缺少加减分汇总

---

## 核心方案：德育任务完整逻辑

### 阶段1：任务创建与初始化

**流程**：
```
创建德育任务（grade_id + task_name + score + start_date + end_date + can_carryover）
↓
自动为该年级所有在校学生初始化 student_task_finish 记录：
  - student_id: 该年级所有学生
  - task_id: 新任务
  - year_id: 当前学年
  - status: 0（未完成）
  - current_score: task['score']（原分值）
  - carryover_count: 0
  - is_carried_over: 0
```

**关键改动**：
- 任务创建时批量初始化所有学生记录（不再在首次完成时创建）
- 确保结转能覆盖所有学生

### 阶段2：批量标记完成

**功能**：
```
篛选年级/班级 → 显示未完成学生列表
多选学生 → 批量标记已完成
记录 finish_date, finish_year_id
status: 1（已完成）
权限：admin/xuefa
```

**集体任务优化**：
- 增加"全班批量完成"按钮
- 支持后续调整"是否参与"（可逐个排除）
- 类似集体事件的 distribution 机制

### 阶段3：手动学期结转

**触发方式**：Settings页面手动触发（xuefa/admin权限）

**流程**：
```
筛选当前学年未完成任务（status=0）
检查 can_carryover=1
检查 carryover_count < MAX_CARRYOVER_TIMES
过滤学生状态 = '在校'
↓
执行结转：
  - current_score = current_score × CARRYOVER_FACTOR（可配置，默认60%）
  - carryover_count = carryover_count + 1
  - year_id = 下一年学年
  - is_carried_over = 1
↓
超过最大次数：
  - status = 2（已作废）
```

**参数配置**：
- `carryover_factor`: 结转系数（默认0.60）
- `max_carryover_times`: 最大结转次数（默认2）
- 存储在 `moral_config` 表，前端可配置

### 阶段4：得分计算

**公式**：
```
task_score = SUM(current_score WHERE status=1)
```

**得分场景**：
| 完成时间 | current_score | 实际得分 |
|---------|---------------|---------|
| 高一期间 | 5（原分值） | 5分 |
| 高二期间（结转1次） | 3（5×60%） | 3分 |
| 高三期间（结转2次） | 1.8（5×60%×60%） | 1.8分 |

---

## 表结构扩展

### grade_moral_task 表

**缺失字段修复**：
```sql
ALTER TABLE grade_moral_task ADD COLUMN start_date DATE COMMENT '任务开始日期';
ALTER TABLE grade_moral_task ADD COLUMN end_date DATE COMMENT '任务结束日期';
ALTER TABLE grade_moral_task ADD COLUMN can_carryover TINYINT DEFAULT 1 COMMENT '是否允许结转';
```

**严重bug**：carryover.py 第58行查询 `t.can_carryover`，但表没有这个字段，必须修复。

### grade 表（升年级功能）

```sql
ALTER TABLE grade ADD COLUMN is_archived TINYINT DEFAULT 0 COMMENT '是否已归档';
ALTER TABLE grade ADD COLUMN archived_at DATETIME COMMENT '归档时间';
```

---

## 功能对比与边界

### 德育任务 vs 集体事件

| 维度 | 德育任务 | 集体事件 |
|------|----------|----------|
| **绑定对象** | grade_id（年级） | class_id（班级） |
| **粒度** | 个人任务 | 班级集体 |
| **特点** | 每个学生独立完成状态 | 全班统一加分/扣分 |
| **结转** | ✓ 支持 | ✗ 不支持 |
| **事件类型** | 志愿服务、社会实践 | 班级荣誉、集体违纪 |

**结论**：功能互补不重叠，德育任务负责个人任务追踪，集体事件负责班级荣誉/违纪。

### 集体任务 vs 集体事件

| 维度 | 集体任务（德育任务） | 集体事件 |
|------|---------------------|----------|
| **创建时分配** | 手动选学生 → **改进：全班批量完成** | 自动全班分配 |
| **后续调整** | **需新增：可逐个排除** | 可逐个调整"是否参与" |
| **适用场景** | 需结转的集体活动 | 一次性班级活动 |

**改进方案**：集体任务增加"全班批量完成"按钮 + 可逐个排除机制。

---

## 权限配置

### semester_manage 权限

**当前**：admin + jiaowu
**需求**：改为 xuefa + admin

**修改**：`lesson/models/datas_api/moral/base.py`
```python
'xuefa': {
    'permissions': [
        ...
        'semester_manage',  # 新增
    ]
}
```

---

## 升年级功能

### 核心逻辑

年级层级动态计算，grade_id 不变：
```
years_after_enrollment = 当前年份 - enrollment_year
→ 0=高一, 1=高二, 2=高三
```

**升年级步骤**：
1. 更新 school_year 表的 is_current 标记
2. 高三学生（years_after_enrollment >= 2）→ status='毕业'
3. 对应 grade 记录 → is_archived=1
4. 高一新生入学 → 创建新 grade 记录

---

## 一生一册改进

### 筛选布局重构

**当前**：[班级] [学生] [日期] [事件类型] 放在一起

**改为**：
- 第一层：[班级选择] [学生选择] → 点击"查看档案"
- 第二层：[日期范围] [事件类型] → 篛选该学生的记录

### 加减分汇总显示

新增字段：`score_summary`
- 总分 + 各类型分项 + 处分扣分
- 计算指定时间范围内加减分情况

### 已归档学生查询

- 新增"查看已归档学生"入口
- 支持搜索毕业/转学/休学学生

---

## 实施清单

### Phase 1：后端改动

| 优先级 | 文件 | 改动内容 |
|--------|------|----------|
| P0 | `create_moral_tables.py` | grade_moral_task 表扩展（can_carryover字段） |
| P0 | `task.py` | 创建任务时初始化学生记录 |
| P0 | `task.py` | 批量完成API `/tasks/batch-finish` |
| P1 | `carryover.py` | 参数可配置 + 学生状态过滤 |
| P1 | `base.py` | xuefa 添加 semester_manage 权限 |
| P2 | `admin.py` | 新增升年级API |
| P2 | `create_moral_tables.py` | grade 表扩展（is_archived字段） |
| P3 | `timeline_api.py` | 加减分汇总字段 |

### Phase 2：前端改动

| 优先级 | 文件 | 改动内容 |
|--------|------|----------|
| P0 | `TaskManage.vue` | 时间字段显示 + 批量标记完成UI |
| P1 | `Settings.vue` | 结转触发按钮 + 参数配置 |
| P2 | `Settings.vue` | 升年级按钮 |
| P3 | `LifeBook.vue` | 筛选重构 + 加减分汇总 |
| P3 | `moral.js` | 新API方法 |

---

## 验证方案

### 德育任务流程验证

1. 创建任务 → 自动初始化所有学生未完成记录
2. 批量标记完成 → 选班级，多选学生，一键完成
3. 结转 → Settings页面预览/执行，显示衰减后的分值
4. 得分计算 → 查看学生评价，验证衰减得分正确

### 升年级验证

1. 一键升年级 → 高三学生标记毕业，grade归档
2. 前端过滤 → 默认不显示已归档年级/班级

### 一生一册验证

1. 选择学生 → 点击"查看档案"
2. 日期篛选 → 显示指定范围记录
3. 加减分汇总 → 显示总分和分项
4. 归档查询 → 可搜索毕业学生

---

## API测试

```bash
# 任务批量完成
curl -X POST "http://localhost:14600/api/moral/tasks/batch-finish" \
  -H "Authorization: Bearer $JWT" \
  -d '{"task_id":1,"class_id":1,"student_ids":["001","002","003"]}'

# 结转预览
curl -s "http://localhost:14600/api/moral/carryover/preview" \
  -H "Authorization: Bearer $JWT"

# 升年级预览
curl -s "http://localhost:14600/api/moral/admin/grades/promote/preview" \
  -H "Authorization: Bearer $JWT"
```