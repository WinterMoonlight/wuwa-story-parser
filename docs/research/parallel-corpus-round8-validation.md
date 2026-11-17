# 第八轮：实体触发与手机消息调用锚点

2026-11-17，3.8.11快照，基线20261117_124337_124773。三路分别核查实体触发、手机阅读节点、跨来源主干锚点，主agent统一整合。27处回顾阻塞及3段30事件前缀保持，资产和原始数据库不动。

## 已定位：两条手机消息的回顾提示位置

《影面颠倒的兔影》165800000，节点38发送32000（14事件）、节点43发送32001（9事件）。两节点Condition精确要求同消息ReadPhoneMessage/CompleteMessage，TrackCustomBoard再次指向同消息。TidTip在任务和回顾各唯一，分别为Quest_165800000_ChildQuestTip_165_1和Quest_165800000_ChildQuestTip_165_6，对应回顾原始entry_index 0、5，Flow严格为空名与0/0。

这证明配置中的阅读步骤有明确回顾位置，而不是发送后即刻读完。两段分别作为独立手机区段插到提示位置，不附在任意邻近对白末尾。原始流程segments不增加、不改顺序；新增backbone.phone_tip_insertions保留事件和原消息、任务节点、发送动作、条件、回顾条目、祖先证据。task_order_verified/read_completion_verified/runtime_verified仍false。

通用规则同时要求：唯一任务节点与提示、唯一同ID发送（异步/异常形状的重复发送也计入冲突）、唯一外部消息来源、精确消息追踪板、无缺失文字、消息流程不已存在回顾、祖先仅已验证Sequence形状。周围动作只允许精确SetAudioState/GetItem/ShowHidedGroup形状，不接受未知控制字段、异步发送、非完整阅读条件、跨任务条件或有正文的回顾Flow条目。

TXT按entry_index把手机区段放在相应提示处，仍保留消息内部选项、说话人和表情未核验占位。原external_content源证据留JSON，重复记录标记text_duplicate_of/counted_elsewhere，不在附录重复打印或重复计数。23事件是既有材料归位，不是23条新台词或新增完整任务。

## 保留：其他手机消息

批量验证还命中同形案例121000040《昨夜群星》：节点164发送33006并要求CompleteMessage、同ID追踪面板，唯一提示Quest_121000040_ChildQuestTip_121_97对应回顾空Flow条目10，祖先162→152→1均为纯Sequence。两句洛瑟菈飞讯已按该提示归位。该消息原本已在附录，不是本轮新增发现的文本；最终共2任务3个手机区段25事件归位。

- 173000000消息36000虽有唯一回顾提示（entry0、节点2），但节点周围还有ChangeEntityState、FocusOnMapMark等未纳入本规则的动作。保留单列，诊断为unverified_surrounding_action_shape；不是声称没有任何锚点。
- 35000—35007的ReadPhoneMessage条件在另一个Type11任务192750006“短信成就检测”，属于ParallelSelect；不能借它排序主任务192000006节点64发送的八条消息。
- 34001、38005的读完节点没有唯一回顾提示；33003发送节点仅ReachArea条件。继续保留消息内部顺序，不推断主干位置。
- phone_tip_diagnostics为未放回的消息记录提示候选索引、原因、源节点和placement_verified=false。

## 保留：68次实体触发候选

31个任务/流程组合中23次显式Async=true，8次同步或省略Async。同步仅约束触发器自己的动作数组，未找到任务等待对应精确流程完成的配置，因此全部继续单列。

《远航星》可定位Awake/Destroy生命周期，但只能说明可触发窗口。圣者实体14/1有两次唤醒，不是唯一窗口；梦枢9/3里的10/1引用是Preload，不能认作执行/完成链；捕梦能源场1/41同步后有Wait，也不证明任务ReachArea节点55会等它完成。不得按区域、变量名或相邻ID补顺序。

## 其他修正与验证边界

external_inventory隔离解码会清空临时数组中其他动作。本轮新增original_following_actions，与既有original_preceding_actions/原索引共同保留真实调用上下文；临时隔离位置不作为排序证据。

新增测试覆盖唯一提示位置、同ID读取/追踪约束、异步及重复发送、跨节点来源、未知周围动作、消息已在回顾等拒绝条件，并核对真实任务23事件的源顺序、不重复展示和候选保留。

详细本地证据：work/round8_entity.md、work/round8_entity_evidence.json、work/round8_entity_probe.py、work/round8_phone.md、work/round8_anchors.md。最终验证统计见下节。


## 最终验证

第八轮三路核查完成：275项全量测试通过（114.123秒），批次20261117_124951_778402核对135对JSON/TXT。影面消息32000/32001及昨夜群星33006按唯一回顾提示归位，共2任务3区段25事件；非新增台词，不增加完整任务数。2634个原回顾流程段、27处阻塞、3段30事件前缀及68次实体候选保持。严格通过仍2，资产未动。

- 最新产物：outputs/主线批量/20261117_124951_778402/覆盖阅读版；产物核对.json记录三条插入位置，覆盖报告新增phone_tip_anchored、phone_tip_sections/events。
- 旧回顾segments逐对象相等，旧主干事件相等，27处阻塞报告完全相等；实体候选records全部相等。
- TXT与JSON渲染逐份一致，旧可见文本保留；每任务计数总和不变，已定位消息只在正文计数一次。
- 四个代表任务165800000、121000040、173000000、690000001各JSON/TXT，位于outputs/第八轮调用锚点核查。前两者展示归位结果，后两者展示仍单列的边界。
- 新增6项测试及既有隔离调用上下文测试通过。早期子agent接线测试因message_id/phone_message_id接口字段不一致出现KeyError，统一接口后复验通过；最终全量275项通过。未推送仓库或修改资产。

下一步核查36000已有提示锚点的周围动作，能证实再放回；缺少锚点的其他消息、无任务等待证据的实体触发继续保留单列。
