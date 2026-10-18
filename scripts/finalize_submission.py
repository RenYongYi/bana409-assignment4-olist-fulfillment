"""Insert verified personal-account URLs after publication, then build a clean ZIP."""
from argparse import ArgumentParser
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import nbformat

root = Path(__file__).resolve().parents[1]
parser = ArgumentParser()
parser.add_argument('--repo-url')
parser.add_argument('--app-url')
parser.add_argument('--team-name')
args = parser.parse_args()
links_path = root / 'submission-links.json'
links = json.loads(links_path.read_text()) if links_path.exists() else {}
if args.repo_url:
    if not args.repo_url.startswith('https://github.com/'):
        raise ValueError('Expected the verified personal GitHub repository URL')
    links['repo_url'] = args.repo_url
if args.app_url:
    if not args.app_url.startswith('https://') or '.streamlit.app' not in args.app_url:
        raise ValueError('Expected the verified deployed Streamlit app URL')
    links['app_url'] = args.app_url
if args.team_name:
    old = links.get('team_name', 'Fulfillment Operations Team')
    for name in ['app.py','README.md']:
        p = root/name
        p.write_text(p.read_text().replace(old, args.team_name))
    links['team_name'] = args.team_name
links_path.write_text(json.dumps(links,indent=2)+'\n')

nb_path = root/'phone-trade-in.ipynb'
nb = nbformat.read(nb_path,as_version=4)
source = nb.cells[0].source.splitlines()
for i,line in enumerate(source):
    if line.startswith('- **Deployed app URL:**') and links.get('app_url'):
        source[i]='- **Deployed app URL:** '+links['app_url']
    if line.startswith('- **GitHub repository URL:**') and links.get('repo_url'):
        source[i]='- **GitHub repository URL:** '+links['repo_url']
nb.cells[0].source='\n'.join(source)
nbformat.write(nb,nb_path)
readme=root/'README.md'
lines=readme.read_text().splitlines()
for i,line in enumerate(lines):
    if line.startswith('**App URL:**') and links.get('app_url'):
        lines[i]='**App URL:** '+links['app_url']
    if line.startswith('**Repository URL:**') and links.get('repo_url'):
        lines[i]='**Repository URL:** '+links['repo_url']
readme.write_text('\n'.join(lines)+'\n')

excluded={'.venv','.git','__pycache__','.ipynb_checkpoints','raw','src'}
files=[p for p in root.rglob('*') if p.is_file() and not any(s in excluded for s in p.relative_to(root).parts)
       and p.name not in {'submission-links.json','.DS_Store'} and p.suffix != '.pyc']
archive=root.parent/'Assignment4_Olist_Submission.zip'
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
    for p in sorted(files):z.write(p,Path(root.name)/p.relative_to(root))
print('Packaged',len(files),'files:',archive)
print('Publication status:',json.dumps({k:v for k,v in links.items() if k.endswith('_url')}))
