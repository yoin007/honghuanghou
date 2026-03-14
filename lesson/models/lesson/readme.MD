# lesson

教务管理模块

## lesson.py

课程通知模块

### Lesson类

#### schedule_data函数

##### 参数

1. week_next: int(0)
2. replace_flag: bool(True)
3. ignore:bool(False)

##### 功能

1. 加载xlsx课表文件
2. 调用 format_schedule函数

#### format_schedule函数

##### 参数

    1. df_schedule: 课程表
     2. week_flag: 单/双
     3. replace_flag: bool
     4. ignore:bool

##### 功能

1. 替换`空值` 为`-`,替换中文括号为英文括号
2. 替换所有空白字符
3. 如果replace_flag为True读取替换模版,进行数据替换
4. 如果ignore为True,将ignore的课程替换为`-`
5. 处理单数周课程

## group_send函数

### 功能

读取xlsx文件，实现消息的群发

### xlsx文件字段说明

1. 接收人：教师姓名

2. 类型：消息/课表

3. 消息内容：
   
   1. 如果类型为`消息`, 则 填写 通知内容
   
   2. 如果类型为`课表`， 则 填写 本周课表/下周课表。同时支持接收人填写 班级名称