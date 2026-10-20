# 输入输出契约

## 使用方法

Python 3.9+，标准库：`python scripts/replan_guard.py examples/delay-replan.json`，或从标准输入读JSON。调用函数 `replan_guard.run(payload)` 可接代码节点。无第三方包、无网络、无定位。顶层invalid退出码2，其余退出码0；0不等于通过，须读取status。

## 顶层输入

| 字段 | 说明 |
|---|---|
| original_version | 非空版本标识，宿主负责与正式方案版本核对 |
| plan | 完整最新进度基线，与travel-plan-review契约一致 |
| sources | 本次用户请求/事件/新资料来源数组，与plan.sources合并；相同ID不可改变内容 |
| current_state | as_of、ready_at、anchor_place_id、location_source、location_authorized、source_ids |
| event | id、kind、description、status、source_ids、restrictions |
| requirement_updates | 已确认或待确认的硬约束更新数组，无则[] |
| candidate | 完整草案，可省略/null表示prepare |
| start_leg | 当前锚点到第一个未来活动的交通，review时需要；全部未来活动删掉时无需 |

current_state的时间含日期及UTC偏移，ready_at>=as_of。anchor_place_id只用公共地点标识，不用精确设备坐标。location_source=user_provided/authorized_device；后者必须location_authorized=true，前者可false。测试用user_provided。source_ids引用用户明确输入/进度证据。

event.kind=departure_delay/weather/place_unavailable/preference/budget/mobility；status=confirmed/unknown。restrictions={blocked_place_ids:[],blocked_windows:[]}；每个window含place_id/start/end，按重叠时段检查。限制仅应用于planned活动，不抹除过去已去过的地点。

requirement_updates每项{field,value,confirmed,source_ids}，field是plan.requirements的字段名称（例如budget），value是完整替换值，不能重复同字段。confirmed=true须来自明确用户决定，由宿主传入，智能体不能捏造；未确认的不应用。完整替换值需满足原校验契约。例：budget={currency:"CNY",amount_minor:90000,scope:"两人全程住宿和门票"}。

start_leg字段：from_place_id/to_activity_id/mode/duration_minutes/buffer_minutes/walking_m/evidence。三个数值是非负整数或null。evidence={status:verified/estimated/unknown,source_ids:[]}。与最后冻结活动之间的边界leg若存在，两处交通字段须一致，不重复累计步行；没有冻结活动时由guard额外把当前起点交通计入当日步行上限。当前交通费用应加入candidate.cost_items，是否漏费由上层检查并控制costs_complete。

## plan/candidate结构速查

同travel-plan-review输入，原有上游可以复用；完整可运行样例见 [模拟延误案例](../examples/delay-replan.json)。任何字段缺失或类型不符返回invalid，不用零填补。

- requirements：budget(null或currency/amount_minor/scope)、mandatory_place_ids列表、daily_walking_limit_m(null或非负整数)、daily_windows(日期到start/end对象)、deadlines(activity_id/at/evidence列表)、allowed_transport_modes(null或字符串列表)、additional_checks(name/status/evidence列表)。
- activities：id/name/place_id/day/start/end/status/locked/optional/min_duration_minutes/walking_m/evidence/opening/reservation。status=planned/completed/in_progress；min_duration_minutes与walking_m可null。opening={applicable,windows,latest_entry,is_latest_entry_known,evidence}，windows=null未知、[]关闭、其他为start/end列表。reservation={required,confirmed,window,evidence}，required/confirmed可null，window可null。时间必须带日期与时区。
- legs：每相邻活动恰好一项from_id/to_id/day/mode/duration_minutes/buffer_minutes/walking_m/evidence，day等于起点活动day。三个数值可null。
- cost_items：id/charge_key/amount_minor/currency/paid/evidence；金额为整个范围内该费用项所有人所有晚数总额，非负整数最小单位或null，不再乘人数。id与charge_key唯一。
- costs_complete：预算覆盖范围费用是否完整，布尔值。
- sources：id/reference/queried_at列表；reference为网页URL/工具结果标识/用户明确输入，queried_at带时区。
- evidence：status=verified/estimated/unknown；前两者必须有有效source_ids。估算仍需披露，不是未来结果保证。

## 输出

status：invalid=输入无法处理；finished=基线已无未完成活动；partial=缺资料或未核实；blocked=该草案存在冲突；needs_confirmation=存在待确认修改；ready=本模式完成。

必须同时读mode：prepare的ready只表示准备状态有效；review的ready表示草案经当前数据检查通过，不代表用户已接受、订单已改或没有现实不确定性。

主要字段：original_version、event_id、frozen_activity_ids、adjustable_activity_ids、stale_activity_ids、applied_requirement_updates、pending_requirement_updates、missing_data、guard_issues、validation、requires_confirmation、candidate、baseline_for_planning、sources。review中的validation包含校验器原案结果及recheck_result，顶层guard检查可能更严格。

推荐给用户的最终工作流JSON可包含guard原始结果及 explanation（变更原因）、next_steps、attempt_count。不得覆写原始status；needs_confirmation不能用解释文字自动改成ready。输出不默认带用户坐标或登录信息。

已通过但未接受的草案由宿主展示；用户接受后宿主核对original_version，生成新版本。guard本身不持久化、不去重事件，不保证并发安全。

## 测试

`python scripts/test_replan_guard.py`运行离线测试。所有来源为人工模拟，不能当作真实景点营业、预约或价格证据。真实环境还需验证工具调用、权限、状态保存和两轮停止行为。
