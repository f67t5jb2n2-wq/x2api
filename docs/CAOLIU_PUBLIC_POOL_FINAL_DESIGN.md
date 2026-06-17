# 草榴社区公共池与双层检索最终方案

## 1. 文档目标

本文档定义 `草榴社区` 接入后的最终态方案，并顺带统一 `items` / `feed` / OpenSearch / PostgreSQL 的内容模型。

这不是过渡方案，也不是“先兼容后再看”的方案。本文档定义的目标是一次性切到最终态：

- `items` 支持公共池检索
- `feed` 继续支持公共池视频流
- 成人内容有统一、可插拔、可查询的标记
- 一个帖子可以同时承载图文父层和多个视频子层
- OpenSearch 成为统一查询模型，PostgreSQL 保留关系锚点与行为数据
- 旧文档和旧索引通过一次迁移切换，不保留长期混合逻辑

## 2. 当前现状与问题

### 2.1 已确认的现状

当前代码里，`items` 和 `feed` 的检索边界并不一致：

- `items` 只查用户订阅目标，不查公共池
  - 见 `service/src/lib/opensearch-item-service.ts`
  - `getSubscribedTargetIds()` 只读取 `subscriptions`
  - `buildItemsQuery()` 在无订阅时直接压入 `target_id = __no_subscriptions__`
- `feed` 已支持公共池
  - 见 `service/src/lib/feed-engine.ts`
  - `sourceFilter()` 已支持 `public` / `user` / `all`
- 敏感内容标记已经存在
  - `target_profiles.category`
  - `categories.is_sensitive`
  - `collector/opensearch_items.py` 会把 `category` / `is_sensitive` / `is_public_pool` 写入 OpenSearch
- 查询主链路是 OpenSearch，不是直接查 PostgreSQL 内容表
  - `service/src/app/api/items/route.ts`
  - `service/src/lib/item-service.ts`
  - `service/src/lib/opensearch-item-service.ts`

### 2.2 当前模型为什么接不住草榴

`草榴社区` 这类源有三个特征：

- 帖子是“父层内容”，视频只是帖子里的一个或多个媒体变体
- 有的帖子只有图片，没有视频
- 有的帖子一个父帖里会带多个视频

当前单层模型的问题是：

- `items` 与 `feed` 共用一层文档，无法明确区分“帖子卡片”和“视频卡片”
- 一个帖子多个视频时，无法稳定表达“1 个父项 + N 个视频子项”
- 如果只保留视频项，会丢失“有图的楼主帖”这一父层入口
- 如果只保留帖子项，`feed` 无法稳定按视频粒度排序、去重、埋点、失效处理

结论：必须采用双层模型，而不是继续把所有内容塞进单层 `item` 文档。

## 3. 最终决策

### 3.1 方案结论

采用“父层 entry + 子层 video_variant”的双层模型。

- `items` 只返回父层 `entry`
- `feed` 只返回子层 `video_variant`
- 一个内容源可以只有父层，也可以有父层加多个子层
- 公共池仍然是“目标级属性”，不是“单条内容临时属性”
- 成人标记仍然以分类体系为准，不在每个解析器里各写一套规则

### 3.2 对草榴的产品定位

`草榴社区` 不进入用户手动订阅语法，不走“用户自己新增一个 caoliu 目标”的前端主流程。

它的定位是：

- 系统维护的 `site` 目标
- `target_profiles.scope = 'system'`
- `target_profiles.is_public_pool = true`
- `target_profiles.category = 'adult'`
- `target_profiles.tags` 默认包含 `["草榴社区", "成人"]`

这意味着：

- 前端不需要把 `caoliu:` 当作普通订阅源暴露给用户
- 前端通过 `items` / `feed` 的公共池模式消费该源
- 如果未来需要私有化运行，同一解析器也可以把目标写成 `is_public_pool = false`

## 4. 数据模型

### 4.1 `target_profiles` 不改表

`target_profiles` 已经有足够的目标级语义：

- `scope`
- `tags`
- `category`
- `weight`
- `is_public_pool`

因此：

- `target_profiles` 不新增字段
- 成人标记继续由 `category = 'adult'` 驱动
- 是否进入公共池继续由 `is_public_pool` 驱动

### 4.2 `items` 必须改表

最终态下，`items` 不能再只承载“单层内容锚点”。它必须同时承载：

- 父层内容项 `entry`
- 视频子项 `video_variant`

建议对 `items` 增加以下字段：

