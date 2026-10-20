import sys
import os
import json
import argparse
import re

from curl_cffi import requests

MCP_SERVER_URL = "https://mcp.mcd.cn"
MCP_PROTOCOL_VERSION = "2025-06-18"

MCP_TOKEN = os.environ.get("MCD_MCP_TOKEN") or os.environ.get("mcd_mcp_token", "").strip()

HEADERS = {
    "Content-Type": "application/json",
    "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
}

def get_headers() -> dict:
    h = dict(HEADERS)
    if MCP_TOKEN:
        h["Authorization"] = f"Bearer {MCP_TOKEN}"
    return h

def json_rpc_request(method: str, params: dict = None) -> dict:
    """发送 JSON-RPC 2.0 请求"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {},
    }
    try:
        resp = requests.post(
            MCP_SERVER_URL,
            json=payload,
            headers=get_headers(),
            timeout=30,
            impersonate="chrome",
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

_mcp_initialized = False

def mcp_initialize() -> None:
    """MCP 握手（全局只做一次）"""
    global _mcp_initialized
    if _mcp_initialized:
        return
    result = json_rpc_request("initialize", {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "mcd-mcp-client", "version": "3.0.0"}
    })
    if "error" in result:
        raise Exception(f"MCP 初始化失败: {result['error']}")
    _mcp_initialized = True

def call_tool(tool_name: str, arguments: dict = None) -> dict:
    """调用指定的 MCP 工具"""
    mcp_initialize()
    params = {"name": tool_name}
    if arguments:
        params["arguments"] = arguments
    return json_rpc_request("tools/call", params)

def get_default_store() -> dict:
    """获取收藏门店（searchType=1），返回 storeCode 和 storeName"""
    result = json_rpc_request("tools/call", {
        "name": "query-nearby-stores",
        "arguments": {"searchType": 1, "beType": 1}
    })
    sc = result.get("result", {}).get("structuredContent", {})
    stores = sc.get("data", [])
    if stores:
        return stores[0]
    return {}

def get_be_code(store_code: str, be_type: int = 1) -> str:
    """
    获取 beCode：
    - 到店/得来速（beType=1/5）：从 query-nearby-stores 返回的门店列表取
    - 外送/团餐（beType=2/6）：从 delivery-query-stores 返回的门店列表取
    """
    if be_type in (1, 5):
        result = json_rpc_request("tools/call", {
            "name": "query-nearby-stores",
            "arguments": {"searchType": 1, "beType": be_type}
        })
        sc = result.get("result", {}).get("structuredContent", {})
        stores = sc.get("data", [])
        for s in stores:
            if s.get("storeCode") == store_code:
                return s.get("beCode", "")
        return ""
    else:
        addr_result = json_rpc_request("tools/call", {
            "name": "delivery-query-addresses",
            "arguments": {"beType": be_type}
        })
        sc = addr_result.get("result", {}).get("structuredContent", {})
        addresses = sc.get("data", {}).get("addresses", [])
        if not addresses:
            return ""
        for addr in addresses:
            store_result = json_rpc_request("tools/call", {
                "name": "delivery-query-stores",
                "arguments": {"addressId": addr.get("addressId"), "beType": be_type}
            })
            sc2 = store_result.get("result", {}).get("structuredContent", {})
            stores = sc2.get("data", [])
            for s in stores:
                if s.get("storeCode") == store_code:
                    return s.get("beCode", "")
        return ""

def get_text_content(result: dict) -> str:
    """从 MCP result 中提取 text content"""
    content = result.get("content", [])
    if not content:
        return ""
    try:
        return content[0].get("text", "")
    except (IndexError, KeyError):
        return str(content)

def format_available_coupons(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    text = get_text_content(result)
    if not text:
        return "⚠️ 未返回可用优惠券"
    lines = ["🍔 麦麦省可领优惠券", "─" * 32]
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("[") or line.startswith("-" * 10) or "couponId" in line:
            continue
        if "优惠券标题" in line:
            continue
        if line.startswith("🎟️"):
            lines.append(f"  {line}")
        elif any(kw in line for kw in ["已领取", "未领取", "不可领取"]):
            icon = "✅" if "已领取" in line else ("❌" if "不可领取" in line else "⏳")
            lines.append(f"     {icon} {line.strip()}")
    return "\n".join(lines) if len(lines) > 2 else text[:2000]

def format_auto_bind_result(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    text = get_text_content(result)
    if not text:
        return "⚠️ 未返回结果"
    sc = result.get("structuredContent", {})
    d = sc.get("data") or {}
    total = d.get("totalCount", "?")
    success = d.get("successCount", "?")
    failed = d.get("failCount", "?")
    header = f"🎉 领券结果（共{total}张，成功{success}张，失败{failed}张）"
    return header + "\n" + "─" * 32 + "\n" + text

def format_my_coupons(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    text = get_text_content(result)
    if not text:
        return "⚠️ 未查询到优惠券"
    return "🎫 我的优惠券\n" + "─" * 32 + "\n" + text[:3000]

def format_my_account(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        text = get_text_content(result)
        if not text:
            return "⚠️ 未查询到积分信息"
        try:
            json_str = re.search(r'\{[^{}]*"availablePoint"[^{}]*\}', text)
            if json_str:
                dd = json.loads(json_str.group())
                lines = [
                    "💰 麦麦积分账户",
                    "─" * 32,
                    f"  可用积分: {dd.get('availablePoint', 'N/A')} 分",
                    f"  累计积分: {dd.get('accumulativePoint', 'N/A')} 分",
                    f"  已使用积分: {dd.get('usedPoint', 'N/A')} 分",
                    f"  冻结积分: {dd.get('frozenPoint', 'N/A')} 分",
                    f"  已过期积分: {dd.get('expiredPoint', 'N/A')} 分",
                ]
                return "\n".join(lines)
        except Exception:
            pass
        return "💰 麦麦积分账户\n" + "─" * 32 + "\n" + text[:2000]

    lines = [
        "💰 麦麦积分账户",
        "─" * 32,
        f"  可用积分: {d.get('availablePoint', 'N/A')} 分",
        f"  累计积分: {d.get('accumulativePoint', 'N/A')} 分",
        f"  已使用积分: {d.get('usedPoint', 'N/A')} 分",
        f"  冻结积分: {d.get('frozenPoint', 'N/A')} 分",
        f"  已过期积分: {d.get('expiredPoint', 'N/A')} 分",
    ]
    if d.get('nextMouthExpirePoint', '0') not in ('0', None, ''):
        lines.append(f"  下月将过期: {d['nextMouthExpirePoint']} 分")
    return "\n".join(lines)

def format_nearby_stores(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    stores = sc.get("data", [])

    if not stores:
        msg = sc.get("message", "")
        return f"📍 附近门店查询\n" + "─" * 32 + f"\n  {msg or '未找到附近门店'}"

    lines = ["📍 附近麦当劳门店", "─" * 32]
    for s in stores[:10]:
        name = s.get("storeName", "未知门店")
        addr = s.get("address", "")
        code = s.get("storeCode", "")
        bec = s.get("beCode", "")
        dist = s.get("distance", 0)
        dist_km = round(dist / 1000, 1) if dist else None
        lines.append(f"  🏪 {name}")
        if addr:
            lines.append(f"     📍 {addr}")
        if dist_km:
            lines.append(f"     📏 距离 {dist_km}km")
        if code:
            lines.append(f"     🔖 storeCode: {code}")
        if bec:
            lines.append(f"     🏷️ beCode: {bec}")
        lines.append("")
    return "\n".join(lines).strip()

def format_delivery_addresses(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    addrs = sc.get("data", {}).get("addresses", [])

    if not addrs:
        return "📦 配送地址\n" + "─" * 32 + "\n  暂无配送地址"

    lines = [f"📦 配送地址列表（共{len(addrs)}个）", "─" * 32]
    for a in addrs:
        lines.append(f"  🏠 {a.get('contactName', '')} {a.get('phone', '')}")
        lines.append(f"     {a.get('fullAddress', '')}")
        lines.append(f"     门店: {a.get('storeName', '')} (storeCode: {a.get('storeCode', '')})")
        lines.append(f"     beCode: {a.get('beCode', '')}")
        lines.append("")
    return "\n".join(lines).strip()

def format_delivery_create_address(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回结果"
    return (
        f"✅ 配送地址创建成功\n" + "─" * 32 + f"\n"
        f"  地址ID: {d.get('addressId', '')}\n"
        f"  联系人: {d.get('contactName', '')}\n"
        f"  电话: {d.get('phone', '')}\n"
        f"  完整地址: {d.get('fullAddress', '')}\n"
        f"  门店: {d.get('storeName', '')} (storeCode: {d.get('storeCode', '')})"
    )

def format_calendar(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    text = get_text_content(result)
    if not text:
        return "⚠️ 未查询到活动日历"
    return "📅 麦当劳活动日历\n" + "─" * 32 + "\n" + text[:5000]

def format_nutrition(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    raw = sc.get("data", "") or get_text_content(result)

    lines = [
        "🍔 餐品营养成分",
        "─" * 32,
        f"{'餐品':<18} {'kJ':<7} {'kcal':<6} {'蛋白质':<6} {'脂肪':<6} {'碳水':<6} {'钠(mg)':<8} {'钙(mg)':<8}"
    ]
    lines.append(" " + "─" * 75)

    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("[") or line.startswith("{"):
            continue
        parts = line.split(",")
        if len(parts) >= 9:
            name = parts[0].strip()
            kj = parts[2].strip() if parts[2] != "null" else "-"
            kcal = parts[3].strip() if parts[3] != "null" else "-"
            protein = parts[4].strip() if parts[4] != "null" else "-"
            fat = parts[5].strip() if parts[5] != "null" else "-"
            carb = parts[6].strip() if parts[6] != "null" else "-"
            sodium = parts[7].strip() if parts[7] != "null" else "-"
            calcium = parts[8].strip() if len(parts) > 8 and parts[8] != "null" else "-"
            if name:
                lines.append(f"  {name:<16} {kj:<7} {kcal:<6} {protein:<6} {fat:<6} {carb:<6} {sodium:<8} {calcium:<8}")

    return "\n".join(lines[:50])

def format_points_products(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    items = sc.get("data", []) or []

    if not items:
        return "🎁 积分兑换商品\n" + "─" * 32 + "\n  暂无可兑换商品"

    lines = ["🎁 积分兑换商品", "─" * 32,
             f"{'商品名称':<22} {'积分':<6} {'截止时间'}"]
    lines.append(" " + "─" * 50)
    for item in items[:20]:
        name = item.get("spuName", "")[:22]
        pts = item.get("point", "")
        down = item.get("downTime", "")[:10]
        lines.append(f"  {name:<20} {pts:<6} {down}")
    return "\n".join(lines)

def format_mall_product_detail(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回商品详情"
    lines = [
        "🎁 积分商品详情",
        "─" * 32,
        f"  商品名称: {d.get('spuName', '')}",
        f"  积分: {d.get('points', d.get('point', ''))}",
        f"  有效期: {d.get('downDate', d.get('downTime', ''))}",
        f"  卖点: {d.get('selling', '')}",
    ]
    detail = d.get("detail", "")
    if detail:
        lines.append(f"  详情: {detail}")
    return "\n".join(lines)

def format_mall_create_order(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回结果"
    coupons = d.get("coupons", [])
    lines = [
        "✅ 积分兑换成功",
        "─" * 32,
        f"  订单号: {d.get('orderId', '')}",
        f"  状态: {d.get('status', '')}",
    ]
    for c in coupons:
        for code in c.get("couponCodes", []):
            lines.append(f"  券码: {code}")
    return "\n".join(lines)

def format_order(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回订单信息"
    lines = [
        "🛒 订单详情",
        "─" * 32,
        f"  订单号: {d.get('orderId', '')}",
        f"  状态: {d.get('orderStatus', '')}",
        f"  门店: {d.get('storeName', '')}",
        f"  实付: {d.get('realTotalAmount', '')}",
        f"  下单时间: {d.get('createTime', '')}",
    ]
    delivery = d.get("deliveryInfo", {})
    if delivery:
        lines.append(f"  配送地址: {delivery.get('deliveryAddress', '')}")
    # v1.0.9+ 堂食外带场景返回取餐柜二维码
    locker_qr = d.get("lockerQrCode", "")
    if locker_qr:
        lines.append(f"  🗄️ 取餐柜码: {locker_qr}")
    remark = d.get("remark", "")
    if remark:
        lines.append(f"  📝 备注: {remark}")
    return "\n".join(lines)

def format_create_order(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回订单信息"
    # v1.0.9+ 响应里 orderDetail 包含 lockerQrCode / remark
    detail = d.get("orderDetail", {}) if isinstance(d.get("orderDetail"), dict) else {}
    lines = [
        "✅ 订单创建成功",
        "─" * 32,
        f"  订单号: {d.get('orderId', '')}",
        f"  门店: {detail.get('storeName', d.get('storeName', ''))}",
        f"  总金额: ¥{detail.get('totalAmount', d.get('realTotalAmount', d.get('totalAmount', '?')))}",
        f"  配送费: ¥{detail.get('deliveryPrice', d.get('realDeliveryPrice', '?'))}",
        f"  就餐方式: {detail.get('takeWay', d.get('takeWay', ''))}",
    ]
    pay_url = d.get("payH5Url", "") or (d.get("paymentInfo", {}).get("payUrl", ""))
    if pay_url:
        lines.append(f"  支付链接: {pay_url}")
    pickup = d.get("pickupCode", "") or detail.get("pickupCode", "")
    if pickup:
        lines.append(f"  取餐码: {pickup}")
    # v1.0.9+ 堂食外带场景取餐柜二维码 / 备注
    locker_qr = d.get("lockerQrCode", "") or detail.get("lockerQrCode", "")
    if locker_qr:
        lines.append(f"  🗄️ 取餐柜码: {locker_qr}")
    remark = d.get("remark", "") or detail.get("remark", "")
    if remark:
        lines.append(f"  📝 备注: {remark}")
    return "\n".join(lines)

def format_price_calc(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回价格信息"
    lines = [
        "💰 价格计算结果",
        "─" * 32,
        f"  商品总价: ¥{d.get('productPrice', '?')}",
        f"  配送费: ¥{d.get('deliveryPrice', '?')}",
        f"  优惠金额: -¥{d.get('totalDiscountAmount', '0')}",
        f"  实付金额: ¥{d.get('price', d.get('realTotalAmount', '?'))}",
    ]
    # v1.0.9+ 餐具费(单位分,转元)
    tableware = d.get("tablewarePrice")
    if tableware not in (None, '', 0, '0'):
        try:
            yuan = int(tableware) / 100
            lines.append(f"  餐具费: ¥{yuan:.2f}")
        except (ValueError, TypeError):
            lines.append(f"  餐具费: {tableware}分")
    pl = d.get("productList", [])
    if pl:
        names = [p.get("productName", "") for p in pl]
        lines.append(f"  商品: {', '.join(names)}")
    tw = d.get("takeWayList", [])
    if tw:
        tw_names = [t.get("name", t.get("takeWay", str(t))) if isinstance(t, dict) else str(t) for t in tw]
        lines.append(f"  可用取餐方式: {', '.join(tw_names)}")
    return "\n".join(lines)

def format_store_coupons(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    coupons = sc.get("data", []) or []

    if not coupons:
        msg = sc.get("message", "")
        return "🎟️ 门店可用优惠券\n" + "─" * 32 + f"\n  暂无可用优惠券（{msg}）"

    lines = ["🎟️ 门店可用优惠券", "─" * 32]
    for c in coupons:
        title = c.get("title", "")
        code = c.get("couponCode", "")
        valid = c.get("tradeDateTime", "")
        products = c.get("products", [])
        prod_names = ", ".join(p.get("productName", "") for p in products) or "全场通用"
        lines.append(f"  🍔 {title}")
        lines.append(f"     券码: {code}")
        lines.append(f"     有效期: {valid}")
        lines.append(f"     适用: {prod_names}")
        lines.append("")
    return "\n".join(lines).strip()

def format_meal_detail(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    text = get_text_content(result)
    if not text:
        return "⚠️ 未返回餐品详情"
    return "🍔 餐品详情\n" + "─" * 32 + "\n" + text[:3000]

def format_now_time(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回时间信息"
    return (
        f"🕐 当前时间信息\n" + "─" * 32 + f"\n"
        f"  日期时间: {d.get('formatted', d.get('datetime', ''))}\n"
        f"  星期: {d.get('dayOfWeek', '')}\n"
        f"  时区: {d.get('timezone', '')}\n"
        f"  UTC: {d.get('utc', '')}"
    )

def format_delivery_stores(data: dict) -> str:
    """外送场景下可配送门店"""
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    stores = sc.get("data", [])
    if not stores:
        msg = sc.get("message", "")
        return f"📦 可配送门店\n" + "─" * 32 + f"\n  {msg or '暂无可配送门店'}"
    lines = ["📦 可配送门店", "─" * 32]
    for s in stores[:10]:
        lines.append(f"  🏪 {s.get('storeName', '未知门店')}")
        lines.append(f"     storeCode: {s.get('storeCode', '')}")
        lines.append(f"     beCode: {s.get('beCode', '')}")
        status = "营业中" if s.get("businessStatus") else "休息中"
        start = s.get("businessStartTime", "")
        end = s.get("businessEndTime", "")
        if start or end:
            lines.append(f"     ⏰ 营业: {start}-{end} ({status})")
        reserv = s.get("reservationTimeOptions", [])
        if reserv:
            options = " | ".join(r.get("reservationOptionText", "") for r in reserv[:3])
            lines.append(f"     📅 预约: {options}")
        lines.append("")
    return "\n".join(lines).strip()

def format_meal_assistance(data: dict) -> str:
    """团餐助餐服务"""
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回助餐服务信息"
    lines = ["🍱 企业团餐助餐服务", "─" * 32]
    items = d.get("mealAssistanceItems", [])
    if items:
        lines.append("  可选服务：")
        for it in items:
            mark = "✅ 已选" if it.get("selected") else ("🟢 可用" if it.get("enable") else "⚫ 不可用")
            lines.append(f"    {mark} {it.get('gmServiceName', '')} ({it.get('gmServiceCode', '')})")
            services = it.get("serviceItems", [])
            for sv in services:
                lines.append(f"       • {sv}")
    promos = d.get("promotions", [])
    if promos:
        lines.append("")
        lines.append("  🎁 优惠：")
        for p in promos:
            lines.append(f"    • {p}")
    return "\n".join(lines)

def format_mall_order_list(data: dict) -> str:
    """麦麦商城订单列表"""
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    pages = sc.get("data", [])
    if not pages:
        return "🛒 麦麦商城订单\n" + "─" * 32 + "\n  暂无商城订单"
    all_orders = []
    has_next = False
    last_id = None
    for p in pages:
        if p.get("hasNext"):
            has_next = True
        last_id = p.get("lastId")
        all_orders.extend(p.get("list", []))
    lines = [f"🛒 麦麦商城订单（共 {len(all_orders)} 单{'，还有更多' if has_next else ''}）", "─" * 32]
    for o in all_orders[:20]:
        lines.append(f"  📦 订单号: {o.get('orderId', '')}")
        lines.append(f"     状态: {o.get('orderStatusTitle', o.get('orderStatus', ''))}")
        goods = o.get("goods", [])
        for g in goods:
            name = g.get("spuName", "")
            sku = g.get("skuName", "")
            cnt = g.get("count", 1)
            price = g.get("price", "")
            label = f"{name}"
            if sku:
                label += f" ({sku})"
            lines.append(f"     🧾 {label} ×{cnt} ¥{price}")
        tag = o.get("tag", {})
        if tag.get("name"):
            lines.append(f"     🏷️ 渠道: {tag['name']}")
        lines.append("")
    if last_id and has_next:
        lines.append(f"  💡 还有更多订单，下一页 lastId: {last_id}")
        lines.append(f"     用法: mall-order-list '{{\"lastId\":{last_id}}}'")
    return "\n".join(lines).strip()

def format_mall_order_detail(data: dict) -> str:
    """麦麦商城订单详情"""
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回订单详情"
    lines = [
        "🛒 麦麦商城订单详情",
        "─" * 32,
        f"  订单号: {d.get('orderId', '')}",
        f"  状态: {d.get('orderStatusTitle', '')}",
        f"  状态说明: {d.get('orderStatusSubTitle', '')}",
        f"  店铺: {d.get('shopName', '')}",
        f"  下单时间: {d.get('createTime', '')}",
        f"  商品总金额: ¥{d.get('goodsTotalPrice', '0')}",
        f"  实际支付: ¥{d.get('realTotalAmount', '0')}",
        f"  使用积分: {d.get('realTotalPoints', '0')}",
    ]
    if d.get('leftPaySecond') and int(d.get('leftPaySecond', 0)) > 0:
        lines.append(f"  剩余支付时间: {int(d['leftPaySecond'])}秒")
    addr = d.get("addressVO", {})
    if addr:
        lines.append(f"  收货地址: {addr.get('contactName', '')} {addr.get('phone', '')}")
        lines.append(f"           {addr.get('fullAddress', '')}")
    pay_id = d.get("payId", "")
    if pay_id:
        lines.append(f"  支付ID: {pay_id}")
    goods = d.get("goods", [])
    if goods:
        lines.append("")
        lines.append("  🧾 商品清单：")
        for g in goods:
            label = g.get("spuName", "")
            sku = g.get("skuName", "")
            if sku:
                label += f" ({sku})"
            lines.append(f"     • {label} ×{g.get('count', 1)} ¥{g.get('price', '')}")
    return "\n".join(lines)

def format_cancel_order(data: dict) -> str:
    """v1.0.9+ 取消订单结果"""
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    sc = result.get("structuredContent", {})
    d = sc.get("data", {})
    if not d:
        return "⚠️ 未返回取消结果"
    cancel_ok = d.get("cancelResult", False)
    oid = d.get("orderId", "")
    icon = "✅" if cancel_ok else "❌"
    status = "已取消" if cancel_ok else "取消失败"
    return f"{icon} 订单{status}\n" + "─" * 32 + f"\n  订单号: {oid}\n  取消结果: {cancel_ok}"


def format_raw(data: dict) -> str:
    if "error" in data:
        return f"❌ 错误: {data['error']}"
    result = data.get("result", {})
    text = get_text_content(result)
    sc = result.get("structuredContent", {})
    if sc:
        return json.dumps(sc, indent=2, ensure_ascii=False)[:5000]
    return text[:5000] if text else "⚠️ 未返回结果"

FORMATTERS = {
    "available-coupons": format_available_coupons,
    "auto-bind-coupons": format_auto_bind_result,
    "query-my-coupons": format_my_coupons,
    "query-my-account": format_my_account,
    "query-nearby-stores": format_nearby_stores,
    "delivery-query-addresses": format_delivery_addresses,
    "delivery-create-address": format_delivery_create_address,
    "delivery-query-stores": format_delivery_stores,
    "query-meal-assistance": format_meal_assistance,
    "campaign-calendar": format_calendar,
    "list-nutrition-foods": format_nutrition,
    "mall-points-products": format_points_products,
    "mall-product-detail": format_mall_product_detail,
    "mall-create-order": format_mall_create_order,
    "mall-order-list": format_mall_order_list,
    "mall-order-detail": format_mall_order_detail,
    "query-order": format_order,
    "create-order": format_create_order,
    "cancel-order": format_cancel_order,
    "calculate-price": format_price_calc,
    "query-store-coupons": format_store_coupons,
    "query-meal-detail": format_meal_detail,
    "query-meals": format_raw,
    "now-time-info": format_now_time,
    "order-list": format_raw,
    "query-party-city": format_raw,
    "query-party-store": format_raw,
    "query-partystore-date": format_raw,
    "query-partystore-session": format_raw,
    "party-order-create": format_raw,
    "query-lottery-info": format_raw,
    "draw-lottery": format_raw,
    "query-my-prizes": format_raw,
}

DANGEROUS_TOOLS = {
    "draw-lottery": "积分抽奖（消耗积分）",
    "create-order": "创建点餐订单（可能产生支付链接）",
    "cancel-order": "取消点餐订单（订单状态不可恢复）",
    "mall-create-order": "积分兑换下单（扣积分）",
    "party-order-create": "主题活动订单（可能产生支付链接）",
}

ALIASES = {
    "nearby-stores": "query-nearby-stores",
    "stores": "query-nearby-stores",
    "my-account": "query-my-account",
    "account": "query-my-account",
    "my-coupons": "query-my-coupons",
    "coupons": "query-my-coupons",
    "auto-bind": "auto-bind-coupons",
    "available": "available-coupons",
    "calendar": "campaign-calendar",
    "nutrition": "list-nutrition-foods",
    "points-products": "mall-points-products",
    "points": "mall-points-products",
    "order": "query-order",
    "orders": "order-list",
    "cancel": "cancel-order",
    "addr": "delivery-query-addresses",
    "addresses": "delivery-query-addresses",
    "delivery-stores": "delivery-query-stores",
    "meal-assistance": "query-meal-assistance",
    "mall-orders": "mall-order-list",
    "mall-order": "mall-order-detail",
}

def main():
    if not MCP_TOKEN:
        print("❌ 未设置 MCD_MCP_TOKEN 环境变量")
        print("请设置环境变量 MCD_MCP_TOKEN（或在 openclaw.json 的 env.vars.MCD_MCP_TOKEN 中配置）")
        print("或运行: export MCD_MCP_TOKEN=你的TOKEN")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="麦当劳 MCP 工具调用")
    parser.add_argument("tool", help="工具名称或别名")
    parser.add_argument("params", nargs="*", help="JSON 格式参数（可选）")
    parser.add_argument("--confirm", action="store_true", help="显式确认执行危险操作（draw-lottery / create-order / mall-create-order / party-order-create）")
    parsed = parser.parse_args()

    tool_name = ALIASES.get(parsed.tool, parsed.tool)

    if tool_name in DANGEROUS_TOOLS and not parsed.confirm:
        print(f"⚠️  {tool_name} 是危险操作：{DANGEROUS_TOOLS[tool_name]}")
        print(f"   加 --confirm 才执行（不加只会打印这个警告）")
        return
    arguments = {}
    params = parsed.params

    if params:
        raw = " ".join(params)
        try:
            arguments = json.loads(raw)
        except json.JSONDecodeError:
            for pair in raw.split():
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    try:
                        arguments[k] = json.loads(v)
                    except json.JSONDecodeError:
                        arguments[k] = v

    need_store = tool_name in ("query-meals", "query-meal-detail", "query-store-coupons",
                               "calculate-price", "create-order")
    if need_store and arguments.get("storeCode") in (None, ""):
        default_store = get_default_store()
        if default_store:
            arguments["storeCode"] = default_store.get("storeCode", "")
            print(f"🔍 使用默认门店: {default_store.get('storeName', '')} ({arguments['storeCode']})")

    if tool_name in ("query-meals", "query-store-coupons", "calculate-price", "create-order"):
        if not arguments.get("beCode"):
            store_code = arguments.get("storeCode", "")
            if store_code:
                be_type = arguments.get("beType", 1)
                try:
                    be_type = int(be_type)
                except (TypeError, ValueError):
                    be_type = 1
                be_code = get_be_code(store_code, be_type)
                if be_code:
                    arguments["beCode"] = be_code
                    print(f"📍 自动填充 beCode: {be_code}")

    print(f"🔧 调用工具: {tool_name}")
    if arguments:
        print(f"📦 参数: {arguments}")

    result = call_tool(tool_name, arguments if arguments else None)

    if tool_name == "query-meals":
        sc = result.get("result", {}).get("structuredContent", {})
        if sc.get("code") == 400 and "缺少参数" in str(sc.get("message", "")):
            print("\n⚠️ query-meals 接口暂时不可用（服务端 bug），正在通过营养成分列表提供替代浏览...")
            result = call_tool("list-nutrition-foods", None)
            formatter = FORMATTERS.get("list-nutrition-foods", format_raw)
            output = formatter(result)
            print("\n" + output)
            return

    formatter = FORMATTERS.get(tool_name, format_raw)
    output = formatter(result)
    print("\n" + output)

if __name__ == "__main__":
    main()
