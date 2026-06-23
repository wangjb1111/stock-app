# -*- coding: utf-8 -*-
"""Render.com 部署入口"""
import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import re
import time
import socket

PORT = int(__import__("os").environ.get("PORT", 8000))

INDICES = [
    ("上证指数", "1.000001"),
    ("深证成指", "0.399001"),
    ("创业板指", "0.399006"),
    ("沪深300", "1.000300"),
    ("中证1000", "1.000852"),
    ("中证500", "1.000905"),
    ("上证50", "1.000016"),
    ("科创50", "1.000688"),
]

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
<div class="header"><h1>各指数近30日涨跌分析</h1><div class="sub" id="ut">数据更新时间: --</div></div>
<div class="bar"><span class="s" id="st">准备就绪</span><button id="rb" onclick="load()">刷新</button></div>
<div class="wrap"><table>
<thead><tr>
<th>指数</th><th>当前点位</th><th>30日最高</th><th>最高日期</th><th>30日最低</th><th>最低日期</th>
<th>最低相对最高跌幅%</th><th>当前相对最低涨幅%</th><th>趋势顶底中期线</th>
</tr></thead>
<tbody id="tb"><tr><td colspan="9" class="load">加载中...</td></tr></tbody>
</table></div>
<div id="eb" style="display:none"></div>
<div class="footer">数据来源: 腾讯财经<br>建议横屏查看 &middot; 数据仅供参考</div>
<script>
const INDICES=[{name:'上证指数',code:'1.000001'},{name:'深证成指',code:'0.399001'},{name:'创业板指',code:'0.399006'},{name:'沪深300',code:'1.000300'},{name:'中证1000',code:'1.000852'},{name:'中证500',code:'1.000905'},{name:'上证50',code:'1.000016'},{name:'科创50',code:'1.000688'}];
function ema(a,n){if(a.length<n)return null;let k=2/(n+1),e=a.slice(0,n).reduce((x,y)=>x+y,0)/n;for(let i=n;i<a.length;i++)e=a[i]*k+e*(1-k);return e}
function ml(r){if(r.length<34)return null;let cp=r.map(x=>x.c),hp=r.map(x=>x.h),lp=r.map(x=>x.l),s=[];for(let i=0;i<r.length;i++){let st=Math.max(0,i-33),h34=Math.max.apply(null,hp.slice(st,i+1)),l34=Math.min.apply(null,lp.slice(st,i+1));s.push(h34===l34?0:-100*(h34-cp[i])/(h34-l34))}let e=ema(s,4);return e!==null?Math.round((e+100)*100)/100:null}
function an(r,n){if(r.length<30)return{name:n,error:'数据不足'};let l=r.slice(-30),hm=Math.max.apply(null,l.map(x=>x.h)),lm=Math.min.apply(null,l.map(x=>x.l)),c=r[r.length-1].c;return{name:n,current:Math.round(c*100)/100,highMax:Math.round(hm*100)/100,highDate:l.reduce((p,x)=>x.h>p.h?x:p).d,lowMin:Math.round(lm*100)/100,lowDate:l.reduce((p,x)=>x.l<p.l?x:p).d,drop:Math.round((lm-hm)/hm*10000)/100,rise:Math.round((c-lm)/lm*10000)/100,ml:ml(r)}}
async function load(){var b=document.getElementById('rb'),s=document.getElementById('st'),tb=document.getElementById('tb'),eb=document.getElementById('eb');b.disabled=true;b.textContent='加载中';s.textContent='正在获取数据...';eb.style.display='none';var rs=[],er=[];await Promise.all(INDICES.map((idx,i)=>new Promise(rv=>setTimeout(async()=>{try{const res=await fetch('/api/kline?secid='+encodeURIComponent(idx.code)),d=await res.json();if(d.code===0&&d.data&&d.data[idx.code]){const rows=d.data[idx.code].day.map(x=>({d:x[0],c:parseFloat(x[2]),h:parseFloat(x[3]),l:parseFloat(x[4])}));rs.push(an(rows,idx.name))}else{er.push(idx.name+':无数据')}}catch(e){er.push(idx.name+':'+e.message)}s.textContent='已加载'+(rs.length+er.length)+'/'+INDICES.length+'个';rv()},i*200))));if(rs.length===0){tb.innerHTML='<tr><td colspan="9" class="load" style="color:#e74c3c">全部失败:'+er.join(';')+'</td></tr>'}else{tb.innerHTML=rs.map(x=>{var mv=x.ml!==null?x.ml.toFixed(2):'-',mc=x.ml!==null?(x.ml>70?'green':x.ml<30?'red':'orange'):'';return'<tr><td class="name">'+x.name+'</td><td>'+x.current.toFixed(2)+'</td><td>'+x.highMax.toFixed(2)+'</td><td>'+x.highDate+'</td><td>'+x.lowMin.toFixed(2)+'</td><td>'+x.lowDate+'</td><td class="'+(x.drop<0?'red':'green')+'">'+x.drop.toFixed(2)+'</td><td class="'+(x.rise>=0?'green':'red')+'">'+x.rise.toFixed(2)+'</td><td class="'+mc+'">'+mv+'</td></tr>'}).join('');document.getElementById('ut').textContent='更新时间:'+new Date().toLocaleString('zh-CN')}if(er.length>0){eb.style.display='block';eb.className='err-box';eb.textContent='部分失败:'+er.join(';')}b.disabled=false;b.textContent='刷新';s.textContent='加载完成'}
load();
</script>
</body>
</html>"""


def fetch_kline(secid, retries=3):
    url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=0&ut=fa5fd1943c7b386f172d689347e4b72b&cb=jsonp123'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/',
        'Connection': 'close',
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode('utf-8', errors='ignore')
            m = re.search(r'jsonp123\((.*)\)', raw, re.S)
            if not m:
                time.sleep(0.5)
                continue
            data = json.loads(m.group(1))
            if data.get('data') and data['data'].get('klines'):
                return data
        except Exception:
            time.sleep(0.5)
    return None


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
        elif self.path.startswith('/api/kline'):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            secid = qs.get('secid', [''])[0]
            data = fetch_kline(secid) if secid else None
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data or {'error': 'fail'}).encode('utf-8'))
        else:
            self.send_error(404)
    
    def log_message(self, *args):
        pass


if __name__ == '__main__':
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as srv:
        print(f"Listening on {PORT}")
        srv.serve_forever()
