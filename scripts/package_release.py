import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

p = argparse.ArgumentParser()
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
config = json.loads((root / 'font.config.json').read_text())
validation = json.loads((a.out / 'validation.json').read_text())
report = json.loads((a.out / 'build-report.json').read_text())
if report['version'] != config['version']:
    raise ValueError('Rebuild fonts after changing version')
if validation.get('status') != 'passed':
    raise ValueError('Font validation must pass before packaging')
release = a.out / 'release'
release.mkdir(exist_ok=True)
archive = release / f"common-chinese-english-sans-v{config['version']}.zip"
with ZipFile(archive, 'w', ZIP_DEFLATED) as z:
    for name in [config['postscriptName'] + '.otf', config['postscriptName'] + '.woff2', 'build-report.json', 'validation.json']:
        z.write(a.out / name, name)
    z.writestr('README.md', '# Common Chinese English Sans\n\nInstall the OTF by opening it with your system font installer. Use WOFF2 for websites. Select Common Chinese English Sans. English annotations are vocabulary hints, not sentence translations. Use a line height of 1.9 and font sizes of 28px or larger. Set OpenType rclt=0 to hide hints.\n\nFonts retain OFL obligations; derived vocabulary retains CC BY-SA attribution. Read LICENSES.md, OFL.txt and wordfreq-attribution.md. MIT applies to original project source only.\n\nSource and build instructions: https://github.com/Matrixbirds/common-chinese-english-sans\n')
    for name in ['LICENSE', 'LICENSES.md', 'OFL.txt', 'wordfreq-attribution.md']:
        z.write(root / name, name)
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(release / 'SHA256SUMS.txt').write_text(f'{checksum}  {archive.name}\n')
print(archive)
