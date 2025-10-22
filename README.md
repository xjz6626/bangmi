🎌 自动追番系统（Bangmi — Bangumi Auto-Downloader）

一个自动化追番工具，按播出时间搜索番剧、通过 Seedr.cc 做云端离线下载并把完成的视频同步到本地。

## 核心功能

- 新番拉取：`get_seasonal_anime.py` 从 Bangumi Data 获取指定季度的番剧列表。
- Web 管理：`app.py` 提供基于 Flask 的管理界面，便于勾选/管理追番。
- 定时调度：`bangmi_scheduler.py` 作为后台调度器按 JST 定时触发搜索与下载。
- 智能搜索：`search_torrents.py` 根据播出时间、追番配置和下载历史，筛选并生成下载任务。
- 云端下载：`download_bt.py` 集成 Seedr.cc（seedrcc），完成磁力 -> 云端 -> 本地的全流程。
- 历史跟踪：`download_history.json` 记录已下载的最高集数与磁力链接，避免重复下载。
- 任务队列：`search_results.json` 作为搜索到下载之间的任务队列，支持失败重试。

## 项目结构（简要）

```
.
├── bangmi_scheduler.py        # 调度器（后台运行）
├── get_seasonal_anime.py      # 获取季度新番列表
├── app.py                     # Flask Web 管理界面
├── search_torrents.py         # 智能搜索脚本
├── download_bt.py             # Seedr 云端下载脚本

├── config.json                # 核心配置（请保密，不提交到仓库）
├── config.example.json        # 配置示例（提交到仓库）
├── seasonal_anime_list.json   # 季度番剧数据（脚本生成）
├── download_history.json      # 下载历史（脚本生成）
├── search_results.json        # 任务队列（脚本生成）
├── scheduler.log              # 调度日志（可被忽略）

├── templates/                 # Flask 模板（web UI）
└── static/                    # 静态资源（CSS 等）

└── anime/                     # 本地下载目录（在 .gitignore 中）
```

## 快速开始

### 1. 安装依赖

推荐使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install requests schedule pytz seedrcc flask
```

（如果没有 `requirements.txt`，上面命令会回退为手动安装常用依赖）

### 2. 配置

复制示例配置并编辑：

```bash
cp config.example.json config.json
# 编辑 config.json，填写 seedr_email / seedr_password 等敏感信息
```

注意：`config.json` 含有敏感信息，仓库中已将其加入 `.gitignore`，请勿将真实凭据提交到远程。

### 3. 生成季度番剧列表（每季度执行一次）

```bash
python3 get_seasonal_anime.py
```

脚本会根据 `config.json` 中的 `target_year` 与 `target_months` 生成 `seasonal_anime_list.json`。

### 4. 使用 Web UI 管理追番（可选）

```bash
python3 app.py
```

访问：http://127.0.0.1:5000，勾选要追的番剧并保存。

### 5. 启动调度器（推荐后台运行）

```bash
nohup python3 bangmi_scheduler.py > scheduler.log 2>&1 &
```

调度器会在 JST（Asia/Tokyo）按 `TARGET_TIMES_JST` 设定触发 `search_torrents.py` 与 `download_bt.py`。

### 手动运行（调试/测试）

- 手动搜索：
```bash
python3 search_torrents.py
```
- 手动下载队列：
```bash
python3 download_bt.py
```

## 文件说明（功能概述）

- `get_seasonal_anime.py`：拉取并筛选当季度番剧。
- `app.py`：Flask Web 管理界面，更新 `config.json` 中的 `torrent_searcher.search_config`。
- `bangmi_scheduler.py`：调度器，负责定时触发搜索与下载。
- `search_torrents.py`：根据时间窗口和历史生成 `search_results.json` 任务。
- `download_bt.py`：使用 Seedr 服务上传磁力、等待云端完成并下载到本地，最后清理云端并更新历史记录。

## 注意事项

- Seedr 依赖：下载逻辑强依赖 Seedr.cc（`seedrcc` 库）。当前脚本不会使用 `qbittorrent`/`transmission`/`aria2` 配置块。
- 隐私与安全：`config.json` 包含凭据，请务必保密。仓库中保留了 `config.example.json` 供他人参考。
- 时区：系统按 JST（Asia/Tokyo）判断播出时间，请确保时间配置与目标时区一致。

## 将调度器注册为 systemd 服务（可选，推荐服务器运行）

下面提供两种常见方案：系统级（system service）和用户级（user service）。如果你的服务器供多用户使用或希望开机时自动启动，请使用**系统级**服务；如果你仅以个人用户运行并且不希望修改系统服务，请使用**用户级**服务（需启用 linger 来在无登录时启动）。

### 1) 系统级 service（以 root 创建）

创建一个 system unit（在 `/etc/systemd/system/bangmi.service`）：

```ini
[Unit]
Description=Bangmi Scheduler
After=network.target

[Service]
Type=simple
User=xjz
WorkingDirectory=/home/xjz/workplace/bangmi
ExecStart=/usr/bin/env python3 /home/xjz/workplace/bangmi/bangmi_scheduler.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

保存后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bangmi.service
```

检查状态与日志：

```bash
sudo systemctl status bangmi.service
sudo journalctl -u bangmi.service -n 200 --no-pager
```

### 2) 用户级 service（无需 root，但需开启 linger）

在 `~/.config/systemd/user` 下创建 `bangmi.service`：

```ini
[Unit]
Description=Bangmi Scheduler (user)
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/xjz/workplace/bangmi
ExecStart=/usr/bin/env python3 /home/xjz/workplace/bangmi/bangmi_scheduler.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

启用并启动：

```bash
systemctl --user daemon-reload
systemctl --user enable --now bangmi.service
# 如果希望在未登录时也能运行（允许 user services 在没有交互登录时启动）
sudo loginctl enable-linger $USER
```

查看日志：

```bash
journalctl --user -u bangmi.service -n 200 --no-pager
```

### 常见问题与建议

- 如果脚本依赖虚拟环境，修改 `ExecStart` 指向虚拟环境中的 python：
	`/home/xjz/workplace/bangmi/.venv/bin/python /home/xjz/workplace/bangmi/bangmi_scheduler.py`
- 请确保 `User` 的权限可以访问 `anime/` 目录和其他相关文件。可通过 `chown -R xjz:xjz /home/xjz/workplace/bangmi/anime` 设置文件所有权。
- 使用 `Restart=on-failure` 可以在脚本崩溃时自动重启；若需要更强的保护可用 `Restart=always`。



