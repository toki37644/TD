from pathlib import Path
from time import monotonic
panel_qa_view = op('/project1/viewport')
panel_qa_runtime = op('/project1/runtime').module
panel_qa_runtime.reset()
panel_qa_log = Path.home()/'Documents'/'ChatGPT'/'空'/'.echo-work'/'captures'/'panel_qa.txt'
panel_qa_log.write_text('',encoding='utf-8')

def event_qa(x,y,down):
    panel_qa_view.interactMouse(x,y,left=down)

def record_qa(stage):
    s = panel_qa_runtime.survey
    with panel_qa_log.open('a',encoding='utf-8') as f:
        f.write(repr((stage,s.down,s.seen,s.route,s.strikes,panel_qa_runtime.panel_input(),monotonic(),s.pulse))+'\n')

def series_qa():
    stages = [
        (.20,record_qa,('held',)),(.65,event_qa,(.62,.5,False)),
        (.10,record_qa,('released',)),(1.4,record_qa,('revealed',)),
        (.1,event_qa,(.82,.39,True)),(.1,event_qa,(.82,.39,False)),
        (.2,event_qa,(.39,.43,True)),(.1,event_qa,(.39,.43,False)),
        (.2,event_qa,(.63,.66,True)),(.1,event_qa,(.63,.66,False)),(.1,record_qa,('route',)),
        (.2,event_qa,(.93,.07,True)),(.1,event_qa,(.93,.07,False)),(.1,record_qa,('reset',))]
    def next_event(index, since):
        duration, callback, values = stages[index]
        if monotonic()-since < duration:
            run("args[0](args[1],args[2])",next_event,index,since,delayFrames=1)
        else:
            callback(*values)
            if index+1 < len(stages):
                run("args[0](args[1],args[2])",next_event,index+1,monotonic(),delayFrames=1)
    event_qa(.62,.50,True)
    next_event(0,monotonic())
series_qa()
