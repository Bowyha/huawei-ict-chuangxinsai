# 输入输出契约

## Skill 输入

接收自然语言或对象：`mode` 为 area/hotel/compare/nearby；`requirements` 包含 destination、check_in/check_out（YYYY-MM-DD）、adults、children_ages、rooms、bed_preference、budget（amount_minor/currency/scope，scope 为 total 或 per_room_per_night）、hard_constraints、preferences、landmarks、requested_platforms。未知为 null，不用虚构默认值填满。

`location_context` 可由宿主提供：source=manual_destination/manual_landmark/authorized_device；consent=not_requested/granted/denied/revoked；只有有效授权时在本次工具调用内使用精确坐标。无定位工具或授权失败转手动输入。不要求用户提供身份证号、密码等预订身份数据。

## Skill 输出（固定顶层结构）

```json
{
  "status": "needs_clarification",
  "requirements": {"destination": "用户指定城市", "check_in": null, "check_out": null},
  "questions": ["请提供入住和退房日期。"],
  "search_context": {"mode": "hotel", "source": "manual_destination", "label": "用户指定城市"},
  "areas": [],
  "hotels": [],
  "offers": [],
  "recommendations": [],
  "sources": [],
  "unknowns": ["入住日期未知"]
}
```

status：needs_clarification=缺少当前模式必要输入；completed=本次请求已完成且关键事实可核实（区域模式不要求报价）；partial=仍有缺失/访问限制；failed=无法获取足够数据。成功查询但无匹配酒店可以 completed，并明确无匹配结果。

- areas：id/name/reasons/tradeoffs/source_ids。
- hotels：id/name/address/platform_ids/facilities/hard_constraint_checks/review_summary/source_ids。设施和约束逐条有状态及来源。
- offers：id/hotel_id/platform/room_name/room_features/occupancy/check_in/check_out/rooms/breakfast/cancellation/payment/eligibility/availability/comparability/cost_input/cost_result/queried_at/url/source_ids。取消字段包括 deadline_local/timezone/penalty；价格未知为 null。availability=available/unavailable/request_confirmation/unknown；comparability=equivalent/different/unknown。
- recommendations：hotel_id/offer_id/category/reasons/tradeoffs/unknowns。category=balanced/lower_cost/flexible。
- sources：id/platform/url/queried_at/access_status/limitations；用户提供资料可没有URL，但明确user_provided。
- 每个事实通过 source_ids 关联真正支持它的来源，不能将首页链接充当房型条款证据。

`search_context` 只展示粗粒度文字及来源，不输出精确用户坐标。工作流模式输出纯 JSON，未知值 null，列表无内容时 []。

## 离线费用工具

Python 3.9+，仅标准库。命令：`python scripts/compare_stay_costs.py input.json`；也可从标准输入读入 JSON。输出一份 JSON，参数无效时退出码2。工作流可导入 `compare_stay_costs.compare(payload)`；宿主自行将其封装成代码节点/插件，不会自动注册。

```json
{
  "budget": {"currency": "CNY", "amount_minor": 150000},
  "offers": [{
    "id": "demo-a",
    "currency": "CNY",
    "check_in": "2026-11-01",
    "check_out": "2026-11-03",
    "rooms": 2,
    "base": {"mode": "nightly_per_room", "amounts_minor": [30000, 35000]},
    "extra_fees": [{"name": "服务费", "amount_minor": 5000, "included_in_base": false}],
    "costs_complete": true,
    "eligibility": "eligible",
    "deposit_minor": 20000
  }]
}
```

示例为虚构测试数据，不是真实酒店报价。结果全程135000最小单位，即1350元；押金200元另外展示。

字段约定：budget 可为 null；offers 为数组且 id 唯一。rooms为正整数；日期须有效且退房晚于入住。base.mode 二选一：nightly_per_room 使用与晚数相等的 amounts_minor 数组（元素可为 null）；stay_total 使用 amount_minor（所有房间全程总价，可为 null）。extra_fees 必须提供，数组项的 included_in_base 必须为布尔值，amount_minor 非负整数或 null。costs_complete 必须为布尔值；eligibility=eligible/ineligible/unknown；deposit_minor非负整数或 null。金额不接受布尔值、负数、小数或数字字符串。

脚本输出 status=ok/partial/invalid；逐条给出 known_subtotal_minor、total_minor（不完整或资格不明时null）、cost_status=complete/incomplete/ineligible、budget_status=within/over/unknown/currency_mismatch/not_provided/not_applicable、nights、rooms、deposit_minor、issues。无效报价不会阻止其余报价计算，但总体状态为 partial。脚本不判断房态、来源真实性、可比性或设施；这些必须由上层核实，`within` 不等于酒店已满足全部需求。

## 验收场景

行为检查：提前规划不定位；附近请求先检查权限；拒绝定位转手动；没有日期不给实时价；平台受限返回partial；价格或设施未知不判满足；改变日期使旧报价失效。使用手动地点/模拟数据，不获取测试者位置。

运行随包 `scripts/test_compare_stay_costs.py` 验证计算边界。它是费用测试，不替代真实平台联调或模型行为验收。
