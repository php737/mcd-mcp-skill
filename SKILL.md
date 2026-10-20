---
name: mcd-mcp
description: "麦当劳中国 MCP 平台,查询门店、领优惠券、点餐(到店自取/麦乐送/得来速/企业团餐)、查积分、抽奖、积分兑换餐品券/实物商品、查商城订单、主题活动(派对/品鉴会)查询/下单。触发词:查麦当劳优惠、领券、点麦当劳、查积分、麦当劳热量、麦乐送、得来速、团餐、积分兑换、抽奖、麦当劳派对、品鉴会、主题活动、随单购、麦金卡、早餐卡、套餐特制、历史订单。"
metadata: { "openclaw": { "emoji": "🍔", "requires": { "bins": ["python"], "env": ["MCD_MCP_TOKEN"] }, "primaryEnv": "MCD_MCP_TOKEN" } }
---

**返回格式要求**：所有查询结果必须以**markdown 表格形式**展示，包含字段名和字段值，便于用户一目了然。
- 优惠券列表：表格展示优惠名称、价格、有效期、标签
- 餐品详情：表格展示名称、价格、选配项(modification)
- 套餐：表格展示包含的主食/小食/饮料
- 门店信息：表格展示门店名称、地址、code、beCode
- 积分账户：表格展示可用/累计/已用/过期
- 抽奖：表格展示活动名称、消耗、奖品列表、可抽奖次数
- 主题活动：表格展示活动名/价格/可约城市/门店/日期/场次
- 订单信息：表格展示订单号/状态/金额/内容
- 商城订单：表格展示订单号/状态/商品/积分
- 营养成分：表格展示名称/热量/蛋白质/脂肪/碳水/钠等

# McDonald's China MCP Skill (v4.0)

调用麦当劳中国 MCP Server（基于 Model Context Protocol）的 Python客户端。本 skill 已对齐官方文档 **v1.0.9 / 2026-09-10**。

## 配置

Token 通过环境变量 `MCD_MCP_TOKEN` 传入(本机配置在 `openclaw.json` 的 `env.vars.MCD_MCP_TOKEN`)。

Token 申请地址：https://open.mcd.cn/mcp（登录后控制台申请）

## 使用方法

**统一使用 JSON 格式传参**（所有参数均为 JSON 字符串）

```bash
python <skill_dir>/scripts/call_tool.py <工具名> '<JSON参数>'
```

无参数时可不传 JSON，有参数时必须用 JSON 格式。

## 参数规范说明（重要！）

| 参数 | 含义 |
|------|------|
| `searchType` | 1=查询收藏, 2=按位置搜索（searchType=2 时 city+keyword 必填） |
| `beType` | **1=到店自取**, **2=麦乐送**, **5=得来速(DT)**, **6=企业团餐** |
| `orderType` | 1=到店自取/得来速, 2=外送（麦乐送/团餐） |
| `beCode` | 业务实体编码。**到店/得来速**：从 `query-nearby-stores` 返回取；**外送/团餐**：从 `delivery-query-stores` 返回取；到店场景下也可传 `null` |
| `takeWayCode` | 到店取餐方式，从 `calculate-price` 返回的 `takeWayList` 中取（如 `eat-in`/`take-out`/`locker-in`），不是数字 |
| `reservationDate` | 预约时间，格式 `yyyy-MM-dd HH:mm`，预约场景下必填 |
| `gmServiceCode` | 企业团餐场景的助餐服务 code，从 `query-meal-assistance` 返回取 |
| `withOrder` | 随单购商品，从 `query-meals` 返回的 `withOrder` 字段带入算价/下单 |
| `items.productCode` | 商品编码（注意：不是 `code`，是 `productCode`） |
| `items.modification` | 单品特调，套餐内组合更换/部分餐品特制 |
| `items.roundList` | 商品子项，套餐组合明细 |
| `items.couponId` / `couponCode` | 优惠券 ID / 编码（选填，要在订单里用券时才传） |
| `mall-create-order.spuCategory` | "1"=虚拟餐品券, "2"=实物商品（实物时必须传 `addressId`） |

