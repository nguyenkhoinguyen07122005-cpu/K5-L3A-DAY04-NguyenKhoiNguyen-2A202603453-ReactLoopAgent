# Ghi chú phân tích · Day 04

Họ và tên: Nguyễn Khôi Nguyên
MSSV: 2A202603453

Cấu hình (giống nhau ở cả hai lần chạy): agent `gemini` / `gemini-3.1-flash-lite`; judge cùng provider và cùng model; `max_steps` 8; dataset `core` (22 case); snapshot cố định. Chạy bằng `run_evals_retry.py` (chỉ thêm chờ-thử-lại khi HTTP 429/503, không đổi cách chấm). `eval_before.json` chạy với `AGENT_BASELINE=1` (trace có `run_start: baseline`), `eval_after.json` chạy bản cải tiến (`run_start: improved`).

## 1. Case được chọn

- ID case: **H6**
- Câu trả lời của agent (trích từ `eval_before.json`):

```text
Dựa trên dữ liệu từ hệ thống trạng thái của GitHub, dưới đây là thông tin chi tiết về incident **h02n9572mx9y**:

### Nội dung và Nguyên nhân
Incident **h02n9572mx9y** liên quan đến sự cố của **GitHub Actions** và đã được hợp nhất vào incident tổng thể có mã **xr3myzj7ms51** ("Incident with Actions and Pages").

*   **Nguyên nhân:** Incident gộp **xr3myzj7ms51** đã chỉ rõ nguyên nhân. Sự cố được xác định là do "thay đổi cấu hình đối với một dịch vụ định tuyến sự kiện nội bộ" (*a configuration change to an internal event-routing service*). Thay đổi này phụ thuộc vào các cờ tính năng (feature flags) không được thiết lập đúng cách và dịch vụ đã không xử lý tình huống này một cách ổn định, dẫn đến việc tạm dừng cung cấp một số luồng sự kiện.
*   **Ảnh hưởng:** Sự cố gây ra độ trễ lên tới 25 phút cho các workflow của Actions, sụt giảm lưu lượng triển khai của Pages và phân phối webhook, đồng thời làm chậm quá trình quét mã (Code Scanning) và các phiên làm việc của Copilot.

### Giới hạn dữ liệu
*   **Tính chất:** Thông tin này dựa trên các bản ghi log trạng thái do GitHub cung cấp tại thời điểm sự cố. Nó mô tả các tác động quan sát được và nguyên nhân kỹ thuật cấp cao do chính GitHub công bố.
*   **Thiếu chi tiết chuyên sâu:** Dữ liệu này không cung cấp mã nguồn cụ thể, các tệp cấu hình chi tiết hoặc quy trình kiểm soát thay đổi nội bộ của GitHub.
*   **Thời điểm:** Dữ liệu mang tính chất snapshot (ghi lại tại thời điểm truy xuất), phản ánh những gì đã được ghi nhận và báo cáo công khai vào tháng 11 năm 2026.

### Nguồn trích dẫn
*   GitHub Status: [Incident h02n9572mx9y](https://www.githubstatus.com/incidents/h02n9572mx9y)
*   GitHub Status: [Incident xr3myzj7ms51 (Bản báo cáo gộp)](https://www.githubstatus.com/incidents/xr3myzj7ms51)
```

- Điểm ở lần chạy 1: **50** (bị cap bởi kiểm tra cơ học: "Chưa gọi tool cần thiết: get_status")

## 2. Bằng chứng trong trace

Các sự kiện `tool` của H6 trong `eval_before.json`:

```text
step 1  get_incident_details {"incident_id": "h02n9572mx9y", "provider": "github"}
step 2  get_incident_details {"provider": "github", "incident_id": "xr3myzj7ms51"}
(không có get_status)
grade.mechanical.violations: ["Chưa gọi tool cần thiết: get_status"]  -> score_cap 50
```

Cùng mẫu ở H2 (cũng 50): trace chỉ có `step 1  get_incident_details {"provider": "github", "incident_id": "t89g2q1800fr"}`.

Nguyên nhân có thể (giả thuyết, trace không cho biết suy nghĩ của model): câu hỏi đã chứa ID incident nên model đi thẳng vào `get_incident_details` và bỏ qua `get_status` để biết trạng thái hiện tại; prompt gốc chỉ nói "phân biệt incident hiện tại và lịch sử" mà không bảo phải gọi `get_status`. Ở H6, judge nhận xét nội dung trả lời đúng và có nêu giới hạn dữ liệu bị cắt, nên lỗi nằm ở quy trình (thiếu bước kiểm tra trạng thái hiện tại), không phải nội dung câu trả lời.

