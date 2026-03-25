# 论文摘要自动化工具

自动化每日论文摘要工具。从 arXiv获取论文，通过关键词过滤、LLM（DeepSeek）相关性评分，自动将符合条件的论文推送到钉钉群。可实现论文评分、评论、分类筛选等功能。


**系统架构**：GitHub Actions（每日定时）&rarr; 钉钉推送 

## 功能特点

1. **多源论文抓取**：支持 arXiv、bioRxiv、ChemRxiv 以及多种期刊 RSS
2. **双层智能筛选**：关键词快速过滤 + DeepSeek LLM 相关性打分
3. **核心作者高亮**：指定作者的论文绕过所有过滤，直接推送
4. **自动化推送**：钉钉机器人实时推送
5. **可选前端**：基于 React+Supabase+Cloudflare Pages，支持评分、评论、筛选、排序
6. **去重与历史同步**：记录已推送论文，避免重复，支持首次使用同步历史论文

## 工作流程

每日 GitHub Actions 定时任务自动执行以下步骤：

1. 从 arXiv、bioRxiv、ChemRxiv 及期刊 RSS 源获取最新论文
2. 关键词快速过滤 + DeepSeek LLM 相关性评分（以研究方向描述为上下文）
3. 高亮关键作者论文（绕过过滤）
4. 将分类后的摘要推送到钉钉群

**成本说明**：仅需 DeepSeek API 费用（通常每天 $0.10-0.30，取决于论文数量）。Supabase、Cloudflare Pages 和 GitHub Actions 均为免费套餐。

## 快速开始

### 前置条件

