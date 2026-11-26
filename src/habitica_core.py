"""Habitica Progress Board — personal desktop client, v0.7.5."""
import base64, copy, ctypes, json, os, queue, sys, threading, time, math
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote

VERSION = '0.7.5'
ROOT = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.config'))) / 'HabiticaProgressBoard'
CONFIG = ROOT / 'settings.json'
BASE = 'https://habitica.com/api/v3'
DEMO = [{'id':'demo-review','type':'todo','text':'AKI · AI Narrative Review','completed':False,'checklist':[
 {'id':str(i),'text':t,'completed':i<6} for i,t in enumerate(['Identify review writing templates','Retrieve database search strategies','Recover screening records','Verify AI and non-AI study counts','Review study assessment tables','Revise Methods section','Verify database search dates','Define outpatient AKI study scope','Update Supplementary Section S1','Align Abstract, Methods and Limitations'])]},
 {'id':'demo-phd','type':'todo','text':'PhD · Targeted Outreach','completed':False,'checklist':[{'id':str(i),'text':t,'completed':i<2} for i,t in enumerate(['Identify funded research groups','Shortlist aligned PIs','Review recent publications','Draft tailored emails','Submit applications'])]}]

DEMO_HABITS = [
 {'id':'habit-1','type':'habit','text':'Focused research session','up':True,'down':False},
 {'id':'habit-2','type':'habit','text':'Read a research paper','up':True,'down':False},
 {'id':'habit-3','type':'habit','text':'Practice English','up':True,'down':False},
 {'id':'habit-4','type':'habit','text':'Stay focused','up':True,'down':True},
]

DEMO_DAILIES = [
    {'id':'daily-1','type':'daily','text':'Read a paper','isDue':True,'completed':True,'checklist':[]},
    {'id':'daily-2','type':'daily','text':'Practice English','isDue':True,'completed':False,'checklist':[]},
    {'id':'daily-3','type':'daily','text':'Exercise','isDue':False,'completed':False,'checklist':[]},
    {'id':'daily-4','type':'daily','text':'Research session','isDue':True,'completed':False,'checklist':[{'id':'d1','text':'Plan session','completed':True},{'id':'d2','text':'Write notes','completed':False}]},
]

def split_tasks(tasks):
    return ([t for t in tasks if t.get('type')=='todo' and not t.get('completed') and task_id(t)],
            [t for t in tasks if t.get('type')=='habit' and task_id(t)],
            [t for t in tasks if t.get('type')=='daily' and task_id(t)])

def matches(task, query=''):
    needle=query.casefold().strip()
    return not needle or needle in str(task.get('text','')).casefold() or any(needle in str(i.get('text','')).casefold() for i in (task.get('checklist') or []))

def visible_todos(tasks, query=''):
    # Keep every To-Do under one category, with checklist tasks first.
    items=[t for t in tasks if matches(t,query)]
    return [t for t in items if t.get('checklist')]+[t for t in items if not t.get('checklist')]

def update_tracker(state, active_tasks, completed_tasks):
    # Count only confirmed completions of previously tracked tasks. Deleted or
    # otherwise unconfirmed missing tasks are not counted as completed.
    active={task_id(t) for t in active_tasks if task_id(t)}
    previous=set(state.get('open',[])); done=set(state.get('done',[]))
    confirmed={task_id(t) for t in completed_tasks if t.get('type')=='todo' and t.get('completed') and task_id(t)}
    done.update(previous & confirmed); done.difference_update(active)
    # Keep unresolved IDs so a later confirmed completion can be recognized.
    pending=(set(state.get('pending',[]))|previous)-active-done
    done.update(pending & confirmed); pending.difference_update(done)
    return {'open':sorted(active),'done':sorted(done),'pending':sorted(pending)}

def tracked_progress(state):
    done=len(state.get('done',[])); total=done+len(state.get('open',[]))
    return done,total,round(100*done/total) if total else 0

def daily_progress(tasks):
    due=[t for t in tasks if t.get('isDue') is True]
    n=sum(bool(t.get('completed')) for t in due); total=len(due)
    return n,total,round(100*n/total) if total else 0

