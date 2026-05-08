# _*_ coding: utf-8 _*_
"""教师、成员、班级联系人查询。

该模块集中处理 teacher 表、Member 通讯录和课表侧 wxid 查询，
避免 Lesson 主类直接承担人员目录职责。
"""

import pandas as pd

from models.manage.member import Member
from utils.teacher_db import (
    create_teacher_record,
    delete_teacher_record,
    get_teachers_dataframe,
    update_teacher_record,
)


class TeacherDirectory:
    """教师与通讯录目录。"""

    def __init__(self, class_provider=None, students_provider=None):
        self.class_provider = class_provider
        self.students_provider = students_provider

    def get_teacher_template(self) -> pd.DataFrame:
        return get_teachers_dataframe()

    def get_members(self) -> pd.DataFrame:
        with Member() as member_db:
            members_list = member_db.member_info()
            if members_list is None:
                return pd.DataFrame()
            columns = member_db.member_columns()
        return pd.DataFrame(members_list, columns=columns)

    def sync_members(self) -> pd.DataFrame:
        with Member() as member_db:
            member_db.update_contacts()
        return self.get_members()

    def member_wxid(self, name: str, active: bool = True, members: pd.DataFrame = None) -> str:
        members = members if members is not None else self.get_members()
        if members is None or members.empty:
            return ""
        if active:
            wxids = members[(members["alias"] == name) & (members["active"] == active)]["wxid"].tolist()
        else:
            wxids = members[members["alias"] == name]["wxid"].tolist()
        return "" if not wxids else wxids[0]

    def get_wxids(
        self,
        name: str,
        notice: bool = True,
        class_template: pd.DataFrame = None,
        teacher_template: pd.DataFrame = None,
        members: pd.DataFrame = None,
    ) -> list:
        wxids = []
        class_template = class_template if class_template is not None else self._get_class_template()
        teacher_template = teacher_template if teacher_template is not None else self.get_teacher_template()

        if class_template is None or teacher_template is None:
            return wxids

        if notice:
            teacher_template = teacher_template.copy()
            teacher_template["notice"] = teacher_template["notice"].astype(int)
            teacher_template = teacher_template[teacher_template["notice"] == 1]

        members = members if members is not None else self.get_members()

        if not class_template.empty and "class_name" in class_template.columns and name in class_template["class_name"].tolist():
            class_leaders = dict(zip(class_template["class_name"], class_template["leaders"]))
            leaders = str(class_leaders.get(name, "")).split("/")
            for leader in leaders:
                wxid = self.member_wxid(leader, active=True, members=members)
                if wxid:
                    wxids.append(wxid)
            return wxids

        if not teacher_template.empty and "name" in teacher_template.columns and name in teacher_template["name"].tolist():
            wxid = self.member_wxid(name, active=True, members=members)
            if wxid:
                wxids.append(wxid)
            return wxids

        return wxids

    def get_sid(self, cname: str, name: str, students: pd.DataFrame = None) -> str:
        students = students if students is not None else self._get_students()
        if students is None or students.empty:
            return ""
        sid = students[(students["cname"] == cname) & (students["name"] == name)]["sid"].tolist()
        return "" if not sid else sid[0]

    def get_alias(self, wxid: str, members: pd.DataFrame = None) -> str:
        members = members if members is not None else self.get_members()
        if members is None or members.empty:
            return ""
        alias = members[members["wxid"] == wxid]["alias"].tolist()
        return "" if not alias else alias[0]

    def add_teacher(self, wxid: str, name: str, subject: str) -> str:
        try:
            default_password = "666666"
            create_teacher_record(
                name=name,
                subject=subject,
                course=subject[:2] if subject else "",
                password_hash=default_password,
                role="teacher",
                level=10,
                notice=1,
                active=1,
                is_password_changed=0,
            )
            if wxid:
                update_teacher_record(name, wxid=wxid)
            return "OK"
        except ValueError as exc:
            return str(exc)

    def delete_teacher(self, name: str) -> str:
        try:
            delete_teacher_record(name)
            return "OK"
        except ValueError as exc:
            return str(exc)

    def _get_class_template(self) -> pd.DataFrame:
        if self.class_provider is None:
            return pd.DataFrame()
        return self.class_provider()

    def _get_students(self) -> pd.DataFrame:
        if self.students_provider is None:
            return pd.DataFrame()
        return self.students_provider()
