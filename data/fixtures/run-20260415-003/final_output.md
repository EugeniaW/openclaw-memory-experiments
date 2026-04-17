[2026-04-17 10:48 AM] eu-assistant: How an OpenClaw-based research bot could be improved for long-session memory tasks

A. Problem framing

这里的问题不是“有没有 memory”，而是：

一个基于 OpenClaw 的 research bot，在长 session / 多轮任务 / 跨轮次研究里，为什么会逐渐变差，以及该怎么改。

“long-session memory tasks” 可以理解为几类场景：

• 长时间做同一份研究
• 多次迭代同一主题的报告
• 多轮积累判断、对比、来源、结论
• 需要在后续步骤里稳定复用前面已经得到的结构化信息

───

likely known

• 长 session 里，模型会受到上下文窗口、注意力分配、信息检索质量、状态漂移等问题影响。
• OpenClaw 这类 agent 框架通常已经有：
• session context
• workspace files
• memory search
• 外部文件读写
所以问题不只是“能不能存下来”，而是“后续能不能稳定拿对、用对”。

inferred

• 对 research bot 来说，memory failure 往往不是单点问题，而是三段链条里的某一段出错：

1. 记住了没有
2. 找到了没有
3. 用对了没有

unclear

• 在 OpenClaw 的具体实现里，当前主要瓶颈到底更偏 retrieval 还是 reasoning integration：uncertain
• 不做实验前，不能断言“memory system 本身差”还是“agent 使用 memory 的 prompt discipline 不够好”：uncertain

───

B. Long-session memory 的主要瓶颈

1. 记忆写入粒度不稳定

likely known

• 如果 memory 写得太原始，会变成日志堆积。
• 如果写得太抽象，会丢失后续可复用的关键上下文。
• research task 很依赖“半结构化中间产物”，例如：
• competitor list
• source judgments
• uncertain points
• rejected hypotheses
• final takeaways

inferred

• 很多 memory 系统的问题不是没写，而是写入粒度不一致：
• 有时写 raw notes
• 有时写 final summary
• 却缺少可复用的 task-state layer

unclear

• 当前 OpenClaw 工作流里，最缺的是：
• summary memory
• task-state memory
• source memory
哪一层占主瓶颈：uncertain

───

2. 检索命中不等于可用

likely known

• semantic search 能找到“相关文本”，但不保证找到“当前步骤最有用的信息”。
• 对 research bot 来说，相关不等于可操作。

inferred

• memory_search 适合召回，但未必适合直接驱动后续 research step。
• 如果没有更强的 memory typing，agent 很容易拿到：
• vaguely related snippets
• 但不是“当前问题需要的那个结构化结论”。

unclear

• retrieval 失败主要来自 embedding-level recall，还是 memory schema 太弱：uncertain

───

3. 已有结论在后续步骤中容易漂移

likely known

• 长 session 中，模型容易对先前判断进行改写、弱化、遗忘或重述变形。
• 这在 research task 里尤其明显，因为结论常常会在：
-搜集信息
-写比较
-写结论
三个环节被重复表达。

inferred

• 真正的问题不是“忘了”，而是同一结论跨步骤表达不一致。
• 这会导致：
• 前面说 A
• 后面写成 A'
• 最后总结成更弱或更泛的版本

unclear

• 这种漂移更多来自模型自然生成，还是缺少 explicit state pinning：uncertain

───

4. 事实、推断、待确认项混在一起

likely known

• research 场景里，不同信息状态必须区分：
• observed
• inferred
• uncertain
• 如果混在一起，后续很容易把推断当事实复用。

inferred

• 很多 long-session memory failure 其实是epistemic labeling failure：
• 没给每条记忆打上“我为什么相信它”的标签
• 后续步骤就只能把所有历史内容当同一种东西处理

unclear

• 给 memory 加状态标签后，效果会提升多少：uncertain

───

5. 缺少“任务态 memory”，只有“历史 memory”

likely known

• 长任务中需要的不只是历史记录，还需要当前任务状态：
• 当前研究问题
• 已确认的竞争格局
• 已排除方向
• 待补证据
• 当前版本结论

inferred

• OpenClaw 式 memory 如果主要依赖：
• MEMORY.md
• daily memory
• semantic recall
那它更像“长期记忆”与“会话痕迹”，不一定足够支撑复杂 research 的任务态控制。

unclear

• 现有 workspace file + memory file 机制是否已足够，只是 agent 没用好：uncertain

───

C. 这些瓶颈分别更像 storage、application、consistency 中的哪一类问题

| 瓶颈                     | 更像哪类问题                    | 为什么                           |
| ---------------------- | ------------------------- | ----------------------------- |
| 写入粒度不稳定                | storage                   | 先存什么、怎么存就已经不稳                 |
| 检索命中不等于可用              | application               | 找到了信息，但没法直接转成当前步骤可执行状态        |
| 结论在后续步骤中漂移             | consistency               | 同一判断跨轮次表达不稳                   |
| 事实 / 推断 / uncertain 混淆 | consistency + application | 既影响知识状态一致性，也影响后续如何使用          |
| 缺少任务态 memory           | storage + application     | 没把 task state 显式存下来，后续也无法正确调用 |

───

likely known

