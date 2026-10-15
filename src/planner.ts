export interface Entry { hanzi: string; annotation: string; english?: string }
export interface Rule { text: string; annotation: string; mode: 'annotate' | 'protect' }
export function entries(value: unknown, protection = false): Entry[] {
  if (!Array.isArray(value)) throw new Error('Word list must be an array');
  return value.map((raw: unknown, i) => {
    if (!raw || typeof raw !== 'object') throw new Error(`Invalid entry ${i}`);
    const row = raw as Record<string, unknown>;
    if (typeof row.hanzi !== 'string' || !/^[\u3400-\u9fff]{1,16}$/u.test(row.hanzi)) throw new Error(`Invalid Han text at entry ${i}`);
    if (typeof row.annotation !== 'string' || (!protection && !row.annotation.trim()) || !/^[\x20-\x7e]*$/.test(row.annotation)) throw new Error(`Invalid annotation for ${row.hanzi}`);
    if (protection && row.annotation !== '') throw new Error(`Protection must have no annotation: ${row.hanzi}`);
    return { hanzi: row.hanzi, annotation: row.annotation };
  });
}
export function plan(vocabulary: Entry[], protection: Entry[], coverage: Set<number>, baseGlyphs: number): Rule[] {
  const map = new Map<string, Rule>();
  for (const [rows, mode] of [[vocabulary, 'annotate'], [protection, 'protect']] as const) {
    for (const row of rows) {
      if (map.has(row.hanzi)) throw new Error(`Duplicate or conflicting rule: ${row.hanzi}`);
      for (const c of row.hanzi + row.annotation) {
        if (!coverage.has(c.codePointAt(0)!)) throw new Error(`Base font lacks ${JSON.stringify(c)} in ${row.hanzi}`);
      }
      map.set(row.hanzi, { text: row.hanzi, annotation: row.annotation, mode });
    }
  }
  if (baseGlyphs + map.size > 65535) throw new Error('OpenType glyph capacity exceeded');
  return [...map.values()].sort((a, b) => [...b.text].length - [...a.text].length || (a.text < b.text ? -1 : a.text > b.text ? 1 : 0));
}
