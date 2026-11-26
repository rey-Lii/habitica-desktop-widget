"""Habitica Progress Board 0.7.5 — Qt desktop widget."""
import sys, os, copy, threading, time
from pathlib import Path


def asset_path(filename):
    """Resolve icons from the source tree or PyInstaller bundle."""
    root = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    return root / 'assets' / filename

from habitica_core import API, APIError, RateLimitError, DEMO, DEMO_HABITS, DEMO_DAILIES, split_tasks, visible_todos, matches, update_tracker, tracked_progress, daily_progress, task_id, progress, protect, load_settings, save_settings, display_signature, merge_task, changed_keys
try:
    from PySide6.QtCore import Qt, QRectF, QPoint, QTimer, QVariantAnimation, QEasingCurve, Signal, QObject
    from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QFont, QCursor, QFontDatabase, QIcon, QPixmap, QFontMetrics
    from PySide6.QtWidgets import (QApplication, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QScrollArea, QLineEdit, QDialog, QDialogButtonBox, QCheckBox, QSlider, QMessageBox, QSizeGrip, QComboBox, QSizePolicy, QStackedWidget)
except ImportError:
    if os.name=='nt':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,'PySide6 is required for this version. Open PowerShell in this folder and run: py -m pip install PySide6-Essentials\nThen reopen this file.','Habitica Progress Board',0x10)
    raise SystemExit('Install PySide6-Essentials first.')

from virtual_scroll import VirtualScroll, Row
from optimistic import Action, OptimisticState

CSS='''
QWidget { color: #30313a; font-size: 13px; }
QLabel { background: transparent; }
QLabel#muted { color: #686a75; font-size: 12px; }
QLabel#heading { font-size: 15px; font-weight: 600; }
QLabel#title { font-size: 14px; font-weight: 500; }
QLabel#group { color: #686a75; font-size: 12px; font-weight: 600; }
QLabel#metric { font-size: 16px; font-weight: 600; color: #56516e; }
QFrame#card { background: #fcfcfd; border: 1px solid #e7e7ed; border-radius: 15px; }
QFrame#row { background: transparent; border: none; border-radius: 9px; }
QFrame#row:hover { background: #f0f0f5; }
QPushButton { background: #f6f6f9; border: 1px solid #e4e4eb; border-radius: 10px; padding: 4px 9px; font-weight: 400; }
QPushButton:hover { background: #ededf4; border-color: #bfc1d0; }
QPushButton:pressed { background: #e5e4ef; }
QPushButton:disabled { color: #94949f; background: #f0f0f4; }
QPushButton#primary { background: #e9e6f3; border: 1px solid #d8d3e8; color: #51496c; }
QPushButton#check { background: #ffffff; border: 1px solid #b8b9c6; border-radius: 10px; padding: 0; font-size: 13px; }
QPushButton#check:hover { background: #ebe8f6; border-color: #9185b6; }
QPushButton#check[done="true"] { background: #dedbed; color: #50476f; border: 1px solid #c9c3df; }
QLineEdit { background: #fcfcfd; border: 1px solid #e3e3ea; border-radius: 10px; padding: 6px 10px; selection-background-color: #d4cee7; }
QLineEdit:focus { border-color: #b8aecf; }
QComboBox { background: #f7f7fa; border: 1px solid #e2e2ea; border-radius: 8px; padding: 4px 8px; min-width: 74px; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background: #fcfcfd; color: #30313a; selection-background-color: #e9e6f3; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 2px; }
QScrollBar::handle:vertical { background: #c7c6d2; border-radius: 3px; min-height: 25px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background: transparent; }
QDialog { background: #f8f8fb; }
'''

def label(text='',name=None):
    w=QLabel(str(text)); w.setTextFormat(Qt.TextFormat.PlainText); w.setWordWrap(True)
    if name: w.setObjectName(name)
    return w

def button(text, fn, name=None):
    w=QPushButton(text); w.setCursor(Qt.CursorShape.PointingHandCursor)
    if name: w.setObjectName(name)
    w.clicked.connect(lambda _=False:fn()); return w

def row_layout(parent=None):
    l=QHBoxLayout(parent) if parent is not None else QHBoxLayout(); l.setContentsMargins(0,0,0,0); l.setSpacing(8); return l

def spectrum(a,b,alpha=255):
    g=QLinearGradient(a,b)
    for pos,hex in [(0,'#dbbed3'),(.25,'#e6d5c2'),(.48,'#c2ddd5'),(.74,'#bdcde4'),(1,'#d2c3e1')]:
        c=QColor(hex); c.setAlpha(alpha); g.setColorAt(pos,c)
    return g

TABS=('todos','dailies','habits')
TAB_LABELS=('To-Dos','Dailies','Habits')
SEARCH_LABELS={'todos':'Find a To-Do…','dailies':'Find a Daily…','habits':'Find a habit…'}

