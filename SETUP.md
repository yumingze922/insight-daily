# 每日深度思辨 · 部署与使用指南

> 方案一：PWA + 飞书/企业微信机器人 + Vercel 部署

整体逻辑：每天早上 8 点，系统自动抓取 36 氪新闻、调用 LLM 生成分析、通过飞书/企业微信/钉钉推送卡片通知。你收到消息，点击按钮打开 PWA 进行深度思辨对话。

---

## 效果预览

**手机上收到推送**（飞书示例）：
```
┌─────────────────────────────────┐
│ ██ 每日深度思辨                  │
│                                  │
│ 台积电在美追加1000亿美元          │
│ 建设第三座先进晶圆厂              │
│                                  │
│ 代工厂 → 地缘定价者？             │
│ ──────────────────────────────── │
│  [ 开始今日思辨 ]  [ 往期回顾 ]   │
└─────────────────────────────────┘
```

点击「开始今日思辨」→ 打开 PWA → 完整的深度分析 + 思辨对话体验。

---

## 第一步：创建飞书自定义机器人（推荐）

这是最简单的方式，**不需要企业认证、不需要审核**。

### 1.1 打开飞书
电脑端或手机端都可以。

### 1.2 创建群聊
- 点击右上角 `+` → `创建群聊`
- 群名称随意，比如「每日思辨」
- 只拉你自己就行（单人群也可以）

### 1.3 添加自定义机器人
- 进入群聊 → 点击右上角 `...` → `设置`
- 找到 `群机器人` → `添加机器人` → `自定义机器人`
- 机器人名称：`每日深度思辨`
- 点击 `添加`

### 1.4 复制 Webhook 地址
添加成功后，你会看到一个 Webhook 地址，格式类似：
```
https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxxxxxxxxx
```
**复制这个地址，下一步要用。**

---

## 第二步：创建 GitHub 仓库并配置密钥

### 2.1 将代码推送到 GitHub
```bash
cd news-daily-analyzer
git init
git add .
git commit -m "初始版本"
git remote add origin https://github.com/你的用户名/insight-daily.git
git push -u origin main
```

### 2.2 配置 GitHub Secrets
在 GitHub 仓库页面：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

需要添加的密钥：

