import requests
import json
import time
import os
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
import dateutil.parser

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
    base_url = 'https://api.bgm.tv'
    
    # 初始化结果列表
    all_games = []
    offset = 0
    limit = 100  # API默认最大值
    
    print("正在获取用户收藏的游戏列表...")
    
    # 首次请求获取总数
    url = f'{base_url}/v0/users/{username}/collections'
    params = {
        'subject_type': 4,
        'offset': 0,
        'limit': 1
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        return []
    total = response.json()['total']
    
    # 使用进度条获取所有数据
    with tqdm(total=total, desc="获取游戏列表") as pbar:
        while True:
            params['limit'] = limit
            params['offset'] = offset
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                break
                
            data = response.json()
            all_games.extend(data['data'])
            
            pbar.update(len(data['data']))
            
            if len(data['data']) < limit:
                break
                
            offset += limit
            time.sleep(0.5)  # 添加延时避免请求过快
    
    return all_games

def get_game_collection_count(game_id, access_token=None, cache_data=None):
    """获取游戏的收藏统计信息（带缓存）"""
    # 如果没有提供缓存数据，创建新的缓存
    if cache_data is None:
        cache_data = load_cache()
    
    # 检查缓存
    game_id_str = str(game_id)
    
    # 如果游戏在多收藏缓存中直接返回
    if game_id_str in cache_data['multi_collect_games']:
        return cache_data['multi_collect_games'][game_id_str]
    
    # 如果缓存不存在，请求API
    with open('config.json', 'r') as f:
        config = json.load(f)
        
    headers = {
        'User-Agent': config['user_agent']
    }
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
        
    url = f'https://api.bgm.tv/v0/subjects/{game_id}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"错误: 无法获取游戏 {game_id} 的信息")
        return None
        
    data = response.json()
    collect_count = data['collection'].get('collect', 0)
    
    # 如果收藏数大于1，更新缓存
    if collect_count > 1:
        cache_data['multi_collect_games'][game_id_str] = collect_count
        save_cache(cache_data)
    
    return collect_count

def get_index_items(index_id, access_token):
    """获取目录中的所有条目"""
    print("正在获取目录内容...")
    with open('config.json', 'r') as f:
        config = json.load(f)
        
    headers = {
        'User-Agent': config['user_agent'],
        'Authorization': f'Bearer {access_token}'
    }
    
    all_items = []
    offset = 0
    limit = 30  # API默认限制

    while True:
        url = f'https://api.bgm.tv/v0/indices/{index_id}/subjects?limit={limit}&offset={offset}'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"错误: 无法获取目录内容 (状态码: {response.status_code})")
            return []
            
        try:
            data = response.json()
            if not isinstance(data, dict) or 'data' not in data:
                print("错误: 返回数据格式不正确")
                return []
                
            items = data['data']
            all_items.extend(items)
            
            # 检查是否还有更多数据
            total = data.get('total', 0)
            if offset + limit >= total:
                break
                
            offset += limit
            time.sleep(0.5)  # 添加延时避免请求过快
            
        except json.JSONDecodeError:
            print("错误: 返回的不是有效的JSON数据")
            return []
            
    return all_items

