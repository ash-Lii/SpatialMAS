# SpatialMAS 仓库级说明

> 这是本仓库的“单一事实来源”之一。任何对项目的修改，凡是会影响代码、配置、schema、prompt、脚本、测试、运行方式或使用说明，都要同步反映到这里。
>
> 如果你改了项目，却没改这个文件，说明文档没有跟上代码。

## 1. 项目概览

SpatialMAS 是一个面向 Snowflake 的空间与表格分析 CLI 项目。它的核心目标很明确：

- 用环境变量做安全配置
- 只执行只读 SQL
- 让工具输出保持结构化、可消费
- 通过模块化拆分，方便长期维护

这个项目面向的是以 `SAN_FRANCISCO_PLUS` 为默认数据库快照的一组城市数据集，包含 311、共享单车、电影拍摄地、社区边界、消防、警情、公交、树木等多个主题。

## 2. 技术栈

- Python 3.11+
- LangChain
- LangGraph
- Snowflake Connector for Python
- pandas
- numpy
- python-dotenv
- 开发工具：pytest、pytest-asyncio、ruff、black、mypy

打包方式使用 `setuptools`。

## 3. 运行形态

### 3.1 运行入口

- 自然语言入口：`python main.py "你的问题"`
- SQL 直执行入口：`python db.py "SELECT ..."`
- 两个入口都使用源码直跑和环境变量配置；`db.py` 复用现有的 Snowflake 连接与只读查询逻辑。

`main.py` 会以流式方式打印模型内容和工具调用过程；`db.py` 则直接输出查询结果 JSON。

### 3.2 schema 重建与校验

- 重建 schema：`python scripts/generate_schema.py`
- 校验 schema：`python scripts/validate_schema.py`

## 4. 内部工具

当前 CLI 会调用 4 个工具，名字必须保持稳定：

1. `select_relevant_schema`
2. `generate_sql_query`
3. `execute_db_query`
4. `analyze_query_result`

### 4.1 `select_relevant_schema`

输入：`question`

输出是结构化 JSON，核心字段包括：

- `schema_string`
- `selected_tables`
- `reasoning`
- `schema_reduction`
- `warnings`

### 4.2 `generate_sql_query`

输入：

- `question`
- `schema_string`

输出是 SQL 文本。

### 4.3 `execute_db_query`

输入：

- `sql_query`
- `limit`，可选

输出是 `QueryExecutionResult` 的 JSON，包含：

- `sql_original`
- `sql_executed`
- `columns`
- `rows`
- `row_count`
- `warnings`
- `truncated`

### 4.4 `analyze_query_result`

输入：

- `data`
- `analysis_type`，可选，默认 `comprehensive`

输出是分析结果字典，通常包含行数、列名、统计指标、相关性、趋势和建议。

## 5. 代码流

### 5.1 CLI 的调用链

`main.py` 会创建 `ChatAgent`，把 4 个 LangChain 工具挂进去，然后按流式事件输出内容。

推荐的工具顺序是：

1. 先选 schema
2. 再生成 SQL
3. 再执行查询
4. 最后分析结果

   另外，CLI 的系统提示也会明确要求：所有 SQL 列名都要按 schema 里的双引号写，遇到微秒时间戳要先 `/1000000` 再 `TO_TIMESTAMP`。

### 5.2 工具层调用

`spatialmas/langchain_tools.py` 负责把四个内部工具包装成 LangChain tool，再落到 service 层：

- `SchemaSelectionService`
- `SQLGenerationService`
- `QueryService`
- `AnalysisService`

### 5.3 LLM 和会话

`spatialmas/agent.py` 使用 LangChain 的 `create_agent` 和 LangGraph 的 `InMemorySaver`。
这意味着：

- 会话状态只在进程内保存
- 重启后不保留历史
- `clear_history()` 会重置 thread id

## 6. 目录地图

### 6.1 仓库根目录

- `README.md`：项目快速说明
- `db.py`：直接执行 SQL 的轻量脚本
- `questions.md`：批量评测问题清单
- `test.py`：批量执行脚本，实时输出 `main.py` 的 stdout，并覆盖写入 `answers/` 下的单独文件
- `answers/`：批量跑题输出结果（每题一个 Markdown 文件，包含完整日志）
- `MIGRATION.md`：部署和兼容性注意事项
- `.env.example`：环境变量样例
- `pyproject.toml`：依赖、脚本、测试和格式化配置
- `schema/`：LLM 可读 schema 与 prompt 规则
- `scripts/`：schema 生成和验证脚本
- `spatialmas/`：核心 Python 包
- `tests/`：测试
- `prompts/`：独立的研究提示词资产
- `paperworks/`：项目文档、图表、报告材料

### 6.2 核心代码

