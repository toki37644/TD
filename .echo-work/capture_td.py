"""Run in the TouchDesigner Textport to exercise the embedded runtime and save actual TOP images."""
from pathlib import Path
import traceback


def capture_echo():
    dest = Path.home() / 'Documents' / 'ChatGPT' / '空' / '.echo-work' / 'captures'
    dest.mkdir(exist_ok=True)
    report = []
    runtime = op('/project1/runtime').module
    final = op('/project1/final_image')
    shader = op('/project1/starfield')
    mix = op('/project1/motif_mix')
    sim = runtime.Survey(0.)
    runtime.paused_for_capture = True
    center = (.626, .50)
    def picture(name, vectors):
        runtime.apply(vectors)
        shader.cook(force=True)
        final.cook(force=True)
        assert (final.width,final.height) == (1200,675)
        assert not shader.errors(), shader.errors()
        final.save(str(dest / (name+'.png')))
        report.append(name+' '+repr(vectors))
    try:
        picture('01_idle', sim.advance(1.0, center, False))
        for t in (1.05,1.13,1.25,1.5,1.75):
            hover = sim.advance(t, (.553,.51), True)
        picture('02_hover', hover)
        sim.button(2.,True,center)
        picture('03_charge',sim.advance(2.8,center,True))
        sim.button(2.9,False,center)
        scan = sim.advance(3.43,center,True)
        assert 0 < sum(sim.seen) < 3, sim.seen
        picture('04_scan',scan)
        picture('05_discovery',sim.advance(5.8,center,False))
        assert sim.seen == [True, True, True]
        for i, idx in enumerate((2,0,1)):
            pt=runtime.BEACONS[idx]
            sim.button(6.+i*.5,True,pt)
            sim.button(6.08+i*.5,False,pt)
        assert sim.route == [2,0,1]
        motif = sim.advance(7.82, (.415,.43), False)
        assert motif[4][2] > .7, motif[4]
        picture('06_motif',motif)
        mix.cook(force=True)
        audio = mix.numpyArray()
        audio_peak = float(abs(audio).max())
        assert audio_peak > .05, audio_peak
        speakers = op('/project1/speaker_output')
        assert not speakers.errors(), speakers.errors()
        report.append('audio signal peak '+str(audio_peak))
        picture('07_route',sim.advance(9.6,center,False))
        sim.button(10.,True,(.93,.07))
        sim.button(10.08,False,(.93,.07))
        assert sum(sim.seen)==0 and sim.route==[] and sim.motif==[]
        sim.button(10.5, True, center)
        sim.button(11.1, False, center)
        sim.advance(13.85, center, False)
        assert all(sim.seen)
        for i, idx in enumerate((0,1,2)):
            pt = runtime.BEACONS[idx]
            sim.button(14.0+i*.5, True, pt)
            sim.button(14.08+i*.5, False, pt)
        assert sim.route == [0, 1, 2]
        alternate = sim.advance(15.82, center, False)
        assert alternate[4][0] > .7, alternate[4]
        picture('08_alternate_route', alternate)
        # Identical 3-second timestamps isolate the effect of cursor position.
        for name, point in (('09_planet_left',(.15,.29)), ('10_planet_right',(.87,.78))):
            demonstration = runtime.Survey(0.)
            for t in (1.,1.25,1.5,1.75,2.,2.25,2.5,2.75,3.):
                vectors = demonstration.advance(t,point,True)
            assert abs(vectors[0][1]-point[0]) < .001 and abs(vectors[0][2]-point[1]) < .001
            picture(name, vectors)
        # The released wave reaches the planet center at the same instant as comparison 10.
        scan_light = runtime.Survey(0.)
        planet = (.84,.68)
        released = 3. - runtime.distance(center, planet)/runtime.WAVE_SPEED
        scan_light.button(released-.8,True,center)
        scan_light.button(released,False,center)
        for t in (2.45,2.6,2.75,3.):
            vectors = scan_light.advance(t,(.87,.78),True)
        assert abs(vectors[1][2] - runtime.distance(center,planet)) < .001
        picture('11_planet_scanlight', vectors)
        report.append('PASS idle, hover, charge, partial scan, persistent discoveries, the C-A-B and A-B-C motifs, audio signal, reset.')
    except Exception:
        report.append(traceback.format_exc())
        raise
    finally:
        runtime.paused_for_capture = False
        runtime.reset()
        (dest/'qa.txt').write_text('\n'.join(report),encoding='utf-8')


capture_echo()
