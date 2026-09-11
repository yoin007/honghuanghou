# -*- coding: utf-8 -*-
"""生成全合成演示数据（用于录制教程，不含任何真实数据）。

用法：
    cd lesson
    python scripts/generate_demo_data.py

行为：
1. 以 databases/ 下现有库为模板，复制结构与非人员配置到 databases/demo/；
2. 清空所有真实人员数据（学生、教师、记录、日志、微信联系人、消息等）；
3. 从零生成虚构教师、学生和全类型业务数据（德育记录、处分、集体事件、
   评价、画像、待办、监考、作业公告等）；
4. VACUUM 压缩，确保已删除的真实数据不留存在文件未使用页中。

切换方式：在 lesson/config/lesson.yaml 中设置 demo_mode: true，
所有数据库与附件存储将自动指向 databases/demo/（见 utils/db_config.py）。

所有演示账号密码统一为 demo1234（登录用户名 = 教师姓名）。
"""

import json
import os
import random
import re
import shutil
import sqlite3
import string
import sys
from datetime import date, datetime, timedelta

import bcrypt

LESSON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(LESSON_DIR, "databases")
DEMO_DIR = os.path.join(SRC_DIR, "demo")

PASSWORD = "demo1234"
TODAY = date.today()
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

random.seed(20260909)

# ---------------------------------------------------------------------------
# 虚构姓名池
# ---------------------------------------------------------------------------
SURNAMES = list("王李张刘陈杨黄赵周吴徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董潘袁蔡蒋余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤")
GIVEN_CHARS = list("子雨欣怡梓涵一诺思远浩然宇轩萱诗可佳琪墨天佑明志嘉懿晨曦语桐琪宇雅静梦若曦睿泽文静海涛丽华建国玉兰桂英俊杰晓芳海燕晓东婷婷雪梅志强鹏飞婷婷丹丹丽丽洋洋")

NAMES = set()
REAL_NAMES = set()


def load_real_names():
    """从源库收集真实姓名，既用于防随机重名，也用于扫描文本残留"""
    def collect(db, sql):
        con = sqlite3.connect(f"file:{os.path.join(SRC_DIR, db)}?mode=ro", uri=True)
        for (n,) in con.execute(sql):
            if n and 2 <= len(str(n)) <= 4 and re.fullmatch(r"[一-龥]+", str(n)):
                REAL_NAMES.add(str(n))
        con.close()
    collect("moral.db", "SELECT name FROM teacher")
    collect("moral.db", "SELECT name FROM student")
    collect("member.db", "SELECT nick_name FROM contacts")
    collect("member.db", "SELECT remark FROM contacts")
    NAMES.update(REAL_NAMES)  # 生成的虚构姓名不与真实姓名重名


def fake_name():
    while True:
        n = random.choice(SURNAMES) + "".join(random.choice(GIVEN_CHARS) for _ in range(random.choice([1, 2])))
        if n not in NAMES:
            NAMES.add(n)
            return n


def fake_phone():
    return "1" + random.choice("35789") + "".join(random.choice(string.digits) for _ in range(9))


def fake_wxid():
    return "wxid_" + "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(12))


def rand_dt(start, end) -> datetime:
    start_d = start.date() if isinstance(start, datetime) else start
    end_d = end.date() if isinstance(end, datetime) else end
    return datetime.combine(start_d + timedelta(days=random.randint(0, max(0, (end_d - start_d).days))),
                            datetime.min.time().replace(hour=random.randint(7, 21), minute=random.randint(0, 59)))


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# 1. 复制模板库
# ---------------------------------------------------------------------------
def copy_db(name: str):
    src = os.path.join(SRC_DIR, name)
    dst = os.path.join(DEMO_DIR, name)
    if os.path.exists(dst):
        os.remove(dst)
    scon = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    dcon = sqlite3.connect(dst)
    scon.backup(dcon)
    scon.close()
    dcon.close()


def main():
    if not os.path.isdir(SRC_DIR):
        sys.exit(f"数据库目录不存在: {SRC_DIR}")
    load_real_names()
    if os.path.isdir(DEMO_DIR):
        shutil.rmtree(DEMO_DIR)
    os.makedirs(DEMO_DIR)
    os.makedirs(os.path.join(DEMO_DIR, "storage"), exist_ok=True)

    for name in ["moral.db", "member.db", "task.db", "messages.db", "daily.db",
                 "inout.db", "homework.db", "filegather.db", "invigilation.db"]:
        copy_db(name)
    print("模板库已复制到 databases/demo/")

    gen_moral()
    gen_member()
    gen_task()
    gen_messages()
    gen_daily()
    gen_inout()
    gen_homework()
    gen_filegather()
    gen_invigilation()

    for name in ["moral.db", "member.db", "task.db", "messages.db", "daily.db",
                 "inout.db", "homework.db", "filegather.db", "invigilation.db"]:
        con = sqlite3.connect(os.path.join(DEMO_DIR, name))
        con.execute("VACUUM")
        con.close()
    print("VACUUM 完成，已删除数据不残留在文件页中。")
    print("\n演示模式启动后端:  在 lesson/config/lesson.yaml 中设置 demo_mode: true，然后 python main.py")
    print("演示账号:  用户名 = 教师姓名,  密码统一为 demo1234")