- GitHub 账户（用于托管仓库和运行 Actions）
- [DeepSeek API 密钥](https://platform.deepseek.com/)（用于 LLM 评分）（其它LLM密钥也可以）
- Python 3.10+（本地测试用）


### 1. 配置您的研究方向

**`config.json`** 是主要的配置文件：

| 字段 | 说明 |
|---|---|
| `lab_description` | 研究方向描述。作为 LLM 评分相关性的上下文。描述越详细，过滤效果越好。 |
| `keywords` | 第一轮过滤的关键词。论文必须匹配至少一个关键词才会进入 LLM 评分。 |
| `relevance_threshold` | LLM 评分阈值（0-1），默认 `0.6`。数值越低，论文越多；越高越严格。 |
| `min_impact_factor` | RSS 期刊源的最低影响因子，默认 `5.0`。 |
| `max_age_hours` | 论文的时间范围（小时），默认 `48`。 |
| `model` | （可选）LLM 模型，默认 `"deepseek-chat"`。 |

**`key_authors.json`**：指定的关键作者论文将绕过所有过滤，始终包含在推送中（钉钉中加粗显示）。建议包含姓名变体（中间名首字母、全名等）以确保准确匹配。匹配规则不区分大小写，忽略重音符号、空格和连字符。

**论文来源**：要更改监控的 arXiv 类别、bioRxiv 主题或期刊，请直接编辑抓取器文件：
- `paper_filter/fetchers/arxiv.py`: `ArxivFetcher.CATEGORIES`
- `paper_filter/fetchers/biorxiv.py`: bioRxiv API 主题
- `paper_filter/fetchers/journals.py`: `SpringerNatureFetcher.RSS_FEEDS` 和 `JournalRSSFetcher.FEEDS`

**论文分类**：论文由 LLM 按研究领域分类。更改分类需要同时编辑：
- `paper_filter/filters/categorizer.py`: `CATEGORIES` 列表和 LLM 提示词中的分类指南
- `frontend/src/App.jsx`: 顶部的 `CATEGORIES`、`CATEGORY_COLORS` 和 `CATEGORY_SHORT` 常量

### 2. 配置环境变量

```bash
cp .env.example .env  # 然后填入您的密钥
```

| 变量 | 必需 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API 密钥 |
| `DINGTALK_WEBHOOK_URL` | 是 | 钉钉自定义机器人 Webhook URL |
| `DINGTALK_SECRET` | 否 | 钉钉机器人加签密钥（如果启用了加签） |
| `SUPABASE_URL` | 前端用 | Supabase 项目 URL （暂无）|
| `SUPABASE_SERVICE_KEY` | 前端用 | Supabase 服务角色密钥（暂无） |

### 3. 本地测试

```bash
# 模拟运行（打印结果，不发送）
python run.py --dry-run

# 测试模式（限制50篇论文，快速便宜测试）
python run.py --dry-run --test

# 测试单个数据源
python test_feeds.py arxiv
python test_feeds.py --by-journal journals
```


## 部署方式

### 方式一：GitHub Actions（推荐）

#### 设置钉钉自定义机器人

1. 打开钉钉，进入您想要接收消息的群聊
2. 点击群设置 → 智能群助手 → 添加机器人 → 自定义
3. 填写机器人名称，选择"加签"安全设置
4. 复制生成的 Webhook URL 和加签密钥
5. 将 Webhook URL 填入 `DINGTALK_WEBHOOK_URL`
6. 将加签密钥填入 `DINGTALK_SECRET`
（个人直接使用的关键词，没有使用密钥）

#### 配置 GitHub Actions

1. 将代码推送到您的 GitHub 仓库
2. 进入 **Settings** → **Secrets and variables** → **Actions**（[文档](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)）
3. 添加以下仓库密钥：
   - `DEEPSEEK_API_KEY`
   - `DINGTALK_WEBHOOK_URL`
   - `DINGTALK_SECRET`（如果启用了加签）
   - `SUPABASE_URL`（可选，用于前端）
   - `SUPABASE_SERVICE_KEY`（可选，用于前端）
4. 手动触发：在 **Actions** → **Daily Paper Digest** → **Run workflow**

#### 修改触发时间

编辑 `.github/workflows/daily-digest.yml` 中的 `cron` 行。使用 [crontab.guru](https://crontab.guru/) 构建 cron 表达式。

当前配置：每天北京时间下午 3:20（UTC 早上 7:20）

```yaml
schedule:
  # 每天北京时间下午 3:20（UTC 早上 7:20）
  - cron: '20 7 * * *'
```

常用 cron 表达式示例：
- `0 8 * * *` - 每天 UTC 8:00（北京时间 16:00）
- `0 0 * * *` - 每天 UTC 0:00（北京时间 8:00）
- `0 22 * * *` - 每天 UTC 22:00（北京时间次日 6:00）

### 方式二：本地服务器 + Cron 作业

如果您更倾向于在本地服务器运行，可以使用 cron 作业：

#### 步骤 1：创建虚拟环境

```bash
python3 -m venv paper_digest_auto
source paper_digest_auto/bin/activate
pip install -r requirements.txt
```

#### 步骤 2：配置环境变量

创建 `.env` 文件并填入您的密钥（同本地测试）

#### 步骤 3：创建 Cron 作业

```bash
crontab -e
```

添加以下行（每天早上 8 点运行）：

```cron
0 8 * * * cd /home/oyzy/projects/PaperDigestAutomation && source paper_digest_auto/bin/activate && python run.py >> /tmp/paper_digest.log 2>&1
```

#### 步骤 4：验证 Cron 作业

```bash
crontab -l  # 查看已添加的作业
# 手动测试一次
python run.py
```

**Cron 格式说明**：`minute hour day month weekday`
- `0 8 * * *` = 每天 8:00 运行
- `20 15 * * *` = 每天 15:20 运行

**注意事项**：
- 确保虚拟环境路径正确
- Cron 作业会在服务器未登录时继续运行
- 检查服务器时区并相应调整时间
- 建议添加日志输出（`>> /tmp/paper_digest.log 2>&1`）便于排查问题

#### CentOS/RHEL 服务器额外配置

如果 cron 邮件导致问题，禁用邮件通知：

```bash
echo "MAILTO=\"\"" >> /etc/crontab
```

## 国外参考开源项目

https://github.com/mcox3406/lab-paper-feed

## 贡献

欢迎提交 Issue 和 Pull Request！
