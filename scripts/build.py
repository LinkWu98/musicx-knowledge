#!/usr/bin/env python3
"""MusicX catalog v1. Local builds never enable or deploy Pages."""
import argparse, datetime, hashlib, json, re, shutil, subprocess, tempfile, unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit
import yaml
from PIL import Image
from markdown_it import MarkdownIt

ID = re.compile(r'[a-z0-9][a-z0-9._-]*\Z')
MD = MarkdownIt('commonmark').enable('table')
LIMIT_BODY, LIMIT_IMAGE, LIMIT_CATALOG = 256*1024, 5*1024*1024, 2*1024*1024

def sha(data): return hashlib.sha256(data).hexdigest()
def norm(text): return ' '.join(unicodedata.normalize('NFC', text).split())
def plain(tokens): return ''.join(t.content for t in (tokens or []) if t.type in ('text','code_inline','softbreak'))
def require(ok, message):
    if not ok: raise ValueError(message)
def scoped(root, base, target):
    url = urlsplit(target)
    require(not url.scheme and not url.netloc and not url.query and not url.fragment, f'非法相对路径: {target}')
    path = (base / unquote(url.path)).resolve()
    require(path.is_relative_to(root.resolve()), f'路径越界: {target}')
    require(path.is_file(), f'文件不存在: {target}')
    return path

