import requests
import json
import time
import os
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
import dateutil.parser

# --- load_cache, save_cache, get_user_game_collections, get_game_collection_count ---
# (Keep these functions as they are, assuming they still work for fetching data)
# ... (previous code for these functions) ...

def load_cache():
    """加载缓存数据"""
    try:
        if os.path.exists('cache.json'):
            with open('cache.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"警告: 加载缓存文件失败 ({str(e)})")
    return {
        'multi_collect_games': {},  # 记录收藏数>1的游戏
    }

def save_cache(cache_data):
    """保存缓存数据"""
    try:
        with open('cache.json', 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"警告: 保存缓存文件失败 ({str(e)})")

def get_user_game_collections(username, access_token=None):
    """获取用户收藏的游戏列表"""
    
    # 读取配置
    with open('config.json', 'r') as f:
        config = json.load(f)
        
    # 设置请求头
    headers = {
        'User-Agent': config['user_agent']
    }
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
        
    # API基础URL
    base_url = 'https://api.bgm.tv/v0/users'
    url = f"{base_url}/{username}/collections"
    
    all_collections = []
    offset = 0
    limit = 50 # Bangumi API v0 default/max limit per page is often 50
    
    print("正在获取用户游戏收藏...")
    
    # Use a loop with tqdm for progress
    with tqdm(desc="获取收藏分页", unit=" 页") as pbar:
        while True:
            params = {
                'subject_type': 4, # 4 = game
                'limit': limit,
                'offset': offset
            }
            try:
                response = requests.get(url, headers=headers, params=params, timeout=20)
                response.raise_for_status()  # Raise an exception for bad status codes
                data = response.json()
                
                if not data or not data.get('data'):
                    break # No more data
                    
                collections = data['data']
                all_collections.extend(collections)
                pbar.update(1) # Update progress bar by one page
                
                # Check if we've reached the end
                if len(collections) < limit or data.get('total', 0) <= offset + len(collections):
                     # If total is present and we've fetched >= total, stop.
                     # Also stop if the returned items are fewer than the limit requested.
                     break
                     
                offset += limit
                time.sleep(0.5) # Respect API rate limits

            except requests.exceptions.RequestException as e:
                print(f"\n获取用户收藏时出错: {e}")
                if response is not None:
                    print(f"响应内容: {response.text}")
                break # Stop trying on error
            except json.JSONDecodeError:
                print(f"\n无法解析服务器响应 (JSON): {response.text}")
                break

    print(f"获取完成，总共找到 {len(all_collections)} 条收藏记录.")
    return all_collections

def get_game_collection_count(game_id, access_token=None, cache_data=None):
    """获取指定游戏的全局'玩过'收藏数 (利用缓存)"""
    
    if cache_data and str(game_id) in cache_data.get('multi_collect_games', {}):
        # print(f"游戏 {game_id} 在缓存中 (多于1人收藏)，跳过API查询.")
        return cache_data['multi_collect_games'][str(game_id)]

    # 读取配置 (只需要User-Agent)
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        user_agent = config.get('user_agent', 'bgm-script/1.0')
    except Exception as e:
        print(f"警告: 读取config.json获取User-Agent失败: {e}")
        user_agent = 'bgm-script/1.0' # Fallback

    headers = {'User-Agent': user_agent}
    if access_token: # May not be strictly needed for subject details, but good practice
         headers['Authorization'] = f'Bearer {access_token}'

    url = f"https://api.bgm.tv/v0/subjects/{game_id}"
    count = 0
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        count = data.get('collection', {}).get('collect', 0) # 获取 'collect' (玩过) 的数量

        # 更新缓存（仅当数量大于1时）
        if count > 1 and cache_data is not None:
            if 'multi_collect_games' not in cache_data:
                 cache_data['multi_collect_games'] = {}
            cache_data['multi_collect_games'][str(game_id)] = count
            save_cache(cache_data) # Save immediately after finding a multi-collect game

        time.sleep(0.2) # Slightly shorter sleep for potentially faster checks

    except requests.exceptions.RequestException as e:
        print(f"\n获取游戏 {game_id} 收藏数时出错: {e}")
        if response is not None:
            print(f"响应内容: {response.text}")
        # Return a high number on error to exclude it from unique list? Or 0? Let's return 0.
        count = 0 # Assume 0 or error state
    except json.JSONDecodeError:
        print(f"\n无法解析游戏 {game_id} 的响应 (JSON): {response.text}")
        count = 0
    except Exception as e:
        print(f"\n处理游戏 {game_id} 时发生未知错误: {e}")
        count = 0

    return count


def get_index_items(index_id, access_token):
    """获取目录中的所有条目ID和信息"""
    with open('config.json', 'r') as f:
        config = json.load(f)
    headers = {
        'User-Agent': config['user_agent'],
        'Authorization': f'Bearer {access_token}'
    }
    url = f"https://api.bgm.tv/v0/indices/{index_id}/subjects"
    items = []
    offset = 0
    limit = 50
    print("正在获取当前目录内容...")
    with tqdm(desc="获取目录分页", unit=" 页") as pbar:
        while True:
            params = {'limit': limit, 'offset': offset}
            try:
                response = requests.get(url, headers=headers, params=params, timeout=20)
                response.raise_for_status()
                data = response.json()

                if not data or not data.get('data'):
                     break

                current_items = data['data']
                items.extend(current_items)
                pbar.update(1)

                if len(current_items) < limit or data.get('total', 0) <= offset + len(current_items):
                     break

                offset += limit
                time.sleep(0.5)
            except requests.exceptions.RequestException as e:
                print(f"\n获取目录 {index_id} 内容时出错: {e}")
                if response is not None:
                    print(f"响应内容: {response.text}")
                return [] # Return empty list on error
            except json.JSONDecodeError:
                print(f"\n无法解析目录 {index_id} 响应 (JSON): {response.text}")
                return []

    print(f"获取完成，目录 {index_id} 当前包含 {len(items)} 个条目.")
    return items

# --- update_index function is NO LONGER USED by main flow ---
# You can comment it out or remove it if not needed elsewhere.
# def update_index(index_id, subject_id, comment, sort_order, access_token, is_add=True):
#     # ... (old implementation) ...

def format_time(timestamp):
    """格式化时间戳"""
    if not timestamp:
        return "N/A"
    try:
        # Parse the ISO 8601 timestamp, which might have timezone info
        dt_obj = dateutil.parser.isoparse(timestamp)
        # Format without timezone info for simplicity
        return dt_obj.strftime('%Y-%m-%d %H:%M')
    except ValueError:
        return "Invalid Date"
    except Exception as e:
        print(f"Error formatting time {timestamp}: {e}")
        return "Error"


def sort_games(games):
    """对游戏列表进行排序：评分降序 -> 更新时间降序"""
    def sort_key(game):
        rate = game.get('rate', 0)
        updated_at = game.get('updated_at', '')
        # Parse updated_at for comparison, handle errors
        try:
            dt_updated = dateutil.parser.isoparse(updated_at) if updated_at else datetime.min.replace(tzinfo=timezone.utc)
        except ValueError:
            dt_updated = datetime.min.replace(tzinfo=timezone.utc) # Fallback for invalid format

        # Return tuple for sorting: higher rate first, then more recent update first
        # Negate rate for descending order; use datetime object directly for descending time
        return (-rate, dt_updated)

    return sorted(games, key=sort_key, reverse=True) # reverse=True on the tuple sorting handles time correctly


# --- MODIFIED FUNCTION ---
def batch_add_update_to_index(index_id, games, access_token):
    """
    使用 PATCH /v0/indices/{index_id}/subjects 批量添加或更新条目到目录.
    会根据传入的 games 列表（已排序）设置 sort 和 comment.
    """
    if not games:
        print("没有需要添加或更新的游戏。")
        return 0

    with open('config.json', 'r') as f:
        config = json.load(f)
    headers = {
        'User-Agent': config['user_agent'],
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json' # Important for PATCH/POST/DELETE with body
    }
    url = f"https://api.bgm.tv/v0/indices/{index_id}/subjects"

    # 1. 排序 (现在在 main 函数外部完成，这里假设 games 列表已排序)
    #    如果需要在函数内部排序，取消下面的注释
    # print("正在对游戏进行排序...")
    # sorted_games = sort_games(games)
    sorted_games = games # Assume games are pre-sorted

    # 2. 构建请求体 (payload)
    payload_items = []
    print("正在准备批量更新数据...")
    for idx, game in enumerate(tqdm(sorted_games, desc="准备条目数据")):
        subject = game.get('subject', {})
        subject_id = subject.get('id')
        if not subject_id:
            print(f"警告: 游戏条目缺少 ID: {game}")
            continue

        rating = f"评分: {game.get('rate', 'N/A')}"
        mark_time = f"时间: {format_time(game.get('updated_at'))}"
        user_comment = game.get('comment', '').strip().replace('\r', ' ').replace('\n', ' ') # Clean comment
        
        # 组合评论，如果用户有评论则添加
        comment_parts = [rating, mark_time]
        if user_comment:
            comment_parts.append(f"吐槽: {user_comment}")
        full_comment = " | ".join(comment_parts)

        # sort 值基于列表中的顺序 (0-based index)
        sort_order = idx

        payload_items.append({
            "subject_id": subject_id,
            "comment": full_comment,
            "sort": sort_order
        })

    if not payload_items:
        print("没有有效的条目数据可以更新。")
        return 0

    # 3. 发送单个 PATCH 请求
    print(f"正在发送批量更新请求 (共 {len(payload_items)} 个条目)...")
    success_count = 0
    try:
        response = requests.patch(url, headers=headers, json=payload_items, timeout=60) # Increase timeout for batch ops

        print(f"  请求 URL: {response.request.url}")
        # print(f"  请求 Body: {json.dumps(payload_items, ensure_ascii=False, indent=2)}") # Uncomment for debugging

        if response.status_code == 204: # No Content - Success for PATCH/DELETE often
            print("批量更新成功！")
            success_count = len(payload_items)
        else:
            print(f"批量更新失败。状态码: {response.status_code}")
            try:
                print(f"错误响应: {response.json()}")
            except json.JSONDecodeError:
                print(f"错误响应 (非JSON): {response.text}")
            # Partial success is not indicated by API, assume all failed on non-204
            success_count = 0

    except requests.exceptions.RequestException as e:
        print(f"批量更新时发生网络错误: {e}")
        success_count = 0
    except Exception as e:
         print(f"批量更新时发生未知错误: {e}")
         success_count = 0

    # No need for sleep here as it's a single call, unless server has specific batch rate limits
    # time.sleep(0.5)

    return success_count

# --- MODIFIED FUNCTION ---
def batch_remove_from_index(index_id, subject_ids, access_token):
    """
    使用 DELETE /v0/indices/{index_id}/subjects 批量从目录移除条目.
    """
    if not subject_ids:
        print("没有需要移除的条目。")
        return True # Considered successful if nothing to do

    with open('config.json', 'r') as f:
        config = json.load(f)
    headers = {
        'User-Agent': config['user_agent'],
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json' # Important for DELETE with body
    }
    url = f"https://api.bgm.tv/v0/indices/{index_id}/subjects"

    # Convert set/list to list for JSON serialization
    ids_to_remove = list(subject_ids)

    print(f"正在发送批量删除请求 (共 {len(ids_to_remove)} 个条目)...")
    success = False
    try:
        response = requests.delete(url, headers=headers, json=ids_to_remove, timeout=60)

        print(f"  请求 URL: {response.request.url}")
        # print(f"  请求 Body: {json.dumps(ids_to_remove)}") # Uncomment for debugging

        if response.status_code == 204: # No Content - Success
            print("批量删除成功！")
            success = True
        else:
            print(f"批量删除失败。状态码: {response.status_code}")
            try:
                print(f"错误响应: {response.json()}")
            except json.JSONDecodeError:
                print(f"错误响应 (非JSON): {response.text}")
            success = False

    except requests.exceptions.RequestException as e:
        print(f"批量删除时发生网络错误: {e}")
        success = False
    except Exception as e:
         print(f"批量删除时发生未知错误: {e}")
         success = False

    return success


def update_index_description(index_id, access_token):
    """更新目录描述，添加或更新 '最近更新时间'"""
    with open('config.json', 'r') as f:
        config = json.load(f)
    headers = {
        'User-Agent': config['user_agent'],
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    base_url = f"https://api.bgm.tv/v0/indices/{index_id}"

    # 1. 获取当前目录信息
    current_title = "AutoGen: Unique Played Games" # Default title if fetch fails
    current_desc = ""
    try:
        response_get = requests.get(base_url, headers=headers, timeout=15)
        response_get.raise_for_status()
        data = response_get.json()
        current_title = data.get('title', current_title)
        current_desc = data.get('description', '')
    except requests.exceptions.RequestException as e:
        print(f"获取目录 {index_id} 信息失败: {e}")
        # Continue with default title and empty description
    except json.JSONDecodeError:
         print(f"解析目录 {index_id} 信息响应失败: {response_get.text}")
         # Continue
    except Exception as e:
        print(f"处理目录 {index_id} 信息时出错: {e}")
        # Continue


    # 2. 准备新的描述
    # 使用北京时间 (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(beijing_tz)
    timestamp_str = now_beijing.strftime('%Y-%m-%d %H:%M:%S %Z')
    update_line = f"最近更新时间：{timestamp_str}"

    lines = current_desc.split('\n')
    # 移除旧的更新时间行 (如果存在)
    lines = [line for line in lines if not line.startswith("最近更新时间：")]
    # 添加新的更新时间行到末尾
    lines.append(update_line)
    new_desc = "\n".join(lines).strip()

    # 3. 发送 PUT 请求更新描述和标题
    payload = {
        "title": current_title, # Keep original title unless specified otherwise
        "description": new_desc
    }
    print("正在更新目录描述...")
    try:
        response_put = requests.put(base_url, headers=headers, json=payload, timeout=30)

        if response_put.status_code == 204:
            print("目录描述更新成功！")
            return True
        else:
            print(f"目录描述更新失败。状态码: {response_put.status_code}")
            try:
                print(f"错误响应: {response_put.json()}")
            except json.JSONDecodeError:
                print(f"错误响应 (非JSON): {response_put.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"更新目录描述时发生网络错误: {e}")
        return False
    except Exception as e:
        print(f"更新目录描述时发生未知错误: {e}")
        return False


def main():
    print("脚本开始运行...")
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            # Validate essential config keys
            required_keys = ['user_id', 'access_token', 'indice_id', 'user_agent']
            if not all(key in config for key in required_keys):
                print("错误: config.json 文件缺少必要的键 (user_id, access_token, indice_id, user_agent)")
                return
    except FileNotFoundError:
        print("错误: 未找到 config.json 文件。请确保配置文件存在。")
        return
    except json.JSONDecodeError:
        print("错误: config.json 文件格式无效。")
        return
    except Exception as e:
        print(f"读取配置文件时发生错误: {e}")
        return

    cache_data = load_cache()

    # 1. 获取用户所有游戏收藏
    all_games = get_user_game_collections(config['user_id'], config['access_token'])
    if not all_games:
        print("未能获取用户游戏收藏，脚本终止。")
        return

    # 2. 筛选"玩过" (type == 2)
    played_games = [game for game in all_games if game.get('type') == 2]
    print(f"\n找到 {len(played_games)} 个标记为 '玩过' 的游戏。")
    if not played_games:
        print("没有找到 '玩过' 的游戏，脚本结束。")
        # Optionally clear the index here if that's the desired behavior
        return

    # 3. 筛选全局收藏数为1的游戏
    unique_games = []
    print("正在检查游戏的全局收藏数 (玩过 > 1 的会使用缓存)...")
    for game in tqdm(played_games, desc="筛选独特游戏"):
        subject_id = game.get('subject', {}).get('id')
        if not subject_id:
            continue
        
        # 使用缓存优化检查
        count = get_game_collection_count(subject_id, config.get('access_token'), cache_data) # Pass token if needed by count check

        if count == 1:
            unique_games.append(game)
        # else:
            # print(f"游戏 {subject_id} ({game.get('subject',{}).get('name')}) 全局收藏数: {count}, 已跳过.")


    print(f"\n找到 {len(unique_games)} 个全局唯一收藏（玩过=1）的游戏。")

    # 4. 获取当前目录内容
    current_index_items = get_index_items(config['indice_id'], config['access_token'])
    current_index_ids = {item['subject_id'] for item in current_index_items}
    # print(f"当前目录中的条目 ID: {current_index_ids}")

    # 5. 确定需要添加/更新和移除的条目
    new_game_ids = {game['subject']['id'] for game in unique_games}

    to_remove_ids = current_index_ids - new_game_ids
    print(f"\n需要从目录移除的条目 ID ({len(to_remove_ids)}个): {to_remove_ids if to_remove_ids else '无'}")

    # 所有 unique_games 都需要被加入或更新其信息 (评论/排序)
    # 在使用 PATCH 时，即使条目已存在，也会更新其 comment 和 sort
    to_add_update_games = unique_games
    # 先排序，以便 batch_add_update_to_index 可以直接使用顺序作为 sort 值
    print("\n正在排序需要添加/更新的游戏...")
    sorted_games_to_update = sort_games(to_add_update_games)
    
    print("\n准备更新的游戏:")
    if sorted_games_to_update:
        for idx, game in enumerate(sorted_games_to_update):
             print(f"  {idx+1}. ID: {game['subject']['id']} ({game['subject'].get('name', '未知名称')}) Rate: {game.get('rate', 'N/A')} @ {format_time(game.get('updated_at'))}")
    else:
        print("  无")


    # 6. 执行移除操作 (使用批量删除)
    if to_remove_ids:
        print(f"\n正在执行批量移除 ({len(to_remove_ids)} 个条目)...")
        remove_success = batch_remove_from_index(
            config['indice_id'],
            to_remove_ids,
            config['access_token']
        )
        if not remove_success:
            print("警告: 批量移除操作未完全成功。")
        # No need for sleep as it's a single call
    else:
        print("\n无需移除条目。")


    # 7. 执行添加/更新操作 (使用批量修改)
    print(f"\n正在执行批量添加/更新 ({len(sorted_games_to_update)} 个条目)...")
    update_success_count = batch_add_update_to_index(
        config['indice_id'],
        sorted_games_to_update, # Pass the pre-sorted list
        config['access_token']
    )
    print(f"批量添加/更新操作完成，成功处理 {update_success_count} 个条目。")


    # 8. 更新目录描述
    print("\n正在更新目录描述中的时间戳...")
    desc_update_success = update_index_description(config['indice_id'], config['access_token'])
    if desc_update_success:
        print("目录描述更新成功。")
    else:
        print("目录描述更新失败。")

    # 9. 保存可能已更新的缓存
    print("\n正在保存缓存...")
    save_cache(cache_data)

    print("\n脚本执行完毕。")


if __name__ == "__main__":
    main()