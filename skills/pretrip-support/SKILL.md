---
name: pretrip-support
description: 回答共享出行用户的路线、费用、附近车辆和城市规则问题
---

# pretrip-support

## applicable_scenarios

用户询问怎么去、附近是否有车、预计费用、骑行时间、停车规则或当地出行政策时使用。

## required_information

- 路线问题：出发地和目的地
- 附近车辆：当前位置或可识别的地点
- 当地政策：城市或地区（如果问题中未明确）

## workflow

1. 识别用户要查询的是路线、费用、车辆还是政策。
2. 路线和地点问题调用地图能力；费用使用 RideOps 自己的计价规则。
3. 政策问题只返回有来源的 RAG 证据，并标注适用城市和生效条件。
4. 信息不足时先追问，不猜测当前位置、价格或政策。

## allowed_tools

- `estimate_route`
- `estimate_fare`
- `search_nearby_vehicles`
- `search_local_policy`

## approval_policy

只读查询不需要人工审批。预约车辆或改变订单状态时，必须进入独立的确认和幂等写入流程。

## failure_handling

地图服务不可用时明确标注使用了合成路线；知识库没有足够证据时拒答，不把搜索结果当作确定政策。

## output_template

说明查询类型、已确认条件、结果、数据来源和仍然需要用户补充的信息。
