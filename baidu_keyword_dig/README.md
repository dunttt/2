## 百度关键词挖掘与流量查询工具（baidu_keyword_dig）

本模块提供两类能力：
- 关键词挖掘：基于百度下拉联想、相关搜索与推广后台 API 拓展关键词。
- 流量查询：对既有关键词批量查询月均搜索量等指标，按批写入 CSV。

目录结构（关键文件）：
- `run.py`：入口程序，交互选择执行“挖词”或“流量查询”。
- `keyword_dig.py`：挖词逻辑（下拉、相关搜索、凤巢 API）。
- `keyword_searchpv.py`：搜索量查询（批量请求凤巢 API，分批保存）。
- `file_reader.py`：读取 `input_data` 下关键词文件，自动生成默认示例。
- `data_save.py`：结果处理与 CSV 保存（含去重统计与字段对齐）。
- `config.ini`：接口地址与用户配置（user-agent、cookie、token、reqid、userid）。
- 目录 `input_data/`：输入文件（`keyword.txt`、`pv_keywords.txt`）。
- 目录 `output_data/`：输出 CSV 结果（文件名含时间戳）。

### 运行环境与依赖
- Python 3.12（兼容 3.9+ 通常也可）
- 依赖：`requests`、`lxml`

安装依赖：
```bash
pip install requests lxml
```

### 配置说明（config.ini）
`config.ini` 已提供默认段与用户段：
- `[DEFAULT]`
  - `baidu_sug_url`：下拉联想接口
  - `baidu_search_url`：搜索结果页地址（用于解析相关搜索）
  - `fengchao_api_url`：凤巢接口网关
- `[USER_CONFIG]`
  - `user-agent`：浏览器 UA 字符串
  - `cookie`：需要有效的登录 Cookie（含 BDUSS 等），用于访问页面与凤巢
  - `reqid`、`userid`、`token`：凤巢接口鉴权相关参数

重要提示：
- 请用你自己的 `cookie`、`reqid`、`userid`、`token` 替换示例值，且避免泄露；这些值可能会过期，需要定期更新。
- `configparser` 在本项目中禁用了插值，配置值可包含 `%`。

### 输入与输出
- 输入目录：`input_data/`
  - `keyword.txt`：挖词种子列表，每行一个；`#` 开头的行会被忽略。
  - `pv_keywords.txt`：待查询流量的关键词列表，每行一个；`#` 开头的行会被忽略。
  - 首次运行会自动创建以上文件并写入示例注释。

- 输出目录：`output_data/`
  - 挖词结果：`keyword_dig_results_YYYYMMDD_HHMMSS.csv`
    - 表头：`种子词, 挖词类型, 关键词, 月均搜索量, 月均PC搜索量, 月均M搜索量, 日均搜索量, 日均PC搜索量, 日均M搜索量, 挖掘时间`
    - 说明：API 返回的词携带指标；下拉/相关搜索词无指标时以 `-` 填充。
  - 流量查询结果：`keyword_pv_results_YYYYMMDD_HHMMSS.csv`
    - 表头：`关键词, 过滤状态, 过滤原因, 月均搜索量, 月均PC搜索量, 月均M搜索量, 日均搜索量, 日均PC搜索量, 日均M搜索量, 数据来源, 查询时间`
    - 说明：超长词会被“字符过滤”；API 未返回的词标记“未知过滤”。

### 使用步骤
1) 准备配置
   - 编辑 `config.ini` 的 `[USER_CONFIG]`，填入有效的 `user-agent`、`cookie`、`reqid`、`userid`、`token`。

2) 准备关键词
   - 挖词：把种子词写入 `input_data/keyword.txt`，一行一个。
   - 流量查询：把待查词写入 `input_data/pv_keywords.txt`，一行一个。

3) 运行程序
```bash
python run.py
```
   - 选择 `1` 执行“关键词挖掘”；或选择 `2` 执行“关键词流量查询”。

4) 查看输出
   - 结果保存在 `output_data/` 下的对应 CSV 文件。

### 主要逻辑概览
- 挖词（`keyword_dig.py`）
  - `sug_word`：请求 `baidu_sug_url` 获取联想词。
  - `other_search_word`：请求 `baidu_search_url` 并用 XPath 抽取“大家都在搜/相关搜索”。
  - `fc_api_word`：调用凤巢关键词推荐接口，返回关键词及 PV 相关指标。
  - 挖词后自动 PV 查询：对“仅来自下拉/相关搜索且未出现在 API 返回中的词”，在保存挖词结果后自动触发一次批量 PV 查询，结果输出到独立 CSV。

- 流量查询（`keyword_searchpv.py`）
  - 超长词过滤：按中英文字符宽度计算，超过 40 记为“字符过滤”。
  - 批量查询：默认每批 1000 个关键词，请求凤巢 *PvSearch* 接口。
  - 分批保存：首批写入表头，其余批次追加，避免内存占用并保证字段对齐。
  - 仍支持从菜单选择“2. 关键词流量查询”单独运行该功能。

- 数据保存（`data_save.py`）
  - 挖词：API 结果去重；其余来源补齐字段并统一写出；提供去重统计。
  - PV：严格按表头字段映射，避免字段错位。

### 常见问题与提示
- 登录态与鉴权：`cookie`、`token`、`reqid` 失效会导致返回为空或频繁被风控，请及时更新并降低请求频率。
- 请求频率：程序已在必要处加入 `sleep`，如仍遇到限制，可适当加大等待时间或减小批量大小。
- XPath 选择器：百度页面结构可能变动，如相关搜索抽取为空，请根据实际 HTML 调整 `other_search_word` 内的 XPath。
- 字符集：文件读写均为 UTF-8；CSV 使用 `utf-8-sig` 以便 Excel 直接打开。

### 免责声明
本工具仅供学习与研究，使用者需自行确保符合目标网站及相关平台的服务条款与法律法规。


