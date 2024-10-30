> 本程序与readme均由AI生成

# Bangumi 独特游戏目录生成器

这是一个用于生成 Bangumi 独特游戏目录的 Python 工具。它可以帮助你创建一个只包含被标记为"玩过"且仅有一次收藏记录的游戏列表。

## 功能特点

- 自动获取用户的游戏收藏记录
- 筛选出仅被收藏一次的游戏
- 自动创建和更新 Bangumi 目录
- 支持缓存以提高性能
- 自动排序和格式化游戏条目
- 包含评分、标记时间和评价信息

## 使用方法

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 复制 `config_example.json` 为 `config.json`，并填入以下信息：

```json
{
  "user_id": "你的Bangumi用户名",
  "access_token": "你的API访问令牌",
  "indice_id": "目录ID",
  "user_agent": "你的应用名称/版本"
}
```

3. 运行脚本：

```bash
python indicesMaker.py
```

## 注意事项

- 需要有效的 Bangumi API 访问令牌
- 请遵守 API 的访问频率限制
- 建议定期运行以保持目录更新
- 首次运行可能需要较长时间来建立缓存

## 贡献指南

发现问题了？有新想法？

- 提 Issue 或者 PR 都行
- 代码能跑就行，不用太在意格式
- 记得写点注释，方便别人看懂你在干啥

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的目录生成功能
- 添加缓存机制
- 支持批量更新
```

