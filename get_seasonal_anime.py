import requests
import datetime
import sys
import json
import os

# 配置文件名 (唯一的硬编码常量)
CONFIG_FILE = 'config.json'

def load_config():
    """从 config.json 加载配置"""
    if not os.path.exists(CONFIG_FILE):
        print(f"[!] 配置文件 {CONFIG_FILE} 未找到!", file=sys.stderr)
        return None, None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 返回全局配置和此脚本的特定配置
            return config.get('global_settings'), config.get('seasonal_fetcher')
    except Exception as e:
        print(f"[!] 读取或解析 {CONFIG_FILE} 失败: {e}", file=sys.stderr)
        return None, None

def save_output(data, filename):
    """将数据保存到指定的JSON文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"\n[*] 成功将 {len(data)} 条结果保存到: {filename}")
    except Exception as e:
        print(f"[!] 保存文件 {filename} 失败: {e}", file=sys.stderr)

def fetch_all_anime_data(data_url):
    """从URL下载完整的番剧数据.json文件"""
    print(f"[*] 正在从 {data_url} 下载完整的番剧数据...")
    try:
        response = requests.get(data_url, timeout=30)
        response.raise_for_status()
        print("[*] 数据下载完毕, 准备解析...")
        data = response.json()
        return data.get('items', [])
    except Exception as e:
        print(f"[!] 下载数据失败: {e}", file=sys.stderr)
        return None

def filter_and_extract_seasonal_anime(all_anime, year, months, jst_tz, chinese_weekdays):
    """
    遍历所有番剧, 筛选出指定季度的新番, 并提取信息。
    """
    seasonal_anime_list = []

    for item in all_anime:
        try:
            begin_str = item.get('begin')
            if not begin_str:
                continue

            utc_datetime = datetime.datetime.fromisoformat(begin_str.replace('Z', '+00:00'))
            jst_datetime = utc_datetime.astimezone(jst_tz)
            jst_date = jst_datetime.date()

            if jst_date.year == year and jst_date.month in months:
                weekday_index = jst_date.weekday()
                # 检查索引是否有效
                if 0 <= weekday_index < len(chinese_weekdays):
                    weekday_str = chinese_weekdays[weekday_index]
                else:
                    weekday_str = "未知" # 或者其他默认值

                begin_time_str = jst_datetime.strftime('%H:%M')
                title_jp = item.get('title', 'N/A')
                title_cn_list = item.get('titleTranslate', {}).get('zh-Hans', [])
                primary_title = title_cn_list[0] if title_cn_list else title_jp
                official_site = item.get('officialSite', 'N/A')
                begin_date_str = jst_date.isoformat()

                seasonal_anime_list.append({
                    'primary_title': primary_title,
                    'all_cn_names': title_cn_list,
                    'jp_name': title_jp,
                    'begin_date': begin_date_str,
                    'weekday': weekday_str,
                    'begin_time': begin_time_str,
                    'site': official_site
                })
        except Exception as e:
             # 增加错误打印，方便调试
             # print(f"[Debug] 跳过一条解析错误的条目: {item.get('title')}, 错误: {e}", file=sys.stderr)
             pass # 保持跳过，避免因单个条目错误中断

    seasonal_anime_list.sort(key=lambda x: (x['begin_date'], x['begin_time']))
    return seasonal_anime_list

def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    # 1. 从 config.json 加载配置
    global_config, script_config = load_config()
    if not global_config or not script_config:
        return

    # 2. 解析全局配置
    data_url = global_config.get('bangumi_data_url')
    jst_offset = global_config.get('jst_timezone_offset', 9) # 默认+9
    chinese_weekdays = global_config.get('chinese_weekdays')
    jst_tz = datetime.timezone(datetime.timedelta(hours=jst_offset))

    # 3. 解析脚本特定配置
    target_year = script_config.get('target_year')
    target_months = script_config.get('target_months')
    output_file = script_config.get('output_file')

    # 4. 检查配置是否齐全
    if not all([data_url, chinese_weekdays, isinstance(target_year, int), isinstance(target_months, list), output_file]):
        print("[!] 配置文件 'global_settings' 或 'seasonal_fetcher' 中缺少必要字段或类型错误。", file=sys.stderr)
        # 打印更详细的错误信息
        print(f"    - data_url: {data_url}", file=sys.stderr)
        print(f"    - chinese_weekdays: {chinese_weekdays}", file=sys.stderr)
        print(f"    - target_year: {target_year} (type: {type(target_year)})", file=sys.stderr)
        print(f"    - target_months: {target_months} (type: {type(target_months)})", file=sys.stderr)
        print(f"    - output_file: {output_file}", file=sys.stderr)
        return

    # 5. 执行主逻辑
    all_data = fetch_all_anime_data(data_url)

    if all_data:
        season_str = f"{target_year}年 {target_months[0]}月"
        print(f"\n--- 正在筛选 {season_str} 的新番 ---")

        seasonal_list = filter_and_extract_seasonal_anime(
            all_data, target_year, target_months, jst_tz, chinese_weekdays
        )

        if not seasonal_list:
            print(f"[!] 未能在数据中找到 {season_str} 的新番。")
            return

        print(f"\n[*] 筛选完毕！共找到 {len(seasonal_list)} 部 {season_str} 新番。")

        # 6. 保存输出
        save_output(seasonal_list, output_file)

if __name__ == "__main__":
    main()