```sql
ALTER TABLE items
ADD COLUMN item_role TEXT NOT NULL DEFAULT 'entry',
ADD COLUMN parent_item_id UUID REFERENCES items(id) ON DELETE CASCADE,
ADD COLUMN group_key TEXT,
ADD COLUMN variant_key TEXT,
ADD COLUMN variant_index INTEGER;

ALTER TABLE items
ADD CONSTRAINT items_role_check
CHECK (item_role IN ('entry', 'video_variant'));

CREATE INDEX idx_items_role_expires
ON items (item_role, expires_at DESC, stored_at DESC);

CREATE INDEX idx_items_parent_item
ON items (parent_item_id);

CREATE INDEX idx_items_group_key
ON items (group_key);

CREATE UNIQUE INDEX idx_items_parent_variant_key
ON items (parent_item_id, variant_key)
WHERE item_role = 'video_variant' AND variant_key IS NOT NULL;
```

字段含义：

- `item_role`
  - `entry` 表示父层帖子/推文/图文项
  - `video_variant` 表示可播放视频子项
- `parent_item_id`
  - 仅子项填写，指向父层 `entry`
- `group_key`
  - 同一原始内容的稳定分组键
  - 例如 Twitter 用原始状态 ID，草榴用线程 ID
- `variant_key`
  - 同一父项下某个视频的稳定键
  - 优先用归一化视频 URL、播放器资源 ID、嵌入 ID 等可复现值
- `variant_index`
  - 仅用于展示顺序，不能作为唯一身份

### 4.3 为什么必须改 `items` 表

不改表会直接带来三个问题：

- `feed_events` / `video_stats` 只能挂在一个 `item_id` 上，多个视频必须有多个真实子项
- 图片帖如果没有父层 `item` 锚点，就无法参与统一清理、重建、回查
- 迁移后如果只在 OpenSearch 里做“虚拟父项”，数据库与索引会长期失真，后续运维成本更高

因此最终结论是：

- `target_profiles` 不改
- `items` 必改
- `feed_events` / `video_stats` 不改，继续挂真实视频子项

## 5. OpenSearch 最终文档模型

## 5.1 统一原则

OpenSearch 是查询主模型，必须一次性补齐最终字段，不保留“旧文档没有这些字段时再猜”的长期兼容逻辑。

所有索引文档统一增加以下字段：

```json
{
  "doc_schema_version": 2,
  "item_role": "entry | video_variant",
  "parent_item_id": "uuid-or-null",
  "group_key": "stable-group-key",
  "variant_key": "stable-variant-key-or-null",
  "variant_index": 0,
  "has_images": true,
  "has_video": false,
  "image_count": 3,
  "video_count": 0,
  "is_public_pool": true,
  "category": "adult",
  "is_sensitive": true
}
```

现有字段继续保留并沿用：

- `id`
- `target_id`
- `guid`
- `video_url`
- `cover_url`
- `title`
- `caption`
- `content`
- `author`
- `link`
- `images`
- `published_at`
- `stored_at`
- `expires_at`
- `video_url_expires_at`
- `source`
- `target`
- `target_link`
- `kind`
- `tags`

### 5.2 父层 `entry` 文档

父层文档用于 `items` 列表，要求：

- `item_role = entry`
- `video_url = null`
- `parent_item_id = null`
- `images` 保留楼主层全部图片
- `has_images` / `has_video` / `video_count` 必须准确
- 若帖子有多个视频，父层只负责描述，不直接承担播放

### 5.3 子层 `video_variant` 文档

子层文档用于 `feed`，要求：

- `item_role = video_variant`
- `video_url` 必填
- `parent_item_id` 必填
- `group_key` 与父层一致
- `variant_key` 稳定且可复现
- `cover_url` 可继承父帖首图或视频封面
- `title` 默认继承父帖标题，可追加序号后缀

### 5.4 为什么不继续用单层文档

单层文档会把两个完全不同的消费场景绑死：

- `items` 需要“帖子视角”
- `feed` 需要“视频视角”

双层模型之后：

- `items` 不再被视频粒度污染
- `feed` 不再被图片帖噪音污染
- 一个帖子多个视频天然展开成多个可埋点、可下线、可排序的独立视频项

## 6. 查询与接口契约

### 6.1 `items` 接口新增公共池查询能力

`items` 接口增加 `sourceScope` 参数，取值：

- `user`
- `public`
- `all`

推荐直接复用 `source` 这个名称也可以，但为了避免与已有 `target/source` 文本筛选语义混淆，最终实现建议使用 `sourceScope`。

契约如下：

- `sourceScope=user`
  - 只查订阅目标
- `sourceScope=public`
  - 只查 `is_public_pool = true`
- `sourceScope=all`
  - 查“订阅目标 + 公共池”

默认值建议：

- 默认 `user`

原因：

- 不破坏现有“订阅驱动”的 `items` 行为
- 前端如果要做公共池，只需显式请求 `public` 或 `all`
- 没有公共池时，接口自然返回空，不需要额外兼容分支

`items` OpenSearch 过滤条件固定增加：

- `item_role = entry`
- `expires_at > now`
- 原有标签、分类、关键词过滤保持可用