- `main.py`：CLI 演示入口
- `spatialmas/config.py`：环境变量读取、路径解析、必需项检查
- `spatialmas/models.py`：数据模型、结果结构、JSON 安全转换
- `spatialmas/agent.py`：LangChain 聊天代理封装
- `spatialmas/langchain_tools.py`：LangChain 工具封装
- `spatialmas/infra/llm_client.py`：构建聊天模型客户端
- `spatialmas/infra/snowflake_client.py`：Snowflake 连接与只读查询执行
- `spatialmas/schema/loader.py`：schema 文件和规则文件加载器
- `spatialmas/services/schema_service.py`：schema 选择
- `spatialmas/services/sql_service.py`：SQL 生成与校验
- `spatialmas/services/query_service.py`：查询执行
- `spatialmas/services/analysis_service.py`：结果分析

### 6.3 其他说明

- `spatialmas/tools/` 当前没有实际业务实现，保留为包目录。
- `SpatialMAS.egg-info/`、`__pycache__/`、`.venv/` 属于构建或本地环境产物，不是业务代码。

## 7. 数据与 schema

### 7.1 当前 schema 快照

- schema 文件：`schema/schema.txt`
- 规则文件：`schema/rules.json`
- 当前生成时间：`2026-05-20 16:13`
- 当前表数：20
- 当前关系数：20

这个 schema 文件不是直接连库实时查询出来的，而是生成时对 Snowflake 数据库做的一次快照。它包含：

- 表头
- 行数
- 列定义
- 样例数据
- 推断出来的关系

### 7.2 业务域与表

#### 311

- `SAN_FRANCISCO_311._311_SERVICE_REQUESTS` — 7,263,300

#### Bikeshare

- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_REGIONS` — 6
- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_STATION_INFO` — 472
- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_STATION_INFO_VARIANT` — 0
- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_STATION_STATUS` — 553
- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_TRIPS` — 1,947,417

#### Film locations

- `SAN_FRANCISCO_FILM_LOCATIONS.FILM_LOCATIONS` — 2,084

#### Neighborhoods

- `SAN_FRANCISCO_NEIGHBORHOODS.BOUNDARIES` — 117

#### SFFD service calls

- `SAN_FRANCISCO_SFFD_SERVICE_CALLS.SFFD_SERVICE_CALLS` — 6,734,089

#### SFPD incidents

- `SAN_FRANCISCO_SFPD_INCIDENTS.SFPD_INCIDENTS` — 0

#### Transit Muni

- `SAN_FRANCISCO_TRANSIT_MUNI.CALENDAR` — 8
- `SAN_FRANCISCO_TRANSIT_MUNI.FARES` — 8
- `SAN_FRANCISCO_TRANSIT_MUNI.ROUTES` — 83
- `SAN_FRANCISCO_TRANSIT_MUNI.SHAPES` — 187,288
- `SAN_FRANCISCO_TRANSIT_MUNI.STOPS` — 3,514
- `SAN_FRANCISCO_TRANSIT_MUNI.STOP_MONITORING` — 25,826,668
- `SAN_FRANCISCO_TRANSIT_MUNI.STOP_TIMES` — 1,105,370
- `SAN_FRANCISCO_TRANSIT_MUNI.TRIPS` — 28,811
- `SAN_FRANCISCO_TRANSIT_MUNI.VEHICLE_MONITORING` — 104

#### Trees

- `SAN_FRANCISCO_TREES.STREET_TREES` — 198,354

### 7.3 当前关系

这些关系来自 `scripts/generate_schema.py` 的推断逻辑，对 SQL 选表和 join 很重要：

- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_REGIONS.region_id -> SAN_FRANCISCO_BIKESHARE.BIKESHARE_STATION_INFO.region_id`
- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_STATION_INFO.station_id -> SAN_FRANCISCO_BIKESHARE.BIKESHARE_STATION_STATUS.station_id`
- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_STATION_INFO.region_id -> SAN_FRANCISCO_BIKESHARE.BIKESHARE_REGIONS.region_id`
- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_STATION_STATUS.station_id -> SAN_FRANCISCO_BIKESHARE.BIKESHARE_STATION_INFO.station_id`
- `SAN_FRANCISCO_BIKESHARE.BIKESHARE_TRIPS.trip_id -> SAN_FRANCISCO_TRANSIT_MUNI.TRIPS.trip_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.ROUTES.route_id -> SAN_FRANCISCO_TRANSIT_MUNI.STOP_MONITORING.route_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.SHAPES.shape_id -> SAN_FRANCISCO_TRANSIT_MUNI.TRIPS.shape_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.STOPS.stop_id -> SAN_FRANCISCO_TRANSIT_MUNI.STOP_MONITORING.stop_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.STOP_MONITORING.stop_id -> SAN_FRANCISCO_TRANSIT_MUNI.STOPS.stop_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.STOP_MONITORING.route_id -> SAN_FRANCISCO_TRANSIT_MUNI.ROUTES.route_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.STOP_MONITORING.trip_id -> SAN_FRANCISCO_TRANSIT_MUNI.TRIPS.trip_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.STOP_MONITORING.vehicle_id -> SAN_FRANCISCO_TRANSIT_MUNI.VEHICLE_MONITORING.vehicle_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.STOP_TIMES.stop_id -> SAN_FRANCISCO_TRANSIT_MUNI.STOPS.stop_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.STOP_TIMES.trip_id -> SAN_FRANCISCO_TRANSIT_MUNI.TRIPS.trip_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.TRIPS.trip_id -> SAN_FRANCISCO_BIKESHARE.BIKESHARE_TRIPS.trip_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.TRIPS.route_id -> SAN_FRANCISCO_TRANSIT_MUNI.ROUTES.route_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.TRIPS.shape_id -> SAN_FRANCISCO_TRANSIT_MUNI.SHAPES.shape_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.VEHICLE_MONITORING.route_id -> SAN_FRANCISCO_TRANSIT_MUNI.ROUTES.route_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.VEHICLE_MONITORING.trip_id -> SAN_FRANCISCO_TRANSIT_MUNI.TRIPS.trip_id`
- `SAN_FRANCISCO_TRANSIT_MUNI.VEHICLE_MONITORING.vehicle_id -> SAN_FRANCISCO_TRANSIT_MUNI.STOP_MONITORING.vehicle_id`

### 7.4 schema 文件格式

`spatialmas/schema/loader.py` 依赖固定格式解析 schema 文件，编辑时不要随手改版式。

基本结构是：

- `## 架构名.表名`
- `# Rows: N`
- 两个空格缩进的列定义行
- `# Sample data:` 示例数据
- `## Relationships` 关系区

