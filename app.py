# -*- coding: utf-8 -*-
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import datetime
import urllib.request

PORT = int(__import__("os").environ.get("PORT", 8000))

INDICES = [
    ("上证指数", "000001.SS"),
    ("深证成指", "399001.SZ"),
    ("创业板指", "399006.SZ"),
    ("沪深300", "000300.SS"),
    ("中证1000", "000852.SS"),
    ("中证500", "000905.SS"),
    ("上证50", "000016.SS"),
    ("科创50", "000688.SS"),
]

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>各指数涨跌分析</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f5f5;min-height:100vh}
.header{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;padding:14px;text-align:center}
.header h1{font-size:17px;font-weight:600}
.bar{display:flex;align-items:center;padding:10px 12px;background:#fff;border-bottom:1px solid #eee}
.bar span{flex:1;font-size:12px;color:#666}
.bar button{padding:6px 16px;background:#2a5298;color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer}
.wrap{padding:10px;overflow-x:auto}
table{width:100%;min-width:600px;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden}
th{background:#f8f9fa;font-size:11px;font-weight:600;color:#555;padding:10px 6px;text-align:center}
td{font-size:11px;padding:8px 6px;text-align:center;border-bottom:1px solid #f0f0f0}
.name{font-weight:500;color:#333;text-align:left!important;padding-left:12px!important}
.red{color:#e74c3c}.green{color:#27ae60}.orange{color:#f39c12}
.load{color:#999;font-size:13px;text-align:center;padding:40px}
</style>
</head>
<body>
<div class="header"><h1>各指数近30日涨跌分析</h1></div>
<div class="bar"><span id="st">准备就绪</span><button onclick="load()">刷新</button></div>
<div class="wrap">
<table><thead><tr>
<th>指数</th><th>当前点位</th><th>30日最高</th><th>最高日期</th>
<th>30日最低</th><th>最低日期</th><th>最低相对最高跌幅%</th><th>当前相对最低涨幅%</th>
<th>趋势顶底中期线</th>
</tr></thead><tbody id="tb"><tr><td colspan="9" class="load">加载中...</td></tr></tbody></table>
</div>
<script>
var HTML_ENCODED = "__PLACEHOLDER__";

function render(data) {
  var tb = document.getElementById('tb');
  var st = document.getElementById('st');
  var btn = document.querySelector('button');
  
  if (!data || !data.results || data.results.length === 0) {
    tb.innerHTML = '<tr><td colspan="9" class="load" style="color:#e74c3c">失败: ' + (data && data.errors ? data.errors.join('; ') : '未知') + '</td></tr>';
  } else {
    var html = '';
    var items = data.results;
    for (var i = 0; i < items.length; i++) {
      var x = items[i];
      var mv = x.ml !== null && x.ml !== undefined ? x.ml.toFixed(2) : '-';
      var mc = x.ml !== null && x.ml !== undefined ? (x.ml > 70 ? 'green' : x.ml < 30 ? 'red' : 'orange') : '';
      html += '<tr><td class="name">' + x.n + '</td>' +
        '<td>' + x.current.toFixed(2) + '</td>' +
        '<td>' + x.highMax.toFixed(2) + '</td>' +
        '<td>' + x.highDate + '</td>' +
        '<td>' + x.lowMin.toFixed(2) + '</td>' +
        '<td>' + x.lowDate + '</td>' +
        '<td class="' + (x.drop < 0 ? 'red' : 'green') + '">' + x.drop.toFixed(2) + '</td>' +
        '<td class="' + (x.rise >= 0 ? 'green' : 'red') + '">' + x.rise.toFixed(2) + '</td>' +
        '<td class="' + mc + '">' + mv + '</td></tr>';
    }
    tb.innerHTML = html;
  }
  
  btn.disabled = false;
  btn.textContent = '刷新';
  st.textContent = '完成 (' + new Date().toLocaleString('zh-CN') + ')';
}

async function load() {
  var btn = document.querySelector('button');
  var st = document.getElementById('st');
  var tb = document.getElementById('tb');
  
  btn.disabled = true;
  btn.textContent = '加载中';
  st.textContent = '获取中...';
  tb.innerHTML = '<tr><td colspan="9" class="load">加载中...</td></tr>';
  
  try {
    var resp = await fetch('/api/all');
    var data = await resp.json();
    render(data);
  } catch (e) {
    tb.innerHTML = '<tr><td colspan="9" class="load" style="color:#e74c3c">请求失败: ' + e.message + '</td></tr>';
    btn.disabled = false;
    btn.textContent = '刷新';
    st.textContent = '失败';
  }
}

load();
</script>
</body>
</html>"""

def ema(v, n):
    if len(v) < n: return None
    k = 2.0 / (n + 1)
    e = sum(v[:n]) / n
    for val in v[n:]: e = val * k + e * (1 - k)
    return e

def medium_line(closes, highs, lows):
    n = len(closes)
    if n < 34: return None
    s = []
    for i in range(n):
        st = max(0, i - 33)
        h34 = max(highs[st:i + 1])
        l34 = min(lows[st:i + 1])
        c = closes[i]
        s.append(0 if h34 == l34 else -100 * (h34 - c) / (h34 - l34))
    e = ema(s, 4)
    return round(e + 100, 2) if e is not None else None

_cache = {}
_cache_time = 0

def fetch_yahoo(code):
    global _cache, _cache_time
    now = time.time()
    if code in _cache and (now - _cache_time) < 300:
        return _cache[code]
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + code + "?interval=1d&range=3mo"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        result = data.get('chart', {}).get('result')
        if not result or not result[0]:
            print("No result for " + code, flush=True)
            return None
        ts = result[0]['timestamp']
        q = result[0]['indicators']['quote'][0]
        rows = []
        for i, t in enumerate(ts):
            try:
                close = float(q['close'][i])
                high = float(q['high'][i])
                low = float(q['low'][i])
                if close > 0 and high > 0 and low > 0:
                    rows.append({
                        'date': datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d'),
                        'close': round(close, 2),
                        'high': round(high, 2),
                        'low': round(low, 2)
                    })
            except (TypeError, ValueError):
                continue
        print(code + ": " + str(len(rows)) + " rows", flush=True)
        _cache[code] = rows
        _cache_time = now
        return rows
    except Exception as e:
        print("Error " + code + ": " + str(e), flush=True)
        return None

def analyze(rows, name):
    if not rows or len(rows) < 30:
        return None
    last30 = rows[-30:]
    hm = max(r['high'] for r in last30)
    lm = min(r['low'] for r in last30)
    c = rows[-1]['close']
    highDate = max(last30, key=lambda r: r['high'])['date']
    lowDate = min(last30, key=lambda r: r['low'])['date']
    closes = [r['close'] for r in rows]
    highs = [r['high'] for r in rows]
    lows = [r['low'] for r in rows]
    ml_val = medium_line(closes, highs, lows)
    return {
        'n': name,
        'current': round(c, 2),
        'highMax': round(hm, 2),
        'highDate': highDate,
        'lowMin': round(lm, 2),
        'lowDate': lowDate,
        'drop': round((lm - hm) / hm * 100, 2),
        'rise': round((c - lm) / lm * 100, 2),
        'ml': ml_val
    }

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        elif self.path == "/api/all":
            results = []
            errors = []
            for name, code in INDICES:
                try:
                    rows = fetch_yahoo(code)
                    if rows:
                        a = analyze(rows, name)
                        if a:
                            results.append(a)
                        else:
                            errors.append(name + ': 分析失败')
                    else:
                        errors.append(name + ': 无数据')
                except Exception as e:
                    errors.append(name + ': ' + str(e))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            resp = {"results": results, "errors": errors}
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/test":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        else:
            self.send_error(404)
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    print("Start on " + str(PORT), flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
