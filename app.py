import json
import os
import sys
from flask import Flask, render_template, request, jsonify

# --- 配置 ---
CONFIG_FILE = 'config.json'
app = Flask(__name__)

# --- 辅助函数 ---

def load_config():
    """加载完整的 config.json"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {CONFIG_FILE}: {e}", file=sys.stderr)
        return {}

def save_config(config_data):
    """保存完整的 config.json"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error saving {CONFIG_FILE}: {e}", file=sys.stderr)
        return False

def load_seasonal_list(filename):
    """加载新番列表"""
    if not os.path.exists(filename):
        print(f"File not found: {filename}", file=sys.stderr)
        return []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}", file=sys.stderr)
        return []

# --- 网页路由 ---

@app.route('/')
def index():
    """渲染主页面"""
    return render_template('index.html')

# --- API 路由 (用于网页前后端通信) ---

@app.route('/api/data', methods=['GET'])
def get_data():
    """API: 获取所有新番(按周几分组)和当前已选中的番剧"""
    config = load_config()
    
    # 1. 获取新番列表的文件路径
    seasonal_list_file = config.get('seasonal_fetcher', {}).get('output_file')
    if not seasonal_list_file:
        return jsonify({"error": "Config missing 'seasonal_fetcher.output_file'"}), 500
        
    # 2. 获取当前的追番列表
    current_watchlist_config = config.get('torrent_searcher', {}).get('search_config', {})
    current_watchlist_titles = list(current_watchlist_config.keys())
    
    # 3. 加载新番列表 (get_seasonal_anime.py 已经按日期/时间排好序了)
    seasonal_list = load_seasonal_list(seasonal_list_file)
    if not seasonal_list:
        return jsonify({"error": f"Could not load {seasonal_list_file}. Run 'get_seasonal_anime.py' first."}), 500

    # 4. (新) 按周几分组
    weekdays = config.get('global_settings', {}).get('chinese_weekdays', ["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
    # 初始化一个字典, key是周几, value是空列表
    grouped_anime = {day: [] for day in weekdays}
    
    # 遍历已排序的新番列表, 按周几归类
    for anime in seasonal_list:
        day = anime.get('weekday')
        if day in grouped_anime:
            grouped_anime[day].append(anime)
        
    return jsonify({
        "grouped_anime": grouped_anime,       # <--- 修改: 发送分组后的数据
        "weekdays_order": weekdays,         # <--- 新增: 发送周几的正确顺序
        "current_watchlist": current_watchlist_titles
    })

@app.route('/api/save_watchlist', methods=['POST'])
def save_watchlist():
    """API: 接收网页上勾选的列表并保存到 config.json"""
    
    selected_titles = request.json.get('selected_titles', [])
    print(f"[*] 收到新的追番列表: {selected_titles}")

    # 自动为新添加的番剧设置默认搜索词
    config = load_config()
    if 'torrent_searcher' not in config:
        config['torrent_searcher'] = {}
    
    # 保留旧的配置, 只增/删番剧
    new_search_config = config.get('torrent_searcher', {}).get('search_config', {})
    
    # 1. 移除 (取消勾选的)
    current_titles = list(new_search_config.keys())
    for title in current_titles:
        if title not in selected_titles:
            del new_search_config[title]
            
    # 2. 添加 (新勾选的)
    for title in selected_titles:
        if title not in new_search_config:
            # 如果是新添加的, 设置默认搜索词
            new_search_config[title] = {
                "search_keys": [title, "1080p"]
            }

    config['torrent_searcher']['search_config'] = new_search_config
    
    if save_config(config):
        print("[*] config.json 更新成功!")
        return jsonify({"status": "success", "message": "追番列表已更新!"})
    else:
        return jsonify({"error": "保存 config.json 失败"}), 500

# --- 启动服务器 ---
if __name__ == '__main__':
    print("[*] 启动追番管理服务器...")
    print("[*] 请在浏览器中打开 http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)