列定义要保留列名、类型和空值标记。关系区不会被表解析器当作表定义。

### 7.5 生成脚本的行为

`scripts/generate_schema.py` 会：

- 连接 Snowflake
- 枚举 schema 与表
- 执行 `DESCRIBE TABLE`
- 抽取少量样例行
- 统计行数
- 按 `_id` 规则推断关系
- 写回 `schema/schema.txt`
- 如 `schema/rules.json` 不存在，则补上默认规则文件

## 8. 配置

### 8.1 LLM 配置

- `OPENAI_API_KEY`：必需
- `OPENAI_API_BASE`：可选，默认 `https://openrouter.ai/api/v1/`
- `MODEL`：必需，默认 `openai/gpt-4.1-mini`

### 8.2 Snowflake 配置

- `SNOWFLAKE_USER`：必需
- `SNOWFLAKE_PASSWORD`：必需
- `SNOWFLAKE_ACCOUNT`：必需
- `SNOWFLAKE_DATABASE`：可选，默认 `SAN_FRANCISCO_PLUS`

### 8.3 运行时配置

- `QUERY_TIMEOUT_SECONDS`：默认 `30`
- `DEFAULT_RESULT_LIMIT`：默认 `1000`
- `MAX_RESULT_LIMIT`：默认 `5000`

### 8.4 schema 路径配置

- `SCHEMA_PATH`：默认 `schema/schema.txt`
- `SCHEMA_DETAILED_PATH`：旧兼容变量，只有在 `SCHEMA_PATH` 为空时才会被读取
- `SCHEMA_RULES_PATH`：默认 `schema/rules.json`

### 8.5 加载方式

`spatialmas/config.py` 在导入时会执行 `load_dotenv()`，所以 `.env` 会自动生效。

## 9. 安全与 SQL 规则

### 9.1 只读约束

`SQLValidationService` 只允许只读 SQL：

- 必须以 `SELECT` 或 `WITH` 开头
- 不能包含写操作或危险操作关键字
- 关键字检查包含：`INSERT`、`UPDATE`、`DELETE`、`DROP`、`ALTER`、`TRUNCATE`、`CREATE`、`MERGE`、`GRANT`、`REVOKE`、`CALL`、`COPY`

### 9.2 LIMIT 处理

- 如果 SQL 没有 `LIMIT`，系统会自动补上
- 请求的 `limit` 会被夹在默认值和最大值之间

### 9.3 时间字段处理

- 如果 SQL 出现年份区间 `BETWEEN 2014 AND 2017`，系统会尝试改写成微秒时间戳区间
- 如果语句看起来像在处理时间字段，但没有做微秒归一化，会给出警告

### 9.4 执行层

`SnowflakeClient.execute_read_query()` 会：