| 名称 | 值 | 说明 |
|------|-----|------|
| `DEEPSEEK_API_KEY` | `sk-xxxxxxxx` | DeepSeek API Key（[platform.deepseek.com](https://platform.deepseek.com) 获取） |
| `FEISHU_WEBHOOK` | `https://open.feishu.cn/open-apis/bot/v2/hook/xxx` | 第一步复制的飞书 Webhook |

（如果要用企业微信或钉钉，同理添加 `WECOM_WEBHOOK` 或 `DINGTALK_WEBHOOK`）

### 2.3 配置 BASE_URL（部署后补充）
先跳过这一步，等 Vercel 部署完拿到域名再回来设置。

---

## 第三步：部署到 Vercel

### 3.1 注册 Vercel
访问 [vercel.com](https://vercel.com)，用 GitHub 账号登录。

### 3.2 导入项目
- 点击 `New Project`
- 选择你刚推送的 GitHub 仓库 `insight-daily`
- 无需修改任何配置，直接点 `Deploy`

### 3.3 等待部署完成
约 30 秒后，你会得到一个域名：`https://insight-daily.vercel.app`

### 3.4 （可选）绑定自定义域名
Vercel 项目设置 → `Domains` → 添加你的域名。
如果你有域名，在 DNS 添加一条 CNAME 记录指向 `cname.vercel-dns.com`。

---

## 第四步：手动测试每日更新

部署完成后，手动触发一次更新来验证。

### 4.1 触发 GitHub Actions
在 GitHub 仓库页面：`Actions` → `每日深度思辨 · 自动更新` → `Run workflow`

### 4.2 等待执行
约 2-3 分钟后（取决于 LLM 响应速度），你会看到：
- 飞书群里收到一条卡片消息
- GitHub 仓库的 `public/data/` 目录下生成了今天的 JSON 文件
- Vercel 自动重新部署（因为仓库有更新）

### 4.3 验证 PWA
用手机浏览器打开 `https://insight-daily.vercel.app`：
- 点击浏览器菜单 → `添加到主屏幕`
- 主屏幕上出现「深度思辨」图标
- 点击图标以独立 App 形式打开

---

## 第五步：日常使用

设置好后，你什么都不用管：

| 时间 | 发生的事情 |
|------|----------|
| 每天早上 8:00 | GitHub Actions 自动运行 |
| 8:02 | 从 36 氪获取新闻 → LLM 生成 3 条分析 |
| 8:05 | 飞书群收到卡片推送 |
| 你看到推送 | 点击「开始今日思辨」→ 进入 PWA |
| 思辨中 | 浏览多学科视角 → 与 AI 对话 → 生成笔记 |
| Vercel 自动 | 每次 GitHub 有更新，Vercel 自动重新部署 |

---

## 备用方案：企业微信机器人

如果你不用飞书，企业微信同样简单：

### 创建企业微信机器人
1. 打开企业微信，进入任意群聊
2. 右上角 `...` → `群机器人` → `添加`
3. 复制 Webhook 地址
4. 在 GitHub Secrets 中添加 `WECOM_WEBHOOK`

### 企业微信推送到个人微信
企业微信的群机器人消息可以同步到个人微信（如果你开通了「微信插件」）。
- 企业微信管理后台 → `我的企业` → `微信插件`
- 扫码关注后，企业微信群的消息会同步到个人微信

---

## 备用方案：钉钉机器人

同理：
1. 钉钉群 → `群设置` → `智能群助手` → `添加机器人` → `自定义`
2. 安全设置选择「自定义关键词」，填入 `思辨`
3. 复制 Webhook → 添加 `DINGTALK_WEBHOOK` 到 GitHub Secrets

---

## 自定义 36 氪新闻源

**好消息：36氪 RSS Feed 经实测可用，无需手动维护。**

数据获取方式：

```
GET https://36kr.com/feed
Headers: { "User-Agent": "Mozilla/5.0" }
```

每天早上 7:48 左右，「八点一氪」专栏文章会出现在 RSS Feed 中，包含：
- 今日热点导览（当日最值得关注的新闻概要）
- TOP3 大新闻（完整的事件描述和背景）
- AI 最前沿（AI 行业最新动态）

脚本会自动抓取、解析XML、寻找「8点1氪」文章、提取纯文本、传给 LLM 分析。

如果遇到极端情况（RSS 挂了、八点一氪没更新），脚本会：
1. 回退：取 RSS 中前5篇文章的标题
2. 兜底：读取 `scripts/news_input.txt` 中的手动输入

---

## 常见问题

**Q: GitHub Actions 每月免费额度够用吗？**
A: 免费额度 2000 分钟/月，每天运行一次约 3 分钟，月用量约 90 分钟，完全够用。

**Q: Vercel Hobby 计划够用吗？**
A: 每月 100GB 带宽，个人使用绰绰有余。PWA 缓存后流量更少。

**Q: 飞书机器人需要审核吗？**
A: 自定义机器人（Webhook）不需要。只有「应用机器人」才需要审核。我们用的是最简单的 Webhook 方式。

**Q: 我能同时推送到飞书和企业微信吗？**
A: 可以。在 GitHub Secrets 中同时配置 `FEISHU_WEBHOOK` 和 `WECOM_WEBHOOK`，脚本会同时推送。

**Q: 怎么修改推送时间？**
A: 编辑 `.github/workflows/daily-update.yml`，修改 `cron: '0 0 * * *'`。
   - UTC 时间，北京时间 = UTC + 8
   - `0 0 * * *` = 北京时间早上 8 点
   - `0 22 * * *` = 北京时间早上 6 点
