#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bangumi 自动追番调度器
使用 schedule 库定时执行搜索和下载任务，并作为后台服务运行。
"""

import schedule
import time
import datetime
import subprocess
import sys
import os
import pytz # 用于处理时区
import traceback # 用于打印错误堆栈

# --- 路径定义 ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SEARCH_SCRIPT = os.path.join(PROJECT_ROOT, 'search_torrents.py')
DOWNLOAD_SCRIPT = os.path.join(PROJECT_ROOT, 'download_bt.py')
LOG_FILE = os.path.join(PROJECT_ROOT, 'scheduler.log') # 日志文件

# --- 配置 ---
# (重要) 请确保您的服务器时区设置正确，或者在此处明确指定
# 我们将使用 Asia/Tokyo (JST) 作为目标时区
TARGET_TIMES_JST = ["05:00", "15:00"]
TARGET_TZ = pytz.timezone('Asia/Tokyo')

# --- 辅助函数 ---
def print_log(msg, level="INFO"):
    """记录日志到文件和控制台"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] [{level}] {msg}"
    print(log_line) # 输出到 systemd journal 或控制台
    try:
        # 尝试追加到日志文件
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    except Exception as e:
        # 如果日志写入失败，只打印到控制台
        print(f"[{timestamp}] [ERROR] Failed to write to log file: {e}")

def run_script(script_path):
    """运行指定的 Python 脚本"""
    script_name = os.path.basename(script_path)
    print_log(f"--- 开始执行子脚本: {script_name} ---")
    if not os.path.exists(script_path):
        print_log(f"错误：脚本文件未找到: {script_path}", level="ERROR")
        return False

    try:
        python_executable = sys.executable
        process = subprocess.run(
            [python_executable, script_path],
            check=True,
            capture_output=True, # 捕获输出以便记录
            text=True,
            encoding='utf-8'
        )
        
        # 记录子脚本的标准输出
        if process.stdout:
            print_log(f"--- {script_name} 输出 ---")
            
            # --- *** 修改处：过滤下载脚本的日志 V2 *** ---
            is_download_script = (script_path == DOWNLOAD_SCRIPT)
            
            # 状态标志，用于只记录一次 0% 和 100%
            has_logged_start = False
            has_logged_completion = False

            for line in process.stdout.splitlines():
                log_this_line = True  # 默认记录所有行

                if is_download_script and "进度:" in line:
                    # 如果是下载脚本，并且是进度行
                    
                    # 检查是否为 0% 进度
                    # (增加 " 0%" 兼容性)
                    if (" 0.0%" in line or " 0%" in line) and not has_logged_start:
                        log_this_line = True
                        has_logged_start = True # 标记已记录
                    
                    # 检查是否为 100% 进度
                    # (增加 "100%" 兼容性)
                    elif ("100.0%" in line or "100%" in line) and not has_logged_completion:
                        log_this_line = True
                        has_logged_completion = True # 标记已记录
                    
                    # 其他所有进度行 (非0%, 非100%, 或重复的0/100)
                    else:
                        log_this_line = False # 不记录
                
                if log_this_line:
                    print_log(f"  {line}")
            # --- *** 修改结束 *** ---

            print_log(f"--- {script_name} 输出结束 ---")

        print_log(f"子脚本 '{script_name}' 执行成功。", level="SUCCESS")
        return True

    except FileNotFoundError:
        print_log(f"错误：找不到 Python 解释器 '{python_executable}'", level="ERROR")
        return False
    except subprocess.CalledProcessError as e:
        print_log(f"错误：脚本 '{script_name}' 执行失败。返回码: {e.returncode}", level="ERROR")
        # 记录子脚本的错误输出
        if e.stderr:
            print_log(f"--- {script_name} 错误输出 ---", level="ERROR")
            for line in e.stderr.splitlines():
                print_log(f"  {line}", level="ERROR")
            print_log(f"--- {script_name} 错误输出结束 ---", level="ERROR")
        return False
    except Exception as e:
        print_log(f"运行脚本 '{script_name}' 时发生意外错误: {e}", level="ERROR")
        # 打印详细错误堆栈信息
        traceback.print_exc()
        return False

