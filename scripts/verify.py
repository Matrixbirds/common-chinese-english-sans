"""Validate actual OpenType shaping and preservation of the open-source base."""
import argparse
import io
import json
from pathlib import Path
import uharfbuzz as hb
from fontTools.ttLib import TTFont


def verify(base, output):
    plan = json.loads((output / 'plan.json').read_text())
    report = json.loads((output / 'build-report.json').read_text())
    original = TTFont(base)
    filename = plan['config']['postscriptName']
    checked = []
    for suffix in ['otf', 'woff2']:
        font = TTFont(output / (filename + '.' + suffix))
        assert font.getBestCmap() == original.getBestCmap(), 'Base character mappings changed'
        if 'GSUB' in original:
            original_features = {r.FeatureTag for r in original['GSUB'].table.FeatureList.FeatureRecord}
            features = {r.FeatureTag for r in font['GSUB'].table.FeatureList.FeatureRecord}
            assert original_features <= features, 'Original font features removed'
        font.recalcBBoxes = False
        font.recalcTimestamp = False
        font.flavor = None
        raw = io.BytesIO()
        font.save(raw)
        face = hb.Face(raw.getvalue())
        hfont = hb.Font(face)
        hb.ot_font_set_funcs(hfont)
        def shape(text, on=True):
            buffer = hb.Buffer()
            buffer.add_str(text)
            buffer.guess_segment_properties()
            hb.shape(hfont, buffer, {'rclt': on})
            return [font.getGlyphName(g.codepoint) for g in buffer.glyph_infos]
        for rule in plan['rules']:
            assert shape(rule['text']) == [report['glyphs'][rule['text']]], f"{suffix}: rule failed: {rule['text']}"
        original_hfont = hb.Font(hb.Face(base.read_bytes()))
        hb.ot_font_set_funcs(original_hfont)
        generated = set(report['glyphs'].values())
        for text in ['我是中国人。', '我喜欢学习中文。', '请打开浏览器，搜索附近的地铁站。', '花钱和花园', '长大以后', '中华人民共和国', '东西南北']:
            assert '.notdef' not in shape(text), f'Missing glyph: {text}'
            assert not (set(shape(text, False)) & generated), 'Annotation switch failed'
            original_buffer = hb.Buffer()
            original_buffer.add_str(text)
            original_buffer.guess_segment_properties()
            hb.shape(original_hfont, original_buffer, {'rclt': False})
            assert shape(text, False) == [original.getGlyphName(g.codepoint) for g in original_buffer.glyph_infos], 'Base shaping changed'
        assert report['glyphs']['中国人'] in shape('我是中国人。'), 'Whole-word Chinese rule failed'
        checked.append(suffix)
    result = {'status': 'passed', 'formats': checked, 'rulesCheckedPerFormat': len(plan['rules']), 'characterCoverage': len(original.getBestCmap()), 'checks': ['whole-word annotations', 'protection', 'disabled annotations', 'base coverage', 'base layout features']}
    (output / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    verify(args.base, args.out)
