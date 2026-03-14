## 文件说明

### main.py

程序入口

### client.py

对接WX客户端,实现发送文本,图片,文件等功能

### sendqueue.py

发送消息队列

### wxmsg.py

接收到的消息队列

### config

#### config.py: 配置模块

#### log.py: 日志模块

#### config.yaml: 配置参数

## logs

程序运行日志

### databases

数据库文件

## models

功能模块

#### application

志愿填报模块

#### manage

管理模块

#### lesson

教务管理

##### datas_api.py

教务数据接口

##### homework.py

作业管理模块

##### lesson.py

教务管理模块

##### notes.py

课时记录模块

#### api.py

api接口

#### task.py

任务模块

## 消息类型

{
  "contentTypes": [
    {
      "name": "UnknownContent",
      "code": 0,
      "description": "未知内容"
    },
    {
      "name": "Text",
      "code": 1,
      "description": "文本内容"
    },
    {
      "name": "Picture",
      "code": 2,
      "description": "图片消息"
    },
    {
      "name": "Voice",
      "code": 3,
      "description": "语音消息"
    },
    {
      "name": "Video",
      "code": 4,
      "description": "视频消息"
    },
    {
      "name": "System",
      "code": 5,
      "description": "系统消息"
    },
    {
      "name": "Link",
      "code": 6,
      "description": "链接消息"
    },
    {
      "name": "LinkExt",
      "code": 7,
      "description": "扩展的链接消息（小程序分享等），内容为xml格式，暂未使用"
    },
    {
      "name": "File",
      "code": 8,
      "description": "文件发送"
    },
    {
      "name": "NameCard",
      "code": 9,
      "description": "名片"
    },
    {
      "name": "Location",
      "code": 10,
      "description": "位置信息"
    },
    {
      "name": "LuckyMoney",
      "code": 11,
      "description": "红包"
    },
    {
      "name": "MoneyTrans",
      "code": 12,
      "description": "转账"
    },
    {
      "name": "WeApp",
      "code": 13,
      "description": "小程序"
    },
    {
      "name": "Emoji",
      "code": 14,
      "description": ""
    },
    {
      "name": "RoomManage",
      "code": 15,
      "description": "群管理消息"
    },
    {
      "name": "Sys_LuckyMoney",
      "code": 16,
      "description": "领取红包消息"
    },
    {
      "name": "RoomSystem",
      "code": 17,
      "description": "群聊系统消息"
    },
    {
      "name": "BizLink",
      "code": 18,
      "description": "公众号文章"
    },
    {
      "name": "AudioCall",
      "code": 19,
      "description": "语音通话"
    },
    {
      "name": "VideoCall",
      "code": 20,
      "description": "视频通话"
    },
    {
      "name": "NotifyMsg",
      "code": 21,
      "description": "服务通知"
    },
    {
      "name": "QuoteMsg",
      "code": 22,
      "description": "引用通知"
    },
    {
      "name": "JieLongMsg",
      "code": 23,
      "description": "接龙"
    },
    {
      "name": "ShiPinHao",
      "code": 24,
      "description": "视频号消息"
    },
    {
      "name": "RoomLiving",
      "code": 25,
      "description": "群直播消息"
    },
    {
      "name": "PaiYiPai",
      "code": 26,
      "description": "拍一拍"
    },
    {
      "name": "Music",
      "code": 27,
      "description": "分享音乐"
    },
    {
      "name": "FinderLive",
      "code": 28,
      "description": "视频号直播"
    },
    {
      "name": "KefuNameCard",
      "code": 29,
      "description": "客服号名片"
    },
    {
      "name": "QiyeNameCard",
      "code": 30,
      "description": "企业微信名片"
    },
    {
      "name": "UnSupport",
      "code": 99,
      "description": "不支持的消息"
    },
    {
      "name": "UNRECOGNIZED",
      "code": -1,
      "description": ""
    }
  ]
}