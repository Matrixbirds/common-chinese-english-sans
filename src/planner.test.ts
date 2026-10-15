import { test } from 'node:test';
import assert from 'node:assert/strict';
import { entries, plan } from './planner.ts';
const coverage = new Set([...'中国人ChineseChina'].map(c => c.codePointAt(0)!));
test('longest words precede their prefixes, including protection', () => {
  const rules = plan([{hanzi:'中国',annotation:'China'}], [{hanzi:'中国人',annotation:''}], coverage, 100);
  assert.deepEqual(rules.map(r => [r.text,r.mode]), [['中国人','protect'],['中国','annotate']]);
});
test('reject conflicting rules instead of silently picking a meaning', () => {
  assert.throws(() => plan([{hanzi:'中国',annotation:'China'}], [{hanzi:'中国',annotation:''}], coverage,100), /conflicting/);
});
test('missing base glyphs and capacity overflow fail before compilation', () => {
  assert.throws(() => plan([{hanzi:'中国',annotation:'China'}], [],new Set(),100), /lacks/);
  assert.throws(() => plan([{hanzi:'中国',annotation:'China'}], [],coverage,65535), /capacity/);
});
test('reject malformed vocabulary and non-empty protection annotations', () => {
  assert.throws(() => entries([{hanzi:'中国',annotation:''}]), /annotation/);
  assert.throws(() => entries([{hanzi:'中国',annotation:'China'}], true), /Protection/);
});
