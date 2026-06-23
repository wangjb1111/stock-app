# -*- coding: utf-8 -*-
"""
Render.com 部署 - 使用 Stooq 数据源 (全球可访问)
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import urllib.request

PORT = int(__import__("os").environ.get("PORT", 8000))

INDICES = [
    ("上证指数", "sh000001"),
    ("深证成指", "sz399001"),
    ("创业板指", "sz399006"),
    ("沪深300", "sh000300"),
    ("中证1000", "sh000852"),
    ("中证500", "sh000905"),
    ("上证50", "sh000016"),
    ("科创50", "sh000688"),
]

def ema(values, period):
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    ema_val = sum(values[:period]) / period
    for v in values[period:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val

def medium_line(closes, highs, lows):
    n = len(closes)
    if n < 34:
        return None
    series = []
    for i in range(n):
        start = max(0, i - 33)
        h34 = max(highs[start:i + 1])
        l34 = min(lows[start:i + 1])
        c = closes[i]
        series.append(0 if h34 == l34 else -100 * (h34 - c) / (h34 - l34))
    e = ema(series, 4)
    return round(e + 100, 2) if e is not None else None

_cache = {}
_cache_time = 0
CACHE_DURATION = 300

def fetch_stooq(code):
    """使用 Stooq 获取数据"""
    global _cache, _cache_time
    
    now = time.time()
    if code in _cache and (now - _cache_time) < CACHE_DURATION:
        return _cache[code]
    
    try:
        # Stooq API - 简洁的数据格式
        url = f"https://stooq.com/q/l/?s={code}&i=d&l=120"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        # 解析 HTML 表格
        rows = []
        lines = html.strip().split('\n')
        for line in lines[1:]:  # 跳过标题行
            parts = line.split(',')
            if len(parts) >= 6:
                try:
                    date = parts[0].strip()
                    open_price = float(parts[1])
                    high = float(parts[2])
                    low = float(parts[3])
                    close = float(parts[4])
                    volume = float(parts[5]) if len(parts) > 5 else 0
                    if close > 0:
                        rows.append({
                            "date": date,
                            "close": close,
                            "high": high,
                            "low": low,
                        })
                except (ValueError, IndexError):
                    continue
        
        rows.reverse()  # 从旧到新
        _cache[code] = rows
        _cache_time = now
        return rows
        
    except Exception as e:
        print(f"Error fetching {code}: {e}", flush=True)
        _cache[code] = None
        _cache_time = now
        return None

def analyze(rows, name):
    if not rows or len(rows) < 30:
        return {"name": name, "error": "数据不足"}
    last30 = rows[-30:]
    high_max = max(r["high"] for r in last30)
    low_min = min(r["low"] for r in last30)
    current = rows[-1]["close"]
    high_date = max(last30, key=lambda r: r["high"])["date"]
    low_date = min(last30, key=lambda r: r["low"])["date"]
    drop_from_high = round((low_min - high_max) / high_max * 100, 2)
    rise_from_low = round((current - low_min) / low_min * 100, 2)
    closes = [r["close"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    ml_val = medium_line(closes, highs, lows)
    return {
        "name": name,
        "current": round(current, 2),
        "high_max": round(high_max, 2),
        "high_date": high_date,
        "low_min": round(low_min, 2),
        "low_date": low_date,
        "drop_from_high": drop_from_high,
        "rise_from_low": rise_from_low,
        "medium_line": ml_val,
    }

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>各指数涨跌分析</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f5f5;min-height:100vh}
.header{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;padding:14px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.header h1{font-size:17px;font-weight:600;margin-bottom:4px}
.header .sub{font-size:11px;opacity:.85}
.bar{display:flex;align-items:center;padding:10px 12px;background:#fff;border-bottom:1px solid #eee;gap:10px}
.bar .s{flex:1;font-size:12px;color:#666;line-height:1.4}
.bar button{padding:6px 16px;background:#2a5298;color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer;font-weight:500}
.bar button:active{opacity:.7}
.bar button:disabled{background:#999}
.wrap{overflow-x:auto;padding:10px;-webkit-overflow-scrolling:touch}
table{width:100%;min-width:600px;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}
th{background:#f8f9fa;font-size:11px;font-weight:600;color:#555;padding:10px 6px;text-align:center;white-space:nowrap;border-bottom:2px solid #e0e0e0}
td{font-size:11px;padding:8px 6px;text-align:center;border-bottom:1px solid #f0f0f0}
tr:nth-child(odd) td{background:#fafafa}
.name{font-weight:500;color:#333;text-align:left!important;padding-left:12px!important}
.red{color:#e74c3c;font-weight:500}
.green{color:#27ae60;font-weight:500}
.orange{color:#f39c12;font-weight:500}
.load{color:#999;font-size:13px;text-align:center;padding:40px 20px}
.err-box{background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:10px 12px;margin:10px;font-size:11px;color:#856404}
.footer{text-align:center;padding:20px 10px 40px;font-size:10px;color:#999;line-height:1.8}
</style>
</head>
<body>
<div class="header">
<h1>各指数近30日涨跌分析</h1>
<div class="sub" id="ut">数据更新时间: --</div>
</div>
<div class="bar">
<span class="s" id="st">准备就绪</span>
<button id="rb" onclick="load()">刷新</button>
</div>
<div class="wrap">
<table>
<thead>
<tr>
<th>指数</th><th>当前点位</th><th>30日最高</th><th>最高日期</th>
<th>30日最低</th><th>最低日期</th>
<th>最低相对最高跌幅%</th><th>当前相对最低涨幅%</th>
<th>趋势顶底中期线</th>
</tr>
</thead>
<tbody id="tb"><tr><td colspan="9" class="load">加载中...</td></tr></tbody>
</table>
</div>
<div id="eb" style="display:none"></div>
<div class="footer">数据来源: Stooq<br>建议横屏查看 &middot; 数据仅供参考</div>
<script>
const INDICES=[{name:'上证指数',code:'sh000001'},{name:'深证成指',code:'sz399001'},{name:'创业板指',code:'sz399006'},{name:'沪深300',code:'sh000300'},{name:'中证1000',code:'sh000852'},{name:'中证500',code:'sh000905'},{name:'上证50',code:'sh000016'},{name:'科创50',code:'sh000688'}];
function ema(a,n){if(a.length<n)return null;let k=2/(n+1),e=a.slice(0,n).reduce((x,y)=>x+y,0)/n;for(let i=n;i<a.length;i++)e=a[i]*k+e*(1-k);return e}
function ml(r){if(r.length<34)return null;let cp=r.map(x=>x.c),hp=r.map(x=>x.h),lp=r.map(x=>x.l),s=[];for(let i=0;i<r.length;i++){let st=Math.max(0,i-33),h34=Math.max.apply(null,hp.slice(st,i+1)),l34=Math.min.apply(null,lp.slice(st,i+1));s.push(h34===l34?0:-100*(h34-cp[i])/(h34-l34))}let e=ema(s,4);return e!==null?Math.round((e+100)*100)/100:null}
function an(r,n){if(!r||r.length<30)return{name:n,error:'数据不足'};let l=r.slice(-30),hm=Math.max.apply(null,l.map(x=>x.h)),lm=Math.min.apply(null,l.map(x=>x.l)),c=r[r.length-1].c;return{name:n,current:Math.round(c*100)/100,highMax:Math.round(hm*100)/100,highDate:l.reduce((p,x)=>x.h>p.h?x:p).d,lowMin:Math.round(lm*100)/100,lowDate:l.reduce((p,x)=>x.l<p.l?x:p).d,drop:Math.round((lm-hm)/hm*10000)/100,rise:Math.round((c-lm)/lm*10000)/100,ml:ml(r)}}
async function load(){var b=document.getElementById('rb'),s=document.getElementById('st'),tb=document.getElementById('tb'),eb=document.getElementById('eb');b.disabled=true;b.textContent='加载中';s.textContent='正在获取数据...';eb.style.display='none';var rs=[],er=[];await Promise.all(INDICES.map((idx,i)=>new Promise(rv=>setTimeout(async()=>{try{const res=await fetch('/api/kline?code='+encodeURIComponent(idx.code));const text=await res.text();if(!text||text.trim()===''){er.push(idx.name+':空响应');rv();return}const d=JSON.parse(text);if(d&&d.data&&d.data.length>0){const rows=d.data.map(x=>({d:x.date,c:x.close,h:x.high,l:x.low}));rs.push(an(rows,idx.name))}else{er.push(idx.name+':'+(d.error||'无数据'))}}catch(e){er.push(idx.name+':'+e.message)}s.textContent='已加载'+(rs.length+er.length)+'/'+INDICES.length+'个';rv()},i*1000))));if(rs.length===0){tb.innerHTML='<tr><td colspan="9" class="load" style="color:#e74c3c">全部失败:'+er.join(';')+'</td></tr>'}else{tb.innerHTML=rs.map(x=>{var mv=x.ml!==null?x.ml.toFixed(2):'-',mc=x.ml!==null?(x.ml>70?'green':x.ml<30?'red':'orange'):'';return'<tr><td class="name">'+x.name+'</td><td>'+x.current.toFixed(2)+'</td><td>'+x.highMax.toFixed(2)+'</td><td>'+x.highDate+'</td><td>'+x.lowMin.toFixed(2)+'</td><td>'+x.lowDate+'</td><td class="'+(x.drop<0?'red':'green')+'">'+x.drop.toFixed(2)+'</td><td class="'+(x.rise>=0?'green':'red')+'">'+x.rise.toFixed(2)+'</td><td class="'+mc+'">'+mv+'</td></tr>'}).join('');document.getElementById('ut').textContent='更新时间:'+new Date().toLocaleString('zh-CN')}if(er.length>0){eb.style.display='block';eb.className='err-box';eb.textContent='部分失败:'+er.join(';')}b.disabled=false;b.textContent='刷新';s.textContent='加载完成'}
load();
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        elif self.path.startswith("/api/kline"):
            qs = __import__("urllib.parse").parse_qs(__import__("urllib.parse").urlparse(self.path).query)
            code = qs.get("code", [""])[0]
            rows = fetch_stooq(code) if code else None
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            response = {"code": 0 if rows else 1, "data": rows, "error": None if rows else "获取失败"}
            self.wfile.write(json.dumps(response).encode("utf-8"))
        elif self.path == "/api/test":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "time": time.time()}).encode("utf-8"))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"Listening on {PORT}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
