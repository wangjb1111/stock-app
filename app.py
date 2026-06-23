# -*- coding: utf-8 -*-
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import datetime
import urllib.request

PORT = int(__import__("os").environ.get("PORT", 8000))

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
const INDICES=[{n:'上证指数',c:'000001.SS'},{n:'深证成指',c:'399001.SZ'},{n:'创业板指',c:'399006.SZ'},{n:'沪深300',c:'000300.SS'},{n:'中证1000',c:'000852.SS'},{n:'中证500',c:'000905.SS'},{n:'上证50',c:'000016.SS'},{n:'科创50',c:'000688.SS'}];
function ema(a,n){if(a.length<n)return null;let k=2/(n+1),e=a.slice(0,n).reduce((x,y)=>x+y,0)/n;for(let i=n;i<a.length;i++)e=a[i]*k+e*(1-k);return e}
function ml(r){if(r.length<34)return null;let cp=r.map(x=>x.c),hp=r.map(x=>x.h),lp=r.map(x=>x.l),s=[];for(let i=0;i<r.length;i++){let st=Math.max(0,i-33),h34=Math.max.apply(null,hp.slice(st,i+1)),l34=Math.min.apply(null,lp.slice(st,i+1));s.push(h34===l34?0:-100*(h34-cp[i])/(h34-l34))}let e=ema(s,4);return e!==null?Math.round((e+100)*100)/100:null}
function an(r,n){if(!r||r.length<30)return{n,er:'数据不足'};let l=r.slice(-30),hm=Math.max.apply(null,l.map(x=>x.h)),lm=Math.min.apply(null,l.map(x=>x.l)),c=r[r.length-1].c;return{n,current:Math.round(c*100)/100,highMax:Math.round(hm*100)/100,highDate:l.reduce((p,x)=>x.h>p.h?x:p).d,lowMin:Math.round(lm*100)/100,lowDate:l.reduce((p,x)=>x.l<p.l?x:p).d,drop:Math.round((lm-hm)/hm*10000)/100,rise:Math.round((c-lm)/lm*10000)/100,ml:ml(r)}}
async function load(){var b=document.querySelector('button'),s=document.getElementById('st'),tb=document.getElementById('tb');b.disabled=true;b.textContent='加载中';s.textContent='获取中...';var rs=[],er=[];await Promise.all(INDICES.map((idx,i)=>new Promise(rv=>setTimeout(async()=>{try{const r=await fetch('/api/kline?code='+encodeURIComponent(idx.c));const t=await r.text();if(!t||t.trim()===''){er.push(idx.n+':空');rv()}const d=JSON.parse(t);if(d&&d.data&&d.data.length>0){const rows=d.data.map(x=>({d:x.date,c:x.close,h:x.high,l:x.low}));rs.push(an(rows,idx.n))}else{er.push(idx.n+':无')}}catch(e){er.push(idx.n+':'+e.message)}s.textContent=(rs.length+er.length)+'/'+INDICES.length;rv()},i*2000))));if(rs.length===0){tb.innerHTML='<tr><td colspan="9" class="load" style="color:#e74c3c">失败:'+er.join(';')+'</td></tr>'}else{tb.innerHTML=rs.map(x=>{var mv=x.ml!==null?x.ml.toFixed(2):'-',mc=x.ml!==null?(x.ml>70?'green':x.ml<30?'red':'orange'):'';return'<tr><td class="name">'+x.n+'</td><td>'+x.current.toFixed(2)+'</td><td>'+x.highMax.toFixed(2)+'</td><td>'+x.highDate+'</td><td>'+x.lowMin.toFixed(2)+'</td><td>'+x.lowDate+'</td><td class="'+(x.drop<0?'red':'green')+'">'+x.drop.toFixed(2)+'</td><td class="'+(x.rise>=0?'green':'red')+'">'+x.rise.toFixed(2)+'</td><td class="'+mc+'">'+mv+'</td></tr>'}).join('')}b.disabled=false;b.textContent='刷新';s.textContent='完成'}
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
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}?interval=1d&range=3mo"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        result = data.get('chart', {}).get('result')
        if not result or not result[0]: return None
        ts = result[0]['timestamp']
        q = result[0]['indicators']['quote'][0]
        rows = []
        for i, t in enumerate(ts):
            rows.append({'date': datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d'),
                         'close': round(float(q['close'][i]), 2),
                         'high': round(float(q['high'][i]), 2),
                         'low': round(float(q['low'][i]), 2)})
        rows = [r for r in rows if r['close'] and r['close'] > 0]
        _cache[code] = rows
        _cache_time = now
        return rows
    except Exception as e:
        print(f"Error {code}: {e}", flush=True)
        return None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        elif self.path.startswith("/api/kline"):
            code = self.path.split("code=")[1].split("&")[0] if "code=" in self.path else ""
            rows = fetch_yahoo(code) if code else None
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            resp = {"code": 0 if rows else 1, "data": rows, "error": None if rows else "获取失败"}
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif self.path == "/api/test":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        elif self.path.startswith("/api/debug"):
            # 调试端点 - 测试Yahoo API
            code = self.path.split("code=")[1].split("&")[0] if "code=" in self.path else "000001.SS"
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}?interval=1d&range=3mo"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    raw = resp.read().decode('utf-8')
                result = json.loads(raw).get('chart', {}).get('result')
                if result and result[0]:
                    ts = result[0].get('timestamp', [])
                    debug = {"status": "ok", "code": code, "records": len(ts)}
                else:
                    debug = {"status": "no_data", "code": code}
            except Exception as e:
                debug = {"status": "error", "code": code, "msg": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(debug).encode("utf-8"))
        else:
            self.send_error(404)
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    print(f"Start on {PORT}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