def collect(root, release):
    errors, sources, ids = [], {}, set()
    def check_meta(meta, keys, where):
        require(isinstance(meta, dict), f'{where}: 应为映射')
        require(not set(meta)-keys, f'{where}: 未知字段 {set(meta)-keys}')
        require(isinstance(meta.get('id'), str) and ID.fullmatch(meta['id']), f'{where}: id 非法')
        require(isinstance(meta.get('title'), str) and bool(meta['title'].strip()) and '\n' not in meta['title'] and '<' not in meta['title'], f'{where}: title 应为非空纯文本')
        require(type(meta.get('order')) is int and meta['order'] >= 0, f'{where}: order 应为非负整数')
    categories = yaml.safe_load((root/'categories.yml').read_text())
    require(isinstance(categories, dict) and set(categories)=={'categories'} and isinstance(categories['categories'], list), 'categories.yml: categories 应为数组')
    cats = categories['categories']; cat_ids=set()
    for cat in cats:
        check_meta(cat, {'id','title','order'}, 'categories.yml')
        require(cat['id'] not in cat_ids, 'categories.yml: 重复分类 ID'); cat_ids.add(cat['id'])
    for file in sorted((root/'content').rglob('*.md')):
        try:
            require(file.resolve().is_relative_to(root.resolve()), '源文件符号链接越界')
            raw=file.read_text(encoding='utf-8').replace('\r\n','\n')
            require(raw.startswith('---\n') and '\n---\n' in raw[4:], '缺少 front matter')
            front, body=raw[4:].split('\n---\n',1); meta=yaml.safe_load(front)
            check_meta(meta, {'id','title','category','order','updated','draft','related'}, str(file))
            require(meta['id'] not in ids, '重复文章 ID'); ids.add(meta['id'])
            require(meta.get('category') in cat_ids, '未知 category')
            require(type(meta.get('draft',False)) is bool, 'draft 应为布尔值')
            related=meta.get('related',[])
            require(isinstance(related,list) and all(isinstance(x,str) for x in related) and len(set(related))==len(related) and meta['id'] not in related, 'related 非法')
            if 'updated' in meta:
                require(isinstance(meta['updated'],str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',meta['updated']), 'updated 应为双引号日期')
                datetime.date.fromisoformat(meta['updated'])
            sources[file.resolve()]=(meta,body.strip()+'\n')
        except (ValueError, TypeError, yaml.YAMLError) as e: errors.append(f'{file}: {e}')
    published={m['id'] for m,b in sources.values() if not m.get('draft',False)}
    articles=[]; files={}
    for file,(meta,body) in sources.items():
        if meta.get('draft',False): continue
        try:
            require(all(x in published for x in meta.get('related',[])), 'related 指向不存在或草稿文章')
            tokens=MD.parse(body); headings=[]; counts={}; assets={}; replacements={}
            # Reference definitions are deliberately rejected with an author-facing error.
            require(not re.search(r'^ {0,3}\[[^\]]+\]:',body,re.M), '请用行内链接，不使用引用式链接定义')
            for i,t in enumerate(tokens):
                require(t.type not in ('html_block','html_inline'), f'行 {(t.map or [0])[0]+1}: 不允许 HTML')
                if t.type=='heading_open':
                    level=int(t.tag[1:]); require(level in (2,3), f'行 {t.map[0]+1}: 正文只允许 H2/H3')
                    title=norm(plain(tokens[i+1].children)); key='h-'+sha(f'{level}:{title}'.encode())[:12]
                    counts[key]=counts.get(key,0)+1
                    headings.append(dict(id=key+(f'-{counts[key]}' if counts[key]>1 else ''),level=level,index=len(headings),title=title))
                for child in t.children or []:
                    require(child.type!='html_inline', f'行 {(t.map or [0])[0]+1}: 不允许 HTML')
                    if child.type not in ('image','link_open'): continue
                    target=child.attrGet('src' if child.type=='image' else 'href')
                    if child.type=='image':
                        require(bool(child.content.strip()), '图片必须提供替代文字')
                        path=scoped(root/'assets',file.parent,target); data=path.read_bytes()
                        require(len(data)<=LIMIT_IMAGE, '图片超过 5 MiB')
                        with Image.open(path) as im:
                            require(im.format in ('PNG','JPEG'), '图片仅支持 PNG/JPEG')
                            require(max(im.size)<=4096, '图片最长边超过 4096px')
                            ext='png' if im.format=='PNG' else 'jpg'; media='image/png' if ext=='png' else 'image/jpeg'; width,height=im.size
                            im.verify()
                        digest=sha(data); out=f'releases/{release}/assets/{digest}.{ext}'; files[out]=data
                        assets[out]=dict(path=out,sha256=digest,bytes=len(data),mediaType=media,width=width,height=height)
                        replacements[target]=f'../assets/{digest}.{ext}'
                    elif urlsplit(target).scheme=='https':
                        require(bool(urlsplit(target).netloc), 'HTTPS 链接缺少主机')
                    else:
                        linked=scoped(root,file.parent,target)
                        require(linked in sources and sources[linked][0]['id'] in published, '内链指向不存在或草稿文章')
                        replacements[target]='musicx-knowledge://article/'+sources[linked][0]['id']
            # Reject schemes CommonMark may leave as literal text rather than silently shipping them.
            require(not re.search(r'\]\(\s*(?:javascript|data|http|file):',body,re.I), '不支持的 URL scheme')
            for old,new in replacements.items():
                if ']('+old not in body and '](<'+old+'>' not in body: old=unquote(old)
                require(']('+old in body or '](<'+old+'>' in body, f'请使用简单行内链接路径: {old}')
                body=body.replace(']('+old,']('+new).replace('](<'+old+'>','](<'+new+'>')
            encoded=body.encode(); require(len(encoded)<=LIMIT_BODY, '正文超过 256 KiB')
            require(sum(a['bytes'] for a in assets.values())<=20*1024*1024,'单篇图片超过 20 MiB')
            out=f"releases/{release}/articles/{meta['id']}.md"; files[out]=encoded
            article={k:meta[k] for k in ('id','title','category','order','updated') if k in meta}
            article.update(path=out,sha256=sha(encoded),bytes=len(encoded),headings=headings,assets=list(assets.values()),related=meta.get('related',[])); articles.append(article)
        except (ValueError, OSError) as e: errors.append(f'{file}: {e}')
    require(not errors, '\n'.join(errors))
    articles.sort(key=lambda a:(a['category'],a['order'],a['id']))
    catalog=dict(schemaVersion=1,releaseID=release,categories=sorted([c for c in cats if any(a['category']==c['id'] for a in articles)],key=lambda c:(c['order'],c['id'])),articles=articles)
    encoded=(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode(); require(len(encoded)<=LIMIT_CATALOG,'清单超过 2 MiB')
    files['catalog.json']=encoded
    return files

def build(root, release, output=None, previous=None):
    require(bool(re.fullmatch(r'(?:[0-9a-f]{40}|local-[a-zA-Z0-9._-]+)',release)), 'releaseID 非法')
    files=collect(root,release)
    if output is None: return files
    output=output.resolve(); output.parent.mkdir(parents=True,exist_ok=True)
    if previous is not None: require(previous.is_dir() and (previous/'catalog.json').is_file(), '上一发布树不可读取，停止构建')
    history=previous or (output if output.exists() else None)
    temp=Path(tempfile.mkdtemp(prefix='.knowledge-',dir=output.parent))
    try:
        if history and (history/'releases').exists(): shutil.copytree(history/'releases',temp/'releases')
        for name,data in files.items():
            path=temp/name
            require(not path.exists() or path.read_bytes()==data, f'不可覆盖同一 release 的不同字节: {name}')
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        # Keep the old tree intact until the entire new tree exists.
        backup=output.with_name(output.name+'.previous')
        require(not backup.exists(), f'请先恢复或移走 {backup}')
        if output.exists(): output.rename(backup)
        try: temp.rename(output)
        except BaseException:
            if backup.exists(): backup.rename(output)
            raise
        if backup.exists(): shutil.rmtree(backup)
    finally:
        if temp.exists(): shutil.rmtree(temp)
    return files

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['validate','build']); parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); parser.add_argument('--release',default='local-preview'); parser.add_argument('--previous',type=Path); parser.add_argument('--output',type=Path); args=parser.parse_args()
    try:
        if not args.release.startswith('local-'):
            require(not subprocess.check_output(['git','status','--porcelain'],cwd=args.root).strip(),'正式构建要求工作树干净')
            require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.root,text=True).strip()==args.release,'release 必须是当前完整提交 SHA')
        result=build(args.root,args.release,(args.output or args.root/'dist') if args.command=='build' else None,args.previous)
        print(f'{args.command}: {len(result)} files validated; release {args.release}')
    except (ValueError,OSError,yaml.YAMLError) as e: parser.exit(1,str(e)+'\n')
