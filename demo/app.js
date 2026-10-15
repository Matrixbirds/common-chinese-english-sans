const status = document.querySelector('#status');
const grid = document.querySelector('#grid');
const search = document.querySelector('#search');
const kind = document.querySelector('#kind');
try {
  const response = await fetch('../data/vocabulary.json');
  if (!response.ok) throw new Error(`词库加载失败：${response.status}`);
  const rows = await response.json();
  function draw() {
    const q = search.value.toLowerCase();
    const shown = rows.filter(r => (kind.value === 'all' || (kind.value === 'single' ? [...r.hanzi].length === 1 : [...r.hanzi].length > 1)) && [r.hanzi,r.english,r.pinyin].some(v => v.toLowerCase().includes(q)));
    grid.replaceChildren(...shown.slice(0,120).map(r => {
      const card = document.createElement('div'); card.className = 'card';
      for (const [cls,text] of [['hint',r.pinyin],['word',r.hanzi],['hint',r.english]]) {
        const node = document.createElement('div'); node.className = cls; node.textContent = text; card.append(node);
      }
      return card;
    }));
    document.querySelector('#count').textContent = `${shown.length} 个词条，最多显示 120 个。`;
  }
  search.oninput = kind.onchange = draw; draw();
  await document.fonts.load('36px ChineseHints');
  if (![...document.fonts].some(f => f.family === 'ChineseHints' && f.status === 'loaded')) throw new Error('字体未加载，请先运行 npm run build');
  status.textContent = `字体已加载 · ${rows.length} 个词条`;
} catch (error) { status.textContent = String(error); }
document.querySelector('#toggle').onclick = e => {
  document.body.classList.toggle('off'); e.target.textContent = document.body.classList.contains('off') ? '显示英文' : '隐藏英文';
};
document.querySelector('#size').oninput = e => document.querySelector('#sample').style.fontSize = `${e.target.value}px`;
