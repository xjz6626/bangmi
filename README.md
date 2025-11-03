# 🎌 Bangmi - 自动追番系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

一个功能完善的自动化追番系统，集成 Bangumi API、智能种子搜索、云端下载和 Web 管理界面

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [配置说明](#-配置说明) • [使用指南](#-使用指南) • [API 文档](#-api-文档)

</div>

---

## ✨ 功能特性

### 🎯 核心功能
- **🌐 Web 管理界面** - 基于 Flask 的现代化 Web UI，可视化管理追番列表
- **📺 Bangumi 集成** - 完整集成 Bangumi API，获取番剧详情、评分、角色、讨论等
- **🔍 智能搜索** - 自动从 animes.garden 搜索种子，支持关键词过滤和集数识别
- **☁️ 云端下载** - 使用 Seedr 云端服务下载种子，无需本地 BT 客户端
- **⏰ 定时调度** - 基于 JST 时区的定时任务，自动搜索和下载新番
- **📝 历史跟踪** - 自动记录下载历史，避免重复下载
- **🎭 观看状态** - 支持标记章节观看状态（需要 Bangumi Token）

### 📊 番剧信息展示
- 评分和排名
- 封面图片
- 剧情简介
- 章节列表（每集标题、放送日期）
- 角色和声优信息
- 制作人员（导演、编剧等）
- 关联作品（前作、续集）
- 讨论区和评论日志

### 🔧 技术栈
- **后端**: Flask, Python 3.8+
- **API**: Bangumi API (Legacy + v0)
- **下载**: Seedr Cloud Service
- **调度**: schedule + pytz (JST timezone)
- **前端**: HTML5 + CSS3 + Vanilla JavaScript

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.8 或更高版本
- pip 包管理器
- Seedr 账号（用于云端下载）
- Bangumi API Token（可选，用于高级功能）

### 2. 克隆项目

```bash
git clone https://github.com/xjz6626/bangmi.git
cd bangmi
```

### 3. 安装依赖

```bash
# 推荐使用虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

如果没有 `requirements.txt`，手动安装：

```bash
pip install flask requests schedule pytz seedrcc
```

### 4. 配置系统

复制示例配置文件并编辑：

```bash
cd data
cp config.example.json config.json
cp watchlist.example.json watchlist.json
cd ..
```

编辑 `data/config.json`，填入你的配置：

```json
{
    "global_settings": {
        "bangumi_api_token": "YOUR_BANGUMI_API_TOKEN",
        "seedr_email": "your_email@example.com",
        "seedr_password": "your_seedr_password"
    }
}
```

**获取 Bangumi API Token**: 访问 https://next.bgm.tv/demo/access-token

**注册 Seedr**: 访问 https://www.seedr.cc/

### 5. 启动 Web 服务

```bash
python app.py
```

打开浏览器访问: http://localhost:5000

### 6. 配置系统服务（可选）

将 Web 服务和调度器注册为系统服务：

```bash
# 复制服务文件
sudo cp bangmi-web.service /etc/systemd/system/
sudo cp bangmi-scheduler.service /etc/systemd/system/

# 编辑服务文件，修改路径和用户
sudo nano /etc/systemd/system/bangmi-web.service

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable bangmi-web.service
sudo systemctl start bangmi-web.service

# 查看服务状态
sudo systemctl status bangmi-web.service
```

---

## ⚙️ 配置说明

### config.json

主配置文件，包含所有系统设置：

```json
{
    "global_settings": {
        "bangumi_api_token": "你的Bangumi API Token",
        "seedr_email": "Seedr 邮箱",
        "seedr_password": "Seedr 密码",
        "torrent_api_url": "https://api.animes.garden/resources",
        "download_history_file": "data/download_history.json"
    },
    "local_storage": {
        "anime_dir": "anime"
    },
    "seasonal_fetcher": {
        "target_year": 2025,
        "target_months": [10, 11, 12],
        "output_file": "data/seasonal_anime_list.json"
    }
}
```

### watchlist.json

追番列表，通过 Web 界面管理：

```json
{
    "间谍过家家 第三季": {
        "search_keys": ["间谍过家家", "1080p"],
        "weekday": "周六",
        "begin_time": "23:00",
        "begin_date": "2025-10-05"
    }
}
```

---

## 📖 使用指南

### Web 界面操作

1. **刷新新番列表**: 点击"更新失效: 更新失败"按钮，从 Bangumi 获取当季新番
2. **添加追番**: 勾选想要追的番剧，点击"保存"
3. **编辑搜索关键词**: 点击番剧旁的编辑按钮，修改搜索关键词
4. **查看番剧详情**: 点击番剧名称，查看详细信息、章节列表等
5. **手动搜索**: 点击"搜索种子"按钮，立即搜索新集
6. **手动下载**: 点击"启动下载"按钮，下载搜索到的种子
7. **查看日志**: 点击"查看日志"按钮，查看调度器运行日志

### 命令行操作

```bash
# 手动刷新新番列表（已移除 get_seasonal_anime.py，使用 Bangumi API）
python -c "from app import bangumi_client; from bangumi_api import convert_calendar_to_seasonal_list; import json; data = convert_calendar_to_seasonal_list(bangumi_client.get_calendar()); json.dump(data, open('data/seasonal_anime_list.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=4)"

# 手动搜索种子
python search_torrents.py

# 手动下载
python download_bt.py

# 启动调度器（前台运行）
python bangmi_scheduler.py
```

### 调度器时间表

默认在 JST 时区的以下时间自动运行：
- 每天 05:00 (搜索 + 下载)
- 每天 15:00 (搜索 + 下载)

可在 `bangmi_scheduler.py` 中修改 `TARGET_TIMES_JST` 变量。

---

## 🔌 API 文档

### Web API 端点

#### 基础功能
- `GET /` - Web 主页
- `GET /api/data` - 获取新番列表和追番列表
- `POST /api/save_watchlist` - 保存追番列表
- `POST /api/refresh_seasonal` - 刷新新番列表
- `POST /api/search_torrents` - 触发种子搜索
- `POST /api/start_download` - 触发下载任务
- `GET /api/get_logs` - 获取调度器日志
- `POST /api/update_search_keys` - 更新番剧搜索关键词

#### Bangumi API
- `GET /api/bangumi/calendar` - 获取每日放送
- `GET /api/bangumi/search?keyword=关键词` - 搜索番剧
- `GET /api/bangumi/subject/<id>` - 获取番剧详情
- `GET /api/bangumi/episodes/<id>` - 获取章节列表
- `GET /api/bangumi/characters/<id>` - 获取角色信息
- `GET /api/bangumi/persons/<id>` - 获取制作人员
- `GET /api/bangumi/relations/<id>` - 获取关联作品
- `GET /api/bangumi/subject/<id>/topics` - 获取讨论话题
- `GET /api/bangumi/subject/<id>/comments` - 获取评论日志

#### 用户功能（需要 Token）
- `GET /api/bangumi/user/<username>/collections` - 获取用户收藏
- `PATCH /api/bangumi/episode/<subject_id>/<episode_id>/status` - 更新章节状态
- `PATCH /api/bangumi/episodes/<subject_id>/batch-status` - 批量更新章节状态

---

## 📁 项目结构

```
bangmi/
├── app.py                      # Flask Web 应用
├── bangmi_scheduler.py         # 定时调度器
├── bangumi_api.py              # Bangumi API 客户端
├── search_torrents.py          # 种子搜索脚本
├── download_bt.py              # 下载管理脚本
├── bangmi-web.service          # Web 服务配置（systemd）
├── README.md                   # 项目说明
├── requirements.txt            # Python 依赖
├── data/                       # 数据目录
│   ├── config.example.json     # 配置示例
│   ├── watchlist.example.json  # 追番列表示例
│   ├── config.json             # 实际配置（不提交）
│   ├── watchlist.json          # 实际追番列表（不提交）
│   ├── seasonal_anime_list.json # 新番列表（自动生成）
│   ├── search_results.json     # 搜索结果（自动生成）
│   ├── download_history.json   # 下载历史（自动生成）
│   └── scheduler.log           # 调度日志（自动生成）
├── anime/                      # 下载目录（不提交）
├── templates/                  # HTML 模板
│   └── index.html
└── static/                     # 静态资源
    └── style.css
```

---

## 🔧 高级配置

### 修改下载客户端

虽然默认使用 Seedr，但也支持其他 BT 客户端：

```json
{
    "bt_downloader": {
        "client_type": "qbittorrent",  // 可选: transmission, aria2
        "qbittorrent": {
            "host": "localhost",
            "port": 8080,
            "username": "admin",
            "password": "adminadmin"
        }
    }
}
```

### 自定义搜索关键词

在追番列表中为每个番剧配置特定的搜索关键词：

```json
{
    "番剧名称": {
        "search_keys": [
            "番剧关键词1",
            "字幕组",
            "1080p",
            "简体"
        ]
    }
}
```

### 修改调度时间

编辑 `bangmi_scheduler.py`:

```python
TARGET_TIMES_JST = ["05:00", "15:00", "20:00"]  # 添加更多时间点
```

---

## 🐛 故障排查

### Web 服务无法启动

```bash
# 检查端口占用
sudo lsof -i :5000

# 查看服务日志
sudo journalctl -u bangmi-web.service -f
```

### 下载失败

1. 检查 Seedr 账号是否正常
2. 查看 `data/scheduler.log` 日志
3. 手动运行测试: `python download_bt.py`

### 搜索不到种子

1. 检查追番列表的搜索关键词是否准确
2. 确认番剧已经开播
3. 手动运行测试: `python search_torrents.py`

### Bangumi API 返回 404

某些 API 功能需要 Legacy API，确保：
1. 使用正确的 API Token
2. 检查番剧 ID 是否正确
3. 部分功能（如观看状态）可能需要 v0 API Token

---

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📮 联系方式

- GitHub: [@xjz6626](https://github.com/xjz6626)
- 项目地址: https://github.com/xjz6626/bangmi

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**

Made with ❤️ by xjz6626

</div>
