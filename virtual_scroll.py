"""Bounded real-widget list: only nearby rows are instantiated.

Real QPushButtons/QLabels preserve the established stylesheet, typography,
wrapping and accessibility. The list itself owns geometry; offscreen rows
have only a data descriptor and a measured/estimated height.
"""
from dataclasses import dataclass
from collections import OrderedDict
from PySide6.QtCore import Qt, QRectF, QTimer, QVariantAnimation, QEasingCurve, QAbstractAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractScrollArea, QFrame
from virtual_geometry import offsets, visible_range, anchor_at, restore_anchor


@dataclass
class Row:
    key: object
    signature: object
    create: object
    estimate: object
    group: object = None
    gap: int = 0
    top_pad: int = 0
    bottom_pad: int = 0


class VirtualScroll(QAbstractScrollArea):
    def __init__(self):
        super().__init__(); self.rows=[]; self.keys=[]; self.edges=[0]; self.groups=[]; self.live={}; self.heights=OrderedDict(); self.estimates=OrderedDict(); self._updating=False
        self.viewport().setAutoFillBackground(False); self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Stable width avoids scrollbar appearance causing text reflow during measurement.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.verticalScrollBar().setSingleStep(28); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet('QAbstractScrollArea {border:none;background:transparent;} QScrollBar:vertical {background:transparent;width:7px;margin:2px;}')
        self.anim=QVariantAnimation(self); self.anim.setDuration(115); self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(lambda v:self.verticalScrollBar().setValue(round(v)))
        self.verticalScrollBar().sliderPressed.connect(self.anim.stop)
        self.reflow_timer=QTimer(self); self.reflow_timer.setSingleShot(True); self.reflow_timer.timeout.connect(self.reflow)
    def row_width(self,row): return max(1,self.viewport().width()-(14 if row.group is not None else 2))
    def height_key(self,row): return (row.key,row.signature,self.row_width(row))
    def height(self,row):
        key=self.height_key(row)
        height=self.heights.get(key)
        if height is None:
            height=self.estimates.get(key)
            if height is None:
                height=max(1,int(row.estimate(self.row_width(row)))); self.estimates[key]=height
                while len(self.estimates)>3000: self.estimates.popitem(last=False)
        return height+row.top_pad+row.bottom_pad+row.gap
    def remember_height(self,row,height):
        key=self.height_key(row); self.heights[key]=height; self.heights.move_to_end(key)
        while len(self.heights)>3000: self.heights.popitem(last=False)
    def recalculate(self, anchor, old_top):
        self.edges=offsets(self.height(row) for row in self.rows)
        bar=self.verticalScrollBar(); bar.setPageStep(max(1,self.viewport().height())); bar.setRange(0,max(0,self.edges[-1]-self.viewport().height()))
        bar.setValue(restore_anchor(self.keys,self.edges,anchor,old_top,self.viewport().height()))
    def set_rows(self,rows):
        if [(r.key,r.signature,r.group,r.gap,r.top_pad,r.bottom_pad) for r in rows]==[(r.key,r.signature,r.group,r.gap,r.top_pad,r.bottom_pad) for r in self.rows]: return
        self.anim.stop(); top=self.verticalScrollBar().value(); anchor=anchor_at(self.keys,self.edges,top)
        self.rows=rows; self.keys=[r.key for r in rows]; self.groups=[]
        for i,r in enumerate(rows):
            if r.group is None: continue
            if i and rows[i-1].group==r.group: self.groups[-1]=(self.groups[-1][0],i)
            else: self.groups.append((i,i))
        self._updating=True
        try: self.recalculate(anchor,top)
        finally: self._updating=False
        self.materialize()
    def reflow(self):
        if self._updating or not self.isVisible(): return
        top=self.verticalScrollBar().value(); anchor=anchor_at(self.keys,self.edges,top)
        self._updating=True
        try: self.recalculate(anchor,top)
        finally: self._updating=False
        self.materialize()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'reflow_timer'): self.reflow_timer.start(0)
    def showEvent(self,event):
        super().showEvent(event)
        if hasattr(self,'reflow_timer'): self.reflow_timer.start(0)
    def hideEvent(self,event):
        self.anim.stop(); super().hideEvent(event)
    def scrollContentsBy(self,dx,dy):
        if not self._updating: self.materialize()
    def materialize(self):
        if self._updating or not self.isVisible(): return
        self._updating=True
        try:
            # A small overscan keeps the next few rows ready during fast scrolling.
            # Remeasure the visible widgets, preserving the top row as heights settle.
            for attempt in range(3):
                top=self.verticalScrollBar().value(); vh=self.viewport().height(); anchor=anchor_at(self.keys,self.edges,top)
                indices=visible_range(self.edges,top,vh,90); wanted={self.rows[i].key:self.rows[i] for i in indices}
                for key,(sig,w) in list(self.live.items()):
                    if key not in wanted or wanted[key].signature!=sig:
                        w.hide(); w.deleteLater(); del self.live[key]
                changed=False
                for i in indices:
                    row=self.rows[i]; width=self.row_width(row)
                    if row.key not in self.live:
                        w=row.create(); w.setParent(self.viewport()); w.ensurePolished(); self.live[row.key]=(row.signature,w)
                    else: w=self.live[row.key][1]
                    if getattr(w,"_measured_width",None)==width and self.height_key(row) in self.heights: continue
                    w.resize(width,max(1,w.sizeHint().height()))
                    layout=w.layout()
                    # Qt computes the actual wrapped height from the existing layout.
                    if layout is not None and layout.hasHeightForWidth(): h=layout.totalHeightForWidth(width)
                    elif w.hasHeightForWidth(): h=w.heightForWidth(width)
                    else: h=w.sizeHint().height()
                    h=max(1,h,w.minimumSizeHint().height()); w._measured_width=width
                    if self.heights.get(self.height_key(row))!=h:
                        self.remember_height(row,h); changed=True
                if changed:
                    bar=self.verticalScrollBar(); at_end=bar.maximum()>0 and top==bar.maximum()
                    self.recalculate(anchor,top)
                    if at_end: bar.setValue(bar.maximum())
                else: break
            top=self.verticalScrollBar().value()
            final_indices=visible_range(self.edges,top,self.viewport().height(),90)
            final_keys={self.rows[i].key for i in final_indices}
            for key,(sig,w) in list(self.live.items()):
                if key not in final_keys: w.hide(); w.deleteLater(); del self.live[key]
            for i in final_indices:
                row=self.rows[i]
                if row.key not in self.live: continue
                w=self.live[row.key][1]; x=6 if row.group is not None else 0
                h=self.edges[i+1]-self.edges[i]-row.top_pad-row.bottom_pad-row.gap
                w.setGeometry(x,self.edges[i]-top+row.top_pad,self.row_width(row),max(1,h))
                if w.isHidden(): w.show()
            self.viewport().update()
            if any(self.rows[i].key not in self.live for i in final_indices): self.reflow_timer.start(0)
        finally: self._updating=False
    def paintEvent(self,event):
        # QAbstractScrollArea remaps viewport paint events to this method.
        painter=QPainter(self.viewport()); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#e7e7ed"),1)); painter.setBrush(QColor("#fcfcfd"))
        top=self.verticalScrollBar().value(); width=self.viewport().width()-2
        for first,last in self.groups:
            y=self.edges[first]-top; h=self.edges[last+1]-self.rows[last].gap-self.edges[first]
            if y+h>=0 and y<=self.viewport().height():
                painter.drawRoundedRect(QRectF(.5,y+.5,max(1,width-1),max(1,h-1)),15,15)
    def wheelEvent(self,event):
        bar=self.verticalScrollBar(); pixels=event.pixelDelta().y(); angle=event.angleDelta().y()
        if pixels:
            self.anim.stop(); bar.setValue(bar.value()-pixels)
        elif angle:
            target=self.anim.endValue() if self.anim.state()==QAbstractAnimation.State.Running else bar.value()
            target=max(bar.minimum(),min(bar.maximum(),round(target-angle/120*84)))
            self.anim.stop(); self.anim.setStartValue(bar.value()); self.anim.setEndValue(target); self.anim.start()
        else: super().wheelEvent(event); return
        event.accept()
