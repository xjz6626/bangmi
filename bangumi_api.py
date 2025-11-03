#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bangumi API 客户端
用于获取番剧的详细信息、评分、封面等
API文档: https://bangumi.github.io/api/
"""

import requests
import json
import sys
import os
from typing import List, Dict, Optional

# API 基础 URL
BASE_URL = "https://api.bgm.tv"

# User Agent (根据 Bangumi API 要求)
USER_AGENT = "xjz6626/bangmi-anime-tracker (https://github.com/xjz6626/bangmi)"

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'data/config.json')

def print_error(msg): 
    print(f"❌ {msg}", file=sys.stderr)

def print_info(msg): 
    print(f"ℹ️  {msg}")

def print_success(msg): 
    print(f"✅ {msg}")


def load_bangumi_token_from_config() -> Optional[str]:
    """
    从 config.json 加载 Bangumi API Token
    
    Returns:
        Access Token 或 None
    """
    try:
        if not os.path.exists(CONFIG_FILE):
            print_info("配置文件不存在，将使用无认证模式")
            return None
            
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        token = config.get('global_settings', {}).get('bangumi_api_token', '')
        
        if token and token.strip():
            print_info("已从配置文件加载 Bangumi API Token")
            return token.strip()
        else:
            print_info("配置文件中未设置 Bangumi API Token，将使用无认证模式")
            return None
            
    except Exception as e:
        print_error(f"读取配置文件失败: {e}")
        return None


class BangumiAPI:
    """Bangumi API 客户端"""
    
    def __init__(self, access_token: Optional[str] = None):
        """
        初始化 Bangumi API 客户端
        
        Args:
            access_token: 可选的访问令牌，用于访问 NSFW 内容
        """
        self.base_url = BASE_URL
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json"
        }
        
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
    
    def get_calendar(self) -> List[Dict]:
        """
        获取每日放送信息
        
        Returns:
            按星期几分组的番剧列表
        """
        try:
            print_info("正在从 Bangumi API 获取每日放送信息...")
            response = requests.get(
                f"{self.base_url}/calendar",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            print_success(f"成功获取 {len(data)} 天的放送信息")
            return data
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取每日放送失败: {e}")
            return []
    
    def get_subject(self, subject_id: int) -> Optional[Dict]:
        """
        获取条目详细信息
        
        Args:
            subject_id: 条目 ID
            
        Returns:
            条目详细信息
        """
        try:
            print_info(f"正在获取条目 {subject_id} 的详细信息...")
            response = requests.get(
                f"{self.base_url}/v0/subjects/{subject_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            print_success(f"成功获取条目信息: {data.get('name', 'Unknown')}")
            return data
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取条目信息失败: {e}")
            return None
    
    def search_subjects(self, keyword: str, subject_type: int = 2, limit: int = 10) -> List[Dict]:
        """
        搜索条目
        
        Args:
            keyword: 搜索关键词
            subject_type: 条目类型 (2=动画, 1=书籍, 3=音乐, 4=游戏, 6=三次元)
            limit: 返回结果数量限制
            
        Returns:
            搜索结果列表
        """
        try:
            print_info(f"正在搜索: {keyword}")
            response = requests.get(
                f"{self.base_url}/search/subject/{keyword}",
                params={
                    "type": subject_type,
                    "responseGroup": "large",
                    "max_results": limit
                },
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get("list", [])
            print_success(f"找到 {len(results)} 个结果")
            return results
            
        except requests.exceptions.RequestException as e:
            print_error(f"搜索失败: {e}")
            return []
    
    def get_episodes(self, subject_id: int, episode_type: int = 0, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        获取条目的章节列表
        
        Args:
            subject_id: 条目 ID
            episode_type: 章节类型 (0=本篇, 1=特别篇, 2=OP, 3=ED, 4=PV, 5=MAD, 6=其他)
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            章节列表
        """
        try:
            print_info(f"正在获取条目 {subject_id} 的章节信息...")
            response = requests.get(
                f"{self.base_url}/v0/episodes",
                params={
                    "subject_id": subject_id,
                    "type": episode_type,
                    "limit": limit,
                    "offset": offset
                },
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            episodes = data.get("data", [])
            print_success(f"成功获取 {len(episodes)} 集")
            return episodes
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取章节信息失败: {e}")
            return []
    
    def get_characters(self, subject_id: int) -> List[Dict]:
        """
        获取条目的角色信息
        
        Args:
            subject_id: 条目 ID
            
        Returns:
            角色列表
        """
        try:
            print_info(f"正在获取条目 {subject_id} 的角色信息...")
            response = requests.get(
                f"{self.base_url}/v0/subjects/{subject_id}/characters",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            characters = response.json()
            print_success(f"成功获取 {len(characters)} 个角色")
            return characters
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取角色信息失败: {e}")
            return []
    
    def get_persons(self, subject_id: int) -> List[Dict]:
        """
        获取条目的制作人员信息
        
        Args:
            subject_id: 条目 ID
            
        Returns:
            制作人员列表
        """
        try:
            print_info(f"正在获取条目 {subject_id} 的制作人员信息...")
            response = requests.get(
                f"{self.base_url}/v0/subjects/{subject_id}/persons",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            persons = response.json()
            print_success(f"成功获取 {len(persons)} 位制作人员")
            return persons
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取制作人员信息失败: {e}")
            return []
    
    def get_subject_relations(self, subject_id: int) -> List[Dict]:
        """
        获取条目的关联条目
        
        Args:
            subject_id: 条目 ID
            
        Returns:
            关联条目列表
        """
        try:
            print_info(f"正在获取条目 {subject_id} 的关联信息...")
            response = requests.get(
                f"{self.base_url}/v0/subjects/{subject_id}/subjects",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            relations = response.json()
            print_success(f"成功获取 {len(relations)} 个关联条目")
            return relations
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取关联信息失败: {e}")
            return []
    
    def get_user_collection(self, username: str, subject_type: int = 2, collection_type: int = None, limit: int = 30, offset: int = 0) -> Dict:
        """
        获取用户的收藏信息
        
        Args:
            username: 用户名
            subject_type: 条目类型 (2=动画)
            collection_type: 收藏类型 (1=想看, 2=看过, 3=在看, 4=搁置, 5=抛弃)
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            用户收藏信息
        """
        try:
            print_info(f"正在获取用户 {username} 的收藏...")
            params = {
                "subject_type": subject_type,
                "limit": limit,
                "offset": offset
            }
            if collection_type:
                params["type"] = collection_type
                
            response = requests.get(
                f"{self.base_url}/v0/users/{username}/collections",
                params=params,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            print_success(f"成功获取收藏信息")
            return data
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取收藏信息失败: {e}")
            return {}
    
    def get_user_episode_collection(self, username: str, subject_id: int, episode_type: int = 0) -> Dict:
        """
        获取用户对某个条目的章节收藏状态（已看/未看）
        
        Args:
            username: 用户名
            subject_id: 条目 ID
            episode_type: 章节类型 (0=本篇)
            
        Returns:
            用户章节收藏状态
        """
        try:
            print_info(f"正在获取用户 {username} 对条目 {subject_id} 的观看状态...")
            response = requests.get(
                f"{self.base_url}/v0/users/{username}/collections/{subject_id}/episodes",
                params={"episode_type": episode_type},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            print_success(f"成功获取观看状态")
            return data
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取观看状态失败: {e}")
            return {}
    
    def update_episode_collection(self, subject_id: int, episode_id: int, collection_type: int = 2) -> bool:
        """
        更新章节收藏状态（标记已看/未看）
        需要用户认证
        
        注意：此功能需要 v0 API，当前 Legacy API Token 可能不兼容
        
        Args:
            subject_id: 条目 ID
            episode_id: 章节 ID
            collection_type: 收藏类型 (0=未收藏, 1=想看, 2=看过, 3=抛弃)
            
        Returns:
            是否成功
        """
        try:
            print_info(f"正在更新章节 {episode_id} 的收藏状态...")
            
            # 使用 PUT 方法更新状态 (根据 Bangumi API 文档)
            response = requests.put(
                f"{self.base_url}/v0/users/-/collections/{subject_id}/episodes/{episode_id}",
                json={"type": collection_type},
                headers=self.headers,
                timeout=30
            )
            
            # 检查各种可能的成功状态码
            if response.status_code in [200, 201, 204]:
                print_success(f"成功更新章节状态")
                return True
            else:
                print_error(f"更新章节状态失败: HTTP {response.status_code} - {response.text}")
                return False
            
        except requests.exceptions.RequestException as e:
            print_error(f"更新章节状态失败: {e}")
            return False
    
    def batch_update_episode_collection(self, subject_id: int, episode_ids: List[int], collection_type: int = 2) -> bool:
        """
        批量更新章节收藏状态
        需要用户认证
        
        注意：此功能需要 v0 API，当前 Legacy API Token 可能不兼容
        
        Args:
            subject_id: 条目 ID
            episode_ids: 章节 ID 列表
            collection_type: 收藏类型 (0=未收藏, 1=想看, 2=看过, 3=抛弃)
            
        Returns:
            是否成功
        """
        try:
            print_info(f"正在批量更新 {len(episode_ids)} 个章节的收藏状态...")
            
            response = requests.put(
                f"{self.base_url}/v0/users/-/collections/{subject_id}/episodes",
                json={
                    "episode_id": episode_ids,
                    "type": collection_type
                },
                headers=self.headers,
                timeout=30
            )
            
            # 检查各种可能的成功状态码
            if response.status_code in [200, 201, 204]:
                print_success(f"成功批量更新章节状态")
                return True
            else:
                print_error(f"批量更新章节状态失败: HTTP {response.status_code} - {response.text}")
                return False
            
        except requests.exceptions.RequestException as e:
            print_error(f"批量更新章节状态失败: {e}")
            return False
    
    def get_subject_topics(self, subject_id: int, limit: int = 30, offset: int = 0) -> Dict:
        """
        获取条目的讨论话题列表
        使用 Legacy API 获取完整条目信息，包含 topic 字段
        
        Args:
            subject_id: 条目 ID
            limit: 返回数量限制（Legacy API 不支持分页，会返回所有）
            offset: 偏移量（Legacy API 不支持）
            
        Returns:
            话题列表
        """
        try:
            print_info(f"正在获取条目 {subject_id} 的讨论话题...")
            # 使用 Legacy API 获取包含 topic 的完整信息
            response = requests.get(
                f"{self.base_url}/subject/{subject_id}",
                params={"responseGroup": "large"},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            topics = data.get("topic", [])
            print_success(f"成功获取 {len(topics)} 个话题")
            return {"data": topics, "total": len(topics)}
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取讨论话题失败: {e}")
            return {"data": [], "total": 0}
    
    def get_topic_detail(self, topic_id: int) -> Dict:
        """
        获取话题的详细内容和回复
        
        Args:
            topic_id: 话题 ID
            
        Returns:
            话题详细信息
        """
        try:
            print_info(f"正在获取话题 {topic_id} 的详细信息...")
            response = requests.get(
                f"{self.base_url}/v0/topics/{topic_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            print_success(f"成功获取话题详情")
            return data
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取话题详情失败: {e}")
            return {}
    
    def get_episode_comments(self, episode_id: int, limit: int = 20, offset: int = 0) -> Dict:
        """
        获取章节的评论/吐槽
        Legacy API 中章节包含 comment 数量，但不提供评论详情 API
        这里返回空结果，建议用户直接访问 bgm.tv 网站查看
        
        Args:
            episode_id: 章节 ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            评论列表（Legacy API 不支持获取章节评论详情）
        """
        print_info(f"Legacy API 不支持直接获取章节评论，请访问 https://bgm.tv/ep/{episode_id} 查看")
        return {"data": [], "total": 0, "message": "Legacy API 不支持章节评论，请访问网站查看"}
    
    def get_subject_comments(self, subject_id: int, limit: int = 20, offset: int = 0) -> Dict:
        """
        获取条目的评论/日志
        使用 Legacy API 获取完整条目信息，包含 blog 字段
        
        Args:
            subject_id: 条目 ID
            limit: 返回数量限制（Legacy API 不支持分页）
            offset: 偏移量（Legacy API 不支持）
            
        Returns:
            评论列表
        """
        try:
            print_info(f"正在获取条目 {subject_id} 的评论日志...")
            # 使用 Legacy API 获取包含 blog 的完整信息
            response = requests.get(
                f"{self.base_url}/subject/{subject_id}",
                params={"responseGroup": "large"},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            blogs = data.get("blog", [])
            print_success(f"成功获取 {len(blogs)} 条评论日志")
            return {"data": blogs, "total": len(blogs)}
            
        except requests.exceptions.RequestException as e:
            print_error(f"获取条目评论失败: {e}")
            return {"data": [], "total": 0}
    
    def create_topic_reply(self, topic_id: int, content: str, related_id: int = None) -> bool:
        """
        发表话题回复
        需要用户认证
        
        Args:
            topic_id: 话题 ID
            content: 回复内容
            related_id: 关联的回复 ID（用于@某人）
            
        Returns:
            是否成功
        """
        try:
            print_info(f"正在发表回复到话题 {topic_id}...")
            
            payload = {"content": content}
            if related_id:
                payload["related_id"] = related_id
            
            response = requests.post(
                f"{self.base_url}/v0/topics/{topic_id}/replies",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            print_success(f"成功发表回复")
            return True
            
        except requests.exceptions.RequestException as e:
            print_error(f"发表回复失败: {e}")
            return False


def convert_calendar_to_seasonal_list(calendar_data: List[Dict]) -> List[Dict]:
    """
    将 Bangumi API 的 calendar 数据转换为与现有格式兼容的数据结构
    
    Args:
        calendar_data: Bangumi API 返回的每日放送数据
        
    Returns:
        与 seasonal_anime_list.json 格式兼容的数据
    """
    weekday_map = {
        1: "周一",
        2: "周二", 
        3: "周三",
        4: "周四",
        5: "周五",
        6: "周六",
        7: "周日"
    }
    
    seasonal_list = []
    
    for day_data in calendar_data:
        weekday_id = day_data.get("weekday", {}).get("id", 0)
        weekday_cn = weekday_map.get(weekday_id, "未知")
        
        for item in day_data.get("items", []):
            # 只处理动画类型 (type=2)
            if item.get("type") != 2:
                continue
            
            anime_info = {
                "primary_title": item.get("name_cn") or item.get("name", ""),
                "all_cn_names": [item.get("name_cn")] if item.get("name_cn") else [],
                "jp_name": item.get("name", ""),
                "begin_date": item.get("air_date", ""),
                "weekday": weekday_cn,
                "begin_time": "00:00",  # API 不提供具体时间
                "site": item.get("url", ""),
                # 新增字段
                "bangumi_id": item.get("id"),
                "images": item.get("images", {}),
                "summary": item.get("summary", ""),
                "eps_count": item.get("eps", 0),
                "rating": item.get("rating", {}),
                "rank": item.get("rank"),
                "collection": item.get("collection", {})
            }
            
            seasonal_list.append(anime_info)
    
    # 按日期和时间排序
    seasonal_list.sort(key=lambda x: (x.get("begin_date", ""), x.get("begin_time", "")))
    
    return seasonal_list


def main():
    """测试函数"""
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    
    print_info("测试 Bangumi API 客户端")
    print()
    
    # 从配置文件加载 token
    token = load_bangumi_token_from_config()
    if token:
        print_success(f"已加载 Token（前10位）: {token[:10]}...")
    else:
        print_info("未配置 Token，将使用无认证模式")
    
    # 创建客户端实例
    client = BangumiAPI(access_token=token)
    
    # 测试 1: 获取每日放送
    print("=" * 60)
    print("测试 1: 获取每日放送")
    print("=" * 60)
    calendar = client.get_calendar()
    
    if calendar:
        print(f"\n找到 {len(calendar)} 天的放送信息:")
        for day in calendar[:2]:  # 只显示前两天
            weekday = day.get("weekday", {})
            items_count = len(day.get("items", []))
            print(f"  {weekday.get('cn', 'Unknown')}: {items_count} 部番剧")
            
            # 显示前3部番剧
            for item in day.get("items", [])[:3]:
                name = item.get("name_cn") or item.get("name", "Unknown")
                rating_score = item.get("rating", {}).get("score", "N/A")
                rank = item.get("rank", "N/A")
                print(f"    - {name} (评分: {rating_score}, 排名: {rank})")
    
    # 测试 2: 转换为兼容格式
    print("\n" + "=" * 60)
    print("测试 2: 转换数据格式")
    print("=" * 60)
    
    if calendar:
        seasonal_list = convert_calendar_to_seasonal_list(calendar)
        print(f"\n转换后共有 {len(seasonal_list)} 部动画")
        
        # 显示前5部
        print("\n前5部动画:")
        for anime in seasonal_list[:5]:
            print(f"  - {anime['primary_title']}")
            print(f"    日期: {anime['begin_date']}, {anime['weekday']}")
            print(f"    评分: {anime.get('rating', {}).get('score', 'N/A')}")
            print(f"    Bangumi ID: {anime.get('bangumi_id')}")
            print()
    
    # 测试 3: 搜索功能
    print("=" * 60)
    print("测试 3: 搜索番剧")
    print("=" * 60)
    
    search_keyword = "进击的巨人"
    results = client.search_subjects(search_keyword, subject_type=2, limit=5)
    
    if results:
        print(f"\n搜索 '{search_keyword}' 的结果:")
        for result in results:
            name = result.get("name_cn") or result.get("name", "Unknown")
            subject_id = result.get("id")
            print(f"  - {name} (ID: {subject_id})")


if __name__ == "__main__":
    main()