### 6.2 `feed` 接口继续用公共池模型

`feed` 继续保留当前 `public` / `user` / `all` 的模式，但统一改为只读子层：

- `item_role = video_variant`
- `video_url_expires_at > now`
- 原有公共池/订阅并集逻辑保持

多视频的处理方式：

- 一个视频子项就是一个 feed 卡片
- 同父项多个视频允许同时进入 feed
- 去重粒度为 `variant_key`，不是父项 `group_key`

### 6.3 空池与无内容行为

系统必须天然支持“无公共池”与“某源暂无内容”：

- `items?sourceScope=public`
  - 无公共池时返回空列表
- `items?sourceScope=all`
  - 有订阅但无公共池时，只返回订阅内容
  - 无订阅但有公共池时，只返回公共池内容
  - 两者都没有时返回空列表
- `feed` 同理

这意味着公共池是可插拔能力，不会绑死其他解析器。

## 7. 成人内容标记

### 7.1 canonical 标记位置

成人标记不应该散落在每个解析器里，而应该继续走现有分类体系：

- `target_profiles.category = 'adult'`
- `categories.is_sensitive = true`

OpenSearch 写入时统一派生：

- `category = 'adult'`
- `is_sensitive = true`

### 7.2 草榴默认策略

`草榴社区` 目标默认写入：

```text
scope = system
is_public_pool = true
category = adult
tags = ["草榴社区", "成人"]
```

效果：

- `items` / `feed` 都能直接返回 `is_sensitive = true`
- 分类接口可继续使用 `adult`
- 前端可继续用 `categories.default_hidden` 决定默认折叠或默认隐藏

### 7.3 可插拔要求

同一套模型必须支持非成人公共池源，因此：

- `category` 可以为空
- `is_sensitive` 默认为 `false`
- `is_public_pool` 默认为 `false`

当这些字段为空或为假时，查询不报错，只是自然不进入对应筛选。

## 8. 草榴社区采集契约

### 8.1 调度

固定调度要求：

- 目标名称：`草榴社区`
- 入口：`https://t66y.com/thread0806.php?fid=16`
- 周期：每 4 小时一次
- 范围：仅抓前 5 页

建议 workflow cron：

```text
0 */4 * * *
```

### 8.2 目标建模

数据库目标：

- `source = 'caoliu'`
- `kind = 'site'`
- `value = 'https://t66y.com/thread0806.php?fid=16'`
- `normalized_value` 为该入口的归一化站点键

该目标由系统创建和维护，不要求用户手动订阅。

### 8.3 内容准入规则

仅保留满足以下条件的帖子：

- 有标题
- 只取楼主层内容
- 楼主层至少有 1 张图片

补充规则：

- 回复层全部忽略
- 无图帖直接丢弃
- 有视频则额外提取视频变体
- 无视频但有图的帖子，仍然保留父层 `entry`

### 8.4 入库规则

每个合格帖子至少生成 1 个父层 `entry`：

- `guid = caoliu:thread:<threadId>`
- `item_role = entry`
- `group_key = caoliu:thread:<threadId>`
- `images = 楼主层图片列表`
- `title = 帖子标题`
- `link = 详情页链接`

每个可播放视频额外生成 1 个子层 `video_variant`：

- `guid = caoliu:thread:<threadId>#video:<variantKey>`
- `item_role = video_variant`
- `parent_item_id = 父层 id`
- `group_key = caoliu:thread:<threadId>`
- `variant_key = 归一化视频资源键`
- `variant_index = 楼主层出现顺序`

### 8.5 多视频处理规则

多个视频不做聚合播放，也不塞回父层，而是直接展开成多个子项。

理由：

- `feed` 的消费单位就是“一个可播放视频”
- 每个视频需要独立埋点、独立失效、独立下线
- 同帖多个视频如果合并成一个项，会把播放失败、去重和推荐排序全部搞复杂

## 9. 对其他解析器的影响

### 9.1 解析器改造原则

所有解析器统一遵循以下规则：

- 每条原始内容至少写 1 个父层 `entry`
- 如果存在 1 个视频，则额外写 1 个 `video_variant`
- 如果存在多个视频，则写多个 `video_variant`
- 没有视频的内容只写 `entry`

### 9.2 对现有单视频源的影响

现有单视频源改造后变成：

- 1 个父层 `entry`
- 1 个子层 `video_variant`

这会比现在多一层父项，但可以彻底统一模型，避免未来继续分叉。

### 9.3 对 Twitter / YouTube / 关键词的影响

这些源仍然可以继续走原来的订阅模型，只是写入结构统一为双层：

- 列表检索看父项
- 视频流检索看子项

换句话说：

- 订阅模型不废弃
- 公共池模型也不再只属于 `feed`
- 两者在 OpenSearch 层完成统一

## 10. 迁移与切换

### 10.1 不做长期兼容分支