class Switch(QWidget):
    def __init__(self,tab,callback):
        super().__init__(); self.tab=tab; self.pos=float(TABS.index(tab)); self.callback=callback
        self.setFixedHeight(34); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Switch between To-Dos, Dailies and Habits'); self.anim=QVariantAnimation(self); self.anim.setDuration(185); self.anim.setEasingCurve(QEasingCurve.Type.OutCubic); self.anim.valueChanged.connect(self.set_pos)
    def set_pos(self,v): self.pos=float(v); self.update()
    def choose(self,tab):
        self.tab=tab; self.anim.stop(); self.anim.setStartValue(self.pos); self.anim.setEndValue(float(TABS.index(tab))); self.anim.start(); self.callback(tab)
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self.anim.stop(); self.mouseMoveEvent(e)
    def mouseMoveEvent(self,e):
        if e.buttons() & Qt.MouseButton.LeftButton: self.set_pos(max(0,min(2,e.position().x()/max(1,self.width())*3-.5)))
    def mouseReleaseEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self.choose(TABS[max(0,min(2,int(e.position().x()/max(1,self.width())*3)))])
    def keyPressEvent(self,e):
        i=TABS.index(self.tab)
        if e.key() in (Qt.Key.Key_Left,Qt.Key.Key_Right,Qt.Key.Key_Space,Qt.Key.Key_Return): self.choose(TABS[max(0,i-1) if e.key()==Qt.Key.Key_Left else min(2,i+1) if e.key()==Qt.Key.Key_Right else (i+1)%3])
        else: super().keyPressEvent(e)
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); r=QRectF(self.rect()).adjusted(1,1,-1,-1); p.setPen(QPen(QColor('#dedee9'),1)); p.setBrush(QColor('#eeedf3')); p.drawRoundedRect(r,19,19)
        w=(r.width()-6)/3; thumb=QRectF(r.x()+3+w*self.pos,r.y()+3,w,r.height()-6)
        p.setBrush(QBrush(spectrum(thumb.topLeft(),thumb.bottomRight(),170))); p.setPen(QPen(QColor(255,255,255,230),1)); p.drawRoundedRect(thumb,16,16)
        for i,t in enumerate(TAB_LABELS):
            active=self.tab==TABS[i]; f=QFont(self.font()); f.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal); p.setFont(f); p.setPen(QColor('#303247' if active else '#67697c')); p.drawText(QRectF(r.x()+i*r.width()/3,r.y(),r.width()/3,r.height()),Qt.AlignmentFlag.AlignCenter,t)

class Progress(QWidget):
    def __init__(self,pct): super().__init__(); self.pct=max(0,min(100,pct)); self.setFixedHeight(6); self.setAccessibleName(f'{pct}% complete')
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(Qt.PenStyle.NoPen); r=QRectF(self.rect()); p.setBrush(QColor('#e9e7ee')); p.drawRoundedRect(r,3,3)
        if self.pct:
            fill=QRectF(0,0,r.width()*self.pct/100,r.height()); g=QLinearGradient(r.topLeft(),r.topRight()); g.setColorAt(0,QColor('#a59acb')); g.setColorAt(.48,QColor('#93b4c9')); g.setColorAt(1,QColor('#a2c6b5')); p.setBrush(QBrush(g)); p.drawRoundedRect(fill,min(3,fill.width()/2),3)

class DragLabel(QLabel):
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:
            self.offset=e.globalPosition().toPoint()-self.window().pos()
            e.accept()
    def mouseMoveEvent(self,e):
        if e.buttons() & Qt.MouseButton.LeftButton and hasattr(self,'offset'): self.window().move(e.globalPosition().toPoint()-self.offset)

class ResultBridge(QObject):
    finished=Signal(str,bool,object)

