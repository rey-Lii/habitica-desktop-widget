import copy, unittest
from unittest.mock import Mock
from habitica_core import API, APIError, DEMO, DEMO_HABITS, DEMO_DAILIES, split_tasks, progress, visible_todos, update_tracker, tracked_progress, daily_progress

class Logic(unittest.TestCase):
    def api(self,t):
        api=API('uid','secret'); api.task=Mock(return_value=copy.deepcopy(t)); api.request=Mock(); api.tasks=Mock(return_value=[]); return api
    def test_progress(self):
        self.assertEqual(progress(DEMO[0]),(6,10,60)); self.assertEqual(progress(DEMO[2]),(0,0,0)); self.assertEqual(progress({'completed':True}),(0,0,100))
    def test_single_complete(self):
        api=self.api(DEMO[2]); api.complete('demo-single'); api.request.assert_called_once_with('POST','/tasks/demo-single/score/up')
    def test_completed_does_not_score_twice(self):
        api=self.api(dict(DEMO[2],completed=True)); api.complete('demo-single'); api.request.assert_not_called()
    def test_unfinished_parent(self):
        api=self.api(DEMO[0]); self.assertRaises(APIError,api.complete,'demo-review'); api.request.assert_not_called()
    def test_finished_parent(self):
        t=copy.deepcopy(DEMO[0]); [i.update(completed=True) for i in t['checklist']]; api=self.api(t); api.complete('demo-review'); api.request.assert_called_once_with('POST','/tasks/demo-review/score/up')
    def test_wrong_type(self):
        api=self.api(DEMO_HABITS[0]); self.assertRaises(APIError,api.complete,'habit-1'); api.request.assert_not_called()
    def test_check(self):
        api=self.api(DEMO[0]); api.set_item('demo-review','6',True); api.request.assert_called_once_with('POST','/tasks/demo-review/checklist/6/score')
    def test_uncheck(self):
        api=self.api(DEMO[0]); api.set_item('demo-review','0',False); api.request.assert_called_once_with('POST','/tasks/demo-review/checklist/0/score')
    def test_check_idempotence(self):
        api=self.api(DEMO[0]); api.set_item('demo-review','0',True); api.request.assert_not_called()
    def test_habit(self):
        api=self.api(DEMO_HABITS[3]); api.score_habit('habit-4','up'); api.request.assert_called_once_with('POST','/tasks/habit-4/score/up'); api.request.reset_mock(); api.score_habit('habit-4','down'); api.request.assert_called_once_with('POST','/tasks/habit-4/score/down')
    def test_unavailable_habit_direction(self):
        api=self.api(DEMO_HABITS[0]); self.assertRaises(APIError,api.score_habit,'habit-1','down'); api.request.assert_not_called()
    def test_fetch_all_types_and_recent_completed(self):
        api=API('uid','secret'); finished=dict(DEMO[2],id='finished',completed=True)
        api.request=Mock(side_effect=[DEMO+DEMO_HABITS+DEMO_DAILIES,[finished]])
        result=api.tasks(); self.assertEqual(result,DEMO+DEMO_HABITS+DEMO_DAILIES+[finished]); self.assertEqual(split_tasks(result),(DEMO,DEMO_HABITS,DEMO_DAILIES))
        self.assertEqual(api.request.call_args_list[1].args,('GET','/tasks/user?type=completedTodos'))
    def test_write_failure_not_retried(self):
        api=self.api(DEMO[2]); api.request.side_effect=APIError('network'); self.assertRaises(APIError,api.complete,'demo-single'); api.request.assert_called_once(); api.tasks.assert_not_called()

    def test_84_todos_all_preserved(self):
        quick=[dict(id=f'q{i}',type='todo',text=f'Task {i}',completed=False) for i in range(82)]
        data=quick[:40]+[DEMO[0]]+quick[40:]+[DEMO[1]]
        self.assertEqual(visible_todos(data),DEMO[:2]+quick)
        self.assertEqual(len(visible_todos(data)),84)
        state=update_tracker({},data,[])
        self.assertEqual(tracked_progress(state),(0,84,0))
        state=update_tracker(state,data[21:],[dict(t,completed=True) for t in data[:21]])
        self.assertEqual(tracked_progress(state),(21,84,25))
    def test_search_checklist_text(self):
        self.assertEqual(visible_todos(DEMO,'supplementary'),[DEMO[0]])
    def test_no_checklist(self):
        items=[{'id':'x','checklist':None},{'id':'y','checklist':[]}]
        self.assertEqual(visible_todos(items),items)
    def test_first_sync_excludes_old_completed(self):
        state=update_tracker({},DEMO,[dict(DEMO[2],id='old',completed=True)])
        self.assertEqual(tracked_progress(state),(0,3,0))
    def test_completion_persists_after_recent_list_rolls_over(self):
        state=update_tracker({},DEMO,[])
        state=update_tracker(state,DEMO[:2],[dict(DEMO[2],completed=True)])
        self.assertEqual(tracked_progress(state),(1,3,33))
        state=update_tracker(state,DEMO[:2],[])
        self.assertEqual(tracked_progress(state),(1,3,33))
        state=update_tracker(state,DEMO,[])
        self.assertEqual(tracked_progress(state),(0,3,0))
    def test_deleted_not_counted_as_complete(self):
        state=update_tracker({},DEMO,[])
        state=update_tracker(state,DEMO[:2],[])
        self.assertEqual(tracked_progress(state),(0,2,0))
    def test_new_tasks_update_denominator(self):
        state=update_tracker({},DEMO[:2],[])
        self.assertEqual(tracked_progress(update_tracker(state,DEMO,[])),(0,3,0))
    def test_daily_progress_only_due(self):
        self.assertEqual(daily_progress(DEMO_DAILIES),(1,3,33))
        self.assertEqual(daily_progress([DEMO_DAILIES[2]]),(0,0,0))
    def test_daily_complete_and_undo(self):
        api=self.api(DEMO_DAILIES[1]); api.set_daily('daily-2',True); api.request.assert_called_once_with('POST','/tasks/daily-2/score/up')
        api=self.api(DEMO_DAILIES[0]); api.set_daily('daily-1',False); api.request.assert_called_once_with('POST','/tasks/daily-1/score/down')
    def test_daily_idempotence_and_wrong_type(self):
        api=self.api(DEMO_DAILIES[0]); api.set_daily('daily-1',True); api.request.assert_not_called()
        api=self.api(DEMO[0]); self.assertRaises(APIError,api.set_daily,'demo-review',True); api.request.assert_not_called()
    def test_daily_checklist(self):
        api=self.api(DEMO_DAILIES[3]); api.set_item('daily-4','d2',True); api.request.assert_called_once_with('POST','/tasks/daily-4/checklist/d2/score')
    def test_confirmed_write_retained(self):
        api=self.api(DEMO[2]); result=api.complete('demo-single'); self.assertEqual(result,[dict(DEMO[2],completed=True)])

if __name__=='__main__': unittest.main()
