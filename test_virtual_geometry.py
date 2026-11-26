import random, unittest
from virtual_geometry import offsets, visible_range, anchor_at, restore_anchor

class VirtualGeometryTests(unittest.TestCase):
    def test_empty(self): self.assertEqual(list(visible_range([0],0,400)),[])
    def test_zero_height(self): self.assertEqual(list(visible_range([0,30],0,0)),[])
    def test_boundaries(self):
        self.assertEqual(list(visible_range([0,30,60,90],30,30,0)),[1])
    def test_variable_height(self):
        self.assertEqual(list(visible_range(offsets([20,90,5,40]),25,90,0)),[1,2])
    def test_initial_84(self):
        edges=offsets([30]*84)
        self.assertLessEqual(len(visible_range(edges,0,350,90)),15)
    def test_middle_84(self):
        edges=offsets([30]*84)
        self.assertLessEqual(len(visible_range(edges,960,350,90)),19)
    def test_large_list(self):
        edges=offsets([34]*10000)
        self.assertLessEqual(len(visible_range(edges,170000,450,90)),20)
    def test_no_lost_rows(self):
        e=offsets([30]*84); visible=set()
        for top in range(0,e[-1],50): visible.update(visible_range(e,top,350,90))
        self.assertEqual(visible,set(range(84)))
    def test_anchor_insert(self):
        keys=['a','b','c']; e=offsets([30,40,90]); a=anchor_at(keys,e,37)
        self.assertEqual(restore_anchor(['new']+keys,offsets([12,30,40,90]),a,37,30),49)
    def test_anchor_height_changes(self):
        keys=['a','b','c']; a=anchor_at(keys,offsets([30,40,90]),37)
        self.assertEqual(restore_anchor(keys,offsets([90,40,90]),a,37,30),97)
    def test_anchor_deleted(self):
        self.assertEqual(restore_anchor(['a','c'],offsets([30,90]),('b',7),37,30),37)
    def test_anchor_bottom_clamp(self):
        self.assertEqual(restore_anchor(['a','b'],offsets([30,30]),('b',20),50,45),15)
    def test_anchor_shrunk(self):
        self.assertEqual(restore_anchor(['a','b','c'],offsets([10,5,90]),('b',30),40,10),14)
    def test_random_visibility_against_brute_force(self):
        rng=random.Random(42)
        for _ in range(500):
            e=offsets([rng.randrange(1,140) for _ in range(rng.randrange(1,180))]); top=rng.randrange(e[-1]+1); h=rng.randrange(1,500); buffer=rng.randrange(0,130)
            expected=[i for i in range(len(e)-1) if e[i+1]>max(0,top-buffer) and e[i]<top+h+buffer]
            self.assertEqual(list(visible_range(e,top,h,buffer)),expected)

if __name__=='__main__': unittest.main()
