"""Mock tests for the incremental UI and partial-sync contract."""
import copy, unittest
from unittest.mock import Mock
from habitica_core import (API, APIError, DEMO, DEMO_DAILIES, DEMO_HABITS,
    display_signature, changed_keys, merge_task, split_tasks, update_tracker, tracked_progress)

class PerformanceTests(unittest.TestCase):
    def api(self,t):
        a=API('uid','token'); a.task=Mock(return_value=copy.deepcopy(t)); a.request=Mock(); a.tasks=Mock(); return a
    def test_unchanged_84_rows(self):
        tasks=[dict(id=str(i),type='todo',text=f'Task {i}') for i in range(84)]
        sigs={t['id']:display_signature(t) for t in tasks}
        self.assertEqual(changed_keys(sigs,dict(sigs)),(set(),set()))
    def test_one_changed_row(self):
        tasks=[dict(id=str(i),type='daily',text=f'Task {i}',completed=False) for i in range(84)]
        before={t['id']:display_signature(t) for t in tasks}; tasks[17]['completed']=True
        after={t['id']:display_signature(t) for t in tasks}
        self.assertEqual(changed_keys(before,after),(set(),{'17'}))
    def test_remove_only_completed(self):
        before={str(i):i for i in range(84)}; after=dict(before); del after['5']
        self.assertEqual(changed_keys(before,after),({'5'},set()))
    def test_ignore_invisible_fields(self):
        t=copy.deepcopy(DEMO_HABITS[0]); a=display_signature(t); t.update(value=9,updatedAt='now')
        self.assertEqual(a,display_signature(t)); t['up']=False; self.assertNotEqual(a,display_signature(t))
    def test_expand_and_checklist_signatures(self):
        t=copy.deepcopy(DEMO[0]); a=display_signature(t); self.assertNotEqual(a,display_signature(t,True)); t['checklist'][0]['completed']=False; self.assertNotEqual(a,display_signature(t))
    def test_partial_complete_and_tracker(self):
        a=self.api(DEMO[2]); result=a.complete('demo-single',partial=True); self.assertTrue(result['completed']); a.tasks.assert_not_called(); a.request.assert_called_once()
        state=update_tracker({},DEMO,[]); combined=merge_task(DEMO,result); active,_,_=split_tasks(combined); self.assertEqual(tracked_progress(update_tracker(state,active,combined)),(1,3,33))
    def test_partial_habit(self):
        a=self.api(DEMO_HABITS[0]); a.score_habit('habit-1','up',partial=True); a.tasks.assert_not_called(); a.task.assert_called_once(); a.request.assert_called_once()
    def test_partial_daily(self):
        a=self.api(DEMO_DAILIES[1]); result=dict(DEMO_DAILIES[1],completed=True); a.task.side_effect=[DEMO_DAILIES[1],result]
        self.assertEqual(a.set_daily('daily-2',True,partial=True),result); a.tasks.assert_not_called(); self.assertEqual(a.task.call_count,2)
    def test_partial_item(self):
        a=self.api(DEMO[0]); result=copy.deepcopy(DEMO[0]); result['checklist'][6]['completed']=True; a.task.side_effect=[DEMO[0],result]
        self.assertEqual(a.set_item('demo-review','6',True,partial=True),result); a.tasks.assert_not_called(); a.request.assert_called_once()
    def test_partial_idempotence(self):
        a=self.api(DEMO_DAILIES[0]); a.set_daily('daily-1',True,partial=True); a.task.assert_called_once(); a.request.assert_not_called(); a.tasks.assert_not_called()
    def test_partial_failure(self):
        a=self.api(DEMO[2]); a.request.side_effect=APIError('network'); self.assertRaises(APIError,a.complete,'demo-single',partial=True); a.request.assert_called_once(); a.tasks.assert_not_called()
    def test_merge_preserves_order_and_others(self):
        updated=dict(DEMO[1],text='New'); result=merge_task(DEMO,updated); self.assertEqual(result,[DEMO[0],updated,DEMO[2]]); self.assertIs(result[0],DEMO[0]); self.assertIs(result[2],DEMO[2])
    def test_merge_invalid_response(self):
        for v in [None,{},dict(id='x',type='reward')]: self.assertRaises(APIError,merge_task,DEMO,v)

if __name__=='__main__': unittest.main()