- 在会话里设置查询超时
- 只抓取指定上限的结果
- 把日期、时间、Decimal、二进制值转换成 JSON 安全格式
- `QueryService` 遇到裸的 `invalid identifier` 时，会尝试把同名列补成双引号再重跑一次；如果还是失败，`execute_db_query` 会返回结构化错误 JSON，不会直接把整条 CLI 弄崩

### 9.5 SQL 生成规则

生成 SQL 时要遵守 `schema/rules.json` 里的约束，尤其是：

- 只用提供的 schema 里的表和列
- 列引用要保留双引号
- 表名和架构名保持原样，不要额外乱加引用
- 优先显式 join
- 保持只读
- 数值型日期/时间字段如果存的是 epoch 微秒，要先 `/1000000` 再 `TO_TIMESTAMP`，然后再取年/月/日
- 大结果集要加 LIMIT

## 10. 结果分析

`AnalysisService` 使用 pandas 和 numpy，对查询结果做基础分析。

支持的分析类型：

- `basic`
- `statistical`
- `trend`
- `comprehensive`

通常会返回：

- 行数
- 列名
- 数值列描述统计
- 相关性矩阵
- 趋势斜率
- 分类列摘要
- 结论和建议

当结果为空时，会返回空结果提示；当样本太小时，会提示扩大查询范围。

## 11. 测试与验证

当前测试主要有两个：

- `tests/test_sql_guard.py`
- `tests/test_schema_relationships.py`

它们覆盖的重点是：

- 非只读 SQL 会被拒绝
- `LIMIT` 会被补上
- 年份 `BETWEEN` 会被改写成微秒范围
- schema 仓库能成功加载表定义
- 指定表 `SAN_FRANCISCO_BIKESHARE.BIKESHARE_TRIPS` 能被找到

修改 SQL 规则、schema 解析、关系推断、工具接口或直执行脚本时，要至少跑：

- `pytest`
- `python scripts/validate_schema.py`
- `python main.py "Show a sample summary from available tables"`（如果改了 CLI 入口或工具编排）
- `python db.py --help`（如果改了直执行脚本；有 Snowflake 环境时再跑一个只读 `SELECT`）
- `python test.py`（如果改了批量跑题脚本或 `questions.md` / `answers/` 的格式）

如果改了 schema 生成逻辑，最好再跑一次 `python scripts/generate_schema.py`，确认输出文件还能被当前 loader 正常读取。

## 12. 参考提示词与文档

### 12.1 prompts

- `prompts/deep_research_system_prompt.md`：给多轮研究式分析用的提示词，强调假设、查询、证据和下一步
- `prompts/research_questions.txt`：示例研究问题

这两个文件目前更像独立资产，不是核心运行链路里的必需输入，但它们体现了项目想要支持的研究风格。

### 12.2 paperworks

`paperworks/` 下是项目过程性材料，主要包括：

- 架构图
- 流程图
- 中期报告
- 开题或申报材料
- 参考文献与论文资料
- 汇报 PPT 和讲稿

这些文件主要用于说明项目背景，不属于运行时代码。

## 13. 给后续 agent 的硬性要求

1. 任何对本项目的修改，都必须反映到这个文件中。
2. 代码、配置、schema、prompt、脚本、测试、依赖、命令、目录结构只要有变化，就要同步更新对应章节。
3. 如果行为变了，不要只改实现，不改说明。
4. 如果不确定当前状态，先看源码和实际文件，不要靠猜。
5. 如果一次改动影响多个模块，既要改代码，也要把本文件中的相关说明一起改掉。
6. 如果修改导致某些条目失效，删掉或重写对应描述，不要留下过期信息。

## 14. 当前快照

- 仓库用途：面向 Snowflake 的空间与表格分析 CLI 项目
- 运行入口：`python main.py` / `python db.py` / `python test.py`
- 工具数：4
- 当前 schema：20 表，20 关系
- 默认数据库：`SAN_FRANCISCO_PLUS`
- 当前 schema 文件生成时间：`2026-05-20 16:13`

## 15. 变更记录

- 2026-05-25：将仓库收敛为 CLI-only 运行方式，移除服务端入口与依赖，并同步更新项目结构、schema、约束和维护要求；后续任何项目改动都要同步更新本文件。
- 2026-05-25：暂时移除安装后的命令入口，只保留 `python main.py` 直接运行入口；同步更新项目说明。
- 2026-05-25：新增 `db.py` 直执行脚本，支持 `python db.py "SELECT ..."` 直接跑只读 SQL，并复用现有 Snowflake 连接与结果输出。
- 2026-05-25：新增 `questions.md` / `test.py` / `answers/` 的批量评测链路；`test.py` 会逐题调用 `main.py`，实时把 stdout 打到控制台，并在结束时覆盖写入 `answers/` 下的单独 Markdown 文件，且文件内保留完整运行日志。