## 工具清单（共 34 个）

### 🕐 通用
| 命令 | 功能 | 参数 |
|------|------|------|
| `now-time-info` | 当前时间（含时区/UTC） | 无 |
| `list-nutrition-foods` | 餐品营养成分（紧凑 TOON 格式） | 无 |

### 🎫 积分 & 优惠券
| 命令 | 功能 | 参数 |
|------|------|------|
| `query-my-account` | 查积分账户 | 无 |
| `query-my-coupons` | 查我的优惠券 | 无 |
| `available-coupons` | 查可领优惠券 | 无 |
| `auto-bind-coupons` | 一键领所有可用券 | 无 |

### 🏪 门店
| 命令 | 功能 | 参数 |
|------|------|------|
| `query-nearby-stores` | 附近门店（到店自取/得来速） | `{"searchType":1,"beType":1}` 收藏模式；或 `{"searchType":2,"city":"长沙","keyword":"中建悦和城","beType":5}` 按位置 |
| `delivery-query-addresses` | 我的配送地址 | `{"beType":2}`（2=麦乐送，6=团餐） |
| `delivery-create-address` | 新增配送地址 | `{"city":"","contactName":"","phone":"","address":"","addressDetail":"","gender":"先生","beType":2}` |
| `delivery-query-stores` | 外送场景查询可配送门店 | `{"addressId":"xxx","beType":2}`（先调 `delivery-query-addresses` 拿 addressId，再调这个拿 beCode） |

### 🍔 餐品 & 点餐
| 命令 | 功能 | 参数 |
|------|------|------|
| `query-store-coupons` | 当前门店可用券 | `{"storeCode":"xxx","orderType":1,"beCode":"xxx","beType":1,"reservationDate":"2026-06-10 18:00"}`（预约场景必填 reservationDate） |
| `query-meals` | 当前门店菜单（含促销价/随单购） | `{"storeCode":"xxx","orderType":1,"beCode":"xxx","beType":1}` |
| `query-meal-detail` | 餐品详情（含特制 modification） | `{"code":"xxx","storeCode":"xxx","orderType":1,"beCode":"xxx","beType":1}` |
| `query-meal-assistance` | 团餐助餐服务 | `{"storeCode":"xxx","beCode":"xxx","beType":6,"orderType":2,"reservationDate":"2026-06-10 18:00"}`（仅 beType=6 团餐） |
| `calculate-price` | 价格计算（含优惠/随单购/特制） | `{"storeCode":"xxx","orderType":1,"beCode":"xxx","beType":1,"items":[{"productCode":"xxx","quantity":1}],"reservationDate":"2026-06-10 18:00","gmServiceCode":"GMSxxx","withOrder":{...}}` |
| `create-order` | 创建订单 | `{"storeCode":"xxx","beCode":"xxx","beType":1,"orderType":1,"takeWayCode":"eat-in","items":[{"productCode":"xxx","quantity":1}],"reservationDate":"2026-06-10 18:00","addressId":"xxx","gmServiceCode":"GMSxxx","withOrder":{...}}` |
| `query-order` | 查订单详情 | `{"orderId":"xxx"}` |
| **`order-list`** | **查询历史订单（到店/外送）** | 无 |
| **`cancel-order`** | **取消点餐订单** | `{"orderId":"xxx","cancelReasonCode":1}`（cancelReasonCode: 1=改主意了, 2=重复下单, 3=点错了/点多了/点少了, 4=地址/电话填错了, 5=送达时间选错了, -1=其它原因） |

### 🎉 互动与内容
| 命令 | 功能 | 参数 |
|------|------|------|
| `campaign-calendar` | 活动日历 | `{"specifiedDate":"yyyy-MM-dd"}` 可选（不传查今天，传日期查附近 3 天） |
| **`query-lottery-info`** | **查看积分抽奖活动信息** | 无 |
| **`draw-lottery`** | **积分抽奖** | 无（自动按活动规则消耗积分/次数） |
| **`query-my-prizes`** | **查看我的奖品** | 无（可选分页参数） |

