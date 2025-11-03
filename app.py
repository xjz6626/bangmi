import json
import os
import sys
from flask import Flask, render_template, request, jsonify
from bangumi_api import BangumiAPI, convert_calendar_to_seasonal_list, load_bangumi_token_from_config

# --- 配置 ---
CONFIG_FILE = 'data/config.json'
WATCHLIST_FILE = 'data/watchlist.json'
app = Flask(__name__)

# 初始化 Bangumi API 客户端（从配置文件加载 token）
bangumi_token = load_bangumi_token_from_config()
bangumi_client = BangumiAPI(access_token=bangumi_token)

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

def load_watchlist():
    """加载追番列表"""
    try:
        if not os.path.exists(WATCHLIST_FILE):
            return {}
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {WATCHLIST_FILE}: {e}", file=sys.stderr)
        return {}

def save_watchlist(watchlist_data):
    """保存追番列表"""
    try:
        with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(watchlist_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error saving {WATCHLIST_FILE}: {e}", file=sys.stderr)
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
    current_watchlist = load_watchlist()
    current_watchlist_titles = list(current_watchlist.keys())
    
    # 3. 加载新番列表 (Bangumi API 已经按日期/时间排好序了)
    seasonal_list = load_seasonal_list(seasonal_list_file)
    if not seasonal_list:
        return jsonify({"error": f"Could not load {seasonal_list_file}. Use 'Bangumi API' to fetch data first."}), 500

    # 4. 按周几分组
    weekdays = config.get('global_settings', {}).get('chinese_weekdays', ["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
    # 初始化一个字典, key是周几, value是空列表
    grouped_anime = {day: [] for day in weekdays}
    
    # 遍历已排序的新番列表, 按周几归类
    for anime in seasonal_list:
        day = anime.get('weekday')
        if day in grouped_anime:
            grouped_anime[day].append(anime)
        
    return jsonify({
        "grouped_anime": grouped_anime,
        "weekdays_order": weekdays,
        "current_watchlist": current_watchlist_titles
    })

@app.route('/api/save_watchlist', methods=['POST'])
def save_watchlist_route():
    """API: 接收网页上勾选的列表并保存到 watchlist.json"""
    
    selected_titles = request.json.get('selected_titles', [])
    print(f"[*] 收到新的追番列表: {selected_titles}")

    # 加载配置和新番列表
    config = load_config()
    seasonal_list_file = config.get('seasonal_fetcher', {}).get('output_file')
    seasonal_list = load_seasonal_list(seasonal_list_file) if seasonal_list_file else []
    
    # 构建番剧信息映射
    anime_info_map = {}
    for anime in seasonal_list:
        anime_info_map[anime.get('primary_title')] = anime
        # 也为备用名称建立映射
        for alt_name in anime.get('all_cn_names', []):
            if alt_name and alt_name != anime.get('primary_title'):
                anime_info_map[alt_name] = anime
    
    # 加载当前追番列表
    current_watchlist = load_watchlist()
    new_watchlist = {}
    
    # 1. 移除 (取消勾选的)
    # 2. 保留 (继续勾选的) - 保持原有配置
    # 3. 添加 (新勾选的) - 使用默认配置并添加放送时间信息
    for title in selected_titles:
        if title in current_watchlist:
            # 保留旧的配置
            new_watchlist[title] = current_watchlist[title]
            # 更新或添加放送时间信息（如果有的话）
            if title in anime_info_map:
                anime_info = anime_info_map[title]
                new_watchlist[title]['weekday'] = anime_info.get('weekday', '')
                new_watchlist[title]['begin_time'] = anime_info.get('begin_time', '00:00')
                new_watchlist[title]['begin_date'] = anime_info.get('begin_date', '')
        else:
            # 新添加的番剧，设置默认搜索词和放送时间
            anime_info = anime_info_map.get(title, {})
            new_watchlist[title] = {
                "search_keys": [title, "1080p"],
                "weekday": anime_info.get('weekday', ''),
                "begin_time": anime_info.get('begin_time', '00:00'),
                "begin_date": anime_info.get('begin_date', '')
            }

    if save_watchlist(new_watchlist):
        print("[*] watchlist.json 更新成功!")
        return jsonify({"status": "success", "message": "追番列表已更新!"})
    else:
        return jsonify({"error": "保存 watchlist.json 失败"}), 500

@app.route('/api/refresh_seasonal', methods=['POST'])
def refresh_seasonal():
    """API: 使用 Bangumi API 获取当前放送的番剧（替代 get_seasonal_anime.py）"""
    try:
        print("[*] 开始使用 Bangumi API 更新数据...")
        
        # 获取 Bangumi 数据
        calendar_data = bangumi_client.get_calendar()
        if not calendar_data:
            return jsonify({"error": "无法获取 Bangumi 数据"}), 500
        
        # 转换格式
        seasonal_list = convert_calendar_to_seasonal_list(calendar_data)
        
        # 获取配置
        config = load_config()
        output_file = config.get('seasonal_fetcher', {}).get('output_file', 'data/seasonal_anime_list.json')
        
        # 保存到文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(seasonal_list, f, ensure_ascii=False, indent=4)
            
            print(f"[*] 成功保存 {len(seasonal_list)} 部动画到 {output_file}")
            return jsonify({
                "status": "success",
                "message": f"成功从 Bangumi API 获取并保存了 {len(seasonal_list)} 部动画",
                "count": len(seasonal_list)
            })
        except Exception as e:
            print(f"[!] 保存文件失败: {e}", file=sys.stderr)
            return jsonify({"error": f"保存文件失败: {str(e)}"}), 500
            
    except Exception as e:
        print(f"[!] 更新失败: {e}", file=sys.stderr)
        return jsonify({"error": f"更新失败: {str(e)}"}), 500

@app.route('/api/search_torrents', methods=['POST'])
def search_torrents():
    """API: 调用 search_torrents.py 脚本进行种子搜索"""
    import subprocess
    
    script_path = os.path.join(os.path.dirname(__file__), 'search_torrents.py')
    
    if not os.path.exists(script_path):
        return jsonify({"error": "search_torrents.py 脚本未找到"}), 500
    
    try:
        print("[*] 开始执行 search_torrents.py...")
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300  # 搜索可能需要更长时间
        )
        # 合并 stdout 和 stderr 以显示完整输出
        full_output = result.stdout
        if result.stderr:
            full_output += "\n" + result.stderr
        
        print(f"[*] 搜索完成")
        return jsonify({
            "status": "success",
            "message": "种子搜索完成！",
            "output": full_output,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "搜索超时"}), 500
    except subprocess.CalledProcessError as e:
        print(f"[!] 搜索失败: {e.stderr}", file=sys.stderr)
        return jsonify({"error": f"搜索失败: {e.stderr}"}), 500
    except Exception as e:
        print(f"[!] 未知错误: {e}", file=sys.stderr)
        return jsonify({"error": f"未知错误: {str(e)}"}), 500

@app.route('/api/start_download', methods=['POST'])
def start_download():
    """API: 调用 download_bt.py 脚本开始下载"""
    import subprocess
    
    script_path = os.path.join(os.path.dirname(__file__), 'download_bt.py')
    
    if not os.path.exists(script_path):
        return jsonify({"error": "download_bt.py 脚本未找到"}), 500
    
    try:
        print("[*] 开始执行 download_bt.py...")
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=1800  # 下载可能需要很长时间，设置30分钟超时
        )
        # 合并 stdout 和 stderr 以显示完整输出
        full_output = result.stdout
        if result.stderr:
            full_output += "\n" + result.stderr
        
        print(f"[*] 下载完成")
        return jsonify({
            "status": "success",
            "message": "下载任务完成！",
            "output": full_output,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "下载超时"}), 500
    except subprocess.CalledProcessError as e:
        print(f"[!] 下载失败: {e.stderr}", file=sys.stderr)
        return jsonify({"error": f"下载失败: {e.stderr}"}), 500
    except Exception as e:
        print(f"[!] 未知错误: {e}", file=sys.stderr)
        return jsonify({"error": f"未知错误: {str(e)}"}), 500

@app.route('/api/get_logs', methods=['GET'])
def get_logs():
    """API: 获取 scheduler.log 的内容"""
    log_file = os.path.join(os.path.dirname(__file__), 'data', 'scheduler.log')
    
    # 获取查询参数，支持获取最后N行
    lines = request.args.get('lines', type=int)
    
    if not os.path.exists(log_file):
        return jsonify({"content": "日志文件不存在", "exists": False})
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            if lines:
                # 读取最后N行
                all_lines = f.readlines()
                content = ''.join(all_lines[-lines:])
            else:
                # 读取全部内容
                content = f.read()
        
        return jsonify({"content": content, "exists": True})
    except Exception as e:
        return jsonify({"error": f"读取日志失败: {str(e)}"}), 500

@app.route('/api/update_search_keys', methods=['POST'])
def update_search_keys():
    """API: 更新指定番剧的搜索关键词"""
    data = request.json
    anime_title = data.get('title')
    search_keys = data.get('search_keys', [])
    
    if not anime_title:
        return jsonify({"error": "缺少番剧标题"}), 400
    
    watchlist = load_watchlist()
    
    if anime_title not in watchlist:
        return jsonify({"error": f"番剧 '{anime_title}' 不在追番列表中"}), 404
    
    # 更新搜索关键词
    watchlist[anime_title]['search_keys'] = search_keys
    
    if save_watchlist(watchlist):
        print(f"[*] 已更新 '{anime_title}' 的搜索关键词: {search_keys}")
        return jsonify({"status": "success", "message": f"已更新 '{anime_title}' 的搜索关键词"})
    else:
        return jsonify({"error": "保存配置失败"}), 500

@app.route('/api/get_search_config', methods=['GET'])
def get_search_config():
    """API: 获取当前所有番剧的搜索配置"""
    watchlist = load_watchlist()
    return jsonify(watchlist)

@app.route('/api/bangumi/calendar', methods=['GET'])
def get_bangumi_calendar():
    """API: 获取 Bangumi 每日放送信息"""
    try:
        calendar_data = bangumi_client.get_calendar()
        if calendar_data:
            # 转换为兼容格式
            seasonal_list = convert_calendar_to_seasonal_list(calendar_data)
            return jsonify({
                "status": "success",
                "data": seasonal_list,
                "count": len(seasonal_list)
            })
        else:
            return jsonify({"error": "无法获取 Bangumi 数据"}), 500
    except Exception as e:
        print(f"[!] Bangumi API 调用失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/search', methods=['GET'])
def search_bangumi():
    """API: 在 Bangumi 搜索番剧"""
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify({"error": "缺少搜索关键词"}), 400
    
    try:
        results = bangumi_client.search_subjects(keyword, subject_type=2, limit=20)
        return jsonify({
            "status": "success",
            "data": results,
            "count": len(results)
        })
    except Exception as e:
        print(f"[!] Bangumi 搜索失败: {e}", file=sys.stderr)
        return jsonify({"error": f"搜索失败: {str(e)}"}), 500

@app.route('/api/bangumi/subject/<int:subject_id>', methods=['GET'])
def get_bangumi_subject(subject_id):
    """API: 获取 Bangumi 番剧详细信息"""
    try:
        subject_data = bangumi_client.get_subject(subject_id)
        if subject_data:
            return jsonify({
                "status": "success",
                "data": subject_data
            })
        else:
            return jsonify({"error": "无法获取番剧信息"}), 404
    except Exception as e:
        print(f"[!] 获取番剧信息失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/use_bangumi_calendar', methods=['POST'])
def use_bangumi_calendar():
    """API: 使用 Bangumi API 的每日放送数据更新本地数据"""
    try:
        print("[*] 开始使用 Bangumi API 更新数据...")
        
        # 获取 Bangumi 数据
        calendar_data = bangumi_client.get_calendar()
        if not calendar_data:
            return jsonify({"error": "无法获取 Bangumi 数据"}), 500
        
        # 转换格式
        seasonal_list = convert_calendar_to_seasonal_list(calendar_data)
        
        # 获取配置
        config = load_config()
        output_file = config.get('seasonal_fetcher', {}).get('output_file', 'seasonal_anime_list.json')
        
        # 保存到文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(seasonal_list, f, ensure_ascii=False, indent=4)
            
            print(f"[*] 成功保存 {len(seasonal_list)} 部动画到 {output_file}")
            return jsonify({
                "status": "success",
                "message": f"成功从 Bangumi API 获取并保存了 {len(seasonal_list)} 部动画",
                "count": len(seasonal_list)
            })
        except Exception as e:
            print(f"[!] 保存文件失败: {e}", file=sys.stderr)
            return jsonify({"error": f"保存文件失败: {str(e)}"}), 500
            
    except Exception as e:
        print(f"[!] 更新失败: {e}", file=sys.stderr)
        return jsonify({"error": f"更新失败: {str(e)}"}), 500

@app.route('/api/bangumi/episodes/<int:subject_id>', methods=['GET'])
def get_bangumi_episodes(subject_id):
    """API: 获取番剧的章节列表"""
    try:
        episode_type = request.args.get('type', 0, type=int)
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        episodes = bangumi_client.get_episodes(subject_id, episode_type, limit, offset)
        return jsonify({
            "status": "success",
            "data": episodes,
            "total": len(episodes)
        })
    except Exception as e:
        print(f"[!] 获取章节信息失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/characters/<int:subject_id>', methods=['GET'])
def get_bangumi_characters(subject_id):
    """API: 获取番剧的角色和声优信息"""
    try:
        characters = bangumi_client.get_characters(subject_id)
        return jsonify({
            "status": "success",
            "data": characters,
            "total": len(characters)
        })
    except Exception as e:
        print(f"[!] 获取角色信息失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/persons/<int:subject_id>', methods=['GET'])
def get_bangumi_persons(subject_id):
    """API: 获取番剧的制作人员信息"""
    try:
        persons = bangumi_client.get_persons(subject_id)
        return jsonify({
            "status": "success",
            "data": persons,
            "total": len(persons)
        })
    except Exception as e:
        print(f"[!] 获取制作人员信息失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/relations/<int:subject_id>', methods=['GET'])
def get_bangumi_relations(subject_id):
    """API: 获取番剧的关联条目（前作、续集等）"""
    try:
        relations = bangumi_client.get_subject_relations(subject_id)
        return jsonify({
            "status": "success",
            "data": relations,
            "total": len(relations)
        })
    except Exception as e:
        print(f"[!] 获取关联信息失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/user/<username>/collections', methods=['GET'])
def get_user_collections(username):
    """API: 获取用户的收藏信息"""
    try:
        subject_type = request.args.get('subject_type', 2, type=int)
        collection_type = request.args.get('type', type=int)
        limit = request.args.get('limit', 30, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        collections = bangumi_client.get_user_collection(
            username, subject_type, collection_type, limit, offset
        )
        return jsonify({
            "status": "success",
            "data": collections
        })
    except Exception as e:
        print(f"[!] 获取用户收藏失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/user/<username>/episode-status/<int:subject_id>', methods=['GET'])
def get_user_episode_status(username, subject_id):
    """API: 获取用户对某个番剧的章节观看状态"""
    try:
        episode_type = request.args.get('type', 0, type=int)
        
        status = bangumi_client.get_user_episode_collection(username, subject_id, episode_type)
        return jsonify({
            "status": "success",
            "data": status
        })
    except Exception as e:
        print(f"[!] 获取观看状态失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/episode/<int:subject_id>/<int:episode_id>/status', methods=['PATCH'])
def update_episode_status(subject_id, episode_id):
    """API: 更新章节观看状态（需要用户认证）"""
    try:
        data = request.json
        collection_type = data.get('type', 2)  # 默认标记为"看过"
        
        success = bangumi_client.update_episode_collection(subject_id, episode_id, collection_type)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "章节状态已更新"
            })
        else:
            return jsonify({"error": "更新失败"}), 500
    except Exception as e:
        print(f"[!] 更新章节状态失败: {e}", file=sys.stderr)
        return jsonify({"error": f"更新失败: {str(e)}"}), 500

@app.route('/api/bangumi/episodes/<int:subject_id>/batch-status', methods=['PATCH'])
def batch_update_episode_status(subject_id):
    """API: 批量更新章节观看状态（需要用户认证）"""
    try:
        data = request.json
        episode_ids = data.get('episode_ids', [])
        collection_type = data.get('type', 2)  # 默认标记为"看过"
        
        if not episode_ids:
            return jsonify({"error": "缺少 episode_ids 参数"}), 400
        
        success = bangumi_client.batch_update_episode_collection(subject_id, episode_ids, collection_type)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"已批量更新 {len(episode_ids)} 个章节的状态"
            })
        else:
            return jsonify({"error": "批量更新失败"}), 500
    except Exception as e:
        print(f"[!] 批量更新章节状态失败: {e}", file=sys.stderr)
        return jsonify({"error": f"批量更新失败: {str(e)}"}), 500

@app.route('/api/bangumi/subject/<int:subject_id>/topics', methods=['GET'])
def get_subject_topics(subject_id):
    """API: 获取番剧的讨论话题列表"""
    try:
        limit = request.args.get('limit', 30, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        topics = bangumi_client.get_subject_topics(subject_id, limit, offset)
        return jsonify({
            "status": "success",
            "data": topics.get("data", []),
            "total": topics.get("total", 0)
        })
    except Exception as e:
        print(f"[!] 获取讨论话题失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/topic/<int:topic_id>', methods=['GET'])
def get_topic_detail(topic_id):
    """API: 获取话题详细内容和回复"""
    try:
        topic = bangumi_client.get_topic_detail(topic_id)
        return jsonify({
            "status": "success",
            "data": topic
        })
    except Exception as e:
        print(f"[!] 获取话题详情失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/topic/<int:topic_id>/reply', methods=['POST'])
def create_topic_reply(topic_id):
    """API: 发表话题回复（需要用户认证）"""
    try:
        data = request.json
        content = data.get('content', '')
        related_id = data.get('related_id')
        
        if not content:
            return jsonify({"error": "回复内容不能为空"}), 400
        
        success = bangumi_client.create_topic_reply(topic_id, content, related_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "回复发表成功"
            })
        else:
            return jsonify({"error": "发表失败"}), 500
    except Exception as e:
        print(f"[!] 发表回复失败: {e}", file=sys.stderr)
        return jsonify({"error": f"发表失败: {str(e)}"}), 500

@app.route('/api/bangumi/episode/<int:episode_id>/comments', methods=['GET'])
def get_episode_comments(episode_id):
    """API: 获取章节的评论/吐槽"""
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        comments = bangumi_client.get_episode_comments(episode_id, limit, offset)
        return jsonify({
            "status": "success",
            "data": comments.get("data", []),
            "total": comments.get("total", 0)
        })
    except Exception as e:
        print(f"[!] 获取章节评论失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

@app.route('/api/bangumi/subject/<int:subject_id>/comments', methods=['GET'])
def get_subject_comments(subject_id):
    """API: 获取番剧的评论/评价"""
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        comments = bangumi_client.get_subject_comments(subject_id, limit, offset)
        return jsonify({
            "status": "success",
            "data": comments.get("data", []),
            "total": comments.get("total", 0)
        })
    except Exception as e:
        print(f"[!] 获取番剧评论失败: {e}", file=sys.stderr)
        return jsonify({"error": f"获取失败: {str(e)}"}), 500

# --- 启动服务器 ---
if __name__ == '__main__':
    print("[*] 启动追番管理服务器...")
    print("[*] 请在浏览器中打开 http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)