#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BT下载脚本 - 使用Seedr云端下载
从search_results.json读取磁力链接，上传到Seedr，下载完成后传输到本地并删除云端文件
"""

import json
import os
import time
import requests
from seedrcc import Seedr
from contextlib import contextmanager
import sys

# --- 1. 路径定义 ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'data/config.json')
HISTORY_FILE = os.path.join(PROJECT_ROOT, 'data/download_history.json')
SEARCH_RESULTS_FILE = os.path.join(PROJECT_ROOT, 'data/search_results.json')
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, 'anime')

# --- 2. 辅助功能 ---
def print_error(msg): print(f"❌ {msg}", file=sys.stderr)
def print_info(msg): print(f"ℹ️ {msg}")
def print_success(msg): print(f"✅ {msg}")

def load_config():
    """加载配置文件"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print_error(f"加载配置文件失败: {e}")
        return None

def load_json(file_path, default=None):
    """安全加载JSON文件"""
    if default is None:
        default = []
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    except Exception as e:
        print_error(f"加载 {file_path} 失败: {e}")
        return default

def save_json(file_path, data):
    """安全保存JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print_error(f"保存 {file_path} 失败: {e}")
        return False


def login_to_seedr():
    """使用配置文件中的账号密码登录Seedr"""
    print_info("加载配置文件...")
    sys.stdout.flush()
    config = load_config()
    if not config:
        return None
        
    global_settings = config.get('global_settings', {})
    email = global_settings.get('seedr_email')
    password = global_settings.get('seedr_password')
    
    if not email or not password:
        print_error("config.json 中未找到 seedr_email 或 seedr_password")
        return None
    
    try:
        print_info(f"正在使用账号 {email} 登录 Seedr...")
        sys.stdout.flush()
        client = Seedr.from_password(email, password)
        print_info("获取用户设置...")
        sys.stdout.flush()
        settings = client.get_settings()
        print_success(f"Seedr 登录成功，用户: {settings.account.username}")
        return client
    except Exception as e:
        print_error(f"Seedr 登录失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def is_already_downloaded(magnet, history):
    """检查磁力链接是否已经下载过"""
    return magnet in history.get('all_downloaded_magnets', [])


def add_to_history(magnet, anime_title, episode_num, history):
    """(新) 将磁力链接和最高集数添加到历史记录"""
    
    # 1. 更新磁力链接列表
    if 'all_downloaded_magnets' not in history:
        history['all_downloaded_magnets'] = []
    
    if magnet not in history['all_downloaded_magnets']:
        history['all_downloaded_magnets'].append(magnet)
        print_info(f"磁力链接已添加到历史: {magnet}")
    
    # 2. 更新最高集数
    if 'highest_episode_downloaded' not in history:
        history['highest_episode_downloaded'] = {}
        
    # 确保 anime_title 是有效的
    if not anime_title or anime_title == 'Unknown':
        print_error("无法更新最高集数，因为 'anime_title' 未知")
        return

    if anime_title not in history['highest_episode_downloaded']:
        history['highest_episode_downloaded'][anime_title] = 0.0

    try:
        # 确保是浮点数比较
        current_max = float(history['highest_episode_downloaded'][anime_title])
        new_ep = float(episode_num)

        if new_ep > current_max:
            history['highest_episode_downloaded'][anime_title] = new_ep
            print_success(f"✅ 更新 {anime_title} 的最高集数为: {new_ep}")
        else:
            print_info(f"ℹ️ {anime_title} 的集数 {new_ep} 不高于历史记录 {current_max}")
            
    except ValueError:
        print_error(f"集数 {episode_num} 不是有效数字，无法更新历史。")
    except Exception as e:
        print_error(f"更新最高集数时出错: {e}")

def wait_for_seedr_download(client, torrent_id, title, skip_initial_wait=False):
    """等待Seedr完成下载"""
    if not skip_initial_wait:
        print_info("等待30秒让Seedr处理种子...")
        time.sleep(30)
    
    print_info(f"检查 Seedr 下载状态: {title}")
    
    # 提取关键词 - 改进版
    def extract_keywords(title):
        """从标题中提取关键词用于匹配"""
        # 移除方括号和括号内容，但保留数字
        import re
        # 提取集数
        episode_match = re.search(r'[\[【](\d{1,3})[\]】]', title)
        episode_num = episode_match.group(1) if episode_match else None
        
        # 移除字幕组信息
        cleaned = re.sub(r'[\[【][^\]】]*(?:字幕|Sub)[^\]】]*[\]】]', '', title, flags=re.IGNORECASE)
        # 移除分辨率信息
        cleaned = re.sub(r'\b(?:1080p|720p|2160p|4K|WebRip|BDRip|BluRay|HEVC|x264|x265)\b', '', cleaned, flags=re.IGNORECASE)
        # 移除语言信息
        cleaned = re.sub(r'[\[【](?:简|繁|日|英|内嵌|外挂)+.*?[\]】]', '', cleaned)
        
        # 分割并清理
        keywords = []
        # 按常见分隔符分割
        parts = re.split(r'[\s\-_/【】\[\]]+', cleaned)
        for part in parts:
            part = part.strip()
            # 保留有意义的词（字母数字组合、中文、长度>1的词）
            if part and (len(part) > 1 or re.search(r'[\u4e00-\u9fff]', part)):
                keywords.append(part.lower())
        
        # 添加集数作为关键词
        if episode_num:
            keywords.append(episode_num)
        
        return [kw for kw in keywords if kw][:8]  # 返回前8个关键词
    
    title_keywords = extract_keywords(title)
    print_info(f"提取的匹配关键词: {title_keywords}")
    
    # 最多检查5次，每次间隔30秒
    for attempt in range(5):
        try:
            contents = client.list_contents()
            
            print_info(f"Seedr 根目录文件数: {len(contents.files)}, 文件夹数: {len(contents.folders)}")
            
            # 寻找匹配的文件或文件夹
            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
            
            # 先检查直接文件
            for file in contents.files:
                file_ext = os.path.splitext(file.name.lower())[1]
                if file_ext in video_extensions:
                    print_info(f"检查文件: {file.name}")
                    # 检查文件名是否匹配（至少匹配2个关键词）
                    match_count = sum(1 for keyword in title_keywords if keyword in file.name.lower())
                    if match_count >= 2:
                        print_success(f"✅ 发现匹配的视频文件: {file.name} (匹配{match_count}个关键词)")
                        return file, 'file'
            
            # 检查文件夹
            for folder in contents.folders:
                print_info(f"检查文件夹: {folder.name}")
                try:
                    folder_contents = client.list_contents(folder_id=folder.id)
                    
                    # 检查文件夹内的视频文件
                    for file in folder_contents.files:
                        file_ext = os.path.splitext(file.name.lower())[1]
                        if file_ext in video_extensions:
                            print_info(f"  └─ 检查文件: {file.name}")
                            # 检查文件名是否匹配（至少匹配2个关键词）
                            match_count = sum(1 for keyword in title_keywords if keyword in file.name.lower())
                            if match_count >= 2:
                                print_success(f"✅ 发现文件夹中的匹配视频: {folder.name}/{file.name} (匹配{match_count}个关键词)")
                                return file, 'file'
                    
                    # 如果文件夹名包含关键词，可能整个文件夹都是相关的
                    folder_match_count = sum(1 for keyword in title_keywords if keyword in folder.name.lower())
                    if folder_match_count >= 2:
                        # 检查文件夹是否有内容
                        if folder_contents.files:
                            print_success(f"✅ 发现匹配的文件夹: {folder.name} (匹配{folder_match_count}个关键词)")
                            return folder, 'folder'
                            
                except Exception as e:
                    print_info(f"跳过文件夹 {folder.name}: {e}")
                    continue
            
            if attempt < 4:  # 不是最后一次尝试
                print_info(f"第 {attempt + 1} 次检查未找到文件，30秒后重试...")
                time.sleep(30)
            
        except Exception as e:
            print_error(f"检查下载状态时出错: {e}")
            if attempt < 4:
                time.sleep(30)
    
    print_error("检查5次后仍未找到匹配的下载文件")
    return None, None

def download_from_seedr(client, item, item_type, save_dir):
    """从Seedr下载文件到本地"""
    downloaded_files = []
    
    try:
        if item_type == 'file':
            # 单个文件
            file_result = client.fetch_file(item.folder_file_id)
            if not file_result or not file_result.url:
                print_error(f"无法获取文件下载链接: {item.name}")
                return []
            
            save_path = os.path.join(save_dir, item.name)
            print_info(f"下载文件: {item.name} ({item.size / (1024*1024):.1f} MB)")
            
            with requests.get(file_result.url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0)) or item.size
                downloaded = 0
                
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\r进度: {progress:.1f}% ({downloaded/(1024*1024):.1f}/{total_size/(1024*1024):.1f} MB)", end='', flush=True)
                
                print()  # 新行
                downloaded_files.append(save_path)
                
        elif item_type == 'folder':
            # 文件夹 - 下载其中的视频文件
            folder_contents = client.list_contents(folder_id=item.id)
            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
            
            video_files_found = False
            for file in folder_contents.files:
                file_ext = os.path.splitext(file.name.lower())[1]
                if file_ext in video_extensions:
                    video_files_found = True
                    file_result = client.fetch_file(file.folder_file_id)
                    if file_result and file_result.url:
                        save_path = os.path.join(save_dir, file.name)
                        print_info(f"下载视频文件: {file.name} ({file.size / (1024*1024):.1f} MB)")
                        
                        with requests.get(file_result.url, stream=True) as r:
                            r.raise_for_status()
                            total_size = int(r.headers.get('content-length', 0)) or file.size
                            downloaded = 0
                            
                            with open(save_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                                        downloaded += len(chunk)
                                        
                                        if total_size > 0:
                                            progress = (downloaded / total_size) * 100
                                            print(f"\r进度: {progress:.1f}% ({downloaded/(1024*1024):.1f}/{total_size/(1024*1024):.1f} MB)", end='', flush=True)
                            
                            print()  # 新行
                            downloaded_files.append(save_path)
            
            if not video_files_found:
                print_error(f"文件夹 {item.name} 中未找到视频文件")
        
        return downloaded_files
        
    except Exception as e:
        print_error(f"下载文件时出错: {e}")
        return []

def cleanup_seedr(client, item, item_type):
    """清理Seedr云端文件"""
    try:
        if item_type == 'file':
            result = client.delete_file(item.folder_file_id)
            if result and result.result:
                print_success(f"已删除云端文件: {item.name}")
            else:
                print_error(f"删除云端文件失败: {item.name}")
        elif item_type == 'folder':
            result = client.delete_folder(item.id)
            if result and result.result:
                print_success(f"已删除云端文件夹: {item.name}")
            else:
                print_error(f"删除云端文件夹失败: {item.name}")
    except Exception as e:
        print_error(f"清理云端文件时出错: {e}")


def clear_seedr_account(client):
    """(新增) 登录后立刻清空Seedr云端所有文件和文件夹"""
    print_info("🧹 正在清空 Seedr 云端空间 (防止空间不足)...")
    try:
        # 1. 获取根目录 (folder_id=0) 的所有内容
        contents = client.list_contents(folder_id=0)
        
        files_to_delete = contents.files
        folders_to_delete = contents.folders
        
        if not files_to_delete and not folders_to_delete:
            print_success("☁️ Seedr 云端已是空的。")
            return True

        print_info(f"   发现 {len(files_to_delete)} 个文件 和 {len(folders_to_delete)} 个文件夹/种子。")

        # 2. 删除所有文件
        for file in files_to_delete:
            try:
                print_info(f"   - 正在删除文件: {file.name}")
                client.delete_file(file.folder_file_id)
            except Exception as e:
                print_error(f"   - 删除文件 {file.name} 失败: {e}")

        # 3. 删除所有文件夹 (注意：种子/Torrents 在这里也表现为 'folder')
        for folder in folders_to_delete:
            try:
                print_info(f"   - 正在删除文件夹/种子: {folder.name}")
                client.delete_folder(folder.id) 
            except Exception as e:
                print_error(f"   - 删除文件夹 {folder.name} 失败: {e}")
        
        print_success("✅ Seedr 云端清空完毕。")
        return True

    except Exception as e:
        print_error(f"💥 清空 Seedr 时发生严重错误: {e}")
        print_error("   警告：脚本将继续执行，但可能会因空间不足而失败。")
        return False


# --- 3. 主下载逻辑 ---

def process_single_task(client, task, history, retry_step=1):
    """处理单个下载任务，支持从指定步骤开始重试"""
    magnet = task.get('magnet')
    title = task.get('title', 'Unknown')
    
    if not magnet:
        print_error(f"任务缺少磁力链接: {title}")
        return False
    
    # 检查是否已下载
    if is_already_downloaded(magnet, history):
        print_info(f"跳过已下载: {title}")
        return True
    
    print_info(f"开始处理: {title}")
    if retry_step > 1:
        print_info(f"重试模式：从步骤 {retry_step} 开始")
    
    try:
        # 步骤 1: 添加到Seedr（如果是重试且从步骤2开始，跳过此步骤）
        if retry_step <= 1:
            print_info("步骤 1/4: 添加到 Seedr...")
            result = client.add_torrent(magnet_link=magnet)
            
            if not result:
                print_error("添加到 Seedr 失败")
                return False
            
            print_success(f"已添加到 Seedr: {result.title if hasattr(result, 'title') else 'Unknown'}")
            torrent_id = result.torrent_id if hasattr(result, 'torrent_id') else 'unknown'
        else:
            print_info("步骤 1/4: 跳过（重试模式）")
            torrent_id = 'unknown'

        # 步骤 2: 等待下载完成
        if retry_step <= 2:
            print_info("步骤 2/4: 等待 Seedr 下载完成...")
            skip_initial_wait = (retry_step == 2)  # 如果是从步骤2重试，跳过初始等待
            item, item_type = wait_for_seedr_download(client, torrent_id, title, skip_initial_wait)
            
            if not item:
                print_error("Seedr 下载失败或超时")
                return False
        else:
            print_info("步骤 2/4: 跳过（重试模式）")
            # 重新查找文件
            item, item_type = wait_for_seedr_download(client, 'unknown', title, skip_initial_wait=True)
            if not item:
                print_error("重试时未找到文件")
                return False

        # 步骤 3: 下载到本地
        if retry_step <= 3:
            print_info("步骤 3/4: 下载到本地...")
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            downloaded_files = download_from_seedr(client, item, item_type, DOWNLOAD_DIR)
            
            if not downloaded_files:
                print_error("本地下载失败")
                return False
            
            print_success(f"下载完成，共 {len(downloaded_files)} 个文件")
            for file_path in downloaded_files:
                print_info(f"  - {os.path.basename(file_path)}")
        else:
            print_info("步骤 3/4: 跳过（重试模式）")

        # 步骤 4: 清理云端文件
        print_info("步骤 4/4: 清理云端文件...")
        cleanup_seedr(client, item, item_type)
        
        # 5. 更新历史记录 (修改)
        # 从 task 对象中获取 'anime_title' 和 'episode'
        # 这两个字段是由 search_torrents.py 写入 search_results.json 的
        
        anime_title_from_task = task.get('anime_title')
        episode_num_from_task = task.get('episode')
        
        if not anime_title_from_task or episode_num_from_task is None:
            print_error(f"❌ 任务 {title} 缺少 'anime_title' 或 'episode' 字段，无法更新最高集数！")
            # 仍然只添加磁力链接，以防重复下载
            add_to_history(magnet, "Unknown_Anime", 0, history) 
        else:
            # (修改) 传入所有必需的参数
            add_to_history(magnet, anime_title_from_task, episode_num_from_task, history)
        
        
        return True
        
    except Exception as e:
        print_error(f"处理任务时出错: {e}")
        return False

# --- 4. 主执行函数 ---

def main():
    """主函数：批量下载动漫，按动漫分组智能重试"""
    print("🎬 BT下载脚本启动")
    print("=" * 50)
    
    try:
        # 1. 登录 Seedr
        print_info("开始登录 Seedr...")
        sys.stdout.flush()  # 强制输出
        client = login_to_seedr()
        if not client:
            print_error("无法登录 Seedr，退出")
            return
        
        # 清空云端空间
        print_info("=" * 50)
        clear_seedr_account(client)
        print_info("=" * 50)

        
        # 2. 加载搜索结果和历史记录
        search_results = load_json(SEARCH_RESULTS_FILE, [])
        history = load_json(HISTORY_FILE, {"highest_episode_downloaded": {}, "all_downloaded_magnets": []})
        
        if not search_results:
            print_info("没有待处理的下载任务")
            return
        
        # 3. 按动漫分组任务
        anime_groups = {}
        for task in search_results:
            anime_title = task.get('anime_title', 'Unknown')
            if anime_title not in anime_groups:
                anime_groups[anime_title] = []
            anime_groups[anime_title].append(task)
        
        print_info(f"总共 {len(search_results)} 个任务，分为 {len(anime_groups)} 个动漫组")
        
        all_completed_tasks = []
        all_failed_tasks = []
        
        # 4. 逐个动漫组处理
        for group_idx, (anime_title, anime_tasks) in enumerate(anime_groups.items(), 1):
            print(f"\n{'='*60}")
            print(f"🎯 [{group_idx}/{len(anime_groups)}] 处理动漫组: {anime_title}")
            print(f"📋 任务数量: {len(anime_tasks)}")
            print('='*60)
            
            group_completed = []
            group_failed = []
            
            # 第一轮：正常处理所有任务
            for i, task in enumerate(anime_tasks, 1):
                print(f"\n[{anime_title}] 📥 任务 {i}/{len(anime_tasks)}")
                print(f"🎬 {task.get('title', 'Unknown')}")
                print("-" * 40)
                
                success = process_single_task(client, task, history)
                if success:
                    group_completed.append(task)
                    print_success(f"✅ 任务完成")
                else:
                    group_failed.append(task)
                    print_error(f"❌ 任务失败")
                
                # 任务间休息
                if i < len(anime_tasks):
                    print_info("⏸️  等待3秒后处理下一个任务...")
                    time.sleep(3)
            
            # 重试失败的任务（每个动漫组最多重试2轮）
            retry_round = 1
            max_retries = 2
            
            while group_failed and retry_round <= max_retries:
                print(f"\n🔄 [{anime_title}] 第 {retry_round} 轮重试")
                print(f"📋 剩余失败任务: {len(group_failed)} 个")
                print("-" * 40)
                
                current_failed = group_failed.copy()
                group_failed = []
                
                for i, task in enumerate(current_failed, 1):
                    print(f"\n🔄 重试 {i}/{len(current_failed)}: {task.get('title', 'Unknown')}")
                    
                    # 重试时从步骤2开始（跳过上传，30s等待后检查）
                    success = process_single_task(client, task, history, retry_step=2)
                    if success:
                        group_completed.append(task)
                        print_success(f"✅ 重试成功")
                    else:
                        group_failed.append(task)
                        print_error(f"❌ 重试仍失败")
                    
                    # 重试任务间休息更长时间
                    if i < len(current_failed):
                        print_info("⏸️  重试间隔5秒...")
                        time.sleep(5)
                
                retry_round += 1
            
            # 输出动漫组结果
            print(f"\n📊 [{anime_title}] 组内统计:")
            print(f"✅ 成功: {len(group_completed)}/{len(anime_tasks)}")
            print(f"❌ 失败: {len(group_failed)}/{len(anime_tasks)}")
            
            if group_failed:
                print_error(f"❌ 最终失败的任务:")
                for task in group_failed:
                    print_error(f"   - {task.get('title', 'Unknown')}")
            
            all_completed_tasks.extend(group_completed)
            all_failed_tasks.extend(group_failed)
            
            # 动漫组间休息
            if group_idx < len(anime_groups):
                print_info("⏸️  动漫组间等待10秒...")
                time.sleep(10)
        
        # 5. 保存结果
        save_json(HISTORY_FILE, history)
        
        # 6. 更新搜索结果文件（移除成功的任务）
        if all_failed_tasks:
            save_json(SEARCH_RESULTS_FILE, all_failed_tasks)
            print_info(f"💾 保留 {len(all_failed_tasks)} 个失败任务供下次重试")
        else:
            save_json(SEARCH_RESULTS_FILE, [])
            print_success("🎉 所有任务完成，搜索结果已清空")
        
        # 7. 显示最终统计
        print("\n" + "=" * 60)
        print("🏆 最终统计报告")
        print("=" * 60)
        print_info(f"📊 总任务数: {len(search_results)}")
        print_success(f"✅ 成功完成: {len(all_completed_tasks)} 个")
        if all_failed_tasks:
            print_error(f"❌ 最终失败: {len(all_failed_tasks)} 个")
        print_info(f"📁 历史记录: {len(history.get('all_downloaded_magnets', []))} 个磁力链接")
        print_info(f"🎬 处理动漫: {len(anime_groups)} 个")
        
        if len(all_failed_tasks) == 0:
            print_success("\n🎉 恭喜！所有下载任务都已完成！")
        else:
            print_error(f"\n⚠️  注意：还有 {len(all_failed_tasks)} 个任务未完成，已保存供下次重试")
            
    except KeyboardInterrupt:
        print_info("\n⌨️  用户中断，正在退出...")
    except Exception as e:
        print_error(f"💥 程序出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 下载脚本执行完毕")

# --- 5. 脚本入口 ---

if __name__ == "__main__":
    main()
    print("--- BT 下载脚本执行完毕 ---")