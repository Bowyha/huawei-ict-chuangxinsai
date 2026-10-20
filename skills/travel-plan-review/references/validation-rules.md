# 校验规则

## 状态与证据

结构错误优先 invalid；有效数据中 fail 优先于 incomplete；没有二者才 pass。每项检查返回 rule、activity_ids、status(pass/fail/unknown)、message、source_ids；完整报告另有 issues、missing_data、summary。单项未知不能用其他单项通过抵消。

金额、交通来自调用方；缺来源时由 evidence 检查拦截。真实资料标 verified，估算标 estimated，缺失标 unknown。verified/estimated 都须提供 source_ids，其中ID必须存在于 sources。查询时间、来源正文及是否适用于具体日期由上层核实，程序只验证声明和引用结构，不替代真实查证。估算可用于规划通过，但报告必保留 assumptions。

## 日期与顺序

所有时间为 ISO 8601 且带时区偏移（例如 2026-11-06T09:00:00+08:00），用实际时刻比较。完整日期正确支持跨午夜。活动 day 用开始时间的当地日期，日界以 daily_windows 明确的时间窗为准；跨午夜活动和交通不能用同一天时分相减。

活动按输入顺序作为计划顺序，不静默排序。起始时间倒序或结束不晚于开始为 invalid；顺序正确但区间重叠是 fail。日期有效性、ID唯一性、引用完整性、整数和布尔类型也严格检查。

## 时间与交通

每相邻两项活动恰好一条 leg，from_id/to_id 对应实际顺序。可用空隙 >= duration_minutes + buffer_minutes；二者未知时 unknown，不默认为零。零交通仅适用于经确认同地或无需移动的情况，须有 evidence。

活动 min_duration_minutes（可null）由上游给出合理下限，不是模型为通过校验随意设置。用户 daily_windows 限定活动及其后的交通占用须在该日允许时窗内。交通跨天时 walking_m 全部计入该 leg 的 day；若需精确按两天分摊，上游应拆分为中间交通活动，不能漏记。

## 开放、预约和固定时间

opening.applicable=false 用于不受营业时段影响的活动；true 时 windows=null 为未知，[] 为已核实当天关闭。整个活动须落在一个开放区间内；午间闭馆不能用首个开门到最后关门拼成长窗口。latest_entry 有值则检查开始不晚于该时刻，时间点相等允许；is_latest_entry_known=false 时 unknown。

reservation.required=null 为尚不清楚预约要求；false为无需预约；true时confirmed必须为true，null为未知，false为未确认而不可作为已落实行程。预约窗口为允许入场范围，检查活动开始是否落入；有规定结束时间的活动另由活动/开放窗口约束。预约 required=true 但 window=null 视为资料不足。

返站/固定截止通过 deadlines 表达：activity_id 指向明确的到达车站/集合点活动；start <= deadline.at。到达该点的交通由前一 leg 检查。进站缓冲须由用户/运营信息设置为提前后的 deadline.at，并注明依据，不一律使用固定分钟数。

## 预算

cost_items 每项 amount_minor 是预算范围内、全程所有人的总额；不再按人数或晚数乘算。id 与 charge_key 均唯一，防止同一费用重复计算；charge_key 必须由上游代表同一收费事项，不可为重复项随意分配新key。语义重复仍需人工/上游复核。

budget.scope 描述覆盖范围；costs_complete 表示该范围必要费用是否已穷尽。未知金额 null，押金不列为消费费用。不同币种不相加，记录 currency mismatch；需转换时上游提供有来源的同币种估算。已知同币种部分超预算即 fail；已知部分未超但存在未知/异币种/未穷尽则 unknown。未设预算也报告费用是否完整，不捏造预算。

## 用户要求

mandatory_place_ids 检查地点是否实际出现在活动中。daily_walking_limit_m 有值时，逐日累加活动内部与交通 walking_m；任何未知距离使该日完整性未知，但已知下限超标仍 fail。不要仅凭年龄推断步行上限。

additional_checks 表示上述字段未覆盖的硬要求（如禁烟房/电梯），由可信资料或上游工具评估 pass/fail/unknown，必须保留证据。不得遗漏不能表达的约束以得到通过结果。
