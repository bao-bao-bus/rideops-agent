# RideOps MVP 后端演示步骤

这份步骤用于演示当前单编排器 MVP，不需要真实企业账号、支付、短信、PostgreSQL 或 Redis。建议在一个新的 PowerShell 窗口中启动独立的本地 SQLite 数据库，避免影响日常开发数据：

```powershell
cd D:\AAA\chuxing\backend
$env:RIDEOPS_DATABASE_PATH = "D:\AAA\chuxing\demo-data\rideops-demo.db"
uvicorn rideops.api.app:app --reload
```

另开一个 PowerShell 窗口，并运行以下命令。所有数据均为合成数据。

```powershell
$base = "http://127.0.0.1:8000"
Invoke-RestMethod "$base/health"
```

## 1. 出行前：查询、预约、取消

```powershell
$plan = Invoke-RestMethod "$base/api/pretrip/plan" -Method Post -ContentType "application/json" -Body '{"origin":"上海市静安区","destination":"上海市人民广场"}'
$plan.nearby_vehicles
$plan.estimate

$reservation = Invoke-RestMethod "$base/api/pretrip/reserve" -Method Post -ContentType "application/json" -Body '{"user_id":"usr_demo_001","vehicle_id":"veh_demo_002","idempotency_key":"demo:reserve-001"}'
$reservation

Invoke-RestMethod "$base/api/pretrip/reservations/$($reservation.reservation_id)/cancel" -Method Post -ContentType "application/json" -Body '{"user_id":"usr_demo_001","idempotency_key":"demo:cancel-001","approval_reference":"customer-confirmed-demo-001"}'
```

最后一个响应应显示 `status: cancelled` 和 `vehicle_status: available`。同一个取消请求可安全重复提交。

## 2. 事故中：检索、追问、审批、写入、回读

```powershell
$body = @{
  user_id = "usr_demo_001"
  message = "车辆发生碰撞，订单仍在计费，需要处理事故"
  idempotency_key = "demo:incident-001"
  order_id = "ord_demo_001"
  vehicle_id = "veh_demo_001"
  location = "上海市静安区"
  description = "车辆碰撞，用户手臂有轻微擦伤，车锁损坏"
} | ConvertTo-Json

$run = Invoke-RestMethod "$base/api/runs" -Method Post -ContentType "application/json" -Body $body
$run.workflow_status
$run.evidence
$run.planned_actions

$completed = Invoke-RestMethod "$base/api/runs/$($run.run_id)/resume" -Method Post -ContentType "application/json" -Body '{"approved":true}'
$completed.final_state
Invoke-RestMethod "$base/api/runs/$($run.run_id)/events"
```

创建 Run 时重复使用 `demo:incident-001` 会返回同一条 Run；审批前数据库不会变，批准后才会暂停计费、停用车辆、创建事故工单并回读状态。

## 3. 长租：方案与确认留资

```powershell
Invoke-RestMethod "$base/api/long-rental/plan" -Method Post -ContentType "application/json" -Body '{"city":"上海","duration_days":45,"daily_budget":40}'

Invoke-RestMethod "$base/api/long-rental/leads" -Method Post -ContentType "application/json" -Body '{"user_id":"usr_demo_001","listing_id":"rent_sh_e1","duration_days":45,"start_date":"2026-09-01","idempotency_key":"demo:long-rental-001","approval_reference":"customer-confirmed-demo-002"}'
```

这一步只生成 `pending_follow_up` 跟进线索，不会生成租赁订单或支付记录。

## 4. 查看最终合成业务状态

```powershell
Invoke-RestMethod "$base/api/demo-data"
```

响应包含订单、车辆、事故工单、预约和长租线索，可用于验证每个写操作确实落在 SQLite 中。