### 🎟️ 麦麦省领券
| 命令 | 功能 | 参数 |
|------|------|------|
| `available-coupons` | 麦麦省券列表查询 | 无 |
| `auto-bind-coupons` | 麦麦省一键领券 | 无 |
| `query-my-coupons` | 我的优惠券查询 | 无 |

### 🎁 麦麦商城（积分兑换）
| 命令 | 功能 | 参数 |
|------|------|------|
| `mall-points-products` | 积分兑换商品列表 | 无（可选 `{"catRuleIds":"1>4,2"}`，1>4=餐品券, 2=实物商品） |
| `mall-product-detail` | 积分商品详情 | `{"spuId":542}` |
| `mall-create-order` | 积分兑换下单 | 虚拟券：`{"skuId":10997,"count":1}`；实物：`{"skuId":10863,"count":1,"addressId":"xxx","spuCategory":"2"}` |
| `mall-order-list` | 商城订单列表 | `{"lastId":81954,"size":10}`（lastId 翻页用，首次不传） |
| `mall-order-detail` | 商城订单详情 | `{"orderId":"ECS1202144786604392448"}` |

### 🎊 主题活动（派对/品鉴会）
| 命令 | 功能 | 参数 |
|------|------|------|
| **`query-party-city`** | **主题活动可参与城市** | 无 |
| **`query-party-store`** | **指定城市主题活动门店** | `{"city":"上海"}` |
| **`query-partystore-date`** | **指定门店可预约日期** | `{"storeCode":"xxx","city":"上海"}` |
| **`query-partystore-session`** | **指定日期场次** | `{"storeCode":"xxx","city":"上海","date":"2026-09-15"}` |
| **`party-order-create`** | **主题活动订单创建** | `{"storeCode":"xxx","city":"上海","date":"2026-09-15","session":"AM","spuId":xxx,"skuId":xxx,"count":1}` |

## 调用示例

