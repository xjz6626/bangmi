import requests
import sys
import json
import os
import datetime
import re

# 配置文件名
CONFIG_FILE = 'config.json'

# --- 辅助函数 (基本不变) ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        print_error(f"配置文件 {CONFIG_FILE} 未找到!")
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print_error(f"读取或解析 {CONFIG_FILE} 失败: {e}")
        return None

def load_json_file(filename, default_data):
    if not os.path.exists(filename):
        print_info(f"文件 {filename} 未找到, 正在创建...")
        # 确保创建时使用正确的默认结构
        if filename.endswith("download_history.json"):
             default_data = {"highest_episode_downloaded": {}, "all_downloaded_magnets": []}
        save_json_file(filename, default_data)
        return default_data
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            # 兼容旧格式或空文件
            content = json.load(f)
            if isinstance(content, dict) and "highest_episode_downloaded" in content and "all_downloaded_magnets" in content:
                return content
            else: # 如果格式不对, 返回默认结构
                print_error(f"{filename} 格式错误, 将使用默认结构。")
                return {"highest_episode_downloaded": {}, "all_downloaded_magnets": []}
    except Exception as e:
        print_error(f"加载 {filename} 失败: {e}")
        return {"highest_episode_downloaded": {}, "all_downloaded_magnets": []}

