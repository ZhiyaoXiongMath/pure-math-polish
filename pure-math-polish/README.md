# Pure Math Polish

纯数学论文 LaTeX 润色 skill。入口为 [SKILL.md](SKILL.md)。

模板只包含 [Xiaokui Yang 的 20 篇论文](assets/templates/INDEX.md)：27 个原始 TeX 文件及其必要的类文件、图和书目。根据论文题材选择主模板，再核对版式、宏定义和实际调用；原始源码保持只读。

## 使用

将 ZIP 解压，保留 `pure-math-polish/` 目录结构，在支持此 skill 格式的环境中载入该目录。提供当前论文主文件与必要依赖，并说明全文或局部编辑范围；需要保留投稿模板时直接说明。

常用检查（在 skill 根目录执行）：

```bash
python -B scripts/author_templates.py verify assets/templates/xiaokui-yang-20
python -B scripts/release.py verify .
python -B scripts/tex_preflight.py /path/to/main.tex --json
```

工具使用 Python 3.10+；发行校验使用 PyYAML。TeX 构建需要实际项目所需的引擎、包和字体；不随包分发字体。运行各脚本的 `--help` 查看接口。静态检查、编译与数学审核彼此不能替代。

论文作者、版本、来源和许可元数据见 [来源说明](NOTICE.md) 与模板 manifest。