```bash
# 通用 / 积分 / 优惠券 / 活动（无参数）
python call_tool.py now-time-info
python call_tool.py list-nutrition-foods
python call_tool.py query-my-account
python call_tool.py query-my-coupons
python call_tool.py available-coupons
python call_tool.py auto-bind-coupons
python call_tool.py campaign-calendar

# 积分抽奖
python call_tool.py query-lottery-info
python call_tool.py draw-lottery
python call_tool.py query-my-prizes

# 取消订单（需 --confirm）
python call_tool.py cancel '{"orderId":"xxx","cancelReasonCode":1}' --confirm
# cancelReasonCode 枚举: 1=改主意了, 2=重复下单, 3=点错了/点多了/点少了, 4=地址/电话填错了, 5=送达时间选错了, -1=其它原因

# 附近门店（到店收藏模式）
python call_tool.py query-nearby-stores '{"searchType":1,"beType":1}'
# 按位置搜索得来速
python call_tool.py query-nearby-stores '{"searchType":2,"city":"长沙","keyword":"中建悦和城","beType":5}'

# 麦乐送流程
python call_tool.py delivery-query-addresses '{"beType":2}'
python call_tool.py delivery-query-stores '{"addressId":"1","beType":2}'

# 餐品菜单（到店）
python call_tool.py query-meals '{"storeCode":"3390091","orderType":1,"beCode":"<从 query-nearby-stores 取>","beType":1}'
# 餐品详情（含特制 modification）
python call_tool.py query-meal-detail '{"code":"520860","storeCode":"3390091","orderType":1,"beCode":"<从 query-nearby-stores 取>","beType":1}'

# 门店可用优惠券（到店）
python call_tool.py query-store-coupons '{"storeCode":"3390091","orderType":1,"beCode":"<从 query-nearby-stores 取>","beType":1}'

# 价格计算（含随单购 + 特制）
python call_tool.py calculate-price '{"storeCode":"3390091","orderType":1,"beCode":"<从 query-nearby-stores 取>","beType":1,"items":[{"productCode":"1440","quantity":1}],"withOrder":{...}}'

# 创建订单（到店）
python call_tool.py create-order '{"storeCode":"3390091","beCode":"<从 query-nearby-stores 取>","beType":1,"orderType":1,"takeWayCode":"eat-in","items":[{"productCode":"1440","quantity":1}]}'

# 预约场景
python call_tool.py calculate-price '{"storeCode":"3390091","orderType":1,"beCode":"<从 query-nearby-stores 取>","beType":1,"reservationDate":"2026-09-10 18:00","items":[{"productCode":"1440","quantity":1}]}'
python call_tool.py create-order '{"storeCode":"3390091","beCode":"<从 query-nearby-stores 取>","beType":1,"orderType":1,"takeWayCode":"eat-in","reservationDate":"2026-09-10 18:00","items":[{"productCode":"1440","quantity":1}]}'

# 企业团餐
python call_tool.py query-meal-assistance '{"storeCode":"3390091","beCode":"xxx","beType":6,"orderType":2,"reservationDate":"2026-09-10 12:00"}'
python call_tool.py calculate-price '{"storeCode":"3390091","orderType":2,"beCode":"xxx","beType":6,"reservationDate":"2026-09-10 12:00","gmServiceCode":"GMSxxx","items":[{"productCode":"1440","quantity":10}]}'

# 查询订单
python call_tool.py query-order '{"orderId":"xxx"}'
# 历史订单
python call_tool.py order-list

# 营养成分
python call_tool.py list-nutrition-foods

# 积分商城
python call_tool.py mall-points-products '{"catRuleIds":"1>4,2"}'
python call_tool.py mall-product-detail '{"spuId":542}'
python call_tool.py mall-create-order '{"skuId":10997,"count":1}'
python call_tool.py mall-create-order '{"skuId":10863,"count":1,"spuCategory":"2","addressId":"xxx"}'
python call_tool.py mall-order-list
python call_tool.py mall-order-detail '{"orderId":"ECS1202144786604392448"}'

# 主题活动
python call_tool.py query-party-city
python call_tool.py query-party-store '{"city":"上海"}'
python call_tool.py query-partystore-date '{"storeCode":"xxx","city":"上海"}'
python call_tool.py query-partystore-session '{"storeCode":"xxx","city":"上海","date":"2026-09-15"}'
python call_tool.py party-order-create '{"storeCode":"xxx","city":"上海","date":"2026-09-15","session":"AM","spuId":xxx,"skuId":xxx,"count":1}'

# 当前时间
python call_tool.py now-time-info
```

## 关键流程

### 1. 到店自取
```
query-nearby-stores(searchType=1, beType=1)
 → 取 storeCode + beCode
 → query-meals / query-meal-detail
 → query-store-coupons（可选）
 → calculate-price（含 withOrder/modification）
 → create-order(takeWayCode=从 calculate-price.takeWayList 取)
```

### 2. 得来速（DT）
```
query-nearby-stores(searchType=2, beType=5, city, keyword)
 → 后续同上
```

### 3. 麦乐送
```
delivery-query-addresses(beType=2)
 → 取 addressId
 → delivery-query-stores(addressId, beType=2)
 → 取 storeCode + beCode
 → query-meals / calculate-price
 → create-order(orderType=2, beType=2)
```

### 4. 企业团餐
```
delivery-query-addresses(beType=6)
 → delivery-query-stores(addressId, beType=6)
 → query-meal-assistance(storeCode, beCode, beType=6, orderType=2, reservationDate)
 → 取 gmServiceCode
 → calculate-price(..., gmServiceCode, reservationDate)
 → create-order(..., gmServiceCode, reservationDate)
```

### 5. 积分兑换实物
```
mall-points-products(catRuleIds="2")  # 筛实物
 → mall-product-detail(spuId) → 取 skuId
 → delivery-query-addresses(beType=2) → 取 addressId
 → mall-create-order(skuId, count, addressId, spuCategory="2")
```

