# -*- coding: utf-8 -*-
"""
德育评价系统数据迁移脚本

从 checkTemplate.xlsx 迁移数据到 MySQL：
- 级号数据
- 班级数据
- 学生数据
- 教师数据
- 创建班级履历记录

运行方式：
    python scripts/migrate_to_mysql.py [--verify] [--dry-run]
"""

import sys
import os
import logging
import argparse
from datetime import datetime, date
import pandas as pd
import re

# 添加 lesson 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from utils.mysql_db import MySQLDatabase, execute_insert, execute_query
from mysql.connector import Error

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataMigrator:
    """数据迁移器"""

    def __init__(self, dry_run: bool = False):
        """
        初始化迁移器

        Args:
            dry_run: 是否只进行模拟运行（不实际写入数据库）
        """
        self.config = Config()
        self.lesson_dir = self.config.get_cross_platform_path("lesson_dir", "lesson.yaml")
        # 模板文件路径使用配置的 lesson_dir
        self.template_file = os.path.join(self.lesson_dir, "checkTemplate.xlsx")
        self.dry_run = dry_run

        # 统计信息
        self.stats = {
            "grades": 0,
            "classes": 0,
            "students": 0,
            "teachers": 0,
            "history": 0,
            "errors": []
        }

    def load_template_data(self) -> dict:
        """
        加载 Excel 模板数据

        Returns:
            dict: 包含 teachers, class, students 的数据
        """
        if not os.path.exists(self.template_file):
            raise FileNotFoundError(f"Template file not found: {self.template_file}")

        logger.info(f"Loading template file: {self.template_file}")

        data = {}

        # 加载教师数据
        try:
            data["teachers"] = pd.read_excel(self.template_file, sheet_name="teachers")
            logger.info(f"Teachers loaded: {len(data['teachers'])} records")
        except Exception as e:
            logger.warning(f"Failed to load teachers sheet: {e}")
            data["teachers"] = pd.DataFrame()

        # 加载班级数据
        try:
            data["class"] = pd.read_excel(self.template_file, sheet_name="class")
            logger.info(f"Classes loaded: {len(data['class'])} records")
        except Exception as e:
            logger.warning(f"Failed to load class sheet: {e}")
            data["class"] = pd.DataFrame()

        # 加载学生数据
        try:
            data["students"] = pd.read_excel(self.template_file, sheet_name="students")
            logger.info(f"Students loaded: {len(data['students'])} records")
        except Exception as e:
            logger.warning(f"Failed to load students sheet: {e}")
            data["students"] = pd.DataFrame()

        return data

    def parse_class_code(self, class_code: str) -> tuple:
        """
        解析班级代码，提取级号和班号

        Args:
            class_code: 班级代码，如 "202301" 或 "高一1班"

        Returns:
            tuple: (enrollment_year, class_number)
        """
        if pd.isna(class_code):
            return None, None

        class_code = str(class_code).strip()

        # 模式1: 数字格式 "202301" = 2023级1班
        match = re.match(r'^(\d{4})(\d{2})$', class_code)
        if match:
            enrollment_year = int(match.group(1))
            class_number = int(match.group(2))
            return enrollment_year, class_number

        # 模式2: 中文格式 "高一1班", "高二3班", "高三日语班"
        # 计算当前年份和年级对应关系（2026年3月）
        # 高一 = 2025年9月入学 = 2025级
        # 高二 = 2024年9月入学 = 2024级
        # 高三 = 2023年9月入学 = 2023级
        current_year = datetime.now().year

        # 年级到入学年份的映射（修正后的正确映射）
        grade_level_map = {
            '高一': current_year - 1,  # 2025级（2025年9月入学）
            '高二': current_year - 2,  # 2024级（2024年9月入学）
            '高三': current_year - 3,  # 2023级（2023年9月入学）
        }

        for grade_level, enrollment_year in grade_level_map.items():
            if grade_level in class_code:
                # 提取班号
                # "高一1班" -> 1, "高三日语1" -> 1, "高二日语" -> 99
                # 先尝试匹配班级末尾的数字（如 "高三日语1" 中的 '1'）
                end_number_match = re.search(r'(\d+)班?$', class_code)
                if end_number_match:
                    class_number = int(end_number_match.group(1))
                else:
                    # 特殊班级如日语班，使用班级名称作为标识
                    class_number = 99  # 特殊班号
                return enrollment_year, class_number

        return None, None

    def parse_class_name(self, class_name: str) -> tuple:
        """
        从班级名称解析级号和班号

        Args:
            class_name: 班级名称，如 "2023级1班" 或 "高一1班"

        Returns:
            tuple: (enrollment_year, class_number)
        """
        if pd.isna(class_name):
            return None, None

        class_name = str(class_name).strip()

        # 模式1: "2023级1班"
        match = re.match(r'^(\d{4})级.*?(\d+)班?$', class_name)
        if match:
            return int(match.group(1)), int(match.group(2))

        # 模式2: "高一1班", "高二3班"
        # 修正后的年级-入学年份映射（2026年3月）
        current_year = datetime.now().year
        grade_level_map = {
            '高一': current_year - 1,  # 2025级
            '高二': current_year - 2,  # 2024级
            '高三': current_year - 3,  # 2023级
        }

        for grade_level, enrollment_year in grade_level_map.items():
            if grade_level in class_name:
                number_match = re.search(r'(\d+)班?$', class_name)
                if number_match:
                    return enrollment_year, int(number_match.group(1))
                return enrollment_year, 99

        return None, None

    def migrate_grades(self, data: dict) -> int:
        """
        迁移级号数据

        Args:
            data: 模板数据

        Returns:
            int: 迁移的级号数量
        """
        grades_set = set()

        # 从班级数据提取级号
        if "class" in data and not data["class"].empty:
            for _, row in data["class"].iterrows():
                class_code = row.get("class_code")
                if pd.notna(class_code):
                    enrollment_year, _ = self.parse_class_code(class_code)
                    if enrollment_year:
                        grades_set.add(enrollment_year)

        # 从学生数据提取级号
        if "students" in data and not data["students"].empty:
            for _, row in data["students"].iterrows():
                sid = row.get("sid")
                if pd.notna(sid):
                    # 学号格式通常以年份开头
                    sid_str = str(sid).strip()
                    if len(sid_str) >= 4:
                        try:
                            year = int(sid_str[:4])
                            if 2020 <= year <= datetime.now().year:
                                grades_set.add(year)
                        except ValueError:
                            pass

        logger.info(f"Found {len(grades_set)} unique grades: {sorted(grades_set)}")

        if self.dry_run:
            logger.info("[DRY RUN] Would insert grades")
            return len(grades_set)

        # 插入级号数据
        count = 0
        with MySQLDatabase() as db:
            for enrollment_year in sorted(grades_set):
                grade_name = f"{enrollment_year}级"
                try:
                    db.execute(
                        "INSERT IGNORE INTO grade (grade_name, enrollment_year) VALUES (%s, %s)",
                        (grade_name, enrollment_year)
                    )
                    if db.cursor.rowcount > 0:
                        count += 1
                        logger.info(f"Grade '{grade_name}' inserted")
                except Error as e:
                    logger.error(f"Failed to insert grade '{grade_name}': {e}")
                    self.stats["errors"].append(f"Grade: {grade_name} - {e}")

        self.stats["grades"] = count
        return count

    def migrate_classes(self, data: dict) -> int:
        """
        迁移班级数据

        Args:
            data: 模板数据

        Returns:
            int: 迁移的班级数量
        """
        if "class" in data and data["class"].empty:
            logger.warning("No class data to migrate")
            return 0

        class_data = data["class"]
        count = 0

        if self.dry_run:
            logger.info(f"[DRY RUN] Would insert {len(class_data)} classes")
            return len(class_data)

        with MySQLDatabase() as db:
            for _, row in class_data.iterrows():
                class_code = row.get("class_code")
                class_name = row.get("class_name", "")
                class_en = row.get("class_en", "")  # 班级英文代码，如 G31
                leaders = row.get("leaders", "")
                active = row.get("active", 1)

                if pd.isna(class_code):
                    continue

                class_code_str = str(class_code).strip() if pd.notna(class_code) else ""
                class_name_str = str(class_name).strip() if pd.notna(class_name) else ""
                class_en_str = str(class_en).strip() if pd.notna(class_en) else ""

                # 尝试从 class_code 或 class_name 解析级号和班号
                enrollment_year, class_number = self.parse_class_code(class_code_str)

                if not enrollment_year:
                    # 尝试从 class_name 解析
                    enrollment_year, class_number = self.parse_class_name(class_name_str)

                # 使用 class_en 字段提取更准确的 class_number（避免日语班冲突）
                # class_en 格式: Gxy，其中 x 是年级(1-3)，y 是班号
                # 如 G31 = 高三1班，G37 = 高三日语1
                if class_en_str and re.match(r'^G\d+$', class_en_str):
                    class_number_from_en = int(class_en_str[2:])  # 提取 y 部分
                    if class_number_from_en > 0:
                        class_number = class_number_from_en

                if not enrollment_year:
                    logger.warning(f"Cannot parse class_code: {class_code_str}")
                    continue

                # 获取级号ID
                grade = db.query_one(
                    "SELECT grade_id FROM grade WHERE enrollment_year = %s",
                    (enrollment_year,)
                )
                if not grade:
                    logger.warning(f"Grade not found for year {enrollment_year}")
                    continue

                grade_id = grade["grade_id"]

                # 使用 class_code 作为 class_name（如果 class_name 为空）
                if not class_name_str:
                    class_name_str = class_code_str

                try:
                    db.execute(
                        """INSERT IGNORE INTO class
                        (class_code, grade_id, class_number, class_name, leader_name, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                        (class_code_str, grade_id, class_number, class_name_str, str(leaders) if pd.notna(leaders) else None, int(active) if pd.notna(active) else 1)
                    )
                    if db.cursor.rowcount > 0:
                        count += 1
                        logger.info(f"Class '{class_name_str}' inserted")
                except Error as e:
                    logger.error(f"Failed to insert class '{class_name_str}': {e}")
                    self.stats["errors"].append(f"Class: {class_name_str} - {e}")

        self.stats["classes"] = count
        return count

    def migrate_students(self, data: dict) -> int:
        """
        迁移学生数据

        Args:
            data: 模板数据

        Returns:
            int: 迁移的学生数量
        """
        if "students" in data and data["students"].empty:
            logger.warning("No student data to migrate")
            return 0

        student_data = data["students"]
        count = 0

        if self.dry_run:
            logger.info(f"[DRY RUN] Would insert {len(student_data)} students")
            return len(student_data)

        with MySQLDatabase() as db:
            for _, row in student_data.iterrows():
                sid = row.get("sid")
                name = row.get("name", "")
                cname = row.get("cname", "")  # 班级名称
                roomid = row.get("roomid")
                rpid = row.get("rpid")
                active = row.get("active", 1)

                if pd.isna(sid):
                    continue

                # 处理学号
                sid_str = str(int(sid)) if isinstance(sid, float) else str(sid)
                name_str = str(name) if pd.notna(name) else ""

                # 从学号提取级号
                enrollment_year = None
                if len(sid_str) >= 4:
                    try:
                        enrollment_year = int(sid_str[:4])
                    except ValueError:
                        pass

                if not enrollment_year:
                    logger.warning(f"Cannot determine grade for student {sid_str}")
                    continue

                # 获取级号ID
                grade = db.query_one(
                    "SELECT grade_id FROM grade WHERE enrollment_year = %s",
                    (enrollment_year,)
                )
                if not grade:
                    logger.warning(f"Grade not found for year {enrollment_year}, student {sid_str}")
                    continue

                grade_id = grade["grade_id"]

                # 获取班级ID
                class_id = None
                # 尝试通过班级名称匹配
                if pd.notna(cname):
                    class_obj = db.query_one(
                        "SELECT class_id FROM class WHERE class_name = %s",
                        (str(cname),)
                    )
                    if class_obj:
                        class_id = class_obj["class_id"]

                # 如果班级名称匹配失败，尝试通过学号推断班号
                if not class_id and len(sid_str) >= 6:
                    try:
                        class_number = int(sid_str[4:6])
                        class_obj = db.query_one(
                            """SELECT class_id FROM class
                            WHERE grade_id = %s AND class_number = %s""",
                            (grade_id, class_number)
                        )
                        if class_obj:
                            class_id = class_obj["class_id"]
                    except ValueError:
                        pass

                if not class_id:
                    logger.warning(f"Class not found for student {sid_str}")
                    continue

                # 处理状态
                status = '在校'
                if pd.notna(active):
                    if int(active) == 0:
                        status = '转出'

                try:
                    db.execute(
                        """INSERT IGNORE INTO student
                        (student_id, name, class_id, grade_id, original_grade_id, roomid, status, enrollment_date, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            sid_str,
                            name_str,
                            class_id,
                            grade_id,
                            grade_id,  # original_grade_id = grade_id
                            str(int(roomid)) if pd.notna(roomid) and isinstance(roomid, float) else (str(roomid) if pd.notna(roomid) else None),
                            status,
                            date(enrollment_year, 9, 1),  # 默认入学日期为9月1日
                            int(active) if pd.notna(active) else 1
                        )
                    )
                    if db.cursor.rowcount > 0:
                        count += 1
                        logger.info(f"Student '{name_str}({sid_str})' inserted")

                        # 创建班级履历记录
                        try:
                            db.execute(
                                """INSERT INTO student_class_history
                                (student_id, class_id, grade_id, start_date, change_reason)
                                VALUES (%s, %s, %s, %s, %s)""",
                                (sid_str, class_id, grade_id, date(enrollment_year, 9, 1), '入学')
                            )
                            self.stats["history"] += 1
                        except Error as e:
                            logger.warning(f"Failed to create history for student {sid_str}: {e}")

                except Error as e:
                    logger.error(f"Failed to insert student '{sid_str}': {e}")
                    self.stats["errors"].append(f"Student: {sid_str} - {e}")

        self.stats["students"] = count
        return count

    def migrate_teachers(self, data: dict) -> int:
        """
        迁移教师数据

        Args:
            data: 模板数据

        Returns:
            int: 迁移的教师数量
        """
        if "teachers" in data and data["teachers"].empty:
            logger.warning("No teacher data to migrate")
            return 0

        teacher_data = data["teachers"]
        count = 0

        if self.dry_run:
            logger.info(f"[DRY RUN] Would insert {len(teacher_data)} teachers")
            return len(teacher_data)

        with MySQLDatabase() as db:
            for _, row in teacher_data.iterrows():
                name = row.get("name")
                subject = row.get("subject", "")
                course = row.get("course", "")
                pwd = row.get("pwd", "")
                role = row.get("role", "teacher")
                level = row.get("level", 0)
                active = row.get("active", 1)
                notice = row.get("notice", 1)
                is_password_changed = row.get("is_password_changed", 0)

                if pd.isna(name):
                    continue

                name_str = str(name)
                # 使用姓名作为 teacher_id（或可以生成工号）
                teacher_id = f"T_{name_str}"

                try:
                    db.execute(
                        """INSERT IGNORE INTO teacher
                        (teacher_id, name, subject, password_hash, role, level, is_active, notice_enabled, is_password_changed)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            teacher_id,
                            name_str,
                            str(subject) if pd.notna(subject) else None,
                            str(pwd) if pd.notna(pwd) else None,
                            str(role) if pd.notna(role) else "teacher",
                            int(level) if pd.notna(level) else 0,
                            int(active) if pd.notna(active) else 1,
                            int(notice) if pd.notna(notice) else 1,
                            int(is_password_changed) if pd.notna(is_password_changed) else 0
                        )
                    )
                    if db.cursor.rowcount > 0:
                        count += 1
                        logger.info(f"Teacher '{name_str}' inserted")
                except Error as e:
                    logger.error(f"Failed to insert teacher '{name_str}': {e}")
                    self.stats["errors"].append(f"Teacher: {name_str} - {e}")

        self.stats["teachers"] = count
        return count

    def create_initial_semester(self) -> int:
        """
        创建初始学年学期配置

        Returns:
            int: 创建的记录数
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would create initial semester data")
            return 0

        current_year = datetime.now().year
        count = 0

        with MySQLDatabase() as db:
            # 创建当前学年
            year_name = f"{current_year}-{current_year + 1}学年"
            try:
                db.execute(
                    """INSERT IGNORE INTO school_year
                    (year_name, start_date, end_date, is_current)
                    VALUES (%s, %s, %s, %s)""",
                    (year_name, date(current_year, 9, 1), date(current_year + 1, 7, 15), 1)
                )
                if db.cursor.rowcount > 0:
                    count += 1
                    logger.info(f"School year '{year_name}' inserted")

                # 获取学年ID
                year = db.query_one(
                    "SELECT year_id FROM school_year WHERE year_name = %s",
                    (year_name,)
                )
                year_id = year["year_id"] if year else None

                if year_id:
                    # 创建上学期
                    semester_name_up = f"{current_year}-{current_year + 1}上"
                    db.execute(
                        """INSERT IGNORE INTO semester
                        (semester_name, year_id, start_date, end_date, status)
                        VALUES (%s, %s, %s, %s, %s)""",
                        (semester_name_up, year_id, date(current_year, 9, 1), date(current_year + 1, 1, 20), 1)
                    )
                    if db.cursor.rowcount > 0:
                        count += 1
                        logger.info(f"Semester '{semester_name_up}' inserted")

                    # 创建下学期
                    semester_name_down = f"{current_year}-{current_year + 1}下"
                    db.execute(
                        """INSERT IGNORE INTO semester
                        (semester_name, year_id, start_date, end_date, status)
                        VALUES (%s, %s, %s, %s, %s)""",
                        (semester_name_down, year_id, date(current_year + 1, 2, 20), date(current_year + 1, 7, 15), 0)
                    )
                    if db.cursor.rowcount > 0:
                        count += 1
                        logger.info(f"Semester '{semester_name_down}' inserted")

            except Error as e:
                logger.error(f"Failed to create semester data: {e}")
                self.stats["errors"].append(f"Semester: {e}")

        return count

    def migrate_all(self) -> dict:
        """
        执行完整迁移

        Returns:
            dict: 迁移统计信息
        """
        logger.info("Starting data migration...")

        # 加载模板数据
        data = self.load_template_data()

        # 创建初始学年学期
        self.create_initial_semester()

        # 按顺序迁移
        self.migrate_grades(data)
        self.migrate_classes(data)
        self.migrate_students(data)
        self.migrate_teachers(data)

        logger.info("Migration completed!")
        logger.info(f"Stats: {self.stats}")

        return self.stats

    def verify_migration(self):
        """
        验证迁移结果
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would verify migration")
            return

        logger.info("Verifying migration results...")

        with MySQLDatabase() as db:
            # 验证级号
            grades_count = db.query_value("SELECT COUNT(*) FROM grade")
            logger.info(f"Grades in database: {grades_count}")

            # 验证班级
            classes_count = db.query_value("SELECT COUNT(*) FROM class")
            logger.info(f"Classes in database: {classes_count}")

            # 验证学生
            students_count = db.query_value("SELECT COUNT(*) FROM student")
            logger.info(f"Students in database: {students_count}")

            # 验证教师
            teachers_count = db.query_value("SELECT COUNT(*) FROM teacher")
            logger.info(f"Teachers in database: {teachers_count}")

            # 验证班级履历
            history_count = db.query_value("SELECT COUNT(*) FROM student_class_history")
            logger.info(f"Student class history: {history_count}")

            # 验证学年学期
            year_count = db.query_value("SELECT COUNT(*) FROM school_year")
            semester_count = db.query_value("SELECT COUNT(*) FROM semester")
            logger.info(f"School years: {year_count}, Semesters: {semester_count}")

            # 检查外键完整性
            orphan_students = db.query_value(
                """SELECT COUNT(*) FROM student s
                WHERE NOT EXISTS (SELECT 1 FROM class c WHERE c.class_id = s.class_id)"""
            )
            if orphan_students > 0:
                logger.warning(f"Orphan students (no matching class): {orphan_students}")

            orphan_history = db.query_value(
                """SELECT COUNT(*) FROM student_class_history sch
                WHERE NOT EXISTS (SELECT 1 FROM student s WHERE s.student_id = sch.student_id)"""
            )
            if orphan_history > 0:
                logger.warning(f"Orphan history records: {orphan_history}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Migrate data from Excel to MySQL for moral evaluation system")
    parser.add_argument("--verify", action="store_true", help="Verify migration results after completion")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without writing to database")
    args = parser.parse_args()

    migrator = DataMigrator(dry_run=args.dry_run)

    try:
        stats = migrator.migrate_all()

        if args.verify and not args.dry_run:
            migrator.verify_migration()

        # 打印统计信息
        print("\n" + "=" * 50)
        print("Migration Statistics")
        print("=" * 50)
        print(f"Grades migrated: {stats['grades']}")
        print(f"Classes migrated: {stats['classes']}")
        print(f"Students migrated: {stats['students']}")
        print(f"Teachers migrated: {stats['teachers']}")
        print(f"History records created: {stats['history']}")
        if stats['errors']:
            print(f"\nErrors ({len(stats['errors'])}):")
            for error in stats['errors'][:10]:
                print(f"  - {error}")
        print("=" * 50)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()