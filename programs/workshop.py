"""Mosslight Works — little makers, unlikely inventions and gifts next door.

Params: worlds=1|2, seed=INT, demo=0|1, show=build|delivery|biscuit|tea.
Keys: Space next story; 1 build; 2 delivery; 3 biscuit; 4 tea; p pause; r reset.
A requested story starts after the current story finishes, preserving handoffs.
"""
from pixoolib.runtime import Program
from pixoolib.workshop.story import Story
from pixoolib.workshop.paint import Painter


class Workshop(Program):
    DESCRIPTION = 'Mosslight Works — tiny makers, mischief, and gifts next door'
    FPS = 8.0
    DEVICE_BRIGHTNESS = 20
    MAX_WORLDS = 2

    def setup(self):
        unknown=set(self.params)-{'worlds','seed','demo','show'}
        if unknown:raise ValueError('unknown workshop parameter: '+', '.join(sorted(unknown)))
        self.world_count=int(self.params.get('worlds','1'))
        demo=self.params.get('demo','0')
        if demo not in ('0','1'):raise ValueError('demo must be 0 or 1')
        self.story=Story(self.world_count,int(self.params.get('seed','7')),demo=='1',self.params.get('show'))
        self.painter=Painter(self.world_count)

    def update(self,dt,events):
        for event in events:
            if event.kind!='key':continue
            if event.key in ('space',' '):self.story.request()
            elif event.key in ('1','2','3','4'):
                self.story.request(('build','delivery','biscuit','tea')[int(event.key)-1])
            elif event.key=='p':self.story.paused=not self.story.paused
            elif event.key=='r':self.setup()
        self.story.update(dt)

    def render(self):
        return self.painter.render(self.story)[0]

    def render_worlds(self):
        return self.painter.render(self.story)

    def status(self):
        names={'build':'An unlikely invention','delivery':'A gift next door' if self.world_count==2 else 'A gift for the workshop',
               'biscuit':'The biscuit bandit' if not self.story._friendly_before else 'A friend brings biscuits',
               'tea':'Umbrella tea','idle':'A quiet moment'}
        text=names[self.story.episode]
        if self.story.paused:text+=' · paused'
        if self.story.pending:text+=' · next: '+self.story.pending
        return text+' | Space next · 1–4 stories · p pause · r reset · q quit'