def save_json_file(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print_error(f"保存 {filename} 失败: {e}")
        return False

def print_error(msg):
    print(f"[!] {msg}", file=sys.stderr)

def print_info(msg):
    print(f"[*] {msg}")

def print_success(msg):
    print(f"[+] {msg}")
# --- 辅助函数结束 ---

# --- 核心逻辑 ---

def get_anime_to_scan(config, seasonal_list):
    # ... (代码同上一版, 基于精确时间窗口) ...
    global_config = config.get('global_settings', {})
    jst_offset = global_config.get('jst_timezone_offset', 9)
    chinese_weekdays = global_config.get('chinese_weekdays')
    jst_tz = datetime.timezone(datetime.timedelta(hours=jst_offset))

    if not chinese_weekdays or len(chinese_weekdays) != 7:
        print_error("config.json 中 'chinese_weekdays' 配置错误。")
        return {}

    now_jst = datetime.datetime.now(jst_tz)
    print_info(f"当前JST时间: {now_jst.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")

    scan_start_time = None
    scan_end_time = None

    if 4 <= now_jst.hour < 12:
        print_info("执行早上扫描任务 (目标: 昨天中午12点至今早5点)...")
        scan_end_time = now_jst.replace(hour=5, minute=0, second=0, microsecond=0)
        scan_start_time = (scan_end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    elif 14 <= now_jst.hour < 20:
        print_info("执行下午扫描任务 (目标: 今早5点至今午3点)...")
        scan_end_time = now_jst.replace(hour=15, minute=0, second=0, microsecond=0)
        scan_start_time = now_jst.replace(hour=5, minute=0, second=0, microsecond=0)

    if scan_start_time is None or scan_end_time is None:
        print_info("当前时间不在预设的扫描时间段内，跳过扫描。")
        return {}

    print_info(f"扫描时间窗口 (JST): [{scan_start_time.strftime('%Y-%m-%d %H:%M:%S')}, {scan_end_time.strftime('%Y-%m-%d %H:%M:%S')})")

    anime_to_scan = {}
    watchlist = config.get('torrent_searcher', {}).get('search_config', {})
    schedule = {}
    for item in seasonal_list:
        schedule[item['primary_title']] = item
        for name in item.get('all_cn_names', []):
             if name != item['primary_title']: schedule[name] = item

    print_info(f"开始检查 {len(watchlist)} 部关注的番剧...")

    for title, search_config in watchlist.items():
        anime_info = schedule.get(title)
        if not anime_info:
            print_info(f"  - [跳过] 番剧 '{title}' 在放送表(schedule)中未找到匹配项。")
            continue
        air_weekday_cn = anime_info.get('weekday')
        air_time_str = anime_info.get('begin_time')
        if not air_weekday_cn or not air_time_str:
            print_info(f"  - [跳过] 番剧 '{title}' 缺少 'weekday' 或 'begin_time' 信息。")
            continue

        try:
            air_weekday_index = chinese_weekdays.index(air_weekday_cn)
            air_hour, air_minute = map(int, air_time_str.split(':'))
            air_time = datetime.time(hour=air_hour, minute=air_minute, tzinfo=jst_tz)
            is_in_window = False
            check_date_1 = scan_end_time.date() - datetime.timedelta(days=1)
            check_dt_1 = datetime.datetime.combine(check_date_1, air_time)
            if check_dt_1.weekday() == air_weekday_index and scan_start_time <= check_dt_1 < scan_end_time:
                is_in_window = True
            check_date_2 = scan_end_time.date()
            check_dt_2 = datetime.datetime.combine(check_date_2, air_time)
            if check_dt_2.weekday() == air_weekday_index and scan_start_time <= check_dt_2 < scan_end_time:
                is_in_window = True

            print_info(f"  - [调试] 番剧 '{title}' 每周 {air_weekday_cn} {air_time_str} 播出 (索引 {air_weekday_index})")
            print_info(f"    [调试] 是否在扫描窗口内? -> {is_in_window}")

            if is_in_window:
                print_info(f"-> {title} (播出时间 {air_time_str}) -> 加入扫描队列")
                anime_to_scan[title] = search_config
        except Exception as e:
             print_error(f"处理番剧 {title} 时出错: {e}")
    return anime_to_scan

def parse_episode_number(title):
    # ... (不变) ...
    match = re.search(
        r'\[(\d{1,3}(?:\.\d{1,2})?)(?:v\d)?\]|'
        r'[\s\.\-_\[](\d{1,3})[\s\.\-_\]]|'
        r'第(\d{1,3})[话話集]|'
        r'(\d{1,3})\s*END',
        title,
        re.IGNORECASE
    )
    if match:
        for group in match.groups():
            if group is not None:
                try:
                    # 尝试转为浮点数以支持 .5 话
                    num = float(group)
                    # 简单的健全性检查，避免过大的数字
                    if 0 <= num < 1000:
                        return num
                except ValueError:
                    continue
    return None # 无法解析时返回None

def search_and_select_episode(search_title, config, api_url, history_data):
    """
    搜索一部番剧, 过滤已下载磁链, 找出新资源中集数最大的,
    再与历史最高集数比较, 只有更新的才返回。
    """
    search_keys = config.get('search_keys', [])
    print(f"\n{'='*50}\n[*] 正在搜索: {search_title} (关键词: {search_keys})\n{'='*50}")

    params = {'page': 1, 'pageSize': 30, 'search': search_keys}
    
    # 获取这部番剧的历史最高集数 (默认为 0.0)
    highest_downloaded_ep = history_data.get('highest_episode_downloaded', {}).get(search_title, 0.0)
    # 获取所有已下载磁链的集合
    downloaded_magnets_set = set(history_data.get('all_downloaded_magnets', []))
    print_info(f"  [*] {search_title} 的历史最高集数记录为: {highest_downloaded_ep}")

    try:
        prepared_request = requests.Request('GET', api_url, params=params).prepare()
        print_info(f"  [Debug] 请求URL: {prepared_request.url}")

        with requests.Session() as session:
            response = session.send(prepared_request, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        resources = data.get('resources', [])
        
        if not resources:
            print_info("  [!] API未返回匹配资源。")
            return None

        # 1. 过滤已下载的磁力链接
        new_resources = []
        for r in resources:
            magnet = r.get('magnet')
            if magnet and magnet not in downloaded_magnets_set:
                new_resources.append(r)
        
        if not new_resources:
            print_info("  [!] 找到了资源, 但根据磁力链接判断都已下载过。")
            return None

        # 2. 在新资源中寻找集数最大的
        latest_new_episode_resource = None
        max_new_episode_num = -1.0
        
        print_info(f"  [*] 找到 {len(new_resources)} 个新资源 (未在历史磁链中), 开始筛选...")
        
        for r in new_resources:
            title = r.get('title', '')
            episode_num = parse_episode_number(title)
            
            if episode_num is None:
                print_info(f"    - [跳过] 无法解析集数: {title}")
                continue
                
            # 更新找到的最大集数
            if episode_num > max_new_episode_num:
                max_new_episode_num = episode_num
                latest_new_episode_resource = r
        
        # 3. (核心修改) 比较新资源的最大集数与历史最高集数
        if latest_new_episode_resource:
            print_info(f"  [*] 新资源中的最高集数为: {max_new_episode_num} (来自: {latest_new_episode_resource.get('title')})")
            
            # 只有当新找到的集数严格大于历史记录时, 才认为它是需要下载的更新
            if max_new_episode_num > highest_downloaded_ep:
                print_success(f"  [+] 该集数 ({max_new_episode_num}) 高于历史记录 ({highest_downloaded_ep}), 标记为需要下载!")
                return latest_new_episode_resource, max_new_episode_num # 返回资源和集数
            else:
                print_info(f"  [!] 该集数 ({max_new_episode_num}) 不高于历史记录 ({highest_downloaded_ep}), 跳过下载。")
                return None # 不需要下载
        else:
            print_info("  [!] 找到了新资源, 但都无法解析集数。")
            return None # 不需要下载

    except Exception as e:
        print_error(f"  [!] 搜索时发生错误: {e}")
        return None

def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    # 1. 加载配置
    config = load_config()
    if not config: return
    global_config = config.get('global_settings', {})
    script_config = config.get('torrent_searcher', {})

    # 2. 加载放送表
    seasonal_file = config.get('seasonal_fetcher', {}).get('output_file')
    if not seasonal_file: print_error("config.json 中 'seasonal_fetcher.output_file' 未配置。"); return
    seasonal_list = load_json_file(seasonal_file, [])
    if not seasonal_list: print_error(f"{seasonal_file} 为空, 请先运行 get_seasonal_anime.py"); return

    # 3. 加载下载历史 (使用新结构)
    history_file = global_config.get('download_history_file')
    if not history_file: print_error("config.json 中 'global_settings.download_history_file' 未配置。"); return
    history_data = load_json_file(history_file, {"highest_episode_downloaded": {}, "all_downloaded_magnets": []})

    # 4. 获取今天该扫描的番剧
    anime_to_scan = get_anime_to_scan(config, seasonal_list)

    if not anime_to_scan:
        return

    # 5. 执行搜索
    print_info(f"--- 开始智能扫描 {len(anime_to_scan)} 部番剧 ---")
    api_url = global_config.get('torrent_api_url')
    output_file = script_config.get('output_file')
    
    newly_found_for_download = [] # 存储真正需要下载的资源
    # (修改) 存储需要更新到历史记录的信息
    history_updates = {'new_magnets': [], 'highest_eps': {}} 

    for title, conf in anime_to_scan.items():
        # (修改) search_and_select_episode 现在返回 (资源, 集数) 或 None
        result = search_and_select_episode(title, conf, api_url, history_data)
        
        if result:
            episode_resource, episode_num = result
            newly_found_for_download.append(episode_resource)
            
            # 记录需要更新的历史信息
            history_updates['new_magnets'].append(episode_resource.get('magnet'))
            history_updates['highest_eps'][title] = episode_num

    # 6. 保存本次找到的需要下载的资源列表 (可选)
    if output_file:
        save_json_file(output_file, newly_found_for_download)
    else:
        print_info(f"未配置 'output_file', 仅打印结果。")

    # 7. (修改) 更新下载历史文件
    if history_updates['new_magnets'] or history_updates['highest_eps']:
        # 更新最高集数
        history_data['highest_episode_downloaded'].update(history_updates['highest_eps'])
        # 添加新的磁力链接 (使用 set 去重后再转回 list)
        existing_magnets = set(history_data.get('all_downloaded_magnets', []))
        existing_magnets.update(history_updates['new_magnets'])
        history_data['all_downloaded_magnets'] = sorted(list(existing_magnets)) # 排序可选

        if save_json_file(history_file, history_data):
            print_success(f"下载历史已更新到 {history_file}")
        else:
             print_error(f"!!! 更新下载历史 {history_file} 失败 !!!")

    print_info(f"\n--- 扫描完毕 ---")
    print_success(f"共找到 {len(newly_found_for_download)} 个符合更新条件的剧集准备下载。")

if __name__ == "__main__":
    main()