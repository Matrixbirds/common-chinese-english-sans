"""Font binary backend. Semantic decisions and rule order come from the TS plan."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools import subset


def merge_gsub(old, new):
    """Append generated lookups while preserving original scripts and features."""
    if old is None:
        return new
    old, new = old.table, new.table
    offset = len(old.LookupList.Lookup)
    old.LookupList.Lookup.extend(new.LookupList.Lookup)
    old.LookupList.LookupCount = len(old.LookupList.Lookup)
    indices = {}
    for i, record in enumerate(new.FeatureList.FeatureRecord):
        record.Feature.LookupListIndex = [n + offset for n in record.Feature.LookupListIndex]
        match = next((j for j, r in enumerate(old.FeatureList.FeatureRecord) if r.FeatureTag == record.FeatureTag), None)
        if match is None:
            match = len(old.FeatureList.FeatureRecord)
            old.FeatureList.FeatureRecord.append(record)
        else:
            feature = old.FeatureList.FeatureRecord[match].Feature
            feature.LookupListIndex.extend(record.Feature.LookupListIndex)
            feature.LookupCount = len(feature.LookupListIndex)
        indices[i] = match
    old.FeatureList.FeatureCount = len(old.FeatureList.FeatureRecord)
    for record in new.ScriptList.ScriptRecord:
        if not any(r.ScriptTag == record.ScriptTag for r in old.ScriptList.ScriptRecord):
            for lang in [record.Script.DefaultLangSys] + [r.LangSys for r in record.Script.LangSysRecord]:
                if lang:
                    lang.FeatureIndex = [indices[i] for i in lang.FeatureIndex]
            old.ScriptList.ScriptRecord.append(record)
    # Expose annotations to each language without removing its existing layout features.
    additions = set(indices.values())
    for record in old.ScriptList.ScriptRecord:
        for lang in [record.Script.DefaultLangSys] + [r.LangSys for r in record.Script.LangSysRecord]:
            if lang:
                lang.FeatureIndex = sorted(set(lang.FeatureIndex) | additions)
                lang.FeatureCount = len(lang.FeatureIndex)
    old.ScriptList.ScriptRecord.sort(key=lambda r: r.ScriptTag)
    old.ScriptList.ScriptCount = len(old.ScriptList.ScriptRecord)
    # OpenType requires feature records sorted by tag; remap references after sorting.
    records = old.FeatureList.FeatureRecord
    order = sorted(range(len(records)), key=lambda i: records[i].FeatureTag)
    remap = {before: after for after, before in enumerate(order)}
    old.FeatureList.FeatureRecord = [records[i] for i in order]
    for record in old.ScriptList.ScriptRecord:
        for lang in [record.Script.DefaultLangSys] + [r.LangSys for r in record.Script.LangSysRecord]:
            if lang:
                lang.FeatureIndex = sorted(remap[i] for i in lang.FeatureIndex)
                if lang.ReqFeatureIndex != 0xFFFF:
                    lang.ReqFeatureIndex = remap[lang.ReqFeatureIndex]
    from fontTools.ttLib import newTable
    table = newTable('GSUB')
    table.table = old
    return table


def build(base, plan_path, output):
    plan = json.loads(plan_path.read_text())
    if plan.get('schema') != 1:
        raise ValueError('Unsupported plan schema')
    if hashlib.sha256(base.read_bytes()).hexdigest() != plan['baseSha256']:
        raise ValueError('Plan and base font do not match')
    config, rules = plan['config'], plan['rules']
    font = TTFont(base, recalcTimestamp=False)
    if 'CFF ' not in font:
        raise ValueError('This backend supports static CFF OTF fonts only')
    if any(tag in font for tag in ['fvar', 'CFF2']):
        raise ValueError('Variable fonts are not supported by this backend')
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    top = font['CFF '].cff.topDictIndex[0]
    cs = top.CharStrings
    original_bbox = list(top.FontBBox)
    original_gsub = copy.deepcopy(font['GSUB']) if 'GSUB' in font else None
    used = {int(n[3:]) for n in top.charset if n.startswith('cid')}
    free = iter(i for i in range(1, 65535) if i not in used)
    index = {name: i for i, name in enumerate(top.charset)}
    words, singles, glyphs, small = [], [], {}, []
    if len(top.charset) + len(rules) > 65535:
        raise ValueError('Glyph capacity exceeded')
    for i, rule in enumerate(rules):
        text, annotation = rule['text'], rule['annotation']
        bases = [cmap[ord(c)] for c in text]
        letters = [cmap[ord(c)] for c in annotation]
        width = sum(font['hmtx'][g][0] for g in bases)
        ew = sum(font['hmtx'][g][0] for g in letters)
        scale = min(config['annotationScale'], (width - 70) / max(ew, 1))
        if letters and scale < .2:
            small.append({'text': text, 'annotation': annotation, 'scale': scale})
        pen = T2CharStringPen(width, gs)
        x = 0
        for g in bases:
            gs[g].draw(TransformPen(pen, (1, 0, 0, 1, x, 0)))
            x += font['hmtx'][g][0]
        x = (width - ew * scale) / 2
        for g in letters:
            gs[g].draw(TransformPen(pen, (scale, 0, 0, scale, x, config['annotationBaseline'])))
            x += font['hmtx'][g][0] * scale
        name = ('cid%05d' % next(free)) if hasattr(top, 'ROS') else 'english%05d' % i
        glyphs[text] = name
        charstring = pen.getCharString(private=cs[bases[0]].private, globalSubrs=top.GlobalSubrs)
        if hasattr(top, 'FDSelect'):
            top.FDSelect.gidArray.append(top.FDSelect.gidArray[index[bases[0]]])
        cs.charStrings[name] = len(cs.charStringsIndex)
        cs.charStringsIndex.append(charstring)
        top.charset.append(name)
        font['hmtx'][name] = (width, 0)
        if 'vmtx' in font:
            font['vmtx'][name] = (1600, 0)
        (singles if len(text) == 1 else words).append('sub ' + ' '.join(bases) + ' by ' + name + ';')
    font.setGlyphOrder(top.charset)
    ps, family = config['postscriptName'], config['family']
    font['CFF '].cff.fontNames = [ps]
    top.FullName, top.FamilyName = family + ' Regular', family
    feature = 'languagesystem DFLT dflt;\nlanguagesystem hani dflt;\n'
    feature += 'lookup EnglishWords {\n' + '\n'.join(words) + '\n} EnglishWords;\n'
    feature += 'lookup EnglishChars {\n' + '\n'.join(singles) + '\n} EnglishChars;\n'
    feature += 'feature rclt { lookup EnglishWords; lookup EnglishChars; } rclt;'
    addOpenTypeFeaturesFromString(font, feature)
    font['GSUB'] = merge_gsub(original_gsub, font['GSUB'])
    for record in font['name'].names:
        values = {1: family, 2: 'Regular', 3: family + ' ' + config['version'], 4: family + ' Regular', 5: 'Version ' + config['version'], 6: ps, 16: family, 17: 'Regular'}
        if record.nameID in values:
            record.string = values[record.nameID].encode(record.getEncoding(), errors='replace')
    ascent = max(font['hhea'].ascent, config['annotationBaseline'] + 410)
    font['hhea'].ascent = ascent
    font['OS/2'].sTypoAscender = max(font['OS/2'].sTypoAscender, ascent)
    font['OS/2'].usWinAscent = max(font['OS/2'].usWinAscent, ascent)
    font.recalcBBoxes = False
    top.FontBBox = [min(original_bbox[0], -1000), original_bbox[1], max(original_bbox[2], max(font['hmtx'][g][0] for g in glyphs.values())), max(original_bbox[3], ascent)]
    font['hhea'].advanceWidthMax = max(w for w, _ in font['hmtx'].metrics.values())
    # Explicit build timestamp for repeatable artifacts; Mac epoch offset.
    font['head'].created = font['head'].modified = config['buildEpoch'] + 2082844800
    output.mkdir(parents=True, exist_ok=True)
    font.save(output / (ps + '.otf'))
    font.flavor = 'woff2'
    font.save(output / (ps + '.woff2'))
    report = {'version': config['version'], 'baseSha256': plan['baseSha256'], 'baseCharacterCoverage': len(cmap), 'annotatedForms': sum(r['mode'] == 'annotate' for r in rules), 'protectedForms': sum(r['mode'] == 'protect' for r in rules), 'glyphs': glyphs, 'smallAnnotations': small}
    (output / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    # A lightweight demo font, retaining all rules whose input characters are present.
    preview = TTFont(output / (ps + '.otf'), recalcTimestamp=False)
    options = subset.Options()
    options.layout_features = ['*']
    options.name_IDs = ['*']
    options.name_languages = ['*']
    options.name_legacy = True
    sub = subset.Subsetter(options=options)
    chars = ''.join(r['text'] for r in rules) + '。！？、，；：' + ''.join(chr(i) for i in range(32, 127))
    sub.populate(unicodes={ord(c) for c in chars})
    sub.subset(preview)
    preview.flavor = 'woff2'
    preview.save(output / 'preview-font.woff2')
    print(f"Compiled {report['annotatedForms']} annotations, {report['protectedForms']} protections")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['inspect', 'build'])
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--plan', type=Path)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    if args.command == 'inspect':
        f = TTFont(args.base)
        if 'CFF ' not in f or 'fvar' in f:
            raise ValueError('Expected a static CFF OTF base font')
        print(json.dumps({'codepoints': list(f.getBestCmap()), 'glyphs': len(f.getGlyphOrder())}))
    else:
        if args.plan is None or args.out is None:
            p.error('build requires --plan and --out')
        build(args.base, args.plan, args.out)
