import copy, unittest
from unittest.mock import Mock
from optimistic import Action, OptimisticState, MAX_PENDING
from habitica_core import DEMO, DEMO_DAILIES, DEMO_HABITS, APIError, tracked_progress, task_id

class OptimisticTests(unittest.TestCase):
    def setUp(self): self.s=OptimisticState(copy.deepcopy(DEMO+DEMO_DAILIES+DEMO_HABITS))
    def task(self,tid,data): return next(t for t in data if task_id(t)==tid)
    def test_complete_is_instant_not_persisted(self):
        active,_,_,preview=self.s.enqueue(Action('complete','demo-single'))
        self.assertNotIn('demo-single',[task_id(t) for t in active]); self.assertEqual(tracked_progress(preview),(1,3,33)); self.assertEqual(tracked_progress(self.s.tracker),(0,3,0))
    def test_acknowledge_preserves_projection(self):
        self.s.enqueue(Action('complete','demo-single')); before=self.s.view(); self.s.acknowledge(dict(DEMO[2],completed=True)); self.assertEqual(self.s.view(),before); self.assertEqual(tracked_progress(self.s.tracker),(1,3,33))
    def test_two_dailies_toggle_same_before_ack(self):
        self.s.enqueue(Action('daily','daily-2',True)); self.s.enqueue(Action('daily','daily-2',False)); self.assertFalse(self.task('daily-2',self.s.view()[2])['completed'])
        self.s.acknowledge(dict(DEMO_DAILIES[1],completed=True)); self.assertFalse(self.task('daily-2',self.s.view()[2])['completed']); self.s.acknowledge(DEMO_DAILIES[1]); self.assertFalse(self.task('daily-2',self.s.view()[2])['completed'])
    def test_checklist_then_parent(self):
        for i in range(6,10): self.s.enqueue(Action('item','demo-review',True,str(i)))
        self.s.enqueue(Action('complete','demo-review')); self.assertNotIn('demo-review',[task_id(t) for t in self.s.view()[0]])
        for i in range(6,10): self.s.acknowledge(self.s.pending[0].apply(self.s.data)[0])
        self.s.acknowledge(dict(self.s.data[0],completed=True)); self.assertEqual(tracked_progress(self.s.tracker),(1,3,33))
    def test_abort_reverts_only_unconfirmed(self):
        self.s.enqueue(Action('complete','demo-single')); self.s.enqueue(Action('daily','daily-2',True)); self.s.acknowledge(dict(DEMO[2],completed=True)); self.assertEqual(self.s.abort(),1); self.assertEqual(tracked_progress(self.s.view()[3]),(1,3,33)); self.assertFalse(self.task('daily-2',self.s.view()[2])['completed'])
    def test_invalid_enqueue_does_not_mutate(self):
        with self.assertRaises(APIError): self.s.enqueue(Action('complete','demo-review'))
        self.assertEqual(self.s.pending,[])
    def test_habit_clicks_never_coalesced(self):
        a=Action('habit','habit-4',direction='up'); b=Action('habit','habit-4',direction='down'); self.s.enqueue(a); self.s.enqueue(a); self.s.enqueue(b)
        self.assertEqual(self.s.pending,[a,a,b]); api=Mock(); api.score_habit.return_value=DEMO_HABITS[3]
        for action in list(self.s.pending): self.s.acknowledge(action.send(api))
        self.assertEqual([x.args[1] for x in api.score_habit.call_args_list],['up','up','down'])
    def test_queue_bound(self):
        a=Action('habit','habit-1',direction='up')
        for _ in range(MAX_PENDING): self.s.enqueue(a)
        with self.assertRaises(APIError): self.s.enqueue(a)
        self.assertEqual(len(self.s.pending),MAX_PENDING)
    def test_mismatched_ack_requires_refresh(self):
        self.s.enqueue(Action('daily','daily-2',True))
        with self.assertRaises(APIError): self.s.acknowledge(DEMO_DAILIES[1])
        self.s.abort(); self.assertFalse(self.task('daily-2',self.s.view()[2])['completed'])
    def test_refresh_does_not_overwrite_pending(self):
        self.s.enqueue(Action('daily','daily-2',True)); self.s.refresh(copy.deepcopy(DEMO+DEMO_DAILIES+DEMO_HABITS)); self.assertTrue(self.task('daily-2',self.s.view()[2])['completed'])
    def test_reconcile_after_ambiguous_write(self):
        self.s.enqueue(Action('complete','demo-single')); self.s.abort(); data=copy.deepcopy(DEMO+DEMO_DAILIES+DEMO_HABITS); data[2]['completed']=True; self.s.refresh(data); self.assertEqual(tracked_progress(self.s.tracker),(1,3,33))
    def test_84_todos(self):
        s=OptimisticState([dict(id=str(i),type='todo',completed=False) for i in range(84)])
        for i in range(21): s.enqueue(Action('complete',str(i)))
        self.assertEqual(tracked_progress(s.view()[3]),(21,84,25)); self.assertEqual(tracked_progress(s.tracker),(0,84,0))
        for i in range(21): s.acknowledge(dict(id=str(i),type='todo',completed=True))
        self.assertEqual(tracked_progress(s.tracker),(21,84,25))
    def test_reset_requires_empty_queue(self):
        self.s.enqueue(Action('habit','habit-1',direction='up'))
        with self.assertRaises(APIError): self.s.reset()
    def test_network_error_not_retried_by_action(self):
        api=Mock(); api.score_habit.side_effect=APIError('timeout'); a=Action('habit','habit-1',direction='up'); self.s.enqueue(a)
        with self.assertRaises(APIError): a.send(api)
        self.s.abort(); self.assertEqual(api.score_habit.call_count,1); self.assertEqual(self.s.pending,[])
if __name__=='__main__': unittest.main()