旧文档没有这些字段、旧索引没有这些字段，这不是运行时兼容问题，而是迁移问题。

最终要求：

- 新服务代码只读新索引模型
- 不保留“字段不存在时自动猜旧语义”的长期逻辑
- 通过一次完整迁移解决历史数据问题

### 10.2 PostgreSQL 迁移顺序

1. 给 `items` 增加双层字段
2. 回填历史数据

历史回填规则：

- 无 `video_url` 的旧行
  - 直接标记为 `entry`
- 有 `video_url` 的旧行
  - 保留原 `id` 作为 `video_variant`
  - 为其补插一个新的父层 `entry`
  - 子项 `parent_item_id` 指向新父项
  - `group_key` 使用原始 `guid`

这样做的原因：

- `feed_events` / `video_stats` 继续沿用老的真实视频 `item_id`
- 不需要迁移行为表外键
- `items` 列表从新插入的父项读取

### 10.3 OpenSearch 切换策略

必须使用新索引，不在旧索引上硬补字段。

建议：

1. 创建新索引，例如 `x2_items_v2`
2. 通过重建任务把旧索引文档 + PostgreSQL 关系字段合成新文档
3. 服务读取别名，例如 `x2_items_active`
4. 重建完成后把别名从旧索引切到 `x2_items_v2`

### 10.4 为什么重建不能只靠 PostgreSQL

当前 PostgreSQL `items` 已经是轻量锚点，不再保存完整正文、图片、标题等重内容。

因此新索引重建的数据来源必须是：

- 旧 OpenSearch 文档
- PostgreSQL 的 `items`
- PostgreSQL 的 `targets`
- PostgreSQL 的 `target_profiles`
- PostgreSQL 的 `categories`

也就是说：

- 关系层从 PostgreSQL 补
- 重内容从旧 OpenSearch 补

### 10.5 文档切换策略

从本次方案开始：

- 本文档是公共池与双层检索的设计基线
- `docs/SERVICE_API.md` 需要在实现合入时同步改写为最终接口文档
- 不允许仓库长期同时维护两套互相矛盾的接口描述

## 11. 验证与验收

### 11.1 解析器验收

`草榴社区` 解析器必须验证：

- 前 5 页能稳定抓取
- 只保留楼主层
- 无图帖被丢弃
- 有图帖能生成父项
- 有视频帖能生成父项 + 多个视频子项
- 重复抓取不会重复插入同一 `variant_key`

### 11.2 查询验收

`items` 必须验证：

- `sourceScope=user` 只返回订阅父项
- `sourceScope=public` 只返回公共池父项
- `sourceScope=all` 返回并集父项
- 敏感分类字段与 `is_sensitive` 正确返回

`feed` 必须验证：

- 只返回 `video_variant`
- 公共池过滤正确
- 同帖多个视频会展开成多个卡片
- 删除一个失效视频不会影响同父帖的其他视频

### 11.3 迁移验收

必须验证：

- 历史单视频内容被正确拆成“父项 + 原视频子项”
- 历史纯图文内容仍能在 `items` 中查询到
- 别名切换后，服务代码不依赖旧字段兜底
- 回滚时只需把 OpenSearch 别名切回旧索引

### 11.4 最终发布口径

只有以下四件事同时完成，才算真正闭环：

1. PostgreSQL 双层字段迁移完成
2. OpenSearch 新索引重建完成
3. `items` / `feed` 查询改到最终态
4. `草榴社区` 定时抓取与验证脚本跑通

## 12. 实施清单

按工程顺序，落地任务应为：

1. 修正当前 WIP，撤掉把 `caoliu` 暴露为普通订阅目标的前端解析逻辑
2. 给 `items` 表增加双层字段与索引
3. 改造采集写入链路，统一写父项和视频子项
4. 改造 OpenSearch 文档结构并新增 `doc_schema_version = 2`
5. 改造 `items` 查询，新增 `sourceScope` 且只查父项
6. 改造 `feed` 查询，只查视频子项
7. 构建历史回填与 OpenSearch 重建脚本
8. 接入 `草榴社区` 的 4 小时定时任务
9. 跑解析器测试、查询测试、重建验证、真实源 dry-run
10. 切别名上线

## 13. 最终结论

这次接 `草榴社区`，本质上不是“再加一个成人站点解析器”，而是把当前内容模型从单层升级成“父帖列表 + 视频流子项”的统一架构。

最终结论明确如下：

- `items` 要加公共池能力
- `feed` 继续吃公共池，但只吃视频子项
- `target_profiles` 不改表
- `items` 必改表
- 成人标记继续走 `category=adult` + `is_sensitive=true`
- `草榴社区` 作为系统公共池目标接入，不走普通用户订阅输入
- 旧文档和旧索引通过一次迁移切换解决，不保留长期兼容逻辑
