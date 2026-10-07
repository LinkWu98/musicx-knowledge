import importlib.util, json, shutil, tempfile, unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class BuildTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  # Minimal isolated fixtures: production articles may be removed independently.
  (self.root/'content/notation').mkdir(parents=True)
  (self.root/'assets/notation').mkdir(parents=True)
  (self.root/'categories.yml').write_text('categories:\n  - id: notation\n    title: 测试分类\n    order: 10\n')
  (self.root/'content/notation/五线谱与中央C.md').write_text("""---
id: notation.staff
title: 五线谱与中央 C
category: notation
order: 10
related: [notation.rhythm]
---
先找到一个熟悉的音。
## 从下往上
测试正文。
## 图片
![测试图片](../../assets/notation/staff.png)
### 图片说明
测试正文。
## 内链
[测试链接](拍号与节奏.md)
## 结尾
测试正文。
""")
  (self.root/'content/notation/拍号与节奏.md').write_text("""---
id: notation.rhythm
title: 测试链接目标
category: notation
order: 20
---
[返回](五线谱与中央C.md)
""")
  Image.new('RGB',(8,8),'white').save(self.root/'assets/notation/staff.png')
 def tearDown(self):self.temp.cleanup()
 def build(self,release='local-one'):return builder.build(self.root,release,self.root/'dist')
 def edit(self,old,new):
  p=self.root/'content/notation/五线谱与中央C.md';p.write_text(p.read_text().replace(old,new))
 def test_artifact_real_digests_links_and_stable_headings(self):
  files=self.build();catalog=json.loads(files['catalog.json'])
  for article in catalog['articles']:
   data=files[article['path']];self.assertEqual(builder.sha(data),article['sha256']);self.assertEqual(len(data),article['bytes'])
   for asset in article['assets']:self.assertEqual(builder.sha(files[asset['path']]),asset['sha256'])
  staff=next(a for a in catalog['articles'] if a['id']=='notation.staff')
  self.assertIn(b'musicx-knowledge://article/notation.rhythm',files[staff['path']]);self.assertEqual(len(staff['headings']),5)
 def test_bad_inputs_leave_last_tree_unchanged(self):
  original=self.build()['catalog.json']
  source=(self.root/'content/notation/五线谱与中央C.md').read_text()
  changes=[('category: notation','category: missing'),('order: 10','order: -1'),('## 从下往上','# 从下往上'),('staff.png','missing.png'),('拍号与节奏.md','拍号与节奏.md#chapter'),('related: [notation.rhythm]','related: [notation.staff]'),('order: 10','ordr: 10'),('order: 10','order: true')]
  for old,new in changes:
   with self.subTest(new=new):
    (self.root/'content/notation/五线谱与中央C.md').write_text(source.replace(old,new))
    with self.assertRaises(ValueError):self.build('local-two')
    self.assertEqual((self.root/'dist/catalog.json').read_bytes(),original)
  (self.root/'content/notation/五线谱与中央C.md').write_text(source)
 def test_duplicate_draft_ids_and_draft_links(self):
  p=self.root/'content/notation/duplicate.md';p.write_text((self.root/'content/notation/五线谱与中央C.md').read_text().replace('order: 10','order: 10\ndraft: true'))
  with self.assertRaises(ValueError):self.build()
  p.unlink();p=self.root/'content/notation/拍号与节奏.md';p.write_text(p.read_text().replace('order: 20','order: 20\ndraft: true'))
  with self.assertRaises(ValueError):self.build()
 def test_versions_preserve_old_resources_and_ids_after_move(self):
  first=self.build();self.edit('五线谱与中央 C','五线谱：从中央 C 开始')
  old=self.root/'content/notation/五线谱与中央C.md';new=self.root/'content/notation/中文.md';old.rename(new)
  for p in (self.root/'content').rglob('*.md'):
   p.write_text(p.read_text().replace('五线谱与中央C.md','中文.md'))
  second=self.build('local-two')
  for name,data in first.items():
   if name!='catalog.json':self.assertEqual((self.root/'dist'/name).read_bytes(),data)
  self.assertEqual({a['id'] for a in json.loads(first['catalog.json'])['articles']},{a['id'] for a in json.loads(second['catalog.json'])['articles']})
 def test_immutable_release_and_missing_history(self):
  self.build();self.edit('先找到一个熟悉的音','先找到一个熟悉的位置')
  with self.assertRaises(ValueError):self.build()
  with self.assertRaises(ValueError):builder.build(self.root,'local-two',self.root/'next',self.root/'missing')
 def test_symlink_escape(self):
  image=self.root/'assets/notation/staff.png';outside=self.root/'outside.png'
  shutil.copy(image,outside);image.unlink();image.symlink_to(outside)
  with self.assertRaises(ValueError):self.build()

if __name__=='__main__':unittest.main()