def run_job():
    """定义要定时执行的任务：搜索并下载"""
    run_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    print_log(f"====== 作业开始 (ID: {run_id}) ======")

    search_success = run_script(SEARCH_SCRIPT)

    if search_success:
        print_log("搜索任务成功，准备执行下载任务...")
        time.sleep(5) # 在下载前稍作停顿
        download_success = run_script(DOWNLOAD_SCRIPT)
        if not download_success:
             print_log("下载任务执行失败。", level="WARNING")
    else:
        print_log("搜索任务失败，跳过本次下载任务。", level="WARNING")

    print_log(f"====== 作业结束 (ID: {run_id}) ======")

# --- 主调度逻辑 ---
def main():
    print_log("====== 🚀 启动 Bangumi 自动追番调度器 ======")
    print_log(f"项目根目录: {PROJECT_ROOT}")
    print_log(f"日志文件: {LOG_FILE}")
    print_log(f"目标时区: {TARGET_TZ.zone}")
    print_log(f"计划执行时间 (JST): {', '.join(TARGET_TIMES_JST)}")

    # 清除旧计划
    print_log("正在清除已存在的计划任务...")
    schedule.clear()
    print_log("计划任务已清除。")

    # 设置定时任务
    job_count = 0
    for time_str in TARGET_TIMES_JST:
        print_log(f"尝试设置每日任务于 {TARGET_TZ.zone} {time_str} 执行...")
        try:
            # 尝试使用带时区的 at() 方法
            schedule.every().day.at(time_str, TARGET_TZ).do(run_job)
            print_log(f"✅ 成功设置每日任务于 {time_str} {TARGET_TZ.zone}")
            job_count += 1
        except TypeError:
            # 备用方案
            print_log(f"⚠️ 警告：当前 schedule 库版本可能不支持时区参数。", level="WARNING")
            print_log(f"    将基于服务器本地时间 {time_str} 设置任务。", level="WARNING")
            print_log(f"    👉 请确保服务器时区已设为 '{TARGET_TZ.zone}' 以保证准确执行！", level="WARNING")
            schedule.every().day.at(time_str).do(run_job)
            print_log(f"✅ 成功设置每日任务于 {time_str} (服务器本地时间)")
            job_count += 1
        except Exception as e:
            print_log(f"❌ 设置任务 {time_str} 失败: {e}", level="ERROR")


    if job_count == len(TARGET_TIMES_JST):
         print_log(f"====== ✅ 调度器初始化成功，共设置 {job_count} 个任务。进入主循环... ======")
    else:
         print_log(f"====== ⚠️ 调度器初始化有误，仅设置 {job_count}/{len(TARGET_TIMES_JST)} 个任务。进入主循环... ======", level="WARNING")

    # 主循环
    last_log_time = None # 初始化上次日志时间
    while True:
        try:
            pending_jobs = schedule.get_jobs()
            if not pending_jobs:
                print_log("错误：没有设置任何计划任务。退出循环。", level="ERROR")
                break

            # --- *** 修正处：调用 next_run() 函数 *** ---
            next_run_datetime = schedule.next_run()
            # --- *** 修正结束 *** ---

            now = datetime.datetime.now(TARGET_TZ)

            if next_run_datetime: # 检查是否成功获取到时间
                # 每隔约1小时记录一次下一个任务时间
                log_interval_passed = (last_log_time is None) or ((now - last_log_time).total_seconds() > 3600)
                if log_interval_passed:
                    # 使用获取到的 next_run_datetime 对象
                    next_run_local = next_run_datetime.astimezone(TARGET_TZ) # 转换为目标时区显示
                    print_log(f"🕒 等待下一个任务... 下次运行时间: {next_run_local.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
                    last_log_time = now # 更新上次记录时间

            # 运行到点的任务
            schedule.run_pending()
            # 短暂休眠，避免CPU空转
            time.sleep(1)

        except Exception as loop_e:
            print_log(f"主循环执行时出错: {loop_e}", level="ERROR")
            traceback.print_exc() # 打印错误细节
            time.sleep(60) # 出错后等待1分钟再重试


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_log("====== 🛑 用户中断，调度器正在退出 ======")
    except Exception as e:
        print_log(f"====== 🔥 调度器发生严重错误: {e} ======", level="CRITICAL")
        traceback.print_exc()

