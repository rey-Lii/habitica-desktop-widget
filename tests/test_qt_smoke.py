"""Optional real Qt smoke checks (run on Windows or a Qt-enabled machine)."""
import os, unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtWidgets import QApplication, QLabel, QFrame, QVBoxLayout, QPushButton
    from virtual_scroll import VirtualScroll, Row
    HAS_QT=True
except ImportError:
    HAS_QT=False

@unittest.skipUnless(HAS_QT,'PySide6 not installed')
class QtSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.view=VirtualScroll(); self.view.resize(360,400); self.view.show(); self.app.processEvents()
    def tearDown(self): self.view.close(); self.app.processEvents()
    def test_84_real_rows(self):
        clicks=[]
        def create(i):
            w=QFrame(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); b=QPushButton(str(i)); b.setFixedHeight(30); b.clicked.connect(lambda:clicks.append(i)); l.addWidget(b); return w
        self.view.set_rows([Row(i,i,lambda i=i:create(i),lambda w:30,group='tasks',gap=1) for i in range(84)])
        self.app.processEvents(); self.assertLess(len(self.view.live),25)
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum()); self.app.processEvents()
        self.assertIn(83,self.view.live); self.assertLess(len(self.view.live),25)
        self.view.live[83][1].findChild(QPushButton).click(); self.assertEqual(clicks,[83])
    def test_wrap_and_resize(self):
        def create():
            w=QLabel('A very long task with a lot of text. '*20); w.setWordWrap(True); return w
        self.view.set_rows([Row('text','text',create,lambda w:60)])
        self.app.processEvents(); old=self.view.edges[-1]
        self.view.resize(230,400); self.app.processEvents(); self.app.processEvents()
        self.assertGreaterEqual(self.view.edges[-1],old)

if __name__=='__main__': unittest.main()
