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

### 本地运行

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

### 使用 GitHub Actions 自动运行

本项目支持使用 GitHub Actions 进行自动更新。设置步骤如下：

1. Fork 本仓库到你的 GitHub 账号下

2. 在你的仓库中，进入 Settings -> Secrets and variables -> Actions

3. 点击 "New repository secret"，添加以下 secret：
   - 名称：`CONFIG_JSON`
   - 值：将你的 `config.json` 完整内容复制粘贴到这里

4. Actions 会在每天北京时间凌晨 0:00 自动运行

5. 你也可以在 Actions 页面手动触发运行

### 注意事项

- 请确保你的 access_token 有足够的权限
- 首次运行 Actions 时需要在 Actions 页面手动允许工作流运行
- 如需修改运行时间，可编辑 `.github/workflows/daily-update.yml` 文件中的 cron 表达式

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

