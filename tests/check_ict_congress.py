"""ICT registration/attendance regression; writes only to an explicitly isolated database."""
from argparse import ArgumentParser
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from tempfile import gettempdir
from urllib.parse import urlencode, urlsplit, parse_qs
from urllib.request import urlopen
import re,subprocess,uuid
parser=ArgumentParser(description=__doc__)
parser.add_argument('--base-url',required=True)
parser.add_argument('--test-datadir',required=True)
parser.add_argument('--mysql-port',required=True,type=int)
a=parser.parse_args()
mysql=['C:/xampp/mysql/bin/mysql.exe','--protocol=TCP','--host=127.0.0.1','--port='+str(a.mysql_port),'--user=root','-N','-B']
def sql(query):
 p=subprocess.run(mysql+['-e',query],capture_output=True,text=True);assert p.returncode==0,p.stderr;return p.stdout.strip()
actual=Path(sql('SELECT @@datadir')).resolve()
assert actual==Path(a.test_datadir).resolve() and actual.name=='mysql' and actual.parent.name=='.work'
assert actual.is_relative_to(Path(gettempdir()).resolve()),'Refusing writes outside OS Temp.'
base=a.base_url.rstrip('/')+'/IctCongress/'
def request(route,values=None):
 with urlopen(base+route,None if values is None else urlencode(values).encode(),timeout=15) as res:
  text=res.read().decode('utf-8')
 assert not re.search(r'(Warning|Deprecated|Fatal error|Parse error)</b>|Database (setup|connection) failed',text),text[:500]
 return text
class Page(HTMLParser):
 def __init__(self,text):
  super().__init__();self.links=[];self.feed(text)
 def handle_starttag(self,tag,attrs):
  values=dict(attrs)
  if tag=='a' and values.get('href'):self.links.append(values['href'])
def literal(value):return '0x'+value.encode('utf-8').hex()
request('registration.php')
id="QA'O&Neil-"+uuid.uuid4().hex[:8]
where='idNum='+literal(id)
values=dict(add='1',idNum=id,campus='Main',studFName='Ava <&>',studLName="O'Neil",amountPaid='123.45')
before=int(sql('SELECT COUNT(*) FROM ictcongress.Registration'))
try:
 html=request('registration.php',values)
 assert int(sql('SELECT COUNT(*) FROM ictcongress.Registration'))==before+1
 assert sql('SELECT studLName FROM ictcongress.Registration WHERE '+where)=="O'Neil"
 assert sql('SELECT amountPaid FROM ictcongress.Registration WHERE '+where)=='123.45'
 assert 'Ava &lt;&amp;&gt;' in html
 links=Page(html).links
 for field,route in [('id','edit.php'),('del','registration.php')]:
  assert any(urlsplit(link).path==route and parse_qs(urlsplit(link).query).get(field)==[id] for link in links),(field,links)
 assert 'already registered' in request('registration.php',values)
 assert int(sql('SELECT COUNT(*) FROM ictcongress.Registration'))==before+1
 for field,bad in [('studFName',''),('amountPaid','-1'),('amountPaid','abc'),('amountPaid','1.001'),('amountPaid','100000000')]:
  assert 'non-negative fee' in request('registration.php',{**values,field:bad})
  assert int(sql('SELECT COUNT(*) FROM ictcongress.Registration'))==before+1
 edit='edit.php?'+urlencode({'id':id})
 request(edit,dict(update='1',campus='Banilad',studFName='Ava',studLName="D'Angelo",amountPaid='75.50'))
 assert sql('SELECT studLName FROM ictcongress.Registration WHERE '+where)=="D'Angelo"
 assert sql('SELECT amountPaid FROM ictcongress.Registration WHERE '+where)=='75.50'
 html=request('attendance.php',dict(submit='1',id=id))
 assert 'D&#039;Angelo' in html
 assert any(parse_qs(urlsplit(link).query).get('attend')==[id] for link in Page(html).links)
 assert 'NOT YET REGISTERED' in request('attendance.php',dict(submit='1',id="missing' OR 1=1 --"))
 request('attendance.php?'+urlencode({'attend':id}))
 assert sql('SELECT attended FROM ictcongress.Registration WHERE '+where)=='Yes'
 assert 'ALREADY EXIST' in request('attendance.php?'+urlencode({'attend':id}))
 total=int(sql('SELECT COUNT(*) FROM ictcongress.Registration'))
 request('registration.php?'+urlencode({'del':"missing' OR 1=1 --"}))
 assert int(sql('SELECT COUNT(*) FROM ictcongress.Registration'))==total
 request('registration.php?'+urlencode({'del':id}))
 assert sql('SELECT COUNT(*) FROM ictcongress.Registration WHERE '+where)=='0'
 assert int(sql('SELECT COUNT(*) FROM ictcongress.Registration'))==before
 print('PASS: ICT apostrophes, quoted/ampersand IDs, escaped output/encoded action links, add/edit/delete, decimal fees, duplicate/invalid input feedback, attendance lookup/mark/repeat and literal SQL-like ID handling.')
finally:
 sql('DELETE FROM ictcongress.Registration WHERE '+where)