## 3. Thay đổi đã thực hiện

- Sửa gì, ở đâu (`agent.py`):
  1. Quy tắc bổ sung trong system prompt: khi câu hỏi liên quan trạng thái hiện tại thì luôn gọi `get_status` trước, kể cả khi đã có ID incident; incident đã resolved không chứng minh trạng thái hiện tại (nhắm vào H2, H6).
  2. Kiểm tra nguồn trước khi nhận final answer (Bài 4): mỗi provider có incident đã đọc thành công phải được dẫn URL của incident đó; nếu thiếu thì ghi `validation_missing_source` và yêu cầu sửa trong ngân sách `max_steps`.
  3. Chặn câu trả lời lặp lại chuỗi do chỉ dẫn giả trong tool result yêu cầu in; thêm quy tắc từ chối bịa trạng thái khi tool timeout (nhắm vào H7); giới hạn retry khi bị rate limit.
  4. Công tắc `AGENT_BASELINE=1` tắt phần cải tiến (2) và (3 prompt) để chạy `eval_before` bằng cùng một file; sự kiện `run_start` ghi chế độ vào trace.
- Vì sao chọn thay đổi này: trace H2/H6 cho thấy lỗi lặp lại ở bước chọn tool, và `get_status` là cách duy nhất để biết trạng thái hiện tại; kiểm tra nguồn là yêu cầu của Bài 4 và có test riêng (`tests/test_validation.py`). Test offline: 54 test chính và 3 test bonus pass.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng | 91.36 | 96.36 |
| Điểm case đã chọn (H6) | 50 | 100 |
| Số model calls | 47 | 47 |
| Token, chi phí nếu có | 39,715 token (không có chi phí tiền) | 65,550 token (không có chi phí tiền) |

- Lỗi đã giải quyết: H1 60→100, H2 50→100, H6 50→100, H7 50→100. Trace H6 sau cải tiến: step 1 gọi `get_status` (GitHub Actions) cùng `get_incident_details h02n9572mx9y`, step 2 đọc `xr3myzj7ms51`, không còn bị cap.
- Lỗi còn lại hoặc mới xuất hiện:
  - **H3 100→50:** trước gọi `get_incident_details` với đúng ID người dùng nêu (`totally-not-a-real-id`); sau chỉ gọi `get_status` và không tra ID đó, nên bị cap vì thiếu `get_incident_details`. Nhiều khả năng quy tắc "gọi `get_status` trước" đã thế chỗ việc tra ID.
  - **E3 100→70:** trước gọi `get_status` rồi `get_incident_details c60k3g4vsoc1`; sau chỉ gọi `get_status` có lọc `component=Cloudflare Spectrum` rồi dừng; judge nói bỏ lỡ chi tiết incident `c60k3g4vsoc1` ở Phoenix. Tôi chưa xem nội dung kết quả `get_status` đó nên nguyên nhân vẫn là giả thuyết.
  - Token tăng 65% trong khi số model call không đổi, phù hợp với system prompt dài hơn ở mỗi lần gọi.

## 5. Giới hạn

- Mỗi phiên bản chỉ chạy một lần để nộp. Một lượt baseline khác (chạy trước đó, bằng bản `agent.py` chưa có `run_start`) cho 90.0, so với 91.36, nên dao động giữa các lần chạy khoảng 1–2 điểm; mức tăng +5.0 lớn hơn dao động đó nhưng không phải bằng chứng thống kê.
- Judge dùng cùng model nhỏ với agent (`gemini-3.1-flash-lite`) nên có thể thiên lệch; điểm judge chỉ là ước lượng.
- Quy tắc `get_status` được thêm sau khi đọc lỗi trên chính 22 case này, nên có nguy cơ khớp riêng với bộ eval; hai case giảm điểm (E3, H3) cho thấy nó cũng đổi hành vi ở những chỗ không nhắm tới.
- Một số điểm bị cap bởi kiểm tra bằng code trong khi judge nhận xét nội dung đúng (H2, H3, H6), nên điểm eval không trùng hoàn toàn với chất lượng câu trả lời.
- Snapshot cố định không phản ánh trạng thái hiện tại; tìm không thấy chỉ có nghĩa là không thấy trong 50 incident gần nhất mỗi provider. Kiểm tra nguồn chỉ xác nhận có URL, không kiểm tra từng claim.
