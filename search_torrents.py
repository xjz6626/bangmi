#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动漫种子搜索脚本
从animes.garden搜索动漫种子，生成下载任务队列
"""

import requests
import sys
import json
import os
import datetime
import re
import urllib.parse

# --- 路径定义 ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.json')

# --- 辅助函数 ---
def print_error(msg): print(f"❌ {msg}", file=sys.stderr)
def print_info(msg): print(f"ℹ️ {msg}")
def print_success(msg): print(f"✅ {msg}")

def load_config():
    """加载配置文件"""
    if not os.path.exists(CONFIG_FILE):
        print_error(f"配置文件 {CONFIG_FILE} 未找到!")
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print_error(f"读取配置文件失败: {e}")
        return None

def load_json_file(filename, default_data):
    """加载JSON文件"""
    absolute_path = os.path.join(PROJECT_ROOT, filename)
    
    if not os.path.exists(absolute_path):
        print_info(f"文件 {absolute_path} 未找到，创建默认文件")
        save_json_file(filename, default_data)
        return default_data
    
    try:
        with open(absolute_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
            
            # 检查下载历史文件格式
            if filename.endswith("download_history.json"):
                if isinstance(content, dict) and "highest_episode_downloaded" in content and "all_downloaded_magnets" in content:
                    return content
                else:
                    print_error(f"{absolute_path} 格式错误，使用默认结构")
                    return {"highest_episode_downloaded": {}, "all_downloaded_magnets": []}
            else:
                return content if content else default_data
    except Exception as e:
        print_error(f"加载 {absolute_path} 失败: {e}")
        return default_data

def save_json_file(filename, data):
    """保存JSON文件"""
    absolute_path = os.path.join(PROJECT_ROOT, filename)
    try:
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        with open(absolute_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print_error(f"保存 {absolute_path} 失败: {e}")
        return False

def analyze_magnet_trackers(magnet_url):
    """分析磁力链接中的tracker信息 (来自您的代码)"""
    if not magnet_url:
        return {"tracker_count": 0, "trackers": []}
    
    tracker_count = magnet_url.count('&tr=')
    trackers = []
    
    if '&tr=' in magnet_url:
        parts = magnet_url.split('&tr=')
        for part in parts[1:]: # 跳过第一部分（hash部分）
            # URL解码tracker
            tracker = urllib.parse.unquote(part.split('&')[0])
            trackers.append(tracker)
    
    return {
        "tracker_count": tracker_count,
        "trackers": trackers,
        "has_anime_trackers": any("bangumi.moe" in t or "acgtracker" in t or "ktxp.com" in t for t in trackers)
    }

# --- 辅助函数结束 ---

# --- 核心逻辑 (来自您的代码, 无需修改) ---

def get_anime_to_scan(config, seasonal_list):
    """
    根据当前时间计算扫描时间窗口，并根据番剧播出时间决定扫描哪些番剧
    """
    global_config = config.get('global_settings', {})
    jst_offset = global_config.get('jst_timezone_offset', 9)
    chinese_weekdays = global_config.get('chinese_weekdays')
    jst_tz = datetime.timezone(datetime.timedelta(hours=jst_offset))

    if not chinese_weekdays or len(chinese_weekdays) != 7:
        print_error("config.json 中 'chinese_weekdays' 配置错误")
        return {}

    # 获取JST当前时间
    now_jst = datetime.datetime.now(jst_tz)
    print_info(f"当前JST时间: {now_jst.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")

    # 定义扫描时间窗口
    if 0 <= now_jst.hour < 12:
        print_info("执行早上扫描任务（目标：昨天中午12点至今早5点）")
        # 固定时间窗口：前一天12点到当天早上5点
        scan_end_time = now_jst.replace(hour=5, minute=0, second=0, microsecond=0)
        scan_start_time = (scan_end_time - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    elif 12 <= now_jst.hour < 24:
        print_info("执行下午补充扫描任务（目标：3点前48小时）")
        # 固定时间窗口：前天下午3点到今天下午3点
        scan_end_time = now_jst.replace(hour=15, minute=0, second=0, microsecond=0)
        scan_start_time = scan_end_time - datetime.timedelta(hours=48)
    else:
        print_error("无法确定扫描时间窗口")
        return {}

    print_info(f"扫描时间窗口：{scan_start_time.strftime('%Y-%m-%d %H:%M')} 至 {scan_end_time.strftime('%Y-%m-%d %H:%M')}")

    # 构建番剧时间表
    anime_to_scan = {}
    watchlist = config.get('torrent_searcher', {}).get('search_config', {})
    schedule = {}
    
    for item in seasonal_list:
        schedule[item['primary_title']] = item
        for name in item.get('all_cn_names', []):
            if name != item['primary_title']:
                schedule[name] = item

    print_info(f"开始检查 {len(watchlist)} 部关注的番剧")

    for title, search_config in watchlist.items():
        anime_info = schedule.get(title)
        if not anime_info:
            print_info(f"跳过：番剧 '{title}' 在放送表中未找到")
            continue
            
        air_weekday_cn = anime_info.get('weekday')
        air_time_str = anime_info.get('begin_time')
        
        if not air_weekday_cn or not air_time_str:
            print_info(f"跳过：番剧 '{title}' 缺少播出时间信息")
            continue

        try:
            air_weekday_index = chinese_weekdays.index(air_weekday_cn)
            air_hour, air_minute = map(int, air_time_str.split(':'))
            air_time = datetime.time(hour=air_hour, minute=air_minute, tzinfo=jst_tz)
            is_in_window = False

            # 检查播出时间是否在扫描窗口内
            check_dates = [
                scan_end_time.date() - datetime.timedelta(days=2),
                scan_end_time.date() - datetime.timedelta(days=1),
                scan_end_time.date()
            ]
            
            for check_date in check_dates:
                check_dt = datetime.datetime.combine(check_date, air_time)
                if check_dt.weekday() == air_weekday_index and scan_start_time <= check_dt < scan_end_time:
                    is_in_window = True
                    break

            if is_in_window:
                print_success(f"加入扫描队列：{title}（{air_weekday_cn} {air_time_str}）")
                anime_to_scan[title] = search_config
            else:
                print_info(f"跳过：{title}（{air_weekday_cn} {air_time_str}）不在时间窗口内")
                
        except Exception as e:
            print_error(f"处理番剧 {title} 时出错: {e}")

    return anime_to_scan


def parse_episode_number(title):
    """从标题中解析集数"""
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
                    num = float(group)
                    if 0 <= num < 1000:
                        return num
                except ValueError:
                    continue
    return None

def search_and_select_episode(search_title, config, api_url, history_data):
    """搜索并选择最新集数"""
    search_keys = config.get('search_keys', [])
    print(f"\n{'='*50}")
    print_info(f"搜索：{search_title}")
    print_info(f"关键词：{search_keys}")
    print(f"{'='*50}")

    params = {'page': 1, 'pageSize': 30, 'search': search_keys}
    highest_downloaded_ep = history_data.get('highest_episode_downloaded', {}).get(search_title, 0.0)
    downloaded_magnets_set = set(history_data.get('all_downloaded_magnets', []))
    
    print_info(f"历史最高集数：{highest_downloaded_ep}")

    try:
        prepared_request = requests.Request('GET', api_url, params=params).prepare()
        print_info(f"请求URL：{prepared_request.url}")

        with requests.Session() as session:
            response = session.send(prepared_request, timeout=20)
        response.raise_for_status()

        data = response.json()
        resources = data.get('resources', [])

        if not resources:
            print_info("API未返回匹配资源")
            return None

        # 过滤新资源
        new_resources = []
        for r in resources:
            magnet = r.get('magnet')
            if magnet and magnet not in downloaded_magnets_set:
                tracker_count = magnet.count('&tr=')
                print_info(f"新资源：{r.get('title', '未知')} (包含 {tracker_count} 个tracker)")
                new_resources.append(r)

        if not new_resources:
            print_info("所有资源都已下载过")
            return None

        # 找到最新集数
        latest_new_episode_resource = None
        max_new_episode_num = -1.0
        
        print_info(f"找到 {len(new_resources)} 个新资源，开始筛选")

        for r in new_resources:
            title = r.get('title', '')
            episode_num = parse_episode_number(title)
            if episode_num is None:
                print_info(f"跳过：无法解析集数 - {title}")
                continue
            if episode_num > max_new_episode_num:
                max_new_episode_num = episode_num
                latest_new_episode_resource = r

        if latest_new_episode_resource:
            magnet_info = analyze_magnet_trackers(latest_new_episode_resource.get('magnet'))
            print_info(f"新资源最高集数：{max_new_episode_num}")
            print_info(f"标题：{latest_new_episode_resource.get('title')}")
            print_info(f"Tracker数量：{magnet_info['tracker_count']}")
            print_info(f"动漫专用Tracker：{'是' if magnet_info['has_anime_trackers'] else '否'}")
            
            if max_new_episode_num > highest_downloaded_ep:
                print_success(f"该集数 ({max_new_episode_num}) 高于历史记录 ({highest_downloaded_ep})，标记下载")
                if magnet_info['tracker_count'] > 0:
                    print_success(f"磁力链接质量良好：包含 {magnet_info['tracker_count']} 个tracker")
                return latest_new_episode_resource, max_new_episode_num
            else:
                print_info(f"该集数 ({max_new_episode_num}) 不高于历史记录 ({highest_downloaded_ep})，跳过")
                return None
        else:
            print_info("找到新资源但无法解析集数")
            return None

    except Exception as e:
        print_error(f"搜索时发生错误: {e}")
        return None

# --- (关键修改) main 函数 ---

def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    print("🔍 动漫种子搜索脚本")
    print("=" * 50)

    # 1. 加载配置
    config = load_config()
    if not config:
        return
    global_config = config.get('global_settings', {})
    script_config = config.get('torrent_searcher', {})

    # 2. 加载放送表
    # (使用新的辅助函数, 传入 config.json 中的相对路径)
    seasonal_file = config.get('seasonal_fetcher', {}).get('output_file')
    if not seasonal_file:
        print_error("config.json 中 'seasonal_fetcher.output_file' 未配置")
        return
        
    seasonal_list = load_json_file(seasonal_file, [])
    if not seasonal_list:
        print_error(f"{seasonal_file} 为空，请先运行 get_seasonal_anime.py")
        return

    # 3. 加载下载历史 (仅用于读取)
    # (使用新的辅助函数, 传入 config.json 中的相对路径)
    history_file = global_config.get('download_history_file')
    if not history_file:
        print_error("config.json 中 'global_settings.download_history_file' 未配置")
        return
        
    history_data = load_json_file(history_file, {"highest_episode_downloaded": {}, "all_downloaded_magnets": []})

    # 4. 获取今天该扫描的番剧 (不变)
    anime_to_scan = get_anime_to_scan(config, seasonal_list)

    if not anime_to_scan:
        print_info("当前时间窗口内没有需要扫描的番剧")
        return

    # 5. 执行搜索
    print_info(f"开始扫描 {len(anime_to_scan)} 部番剧")
    api_url = global_config.get('torrent_api_url')
    # (修改) output_file 是 search_results.json
    output_file = script_config.get('output_file')
    
    # (修改) 准备一个列表来装完整的“任务对象”
    new_tasks_for_queue = []

    for title, conf in anime_to_scan.items():
        # search_and_select_episode 函数本身不需要修改
        result = search_and_select_episode(title, conf, api_url, history_data)
        
        if result:
            episode_resource, episode_num = result
            
            # (新增) 构建一个完整的任务对象, 供 download_bt.py 使用
            task_object = {
                "anime_title": title, # 追番列表中的标准名称 (用于更新历史)
                "episode": episode_num, # 解析出的集数 (用于更新历史)
                "title": episode_resource.get('title'), # 资源原始标题
                "magnet": episode_resource.get('magnet') # 磁力链接
            }
            new_tasks_for_queue.append(task_object)

    # 6. (修改) 保存结果 -> 安全地追加到任务队列
    if not output_file:
        print_info(f"未配置 'output_file', 仅打印结果。")
    elif new_tasks_for_queue:
        print_info(f"正在将 {len(new_tasks_for_queue)} 个新任务添加到 {output_file}...")
        
        # 6a. (新增) 读取现有的任务队列 (search_results.json)
        existing_tasks = load_json_file(output_file, [])
        
        # 6b. (新增) 合并并去重 (基于磁力链接)
        existing_magnets = {task.get('magnet') for task in existing_tasks}
        added_count = 0
        for new_task in new_tasks_for_queue:
            if new_task.get('magnet') not in existing_magnets:
                existing_tasks.append(new_task)
                existing_magnets.add(new_task.get('magnet'))
                added_count += 1
            else:
                print_info(f"任务 '{new_task.get('title')}' 已存在于队列中, 跳过添加。")
        
        # 6c. (修改) 保存合并后的完整队列
        if save_json_file(output_file, existing_tasks):
            print_success(f"成功将 {added_count} 个新任务追加到 {output_file}")
        else:
            print_error(f"!!! 保存任务队列 {output_file} 失败 !!!")
    
    # 7. (已删除) 此脚本不再负责更新 download_history.json
    
    print_info(f"\n--- 扫描完毕 ---")
    print_success(f"共找到 {len(new_tasks_for_queue)} 个符合更新条件的剧集, 已添加到任务队列。")

if __name__ == "__main__":
    main()