def update_index(index_id, subject_id, comment, sort_order, access_token, is_add=True):
    """添加或编辑目录条目"""
    with open('config.json', 'r') as f:
        config = json.load(f)
        
    headers = {
        'User-Agent': config['user_agent'],
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.bgm.tv/v0/indices/{index_id}/subjects/{subject_id}'
    
    if is_add:
        # 添加/编辑条目到目录
        data = {
            'comment': comment if comment else "",
            'sort': sort_order  # 使用正确的字段名 'sort'
        }
        try:
            response = requests.put(url, headers=headers, json=data)
        except Exception as e:
            print(f"错误: 请求失败 ({str(e)})")
            return False
    else:
        # 从目录中删除条目
        response = requests.delete(url, headers=headers)
    
    if response.status_code not in [200, 204]:
        print(f"错误: {'添加' if is_add else '删除'}条目失败 (状态码: {response.status_code})")
        if response.text:
            try:
                error_data = response.json()
                print(f"错误详情: {error_data}")
            except:
                print(f"错误详情: {response.text}")
        return False
    
    return True

def format_time(timestamp):
    """格式化时间为易读格式"""
    try:
        if isinstance(timestamp, str):
            # 解析 ISO 8601 格式的时间字符串
            dt = dateutil.parser.parse(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M')
        return "未知时间"
    except (ValueError, TypeError):
        return "未知时间"

def sort_games(games):
    """对游戏进行排序：按评分从高到低，同评分按收藏时间由近到远"""
    def get_sort_key(x):
        rate = -(x.get('rate', 0) or 0)
        try:
            updated_at = -float(x.get('updated_at', 0))
        except (ValueError, TypeError):
            updated_at = 0
        return (rate, updated_at)
    
    return sorted(games, key=get_sort_key)

def batch_add_to_index(index_id, games, access_token):
    """批量添加条目到目录"""
    with open('config.json', 'r') as f:
        config = json.load(f)
        
    headers = {
        'User-Agent': config['user_agent'],
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.bgm.tv/v0/indices/{index_id}/subjects'
    
    # 对游戏进行排序
    sorted_games = sort_games(games)
    
    # 准备批量添加的数据
    subjects = []
    for order, game in enumerate(sorted_games, 1):
        try:
            comment_parts = []
            if game.get('rate'):
                comment_parts.append(f"评分: {game['rate']}")
            if game.get('updated_at'):
                comment_parts.append(f"标记时间: {format_time(game['updated_at'])}")
            if game.get('comment'):
                # 清理评论文本，移除特殊字符
                cleaned_comment = game['comment'].replace('\n', ' ').replace('\r', ' ')
                comment_parts.append(f"吐嘈: {cleaned_comment}")
            comment = " | ".join(comment_parts)
            
            subjects.append({
                'subject_id': game['subject']['id'],
                'comment': comment,  # 移除长度限制
                'sort': order
            })
        except Exception as e:
            print(f"警告: 处理游戏数据时出错: {e}")
            continue
    
    # 由于批量添加可能有问题，直接切换到逐个添加
    print("正在逐个添加条目...")
    success_count = 0
    
    with tqdm(subjects, desc="添加条目") as pbar:
        for subject in pbar:
            if update_index(
                index_id,
                subject['subject_id'],
                subject['comment'],
                subject['sort'],
                access_token
            ):
                success_count += 1
            else:
                print(f"警告: 无法添加条目 ID {subject['subject_id']}")
            time.sleep(0.5)  # 添加延时避免请求过快
            
            pbar.set_postfix({"成功": success_count})
    
    return success_count

def update_index_description(index_id, access_token):
    """更新目录描述，添加最后更新时间"""
    with open('config.json', 'r') as f:
        config = json.load(f)
        
    headers = {
        'User-Agent': config['user_agent'],
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # 首先获取当前目录信息
    url = f'https://api.bgm.tv/v0/indices/{index_id}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print("错误: 无法获取目录信息")
        return False
        
    index_info = response.json()
    current_description = index_info.get('desc', '')
    current_title = index_info.get('title', '')
    
    # 获取当前UTC时间并转换为北京时间
    current_time_utc = datetime.now(timezone.utc)
    current_time_beijing = current_time_utc.astimezone(timezone(timedelta(hours=8)))
    update_line = f"最近更新时间：{current_time_beijing.strftime('%Y-%m-%d %H:%M:%S')}"
    
    # 将描述分割成行，处理所有可能的换行符
    lines = current_description.replace('\r\n', '\n').split('\n')
    
    # 检查最后一行是否包含更新时间
    if lines and lines[-1].startswith("最近更新时间："):
        lines[-1] = update_line
    else:
        lines.append(update_line)
    
    # 重新组合描述，使用单个换行符
    new_description = '\n'.join(lines)
    
    # 更新目录描述
    update_url = f'https://api.bgm.tv/v0/indices/{index_id}'
    update_data = {
        'title': current_title,
        'description': new_description
    }
    
    response = requests.put(update_url, headers=headers, json=update_data)
    
    if response.status_code not in [200, 204]:
        print("错误: 更新目录描述失败")
        if response.text:
            try:
                error_data = response.json()
                print(f"错误详情: {error_data}")
            except:
                print(f"错误详情: {response.text}")
        return False
        
    return True

def main():
    # 读取配置
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    print("开始处理...\n")
    
    # 加载缓存
    cache_data = load_cache()
    print("已加载缓存数据")
    
    # 获取用户收藏的游戏
    games = get_user_game_collections(
        username=config['user_id'],
        access_token=config['access_token']
    )
    
    # 筛选"玩过"的游戏
    completed_games = [game for game in games if game['type'] == 2]
    
    print(f"\n用户 {config['user_id']} 共玩过 {len(completed_games)} 个游戏")
    print("正在检查每个游戏的收藏数量...\n")
    
    # 获取符合条件的游戏列表（只被标记"玩过"一次）
    unique_games = []
    skipped_count = 0
    
    with tqdm(completed_games, desc="检查游戏收藏数") as pbar:
        for game in pbar:
            subject = game['subject']
            game_id_str = str(subject['id'])
            
            # 更新进度条描述
            pbar.set_description(f"检查游戏 {subject['name'][:20]}")
            
            # 检查缓存中是否已确认为多收藏游戏
            if game_id_str in cache_data['multi_collect_games']:
                skipped_count += 1
                pbar.set_postfix(skipped=skipped_count)
                continue
            
            collect_count = get_game_collection_count(
                subject['id'], 
                config['access_token'],
                cache_data
            )
            
            if collect_count == 1:
                unique_games.append(game)
            
            time.sleep(0.5)  # 添加延时避免请求过快
    
    print(f"\n找到 {len(unique_games)} 个符合条件的游戏")
    print(f"跳过了 {skipped_count} 个已缓存的多收藏游戏")
    
    # 获取目录中的现有条目
    current_index_items = get_index_items(config['indice_id'], config['access_token'])
    
    # 获取现有条目ID（添加更多调试信息）
    current_index_ids = set()
    print("\n当前目录中的条目:")
    for item in current_index_items:
        try:
            if isinstance(item, dict):
                subject_id = item.get('id')  # 注意：API返回的是'id'而不是'subject_id'
                if subject_id:
                    current_index_ids.add(subject_id)
                    print(f"- ID: {subject_id} ({item.get('name', '未知名称')})")
            else:
                print(f"警告: 目录条目格式错误: {item}")
        except Exception as e:
            print(f"警告: 处理目录条目时出错: {e}")
            print(f"问题条目内容: {item}")
            continue
    
    # 获取要添加的游戏ID列表
    new_game_ids = set(game['subject']['id'] for game in unique_games)
    print("\n准备添加的游戏:")
    for game in unique_games:
        print(f"- ID: {game['subject']['id']} ({game['subject'].get('name', '未知名称')})")
    
    # 需要移除的条目
    to_remove_ids = current_index_ids - new_game_ids
    print(f"\n需要移除的条目: {to_remove_ids}")
    
    # 需要添加或更新的条目
    to_update_games = unique_games  # 所有游戏都需要更新
    
    # 移除不再符合条件的条目
    if to_remove_ids:
        print(f"\n正在移除 {len(to_remove_ids)} 个不再符合条件的条目...")
        for subject_id in tqdm(to_remove_ids, desc="移除条目"):
            print(f"正在删除条目 ID: {subject_id}")
            success = update_index(
                config['indice_id'],
                subject_id,
                "",
                0,
                config['access_token'],
                is_add=False
            )
            if not success:
                print(f"警告: 删除条目 {subject_id} 失败")
            time.sleep(0.5)
    
    # 添加或更新所有条目
    print("\n正在更新所有条目...")
    success_count = batch_add_to_index(
        config['indice_id'],
        to_update_games,
        config['access_token']
    )
    
    print(f"\n成功更新 {success_count} 个条目")
    
    # 更新目录描述
    print("\n正在更新目录描述...")
    if update_index_description(config['indice_id'], config['access_token']):
        print("目录描述更新成功")
    else:
        print("警告: 目录描述更新失败")
    
    print("\n目录更新完成！")
    print(f"- 删除了 {len(to_remove_ids)} 个条目")
    print(f"- 添加了 {len(to_update_games)} 个条目")

if __name__ == "__main__":
    main()