• 这不是单纯 storage 问题。
• 单纯“多存一点”不会自动解决 long-session memory。

inferred

• 对 research bot 来说，application 和 consistency 往往比 storage 更关键。
• 因为很多信息其实已经在文件里，只是没有被稳定调用和约束。

unclear

• 三类问题里哪一类占比最大，必须靠任务级实验验证：uncertain

───

D. 一个短期可做的改进方案

方案：引入“task-state memory file”

为每个 research task 增加一个明确的、机器可读也人可读的状态文件，而不只依赖普通 memory notes。

例如：

# task_state.md

## research question
## scope
## confirmed points
## inferred points
## uncertain points
## excluded paths
## current competitor set
## current working conclusion
## next missing evidence

───

likely known

• 把当前任务状态显式外置，通常能降低模型在长 session 中的漂移。
• research task 特别适合这种方法，因为中间
[2026-04-17 10:48 AM] eu-assistant: 状态本来就重要。

inferred

• 一个简单但有效的做法是：
• 每轮关键产出后
• 强制更新 task_state.md
• 后续步骤先读 task_state，再继续工作
• 这会比只依赖长上下文回忆更稳。

unclear

• 手动更新 task_state 的成本是否会抵消收益：uncertain
[2026-04-17 10:48 AM] eu-assistant: • 什么粒度最合适：每步更新、每阶段更新、还是 only-on-checkpoint：uncertain

───

短期方案的核心原则

1. 把任务态和长期记忆分开
2. 把 confirmed / inferred / uncertain 分开
3. 把当前 working conclusion 固定下来
4. 把待补证据列出来，避免“忘记为什么还不确定”

───

E. 一个中期系统化改进方案

方案：把 memory 拆成 3 层

Layer 1 — durable memory

长期偏好、长期项目、稳定背景知识
例如：

• 用户长期研究偏好
• 经常用的分析框架
• 固定写作标准

Layer 2 — task-state memory

当前研究任务的中间状态
例如：

• 当前主题
• 已确认结论
• candidate competitor list
• evidence gaps
• current draft stance

Layer 3 — source-grounded findings

和具体来源或观察绑定的 findings
例如：

• “Product X seems workflow-first”
• evidence status = observed / inferred / uncertain
• supporting snippet or internal citation pointer

───

likely known

• 分层 memory 一般比单一 memory 池更适合复杂任务。
• research bot 尤其需要把“任务状态”和“长期记忆”拆开。

inferred

• 如果 OpenClaw-based bot 要系统改进，重点不该只是提升 retrieval，而是要让 agent 明确知道：
• 现在该读哪一层 memory
• 当前输出允许用哪一层结论
• 哪些内容必须被标 uncertain

unclear

• 这种分层应该主要通过：
• 文件约定
• skill 约定
• agent prompt 约束
• 还是额外 tooling
来实现：uncertain

───

中期方案的附加机制

1. memory schema

每条 finding 至少包含：

• claim
• status: likely known / inferred / unclear
• task relevance
• last updated step

2. checkpoint compaction

不是把所有历史压成摘要，而是压成：

• stable conclusions
• unstable hypotheses
• open questions

3. contradiction check

新结论写入前，检查是否与已有 task-state 冲突。

───

F. 3 个最值得优先验证的实验问题

1. 显式 task-state 文件能否显著降低长 session 漂移？

likely known

• 这是一个高价值、低成本实验。

inferred

• 如果有效，收益可能直接体现在：
• 更少重复推理
• 更稳定的结论口径
• 更少把 uncertain 说成 settled

unclear

• 改善幅度有多大：uncertain

───

2. 给每条 memory 加 epistemic label 是否能改善 research quality？

也就是强制标：

• likely known
• inferred
• unclear

likely known

• 这会提升输出时的知识状态透明度。

inferred

• 对 research bot 来说，这可能比“提高记忆容量”更重要。
• 因为很多错误不是忘记，而是误用历史内容。

unclear

• 这是否会让流程变得太重、降低速度：uncertain

───

3. retrieval 该优先召回“task-state”还是“semantic nearest notes”？

likely known

• 两者不是一回事。
• 最近似的文本，不一定是当前最有用的状态。

inferred

• 对长 research 任务，优先召回 task-state 可能比优先召回历史碎片更稳。

unclear

• 最佳策略是：
• task-state first
• hybrid retrieval
• 还是 stage-dependent retrieval
：uncertain

───

G. Confidence note

likely known

• long-session memory 问题不只是 storage，不少问题发生在 application 和 consistency。
• research bot 比一般聊天 bot 更需要显式任务状态。
• 把事实、推断、uncertain 分开是有价值的。
• 单纯依赖长上下文和语义召回，不足以稳定支撑复杂多轮研究。

inferred

• 一个 OpenClaw-based research bot 的短期最优改进，很可能不是更复杂模型，而是更清晰的 memory structure。
• task-state memory 可能是最值得优先试的低成本改进。
• 分层 memory + epistemic labeling 是比“更多摘要”更系统的方向。

unclear

• 不做实验前，不能断言哪个瓶颈最大。
• 不能断言 schema 化 memory 一定带来净收益。
• 不能断言这些改进对所有 research task 都同样有效：uncertain

如果你要，我可以下一步把这份内容继续压成一版 更像产品策略 memo 的 1-page version。