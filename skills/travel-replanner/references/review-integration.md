# 校验器集成与维护

`scripts/_review_engine.py` 是项目现有 `skills/travel-plan-review/scripts/validate_itinerary.py` 的原样快照，取自已提交的版本 d7ea9e8。

来源：https://github.com/zhouzhiguang2007-wq/huawei-ict-chuangxinsai/tree/d7ea9e8/skills/travel-plan-review

随包复制是为了让本Skill独立导入后能执行，不要求用户先安装另一技能。重规划器通过其schema/review等函数进行校验，不重复开发时间和预算算法。

共享引擎检查原方案与候选、硬约束、完整费用和历史保护；guard额外处理当前时刻、出发锚点、事件生效范围、已确认约束更新与历史交通保护。模型负责生成候选及解释，两层代码均不会自动搜索或生成路线。

模型不能将已知不可行基线悄悄修改到通过。已确认约束变化由requirement_updates应用并记录原值与新值；未确认变更必须保留原要求。

维护：更新travel-plan-review后，审查契约差异，替换快照，运行共享引擎原有测试和本包测试，再更新来源版本。不得通过导入任意外部路径来加载未经核实的脚本。

当前限制：共享引擎仍会检查全程历史数据，历史数据已有矛盾或费用不足可能使草案blocked/partial。遇到此情况应由上游核实实际记录，不删改历史以求通过。强制取消、退款净额、交通实时误差和来源真实性需要额外业务资料支持。
