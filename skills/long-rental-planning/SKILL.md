---
name: long-rental-planning
description: 为共享出行用户规划长租、月租和续租方案
---

# long-rental-planning

## applicable_scenarios

用户咨询长租、月租、长期租赁、租期或续租方案时使用。

## required_information

- 期望租期
- 用车城市和开始时间
- 车型偏好与预算

## workflow

1. 收集租期、地点和车型需求。
2. 查询合成车辆库存与可用性。
3. 生成候选方案并说明待确认条件。
4. 创建线索等写操作必须先请求人工审批。

## allowed_tools

当前阶段仅定义工具边界；MCP 工具将在后续阶段实现。

## approval_policy

创建租赁线索或改变业务状态前必须经过人工审批。

## failure_handling

库存不足时返回替代条件；缺少关键需求时先追问，不虚构价格或库存。

## references

按需读取 `references/policy.md`。

## output_template

输出需求摘要、候选方案、限制条件和下一步确认事项。
