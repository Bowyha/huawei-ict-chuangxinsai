# 输入输出契约与使用

## 运行

Python 3.9+，无需第三方包。运行 `python scripts/validate_itinerary.py examples/basic-plan.json`，也可从标准输入读入 JSON。费用和规则校验无网络请求、无定位。运行 `python scripts/test_validate_itinerary.py` 做回归测试。

宿主代码可导入 `validate_itinerary.validate(plan)` 做单份校验，或 `validate_itinerary.review(payload)` 同时校验原案和草案。AgentArts 需要开发者按节点参数编写入口包装和映射；文件不会自动注册为平台工具。

命令行输出 JSON。原案 invalid 时退出码2，其他检查状态退出码0；必须读取 JSON 中的业务状态，不能将退出码0误认为行程pass。

## 输入结构

顶层 `{"plan": 完整原案, "candidate": 完整草案或null}`。只检查时省略candidate。下面的字段除明确可null外均必需。可运行的完整人工样例位于 [examples/basic-plan.json](../examples/basic-plan.json)，不是酒店/景点实时报价或运营资料。

### plan.requirements

| 字段 | 类型与含义 |
|---|---|
| budget | null或{currency,amount_minor,scope}；全程预算，scope明确覆盖范围 |
| mandatory_place_ids | 必去地点ID列表，无则[] |
| daily_walking_limit_m | 非负整数米或null；来自用户，不由年龄推断 |
| daily_windows | 日期到{start,end}的映射，无限制则{}；可跨午夜 |
| deadlines | {activity_id,at,evidence}列表；引用实际到达活动，at已扣除进站等缓冲 |
| allowed_transport_modes | 允许的交通方式字符串列表，null表示未限制 |
| additional_checks | {name,status,evidence}列表；status=pass/fail/unknown，承载其他硬条件 |

### plan.activities[]

id/name/place_id为非空字符串，id唯一。day为开始时间当地YYYY-MM-DD。start/end为带时区ISO时间，结束晚于开始；按开始时间升序输入，不排序掩盖问题。status=planned/completed/in_progress；locked和optional为布尔值。

min_duration_minutes=合理最短游览分钟数或null；walking_m=活动内部步行米数或null，不能遗漏园区内部步行。evidence适用于本活动数据。

opening={applicable,windows,latest_entry,is_latest_entry_known,evidence}：applicable布尔值；windows为{start,end}数组、null未知、[]已知关闭；latest_entry为时间或null；is_latest_entry_known=false表示最晚入场规则尚未核实，true且latest_entry=null表示明确无额外最晚入场限制。

reservation={required,confirmed,window,evidence}：required和confirmed为true/false/null；window={start,end}或null，是允许到达入场范围。required=false时不需要confirmed或window有值。

### plan.legs[]

恰好每相邻两活动一条，按相邻顺序排列。字段from_id/to_id、day（归入出发活动的day）、mode、duration_minutes、buffer_minutes、walking_m、evidence。三个数值字段为非负整数或null。未知不得补零。跨天步行归属规则见validation-rules.md。

### plan.cost_items[]

字段id、charge_key、amount_minor、currency、paid、evidence。金额是全程所有人该费用项合计，非负整数或null；币种使用大写三字母代码，最小单位按币种确定。id及charge_key唯一。paid布尔值。房费结果可由住宿Skill提供，不能再次乘人数/晚数；未知住宿总价传null。

plan.costs_complete为布尔值，表示预算范围的必要费用是否已穷尽。押金不算消费；退款在实际核实前不抵减费用。若范围含住宿但未查询住宿，不能设true。

### evidence 与 sources

evidence={status,source_ids}，status=verified/estimated/unknown，source_ids引用plan.sources的ID。verified/estimated至少引用一个来源。sources[]={id,reference,queried_at}，reference可为官方URL、工具结果标识或用户明确输入，queried_at带时区。真实运行不能引用测试资料来证明真实营业、交通或价格。

引用存在并不证明真实性：程序检查引用完整性，资料是否适用于目标日期需由查询层核实。估算会输出到assumptions；关键证据unknown使整体至少incomplete。

## 输出结构

```json
{
  "status": "pass",
  "summary": {"failed": 0, "unknown": 0, "passed": 12},
  "checks": [],
  "issues": [],
  "missing_data": [],
  "assumptions": [],
  "cost_summary": {},
  "errors": [],
  "proposed_changes": [],
  "requires_confirmation": false,
  "revised_itinerary": null,
  "recheck_result": null,
  "sources": []
}
```

以上仅展示字段形状，passed应由真实checks计算，不照抄示例数。

- status是原方案状态；有草案时recheck_result.status才是草案复检状态。invalid时可能没有summary。
- checks每项含rule/status/message/activity_ids/source_ids；issues为fail项，missing_data为unknown项。数量与检查条目有关，单个活动可能有多个问题。
- cost_summary含known_totals_minor（各币种分别统计）、complete、budget_status、scope；证据可靠性仍看总报告。金额未知不能算已确认的免费。
- proposed_changes含kind/id/before/after/requires_confirmation。Skill可增加reason解释修改目的，但不得改写程序事实。
- revised_itinerary是草案，不等于正式接受；recheck_result按原始requirements复检。用户确认变更约束后，上游形成新的正式plan再检查。
- requires_confirmation并不覆盖校验结果：需要确认的方案不能自动发布；fail也不能因为确认标记而当作通过。

## 行为联调

在宿主使用人工地点和模拟资料检查：未知交通应补查或incomplete；没有执行工具不能声称程序通过；不定位测试者；固定活动变化待确认；历史记录不改写；超过两轮修正仍不可行应停止并给出取舍。自动测试只验证脚本逻辑，不替代模型和工具联调。
