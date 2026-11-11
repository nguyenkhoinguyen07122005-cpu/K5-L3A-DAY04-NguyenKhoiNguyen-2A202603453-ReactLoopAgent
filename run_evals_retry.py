import json, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))
import providers


def post_json(url, headers, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json', **headers})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < 5:
                retry = exc.headers.get('Retry-After') if exc.headers else None
                wait = min(float(retry), 120) if retry and retry.isdigit() else min(15 * 2 ** attempt, 120)
                print(f'  HTTP {exc.code}, chờ {wait:.0f}s rồi thử lại ({attempt + 1}/5)...', flush=True)
                time.sleep(wait)
                continue
            raise RuntimeError(f'Provider trả HTTP {exc.code}; kiểm tra model, key và quota.') from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f'Không kết nối được provider: {exc.reason}') from exc


providers.post_json = post_json
import run_evals
sys.exit(run_evals.main())