# 两块式建议卡

有具体建议时，先回复文字，再在同一轮生成并交付卡，不等用户催要。欢迎、追问、分流或用户不要卡时不生成。

## 出卡时只使用现成资料

- 直接读取 quotes.json 和已用的人物案例。核验状态随库提供；不为出卡读整份证据附录、找本地原书、联网搜金句或再次核验人物。补库属于维护任务，不能塞进用户这次咨询。
- 用户追问“卡呢”时复用上一轮建议和主方法，不重新辅导或换方法。查库无匹配就当轮说明缺口并结束，不启动研究。
- 有文件执行工具时调用下方脚本一次，优先带 --png；只交付实际生成且用户能访问的文件。PNG失败已保留HTML时直接给HTML，不自动安装依赖、下载字体或另造导出方案。用户明确要求修复环境再处理。
- 宿主不能执行文件时，如有原生HTML制品工具，用 resources/assets/advice-card.html 与内置数据输出两块式页卡；不依赖不存在的本地路径。无文件或制品工具时当轮显示“给你的建议 / 书中金句”的排版文本，并明说当前环境无法导出图片。文本不冒充已生成的图片。
- 本轮结束前检查：有匹配引用且能导出，必须附卡片或可访问链接；否则必须给出准确原因。不可只说“正在生成”后结束。

## 选择金句

读取 quotes.json，只选主能力域内且符合 use_when、没有命中 avoid 的记录。传入 quote_id 与 primary，脚本填充原句、译文和定位；禁止自由生成或改写成“原句”。目前 learning、habit、attention、competition 有短引文，observe、motives、future 暂缺；不切换主方法迁就金句、不把第二张卡的句子冒充主方法。没有贴合引用时正常给建议，并简短说明本次暂不附金句卡，不让引用缺口阻断帮助。

所有当前中文引文均为据英文重排本自译，不是正式中文版原句。source-audit.md 区分正式出版社可核范围与研究底本逐句核对。quoted excerpt（节选）不标完整原句。

## 输入

UTF-8 JSON，示例：

```json
{
  "title": "过去总这样，不代表只能这样",
  "situation": "每写几句就回头删改，写作常常中断。",
  "primary": "habit",
  "quote_id": "habit-past",
  "advice": ["先观察一次回头修改发生在什么时候。", "试着写完一个意思后再检查，看看内容是否更连贯，也保留必要纠正。"],
  "method": "第6章：观察习惯、明确意图、尝试并检查结果。",
  "experience": "一句已核验读者经历，含中文全名与身份。",
  "basis": "本次建议按书中方法改编，不能替代写作技术学习。",
  "sources": [{"label": "科尔采访", "url": "https://www.si.com/nba/2016/05/26/steve-kerr-pete-carroll-nba-playoffs-inner-game-tennis-book"}],
  "example": true
}
```

必填 title≤60字符，situation≤200，advice 1–3项各≤220，method≤120，experience≤220，basis≤300。sources≤4项，每项 label≤100、HTTP(S) url≤2000；人物经历附对应来源。假设情境标 example=true。旧 closing 字段可省略且不显示。

## 生成与保存

```sh
python resources/scripts/render_card.py input.json --out cards
python resources/scripts/render_card.py input.json --out cards --png
python resources/scripts/render_card.py input.json --out cards --png --font /path/to/chinese-font.ttf
```

- 默认以 Python 3 标准库生成独立 HTML 与同名 JSON。HTML 无脚本也可阅读；浏览器按钮通过 JavaScript 导出图片。
- `--png` 用 Pillow 直接输出静态 PNG，无浏览器或 JavaScript 依赖。先安装 `python -m pip install Pillow`，并安装中文字体（Linux 可用 Noto Sans CJK）；macOS/Windows自动查常见字体。自定义字体应含中文字符。
- PNG依赖或字体不可用时，退出码2，stdout仍返回已生成的HTML/JSON绝对路径和png_error。不得报告PNG成功；提供HTML并解释依赖。输入无效退出码1，不生成卡。
- 每次使用新文件名，不覆盖既有卡；日期按UTC+8，仅表示生成时间。

## 卡面

01 给你的建议：回应处境、具体建议、书中方法。02 书中金句：一条相关短句、中文书名、章/文件页、译文标记。人物经历作为小字出处，不扩成第三大块。详细依据与原文放HTML依据区及JSON。无表单、打卡、承诺或评价用户完成度；不加入领域技术指令。正文以250–450个中文字为宜，不凑满建议条数。
