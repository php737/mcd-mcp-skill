# mcd-mcp

麦当劳中国 MCP 平台的 Python 客户端 —— 把「查优惠、领券、看门店菜单、点餐、查积分、积分兑换」变成一行命令行。

支持官方 **34 个 MCP 工具**(协议版本 v1.0.9 / 2026-09-10),全部输出为便于阅读的 markdown 表格。

> ⚠️ **非官方项目**。与麦当劳公司(McDonald's Corporation)无任何关联或背书。麦当劳中国 MCP 平台归麦当劳所有,申请 Token 与使用其服务请遵守其官方条款。

---

## 这个工具解决什么

直接调 MCP Server 需要自己拼 JSON-RPC 报文、自己处理分页、自己把结构化响应翻译成人话。这个客户端把这些都包掉了:

- **别名**: `coupons` / `calendar` / `nearby-stores` / `points` 等短名,不用背 34 个长名字
- **自动补参数**: 查菜单、算价、下单时若缺 `beCode`,自动从门店接口取
- **表格化输出**: 券、门店、菜单、积分、订单、营养成分都是 markdown 表格
- **危险操作需确认**: 下单、抽奖、取消订单、积分兑换必须显式加 `--confirm`,否则只打印警告不执行

---

## 安装

```bash
git clone https://github.com/php737/mcd-mcp-skill.git
cd mcd-mcp-skill
pip install -r requirements.txt
export MCD_MCP_TOKEN=你的TOKEN
```

依赖只有 `curl_cffi`(用于 TLS 指纹伪装,部分接口对普通 `requests` 会拒)。

Token 申请:登录 <https://open.mcd.cn/mcp> 控制台申请。

### 接入 OpenClaw

把本目录放到 `~/.openclaw/skills/mcd-mcp/`,并在 `openclaw.json` 中配置环境变量:

```json
{
  "env": {
    "vars": {
      "MCD_MCP_TOKEN": "你的TOKEN"
    }
  }
}
```

`SKILL.md` 是给 AI Agent 看的操作手册(触发词、参数规范、34 个工具清单、关键流程),与本 README 并存,用途不同。

---

## 快速开始

### 领优惠券

```bash
python scripts/call_tool.py available-coupons
```

```
🔧 调用工具: available-coupons

🍔 麦麦省可领优惠券
────────────────────────────────
     ✅ 状态：已领取
```

一键领取全部可领券:

```bash
python scripts/call_tool.py auto-bind-coupons
```

```
🎉 领券结果（共3张，成功3张，失败?张）
────────────────────────────────
### 领券结果

总计: 3 张优惠券
成功: 3 张
失败: 0 张

---

#### 成功领取的优惠券：

- 免费脆薯饼
  - couponId：0D94B7923332F58026539DB8CCA81275
  - couponCode：MCD66T106Z90F005YSH10

- 人气麦旋风买一送一
  - couponId：9856FF6299069479D1AC037870375F1A
  - couponCode：MCD61U0H0Z07F89T0Y501

- 9.9元中杯冰美式
  - couponId：264B97DBE02BE6CF996AA6914151C4A9
  - couponCode：MCD6FW0T01019H9Z600Y3
```

查看账户已有券:

```bash
python scripts/call_tool.py query-my-coupons
```

```
🎫 我的优惠券
────────────────────────────────
# 您的优惠券列表

共 4 张可用优惠券 | 第 1/1 页 | 每页 200 条

## 11.9元麦辣鸡腿堡
- **优惠**: ¥11.9 (用券价格)
- **有效期**: 2026-10-19 10:30-2026-10-23 23:59 周一、二、三、四、五 10:30-23:59
- **领取时间**: 3日前收到
- **标签**: Pickup、Delivery

## 人气麦旋风买一送一
- **优惠**: ¥15 (用券价格)
- **有效期**: 2026-10-19 00:00-2026-10-25 23:59 10:00-22:00
- **领取时间**: 今日收到
- **标签**: Pickup
```

### 优惠日历

```bash
python scripts/call_tool.py campaign-calendar
python scripts/call_tool.py campaign-calendar '{"specifiedDate":"2026-10-22"}'
```

```
📅 麦当劳活动日历
────────────────────────────────
### 当前时间：2026-10-20 20:20:58

### 活动列表：

#### 2026年10月20日 今日

-   **活动标题**：麦当劳 X PEACEMINUSONE
    **活动内容介绍**：GD同款联名复古棒球帽
    任意餐品消费加39.9元即可得
    经典红黄配色搭配复古轮廓,MV同款灵感重现
    更有标志性小雏菊刺绣图案点缀
    10月8日10:45开售
    更有APP专享积分抢先购10:40开抢
```

### 查门店、菜单、下单

```bash
# 附近门店(收藏模式)
python scripts/call_tool.py query-nearby-stores '{"searchType":1,"beType":1}'

# 按位置搜得来速
python scripts/call_tool.py query-nearby-stores '{"searchType":2,"city":"长沙","keyword":"中建悦和城","beType":5}'

# 门店菜单
python scripts/call_tool.py query-meals '{"storeCode":"3390091","orderType":1,"beType":1}'

# 算价(可带券)
python scripts/call_tool.py calculate-price '{"storeCode":"3390091","orderType":1,"beType":1,"items":[{"productCode":"1440","quantity":1}]}'

# 下单 —— 必须 --confirm
python scripts/call_tool.py create-order '{"storeCode":"3390091","orderType":1,"beType":1,"takeWayCode":"eat-in","items":[{"productCode":"1440","quantity":1}]}' --confirm
```

### 其他常用

```bash
python scripts/call_tool.py query-my-account        # 积分账户
python scripts/call_tool.py list-nutrition-foods   # 餐品营养成分
python scripts/call_tool.py order-list             # 历史订单
python scripts/call_tool.py now-time-info          # 服务器当前时间
```

---

## 参数传递

所有参数都是 **JSON 字符串**,可以整体传,也可以拆成 `key=value` 对:

```bash
python scripts/call_tool.py query-meals '{"storeCode":"3390091","beType":1}'
python scripts/call_tool.py query-meals storeCode=3390091 beType=1
```

### 常用枚举

| 参数 | 取值 | 含义 |
|---|---|---|
| `searchType` | 1 / 2 | 1=查询收藏,2=按位置搜索(此时 `city`+`keyword` 必填) |
| `beType` | 1 / 2 / 5 / 6 | 1=到店自取,2=麦乐送,5=得来速,6=企业团餐 |
| `orderType` | 1 / 2 | 1=到店自取/得来速,2=外送 |
| `takeWayCode` | 字符串 | `eat-in` / `take-out` / `locker-in`,**不是数字**,从 `calculate-price` 返回的 `takeWayList` 取 |
| `reservationDate` | `yyyy-MM-dd HH:mm` | 预约场景必填 |
| `cancelReasonCode` | 1 / 2 / 3 / 4 / 5 / -1 | 改主意 / 重复下单 / 点错 / 地址电话错 / 送达时间错 / 其它 |

### 危险操作

以下工具不加 `--confirm` 时只打印警告,不执行:

`draw-lottery`(抽奖扣积分)、`create-order`(下单)、`cancel-order`(取消订单,状态不可恢复)、`mall-create-order`(积分兑换)、`party-order-create`(主题活动下单)

---

## 目录结构

```
.
├── README.md            # 本文件,面向人
├── SKILL.md             # 面向 AI Agent 的操作手册(34 工具清单/参数规范/流程)
├── LICENSE              # MIT + 非官方声明
├── requirements.txt     # curl_cffi
├── .gitignore
└── scripts/
    └── call_tool.py     # 单文件客户端:JSON-RPC 封装 + 34 个 formatter + 别名/危险操作保护
```

`scripts/call_tool.py` 是单文件设计 —— 拷走就能跑,无需打包。核心结构:

| 区段 | 内容 |
|---|---|
| 顶部常量 | `MCP_SERVER_URL` / `MCP_PROTOCOL_VERSION` / token 读取 |
| `json_rpc_request()` | JSON-RPC 2.0 封装,`curl_cffi` 带 Chrome 指纹 |
| `call_tool()` | initialize 后调用工具,返回原始结构 |
| `get_default_store()` / `get_be_code()` | 自动补 `storeCode` / `beCode` |
| `format_*(data)` × 30 | 每个工具一个 markdown 表格 formatter |
| `FORMATTERS` / `DANGEROUS_TOOLS` / `ALIASES` | 三个映射表,分别是工具→formatter、危险工具清单、别名表 |
| `main()` | 参数解析(`--confirm` 门禁在此)→ 调用 → 格式化输出 |

---

## 已知边界

- **只做点餐与账户侧能力**,不含第三方视频站、歌曲识别等非官方能力
- **`query-meals` 偶发服务端 400**(`缺少参数`),客户端会自动降级到 `list-nutrition-foods` 输出营养成分列表作为替代浏览
- **取消订单不可恢复**,状态一旦变更无法回滚
- **限流**:MCP Server 约 600 次/分钟,超限返回 429

---

## Licence

MIT,见 [LICENSE](./LICENSE)。Outfit 字体等第三方资源不在本仓库范围内。
