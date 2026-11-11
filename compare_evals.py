"""So sánh eval_before.json và eval_after.json, và kiểm tra rò rỉ bí mật trước khi nộp.

  python3 compare_evals.py eval_before.json eval_after.json            # in bảng so sánh
  python3 compare_evals.py eval_before.json eval_after.json --md so_sanh.md
  python3 compare_evals.py --check-secrets eval_before.json eval_after.json
Chỉ dùng dữ liệu có trong file eval; không tự suy ra điểm.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SECRET_PATTERNS = {
    'OpenAI/OpenRouter key': r'sk-[A-Za-z0-9_\-]{16,}',
    'Anthropic key': r'sk-ant-[A-Za-z0-9_\-]{16,}',
    'Google/Gemini key': r'AIza[0-9A-Za-z_\-]{20,}',
    'Bearer token': r'Bearer\s+[A-Za-z0-9_\-\.]{16,}',
    'Gán key trong text': r'(?i)(api[_-]?key|secret|token)["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}',
    'Email cá nhân': r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[a-z]{2,}',
}


def load(path):
    return json.loads(Path(path).read_text())


def usage_tokens(usage_list):
    total = 0
    for u in usage_list or []:
        if not isinstance(u, dict):
            continue
        if isinstance(u.get('total_tokens'), int):
            total += u['total_tokens']
        else:
            total += int(u.get('input_tokens') or 0) + int(u.get('output_tokens') or 0)
    return total


def case_stats(item):
    result, grade = item.get('result') or {}, item.get('grade') or {}
    trace = result.get('trace') or []
    return {'score': grade.get('score'), 'status': result.get('status'),
            'model_calls': sum(t.get('event') == 'model' for t in trace),
            'tool_calls': sum(t.get('event') == 'tool' for t in trace),
            'validation': sum(str(t.get('event', '')).startswith('validation') for t in trace),
            'tokens': usage_tokens(result.get('usage')),
            'cap': (grade.get('mechanical') or {}).get('score_cap'),
            'violations': (grade.get('mechanical') or {}).get('violations') or [],
            'reason': grade.get('reason', '')}


def fmt(x):
    return '—' if x is None else str(x)


def compare(before, after):
    b = {c['id']: case_stats(c) for c in before['cases']}
    a = {c['id']: case_stats(c) for c in after['cases']}
    lines = ['| Case | Trước | Sau | Δ | Status (trước→sau) | Model calls | Tool calls | Token (trước→sau) |',
             '|---|---:|---:|---:|---|---:|---:|---|']
    for cid in b:
        x, y = b[cid], a.get(cid)
        if not y:
            continue
        delta = None if x['score'] is None or y['score'] is None else y['score'] - x['score']
        lines.append(f"| {cid} | {fmt(x['score'])} | {fmt(y['score'])} | {fmt(delta) if delta is None else f'{delta:+}'} | "
                     f"{x['status']}→{y['status']} | {x['model_calls']}→{y['model_calls']} | "
                     f"{x['tool_calls']}→{y['tool_calls']} | {x['tokens']}→{y['tokens']} |")
    sb, sa = before['summary'], after['summary']
    head = [f"Điểm tổng: trước = {fmt(sb.get('score_0_100'))}, sau = {fmt(sa.get('score_0_100'))} "
            f"(partial trước = {fmt(sb.get('partial_mean_0_100'))}, partial sau = {fmt(sa.get('partial_mean_0_100'))}).",
            f"Tổng token: {sum(v['tokens'] for v in b.values())} → {sum(v['tokens'] for v in a.values())}; "
            f"model calls: {sum(v['model_calls'] for v in b.values())} → {sum(v['model_calls'] for v in a.values())}.",
            f"Config trước: {before.get('config')}", f"Config sau:   {after.get('config')}"]
    if before.get('config') != after.get('config'):
        head.append('CẢNH BÁO: config hai lần chạy khác nhau (model/judge/max_steps...). So sánh sẽ không công bằng.')
    low = sorted((c for c in a if a[c]['score'] is not None), key=lambda c: a[c]['score'])[:5]
    tail = ['', 'Các case điểm thấp nhất SAU cải tiến (đọc trace trước khi kết luận):']
    for cid in low:
        tail.append(f"- {cid}: {a[cid]['score']} (cap={a[cid]['cap']}) {'; '.join(a[cid]['violations'])} | {a[cid]['reason'][:300]}")
    return '\n'.join(head + [''] + lines + tail)


def check_secrets(paths):
    found = False
    for p in paths:
        text = Path(p).read_text()
        for label, pattern in SECRET_PATTERNS.items():
            for m in re.finditer(pattern, text):
                found = True
                print(f'[{p}] {label}: ...{text[max(0, m.start()-20):m.end()+10]!r}')
    print('Có thể có thông tin nhạy cảm — kiểm tra thủ công trước khi nộp.' if found else
          'Không phát hiện mẫu key/email phổ biến (vẫn nên đọc lướt file trước khi nộp).')
    return 1 if found else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('files', nargs='+')
    p.add_argument('--check-secrets', action='store_true')
    p.add_argument('--md', help='Ghi kết quả so sánh ra file markdown')
    args = p.parse_args()
    if args.check_secrets:
        return check_secrets(args.files)
    if len(args.files) != 2:
        p.error('Cần đúng 2 file: before after')
    out = compare(load(args.files[0]), load(args.files[1]))
    print(out)
    if args.md:
        Path(args.md).write_text(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