class Board(QWidget):
    def __init__(self,demo=False):
        super().__init__(); self.demo=demo; self.settings=load_settings(); self.api=None; self.tasks=copy.deepcopy(DEMO); self.habits=copy.deepcopy(DEMO_HABITS); self.dailies=copy.deepcopy(DEMO_DAILIES); self.tracker=update_tracker({},self.tasks,[]); self.busy=False; self.stale=False; self.sync_state=None; self.bridge=ResultBridge(self); self.bridge.finished.connect(self.poll,Qt.ConnectionType.QueuedConnection); self.pages={}; self.pending_button=None; self.active_button=None; self.counts={}; self.expanded=set(); self.first_checklist_initialized=False; self.tab='todos' if demo else self.settings.get('tab','todos'); self.tab=self.tab if self.tab in TABS else 'todos'; self.pin=bool(self.settings.get('pin',True)); self.surface=max(85,min(100,int(self.settings.get('qt_surface_v6',99)))); self.compact=False; self.old_size=None; self.last_status='Demo · not connected'; self.query={t:'' for t in TABS}
        self.setWindowTitle('Habitica Progress Board'); self.setWindowFlags(Qt.WindowType.Window|Qt.WindowType.FramelessWindowHint|(Qt.WindowType.WindowStaysOnTopHint if self.pin else Qt.WindowType.Widget)); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.setMinimumSize(325,280); self.setMouseTracking(True)
        layout=QVBoxLayout(self); layout.setContentsMargins(14,11,14,11); layout.setSpacing(8)
        head=row_layout(); brand=DragLabel(); brand.setFixedSize(22,22); brand.setCursor(Qt.CursorShape.SizeAllCursor); brand.setPixmap(QIcon(str(asset_path('HabiticaBoard.ico'))).pixmap(22,22)); head.addWidget(brand); title=DragLabel('HABITICA'); title.setStyleSheet('font-size: 13px; font-weight: 600;'); title.setCursor(Qt.CursorShape.SizeAllCursor); head.addWidget(title,1)
        for t,fn,tip in [('···',self.settings_dialog,'Settings'),('Pin' if not self.pin else 'Pinned',self.toggle_pin,'Always on top'),('−',self.toggle_compact,'Collapse / expand'),('×',self.close,'Close')]:
            b=button(t,fn); b.setToolTip(tip); head.addWidget(b)
            if tip=='Always on top': self.pin_btn=b
            if tip=='Collapse / expand': self.compact_btn=b
        layout.addLayout(head); self.switch=Switch(self.tab,self.change_tab); layout.addWidget(self.switch)
        self.search=QLineEdit(); self.search.setPlaceholderText(SEARCH_LABELS[self.tab]); self.search.setClearButtonEnabled(True); self.search.textChanged.connect(self.search_changed); layout.addWidget(self.search)
        self.section=row_layout(); self.section_title=label('', 'heading'); self.section_count=label('', 'muted'); self.section.addWidget(self.section_title,1); self.section.addWidget(self.section_count); layout.addLayout(self.section)
        self.summary,self.summary_layout=self.card(); self.summary_layout.setSpacing(5)
        metric=row_layout(); self.summary_caption=label('','muted'); self.summary_metric=label('','metric'); metric.addWidget(self.summary_caption,1); metric.addWidget(self.summary_metric); self.summary_layout.addLayout(metric)
        self.summary_bar=Progress(0); self.summary_layout.addWidget(self.summary_bar)
        info=row_layout(); self.summary_hint=label('','muted'); info.addWidget(self.summary_hint,1); self.reset_btn=button('Reset',self.reset_progress); self.reset_btn.setToolTip('Start a new To-Do tracking period'); info.addWidget(self.reset_btn); self.summary_layout.addLayout(info); layout.addWidget(self.summary)
        self.stack=QStackedWidget(); layout.addWidget(self.stack,1); self.classic_list="--classic-list" in sys.argv
        for tab in TABS:
            if not self.classic_list:
                scroll=VirtualScroll(); self.stack.addWidget(scroll); self.pages[tab]={"scroll":scroll}; continue
            scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); scroll.viewport().setAutoFillBackground(False)
            content=QWidget(); content.setAutoFillBackground(False); body=QVBoxLayout(content); body.setContentsMargins(0,1,2,3); body.setSpacing(7); body.addStretch(1); scroll.setWidget(content); self.stack.addWidget(scroll)
            self.pages[tab]={'scroll':scroll,'body':body,'sections':{}}
        self.scroll=self.pages[self.tab]['scroll']; self.stack.setCurrentWidget(self.scroll)
        self.search_timer=QTimer(self); self.search_timer.setSingleShot(True); self.search_timer.setInterval(180); self.search_timer.timeout.connect(self.apply_search)
        foot=row_layout(); self.status_label=label(self.last_status,'muted'); foot.addWidget(self.status_label,1); self.refresh_btn=button('↻  Refresh',self.refresh); foot.addWidget(self.refresh_btn); grip=QSizeGrip(self); grip.setToolTip('Drag to resize'); grip.setFixedSize(15,15); foot.addWidget(grip,0,Qt.AlignmentFlag.AlignBottom); layout.addLayout(foot)
        area=QApplication.primaryScreen().availableGeometry(); width=min(area.width(),max(325,int(self.settings.get('qt_width',405)))); height=min(area.height(),max(280,int(self.settings.get('qt_height',540)))); self.resize(width,height)
        x=int(self.settings.get('qt_x',area.right()-width-16)); y=int(self.settings.get('qt_y',area.top()+18)); self.move(max(area.left(),min(x,area.right()-width+1)),max(area.top(),min(y,area.bottom()-height+1)))
        self.render(); self.refresh_timer=QTimer(self); self.refresh_timer.timeout.connect(self.auto_refresh); self.schedule_refresh()
        if not demo and self.settings.get('uid') and self.settings.get('protected_token'):
            try: self.connect_account(self.settings['uid'],protect(self.settings['protected_token'],True))
            except Exception: self.set_status('Saved credentials unavailable. Open Settings to reconnect.',True)
    def paintEvent(self,e):
        dpr=self.devicePixelRatioF(); key=(self.width(),self.height(),dpr,self.surface)
        if getattr(self,'_background_key',None)==key:
            p=QPainter(self); p.drawPixmap(0,0,self._background); return
        pix=QPixmap(round(self.width()*dpr),round(self.height()*dpr)); pix.setDevicePixelRatio(dpr); pix.fill(Qt.GlobalColor.transparent)
        p=QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing); r=QRectF(self.rect()).adjusted(1,1,-1,-1); a=round(self.surface*255/100); g=QLinearGradient(r.topLeft(),r.bottomRight()); g.setColorAt(0,QColor(251,250,252,a)); g.setColorAt(.48,QColor(247,248,250,a)); g.setColorAt(1,QColor(249,247,251,a)); p.setBrush(QBrush(g)); p.setPen(QPen(QBrush(spectrum(r.topLeft(),r.bottomRight(),245)),1.6)); p.drawRoundedRect(r,24,24)
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(255,255,255,210),1)); p.drawRoundedRect(r.adjusted(2,2,-2,-2),22,22); p.end()
        self._background_key=key; self._background=pix; p=QPainter(self); p.drawPixmap(0,0,pix)
    def change_tab(self,tab):
        if tab==self.tab: return
        self.search_timer.stop(); self.tab=tab; self.scroll=self.pages[tab]['scroll']; self.stack.setCurrentWidget(self.scroll)
        self.search.blockSignals(True); self.search.setText(self.query[tab]); self.search.setPlaceholderText(SEARCH_LABELS[tab]); self.search.blockSignals(False); self.render()
    def search_changed(self,text):
        self.query[self.tab]=text; self.search_timer.start()
    def apply_search(self):
        text=self.query[self.tab]
        if self.tab in ('todos','dailies') and text.strip():
            source=self.tasks if self.tab=='todos' else self.dailies
            self.expanded.update(task_id(t) for t in source if t.get('checklist') and matches(t,text))
        self.render(); self.scroll.verticalScrollBar().setValue(0)
    def action(self,text,fn,name=None):
        def invoke():
            if self.stale:
                if self.cooling_down(): self.cooldown_status()
                else: self.set_status('Refresh before making another change.',True)
                return
            self.active_button=b
            try: fn()
            finally: self.active_button=None
        b=button(text,invoke,name); return b
    def track(self, completed=()):
        before=self.tracker; self.tracker=update_tracker(before,self.tasks,completed)
        if self.api and not self.demo and before!=self.tracker:
            self.settings.setdefault('todo_tracking_v7',{})[self.api.uid]=self.tracker
            self.persist()
    def reset_progress(self):
        if self.busy or self.stale: return
        if QMessageBox.question(self,'Reset To-Do progress?', 'Start a new tracking period with the current open To-Dos? Habitica tasks will not change.')!=QMessageBox.StandardButton.Yes: return
        if self.sync_state is not None:
            self.sync_state.reset(); self.persist_confirmed(); self.project_view()
        else: self.tracker={}; self.track(); self.render()
    def reconcile(self,layout,cache,specs):
        # Widgets are keyed by task ID, not by their position. No layout churn
        # or styling work on unchanged rows. Each group owns a separate cache.
        signatures={key:sig for key,sig,_ in specs}
        removed,changed=changed_keys({k:v[0] for k,v in cache.items()},signatures)
        for key in removed|changed:
            if key in cache:
                _,w=cache.pop(key); layout.removeWidget(w); w.hide(); w.deleteLater()
        for i,(key,sig,create) in enumerate(specs):
            if key not in cache:
                w=create(); cache[key]=(sig,w); layout.insertWidget(i,w)
            else:
                w=cache[key][1]
                if layout.indexOf(w)!=i:
                    layout.removeWidget(w); layout.insertWidget(i,w)
            if w.isHidden(): w.show()
    def group_spec(self,key,items,make,spacing=2):
        def create():
            f,rows=self.card(); rows.setSpacing(spacing); rows.setContentsMargins(5,4,5,4); f.row_cache={}; return f
        # Group container never depends on the number of rows.
        return (key,('group',spacing),create),items,make
    def render(self):
        if self.classic_list: return self.render_legacy()
        source={'todos':self.tasks,'dailies':self.dailies,'habits':self.habits}[self.tab]; search=self.query[self.tab].casefold().strip()
        self.section_title.setText(TAB_LABELS[TABS.index(self.tab)])
        self.summary.setVisible(self.tab!='habits' and not self.compact); self.reset_btn.setVisible(self.tab=='todos'); self.reset_btn.setEnabled(not self.busy and not self.stale)
        rows=[]
        # Estimation is cheap. Visible rows are remeasured with their actual Qt
        # layout, so long English/Chinese labels wrap rather than being clipped.
        def text_height(text,width,size=13):
            f=QFont(QApplication.font()); f.setPixelSize(size); fm=QFontMetrics(f)
            return fm.boundingRect(0,0,max(1,width),100000,int(Qt.TextFlag.TextWordWrap),str(text)).height()
        def check_height(t,w): return max(21,text_height(t.get('text',''),w-41))+8
        def estimate(t,w,kind,opened):
            if kind=='habit': return max(28,text_height(t.get('text',''),w-12-37*sum(bool(t.get(k)) for k in ('up','down'))))+6
            items=t.get('checklist') or []
            if kind=='plain': return check_height(t,w)
            if kind=='daily': return check_height(t,w-(34 if items else 0))+(sum(check_height(i,w)+3 for i in items) if opened else 0)
            n,total,pct=progress(t)
            h=18+max(25,text_height(t.get('text',''),w-56,14))+6+20+6+6
            if opened: h+=sum(check_height(i,w-22)+6 for i in items)
            if total and n==total: h+=34
            return h
        def add(t,kind,group=None,top=0,bottom=0,gap=7):
            tid=task_id(t); opened=tid in self.expanded
            make={'plain':self.quick_row,'checklist':self.checklist_card,'daily':self.daily_card,'habit':self.habit_card}[kind]
            rows.append(Row((kind,tid),display_signature(t,opened),lambda t=t,make=make:make(t),lambda w,t=t,kind=kind,opened=opened:estimate(t,w,kind,opened),group,gap,top,bottom))
        def group(items,kind,key,spacing):
            for i,t in enumerate(items):
                last=i==len(items)-1
                add(t,kind,key,5 if i==0 else 0,5 if last else 0,7 if last else spacing)
        if self.tab=='todos':
            n,total,pct=tracked_progress(self.tracker); self.summary_caption.setText(f'{n} / {total} To-Dos completed'); self.summary_hint.setText('Since tracking started · all To-Dos'); self.summary_metric.setText(f'{pct}%' if total else '—'); self.summary_bar.pct=pct; self.summary_bar.setAccessibleName(f'{pct}% To-Dos complete'); self.summary_bar.update()
            filtered=visible_todos(source,search); first=next((t for t in filtered if t.get('checklist')),None)
            if first and not self.first_checklist_initialized: self.expanded.add(task_id(first)); self.first_checklist_initialized=True
            self.section_count.setText(f'{len(filtered)} / {len(source)}' if search else f'{len(source)} open')
            for t in filtered:
                if t.get('checklist'): add(t,'checklist')
            group([t for t in filtered if not t.get('checklist')],'plain','plain',1)
        elif self.tab=='dailies':
            n,total,pct=daily_progress(source); self.summary_caption.setText(f'{n} / {total} due Dailies completed'); self.summary_hint.setText('Scheduled for the current Habitica day'); self.summary_metric.setText(f'{pct}%' if total else '—'); self.summary_bar.pct=pct; self.summary_bar.setAccessibleName(f'{pct}% due Dailies complete'); self.summary_bar.update()
            filtered=[t for t in source if matches(t,search)]; self.section_count.setText(f'{len(filtered)} / {len(source)}' if search else f'{len(source)} dailies')
            for title,items in [('Due today',[t for t in filtered if t.get('isDue') is True]),('Not scheduled today',[t for t in filtered if t.get('isDue') is False]),('Schedule unavailable',[t for t in filtered if t.get('isDue') not in (True,False)])]:
                if not items: continue
                rows.append(Row(('heading',title),title,lambda title=title:label(title,'group'),lambda w:16,gap=7)); group(items,'daily',title,2)
        else:
            filtered=[t for t in source if matches(t,search)]; self.section_count.setText(f'{len(filtered)} / {len(source)}' if search else f'{len(source)} habits'); group(filtered,'habit','habits',2)
        if not filtered:
            msg='No matching tasks.' if search else 'No tasks in this view.'; rows.append(Row(('empty',),msg,lambda:label(msg,'muted'),lambda w:20))
        self.pages[self.tab]['scroll'].set_rows(rows)
        self.refresh_btn.setEnabled(not self.busy and not self.cooling_down())
    def render_legacy(self):
        page=self.pages[self.tab]; body=page['body']; sections=page['sections']; source={'todos':self.tasks,'dailies':self.dailies,'habits':self.habits}[self.tab]; search=self.query[self.tab].casefold().strip()
        self.section_title.setText(TAB_LABELS[TABS.index(self.tab)])
        self.summary.setVisible(self.tab!='habits' and not self.compact); self.reset_btn.setVisible(self.tab=='todos'); self.reset_btn.setEnabled(not self.busy and not self.stale)
        specs=[]; groups=[]
        def add_group(key,items,make,spacing=2):
            if not items: return
            spec,items,make=self.group_spec(key,items,make,spacing); specs.append(spec); groups.append((key,items,make))
        if self.tab=='todos':
            n,total,pct=tracked_progress(self.tracker); self.summary_caption.setText(f'{n} / {total} To-Dos completed'); self.summary_hint.setText('Since tracking started · all To-Dos'); self.summary_metric.setText(f'{pct}%' if total else '—'); self.summary_bar.pct=pct; self.summary_bar.setAccessibleName(f'{pct}% To-Dos complete'); self.summary_bar.update()
            filtered=visible_todos(source,search); first=next((t for t in filtered if t.get('checklist')),None)
            if first and not self.first_checklist_initialized:
                self.expanded.add(task_id(first)); self.first_checklist_initialized=True
            self.section_count.setText(f'{len(filtered)} / {len(source)}' if search else f'{len(source)} open')
            for t in filtered:
                if t.get('checklist'):
                    specs.append((('todo',task_id(t)),display_signature(t,task_id(t) in self.expanded),lambda t=t:self.checklist_card(t)))
            add_group(('plain',),[t for t in filtered if not t.get('checklist')],self.quick_row,1)
        elif self.tab=='dailies':
            n,total,pct=daily_progress(source); self.summary_caption.setText(f'{n} / {total} due Dailies completed'); self.summary_hint.setText('Scheduled for the current Habitica day'); self.summary_metric.setText(f'{pct}%' if total else '—'); self.summary_bar.pct=pct; self.summary_bar.setAccessibleName(f'{pct}% due Dailies complete'); self.summary_bar.update()
            filtered=[t for t in source if matches(t,search)]; self.section_count.setText(f'{len(filtered)} / {len(source)}' if search else f'{len(source)} dailies')
            for title,group in [('Due today',[t for t in filtered if t.get('isDue') is True]),('Not scheduled today',[t for t in filtered if t.get('isDue') is False]),('Schedule unavailable',[t for t in filtered if t.get('isDue') not in (True,False)])]:
                if not group: continue
                specs.append((('heading',title),title,lambda title=title:label(title,'group'))); add_group(('daily',title),group,self.daily_card)
        else:
            filtered=[t for t in source if matches(t,search)]; self.section_count.setText(f'{len(filtered)} / {len(source)}' if search else f'{len(source)} habits'); add_group(('habits',),filtered,self.habit_card)
        if not filtered:
            msg='No matching tasks.' if search else 'No tasks in this view.'; specs.append((('empty',),msg,lambda:label(msg,'muted')))
        self.reconcile(body,sections,specs)
        for key,items,make in groups:
            f=sections[key][1]; rows=[(task_id(t),display_signature(t,task_id(t) in self.expanded),lambda t=t,make=make:make(t)) for t in items]
            self.reconcile(f.layout(),f.row_cache,rows)
        self.refresh_btn.setEnabled(not self.busy and not self.cooling_down())
    def card(self):
        f=QFrame(); f.setObjectName('card'); l=QVBoxLayout(f); l.setContentsMargins(11,9,11,9); l.setSpacing(6); return f,l
    def check_row(self,text,done,fn):
        r=QFrame(); r.setObjectName('row'); rl=QHBoxLayout(r); rl.setContentsMargins(6,4,6,4); rl.setSpacing(8)
        b=self.action('✓' if done else '',fn,'check'); b.setProperty('done','true' if done else 'false'); b.setFixedSize(21,21); b.setAccessibleName(('Uncheck ' if done else 'Complete ')+str(text)); b.setToolTip(b.accessibleName()); rl.addWidget(b)
        txt=label(text); ft=txt.font(); ft.setStrikeOut(done); txt.setFont(ft)
        if done: txt.setStyleSheet('color:#777784;')
        rl.addWidget(txt,1); return r
    def quick_row(self,t):
        return self.check_row(t.get('text','Untitled'),False,lambda tid=task_id(t):self.complete(tid))
    def checklist_card(self,t):
        f,l=self.card(); tid=task_id(t); items=t.get('checklist') or []; n,total,pct=progress(t); opened=tid in self.expanded
        h=row_layout(); h.addWidget(label(t.get('text','Untitled'),'title'),1); b=button('⌄' if opened else '›',lambda:self.toggle_checklist(tid)); b.setFixedSize(26,25); b.setToolTip('Expand / collapse checklist'); h.addWidget(b); l.addLayout(h)
        m=row_layout(); m.addWidget(label(f'{n} of {total} completed','muted'),1); m.addWidget(label(f'{pct}%','metric')); l.addLayout(m); l.addWidget(Progress(pct))
        if opened:
            for item in items:
                done=bool(item.get('completed')); iid=task_id(item)
                l.addWidget(self.check_row(item.get('text',''),done,lambda tid=tid,iid=iid,done=done:self.toggle_item(tid,iid,not done)))
        if total and n==total: l.addWidget(self.action('✓  Complete To-Do',lambda:self.complete(tid),'primary'))
        return f
    def toggle_checklist(self,tid):
        if tid in self.expanded: self.expanded.remove(tid)
        else: self.expanded.add(tid)
        self.render()
    def daily_card(self,t):
        f=QFrame(); f.setObjectName('row'); l=QVBoxLayout(f); l.setContentsMargins(0,0,0,0); l.setSpacing(3); tid=task_id(t); done=bool(t.get('completed'))
        h=row_layout(); h.addWidget(self.check_row(t.get('text','Untitled'),done,lambda:self.toggle_daily(tid,not done)),1)
        items=t.get('checklist') or []
        if items:
            b=button('⌄' if tid in self.expanded else '›',lambda:self.toggle_checklist(tid)); b.setFixedSize(26,25); b.setToolTip('Expand / collapse checklist'); h.addWidget(b)
        l.addLayout(h)
        if items and tid in self.expanded:
            for item in items:
                checked=bool(item.get('completed')); iid=task_id(item)
                row=self.check_row(item.get('text',''),checked,lambda tid=tid,iid=iid,checked=checked:self.toggle_item(tid,iid,not checked)); row.setEnabled(not done); l.addWidget(row)
        return f
    def toggle_daily(self,tid,desired):
        if self.stale: return
        if self.api: self.enqueue(Action('daily',tid,desired=desired))
        else:
            for t in self.dailies:
                if task_id(t)==tid: t['completed']=desired
            self.render()
    def habit_card(self,t):
        f=QFrame(); f.setObjectName('row'); l=QVBoxLayout(f); l.setContentsMargins(6,3,6,3); h=row_layout(); h.addWidget(label(t.get('text','Untitled')),1)
        for direction,sign in [('down','−'),('up','+')]:
            if t.get(direction):
                b=self.action(sign,lambda tid=task_id(t),d=direction:self.score_habit(tid,d)); b.setFixedSize(29,28); b.setAccessibleName(('Positive ' if direction=='up' else 'Negative ')+str(t.get('text','habit'))); h.addWidget(b)
        l.addLayout(h); return f
    def set_status(self,text,error=False):
        self.last_status=text
        if self.status_label.text()!=text: self.status_label.setText(text)
        style='color:#a13d5b' if error else 'color:#686b7e'
        if self.status_label.styleSheet()!=style: self.status_label.setStyleSheet(style)
    def cooling_down(self):
        return self.api.cooldown_remaining() if self.api else 0
    def cooldown_status(self,dropped=0):
        seconds=self.cooling_down()
        self.set_status(f'Rate limit · auto-sync after {seconds}s'+(f' · {dropped} unconfirmed cleared' if dropped else ''),True)
    def schedule_refresh(self):
        # One existing timer; after a 429 wake only once the server permits it.
        seconds=self.cooling_down()
        self.refresh_timer.start(min(2_000_000_000,max(1000,seconds*1000)) if seconds else 120000)
    def pending_status(self):
        n=len(self.sync_state.pending) if self.sync_state else 0
        if n: self.set_status(f'Syncing {n} change'+('s' if n!=1 else '')+'…')
        else: self.set_status('Habitica · synced '+time.strftime('%H:%M'))
    def project_view(self,view=None):
        view=self.sync_state.view() if view is None else view
        changed=view!=(self.tasks,self.habits,self.dailies,self.tracker)
        self.tasks,self.habits,self.dailies,self.tracker=view
        if changed: self.render()
        else:
            self.refresh_btn.setEnabled(not self.busy and not self.cooling_down())
            self.reset_btn.setEnabled(not self.busy and not self.stale)
    def persist_confirmed(self):
        # Never write optimistic completions into the durable progress record.
        if not self.api or self.demo: return
        records=self.settings.setdefault('todo_tracking_v7',{})
        if records.get(self.api.uid)!=self.sync_state.tracker:
            records[self.api.uid]=copy.deepcopy(self.sync_state.tracker); self.persist()
    def enqueue(self,action):
        if self.stale or self.sync_state is None: return
        try:
            view=self.sync_state.enqueue(action)
        except APIError as e:
            self.set_status(str(e),True); return
        # Start the network worker before rendering; it cannot modify UI state.
        self.dispatch(); self.pending_status()
        if action.kind!='habit': self.project_view(view)
    def dispatch(self):
        if self.busy or self.stale or not self.sync_state or not self.sync_state.pending: return
        action=self.sync_state.pending[0]; api=self.api
        self.run('write',lambda:action.send(api))
    def run(self,kind,fn):
        if self.busy: return
        self.busy=True; self.refresh_btn.setEnabled(False); self.reset_btn.setEnabled(False)
        if kind=='refresh': self.set_status('Refreshing…')
        else: self.pending_status()
        def worker():
            try: outcome=(kind,True,fn())
            except Exception as e: outcome=(kind,False,e if isinstance(e,APIError) else 'Unexpected error. Refresh before retrying.')
            try: self.bridge.finished.emit(*outcome)
            except RuntimeError: pass
        threading.Thread(target=worker,daemon=True).start()
    def poll(self,kind,ok,result):
        self.busy=False
        if ok:
            try:
                if kind=='refresh': self.sync_state.refresh(result)
                else: self.sync_state.acknowledge(result)
                self.persist_confirmed()
                # A remote edit may invalidate a later optimistic action.
                self.sync_state.view()
            except Exception as e:
                ok=False; result=str(e) if isinstance(e,APIError) else 'Unexpected task response.'
        self.stale=not ok
        if not ok:
            # Do not retry an ambiguous scoring write. Drop all unsent intents,
            # restore the last confirmed snapshot, and require a fresh read.
            dropped=self.sync_state.abort()
            if isinstance(result,RateLimitError):
                self.cooldown_status(dropped); self.schedule_refresh()
            else: self.set_status(str(result)+(f' · {dropped} unconfirmed change(s) cleared. Refresh.' if dropped else ' · Refresh.'),True)
            self.project_view(); return
        self.dispatch(); self.pending_status(); self.project_view()
    def refresh(self):
        if self.cooling_down():
            self.cooldown_status(); self.refresh_btn.setEnabled(False); self.schedule_refresh(); return
        if self.api and not self.busy: self.run('refresh',self.api.tasks)
        elif self.api: return
        else: self.render(); self.set_status('Demo · not connected')
    def auto_refresh(self):
        self.schedule_refresh()
        if self.api and not self.busy: self.refresh()
    def toggle_item(self,tid,iid,desired):
        if self.stale: return
        if self.api: self.enqueue(Action('item',tid,desired=desired,iid=iid))
        else:
            for t in self.tasks+self.dailies:
                if task_id(t)==tid:
                    for i in t.get('checklist',[]):
                        if task_id(i)==iid: i['completed']=desired
            self.render()
    def complete(self,tid):
        if self.stale: return
        t=next((x for x in self.tasks if task_id(x)==tid),None)
        if not t or any(not i.get('completed') for i in t.get('checklist',[]) or []): return
        if t.get('checklist') and QMessageBox.question(self,'Complete To-Do?', 'Mark this parent To-Do complete and remove it from the active list?')!=QMessageBox.StandardButton.Yes: return
        if self.api: self.enqueue(Action('complete',tid))
        else: self.tasks=[x for x in self.tasks if task_id(x)!=tid]; self.track([dict(t,completed=True)]); self.render(); self.set_status('Demo · To-Do completed')
    def score_habit(self,tid,direction):
        if self.stale: return
        h=next((x for x in self.habits if task_id(x)==tid),None)
        if not h or not h.get(direction): return
        if self.api: self.enqueue(Action('habit',tid,direction=direction))
        else: self.set_status('Demo · '+('+' if direction=='up' else '−')+' '+h.get('text',''))
    def clear_pages(self):
        for page in self.pages.values():
            if self.classic_list: self.reconcile(page['body'],page['sections'],[])
            else: page['scroll'].set_rows([])
    def connect_account(self,uid,token):
        self.clear_pages()
        self.api=API(uid,token); self.tasks=[]; self.habits=[]; self.dailies=[]; self.tracker=copy.deepcopy(self.settings.get('todo_tracking_v7',{}).get(uid,{})); self.sync_state=OptimisticState([],self.tracker); self.expanded.clear(); self.first_checklist_initialized=False; self.stale=True; self.render(); self.refresh()
    def toggle_pin(self):
        self.pin=not self.pin; self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,self.pin); self.show(); self.pin_btn.setText('Pinned' if self.pin else 'Pin'); self.persist()
    def toggle_compact(self):
        self.compact=not self.compact; self.compact_btn.setText('+' if self.compact else '−')
        if self.compact: self.old_size=self.size(); self.search.hide(); self.section_title.hide(); self.section_count.hide(); self.summary.hide(); self.stack.hide(); self.setMinimumHeight(130); self.resize(self.width(),130)
        else: self.search.show(); self.section_title.show(); self.section_count.show(); self.summary.setVisible(self.tab!='habits'); self.stack.show(); self.setMinimumHeight(280); self.resize(self.old_size or self.size())
    def edge_at(self,point):
        x,y=point.x(),point.y(); E=Qt.Edge; edges=E(0); m=8
        if x<m: edges|=E.LeftEdge
        elif x>self.width()-m: edges|=E.RightEdge
        if y<m: edges|=E.TopEdge
        elif y>self.height()-m: edges|=E.BottomEdge
        return edges
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:
            edge=self.edge_at(e.position())
            if edge:
                if not self.windowHandle() or not self.windowHandle().startSystemResize(edge):
                    self.manual_resize=(edge,e.globalPosition().toPoint(),self.geometry())
                e.accept(); return
        super().mousePressEvent(e)
    def mouseMoveEvent(self,e):
        E=Qt.Edge; edges=self.edge_at(e.position()); C=Qt.CursorShape
        if getattr(self,'manual_resize',None) and e.buttons() & Qt.MouseButton.LeftButton:
            edge,origin,r=self.manual_resize; delta=e.globalPosition().toPoint()-origin
            left,top,right,bottom=r.left(),r.top(),r.right(),r.bottom()
            if edge & E.LeftEdge: left=min(left+delta.x(),right-self.minimumWidth()+1)
            if edge & E.RightEdge: right=max(right+delta.x(),left+self.minimumWidth()-1)
            if edge & E.TopEdge: top=min(top+delta.y(),bottom-self.minimumHeight()+1)
            if edge & E.BottomEdge: bottom=max(bottom+delta.y(),top+self.minimumHeight()-1)
            self.setGeometry(left,top,right-left+1,bottom-top+1); return
        self.setCursor(C.SizeFDiagCursor if edges in (E.TopEdge|E.LeftEdge,E.BottomEdge|E.RightEdge) else C.SizeBDiagCursor if edges in (E.TopEdge|E.RightEdge,E.BottomEdge|E.LeftEdge) else C.SizeHorCursor if edges in (E.LeftEdge,E.RightEdge) else C.SizeVerCursor if edges in (E.TopEdge,E.BottomEdge) else C.ArrowCursor)
    def mouseReleaseEvent(self,e):
        self.manual_resize=None; super().mouseReleaseEvent(e)
    def settings_dialog(self):
        if self.busy:return
        self.refresh_timer.stop()
        d=QDialog(self); d.setWindowTitle('Habitica · Settings'); d.setMinimumWidth(370); l=QVBoxLayout(d); l.addWidget(label('Account & appearance','heading')); l.addWidget(label('Habitica → Settings → API. Credentials stay on this computer.','muted'))
        uid=QLineEdit(self.api.uid if self.api else self.settings.get('uid','')); token=QLineEdit(self.api.token if self.api else ''); token.setEchoMode(QLineEdit.EchoMode.Password); l.addWidget(label('User ID')); l.addWidget(uid); l.addWidget(label('API Token')); l.addWidget(token)
        remember=QCheckBox('Remember token (Windows encrypted storage)'); remember.setChecked(bool(self.settings.get('protected_token')) or os.name=='nt'); remember.setEnabled(os.name=='nt'); l.addWidget(remember)
        op=label(f'Glass surface opacity · {self.surface}%','title'); l.addWidget(op); s=QSlider(Qt.Orientation.Horizontal); s.setRange(85,100); s.setValue(self.surface); l.addWidget(s); old=self.surface
        def change(v): self.surface=v; op.setText(f'Glass surface opacity · {v}%'); self.update()
        s.valueChanged.connect(change); l.addWidget(label('Only the glass background changes; text remains opaque.','muted'))
        l.addWidget(label('Typography · Classic (v0.7.2)','muted'))
        def apply():
            self.settings['font_profile_v74']='classic'; self.persist(); d.accept()
        def connect():
            u,t=uid.text().strip(),token.text().strip()
            if not u or not t: QMessageBox.warning(d,'Missing credentials','Enter both User ID and API Token.'); return
            self.settings['uid']=u; self.settings.pop('protected_token',None)
            if remember.isChecked() and os.name=='nt':
                try:self.settings['protected_token']=protect(t)
                except Exception:QMessageBox.warning(d,'Credential storage','Token could not be encrypted; session only.')
            apply(); self.connect_account(u,t)
        def disconnect():
            self.clear_pages(); self.api=None; self.sync_state=None; self.stale=False; self.expanded.clear(); self.first_checklist_initialized=False; self.tasks=copy.deepcopy(DEMO); self.habits=copy.deepcopy(DEMO_HABITS); self.dailies=copy.deepcopy(DEMO_DAILIES); self.tracker=update_tracker({},self.tasks,[]); self.settings.pop('protected_token',None); self.settings.pop('uid',None); apply(); self.refresh()
        h=row_layout(); h.addWidget(button('Demo / disconnect',disconnect)); h.addStretch(); h.addWidget(button('Apply',apply)); h.addWidget(button('Connect',connect,'primary')); l.addLayout(h)
        if d.exec()!=QDialog.DialogCode.Accepted: self.surface=old; self.update()
        self.schedule_refresh()
    def persist(self):
        if self.demo:return
        size=self.old_size if self.compact and self.old_size else self.size(); self.settings.update(tab=self.tab,pin=self.pin,qt_surface_v6=self.surface,qt_width=size.width(),qt_height=size.height(),qt_x=self.x(),qt_y=self.y())
        try:save_settings(self.settings)
        except OSError:pass
    def closeEvent(self,e):
        if self.sync_state and self.sync_state.pending:
            self.set_status('Syncing pending changes · close after confirmation.'); e.ignore(); return
        self.persist(); self.search_timer.stop(); self.refresh_timer.stop(); super().closeEvent(e)

if __name__=='__main__':
    app=QApplication(sys.argv)
    available=set(QFontDatabase.families()); preferred=['Inter','Segoe UI Variable Text','Segoe UI Variable','Segoe UI','Microsoft YaHei UI','Noto Sans CJK SC','Arial','Sans Serif']
    font=QFont(); font.setFamilies([f for f in preferred if f in available] or ['Sans Serif']); font.setPixelSize(13); font.setWeight(QFont.Weight.Normal); font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias); app.setFont(font)
    app.setStyle('Fusion'); app.setStyleSheet(CSS)
    icon=asset_path('HabiticaBoard.ico')
    if icon.exists(): app.setWindowIcon(QIcon(str(icon)))
    b=Board('--demo' in sys.argv); b.show(); sys.exit(app.exec())