### 6. 主题活动（派对/品鉴会）
```
query-party-city  → 选城市
 → query-party-store(city=xxx)  → 选门店
 → query-partystore-date(storeCode, city)  → 选日期
 → query-partystore-session(storeCode, city, date)  → 选场次
 → mall-points-products 找活动 spuId/skuId（或 mall-product-detail）
 → party-order-create(...)  → 创建订单
```

### 7. 积分抽奖
```
query-lottery-info  → 看活动规则、可抽奖次数、奖品列表
 → draw-lottery  → 抽奖
 → query-my-prizes  → 看历史奖品
```

### 8. 取消订单
```
query-order(orderId=xxx)  → 确认订单状态（仅"待支付"/"待接单"等可取消状态才允许）
 → cancel-order(orderId, cancelReasonCode) --confirm  → 取消
```
⚠️ 取消订单需 `--confirm` 才会真正执行；订单取消后状态不可恢复

## MCP Server 信息

- **地址**: `https://mcp.mcd.cn`
- **协议**: Streamable HTTP + JSON-RPC2.0
- **认证**: `Authorization: Bearer <TOKEN>`
- **限流**: 600 次/分钟（429 错误码表示超限）
- **协议版本**: MCP2025-06-18
- **官方工具总数**: 34 个（v1.0.9 / 2026-09-10）

## 版本记录

| 日期 | 版本 | 说明 |
|------|------|------|
| **2026-09-10** | **1.0.9** | **新增 `cancel-order` 取消订单工具；`calculate-price` / `create-order` 加 `needTableware`（是否要餐具）；`create-order` 加 `remark`（外送备注，最多 50 字，如"无接触配送"）；堂食外带场景 `create-order` / `query-order` 响应新增 `lockerQrCode`（取餐柜二维码）** |

**本 skill 版本**: v4.1（已对齐官方 v1.0.9）

## 注意事项

- `takeWayCode` 是字符串（如 `eat-in` / `take-out` / `locker-in`），**不是数字**，从 `calculate-price` 返回的 `takeWayList` 取
- `beCode` 不要瞎编，到店从 `query-nearby-stores` 取，外送从 `delivery-query-stores` 取
- `code`（餐品详情参数）和 `productCode`（订单/价格参数）是不同字段
- `mall-create-order` 兑换实物时必须传 `spuCategory="2"` + `addressId`，虚拟券不传这两个字段
- 预约场景（`reservationDate`）所有点餐工具都需要传，格式 `yyyy-MM-dd HH:mm`
- 查询订单用 `query-order`（单订单），历史订单用 `order-list`（最近 10 笔），商城订单用 `mall-order-list` / `mall-order-detail`
- **`modification`**: 套餐组合更换/特制用，传给 `calculate-price` / `create-order` 时放在 `items[].modification.values[]`，含 `code` / `quantity` / `key`
- **`withOrder`**: 用户期望享受麦金卡/早餐卡随单购优惠时，把 `query-meals` 返回的 `withOrder` 对象整体带入 `calculate-price` / `create-order` 的 `withOrder` 字段
- **积分抽奖**: `draw-lottery` 不需要参数，调用前先用 `query-lottery-info` 确认活动状态和消耗规则；`query-my-prizes` 支持分页
- **主题活动**: `party-order-create` 需先把 `spuId`/`skuId` 从 `mall-product-detail` 拿到，配合 `city`/`date`/`session` 完成下单
- **v1.0.9 `needTableware`**: 用户点餐时是否需要餐具，`calculate-price` / `create-order` 选传；为 `true` 时响应里会多 `tablewarePrice`（单位分）
- **v1.0.9 `remark`**: 外送订单备注，仅 `orderType=2`（麦乐送/团餐）场景下生效，最多 50 字，常见值"无接触配送"
- **v1.0.9 `lockerQrCode`**: 堂食外带场景（`takeWayCode=locker-in`）下，`create-order` 和 `query-order` 响应会多 `lockerQrCode` 字段（取餐柜二维码 URL）
- **v1.0.9 `cancel-order`**: 取消订单有副作用（订单状态不可恢复），需加 `--confirm` 才会真正执行；`cancelReasonCode` 必须传枚举值