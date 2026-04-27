-- MySQL dump 10.13  Distrib 5.7.24, for osx11.1 (x86_64)
--
-- Host: 172.31.25.228    Database: moral_evaluation
-- ------------------------------------------------------
-- Server version	8.0.21

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `ai_consultation`
--

DROP TABLE IF EXISTS `ai_consultation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ai_consultation` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `consultation_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'academic/behavior/psychological/comprehensive',
  `title` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'active' COMMENT 'active/resolved/closed',
  `priority` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'normal' COMMENT 'urgent/high/normal/low',
  `creator` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assignee` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `participants` json DEFAULT NULL,
  `ai_analysis` text COLLATE utf8mb4_unicode_ci COMMENT 'AI分析报告',
  `ai_suggestions` json DEFAULT NULL COMMENT 'AI建议列表',
  `ai_risk_assessment` text COLLATE utf8mb4_unicode_ci COMMENT '风险评估',
  `solution` text COLLATE utf8mb4_unicode_ci,
  `outcome` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `follow_up_date` date DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `closed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_student_status` (`student_id`,`status`),
  CONSTRAINT `ai_consultation_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI诊疗会话表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ai_consultation`
--

LOCK TABLES `ai_consultation` WRITE;
/*!40000 ALTER TABLE `ai_consultation` DISABLE KEYS */;
/*!40000 ALTER TABLE `ai_consultation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ai_consultation_message`
--

DROP TABLE IF EXISTS `ai_consultation_message`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ai_consultation_message` (
  `id` int NOT NULL AUTO_INCREMENT,
  `consultation_id` int NOT NULL,
  `message_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'user/ai/system',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `sender` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_consultation` (`consultation_id`),
  CONSTRAINT `ai_consultation_message_ibfk_1` FOREIGN KEY (`consultation_id`) REFERENCES `ai_consultation` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI诊疗对话记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ai_consultation_message`
--

LOCK TABLES `ai_consultation_message` WRITE;
/*!40000 ALTER TABLE `ai_consultation_message` DISABLE KEYS */;
/*!40000 ALTER TABLE `ai_consultation_message` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `birthday_reminder`
--

DROP TABLE IF EXISTS `birthday_reminder`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `birthday_reminder` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `reminder_date` date NOT NULL COMMENT '提醒日期',
  `reminder_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'birthday' COMMENT 'birthday/special',
  `message` text COLLATE utf8mb4_unicode_ci COMMENT '祝福内容',
  `is_sent` tinyint DEFAULT '0' COMMENT '是否已发送',
  `sent_at` datetime DEFAULT NULL,
  `recipient_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'student/parent/teacher',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  KEY `idx_reminder_date` (`reminder_date`),
  CONSTRAINT `birthday_reminder_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='生日提醒表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `birthday_reminder`
--

LOCK TABLES `birthday_reminder` WRITE;
/*!40000 ALTER TABLE `birthday_reminder` DISABLE KEYS */;
/*!40000 ALTER TABLE `birthday_reminder` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `birthday_reminder_config`
--

DROP TABLE IF EXISTS `birthday_reminder_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `birthday_reminder_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `config_key` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_value` json DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_key` (`config_key`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='生日提醒配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `birthday_reminder_config`
--

LOCK TABLES `birthday_reminder_config` WRITE;
/*!40000 ALTER TABLE `birthday_reminder_config` DISABLE KEYS */;
INSERT INTO `birthday_reminder_config` VALUES (1,'reminder_days_before','3','提前多少天提醒'),(2,'reminder_time','{\"hour\": 8, \"minute\": 0}','提醒时间'),(3,'message_template','{\"parent\": \"您的孩子即将迎来生日，祝家庭幸福美满！\", \"student\": \"祝你生日快乐！愿你学业进步，前程似锦！\"}','祝福模板');
/*!40000 ALTER TABLE `birthday_reminder_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `class`
--

DROP TABLE IF EXISTS `class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `class` (
  `class_id` int NOT NULL AUTO_INCREMENT,
  `class_code` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '班级代码，如：202501（兼容现有系统）',
  `grade_id` int NOT NULL COMMENT '所属级号',
  `class_number` int NOT NULL COMMENT '班号',
  `class_name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '班级名称，如：2025级1班',
  `leader_wxid` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '班主任微信ID',
  `leader_name` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '班主任姓名',
  `roomid` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信班级群ID',
  `is_active` tinyint DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`class_id`),
  UNIQUE KEY `uk_class_code` (`class_code`),
  UNIQUE KEY `uk_grade_class` (`grade_id`,`class_number`),
  CONSTRAINT `class_ibfk_1` FOREIGN KEY (`grade_id`) REFERENCES `grade` (`grade_id`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='班级信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `class`
--

LOCK TABLES `class` WRITE;
/*!40000 ALTER TABLE `class` DISABLE KEYS */;
INSERT INTO `class` VALUES (1,'高一1班',7,1,'高一1班',NULL,'蔡虎诚',NULL,1,'2026-03-29 08:18:48'),(2,'高一2班',7,2,'高一2班',NULL,'刘亚利',NULL,1,'2026-03-29 08:18:48'),(3,'高一3班',7,3,'高一3班',NULL,'祝月永',NULL,1,'2026-03-29 08:18:48'),(4,'高一4班',7,4,'高一4班',NULL,'王心愉',NULL,1,'2026-03-29 08:18:48'),(5,'高一5班',7,5,'高一5班',NULL,'李滨',NULL,1,'2026-03-29 08:18:48'),(6,'高一6班',7,6,'高一6班',NULL,'单俊杰',NULL,1,'2026-03-29 08:18:48'),(7,'高二1班',3,1,'高二1班',NULL,'郭兢业',NULL,1,'2026-03-29 08:18:48'),(8,'高二2班',3,2,'高二2班',NULL,'袁玲',NULL,1,'2026-03-29 08:18:48'),(9,'高二3班',3,3,'高二3班',NULL,'戴建海',NULL,1,'2026-03-29 08:18:48'),(10,'高二4班',3,4,'高二4班',NULL,'刘欣悦',NULL,1,'2026-03-29 08:18:48'),(11,'高二日语',3,99,'高二日语',NULL,'宋文燕',NULL,1,'2026-03-29 08:18:48'),(12,'高三1班',2,1,'高三1班',NULL,'孙晓燕',NULL,1,'2026-03-29 08:18:48'),(13,'高三2班',2,2,'高三2班',NULL,'段雪琪',NULL,1,'2026-03-29 08:18:48'),(14,'高三3班',2,3,'高三3班',NULL,'任秀辉',NULL,1,'2026-03-29 08:18:48'),(15,'高三4班',2,4,'高三4班',NULL,'朱旭',NULL,1,'2026-03-29 08:18:48'),(16,'高三6班',2,6,'高三6班',NULL,'赵慧',NULL,1,'2026-03-29 08:18:48');
/*!40000 ALTER TABLE `class` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `collective_event`
--

DROP TABLE IF EXISTS `collective_event`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `collective_event` (
  `event_id` int NOT NULL AUTO_INCREMENT,
  `event_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '事件名称',
  `event_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '班级荣誉/集体活动/集体违纪',
  `semester_id` int NOT NULL COMMENT '所属学期',
  `event_date` date NOT NULL COMMENT '事件日期',
  `score` int NOT NULL COMMENT '每人得分/扣分',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '事件描述',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`event_id`),
  KEY `semester_id` (`semester_id`),
  CONSTRAINT `collective_event_ibfk_1` FOREIGN KEY (`semester_id`) REFERENCES `semester` (`semester_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='集体事件表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `collective_event`
--

LOCK TABLES `collective_event` WRITE;
/*!40000 ALTER TABLE `collective_event` DISABLE KEYS */;
/*!40000 ALTER TABLE `collective_event` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `collective_event_distribution`
--

DROP TABLE IF EXISTS `collective_event_distribution`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `collective_event_distribution` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_id` int NOT NULL COMMENT '集体事件ID',
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '学生ID',
  `class_id` int NOT NULL COMMENT '学生所属班级',
  `score_assigned` int DEFAULT NULL COMMENT '分配分数',
  `is_participant` tinyint DEFAULT '1' COMMENT '是否实际参与',
  `remark` text COLLATE utf8mb4_unicode_ci COMMENT '备注',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_event_student` (`event_id`,`student_id`),
  KEY `student_id` (`student_id`),
  KEY `class_id` (`class_id`),
  CONSTRAINT `collective_event_distribution_ibfk_1` FOREIGN KEY (`event_id`) REFERENCES `collective_event` (`event_id`),
  CONSTRAINT `collective_event_distribution_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `collective_event_distribution_ibfk_3` FOREIGN KEY (`class_id`) REFERENCES `class` (`class_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='集体事件分配表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `collective_event_distribution`
--

LOCK TABLES `collective_event_distribution` WRITE;
/*!40000 ALTER TABLE `collective_event_distribution` DISABLE KEYS */;
/*!40000 ALTER TABLE `collective_event_distribution` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `daily_event_type`
--

DROP TABLE IF EXISTS `daily_event_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `daily_event_type` (
  `event_id` int NOT NULL AUTO_INCREMENT,
  `event_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_type` tinyint NOT NULL COMMENT '1=积极 2=消极',
  `score` int NOT NULL COMMENT '加分/扣分',
  `description` text COLLATE utf8mb4_unicode_ci,
  `is_active` tinyint DEFAULT '1',
  PRIMARY KEY (`event_id`),
  CONSTRAINT `chk_score_type` CHECK ((((`event_type` = 1) and (`score` > 0)) or ((`event_type` = 2) and (`score` < 0))))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='日常事件类型表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `daily_event_type`
--

LOCK TABLES `daily_event_type` WRITE;
/*!40000 ALTER TABLE `daily_event_type` DISABLE KEYS */;
/*!40000 ALTER TABLE `daily_event_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `data_visibility_config`
--

DROP TABLE IF EXISTS `data_visibility_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `data_visibility_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `visible_roles` json NOT NULL COMMENT '["admin", "xuefa"]',
  `description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据可见性配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `data_visibility_config`
--

LOCK TABLES `data_visibility_config` WRITE;
/*!40000 ALTER TABLE `data_visibility_config` DISABLE KEYS */;
INSERT INTO `data_visibility_config` VALUES (1,'punishment_record','[\"admin\", \"xuefa\", \"jiaowu\"]','处分记录'),(2,'daily_negative','[\"admin\", \"xuefa\", \"jiaowu\", \"cleader\"]','消极事件'),(3,'daily_positive','[\"admin\", \"xuefa\", \"jiaowu\", \"cleader\", \"teacher\"]','积极事件'),(4,'honor_record','[\"admin\", \"xuefa\", \"jiaowu\", \"cleader\", \"teacher\", \"student\", \"parent\"]','荣誉记录'),(5,'evaluation_score','[\"admin\", \"xuefa\", \"jiaowu\", \"cleader\", \"student\", \"parent\"]','评价得分'),(6,'punishment_record','[\"admin\", \"xuefa\", \"jiaowu\"]','处分记录'),(7,'daily_negative','[\"admin\", \"xuefa\", \"jiaowu\", \"cleader\"]','消极事件'),(8,'daily_positive','[\"admin\", \"xuefa\", \"jiaowu\", \"cleader\", \"teacher\"]','积极事件'),(9,'honor_record','[\"admin\", \"xuefa\", \"jiaowu\", \"cleader\", \"teacher\", \"student\", \"parent\"]','荣誉记录'),(10,'evaluation_score','[\"admin\", \"xuefa\", \"jiaowu\", \"cleader\", \"student\", \"parent\"]','评价得分');
/*!40000 ALTER TABLE `data_visibility_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `grade`
--

DROP TABLE IF EXISTS `grade`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `grade` (
  `grade_id` int NOT NULL AUTO_INCREMENT,
  `grade_name` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '如：2025级',
  `enrollment_year` int NOT NULL COMMENT '入学年份',
  PRIMARY KEY (`grade_id`),
  UNIQUE KEY `uk_enrollment_year` (`enrollment_year`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='级号配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `grade`
--

LOCK TABLES `grade` WRITE;
/*!40000 ALTER TABLE `grade` DISABLE KEYS */;
INSERT INTO `grade` VALUES (1,'2023级',2023),(2,'2024级',2024),(3,'2025级',2025),(7,'2026级',2026);
/*!40000 ALTER TABLE `grade` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `grade_level_config`
--

DROP TABLE IF EXISTS `grade_level_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `grade_level_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `years_after_enrollment` int NOT NULL COMMENT '入学后第几年',
  `level_name` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '高一/高二/高三',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_years` (`years_after_enrollment`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='年级等级配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `grade_level_config`
--

LOCK TABLES `grade_level_config` WRITE;
/*!40000 ALTER TABLE `grade_level_config` DISABLE KEYS */;
INSERT INTO `grade_level_config` VALUES (1,0,'高一'),(2,1,'高二'),(3,2,'高三');
/*!40000 ALTER TABLE `grade_level_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `grade_moral_task`
--

DROP TABLE IF EXISTS `grade_moral_task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `grade_moral_task` (
  `task_id` int NOT NULL AUTO_INCREMENT,
  `grade_id` int NOT NULL COMMENT '适用级号',
  `task_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `task_desc` text COLLATE utf8mb4_unicode_ci,
  `score` int NOT NULL COMMENT '完成后获得分数',
  `deadline_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'semester/year/open',
  `is_required` tinyint DEFAULT '1' COMMENT '是否必修',
  `is_active` tinyint DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`),
  KEY `grade_id` (`grade_id`),
  CONSTRAINT `grade_moral_task_ibfk_1` FOREIGN KEY (`grade_id`) REFERENCES `grade` (`grade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='年级德育任务表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `grade_moral_task`
--

LOCK TABLES `grade_moral_task` WRITE;
/*!40000 ALTER TABLE `grade_moral_task` DISABLE KEYS */;
/*!40000 ALTER TABLE `grade_moral_task` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `moral_config`
--

DROP TABLE IF EXISTS `moral_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `moral_config` (
  `config_id` int NOT NULL AUTO_INCREMENT,
  `config_key` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_value` text COLLATE utf8mb4_unicode_ci,
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`config_id`),
  UNIQUE KEY `uk_key` (`config_key`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='德育系统配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `moral_config`
--

LOCK TABLES `moral_config` WRITE;
/*!40000 ALTER TABLE `moral_config` DISABLE KEYS */;
INSERT INTO `moral_config` VALUES (1,'evaluation_base_score','80','德育评价基础分','2026-03-29 20:12:34','2026-03-29 20:12:34'),(2,'birthday_reminder_days','3','生日提前提醒天数','2026-03-29 20:12:34','2026-03-29 20:12:34'),(3,'evaluation_excellent_line','90','优秀评价分数线','2026-03-29 20:12:34','2026-03-29 20:12:34'),(4,'evaluation_good_line','75','良好评价分数线','2026-03-29 20:12:34','2026-03-29 20:12:34'),(5,'evaluation_pass_line','60','及格评价分数线','2026-03-29 20:12:34','2026-03-29 20:12:34'),(6,'daily_record_roles','teacher,cleader','可录入日常记录的角色','2026-03-29 20:12:34','2026-03-29 20:12:34'),(7,'student_profile_roles','admin,jiaowu,xuefa,cleader','可生成学生画像的角色','2026-03-29 20:12:34','2026-03-29 20:12:34'),(8,'ai_consultation_roles','admin,xuefa,cleader','可使用AI诊疗的角色','2026-03-29 20:12:34','2026-03-29 20:12:34'),(9,'birthday_reminder_roles','admin,jiaowu,xuefa,cleader','可管理生日提醒的角色','2026-03-29 20:12:34','2026-03-29 20:12:34'),(10,'semester_carryover_enabled','1','是否启用学期结转','2026-03-29 20:12:34','2026-03-29 20:12:34');
/*!40000 ALTER TABLE `moral_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `moral_evaluation`
--

DROP TABLE IF EXISTS `moral_evaluation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `moral_evaluation` (
  `eval_id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `semester_id` int NOT NULL,
  `class_id` int NOT NULL COMMENT '评价时所属班级',
  `grade_id` int NOT NULL COMMENT '评价时所属级号',
  `total_score` decimal(6,2) DEFAULT '0.00' COMMENT '总分（可超100）',
  `level` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '优秀/良好/合格/不合格',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`eval_id`),
  UNIQUE KEY `uk_student_semester` (`student_id`,`semester_id`),
  KEY `semester_id` (`semester_id`),
  KEY `class_id` (`class_id`),
  KEY `grade_id` (`grade_id`),
  CONSTRAINT `moral_evaluation_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `moral_evaluation_ibfk_2` FOREIGN KEY (`semester_id`) REFERENCES `semester` (`semester_id`),
  CONSTRAINT `moral_evaluation_ibfk_3` FOREIGN KEY (`class_id`) REFERENCES `class` (`class_id`),
  CONSTRAINT `moral_evaluation_ibfk_4` FOREIGN KEY (`grade_id`) REFERENCES `grade` (`grade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='德育评价表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `moral_evaluation`
--

LOCK TABLES `moral_evaluation` WRITE;
/*!40000 ALTER TABLE `moral_evaluation` DISABLE KEYS */;
/*!40000 ALTER TABLE `moral_evaluation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `moral_operation_log`
--

DROP TABLE IF EXISTS `moral_operation_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `moral_operation_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `operator` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `operator_role` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `operation` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'INSERT/UPDATE/DELETE/REVOKE',
  `table_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `record_id` int DEFAULT NULL,
  `semester_id` int DEFAULT NULL,
  `old_data` json DEFAULT NULL,
  `new_data` json DEFAULT NULL,
  `reason` text COLLATE utf8mb4_unicode_ci,
  `ip_address` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_operator` (`operator`),
  KEY `idx_table_record` (`table_name`,`record_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='德育操作日志表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `moral_operation_log`
--

LOCK TABLES `moral_operation_log` WRITE;
/*!40000 ALTER TABLE `moral_operation_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `moral_operation_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `profile_config`
--

DROP TABLE IF EXISTS `profile_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `profile_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `config_key` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_value` json DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_key` (`config_key`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='画像配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `profile_config`
--

LOCK TABLES `profile_config` WRITE;
/*!40000 ALTER TABLE `profile_config` DISABLE KEYS */;
INSERT INTO `profile_config` VALUES (1,'tag_definitions','[\"责任担当\", \"诚实守信\", \"乐于助人\", \"勤奋刻苦\", \"积极进取\", \"团结协作\", \"遵纪守法\", \"文明礼貌\", \"关爱他人\", \"勇于创新\"]','画像标签定义'),(2,'update_frequency','{\"type\": \"semester\", \"min_records\": 5}','更新频率配置'),(3,'risk_thresholds','{\"high\": {\"score_below\": 50, \"negative_count\": 10}, \"medium\": {\"score_below\": 60, \"negative_count\": 5}}','风险阈值配置');
/*!40000 ALTER TABLE `profile_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `punishment_record`
--

DROP TABLE IF EXISTS `punishment_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `punishment_record` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_id` int NOT NULL COMMENT '处分事件类型',
  `semester_id` int NOT NULL,
  `punishment_date` date NOT NULL,
  `class_id` int NOT NULL,
  `grade_id` int NOT NULL,
  `score_deduct` int NOT NULL COMMENT '扣分',
  `level` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '警告/严重警告/记过/留校察看',
  `reason` text COLLATE utf8mb4_unicode_ci,
  `recorder` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_revoked` tinyint DEFAULT '0' COMMENT '是否已撤销',
  `revoke_date` date DEFAULT NULL,
  `revoke_by` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `revoke_reason` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  KEY `event_id` (`event_id`),
  KEY `semester_id` (`semester_id`),
  KEY `class_id` (`class_id`),
  KEY `grade_id` (`grade_id`),
  CONSTRAINT `punishment_record_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `punishment_record_ibfk_2` FOREIGN KEY (`event_id`) REFERENCES `school_event_type` (`event_id`),
  CONSTRAINT `punishment_record_ibfk_3` FOREIGN KEY (`semester_id`) REFERENCES `semester` (`semester_id`),
  CONSTRAINT `punishment_record_ibfk_4` FOREIGN KEY (`class_id`) REFERENCES `class` (`class_id`),
  CONSTRAINT `punishment_record_ibfk_5` FOREIGN KEY (`grade_id`) REFERENCES `grade` (`grade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='处分记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `punishment_record`
--

LOCK TABLES `punishment_record` WRITE;
/*!40000 ALTER TABLE `punishment_record` DISABLE KEYS */;
/*!40000 ALTER TABLE `punishment_record` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `role`
--

DROP TABLE IF EXISTS `role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `role` (
  `role_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role_name` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `role`
--

LOCK TABLES `role` WRITE;
/*!40000 ALTER TABLE `role` DISABLE KEYS */;
INSERT INTO `role` VALUES ('admin','管理员','系统管理员'),('cleader','班主任','班级管理者'),('jiaowu','教发部','教师发展部，负责教学质量、教师管理'),('parent','家长','学生家长'),('student','学生','学生'),('teacher','教师','普通教师'),('xuefa','学发部','学生发展部，负责德育评价');
/*!40000 ALTER TABLE `role` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `school_event_type`
--

DROP TABLE IF EXISTS `school_event_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `school_event_type` (
  `event_id` int NOT NULL AUTO_INCREMENT,
  `event_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_level` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '校级/市级/省级/国家级',
  `event_type` tinyint NOT NULL COMMENT '1=荣誉 2=处分',
  `score` int NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `is_active` tinyint DEFAULT '1',
  PRIMARY KEY (`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='校级事件类型表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `school_event_type`
--

LOCK TABLES `school_event_type` WRITE;
/*!40000 ALTER TABLE `school_event_type` DISABLE KEYS */;
/*!40000 ALTER TABLE `school_event_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `school_year`
--

DROP TABLE IF EXISTS `school_year`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `school_year` (
  `year_id` int NOT NULL AUTO_INCREMENT,
  `year_name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '如：2025-2026学年',
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `is_current` tinyint DEFAULT '0' COMMENT '是否当前学年',
  PRIMARY KEY (`year_id`),
  UNIQUE KEY `uk_year_name` (`year_name`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学年配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `school_year`
--

LOCK TABLES `school_year` WRITE;
/*!40000 ALTER TABLE `school_year` DISABLE KEYS */;
INSERT INTO `school_year` VALUES (1,'2026-2027学年','2026-09-01','2027-07-15',1);
/*!40000 ALTER TABLE `school_year` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `semester`
--

DROP TABLE IF EXISTS `semester`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `semester` (
  `semester_id` int NOT NULL AUTO_INCREMENT,
  `semester_name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '如：2025-2026上',
  `year_id` int NOT NULL COMMENT '所属学年',
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `status` tinyint DEFAULT '1' COMMENT '1=当前学期 0=已结束',
  PRIMARY KEY (`semester_id`),
  UNIQUE KEY `uk_semester_name_year` (`semester_name`,`year_id`),
  KEY `idx_year` (`year_id`),
  CONSTRAINT `semester_ibfk_1` FOREIGN KEY (`year_id`) REFERENCES `school_year` (`year_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学期配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `semester`
--

LOCK TABLES `semester` WRITE;
/*!40000 ALTER TABLE `semester` DISABLE KEYS */;
INSERT INTO `semester` VALUES (1,'2026-2027上',1,'2026-09-01','2027-01-20',1),(2,'2026-2027下',1,'2027-02-20','2027-07-15',0);
/*!40000 ALTER TABLE `semester` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `semester_carryover_config`
--

DROP TABLE IF EXISTS `semester_carryover_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `semester_carryover_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'honor/punishment/task',
  `can_carryover` tinyint DEFAULT '1',
  `score_factor` decimal(3,2) DEFAULT '1.00' COMMENT '结转分值系数',
  `description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学期结转配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `semester_carryover_config`
--

LOCK TABLES `semester_carryover_config` WRITE;
/*!40000 ALTER TABLE `semester_carryover_config` DISABLE KEYS */;
INSERT INTO `semester_carryover_config` VALUES (1,'honor',0,1.00,'荣誉不结转，记录保留在原学期'),(2,'punishment',0,1.00,'处分不结转，记录保留在原学期'),(3,'task_unfinished',1,0.60,'未完成任务可结转，每次×60%'),(4,'honor',0,1.00,'荣誉不结转，记录保留在原学期'),(5,'punishment',0,1.00,'处分不结转，记录保留在原学期'),(6,'task_unfinished',1,0.60,'未完成任务可结转，每次×60%');
/*!40000 ALTER TABLE `semester_carryover_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student`
--

DROP TABLE IF EXISTS `student`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student` (
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '学号',
  `name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gender` enum('男','女') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `class_id` int NOT NULL COMMENT '当前班级ID',
  `grade_id` int NOT NULL COMMENT '当前级号（留级时会变）',
  `original_grade_id` int DEFAULT NULL COMMENT '入学时级号（不变）',
  `roomid` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信ID',
  `status` enum('在校','休学','转出','毕业') COLLATE utf8mb4_unicode_ci DEFAULT '在校' COMMENT '学生状态',
  `status_date` date DEFAULT NULL COMMENT '状态变更日期',
  `enrollment_date` date DEFAULT NULL COMMENT '入学日期',
  `is_active` tinyint DEFAULT '1',
  `birthday` date DEFAULT NULL COMMENT '出生日期',
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系电话',
  `email` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '电子邮箱',
  `entrance_score` decimal(6,2) DEFAULT NULL COMMENT '入学成绩（中考成绩）',
  `entrance_rank` int DEFAULT NULL COMMENT '入学排名',
  `gaokao_score` decimal(6,2) DEFAULT NULL COMMENT '高考成绩',
  `gaokao_year` int DEFAULT NULL COMMENT '高考年份',
  `gaokao_rank` int DEFAULT NULL COMMENT '高考排名',
  `middle_school` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '初中学校名称',
  `middle_school_city` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '初中学校所在城市',
  `university_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '大学院校名称',
  `university_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '院校类型：985/211/一本/二本/专科',
  `university_major` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '录取专业',
  `university_city` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '大学所在城市',
  `profile_summary` text COLLATE utf8mb4_unicode_ci COMMENT '学生画像摘要（AI生成）',
  `profile_tags` json DEFAULT NULL COMMENT '画像标签数组',
  `profile_updated_at` datetime DEFAULT NULL COMMENT '画像更新时间',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`student_id`),
  KEY `class_id` (`class_id`),
  KEY `original_grade_id` (`original_grade_id`),
  KEY `idx_birthday` (`birthday`) COMMENT '生日索引',
  KEY `idx_grade_status` (`grade_id`,`status`) COMMENT '年级状态索引',
  CONSTRAINT `student_ibfk_1` FOREIGN KEY (`class_id`) REFERENCES `class` (`class_id`),
  CONSTRAINT `student_ibfk_2` FOREIGN KEY (`grade_id`) REFERENCES `grade` (`grade_id`),
  CONSTRAINT `student_ibfk_3` FOREIGN KEY (`original_grade_id`) REFERENCES `grade` (`grade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student`
--

LOCK TABLES `student` WRITE;
/*!40000 ALTER TABLE `student` DISABLE KEYS */;
INSERT INTO `student` VALUES ('20232001','曹子馨',NULL,12,1,1,'A518','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232002','陈橹溍',NULL,12,1,1,'A518','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232003','丁根',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232004','丁天馨',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232005','杜吉业',NULL,12,1,1,'A609','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232006','官家豪',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232007','贺梓浚',NULL,12,1,1,'A609','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232008','黄宇航',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232009','黄宇翔',NULL,12,1,1,'A609','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232010','姜文航',NULL,12,1,1,'A632','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232011','姜子宽',NULL,12,1,1,'A609','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232012','李东燕',NULL,12,1,1,'A517','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232013','李铭豪',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232014','李云欣',NULL,12,1,1,'A517','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232015','李泽宇',NULL,12,1,1,'A630','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232016','刘佳琳',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232017','刘濡林',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232018','刘锡卓',NULL,12,1,1,'A630','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232019','刘晓冉',NULL,12,1,1,'A518','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232020','刘晓彤',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232021','宋贵宁',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232022','宋佳奕',NULL,12,1,1,'A520','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232023','苏红宇',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232024','孙月熙',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232025','滕浩宇',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232026','田思齐',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232027','王梦然',NULL,12,1,1,'A517','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232028','王书青',NULL,12,1,1,'A518','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232029','王文博',NULL,12,1,1,'A630','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232030','王依诺',NULL,12,1,1,'A518','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232031','王子涵',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232032','王子和',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232033','徐晓涵',NULL,12,1,1,'A520','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232034','许涵毅',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232035','杨娅楠',NULL,12,1,1,'A518','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232036','阴晓龙',NULL,12,1,1,'A630','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232037','于佳新',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232038','于欣怡',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232039','于哲',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232040','战一卓',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232042','张冬健',NULL,12,1,1,'A632','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232043','张宁',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232044','张玉洁',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232045','张泽东',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232046','赵浩博',NULL,12,1,1,'A630','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232047','赵鑫研',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232048','赵子元',NULL,12,1,1,'A632','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232049','周铄',NULL,12,1,1,'A517','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232050','朱子玥',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232051','高敬端',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232052','高紫琳',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232053','蓝姝怡',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232054','李宗宸',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232055','刘家乐',NULL,12,1,1,'A609','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232056','裴奥扬',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232057','曲润',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232058','陶鑫汝',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232059','王佳翮',NULL,12,1,1,'A517','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232060','许一诺',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232061','叶宸嘉',NULL,13,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232062','傅灵喜',NULL,12,1,1,'A520','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232063','袁榕',NULL,12,1,1,'A518','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232064','刘洪义',NULL,14,1,1,'A634','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232065','刘新睿',NULL,14,1,1,'A606','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232066','王奥',NULL,14,1,1,'A605','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232067','王思维',NULL,14,1,1,'A605','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232068','杨善青',NULL,14,1,1,'A606','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232069','朱文娜',NULL,14,1,1,'A523','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232070','曹业勤',NULL,14,1,1,'A606','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232071','曹一心',NULL,14,1,1,'A523','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232072','丛嘉祺',NULL,14,1,1,'A523','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232073','崔国涛',NULL,14,1,1,'A606','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232074','杜启航',NULL,14,1,1,'A606','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232075','段隆彬',NULL,14,1,1,'A634','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232076','盖基文',NULL,14,1,1,'A634','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232077','贾云超',NULL,12,1,1,'A630','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232078','焦一樊',NULL,12,1,1,'A609','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232079','李雨蒙',NULL,12,1,1,'A517','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232080','刘凌航',NULL,14,1,1,'A634','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232081','刘智全',NULL,14,1,1,'A605','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232082','马多吉加',NULL,14,1,1,'A605','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232083','马鑫锐',NULL,14,1,1,'A605','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232084','任思汝',NULL,14,1,1,'A523','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232085','宋雨婷',NULL,14,1,1,'A523','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232086','孙士博',NULL,14,1,1,'A605','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232087','孙书勤',NULL,12,1,1,'A520','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232088','孙雨辰',NULL,14,1,1,'A634','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232089','王华润',NULL,14,1,1,'A605','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232090','王佳浩',NULL,12,1,1,'A609','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232091','杨雨辰',NULL,14,1,1,'A523','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232092','杨梓淇',NULL,14,1,1,'A523','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232093','臧子文',NULL,14,1,1,'A634','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232094','张慧敏',NULL,14,1,1,'A523','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232095','张嘉诺',NULL,12,1,1,'A517','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232096','张泽瑞',NULL,14,1,1,'A634','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232097','毕琛坤',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232099','陈凯乐',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232100','陈玥',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232101','陈孜昊',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232102','高雅晶',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232103','何东成',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232104','胡振铎',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232105','黄明洋',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232106','季善宇',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232107','蒋可欣',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232108','金娟弘',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232109','李晨菲',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232110','李坤隆',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232111','李林晟',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232112','李奕君',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232113','李原',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232114','林辰',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232115','林文博',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232116','林一帆',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232117','刘浩铭',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232118','刘嘉浩',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232119','刘匡翼',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232120','刘立轩',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232121','刘敏怡',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232122','刘思妤',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232123','刘响慕',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232124','刘宇涵',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232125','卢子通',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232126','罗婉菁',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232128','马牧原',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232129','毛博宁',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232130','邱玺睿',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232131','曲梦竹',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232132','邵永琪',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232133','宋璨甫',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232134','宋依静',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232135','宋紫萱',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232136','隋奇宏',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232137','孙锐',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232138','孙钰霖',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232139','田钊奇',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232140','王晟辰',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232141','王浩然',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232142','王可宣',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232143','王顺顺',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232144','王新玥',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232145','王馨艺',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232146','王鑫怡',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232147','王悠然',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232148','王雨轩',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232149','王子嫣',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232150','闻皓',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232151','肖颖颖',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232152','徐冉',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232153','徐文强',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232154','薛雅馨',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232155','杨阳',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232156','杨子涵',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232157','尹思絮',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232158','于梦雨',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232159','张静怡',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232160','张熙璨',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232161','张小婷',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232162','张晓晗',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232163','张歆若',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232164','郑然',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232165','郑喆',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232166','朱雨晨',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232167','邹紫懿',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232168','毕爱之',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232169','曹薏萱',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232170','邓可馨',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232171','杜盈慧',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232172','纪雅雯',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232173','揭雅斯',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232174','李亚芯',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232175','李越',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232176','林依菲',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232177','史俊涵',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232178','苏畅',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232179','孙奥宣',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232180','田韶阳',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232181','王奥帆',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232182','王晟辉',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232183','姚骅宸',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232184','张遥',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232185','李享',NULL,15,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20232206','蓝玥璐',NULL,16,1,1,'A666','在校',NULL,'2023-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20241001','王子涵',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241002','高敏捷',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241003','姜立轩',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241004','李贤烁',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241005','姜旭荐',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241006','张铠俊',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241007','白梁均',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241008','董波铄',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241009','李世兴',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241010','朱鑫宇',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241011','吴继超',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241012','臧硕',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241013','杨安旭',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241014','朱良栋',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241015','高梓嘉',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241016','蒙卫政',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241017','苏晨',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241018','王腾然',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241019','曲峻毅',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241020','王志绅',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241021','吴书凡',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241022','刘书宏',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241023','张欣怡',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241024','肖智泓',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241025','滕毓涵',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241026','李昊',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241027','肖程豪',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241028','李民贺',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241029','夏坤',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241030','张奥琪',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241031','张淇',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241032','刘柏彤',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241033','宋述为',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241034','马博文',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241035','马语霏',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241036','李玥',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241037','刘钊源',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241038','王茉涵',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241039','宋宜宸',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241040','李琦',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241041','王嘉翔',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241042','杜传振',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241043','杨宸',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241044','徐嘉诚',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241045','张皓然',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20241046','刘家通',NULL,7,2,2,'A888','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242001','孙甲欣',NULL,8,2,2,'A618','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242002','宋霖轩',NULL,8,2,2,'A618','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242003','韩金桐',NULL,8,2,2,'A506','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242004','赵耀',NULL,8,2,2,'A506','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242005','袁锦艺',NULL,8,2,2,'A506','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242006','王景谊',NULL,8,2,2,'A506','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242007','袁子茜',NULL,8,2,2,'A506','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242008','陈子萱',NULL,8,2,2,'A504','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242009','臧欣怡',NULL,8,2,2,'A506','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242010','李昱陆',NULL,8,2,2,'A618','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242011','耿照博',NULL,8,2,2,'A620','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242012','段良凤',NULL,8,2,2,'A505','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242013','孟科璇',NULL,8,2,2,'A618','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242014','徐婧涵',NULL,8,2,2,'A504','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242015','王乐宇',NULL,8,2,2,'A618','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242016','蔡钰彤',NULL,8,2,2,'A504','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242017','周远',NULL,8,2,2,'A621','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242018','亓昱俨',NULL,8,2,2,'A504','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242019','丁哲',NULL,8,2,2,'A621','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242020','梅崇睿',NULL,8,2,2,'A621','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242021','王欣蓥',NULL,8,2,2,'A507','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242022','王允哲',NULL,8,2,2,'A621','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242023','段靖',NULL,8,2,2,'A505','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242024','谢晨阳',NULL,8,2,2,'A620','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242025','张雨荞',NULL,8,2,2,'A505','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242026','张博睿',NULL,8,2,2,'A620','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242027','王艺恒',NULL,8,2,2,'A620','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242028','程许涵',NULL,8,2,2,'A620','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242029','赵洋洋',NULL,8,2,2,'A505','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242030','黄一航',NULL,8,2,2,'A620','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242031','党海滢',NULL,8,2,2,'A507','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242032','黄奕凝',NULL,8,2,2,'A505','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242033','林雅洁',NULL,8,2,2,'A505','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242034','陆嘉琳',NULL,8,2,2,'A507','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242035','王佳怡',NULL,8,2,2,'A504','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242036','王子豪',NULL,8,2,2,'A623','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242037','刘琪钰',NULL,8,2,2,'A504','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242038','张棋',NULL,8,2,2,'A507','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242039','刘煜森',NULL,8,2,2,'A621','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242040','刘国言',NULL,8,2,2,'A620','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20242041','刘丽洋',NULL,8,2,2,'A507','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243001','陈奕含',NULL,9,2,2,'A508','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243002','徐鹏程',NULL,9,2,2,'A622','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243003','李盈盈',NULL,9,2,2,'A622','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243004','王悦如',NULL,9,2,2,'A530','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243005','郝友涵',NULL,9,2,2,'A530','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243006','巩艺欣',NULL,9,2,2,'A508','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243007','曲昇鑫',NULL,9,2,2,'A530','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243008','陈昊林',NULL,9,2,2,'A623','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243009','付娆',NULL,9,2,2,'A530','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243010','潘宸玉',NULL,9,2,2,'A508','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243011','林逸轩',NULL,9,2,2,'A623','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243012','朱梓浩',NULL,9,2,2,'A622','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243013','王子赫',NULL,9,2,2,'A623','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243014','滕明浩',NULL,9,2,2,'A622','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243015','高静琪',NULL,9,2,2,'A508','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243016','王子诚',NULL,9,2,2,'A623','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243017','李雯瑶',NULL,9,2,2,'A508','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243018','薛佳慧',NULL,9,2,2,'A531','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243019','李元登',NULL,9,2,2,'A530','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243020','王娅琦',NULL,9,2,2,'A508','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243021','徐荣嘉',NULL,9,2,2,'A623','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243022','汪俊涵',NULL,9,2,2,'A624','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243023','于雅菲',NULL,9,2,2,'A507','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243024','刘峻鸣',NULL,9,2,2,'A623','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243025','皮李楚萱',NULL,9,2,2,'A508','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243026','张文睿',NULL,9,2,2,'A622','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243027','宋家馨',NULL,9,2,2,'A531','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243028','王璐文',NULL,9,2,2,'A531','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243029','孙梓洲',NULL,9,2,2,'A624','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243030','汪思宇',NULL,9,2,2,'A624','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243031','李振豪',NULL,9,2,2,'A624','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243032','李灏然',NULL,9,2,2,'A531','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243033','李子洁',NULL,9,2,2,'A531','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243034','张笑笑',NULL,9,2,2,'A531','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243035','陈正豪',NULL,9,2,2,'A624','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243036','左祥硕',NULL,9,2,2,'A622','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243037','吕金洺',NULL,9,2,2,'A531','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243038','许晓婉',NULL,9,2,2,'A530','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243039','马伊帆',NULL,9,2,2,'A622','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243040','周姿彤',NULL,9,2,2,'A530','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243041','孙一峰',NULL,9,2,2,'A615','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243042','班迪柯',NULL,9,2,2,'A621','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243043','张晋熔',NULL,9,2,2,'A618','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243044','康晓薇',NULL,9,2,2,'A506','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243045','蒋梦洁',NULL,9,2,2,'A507','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20243046','邓心怡',NULL,9,2,2,'A505','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244001','陈欣逸',NULL,10,2,2,'A532','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244002','顾雅萱',NULL,10,2,2,'A532','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244003','袁同奥',NULL,10,2,2,'A625','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244004','姜添棋',NULL,10,2,2,'A534','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244005','王清仪',NULL,10,2,2,'A532','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244006','尹治锦',NULL,10,2,2,'A625','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244007','刘钰萱',NULL,10,2,2,'A534','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244008','杨浩冉',NULL,10,2,2,'A533','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244009','王彦鸿',NULL,10,2,2,'A625','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244010','于可',NULL,10,2,2,'A533','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244011','姚佳欣',NULL,10,2,2,'A534','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244012','刘千筠',NULL,10,2,2,'A534','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244013','唐琳涵',NULL,10,2,2,'A534','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244014','黄敬震',NULL,10,2,2,'A625','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244015','刘文喆',NULL,10,2,2,'A625','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244016','黄晓涵',NULL,10,2,2,'A534','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244017','臧天悦',NULL,10,2,2,'A625','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244018','张馨湉',NULL,10,2,2,'A532','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244019','孟凡竣',NULL,10,2,2,'A626','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244020','赵晨旭',NULL,10,2,2,'A626','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:48','2026-03-29 08:18:48'),('20244021','范文钰',NULL,10,2,2,'A626','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244022','李佳璇',NULL,10,2,2,'A533','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244023','刘宇硕',NULL,10,2,2,'A626','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244024','姚家程',NULL,10,2,2,'A533','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244025','田永雷',NULL,10,2,2,'A626','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244026','刘瑞晰',NULL,10,2,2,'A532','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244027','李冠晔',NULL,10,2,2,'A626','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244028','杜泉睿',NULL,10,2,2,'A533','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244029','许梦雪',NULL,10,2,2,'A535','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244030','刘一璠',NULL,10,2,2,'A535','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244031','鲁延硕',NULL,10,2,2,'A625','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244032','田克申',NULL,10,2,2,'A626','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244033','苗子清',NULL,10,2,2,'A535','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244034','杨宝沣',NULL,10,2,2,'A625','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244035','刘笑然',NULL,10,2,2,'A533','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244036','刘雅萌',NULL,10,2,2,'A535','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244037','蒋艺菲',NULL,10,2,2,'A533','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244038','刘昱妃',NULL,10,2,2,'A535','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244039','秦健翔',NULL,10,2,2,'A626','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244040','李豪哲',NULL,10,2,2,NULL,'在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244041','戴丽婷',NULL,10,2,2,'A535','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244042','韩玺茹',NULL,10,2,2,'A535','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244043','刘毓哲',NULL,10,2,2,'A535','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20244044','高子乔',NULL,10,2,2,'A532','在校',NULL,'2024-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250001','安仲秀',NULL,2,3,3,'B505','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250002','白圆凤',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250003','毕功坚',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250004','毕艺娴',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250005','卞悠然',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250006','曹骏轩',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250007','曹潇卿',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250008','曾紫暄',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250009','陈一涵',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250010','陈奕璇',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250011','陈兆宇',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250012','迟熹',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250013','楚奕晨',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250014','戴彬燕',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250015','戴愉晓',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250016','董佳辉',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250017','董瑞琦',NULL,2,3,3,'B506','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250018','董昕蕊',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250019','范昱含',NULL,1,3,3,'B502','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250020','房禹彤',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250021','房泽霖',NULL,1,3,3,'B402','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250022','高隽程',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250023','高梦琪',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250024','高洋',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250025','高艺玮',NULL,1,3,3,'B502','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250026','高子淳',NULL,1,3,3,'B404','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250027','高梓恒',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250028','葛曦晨',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250029','郭佳乐',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250030','郭嘉羿',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250031','郭锡琳',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250032','郭宇阳',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250033','郭珍奕',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250034','国明阳',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250035','韩少岗',NULL,1,3,3,'B403','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250036','韩馨瑶',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250037','韩砚博',NULL,2,3,3,'B404','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250038','韩羽皓',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250039','何微琪',NULL,2,3,3,'B505','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250040','侯玥润',NULL,2,3,3,'B404','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250041','胡瑞鸿',NULL,1,3,3,'B402','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250042','黄文博',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250043','黄小涵',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250044','姬语涵',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250045','贾茗云',NULL,1,3,3,'B501','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250046','姜佳音',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250047','姜仁文',NULL,2,3,3,'B405','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250048','姜尚硕',NULL,2,3,3,'B406','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250049','姜懿馨',NULL,1,3,3,'B503','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250050','解雨凡',NULL,1,3,3,'B403','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250051','巨欣艳',NULL,2,3,3,'B501','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250052','兰佳禾',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250053','冷昕蔚',NULL,1,3,3,'B502','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250054','黎笑彤',NULL,1,3,3,'B503','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250055','李广娟',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250056','李翰林',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250057','李佳辉',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250058','李佳宜',NULL,1,3,3,'B502','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250059','李嘉轩',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250060','李俊昭',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250061','李立鑫',NULL,2,3,3,'B506','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250062','李敏佳',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250063','李倩',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250064','李睿东',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250065','李润',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250066','李腾',NULL,2,3,3,'B404','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250067','李腾楠',NULL,2,3,3,'B405','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250068','李欣怡',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250069','李怡好',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250070','李奕萱',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250071','李悠然',NULL,1,3,3,'B501','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250072','李源哲',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250073','李宗骏',NULL,1,3,3,'B404','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250074','梁超越',NULL,2,3,3,'B406','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250075','梁冬梅',NULL,2,3,3,'B506','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250076','梁腾翔',NULL,1,3,3,'B503','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250077','梁忆彤',NULL,2,3,3,'B505','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250078','林智',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250079','刘畅',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250080','刘恩俊',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250081','刘光明',NULL,1,3,3,'B402','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250082','刘国豪',NULL,2,3,3,'B406','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250083','刘赫',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250084','刘佳倩',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250085','刘家瑞',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250086','刘嘉豪',NULL,2,3,3,'B405','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250087','刘俊豪',NULL,1,3,3,'B403','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250088','刘峻赫',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250089','刘理博',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250090','刘梦琪',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250091','刘绍彤',NULL,2,3,3,'B505','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250092','刘世邦',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250093','刘笑冉',NULL,1,3,3,'B502','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250094','刘心凯',NULL,1,3,3,'B403','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250095','刘奕彤',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250096','刘姿含',NULL,2,3,3,'B506','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250097','刘子钰',NULL,2,3,3,'B505','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250098','刘梓琳',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250099','吕俊楠',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250100','马刘靖怡',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250101','马明昊',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250102','马婷婷',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250103','马依娜',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250104','马跃',NULL,2,3,3,'B506','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250105','聂新蕊',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250106','彭琳',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250107','彭哲宇',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250108','齐文洋',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250109','邱振烨',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250110','曲萱儿',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250111','曲祖均',NULL,2,3,3,'B406','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250112','师永强',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250113','石乐萱',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250114','石砚洋',NULL,1,3,3,'B402','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250115','舒俊羲',NULL,1,3,3,'B403','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250116','宋浩冉',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250117','宋何玉麟',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250118','宋佳隆',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250119','宋佳昕',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250120','宋茂源',NULL,2,3,3,'B406','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250121','宋其硕',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250122','宋欣儒',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250123','苏琛沣',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250124','苏子涵',NULL,1,3,3,'B502','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250125','苏子媛',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250126','孙安泽',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250127','孙基峰',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250128','孙丽彤',NULL,1,3,3,'B503','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250129','孙鲁同',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250130','孙曼芯',NULL,1,3,3,'B501','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250131','孙孝磊',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250132','孙子媛',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250133','唐鸿杰',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250134','陶鸿旭  ',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250135','王安奇',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250136','王晨睿',NULL,2,3,3,'B505','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250137','王春洋',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250138','王凤仪',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250139','王涵',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250140','王鸿锐',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250141','王吉冉',NULL,1,3,3,'B402','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250142','王婧涵',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250143','王敬一',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250144','王羚毓',NULL,2,3,3,'B506','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250145','王率溥',NULL,1,3,3,'B402','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250146','王梦妍',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250147','王启瑞',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250148','王睿滕',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250149','王睿兴',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250150','王若心',NULL,1,3,3,'B503','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250151','王胜楠',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250152','王树奇',NULL,1,3,3,'B403','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250153','王田雨',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250154','王文聪',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250155','王玺婷',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250156','王向南',NULL,2,3,3,'B404','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250157','王筱雅',NULL,2,3,3,'B501','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250158','王心言',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250159','王叙贺',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250160','王雅淇',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250161','王雅琪',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250162','王叶潼',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250163','王一涵',NULL,2,3,3,'B506','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250164','王一航',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250165','王艺橦',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250166','王玉儿',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250167','王岳松',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250168','王子健',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250169','王子瑄',NULL,2,3,3,'B406','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250170','王梓贺',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250171','王梓杨',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250172','魏治宇',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250173','温朔巍',NULL,2,3,3,'B505','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250174','吴笑成',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250175','吴宇航',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250176','武星宇',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250177','项田瑾',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250178','谢梦滢',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250179','辛璟祺',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250180','辛明萱',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250181','辛翘羽',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250182','邢耘嘉',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250183','邢智美',NULL,2,3,3,'B506','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250184','熊梓涵',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250185','徐銘',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250186','徐一峰',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250187','徐允浩',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250188','许昊崧',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250189','许嘉瑞',NULL,2,3,3,'B405','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250190','许轶松',NULL,1,3,3,'B503','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250191','许知行',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250192','闫梦凡',NULL,2,3,3,'B404','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250193','严任强',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250194','杨睿霖',NULL,6,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250195','姚佳宜',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250196','易筱静',NULL,2,3,3,'B505','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250197','尹越',NULL,1,3,3,'B503','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250198','于福冉',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250199','于欣妮',NULL,1,3,3,'B503','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250200','于子豪',NULL,1,3,3,'B403','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250201','虞镇羽',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250202','臧依峻',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250203','张涵',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250204','张翰晨',NULL,2,3,3,'B405','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250205','张惠泽',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250206','张锦哲',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250207','张明昕',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250208','张茹',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250209','张诗榆',NULL,1,3,3,'B502','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250210','张天骐',NULL,2,3,3,'B405','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250211','张曦月',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250212','张馨蕊',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250213','张轩嘉',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250214','张雅琪',NULL,2,3,3,'B505','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250215','张祎睿',NULL,2,3,3,'B405','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250216','张英婵',NULL,1,3,3,'B501','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250217','赵世翔',NULL,1,3,3,'B402','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250218','赵潭',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250219','赵祥廷',NULL,1,3,3,'B402','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250220','赵一凡',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250221','赵誉竣',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250222','赵泽臻',NULL,1,3,3,'B403','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250223','郑慕紫',NULL,3,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250224','郑淇文',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250225','郑鑫泽',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250226','朱泓舟',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250227','朱俊毅',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250228','朱雅琦',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250229','朱怡然',NULL,1,3,3,'B502','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49'),('20250230','朱姿羽',NULL,5,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:50','2026-03-29 08:18:50'),('20250231','朱紫薇',NULL,4,3,3,'B888','在校',NULL,'2025-09-01',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-03-29 08:18:49','2026-03-29 08:18:49');
/*!40000 ALTER TABLE `student` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_class_history`
--

DROP TABLE IF EXISTS `student_class_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student_class_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `class_id` int NOT NULL COMMENT '班级ID',
  `grade_id` int NOT NULL COMMENT '当时的级号',
  `start_date` date NOT NULL COMMENT '生效开始日期',
  `end_date` date DEFAULT NULL COMMENT '生效结束日期，NULL=当前',
  `change_reason` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '入学/调班/留级/复学/转入',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `class_id` (`class_id`),
  KEY `grade_id` (`grade_id`),
  KEY `idx_student_date` (`student_id`,`start_date`,`end_date`),
  CONSTRAINT `student_class_history_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `student_class_history_ibfk_2` FOREIGN KEY (`class_id`) REFERENCES `class` (`class_id`),
  CONSTRAINT `student_class_history_ibfk_3` FOREIGN KEY (`grade_id`) REFERENCES `grade` (`grade_id`)
) ENGINE=InnoDB AUTO_INCREMENT=592 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生班级履历表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_class_history`
--

LOCK TABLES `student_class_history` WRITE;
/*!40000 ALTER TABLE `student_class_history` DISABLE KEYS */;
INSERT INTO `student_class_history` VALUES (1,'20241001',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(2,'20241002',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(3,'20241003',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(4,'20241004',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(5,'20241005',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(6,'20241006',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(7,'20241007',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(8,'20241008',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(9,'20241009',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(10,'20241010',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(11,'20241011',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(12,'20241012',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(13,'20241013',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(14,'20241014',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(15,'20241015',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(16,'20241016',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(17,'20241017',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(18,'20241018',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(19,'20241019',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(20,'20241020',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(21,'20241021',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(22,'20241022',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(23,'20241023',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(24,'20241024',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(25,'20241025',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(26,'20241026',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(27,'20241027',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(28,'20241028',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(29,'20241029',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(30,'20241030',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(31,'20241031',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(32,'20241032',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(33,'20241033',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(34,'20241034',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(35,'20241035',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(36,'20241036',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(37,'20241037',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(38,'20241038',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(39,'20241039',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(40,'20241040',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(41,'20241041',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(42,'20241042',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(43,'20241043',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(44,'20241044',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(45,'20241045',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(46,'20241046',7,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(47,'20242001',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(48,'20242002',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(49,'20242003',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(50,'20242004',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(51,'20242005',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(52,'20242006',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(53,'20242007',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(54,'20242008',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(55,'20242009',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(56,'20242010',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(57,'20242011',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(58,'20242012',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(59,'20242013',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(60,'20242014',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(61,'20242015',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(62,'20242016',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(63,'20242017',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(64,'20242018',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(65,'20242019',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(66,'20242020',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(67,'20242021',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(68,'20242022',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(69,'20242023',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(70,'20242024',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(71,'20242025',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(72,'20242026',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(73,'20242027',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(74,'20242028',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(75,'20242029',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(76,'20242030',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(77,'20242031',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(78,'20242032',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(79,'20242033',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(80,'20242034',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(81,'20242035',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(82,'20242036',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(83,'20242037',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(84,'20242038',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(85,'20242039',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(86,'20242040',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(87,'20242041',8,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(88,'20243001',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(89,'20243002',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(90,'20243003',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(91,'20243004',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(92,'20243005',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(93,'20243006',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(94,'20243007',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(95,'20243008',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(96,'20243009',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(97,'20243010',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(98,'20243011',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(99,'20243012',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(100,'20243013',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(101,'20243014',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(102,'20243015',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(103,'20243016',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(104,'20243017',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(105,'20243018',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(106,'20243019',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(107,'20243020',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(108,'20243021',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(109,'20243022',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(110,'20243023',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(111,'20243024',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(112,'20243025',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(113,'20243026',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(114,'20243027',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(115,'20243028',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(116,'20243029',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(117,'20243030',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(118,'20243031',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(119,'20243032',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(120,'20243033',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(121,'20243034',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(122,'20243035',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(123,'20243036',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(124,'20243037',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(125,'20243038',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(126,'20243039',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(127,'20243040',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(128,'20243041',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(129,'20243042',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(130,'20243043',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(131,'20243044',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(132,'20243045',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(133,'20243046',9,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(134,'20244001',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(135,'20244002',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(136,'20244003',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(137,'20244004',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(138,'20244005',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(139,'20244006',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(140,'20244007',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(141,'20244008',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(142,'20244009',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(143,'20244010',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(144,'20244011',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(145,'20244012',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(146,'20244013',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(147,'20244014',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(148,'20244015',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(149,'20244016',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(150,'20244017',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(151,'20244018',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(152,'20244019',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:48'),(153,'20244020',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(154,'20244021',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(155,'20244022',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(156,'20244023',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(157,'20244024',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(158,'20244025',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(159,'20244026',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(160,'20244027',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(161,'20244028',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(162,'20244029',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(163,'20244030',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(164,'20244031',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(165,'20244032',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(166,'20244033',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(167,'20244034',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(168,'20244035',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(169,'20244036',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(170,'20244037',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(171,'20244038',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(172,'20244039',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(173,'20244040',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(174,'20244041',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(175,'20244042',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(176,'20244043',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(177,'20244044',10,2,'2024-09-01',NULL,'入学','2026-03-29 08:18:49'),(178,'20232001',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(179,'20232002',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(180,'20232005',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(181,'20232007',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(182,'20232009',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(183,'20232010',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(184,'20232011',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(185,'20232012',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(186,'20232014',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(187,'20232015',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(188,'20232018',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(189,'20232019',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(190,'20232022',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(191,'20232027',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(192,'20232028',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(193,'20232029',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(194,'20232030',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(195,'20232033',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(196,'20232035',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(197,'20232036',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(198,'20232042',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(199,'20232046',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(200,'20232048',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(201,'20232049',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(202,'20232055',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(203,'20232059',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(204,'20232062',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(205,'20232063',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(206,'20232077',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(207,'20232078',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(208,'20232079',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(209,'20232087',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(210,'20232090',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(211,'20232095',12,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(212,'20232003',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(213,'20232004',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(214,'20232006',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(215,'20232008',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(216,'20232013',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(217,'20232016',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(218,'20232017',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(219,'20232020',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(220,'20232021',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(221,'20232023',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(222,'20232024',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(223,'20232025',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(224,'20232026',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(225,'20232031',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(226,'20232032',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(227,'20232034',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(228,'20232037',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(229,'20232038',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(230,'20232039',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(231,'20232040',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(232,'20232043',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(233,'20232044',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(234,'20232045',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(235,'20232047',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(236,'20232050',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(237,'20232051',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(238,'20232052',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(239,'20232053',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(240,'20232054',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(241,'20232056',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(242,'20232057',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(243,'20232058',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(244,'20232060',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(245,'20232061',13,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(246,'20232064',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(247,'20232065',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(248,'20232066',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(249,'20232067',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(250,'20232068',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(251,'20232069',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(252,'20232070',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(253,'20232071',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(254,'20232072',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(255,'20232073',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(256,'20232074',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(257,'20232075',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(258,'20232076',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(259,'20232080',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(260,'20232081',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(261,'20232082',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(262,'20232083',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(263,'20232084',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(264,'20232085',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(265,'20232086',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(266,'20232088',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(267,'20232089',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(268,'20232091',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(269,'20232092',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(270,'20232093',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(271,'20232094',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(272,'20232096',14,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(273,'20232097',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(274,'20232099',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(275,'20232100',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(276,'20232103',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(277,'20232107',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(278,'20232109',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(279,'20232115',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(280,'20232116',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(281,'20232118',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(282,'20232119',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(283,'20232120',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(284,'20232122',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(285,'20232123',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(286,'20232126',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(287,'20232129',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(288,'20232130',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(289,'20232131',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(290,'20232134',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(291,'20232136',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(292,'20232137',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(293,'20232139',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(294,'20232142',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(295,'20232149',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(296,'20232150',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(297,'20232151',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(298,'20232157',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(299,'20232159',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(300,'20232160',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(301,'20232161',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(302,'20232162',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(303,'20232163',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(304,'20232165',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(305,'20232166',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(306,'20232171',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(307,'20232172',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(308,'20232173',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(309,'20232174',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(310,'20232175',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(311,'20232177',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(312,'20232178',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(313,'20232179',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(314,'20232181',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(315,'20232185',15,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(316,'20232101',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(317,'20232102',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(318,'20232104',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(319,'20232105',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(320,'20232106',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(321,'20232108',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(322,'20232110',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(323,'20232111',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(324,'20232112',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(325,'20232113',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(326,'20232114',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(327,'20232117',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(328,'20232121',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(329,'20232124',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(330,'20232125',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(331,'20232128',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(332,'20232132',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(333,'20232133',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(334,'20232135',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(335,'20232138',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(336,'20232140',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(337,'20232141',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(338,'20232143',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(339,'20232144',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(340,'20232145',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(341,'20232146',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(342,'20232147',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(343,'20232148',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(344,'20232152',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(345,'20232153',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(346,'20232154',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(347,'20232155',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(348,'20232156',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(349,'20232158',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(350,'20232164',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(351,'20232167',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(352,'20232168',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(353,'20232169',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(354,'20232170',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(355,'20232176',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(356,'20232180',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(357,'20232182',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(358,'20232183',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(359,'20232184',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(360,'20232206',16,1,'2023-09-01',NULL,'入学','2026-03-29 08:18:49'),(361,'20250019',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(362,'20250021',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(363,'20250025',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(364,'20250026',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(365,'20250035',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(366,'20250041',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(367,'20250045',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(368,'20250049',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(369,'20250050',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(370,'20250053',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(371,'20250054',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(372,'20250058',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(373,'20250071',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(374,'20250073',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(375,'20250076',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(376,'20250081',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(377,'20250087',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(378,'20250093',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(379,'20250094',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(380,'20250114',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(381,'20250115',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(382,'20250124',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(383,'20250128',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(384,'20250130',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(385,'20250141',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(386,'20250145',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(387,'20250150',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(388,'20250152',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(389,'20250190',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(390,'20250197',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(391,'20250199',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(392,'20250200',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(393,'20250209',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(394,'20250216',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(395,'20250217',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(396,'20250219',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(397,'20250222',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(398,'20250229',1,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(399,'20250001',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(400,'20250017',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(401,'20250037',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(402,'20250039',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(403,'20250040',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(404,'20250047',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(405,'20250048',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(406,'20250051',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(407,'20250061',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(408,'20250066',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(409,'20250067',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(410,'20250074',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(411,'20250075',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(412,'20250077',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(413,'20250082',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(414,'20250086',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(415,'20250091',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(416,'20250096',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(417,'20250097',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(418,'20250104',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(419,'20250111',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(420,'20250120',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(421,'20250136',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(422,'20250144',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(423,'20250156',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(424,'20250157',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(425,'20250163',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(426,'20250169',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(427,'20250173',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(428,'20250183',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(429,'20250189',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(430,'20250192',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(431,'20250196',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(432,'20250204',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(433,'20250210',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(434,'20250214',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(435,'20250215',2,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(436,'20250002',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(437,'20250005',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(438,'20250008',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(439,'20250013',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(440,'20250024',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(441,'20250028',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(442,'20250031',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(443,'20250055',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(444,'20250056',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(445,'20250057',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(446,'20250059',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(447,'20250072',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(448,'20250079',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(449,'20250080',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(450,'20250105',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(451,'20250106',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(452,'20250110',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(453,'20250116',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(454,'20250118',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(455,'20250119',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(456,'20250123',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(457,'20250126',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(458,'20250134',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(459,'20250137',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(460,'20250147',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(461,'20250168',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(462,'20250171',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(463,'20250172',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(464,'20250174',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(465,'20250175',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(466,'20250177',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(467,'20250179',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(468,'20250182',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(469,'20250185',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(470,'20250198',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(471,'20250202',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(472,'20250206',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(473,'20250208',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(474,'20250212',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(475,'20250213',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(476,'20250218',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(477,'20250223',3,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(478,'20250003',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(479,'20250004',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(480,'20250006',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(481,'20250015',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(482,'20250016',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(483,'20250018',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(484,'20250022',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(485,'20250032',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(486,'20250033',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(487,'20250043',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(488,'20250063',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(489,'20250064',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(490,'20250083',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(491,'20250085',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(492,'20250089',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(493,'20250098',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(494,'20250103',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(495,'20250109',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(496,'20250112',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(497,'20250121',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(498,'20250125',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(499,'20250131',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(500,'20250138',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(501,'20250140',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(502,'20250149',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(503,'20250151',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(504,'20250155',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(505,'20250161',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(506,'20250162',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(507,'20250164',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(508,'20250167',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(509,'20250176',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(510,'20250187',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(511,'20250191',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(512,'20250211',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(513,'20250220',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(514,'20250224',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(515,'20250225',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(516,'20250227',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(517,'20250228',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(518,'20250231',4,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(519,'20250009',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(520,'20250010',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(521,'20250012',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(522,'20250034',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(523,'20250044',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(524,'20250046',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(525,'20250052',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(526,'20250060',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(527,'20250062',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(528,'20250069',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(529,'20250078',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(530,'20250084',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(531,'20250088',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(532,'20250092',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(533,'20250099',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(534,'20250101',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(535,'20250102',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(536,'20250107',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(537,'20250113',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(538,'20250122',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(539,'20250127',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(540,'20250133',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(541,'20250139',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(542,'20250143',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:49'),(543,'20250146',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(544,'20250159',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(545,'20250165',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(546,'20250166',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(547,'20250178',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(548,'20250180',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(549,'20250181',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(550,'20250184',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(551,'20250188',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(552,'20250193',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(553,'20250195',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(554,'20250201',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(555,'20250203',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(556,'20250205',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(557,'20250207',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(558,'20250221',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(559,'20250226',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(560,'20250230',5,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(561,'20250007',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(562,'20250011',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(563,'20250014',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(564,'20250020',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(565,'20250023',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(566,'20250027',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(567,'20250029',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(568,'20250030',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(569,'20250036',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(570,'20250038',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(571,'20250042',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(572,'20250065',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(573,'20250068',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(574,'20250070',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(575,'20250090',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(576,'20250095',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(577,'20250100',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(578,'20250108',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(579,'20250117',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(580,'20250129',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(581,'20250132',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(582,'20250135',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(583,'20250142',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(584,'20250148',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(585,'20250153',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(586,'20250154',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(587,'20250158',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(588,'20250160',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(589,'20250170',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(590,'20250186',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50'),(591,'20250194',6,3,'2025-09-01',NULL,'入学','2026-03-29 08:18:50');
/*!40000 ALTER TABLE `student_class_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_daily_record`
--

DROP TABLE IF EXISTS `student_daily_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student_daily_record` (
  `record_id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_id` int NOT NULL,
  `semester_id` int NOT NULL,
  `record_date` date NOT NULL,
  `class_id` int NOT NULL COMMENT '记录时所属班级（快照）',
  `grade_id` int NOT NULL COMMENT '记录时所属级号（快照）',
  `score` int DEFAULT NULL COMMENT '得分/扣分（冗余）',
  `remark` text COLLATE utf8mb4_unicode_ci,
  `recorder` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_deleted` tinyint DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`record_id`),
  UNIQUE KEY `uk_student_event_date` (`student_id`,`event_id`,`record_date`,`semester_id`),
  KEY `event_id` (`event_id`),
  KEY `semester_id` (`semester_id`),
  KEY `class_id` (`class_id`),
  KEY `grade_id` (`grade_id`),
  KEY `idx_student_semester` (`student_id`,`semester_id`),
  CONSTRAINT `student_daily_record_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `student_daily_record_ibfk_2` FOREIGN KEY (`event_id`) REFERENCES `daily_event_type` (`event_id`),
  CONSTRAINT `student_daily_record_ibfk_3` FOREIGN KEY (`semester_id`) REFERENCES `semester` (`semester_id`),
  CONSTRAINT `student_daily_record_ibfk_4` FOREIGN KEY (`class_id`) REFERENCES `class` (`class_id`),
  CONSTRAINT `student_daily_record_ibfk_5` FOREIGN KEY (`grade_id`) REFERENCES `grade` (`grade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生日常表现记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_daily_record`
--

LOCK TABLES `student_daily_record` WRITE;
/*!40000 ALTER TABLE `student_daily_record` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_daily_record` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_profile`
--

DROP TABLE IF EXISTS `student_profile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student_profile` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `profile_version` int DEFAULT '1',
  `profile_summary` text COLLATE utf8mb4_unicode_ci COMMENT '画像摘要',
  `profile_tags` json DEFAULT NULL COMMENT '画像标签数组',
  `strength_tags` json DEFAULT NULL COMMENT '优势标签',
  `improvement_tags` json DEFAULT NULL COMMENT '待改进标签',
  `risk_level` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '风险等级：low/medium/high',
  `moral_score` decimal(5,2) DEFAULT NULL COMMENT '品德评分',
  `attitude_score` decimal(5,2) DEFAULT NULL COMMENT '态度评分',
  `social_score` decimal(5,2) DEFAULT NULL COMMENT '社交评分',
  `growth_score` decimal(5,2) DEFAULT NULL COMMENT '成长评分',
  `suggestions` text COLLATE utf8mb4_unicode_ci COMMENT '个性化建议',
  `intervention_priority` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '干预优先级',
  `data_source_summary` json DEFAULT NULL COMMENT '数据来源统计',
  `generated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_version` (`student_id`,`profile_version`),
  CONSTRAINT `student_profile_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生画像表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_profile`
--

LOCK TABLES `student_profile` WRITE;
/*!40000 ALTER TABLE `student_profile` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_profile` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_profile_history`
--

DROP TABLE IF EXISTS `student_profile_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student_profile_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `profile_version` int NOT NULL,
  `profile_data` json DEFAULT NULL COMMENT '完整画像数据快照',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  CONSTRAINT `student_profile_history_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='画像历史表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_profile_history`
--

LOCK TABLES `student_profile_history` WRITE;
/*!40000 ALTER TABLE `student_profile_history` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_profile_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_school_record`
--

DROP TABLE IF EXISTS `student_school_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student_school_record` (
  `record_id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_id` int NOT NULL,
  `semester_id` int NOT NULL,
  `get_date` date NOT NULL,
  `class_id` int NOT NULL COMMENT '记录时所属班级',
  `grade_id` int NOT NULL COMMENT '记录时所属级号',
  `score` int DEFAULT NULL,
  `proof` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '证书/文件编号',
  `is_deleted` tinyint DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`record_id`),
  UNIQUE KEY `uk_proof` (`proof`),
  KEY `student_id` (`student_id`),
  KEY `event_id` (`event_id`),
  KEY `semester_id` (`semester_id`),
  KEY `class_id` (`class_id`),
  KEY `grade_id` (`grade_id`),
  CONSTRAINT `student_school_record_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `student_school_record_ibfk_2` FOREIGN KEY (`event_id`) REFERENCES `school_event_type` (`event_id`),
  CONSTRAINT `student_school_record_ibfk_3` FOREIGN KEY (`semester_id`) REFERENCES `semester` (`semester_id`),
  CONSTRAINT `student_school_record_ibfk_4` FOREIGN KEY (`class_id`) REFERENCES `class` (`class_id`),
  CONSTRAINT `student_school_record_ibfk_5` FOREIGN KEY (`grade_id`) REFERENCES `grade` (`grade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生校级事件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_school_record`
--

LOCK TABLES `student_school_record` WRITE;
/*!40000 ALTER TABLE `student_school_record` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_school_record` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_status_change`
--

DROP TABLE IF EXISTS `student_status_change`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student_status_change` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `change_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '休学/复学/转入/转出/毕业',
  `from_class_id` int DEFAULT NULL,
  `to_class_id` int DEFAULT NULL,
  `from_grade_id` int DEFAULT NULL,
  `to_grade_id` int DEFAULT NULL,
  `effective_date` date NOT NULL,
  `reason` text COLLATE utf8mb4_unicode_ci,
  `approver` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  KEY `from_class_id` (`from_class_id`),
  KEY `to_class_id` (`to_class_id`),
  KEY `from_grade_id` (`from_grade_id`),
  KEY `to_grade_id` (`to_grade_id`),
  CONSTRAINT `student_status_change_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `student_status_change_ibfk_2` FOREIGN KEY (`from_class_id`) REFERENCES `class` (`class_id`),
  CONSTRAINT `student_status_change_ibfk_3` FOREIGN KEY (`to_class_id`) REFERENCES `class` (`class_id`),
  CONSTRAINT `student_status_change_ibfk_4` FOREIGN KEY (`from_grade_id`) REFERENCES `grade` (`grade_id`),
  CONSTRAINT `student_status_change_ibfk_5` FOREIGN KEY (`to_grade_id`) REFERENCES `grade` (`grade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学籍变动记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_status_change`
--

LOCK TABLES `student_status_change` WRITE;
/*!40000 ALTER TABLE `student_status_change` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_status_change` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_task_finish`
--

DROP TABLE IF EXISTS `student_task_finish`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student_task_finish` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `task_id` int NOT NULL COMMENT '任务ID',
  `year_id` int NOT NULL COMMENT '当前所属学年',
  `original_task_id` int DEFAULT NULL COMMENT '原始任务ID',
  `original_year_id` int DEFAULT NULL COMMENT '原始学年',
  `is_carried_over` tinyint DEFAULT '0' COMMENT '是否为结转任务',
  `carryover_count` int DEFAULT '0' COMMENT '已结转次数',
  `current_score` decimal(6,2) DEFAULT NULL COMMENT '当前可得分数',
  `status` tinyint DEFAULT '0' COMMENT '0=未完成 1=已完成 2=已作废',
  `finish_date` date DEFAULT NULL,
  `finish_year_id` int DEFAULT NULL COMMENT '完成时学年',
  `proof` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_task_year` (`student_id`,`task_id`,`year_id`),
  KEY `task_id` (`task_id`),
  KEY `year_id` (`year_id`),
  KEY `original_task_id` (`original_task_id`),
  KEY `original_year_id` (`original_year_id`),
  KEY `finish_year_id` (`finish_year_id`),
  CONSTRAINT `student_task_finish_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `student_task_finish_ibfk_2` FOREIGN KEY (`task_id`) REFERENCES `grade_moral_task` (`task_id`),
  CONSTRAINT `student_task_finish_ibfk_3` FOREIGN KEY (`year_id`) REFERENCES `school_year` (`year_id`),
  CONSTRAINT `student_task_finish_ibfk_4` FOREIGN KEY (`original_task_id`) REFERENCES `grade_moral_task` (`task_id`),
  CONSTRAINT `student_task_finish_ibfk_5` FOREIGN KEY (`original_year_id`) REFERENCES `school_year` (`year_id`),
  CONSTRAINT `student_task_finish_ibfk_6` FOREIGN KEY (`finish_year_id`) REFERENCES `school_year` (`year_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生任务完成记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_task_finish`
--

LOCK TABLES `student_task_finish` WRITE;
/*!40000 ALTER TABLE `student_task_finish` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_task_finish` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_carryover_log`
--

DROP TABLE IF EXISTS `task_carryover_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_carryover_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_task_id` int NOT NULL COMMENT '原始任务ID',
  `from_year_id` int NOT NULL,
  `to_year_id` int NOT NULL,
  `carryover_index` int NOT NULL COMMENT '第几次结转',
  `score_before` decimal(6,2) DEFAULT NULL,
  `score_after` decimal(6,2) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  KEY `original_task_id` (`original_task_id`),
  KEY `from_year_id` (`from_year_id`),
  KEY `to_year_id` (`to_year_id`),
  CONSTRAINT `task_carryover_log_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `task_carryover_log_ibfk_2` FOREIGN KEY (`original_task_id`) REFERENCES `grade_moral_task` (`task_id`),
  CONSTRAINT `task_carryover_log_ibfk_3` FOREIGN KEY (`from_year_id`) REFERENCES `school_year` (`year_id`),
  CONSTRAINT `task_carryover_log_ibfk_4` FOREIGN KEY (`to_year_id`) REFERENCES `school_year` (`year_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务结转日志表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_carryover_log`
--

LOCK TABLES `task_carryover_log` WRITE;
/*!40000 ALTER TABLE `task_carryover_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_carryover_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `teacher`
--

DROP TABLE IF EXISTS `teacher`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `teacher` (
  `teacher_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '工号',
  `name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `wxid` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信ID',
  `subject` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '任教学科',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '密码哈希',
  `role` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'teacher' COMMENT '角色：admin/jiaowu/xuefa/cleader/teacher',
  `level` int DEFAULT '0' COMMENT '权限等级',
  `is_active` tinyint DEFAULT '1' COMMENT '登录权限',
  `notice_enabled` tinyint DEFAULT '1' COMMENT '通知开关',
  `is_password_changed` tinyint DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`teacher_id`),
  KEY `idx_wxid` (`wxid`) COMMENT '微信ID索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='教师信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `teacher`
--

LOCK TABLES `teacher` WRITE;
/*!40000 ALTER TABLE `teacher` DISABLE KEYS */;
INSERT INTO `teacher` VALUES ('T_任庆叶','任庆叶',NULL,'政治任','Lk9jH2gF','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_任秀辉','任秀辉',NULL,'化学任','666666','teacher/cleader',6,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_侯莹','侯莹',NULL,'英语侯','Fg3hJ5kL','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_冯秀珍','冯秀珍',NULL,'地理冯','Q2wE4rT6','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_刘亚利','刘亚利',NULL,'化学刘','9J7hG5fD','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_刘斌','刘斌',NULL,'政治刘','4hJ6sD8f','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_刘晓玲','刘晓玲',NULL,'数学刘','3aS5dF7g','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_刘欣悦','刘欣悦',NULL,'语文刘/阅读刘','Jh8gF6dS','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_单俊杰','单俊杰',NULL,'地理单','A3sD5fG7','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_吕婷婷','吕婷婷',NULL,'数学吕','Zx7cV9bN','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_和青茹','和青茹',NULL,'英语和','2aB8cD7e','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_孙兰芳','孙兰芳',NULL,'政治孙/政治(会)','nM5kL7jH','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_孙姿干','孙姿干',NULL,'英语孙','7dS9fG2h','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_孙晓燕','孙晓燕',NULL,'语文孙/阅读孙','Xc2vB9nM','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_孙铭言','孙铭言',NULL,'音乐鉴赏孙','dS6fG8hJ','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_宋文燕','宋文燕',NULL,'日语宋','Jh5gF7dS','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_张亚琦','张亚琦',NULL,'美术鉴赏张','vB6nM8kL','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_张炜','张炜',NULL,'日语张','yU5iO7pP','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_张鹏飞','张鹏飞',NULL,'体育张','6R8tY0uI','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_戴建海','戴建海',NULL,'数学戴','9jH8gF7d','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_方艳','方艳',NULL,'数学方','5RtY7uI9','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_曲杰遵','曲杰遵',NULL,'体育曲','D7fG9hJ2','teacher/xuefa',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_朱旭','朱旭',NULL,'数学朱','7qW9eR2t','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_李东坡','李东坡',NULL,'美术鉴赏李','kL7jH9fD','teacher',5,1,0,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_李伟刚','李伟刚',NULL,'地理刚','zX9cV7bN','admin',5,1,0,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_李园路','李园路',NULL,'语文李','Gf4hJ6sD','teacher/jiaowu',15,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_李婷婷','李婷婷',NULL,'政治婷','0qW2eR4t','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_李滨','李滨',NULL,'体育李','9kL7jH5f','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_李秋涵','李秋涵',NULL,'数学涵','P8oI7uY6','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_杨雪','杨雪',NULL,'心理/信息技术杨','H7jK9lL1','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_段雪琪','段雪琪',NULL,'英语段','Vb9nM1kL','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_温琪','温琪',NULL,'美术鉴赏温','0eR2tY4u','teacher',5,1,0,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_王彬','王彬',NULL,'美术鉴赏王','gF2hJ4sD','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_王心愉','王心愉',NULL,'语文王/阅读王','9uI7oP5y','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_王晓寒','王晓寒',NULL,'数学王','B4nM6kL8','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_王泽辰','王泽辰',NULL,'书法王','G5hJ7kL9','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_田','田',NULL,'技术田/信息技术田/通用技术田','sD9fG0hJ','admin',999,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_盛月兰','盛月兰',NULL,'英语盛','Gf4hJ6sD','teacher',15,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_祝月永','祝月永',NULL,'数学祝','yT5uI7oP','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_纪义笑','纪义笑',NULL,'物理纪','Yt3uI5oP','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_苏子腾','苏子腾',NULL,'体育苏','bN4mK6lL','teacher/xuefa',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_苏雪剑','苏雪剑',NULL,'历史苏','H2jK9lL7','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_董月明','董月明',NULL,'语文董/阅读董','Fd3sD5fG','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_蔡虎诚','蔡虎诚',NULL,'历史蔡','N8bV6cX4','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_蔺建妮','蔺建妮',NULL,'英语蔺','Lk5jH7gF','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_袁玲','袁玲',NULL,'历史袁','4qW6eR8t','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_赵慧','赵慧',NULL,'英语赵','Po7iU8yT','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_赵敏','赵敏',NULL,'体育赵','G9jH2kL4','teacher/xuefa',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_赵毅','赵毅',NULL,'美术鉴赏赵','oP7yT9uI','teacher',5,1,0,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_赵淑娴','赵淑娴',NULL,'语文赵/阅读赵','2rT4yU6i','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_车巧玲','车巧玲',NULL,'语文车/阅读车','mK8bV2cX','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_迟京超','迟京超',NULL,'美术鉴赏迟','iU3oP5yT','teacher',5,1,0,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_邓瑶雪','邓瑶雪',NULL,'语文邓/阅读邓','3cV5bN7m','teacher',5,1,0,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_邵丽莹','邵丽莹',NULL,'生物邵','mK3bV5cX','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_郝子旭','郝子旭',NULL,'生物郝','fG4hJ6sD','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_郭兢业','郭兢业',NULL,'物理郭/物理(会)','5mK7bV9c','teacher/cleader',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_陈明','陈明',NULL,'地理陈','888888','teacher/xuefa',20,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_隋淑帆','隋淑帆',NULL,'地理隋','mK6bV9cX','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_黎文莉','黎文莉',NULL,'英语黎','8sD2fG4h','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_齐建文','齐建文',NULL,'语文齐/阅读齐','5wE7rT9y','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56'),('T_齐迎春','齐迎春',NULL,'历史齐','sD4fG6hJ','teacher',5,1,1,0,'2026-03-29 08:16:56','2026-03-29 08:16:56');
/*!40000 ALTER TABLE `teacher` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `violation_escalation_rule`
--

DROP TABLE IF EXISTS `violation_escalation_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `violation_escalation_rule` (
  `rule_id` int NOT NULL AUTO_INCREMENT,
  `event_id` int NOT NULL COMMENT '违纪事件类型',
  `time_window_days` int DEFAULT '90' COMMENT '统计时间窗口',
  `escalation_rules` json DEFAULT NULL COMMENT '累进规则',
  PRIMARY KEY (`rule_id`),
  KEY `event_id` (`event_id`),
  CONSTRAINT `violation_escalation_rule_ibfk_1` FOREIGN KEY (`event_id`) REFERENCES `daily_event_type` (`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='违纪累进规则表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `violation_escalation_rule`
--

LOCK TABLES `violation_escalation_rule` WRITE;
/*!40000 ALTER TABLE `violation_escalation_rule` DISABLE KEYS */;
/*!40000 ALTER TABLE `violation_escalation_rule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `warning_config`
--

DROP TABLE IF EXISTS `warning_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `warning_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `rule_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `trigger_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'score_threshold/count_threshold',
  `trigger_value` int NOT NULL,
  `notify_roles` json DEFAULT NULL COMMENT '["cleader", "xuefa"]',
  `is_active` tinyint DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预警配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `warning_config`
--

LOCK TABLES `warning_config` WRITE;
/*!40000 ALTER TABLE `warning_config` DISABLE KEYS */;
INSERT INTO `warning_config` VALUES (1,'德育分过低','score_threshold',50,'[\"cleader\", \"xuefa\", \"jiaowu\"]',1),(2,'扣分过多','score_threshold',-20,'[\"cleader\", \"xuefa\", \"jiaowu\"]',1),(3,'违纪次数过多','count_threshold',5,'[\"cleader\", \"xuefa\", \"jiaowu\"]',1),(4,'德育分过低','score_threshold',50,'[\"cleader\", \"xuefa\", \"jiaowu\"]',1),(5,'扣分过多','score_threshold',-20,'[\"cleader\", \"xuefa\", \"jiaowu\"]',1),(6,'违纪次数过多','count_threshold',5,'[\"cleader\", \"xuefa\", \"jiaowu\"]',1);
/*!40000 ALTER TABLE `warning_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `warning_log`
--

DROP TABLE IF EXISTS `warning_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `warning_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rule_id` int NOT NULL,
  `semester_id` int NOT NULL,
  `warning_level` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'warning',
  `message` text COLLATE utf8mb4_unicode_ci,
  `is_read` tinyint DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  KEY `rule_id` (`rule_id`),
  KEY `semester_id` (`semester_id`),
  CONSTRAINT `warning_log_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `warning_log_ibfk_2` FOREIGN KEY (`rule_id`) REFERENCES `warning_config` (`id`),
  CONSTRAINT `warning_log_ibfk_3` FOREIGN KEY (`semester_id`) REFERENCES `semester` (`semester_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预警日志表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `warning_log`
--

LOCK TABLES `warning_log` WRITE;
/*!40000 ALTER TABLE `warning_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `warning_log` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-29 23:23:21
