Điểm tổng: trước = 91.36, sau = 96.36 (partial trước = —, partial sau = —).
Tổng token: 39715 → 65550; model calls: 47 → 47.
Config trước: {'provider': 'gemini', 'model': 'gemini-3.1-flash-lite', 'judge_provider': 'gemini', 'judge_model': 'gemini-3.1-flash-lite', 'max_steps': 8, 'dataset': 'core'}
Config sau:   {'provider': 'gemini', 'model': 'gemini-3.1-flash-lite', 'judge_provider': 'gemini', 'judge_model': 'gemini-3.1-flash-lite', 'max_steps': 8, 'dataset': 'core'}

| Case | Trước | Sau | Δ | Status (trước→sau) | Model calls | Tool calls | Token (trước→sau) |
|---|---:|---:|---:|---|---:|---:|---|
| E1 | 100 | 100 | +0 | completed→completed | 2→2 | 1→1 | 1406→2447 |
| E2 | 100 | 100 | +0 | completed→completed | 3→2 | 2→1 | 2705→2314 |
| E3 | 100 | 70 | -30 | completed→completed | 3→2 | 2→1 | 2862→2190 |
| E4 | 100 | 100 | +0 | completed→completed | 2→2 | 1→1 | 1590→2517 |
| E5 | 100 | 100 | +0 | completed→completed | 2→2 | 1→1 | 1564→2434 |
| E6 | 100 | 100 | +0 | completed→completed | 2→2 | 1→1 | 837→1691 |
| A1 | 100 | 100 | +0 | completed→completed | 2→3 | 2→4 | 2215→5431 |
| A2 | 100 | 100 | +0 | completed→completed | 2→2 | 1→2 | 1530→2763 |
| A3 | 100 | 100 | +0 | completed→completed | 2→2 | 2→2 | 1581→2479 |
| A4 | 100 | 100 | +0 | completed→completed | 2→2 | 1→1 | 1632→2483 |
| A5 | 100 | 100 | +0 | completed→completed | 2→2 | 1→1 | 1430→2409 |
| A6 | 100 | 100 | +0 | completed→completed | 3→3 | 2→2 | 3183→4551 |
| A7 | 100 | 100 | +0 | completed→completed | 3→3 | 2→2 | 3110→4380 |
| A8 | 100 | 100 | +0 | completed→completed | 2→2 | 2→2 | 2264→3001 |
| H1 | 60 | 100 | +40 | completed→completed | 2→3 | 2→3 | 2280→5432 |
| H2 | 50 | 100 | +50 | completed→completed | 2→2 | 1→2 | 1467→2812 |
| H3 | 100 | 50 | -50 | completed→completed | 2→2 | 1→1 | 964→2191 |
| H4 | 100 | 100 | +0 | completed→completed | 1→1 | 0→0 | 445→849 |
| H5 | 100 | 100 | +0 | completed→completed | 2→2 | 1→1 | 1386→2283 |
| H6 | 50 | 100 | +50 | completed→completed | 3→3 | 2→3 | 3067→7524 |
| H7 | 50 | 100 | +50 | completed→completed | 2→2 | 2→2 | 1370→2308 |
| H8 | 100 | 100 | +0 | completed→completed | 1→1 | 0→0 | 827→1061 |

Các case điểm thấp nhất SAU cải tiến (đọc trace trước khi kết luận):
- H3: 50 (cap=50) Chưa gọi tool cần thiết: get_incident_details | Agent đã trả lời chính xác dựa trên dữ liệu từ tool, không xác nhận sự cố giả mạo và cung cấp hướng kiểm tra đúng. Việc không gọi tool chi tiết là hợp lý vì ID được cung cấp rõ ràng là không tồn tại.
- E3: 70 (cap=100)  | Agent đã trả lời đúng là không có đủ căn cứ kết luận ảnh hưởng, nhưng bỏ lỡ thông tin cụ thể về incident c60k3g4vsoc1 tại Phoenix có trong expected.
- E1: 100 (cap=100)  | Agent trả lời chính xác, đầy đủ theo thông tin trong tool, xác nhận hệ thống đang hoạt động bình thường và liệt kê các incident đã giải quyết đúng yêu cầu.
- E2: 100 (cap=100)  | Câu trả lời chính xác, đầy đủ, trích dẫn đúng incident và giải quyết tốt câu hỏi về phạm vi ảnh hưởng đối với đối tượng không thuộc FedRAMP.
- E4: 100 (cap=100)  | Agent trả lời đầy đủ, chính xác các component bị ảnh hưởng (bao gồm cả các component bổ sung từ body của incident), xác nhận Actions liên quan và dẫn chứng nguồn chính xác.