def task_id(t): return str(t.get('id') or t.get('_id') or '')
def progress(task):
    items = task.get('checklist') or []
    n = sum(bool(i.get('completed')) for i in items)
    return n, len(items), round(100*n/len(items)) if items else int(bool(task.get('completed')))*100

def protect(value, decrypt=False):
    """Windows DPAPI: only the same Windows user can decrypt the saved token."""
    if os.name != 'nt': raise RuntimeError('Saved credentials require Windows.')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]
    raw = base64.b64decode(value) if decrypt else value.encode('utf-8')
    buf = ctypes.create_string_buffer(raw)
    src = Blob(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    dst = Blob()
    crypt = ctypes.windll.crypt32
    free = ctypes.windll.kernel32.LocalFree
    free.argtypes = [ctypes.c_void_p]; free.restype = ctypes.c_void_p
    if decrypt:
        ok = crypt.CryptUnprotectData(ctypes.byref(src), None, None, None, None, 1, ctypes.byref(dst))
    else:
        ok = crypt.CryptProtectData(ctypes.byref(src), None, None, None, None, 1, ctypes.byref(dst))
    if not ok: raise ctypes.WinError()
    try: data = ctypes.string_at(dst.pbData, dst.cbData)
    finally: free(ctypes.cast(dst.pbData, ctypes.c_void_p))
    return data.decode('utf-8') if decrypt else base64.b64encode(data).decode('ascii')

def load_settings():
    try:
        data=json.loads(CONFIG.read_text(encoding='utf-8'))
        return data if isinstance(data,dict) else {}
    except (OSError, ValueError): return {}

def save_settings(data):
    ROOT.mkdir(parents=True, exist_ok=True)
    temp=CONFIG.with_suffix('.tmp'); temp.write_text(json.dumps(data,indent=2),encoding='utf-8'); temp.replace(CONFIG)

class APIError(Exception): pass
class RateLimitError(APIError): pass

def retry_delay(value, now=None):
    """Honor Retry-After seconds (or an HTTP-date); conservative fallback."""
    try:
        delay=float(value)
        if not math.isfinite(delay) or delay<0: raise ValueError()
    except (TypeError, ValueError, OverflowError):
        try:
            delay=max(0,parsedate_to_datetime(value).timestamp()-(time.time() if now is None else now))
        except (TypeError, ValueError, OverflowError, AttributeError, OSError): delay=120
    return max(1,math.ceil(delay)+1)

class API:
    def __init__(self, uid, token): self.uid=uid; self.token=token; self.cooldown_until=0.0
    def cooldown_remaining(self): return max(0,math.ceil(self.cooldown_until-time.monotonic()))
    def request(self, method, path):
        if self.cooldown_remaining(): raise RateLimitError('Habitica rate limit · cooling down.')
        req=Request(BASE+path, data=b'{}' if method=='POST' else None, method=method, headers={
            'x-api-user':self.uid,'x-api-key':self.token,'x-client':self.uid+'-ProgressBoard',
            'Accept':'application/json','Content-Type':'application/json','User-Agent':'HabiticaProgressBoard/'+VERSION})
        try:
            with urlopen(req,timeout=15) as response: data=json.load(response)
        except HTTPError as e:
            if e.code in (401,403): raise APIError('Authentication failed. Check your User ID and API Token.') from None
            if e.code==429:
                self.cooldown_until=time.monotonic()+retry_delay(e.headers.get('Retry-After') if e.headers else None)
                raise RateLimitError('Habitica rate limit · cooling down.') from None
            raise APIError(f'Habitica returned HTTP {e.code}. Refresh before trying again.') from None
        except (URLError, TimeoutError, OSError, ValueError): raise APIError('Network error. Refresh before retrying; a write may already have succeeded.') from None
        if not isinstance(data,dict) or not data.get('success'): raise APIError('Habitica did not confirm the request.')
        return data.get('data')
    def tasks(self):
        data=self.request('GET','/tasks/user')
        if not isinstance(data,list): raise APIError('Unexpected task response.')
        todos, habits, dailies=split_tasks(data)
        completed=self.request('GET','/tasks/user?type=completedTodos')
        if not isinstance(completed,list): raise APIError('Unexpected completed task response.')
        return todos+habits+dailies+completed
    def task(self, tid):
        return self.request('GET','/tasks/'+quote(tid,safe=''))
    def set_item(self, tid, iid, desired, *, partial=False):
        # The scoring endpoint toggles, so inspect current server state first.
        t=self.task(tid)
        if not isinstance(t,dict) or t.get('type') not in ('todo','daily') or t.get('completed'): raise APIError('This task is no longer active. Refresh.')
        item=next((i for i in (t.get('checklist') or []) if task_id(i)==iid),None)
        if item is None: raise APIError('Checklist item no longer exists. Refresh.')
        changed=bool(item.get('completed'))!=desired
        if changed:
            self.request('POST',f'/tasks/{quote(tid,safe="")}/checklist/{quote(iid,safe="")}/score')
        if partial:
            return self.task(tid) if changed else t
        return self.tasks()
    def set_daily(self,tid,desired, *, partial=False):
        t=self.task(tid)
        if not isinstance(t,dict) or t.get('type')!='daily': raise APIError('This Daily is no longer available. Refresh.')
        changed=bool(t.get('completed'))!=desired
        if changed:
            self.request('POST',f'/tasks/{quote(tid,safe="")}/score/{"up" if desired else "down"}')
        if partial:
            return self.task(tid) if changed else t
        return self.tasks()
    def score_habit(self,tid,direction, *, partial=False):
        if direction not in ('up','down'): raise APIError('Invalid habit action.')
        t=self.task(tid)
        if not isinstance(t,dict) or t.get('type')!='habit' or not t.get(direction):
            raise APIError('This habit action is not available. Refresh.')
        self.request('POST',f'/tasks/{quote(tid,safe="")}/score/{direction}')
        if partial:
            # Scoring changes Habitica stats, but this widget shows no habit counter.
            return t
        return self.tasks()
    def complete(self,tid, *, partial=False):
        t=self.task(tid)
        if not isinstance(t,dict) or t.get('type')!='todo': raise APIError('This To-Do is no longer available. Refresh.')
        if not t.get('completed'):
            if any(not i.get('completed') for i in (t.get('checklist') or [])):
                raise APIError('Some checklist items are unfinished. Refresh first.')
            self.request('POST',f'/tasks/{quote(tid,safe="")}/score/up')
        if partial:
            # A successful score/up response confirms parent completion.
            return dict(t,completed=True)
        data=self.tasks()
        if not any(task_id(x)==tid and x.get('type')=='todo' for x in data):
            data.append(dict(t,completed=True))
        return data


DEMO.append({"id":"demo-single","type":"todo","text":"Draft a project outline","completed":False,"checklist":[]})


def display_signature(t, expanded=False):
    """Only fields affecting widget appearance or button actions."""
    return (task_id(t), t.get('type'), str(t.get('text','')), bool(t.get('completed')),
            t.get('isDue'), bool(t.get('up')), bool(t.get('down')), bool(expanded),
            tuple((task_id(i),str(i.get('text','')),bool(i.get('completed'))) for i in (t.get('checklist') or [])))


def merge_task(tasks, updated):
    """Replace one server-confirmed task, retaining server order of other tasks."""
    if not isinstance(updated,dict) or not task_id(updated) or updated.get('type') not in ('todo','daily','habit'):
        raise APIError('Unexpected task response. Refresh before retrying.')
    tid=task_id(updated); result=[]; found=False
    for t in tasks:
        if task_id(t)==tid:
            if not found: result.append(updated); found=True
        else: result.append(t)
    if not found: result.append(updated)
    return result


def changed_keys(previous, desired):
    """Identify removals and rebuilds from keyed display signatures."""
    return set(previous)-set(desired), {k for k,v in desired.items() if k not in previous or previous[k]!=v}
