# 平台选择与访问策略

候选库基于 2026-10-19 的公开入口调研；不是实时接口可用性承诺，也不是平台质量排名。使用时核实入口和页面内容，不假定各平台存在官方 MCP。

| 类型 | 平台 | 官方入口 |
|---|---|---|
| 国内 | 携程 | https://hotels.ctrip.com/hotels |
| 国内 | 去哪儿 | https://www.qunar.com/ |
| 国内 | 飞猪 | https://www.fliggy.com/ |
| 国内 | 同程 | https://www.ly.com/ |
| 国内 | 美团酒店 | https://i.meituan.com/hotel/ |
| 国际 | Booking.com | https://www.booking.com/ |
| 国际 | Agoda | https://www.agoda.com/zh-cn/ |
| 国际 | Trip.com | https://www.trip.com/hotels/ |
| 国际 | Expedia | https://www.expedia.com/Hotels |
| 国际 | Hotels.com | https://www.hotels.com/ |
| 比价线索 | trivago | https://www.trivago.com/ |
| 民宿 | 途家 | https://www.tujia.com/ |
| 民宿 | 美团民宿 | https://oia-zhenguo.meituan.com/ |
| 品牌直订 | 华住会 | https://m.huazhu.com/hotel |
| 品牌直订 | 希尔顿 | https://www.hilton.com/zh-hans/ |

其他酒店品牌官网由实际候选酒店确定，通过官方页面核实域名，不拼造预订链接。

## 路由

- 国内酒店：按用户偏好、页面可访问性从国内来源选约三个；海外从国际来源选约三个。
- 用户指定来源优先；民宿仅在接受该类型时加入。
- 集团关联的平台不视为相互独立的证据，页面条款和实际销售方仍逐项比较。
- 比价平台是报价入口：最终价格、销售方、房型和退改以可读取的实际销售页面为据。
- 预售券、套餐先核实有效期、适用日期、加价日、预约确认与退款条件，不能当作目标日期已确认的库存。

## 访问记录

每个来源记录 `access_status`：`detail_read`（详情已读）、`snippet_only`（仅摘要）、`blocked`（访问受限）、`failed`（工具失败）。另记录 `url`、`queried_at`、`limitations`。

没有浏览工具：只输出区域研究或搜索发现的候选与入口，并返回相应的 `partial`；不得编造页面详情。所有来源不可用且无足够资料回答时返回 `failed`。

不得自动创建账号、接受会员付费、提交订单或获取用户登录凭据。用户自供资料标记 `user_provided`，不会因此自动升级为已在线核实。
