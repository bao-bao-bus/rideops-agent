---
name: accident-handling
description: 处理共享出行中的车辆事故、故障、损坏和人身安全事件
---

# accident-handling

## applicable_scenarios

用户报告车辆事故、碰撞、损坏、故障或人身安全风险时使用。

## required_information

- 订单号或车辆编号
- 事件发生地点和时间
- 事件描述与是否有人受伤

## workflow

1. 收集关键信息并确认安全风险。
2. 查询订单、车辆和历史工单状态。
3. 检索适用政策并生成处理计划。
4. 涉及写入业务数据的动作必须先请求人工审批。

## allowed_tools

当前阶段仅定义工具边界；MCP 工具将在后续阶段实现。

## approval_policy

暂停计费、下线车辆、创建工单等写操作必须经过人工审批。

## failure_handling

信息不足时向用户追问；无法确认政策证据时不得给出确定性承诺。

## references

按需读取 `references/policy.md`。

## output_template

说明已确认信息、待补充信息、建议动作和审批状态。
