"""Pure optimistic task projection. Network writes remain serialized and never retried."""
from dataclasses import dataclass
from copy import deepcopy
from habitica_core import task_id, split_tasks, update_tracker, merge_task, APIError

MAX_PENDING=24

@dataclass(frozen=True)
class Action:
    kind: str
    tid: str
    desired: bool | None = None
    iid: str = ''
    direction: str = ''

    def send(self, api):
        if self.kind=='item': return api.set_item(self.tid,self.iid,self.desired,partial=True)
        if self.kind=='daily': return api.set_daily(self.tid,self.desired,partial=True)
        if self.kind=='complete': return api.complete(self.tid,partial=True)
        if self.kind=='habit': return api.score_habit(self.tid,self.direction,partial=True)
        raise APIError('Unknown action.')

    def apply(self, data):
        t=next((x for x in data if task_id(x)==self.tid),None)
        if t is None: raise APIError('Task no longer available.')
        if self.kind=='habit':
            if t.get('type')!='habit' or self.direction not in ('up','down') or not t.get(self.direction): raise APIError('Habit action unavailable.')
            return data
        t=deepcopy(t)
        if self.kind=='daily':
            if t.get('type')!='daily': raise APIError('Daily unavailable.')
            t['completed']=bool(self.desired)
        elif self.kind=='item':
            if t.get('type') not in ('daily','todo') or t.get('completed'): raise APIError('Task no longer active.')
            item=next((i for i in t.get('checklist') or [] if task_id(i)==self.iid),None)
            if item is None: raise APIError('Checklist item unavailable.')
            item['completed']=bool(self.desired)
        elif self.kind=='complete':
            if t.get('type')!='todo' or any(not i.get('completed') for i in t.get('checklist') or []): raise APIError('To-Do checklist is unfinished.')
            t['completed']=True
        else: raise APIError('Unknown action.')
        return merge_task(data,t)

    def confirm(self, result):
        if not isinstance(result,dict) or task_id(result)!=self.tid: raise APIError('Unexpected confirmation. Refresh before retrying.')
        if self.kind=='item':
            i=next((x for x in result.get('checklist') or [] if task_id(x)==self.iid),None)
            valid=result.get('type') in ('todo','daily') and i is not None and bool(i.get('completed'))==self.desired
        elif self.kind=='daily': valid=result.get('type')=='daily' and bool(result.get('completed'))==self.desired
        elif self.kind=='complete': valid=result.get('type')=='todo' and bool(result.get('completed'))
        else: valid=result.get('type')=='habit'
        if not valid: raise APIError('Server state differs from the requested change. Refresh before retrying.')

class OptimisticState:
    def __init__(self,data=(),tracker=None):
        self.data=list(data); self.tracker=deepcopy(tracker or {}); self.pending=[]
        self._track()
    def _track(self):
        active,_,_=split_tasks(self.data)
        self.tracker=update_tracker(self.tracker,active,self.data)
    def refresh(self,data):
        self.data=list(data); self._track()
    def view(self):
        data=self.data
        for action in self.pending: data=action.apply(data)
        active,habits,dailies=split_tasks(data)
        return active,habits,dailies,update_tracker(self.tracker,active,data)
    def enqueue(self,action):
        if len(self.pending)>=MAX_PENDING: raise APIError('Sync queue is full. Wait for Habitica to catch up.')
        self.pending.append(action)
        try: return self.view()
        except Exception:
            self.pending.pop(); raise
    def acknowledge(self,result):
        action=self.pending[0]; action.confirm(result)
        self.data=merge_task(self.data,result); self.pending.pop(0); self._track()
    def abort(self):
        n=len(self.pending); self.pending.clear(); return n
    def reset(self):
        if self.pending: raise APIError('Wait for pending actions before resetting.')
        self.tracker={}; self._track()
