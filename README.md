# 🎌 动漫BT下载系统

一个简洁高效的动漫种子搜索下载系统，基于qBittorrent和animes.garden API。

## 📁 项目结构

```
bangmi/
├── 🔧 核心脚本
│   ├── search_torrents.py      # 搜索动漫种子
│   ├── download_bt.py          # 管理BT下载  
│   ├── get_seasonal_anime.py   # 获取季度新番
│   └── app.py                  # Web管理界面
├── ⚙️ 工具脚本
│   └── optimize_no_proxy.py    # qBittorrent配置优化
├── 📄 配置和数据
│   ├── config.json            # 系统配置
│   ├── download_history.json  # 下载历史记录
│   ├── seasonal_anime_list.json # 新番列表
│   ├── search_results.json    # 搜索结果缓存
│   └── cookies.txt           # 认证凭据
├── 🌐 Web资源
│   ├── templates/            # HTML模板
│   └── static/              # CSS/JS静态文件
└── 📦 下载目录
    └── anime/               # 动漫下载存储
```

## 🚀 快速开始

### 1. 安装依赖
```bash
# Python依赖
pip3 install requests flask

# qBittorrent (无界面版)
sudo dnf install qbittorrent-nox  # Fedora
# sudo apt install qbittorrent-nox  # Ubuntu/Debian
```

### 2. 启动qBittorrent
```bash
sudo systemctl enable qbittorrent-nox@$USER
sudo systemctl start qbittorrent-nox@$USER
```
Web界面: http://localhost:8080 (admin/adminadmin)

### 3. 使用脚本
```bash
# 搜索动漫
python3 search_torrents.py

# 下载种子
python3 download_bt.py

# Web界面管理
python3 app.py  # 访问 http://localhost:5000
```

## 🎯 主要功能

- **🔍 智能搜索**: animes.garden API集成，支持中文搜索
- **📱 Web管理**: 直观的网页界面，支持批量操作
- **⚡ 自动下载**: 无缝对接qBittorrent，自动管理下载
- **📊 历史跟踪**: 完整的下载记录和进度监控
- **🌟 新番追踪**: 自动获取季度新番信息
- **🔧 性能优化**: 内置优化工具，提升下载效率

## ⚡ 性能优化

如遇下载慢或连接问题：
```bash
python3 optimize_no_proxy.py  # 恢复标准协议配置
```

该工具会：
- ✅ 启用DHT/PEX/LSD (UDP协议)
- ✅ 恢复标准BT端口和设置
- ✅ 重新声明所有种子使用新配置

## 📝 配置说明

编辑 `config.json` 自定义：
- BT客户端连接参数
- 搜索过滤和排序规则
- 下载路径和文件组织
- API访问设置

## ⚠️ 注意事项

- 请遵守当地法律法规，尊重版权
- 合理使用网络资源，避免影响他人
- 定期清理下载文件，管理存储空间
- 建议配置防火墙端口转发以获得最佳性能

## 🔧 故障排除

**下载无速度?**
1. 检查qBittorrent服务状态
2. 运行优化脚本恢复UDP协议
3. 确认防火墙端口开放

**搜索无结果?**
1. 验证animes.garden网络可达性
2. 检查搜索关键词是否正确
3. 尝试不同的搜索条件

**Web界面无法访问?**
1. 确认Flask应用正常启动
2. 检查端口5000是否被占用
3. 验证模板和静态文件完整性

## 🌐 Web管理界面

### qBittorrent Web UI
- 地址: http://localhost:8080
- 用户: admin / adminadmin
- 功能: 种子管理、下载监控

### 项目Web界面  
- 地址: http://localhost:5000
- 功能: 搜索、下载历史管理

## 📋 脚本说明

### search_torrents.py
搜索animes.garden上的动漫种子，支持：
- 关键词搜索
- 季度新番获取
- 搜索结果缓存
- 智能过滤和排序

### download_bt.py
管理BT下载，支持：
- 历史记录批量下载
- 磁力链接解析和增强
- qBittorrent API操作
- 下载进度跟踪

### get_seasonal_anime.py
获取季度动漫信息，支持：
- 自动获取当季新番
- 动漫信息缓存
- 多语言标题处理

### optimize_no_proxy.py
qBittorrent性能优化工具，功能：
- 协议配置恢复
- 网络设置优化
- Tracker管理
- 连接诊断