# ---------------------------------------------------------------------------
# 2. 德育主库
# ---------------------------------------------------------------------------
def gen_moral():
    db = os.path.join(DEMO_DIR, "moral.db")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # 清空的表（人员数据 / 业务流水 / 含真实信息的杂项）
    clear_tables = [
        "teacher", "student", "student_class_history", "student_status_change",
        "punishment_record", "punishment_revoke_application", "punishment_expire_reminder",
        "collective_event", "collective_event_distribution",
        "moral_evaluation", "moral_operation_log",
        "student_profile", "student_profile_history",
        "birthday_reminder", "student_daily_record", "moment_record",
        "student_school_record", "teacher_teaching_class",
        "teacher_todo_series", "teacher_todo_assignee", "teacher_todo_occurrence",
        "teacher_todo_group", "teacher_todo_group_member", "teacher_todo_reminder_log",
        "pending_daily_record", "record_attachment",
        "semester_evaluation_record", "warning_log", "warning_handle",
        "ai_consultation", "ai_consultation_message",
        "grade_moral_task", "student_task_finish", "task_carryover_log",
        "backup_history",
    ]
    for t in clear_tables:
        cur.execute(f'DELETE FROM "{t}"')

    classes = [dict(r) for r in cur.execute("SELECT * FROM class ORDER BY class_id")]
    grades = {g["grade_id"]: dict(g) for g in cur.execute("SELECT * FROM grade")}
    semesters = [dict(r) for r in cur.execute("SELECT * FROM semester ORDER BY semester_id")]
    cur_sem = next(s for s in semesters if s["status"] == 1)
    prev_sem = semesters[semesters.index(cur_sem) - 1]
    cur_start = date.fromisoformat(cur_sem["start_date"])
    prev_start = date.fromisoformat(prev_sem["start_date"])
    prev_end = date.fromisoformat(prev_sem["end_date"])

    daily_events = [dict(r) for r in cur.execute("SELECT * FROM daily_event_type WHERE is_active=1")]
    school_events = [dict(r) for r in cur.execute("SELECT * FROM school_event_type WHERE is_active=1")]
    honor_events = [e for e in school_events if e["event_type"] == 1]
    violation_events = [e for e in school_events if e["event_type"] == 2]
    punish_cfg = {r["punishment_type"]: r for r in cur.execute("SELECT * FROM punishment_period_config WHERE is_active=1")}
    tag_defs = json.loads(next(r["config_value"] for r in cur.execute(
        "SELECT config_value FROM profile_config WHERE config_key='tag_definitions'")))

    password_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

    # ---- 教师 ----
    courses = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理",
               "体育", "信息技术", "音乐", "美术", "心理健康"]
    teachers = []  # dicts

    def add_teacher(course, role):
        name = fake_name()
        t = {
            "teacher_id": f"T_{name}", "name": name, "wxid": fake_wxid(),
            "subject": f"{course}{name[0]}", "course": course, "role": role,
            "level": 10, "identity_type": "teacher", "birthday": f"{random.randint(1978, 1994)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "password_hash": password_hash, "raw_pwd": PASSWORD,
            "is_password_changed": 0, "is_active": 1,
            "notice_enabled": random.randint(0, 1), "score": 0, "balance": 0,
            "model": "basic/lesson", "ai_flag": 0, "note": "演示账号",
            "created_at": NOW, "updated_at": NOW,
        }
        teachers.append(t)
        return t

    t_admin = add_teacher("管理", "admin")
    t_xuefa = [add_teacher("德育", "xuefa") for _ in range(2)]
    t_jiaowu = add_teacher("教师发展", "jiaowu")
    active_grades = [g for g in grades.values() if not g["is_archived"]]
    t_gleader = {g["grade_id"]: add_teacher(random.choice(["语文", "数学", "英语"]), "g_leader")
                 for g in active_grades}

    active_classes = [c for c in classes if not grades[c["grade_id"]]["is_archived"] and c["is_active"]]
    archived_classes = [c for c in classes if grades[c["grade_id"]]["is_archived"]]
    cleader_of = {}
    for c in active_classes:
        t = add_teacher(random.choice(courses), "cleader")
        cleader_of[c["class_id"]] = t
    plain_teachers = [add_teacher(c, "teacher") for c in courses]

    for t in teachers:
        cur.execute("""INSERT INTO teacher (teacher_id,name,wxid,subject,course,role,level,identity_type,birthday,
                       password_hash,raw_pwd,is_password_changed,is_active,notice_enabled,score,balance,model,ai_flag,
                       note,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (t["teacher_id"], t["name"], t["wxid"], t["subject"], t["course"], t["role"], t["level"],
                     t["identity_type"], t["birthday"], t["password_hash"], t["raw_pwd"], t["is_password_changed"],
                     t["is_active"], t["notice_enabled"], t["score"], t["balance"], t["model"], t["ai_flag"],
                     t["note"], t["created_at"], t["updated_at"]))

    # 班级/年级 负责人字段改为虚构教师
    for c in active_classes:
        t = cleader_of[c["class_id"]]
        cur.execute("UPDATE class SET leader_name=?, leader_ids=?, leader_names=?, leader_wxid=? WHERE class_id=?",
                    (t["name"], t["teacher_id"], t["name"], t["wxid"], c["class_id"]))
    for c in archived_classes:
        cur.execute("UPDATE class SET leader_name=NULL, leader_ids=NULL, leader_names=NULL, leader_wxid=NULL WHERE class_id=?",
                    (c["class_id"],))
    for g in grades.values():
        if g["grade_id"] in t_gleader:
            t = t_gleader[g["grade_id"]]
            cur.execute("UPDATE grade SET leader_ids=?, leader_names=? WHERE grade_id=?",
                        (t["teacher_id"], t["name"], g["grade_id"]))
        else:
            cur.execute("UPDATE grade SET leader_ids=NULL, leader_names=NULL WHERE grade_id=?", (g["grade_id"],))

    # ---- 学生 ----
    students = []  # dicts with class/grade info
    seq_of_year = {}

    def add_student(cls, status):
        g = grades[cls["grade_id"]]
        year = g["enrollment_year"]
        seq_of_year[year] = seq_of_year.get(year, 0) + 1
        sid = f"{year}{seq_of_year[year]:04d}"
        gender = random.choice(["男", "女"])
        byear = year - 7  # 入学约 13 岁
        birthday = f"{byear}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        s = {
            "student_id": sid, "name": fake_name(), "gender": gender,
            "class_id": cls["class_id"], "grade_id": cls["grade_id"],
            "birthday": birthday, "phone": fake_phone() if random.random() < 0.6 else None,
            "email": f"student{sid}@example.com" if random.random() < 0.3 else None,
            "roomid": f"{random.choice('ABCDEF')}{random.randint(101, 608)}" if random.random() < 0.7 else None,
            "rpid": str(random.randint(1, 6)) if random.random() < 0.7 else None,
            "status": status, "status_date": None,
            "enrollment_date": f"{year}-09-01", "is_active": 1,
            "entrance_score": random.randint(480, 620) if year <= 2025 else None,
            "entrance_rank": None,
            "middle_school": f"示范第{random.randint(1, 20)}中学",
            "middle_school_city": random.choice(["本市", "临市", "外地"]),
            "daily_sum": 0.0, "school_sum": 0,
        }
        students.append(s)
        return s

    for c in active_classes:
        for _ in range(random.randint(30, 38)):
            add_student(c, "在校")
        if random.random() < 0.5:
            add_student(c, "转出")
    for c in archived_classes:
        for _ in range(6):
            add_student(c, "毕业")

    for s in students:
        cur.execute("""INSERT INTO student (student_id,name,gender,class_id,grade_id,original_grade_id,roomid,status,
                       status_date,enrollment_date,is_active,birthday,phone,email,entrance_score,entrance_rank,
                       middle_school,middle_school_city,created_at,updated_at,rpid)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (s["student_id"], s["name"], s["gender"], s["class_id"], s["grade_id"], s["grade_id"],
                     s["roomid"], s["status"], s["status_date"], s["enrollment_date"], s["is_active"],
                     s["birthday"], s["phone"], s["email"], s["entrance_score"], s["entrance_rank"],
                     s["middle_school"], s["middle_school_city"], NOW, NOW, s["rpid"]))
        cur.execute("""INSERT INTO student_class_history (student_id,class_id,grade_id,start_date,end_date,change_reason,created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (s["student_id"], s["class_id"], s["grade_id"], s["enrollment_date"], None, "入学", NOW))
    enrolled = [s for s in students if s["status"] == "在校"]

    def class_students(cid):
        return [s for s in enrolled if s["class_id"] == cid]

    def recorder_for(cls):
        r = random.random()
        if r < 0.7:
            return cleader_of[cls["class_id"]]["name"]
        if r < 0.85:
            return random.choice(t_xuefa)["name"]
        return random.choice(plain_teachers)["name"]

    # ---- 日常记录（当前学期 + 上学期，覆盖全部事件类型） ----
    remark_pos = ["", "", "表现突出，提出表扬", "连续多次，值得鼓励", "主动认错，态度良好"]
    remark_neg = ["", "", "已批评教育", "第{n}次提醒", "经谈话后认识到错误", "已联系家长"]
    daily_rows = 0
    for c in active_classes:
        members = class_students(c["class_id"])
        if not members:
            continue
        for sem, start, end, lo, hi in [
            (prev_sem, prev_start, prev_end, 50, 90),
            (cur_sem, cur_start, min(TODAY, date.fromisoformat(cur_sem["end_date"])), 80, 150),
        ]:
            for _ in range(random.randint(lo, hi)):
                ev = random.choices(daily_events, weights=[3 if e["event_type"] == 2 else 2 for e in daily_events])[0]
                stu = random.choice(members)
                rd = rand_dt(start, end)
                remark = random.choice(remark_neg).format(n=random.randint(2, 5)) if ev["event_type"] == 2 else random.choice(remark_pos)
                cur.execute("""INSERT INTO student_daily_record (student_id,event_id,semester_id,record_date,class_id,
                               grade_id,score,remark,recorder,is_deleted,created_at)
                               VALUES (?,?,?,?,?,?,?,?,?,0,?)""",
                            (stu["student_id"], ev["event_id"], sem["semester_id"], rd.date().isoformat(),
                             c["class_id"], c["grade_id"], ev["score"], remark, recorder_for(c), fmt(rd)))
                stu["daily_sum"] += ev["score"]
                daily_rows += 1

    # ---- 校级记录（荣誉 + 违纪） ----
    for c in active_classes:
        members = class_students(c["class_id"])
        if not members:
            continue
        for sem, start, end in [(prev_sem, prev_start, prev_end), (cur_sem, cur_start, TODAY)]:
            for _ in range(random.randint(4, 9)):
                if random.random() < 0.6:
                    ev = random.choice(honor_events)
                    proof, is_deleted = None, 0
                else:
                    ev = random.choice(violation_events)
                    proof = random.choice(["值周老师现场发现", "监控核实", "同学举报核实", "宿舍检查记录"])
                    is_deleted = 1 if random.random() < 0.05 else 0
                stu = random.choice(members)
                rd = rand_dt(start, end)
                cur.execute("""INSERT INTO student_school_record (record_id,student_id,event_id,semester_id,get_date,class_id,
                               grade_id,score,proof,is_deleted,created_at,recorder)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (None, stu["student_id"], ev["event_id"], sem["semester_id"], rd.date().isoformat(),
                             c["class_id"], c["grade_id"], ev["score"], proof, is_deleted, fmt(rd), recorder_for(c)))
                if not is_deleted:
                    stu["school_sum"] += ev["score"]

    # ---- 处分 ----
    serious = [e for e in violation_events if e["event_id"] in (10, 11, 12, 15, 17, 18)]
    level_pool = ["警告", "严重警告", "记过", "记大过", "留校察看"]
    punish_ids = []
    for i in range(22):
        stu = random.choice(enrolled)
        ev = random.choice(serious)
        sem = prev_sem if random.random() < 0.6 else cur_sem
        if sem is prev_sem:
            pd_ = rand_dt(prev_start, prev_end)
        else:
            pd_ = rand_dt(cur_start, TODAY)
        level = random.choice(level_pool[:3] if random.random() < 0.7 else level_pool)
        cfg = punish_cfg.get(level)
        period = cfg["period_days"] if cfg else 90
        revoked = random.random() < 0.2
        reason = f"{ev['event_name']}，{random.choice(['经调查核实', '值班老师发现', '宿管上报'])}"
        cur.execute("""INSERT INTO punishment_record (student_id,event_id,semester_id,punishment_date,class_id,grade_id,
                       score_deduct,level,reason,recorder,is_revoked,revoke_date,revoke_by,revoke_reason,created_at,
                       review_status,expire_date,period_days,can_apply_revoke,revoke_type)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?,0)""",
                    (stu["student_id"], ev["event_id"], sem["semester_id"], pd_.date().isoformat(),
                     stu["class_id"], stu["grade_id"], abs(ev["score"]), level, reason,
                     random.choice(t_xuefa)["name"], 1 if revoked else 0,
                     (pd_ + timedelta(days=period)).strftime("%Y-%m-%d") if revoked else None,
                     random.choice(t_xuefa)["name"] if revoked else None,
                     "考察期内表现良好，予以撤销" if revoked else None,
                     fmt(pd_), (pd_.date() + timedelta(days=period)).isoformat(), period, 1))
        punish_ids.append(cur.lastrowid)
    # 到期提醒（少量未发送）
    for pid in random.sample(punish_ids, 4):
        row = cur.execute("SELECT punishment_date, student_id, expire_date FROM punishment_record WHERE id=?", (pid,)).fetchone()
        cur.execute("""INSERT INTO punishment_expire_reminder (punishment_id,student_id,expire_date,reminder_type,
                       reminder_days,is_sent,sent_at,recipient_type,message,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (pid, row["student_id"], row["expire_date"], "expire", 7, 0, None, "teacher",
                     "处分即将到期，请关注学生后续表现", NOW))

    # ---- 集体事件 ----
    collective_names = [("军训会操优胜", "军训", 3), ("主题黑板报评比一等奖", "班级荣誉", 3), ("校运动会团体第三名", "班级荣誉", 3)]
    for cname, ctype, score in collective_names:
        c = random.choice(active_classes)
        cur.execute("""INSERT INTO collective_event (event_name,event_type,semester_id,event_date,score,description,
                       created_at,class_id,created_by) VALUES (?,?,?,?,?,?,?,?,?)""",
                    (cname, ctype, cur_sem["semester_id"],
                     rand_dt(cur_start, TODAY).date().isoformat(), score, "", NOW, c["class_id"],
                     random.choice(t_xuefa)["name"]))
        eid = cur.lastrowid
        members = class_students(c["class_id"])
        for stu in random.sample(members, min(len(members), random.randint(20, 35))):
            cur.execute("""INSERT INTO collective_event_distribution (event_id,student_id,class_id,score_assigned,
                           is_participant,remark,created_at,recorder) VALUES (?,?,?,?,?,?,?,?)""",
                        (eid, stu["student_id"], c["class_id"], random.randint(1, 3), 1, None, NOW,
                         recorder_for(c)))

    # ---- 德育评价 ----
    def add_evaluation(stu, sem_id, when):
        total = 80 + stu["daily_sum"] * 0.4 + stu["school_sum"] * 0.4 + random.uniform(-3, 3)
        total = round(max(35, min(120, total)), 1)
        level = "优秀" if total >= 90 else "良好" if total >= 75 else "及格" if total >= 60 else "待改进"
        cur.execute("""INSERT INTO moral_evaluation (student_id,semester_id,class_id,grade_id,total_score,level,update_time)
                       VALUES (?,?,?,?,?,?,?)""",
                    (stu["student_id"], sem_id, stu["class_id"], stu["grade_id"], total, level, when))
    for stu in enrolled:
        add_evaluation(stu, cur_sem["semester_id"], NOW)
        if stu["grade_id"] in t_gleader:  # 非毕业年级：生成上学期评价
            saved = stu["daily_sum"], stu["school_sum"]
            stu["daily_sum"] = stu["daily_sum"] * random.uniform(0.5, 0.9)
            stu["school_sum"] = int(stu["school_sum"] * random.uniform(0.4, 0.8))
            add_evaluation(stu, prev_sem["semester_id"], fmt(rand_dt(prev_end, prev_end + timedelta(days=5))))
            stu["daily_sum"], stu["school_sum"] = saved

    # ---- 学生画像 ----
    risk_levels = ["low", "low", "low", "medium", "medium", "high"]
    for stu in random.sample(enrolled, 35):
        risk = random.choice(risk_levels)
        tags = random.sample(tag_defs, random.randint(1, 3))
        strengths = random.sample(tag_defs, random.randint(1, 2))
        improvements = ["待观察"] if risk == "high" else random.sample(tag_defs, 1)
        summary = (f"{stu['name']}同学本学期总体表现"
                   + ("稳定，能遵守校规校纪" if risk == "low" else "有待关注，近期出现多次违纪记录")
                   + "，建议班主任持续跟进。")
        profile_row = {
            "student_id": stu["student_id"], "profile_version": 1, "profile_summary": summary,
            "profile_tags": tags, "strength_tags": strengths, "improvement_tags": improvements,
            "risk_level": risk, "moral_score": random.randint(60, 100), "attitude_score": random.randint(60, 100),
            "social_score": random.randint(55, 100), "growth_score": random.randint(60, 100),
            "suggestions": "保持正向激励，定期谈心谈话" if risk != "high" else "建议学发部介入，制定帮教方案",
            "intervention_priority": 1 if risk == "high" else None,
            "data_source_summary": {"daily_records": "演示数据", "punishments": "演示数据"},
            "generated_by": random.choice(t_xuefa)["name"],
        }
        cur.execute("""INSERT INTO student_profile (student_id,profile_version,profile_summary,profile_tags,strength_tags,
                       improvement_tags,risk_level,moral_score,attitude_score,social_score,growth_score,suggestions,
                       intervention_priority,data_source_summary,generated_at,updated_at,generated_by)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (profile_row["student_id"], 1, summary, json.dumps(tags, ensure_ascii=False),
                     json.dumps(strengths, ensure_ascii=False), json.dumps(improvements, ensure_ascii=False),
                     risk, profile_row["moral_score"], profile_row["attitude_score"], profile_row["social_score"],
                     profile_row["growth_score"], profile_row["suggestions"], profile_row["intervention_priority"],
                     json.dumps(profile_row["data_source_summary"], ensure_ascii=False),
                     NOW, NOW, profile_row["generated_by"]))
        cur.execute("INSERT INTO student_profile_history (student_id,profile_version,profile_data,created_at) VALUES (?,?,?,?)",
                    (stu["student_id"], 1, json.dumps(profile_row, ensure_ascii=False), NOW))

    # ---- 生日提醒（未来 10 天内过生日的在校生） ----
    for stu in enrolled:
        md = (int(stu["birthday"][5:7]), int(stu["birthday"][8:10]))
        for delta in range(0, 11):
            d = TODAY + timedelta(days=delta)
            if (d.month, d.day) == md:
                cls = next(c for c in classes if c["class_id"] == stu["class_id"])
                sent = delta < 3 and random.random() < 0.5
                cur.execute("""INSERT INTO birthday_reminder (student_id,reminder_date,reminder_type,message,is_sent,sent_at,
                               recipient_type,created_at) VALUES (?,?,?,?,?,?,?,?)""",
                            (stu["student_id"], d.isoformat(), "birthday", f"班级公告：{cls['class_name']}",
                             1 if sent else 0, fmt(datetime.combine(d, datetime.min.time().replace(hour=7))) if sent else None,
                             "class", NOW))
                break

    # ---- 重要时刻 ----
    moment_texts = ["主动帮助同学讲解数学题", "运动会报名参加长跑项目", "晚自习状态不佳，已谈话了解",
                    "捡到饭卡主动上交", "课堂展示表现自信", "与同学发生口角，已调解",
                    "主动承担班级大扫除任务", "月考进步明显，予以鼓励"]
    for _ in range(10):
        stu = random.choice(enrolled)
        rd = rand_dt(cur_start, TODAY)
        cur.execute("""INSERT INTO moment_record (student_id,class_id,grade_id,recorder,record_type,content,record_date,
                       is_private,tags,semester_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (stu["student_id"], stu["class_id"], stu["grade_id"],
                     cleader_of[stu["class_id"]]["name"], "moment", random.choice(moment_texts),
                     rd.date().isoformat(), random.randint(0, 1), None, cur_sem["semester_id"], fmt(rd), fmt(rd)))

    # ---- 操作日志（采样） ----
    ops = [("student_daily_record", "新增日常记录"), ("student_daily_record", "删除日常记录"),
           ("punishment_record", "新增处分"), ("punishment_record", "撤销处分"),
           ("student_profile", "生成学生画像"), ("moral_config", "修改评价配置")]
    for _ in range(180):
        t = random.choice(teachers)
        tbl, op = random.choice(ops)
        rd = rand_dt(cur_start, datetime.now())
        cur.execute("""INSERT INTO moral_operation_log (operator,operator_role,operation,table_name,record_id,semester_id,
                       old_data,new_data,reason,ip_address,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (t["name"], t["role"], op, tbl, random.randint(1, 9999), cur_sem["semester_id"],
                     None, None, "", f"10.0.{random.randint(0, 20)}.{random.randint(2, 250)}", fmt(rd)))

    # ---- 任课关系 ----
    def add_teaching(t, cls):
        cur.execute("""INSERT INTO teacher_teaching_class (teacher_id,teacher_name,class_id,subject,is_active,created_at,updated_at)
                       VALUES (?,?,?,?,1,?,?)""",
                    (t["teacher_id"], t["name"], cls["class_id"], t["subject"], NOW, NOW))

    for c in active_classes:
        add_teaching(cleader_of[c["class_id"]], c)
    for g in active_grades:
        for c in active_classes:
            if c["grade_id"] == g["grade_id"]:
                add_teaching(t_gleader[g["grade_id"]], c)
    for t in plain_teachers:
        for c in random.sample(active_classes, random.randint(2, 5)):
            add_teaching(t, c)

    # ---- 教师待办 ----
    group_specs = [("班主任例会组", t_admin, 5), ("德育工作小组", t_xuefa[0], 4), ("高一年级工作组", t_gleader[active_grades[-1]["grade_id"]], 4)]
    for gname, owner, n in group_specs:
        cur.execute("""INSERT INTO teacher_todo_group (owner_teacher_id,group_name,description,is_active,created_at,updated_at)
                       VALUES (?,?,?,1,?,?)""", (owner["teacher_id"], gname, "演示分组", NOW, NOW))
        gid = cur.lastrowid
        for m in random.sample(teachers, n):
            cur.execute("INSERT INTO teacher_todo_group_member (group_id,teacher_id,teacher_name) VALUES (?,?,?)",
                        (gid, m["teacher_id"], m["name"]))

    def add_series(title, desc, todo_type, start, end=None, weekday=None, creator=None):
        creator = creator or random.choice(t_xuefa)
        rule = json.dumps({"unit": "weekly", "weekday": weekday, "day_of_month": None, "month": None, "day": None},
                          ensure_ascii=False) if weekday is not None else None
        cur.execute("""INSERT INTO teacher_todo_series (title,description,creator_teacher_id,creator_name,todo_type,
                       start_date,end_date,recurrence_rule_json,is_active,created_at,updated_at,time_of_day,
                       wechat_notify_enabled,remind_before_minutes,notify_creator,notify_assignees,reminder_interval,reminder_count)
                       VALUES (?,?,?,?,?,?,?,?,1,?,?,?,?,?,?,?,?,?)""",
                    (title, desc, creator["teacher_id"], creator["name"], todo_type, start.isoformat(),
                     end.isoformat() if end else None, rule, NOW, NOW,
                     f"{random.randint(8, 17):02d}:{random.choice(['00', '15', '30'])}",
                     1, random.choice([15, 30, 60]), 1, 1, 2, random.choice([2, 3])))
        sid_ = cur.lastrowid
        assignees = [creator] + random.sample([t for t in teachers if t is not creator], random.randint(1, 3))
        for a in assignees:
            cur.execute("""INSERT INTO teacher_todo_assignee (todo_series_id,teacher_id,teacher_name,created_at)
                           VALUES (?,?,?,?)""", (sid_, a["teacher_id"], a["name"], NOW))
        return sid_, creator, assignees

    d = lambda day: date(2026, 9, day)
    series_specs = [
        ("期初家访收尾", "完成暑期家访记录汇总", "one_off", date(2026, 8, 25), None, None),
        ("月考质量分析会", "备课组统一分析", "weekly", date(2026, 8, 24), None, 1),
        ("主题班会材料提交", "9月主题：行为规范", "one_off", d(15), None, None),
        ("宿舍安全巡查", "重点检查违规电器", "weekly", date(2026, 8, 20), None, 3),
        ("心理健康摸排", "重点关注名单上报", "one_off", d(5), None, None),
        ("升旗仪式整队", "提前10分钟到位", "weekly", date(2026, 8, 19), None, 0),
        ("备课组研讨", "双周教研", "weekly", date(2026, 8, 26), None, 2),
        ("晚自修值班", "第一周值班表", "one_off", TODAY, None, None),
        ("家校联系周报", "每周五发布", "weekly", date(2026, 8, 21), None, 4),
        ("运动会筹备", "10月校运会", "weekly", date(2026, 9, 1), date(2026, 10, 1), 4),
        ("新生学籍核对", "高一年级", "one_off", date(2026, 8, 28), None, None),
        ("德育案例撰写", "月底提交", "one_off", d(28), None, None),
    ]
    occurrence_ids = []
    for title, desc, ttype, start, end, wd in series_specs:
        sid_, creator, assignees = add_series(title, desc, ttype, start, end, wd)
        dates = []
        if ttype == "weekly":
            step_start = max(start, cur_start)
            step = timedelta(days=7)
            cur_d = step_start + timedelta(days=((wd - step_start.weekday()) % 7))
            stop = min(end or (TODAY + timedelta(days=7)), date.fromisoformat(cur_sem["end_date"]))
            while cur_d <= stop:
                dates.append(cur_d)
                cur_d += step
        else:
            dates = [start]
        for od in dates:
            sched = datetime.combine(od, datetime.min.time().replace(hour=8, minute=30))
            if od < TODAY:
                if random.random() < 0.85:
                    status, done, by, overdue = "completed", sched + timedelta(hours=random.randint(1, 8)), random.choice(assignees)["name"], 0
                else:
                    status, done, by, overdue = "pending", None, None, 1
            else:
                status, done, by, overdue = "pending", None, None, 0
            cur.execute("""INSERT INTO teacher_todo_occurrence (todo_series_id,occurrence_date,due_at,status,completed_at,
                           completed_by,created_at,updated_at,scheduled_at,is_overdue) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (sid_, od.isoformat(), None, status, done.strftime("%Y-%m-%d %H:%M:%S") if done else None,
                         by, NOW, NOW, sched.strftime("%Y-%m-%d %H:%M:%S"), overdue))
            occurrence_ids.append((cur.lastrowid, sid_, title, status, sched))

    for oid, sid_, title, status, sched in random.sample(occurrence_ids, min(40, len(occurrence_ids))):
        t = random.choice(teachers)
        is_sent = 1 if sched.date() <= TODAY else 0
        cur.execute("""INSERT INTO teacher_todo_reminder_log (occurrence_id,receiver_teacher_id,channel,planned_remind_at,
                       sent_at,send_status,error_message,created_at,todo_series_id,teacher_id,reminder_type,
                       remind_before_minutes,scheduled_remind_time,actual_remind_time,message,is_sent,reminder_sequence,reminder_interval)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (oid, t["teacher_id"], "wechat", fmt(sched - timedelta(minutes=30)),
                     fmt(sched - timedelta(minutes=30)) if is_sent else None,
                     "sent" if is_sent else "pending", None, NOW, sid_, t["teacher_id"],
                     "overdue" if status == "pending" and sched.date() < TODAY else "upcoming",
                     30, fmt(sched - timedelta(minutes=30)),
                     fmt(sched - timedelta(minutes=30)) if is_sent else None,
                     f"【待办提醒】{title}", is_sent, 1, 2))

    # ---- 待完善记录（无图片） ----
    pending_events = [e for e in daily_events if e["event_type"] == 2]
    for _ in range(6):
        c = random.choice(active_classes)
        ev = random.choice(pending_events)
        done = random.random() < 0.5
        rd = rand_dt(cur_start, datetime.now())
        cur.execute("""INSERT INTO pending_daily_record (class_id,student_count,event_id,teacher_name,record_date,images,
                       remark,is_completed,student_ids,semester_id,grade_id,recorder,created_at,updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (c["class_id"], random.randint(1, 4), ev["event_id"], cleader_of[c["class_id"]]["name"],
                     rd.date().isoformat(), None, "待补充学生名单" if not done else None, 1 if done else 0,
                     None, cur_sem["semester_id"], c["grade_id"], cleader_of[c["class_id"]]["name"], fmt(rd), fmt(rd)))

    # ---- 学期评价（一生一册） ----
    for stu in random.sample(enrolled, 25):
        total = round(max(40, min(115, 80 + stu["daily_sum"] * 0.4 + random.uniform(-2, 2))), 1)
        level = "优秀" if total >= 90 else "良好" if total >= 75 else "及格" if total >= 60 else "待改进"
        summary = {"summary": f"{stu['name']}同学本学期德育表现平稳，总评{total}分，等级{level}。"
                              "能够遵守校规校纪，日常表现稳定，建议保持并争取更大进步。",
                   "strengths": "1. 遵守纪律，无重大违纪记录。2. 学习态度端正。",
                   "improvements": "正向记录数量仍有提升空间，建议主动参与班级事务。",
                   "suggestions": {"student": "主动认领一项班级事务，积累正向记录。",
                                   "teacher": "创造低门槛参与机会，及时给予肯定。",
                                   "parent": "关注情绪状态，营造支持性家庭氛围。"}}
        cur.execute("""INSERT INTO semester_evaluation_record (student_id,semester_id,class_id,grade_id,total_score,level,
                       score_details,statistics,key_events,ai_summary,generated_by,generated_at,ai_generated_at,
                       template_version,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (stu["student_id"], cur_sem["semester_id"], stu["class_id"], stu["grade_id"], total, level,
                     json.dumps({"student_id": stu["student_id"], "semester_id": cur_sem["semester_id"],
                                 "total_score": total, "level": level, "base_score": 80.0,
                                 "daily_score": round(stu["daily_sum"], 1), "school_score": stu["school_sum"],
                                 "task_score": 0, "collective_score": 0, "punishment_score": 0}, ensure_ascii=False),
                     json.dumps({"positive_count": random.randint(1, 12), "negative_count": random.randint(0, 5),
                                 "honor_count": random.randint(0, 3), "punishment_count": 0}, ensure_ascii=False),
                     "[]", json.dumps(summary, ensure_ascii=False),
                     random.choice(t_xuefa)["name"], NOW, NOW, "v1.0", NOW))

    # ---- AI 诊疗 ----
    consult_specs = [
        ("academic", "学业问题诊断", "近期月考成绩下滑明显", "open", "medium"),
        ("behavior", "行为问题诊断", "连续多次宿舍违纪", "in_progress", "high"),
        ("psychology", "心理问题诊断", "近期情绪低落，不愿交流", "resolved", "medium"),
    ]
    for ctype, cname, desc, status, priority in consult_specs:
        stu = random.choice(enrolled)
        creator = cleader_of[stu["class_id"]]
        assignee = random.choice(t_xuefa)
        cur.execute("""INSERT INTO ai_consultation (student_id,consultation_type,title,description,status,priority,creator,
                       assignee,participants,ai_analysis,ai_suggestions,ai_risk_assessment,solution,outcome,
                       follow_up_date,created_at,updated_at,closed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (stu["student_id"], ctype, cname, desc, status, priority, creator["name"], assignee["name"],
                     json.dumps([creator["name"], assignee["name"]], ensure_ascii=False),
                     f"{stu['name']}同学的{desc}，可能原因包括学习方法不当、近期压力偏大或家庭因素，建议班主任先谈心了解具体情况。",
                     json.dumps(["一对一谈心谈话", "制定阶段性小目标", "与家长沟通形成家校合力"], ensure_ascii=False),
                     "中风险" if priority == "medium" else "高风险",
                     "已完成谈话并制定跟进计划" if status == "resolved" else None,
                     "学生情绪好转，愿意主动交流" if status == "resolved" else None,
                     (TODAY + timedelta(days=7)).isoformat() if status != "resolved" else None,
                     fmt(rand_dt(cur_start, datetime.now())), NOW,
                     fmt(datetime.now()) if status == "resolved" else None))
        cid = cur.lastrowid
        msgs = [(creator["name"], f"发起咨询：{desc}"), (assignee["name"], "收到，我先了解一下情况。")]
        if status != "open":
            msgs.append(("ai", "基于现有记录分析：建议关注近期负向事件的时间分布。"))
        if status == "resolved":
            msgs.append((creator["name"], "已与学生面谈，状态明显好转，申请结案。"))
        for sender, content in msgs:
            cur.execute("""INSERT INTO ai_consultation_message (consultation_id,message_type,content,sender,created_at)
                           VALUES (?,?,?,?,?)""",
                        (cid, "ai" if sender == "ai" else "text", content, sender,
                         fmt(rand_dt(cur_start, datetime.now()))))

    con.commit()

    # 统计输出
    counts = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in
              ["teacher", "student", "student_daily_record", "moral_evaluation", "punishment_record",
               "student_profile", "teacher_todo_series", "teacher_todo_occurrence", "semester_evaluation_record"]}
    con.close()
    print("moral.db 演示数据:", counts)
    print("  演示账号: 管理员={}, 学发部={}, 教发部={}".format(
        t_admin["name"], "、".join(t["name"] for t in t_xuefa), t_jiaowu["name"]))
    print("  任一班主任/教师用户名均可登录, 密码统一", PASSWORD)


# ---------------------------------------------------------------------------
# 3. 微信联系人 / 群
# ---------------------------------------------------------------------------
def gen_member():
    db = os.path.join(DEMO_DIR, "member.db")
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("DELETE FROM contacts")
    cur.execute("DELETE FROM chatroom")
    cur.execute("DELETE FROM chatroom_member")
    # 权限配置里的真实微信号清空；含真实姓名或内网地址的示例文本一并清除
    cur.execute("UPDATE permission SET white_list=NULL, black_list=NULL")
    for row in cur.execute("SELECT id, example, reply FROM permission").fetchall():
        pid, example, reply = row
        if example and (any(n in example for n in REAL_NAMES) or "172." in example):
            example = None
        if reply and (any(n in reply for n in REAL_NAMES) or "172." in reply):
            reply = None
        if example is not row[1] or reply is not row[2]:
            cur.execute("UPDATE permission SET example=?, reply=? WHERE id=?", (example, reply, pid))

    wxids = []
    for i in range(25):
        wxid = fake_wxid()
        wxids.append(wxid)
        cur.execute("""INSERT INTO contacts (wxid,wxid_re,remark,nick_name,phone,sex,city,province,country,notes)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (wxid, "", "", fake_name(), fake_phone(), random.choice([0, 1, None]),
                     random.choice(["杭州", "宁波", "温州"]), "浙江", "中国", None))
    rooms = [("demo_room_001", "高二1班家长群"), ("demo_room_002", "高二2班家长群"),
             ("demo_room_003", "高一年级组"), ("demo_room_004", "班主任工作群"),
             ("demo_room_005", "德育工作群")]
    for rid, rname in rooms:
        cur.execute("INSERT INTO chatroom (roomid,room_name) VALUES (?,?)", (rid, rname))
        for w in random.sample(wxids, random.randint(5, 12)):
            nick = fake_name()
            cur.execute("""INSERT INTO chatroom_member (chat_room_id,member_wx_id,name,unique_code,join_timestamp,status,
                           is_deleted,create_time,update_time) VALUES (?,?,?,?,?,?,0,?,?)""",
                        (rid, w, nick, f"demo_{w}", int(datetime.now().timestamp()), 1, NOW, NOW))
    con.commit()
    con.close()
    print("member.db 演示数据: contacts=25, chatroom=5")


# ---------------------------------------------------------------------------
# 4. 调度任务（保留任务定义，清除其中可能的真实教师引用）
# ---------------------------------------------------------------------------
def gen_task():
    db = os.path.join(DEMO_DIR, "task.db")
    con = sqlite3.connect(db)
    cur = con.cursor()
    pat = re.compile(r"T_[一-龥]+")
    rows = cur.execute("SELECT id, args, kwargs, description FROM tasks").fetchall()
    n = 0
    for tid, args, kwargs, desc in rows:
        new_args = pat.sub("T_demo", args or "") or None
        new_kwargs = pat.sub("T_demo", kwargs or "") or None
        new_desc = desc
        if desc and ("调课" in desc or any(name in desc for name in REAL_NAMES)):
            new_desc = "调课提醒（演示数据）" if "调课" in desc else None
        if new_args != args or new_kwargs != kwargs or new_desc != desc:
            cur.execute("UPDATE tasks SET args=?, kwargs=?, description=? WHERE id=?", (new_args, new_kwargs, new_desc, tid))
            n += 1
    con.commit()
    con.close()
    print(f"task.db 调度任务保留 {len(rows)} 条, 清除真实教师引用 {n} 处")


# ---------------------------------------------------------------------------
# 5. 微信消息
# ---------------------------------------------------------------------------
def gen_messages():
    db = os.path.join(DEMO_DIR, "messages.db")
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("DELETE FROM messages")
    senders = ["demo_room_001", "demo_room_002", "demo_room_004"]
    contents = ["收到，明天早上按时到", "作业已发，请查收", "本周班会主题已确定",
                "麻烦各位老师确认一下名单", "好的，谢谢老师", "明天下午三点会议室集合"]
    for i in range(8):
        cur.execute("""INSERT INTO messages (wxid,msg_id,type,sender,roomid,content,thumb,ext,is_at,is_self,is_group,create_time)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (fake_wxid(), f"demo_msg_{i:04d}", 1, fake_name(), random.choice(senders),
                     random.choice(contents), None, None, 0, 0, 1, fmt(rand_dt(TODAY - timedelta(days=7), datetime.now()))))
    con.commit()
    con.close()
    print("messages.db 演示数据: 8 条")


# ---------------------------------------------------------------------------
# 6. 旧版日常 / 请假
# ---------------------------------------------------------------------------
def gen_daily():
    db = os.path.join(DEMO_DIR, "daily.db")
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("DELETE FROM daily")
    demo_students = _demo_student_ids()
    recorders = _demo_teacher_names()
    for _ in range(5):
        cur.execute("INSERT INTO daily (event,sid,note,recorder,style,create_at) VALUES (?,?,?,?,?,?)",
                    ("请假", random.choice(demo_students), "感冒就医", random.choice(recorders), "病假",
                     fmt(rand_dt(TODAY - timedelta(days=10), datetime.now()))))
    con.commit()
    con.close()
    print("daily.db 演示数据: 5 条")


def gen_inout():
    db = os.path.join(DEMO_DIR, "inout.db")
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("DELETE FROM inout")
    demo_students = _demo_student_ids()
    recorders = _demo_teacher_names()
    for i in range(10):
        consumed = random.random() < 0.5
        cur.execute("""INSERT INTO inout (sid,style,days,status,recorder,guard,active,consumer,note,create_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (random.choice(demo_students), random.choice(["事假", "病假"]), random.randint(1, 3),
                     "已销假" if consumed else "待销假", random.choice(recorders), None, 1,
                     random.choice(recorders) if consumed else None,
                     "家中有事" if random.random() < 0.5 else None,
                     fmt(rand_dt(TODAY - timedelta(days=14), datetime.now()))))
    con.commit()
    con.close()
    print("inout.db 演示数据: 10 条")


_demo_cache = {}


def _demo_student_ids():
    if "students" not in _demo_cache:
        con = sqlite3.connect(os.path.join(DEMO_DIR, "moral.db"))
        _demo_cache["students"] = [r[0] for r in con.execute("SELECT student_id FROM student WHERE status='在校'")]
        _demo_cache["teachers"] = [r[0] for r in con.execute("SELECT name FROM teacher")]
        con.close()
    return _demo_cache["students"]


def _demo_teacher_names():
    _demo_student_ids()
    return _demo_cache["teachers"]


# ---------------------------------------------------------------------------
# 7. 作业公告
# ---------------------------------------------------------------------------
def gen_homework():
    db = os.path.join(DEMO_DIR, "homework.db")
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("DELETE FROM announcements")
    demo_students = _demo_student_ids()
    teachers = _demo_teacher_names()
    class_names = ["高二1班", "高二2班", "高二3班", "高二4班", "高二5班", "高二6班", "高三1班", "高一1班"]
    ann = [("数学周末作业", "完成练习册第 3 章，周日晚自习前上交"),
           ("英语听力练习", "完成 Unit 2 听力并跟读"),
           ("物理错题整理", "整理月考错题并订正"),
           ("语文作文", "以‘秋’为题写一篇不少于 800 字的作文")]
    for i in range(14):
        cur.execute("""INSERT INTO announcements (class_code,title,author,content,date,wxid,deleted)
                       VALUES (?,?,?,?,?,?,0)""",
                    (random.choice(class_names), ann[i % len(ann)][0], random.choice(teachers),
                     ann[i % len(ann)][1], fmt(rand_dt(TODAY - timedelta(days=30), datetime.now())), None))
    stu_name_row = sqlite3.connect(os.path.join(DEMO_DIR, "moral.db")).execute(
        "SELECT name, class_id FROM student WHERE student_id=?", (random.choice(demo_students),)).fetchone()
    con.execute("""INSERT INTO announcements (class_code,title,author,content,date,wxid,deleted) VALUES (?,?,?,?,?,?,0)""",
                ("高二1班", "🎂 今日生日提醒", "系统",
                 f"🎂 今日生日提醒\n\n今天是 {stu_name_row[0]} 同学的生日！\n祝生日快乐，学业进步！", NOW, None))
    con.commit()
    con.close()
    print("homework.db 演示数据: 15 条公告")


# ---------------------------------------------------------------------------
# 8. 文件收集
# ---------------------------------------------------------------------------
def gen_filegather():
    db = os.path.join(DEMO_DIR, "filegather.db")
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("DELETE FROM files")
    teachers = _demo_teacher_names()
    names = ["第3周教案.docx", "月考质量分析.xlsx", "主题班会课件.pptx", "家访记录表.pdf",
             "备课组活动记录.docx", "学生名单核对表.xlsx", "德育案例初稿.docx", "听课本扫描.pdf",
             "家长会发言稿.docx", "工作计划表.xlsx"]
    storage = os.path.join(DEMO_DIR, "storage")
    for i, name in enumerate(names):
        rel = f"uploads/202609/{name}"
        cur.execute("""INSERT INTO files (username,original_name,stored_path,content_type,status,uploaded_at,done_at,
                       copies,use_date,month,note) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (random.choice(teachers), name, os.path.join(storage, rel),
                     "application/octet-stream", "done",
                     fmt(rand_dt(TODAY - timedelta(days=20), datetime.now())),
                     fmt(rand_dt(TODAY - timedelta(days=19), datetime.now())),
                     1, TODAY.isoformat(), "202609", None))
    con.commit()
    con.close()
    print("filegather.db 演示数据: 10 条")


# ---------------------------------------------------------------------------
# 9. 监考
# ---------------------------------------------------------------------------
def gen_invigilation():
    db = os.path.join(DEMO_DIR, "invigilation.db")
    con = sqlite3.connect(db)
    cur = con.cursor()
    for t in ["exam_project", "invigilation_slot", "invigilation_notification_log", "invigilation_snapshot"]:
        cur.execute(f'DELETE FROM "{t}"')
    teachers = _demo_teacher_names()
    cur.execute("""INSERT INTO exam_project (name,school_year,semester,start_date,end_date,grade_ids,status,version_no,
                   first_saved_at,notified_at,created_by,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("2026年9月月考", "2026-2027学年", "上学期", "2026-09-20", "2026-09-22", "[2, 3]", "draft", 1,
                 NOW, None, teachers[0], NOW, NOW))
    pid = cur.lastrowid
    subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史"]
    for i, sub in enumerate(subjects):
        t1, t2 = random.sample(teachers, 2)
        cur.execute("""INSERT INTO invigilation_slot (project_id,grade_id,grade_name,exam_date,start_time,end_time,subject,
                       room_name,room_order,teacher_id,teacher_name,teacher_wxid,source,created_at,updated_at,
                       assistant_teacher_id,assistant_teacher_name,assistant_teacher_wxid)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (pid, 3, "2025级", f"2026-09-{20 + i % 3}", "08:30", "10:30", sub,
                     f"第{i + 1}考场", i + 1, f"T_{t1}", t1, fake_wxid(), "manual", NOW, NOW,
                     f"T_{t2}", t2, fake_wxid()))
    cur.execute("""INSERT INTO invigilation_snapshot (project_id,version_no,slots_json,created_at) VALUES (?,?,?,?)""",
                (pid, 1, "[]", NOW))
    for t in random.sample(teachers, 3):
        cur.execute("""INSERT INTO invigilation_notification_log (project_id,version_no,teacher_name,teacher_id,receiver,
                       message,change_type,slots_json,sent_status,error_message,sent_at,queue_row_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (pid, 1, t, f"T_{t}", None, "您有新的监考安排，请查看。", "new", "[]", "sent", None, NOW, None))
    con.commit()
    con.close()
    print("invigilation.db 演示数据: 1 个项目, 8 个监考场次")


if __name__ == "__main__":
    main()
