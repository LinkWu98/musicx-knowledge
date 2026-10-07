# MusicX 音乐知识内容

公开音乐知识的独立源码仓库。当前包含“学习路线”分类的一篇总览、六篇路线卡片，以及“乐理”分类下的《从频率比到音阶：纯律与十二平均律》。不要加入私人练习记录、数据库、访问令牌或设备数据。

## 本地构建

需要 Python 3.9+。`python3 -m venv .venv` 后安装 `pip install -r requirements.txt`。

```sh
python3 scripts/build.py validate
python3 -m unittest discover -s tests -v
python3 scripts/build.py build --release local-<本次唯一标识>
```

文章标题与作者源文件名使用中文，音名等必要的音乐记号保留原写法；文章 ID 保持稳定，不随文件改名而变化。

作者维护 `categories.yml`、`content/` 的 front matter + Markdown 和 `assets/` 下的 PNG/JPEG。初版支持行内形式的链接（包括中文路径）；引用式链接定义会报清晰错误。分类与文章按 `(order, id)` 排序。正文仅用 H2/H3，不重复文章标题。内链写相对 `.md` 路径，图片提供替代文字。

生成 `dist/catalog.json` 与 `dist/releases/<release>/`。清单协议 schemaVersion=1；使用真实 SHA-256、字节数、图片尺寸和稳定章节 ID。校验失败保留原 dist；同一 release 不能替换不同字节，每次改文后用新的 `local-...` 标识。正式构建传当前完整 Git SHA，且工作树必须干净。

可传 `--previous <完整旧发布目录>` 保留已发布的所有 releases。指定的旧目录不存在则失败；默认保留当前 dist 下的旧 releases。发布前在本地运行校验与测试；公开发布使用独立的 `published-content` 分支。`scripts/validate-workflow.yml.example` 保留可选的 Actions 校验示例，当前未启用。

## 文章与 App 契约

学习路线入口：[爵士与嘻哈钢琴学习路线](content/learning-path/爵士与嘻哈钢琴学习路线.md)。六篇路线卡片依次覆盖钢琴基础、核心入门、爵士和声、节奏律动、曲目应用与自由演奏。各卡片只保留“学什么、用什么学、用什么练、完成标准”，使用简短条目；概念详解另放乐理文章，不把路线写成教材。完成标准是通用自检参考，不记录实际掌握状态。首页仍为单层分类，通过总览和文章内链形成阅读路线；学习路线不包含个人进度、曲目状态或里程碑记录。标题与源文件名均为中文，旧文章 ID 不复用。

“识谱”和“练习方法”分类及三篇文章已于 2026-10-07 从作者源码与当前目录中删除，相关谱例资源和生成脚本一并移除。原音程短文已并入下方的乐理科普文章。已停用的 `notation.staff`、`notation.rhythm`、`practice.slow` 与 `theory.intervals` 不复用；Git 历史和旧 release 保留，供旧缓存兼容使用，不进入最新目录。

乐理文章：[从频率比到音阶：纯律与十二平均律](content/theory/从频率比到音阶：纯律与十二平均律.md)。从声音振动与频率出发，逐步介绍音程度数、常见音程比例、泛音、五度构造、纯律和弦与十二平均律；各节先概括重点，再展开说明。合并保留 `theory.scales-tuning-and-chords`，原样例 ID `theory.intervals` 停用且不复用；源文章引用已迁移，旧 `local-preview` 与 App fixture 保留原样。

App 仓库的 `MusicX/Resources/KnowledgePreview/` 是这次 `local-preview` 的精简共享测试产物，不作为日常编辑位置。Swift 测试读取同一目录校验清单、正文、图片、章节与内链；原生预览使用同一份资源。正文继续只在本内容仓库维护。生成器测试在临时目录中创建最小测试文章和图片，不依赖正式文章，也不会把测试内容发布到知识库。

## 发布与更新

内容源码位于 `main`；完整发布树位于 `published-content`，GitHub Pages 从该分支根目录发布。根目录保留 `.nojekyll`，确保 Markdown 正文按原始字节提供，不经 Jekyll 转换。后续可将校验示例启用为 Actions 工作流；它只生成审阅产物，不负责部署。

App 内容根：[MusicX 知识库](https://linkwu98.github.io/musicx-knowledge/)。App 读取根目录的 `catalog.json`，正文和图片采用带版本的路径。首次上线日期为 2026-10-07；是否部署成功以 Pages 状态及实际 URL 校验为准。

后续发布流程：

1. 修改作者文件，运行校验与测试，提交并推送 `main`；正式 release 使用该完整提交 SHA。
2. 从远端获取 `published-content`，放在源仓库之外的临时 checkout。读取失败必须停止，不能按首次发布处理。
3. 在干净的源码 checkout 执行 `python3 scripts/build.py build --release <完整SHA> --previous <历史checkout> --output <新的输出目录>`。
4. 核对目录、正文和图片的字节数与 SHA-256，并逐字节确认旧 `releases/` 文件全部保留。将生成输出同步到历史 checkout，保留 `.nojekyll`。
5. 提交并普通推送 `published-content`，触发 Pages 发布。禁止 force push；遇到分支前进应重新读取历史并构建。等待本次部署完成，再开始下一次发布。
6. 检查 Pages 部署结果，实际读取线上目录、正文与图片，核对版本及摘要后，才算发布完成。

首次发布已在确认远端仓库为空、未启用 Pages 的情况下显式初始化历史分支。后续不得再次以空历史初始化。旧 `local-preview` 只用于本地和 App 测试，不作为正式发布版本。

App 在 `MusicX/Info.plist` 的 `KnowledgeContentRoot` 中配置上述 HTTPS 根。首次接入需要重新构建并覆盖安装一次；后续内容发布无需重新构建 App，在“知识”的“音乐知识”列表下拉刷新即可。打开知识页会自动检查目录，正常检查有 30 分钟间隔，下拉刷新会强制检查。已经打开的正文保留当前版本，返回列表后重新打开可读取新版。
