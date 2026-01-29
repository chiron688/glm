## 更新后的框架：COTA + Skills 融合架构

### 核心洞察：Skills 应该分层到两个系统中



```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         用户指令层                                           │
│  "上传视频到TikTok" / "养号1小时，垂直领域：美妆"                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 4: 任务编排层 (Orchestrator)                                          │
│  - 任务分解：将复杂任务拆分为原子操作序列                                      │
│  - Skills路由：根据任务类型加载对应的Skill包                                   │
│  - 状态监控：跟踪执行进度，决定何时唤醒系统2                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    双系统执行引擎 (COTA Core)                                │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐         │
│  │      系统2：慢思考层         │    │      系统1：快反应层         │         │
│  │   (VLM - 如Qwen-VL/GPT-4V)  │◄──►│  (轻量策略网络/快速模型)      │         │
│  │                             │    │                             │         │
│  │  • 语义理解（视频内容识别）   │    │  • 触控轨迹生成（贝塞尔曲线） │         │
│  │  • 复杂决策（异常处理）       │    │  • 微动作维持（活性保持）     │         │
│  │  • 长期规划（任务拆解）       │    │  • 即时反馈（滑动阻力响应）   │         │
│  │  • Skills加载（策略选择）     │    │  • 运动原语执行（点赞/滑动）  │         │
│  │                             │    │                             │         │
│  │  延迟：500ms-3s              │    │  延迟：<50ms                 │         │
│  │  采样率：0.5-1 fps           │    │  采样率：30 fps              │         │
│  └─────────────────────────────┘    └─────────────────────────────┘         │
│           ▲                                  │                              │
│           │      异步协同协议                 │                              │
│           │  • 系统2 → 系统1：宏观指令        │                              │
│           │  • 系统1 → 系统2：异常唤醒        │                              │
│           └──────────────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 2: Skills库 (分层设计)                                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Level 3: 异常恢复Skills (由系统2管理)                                │   │
│  │  • 弹窗处理Skill    • 网络错误Skill    • 验证码Skill    • UI变化Skill  │   │
│  │  触发条件：系统1检测到无法处理的异常 → 唤醒系统2 → 加载对应Skill      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Level 2: 任务流程Skills (系统2规划，系统1执行)                       │   │
│  │  • 上传视频Skill    • 养号浏览Skill    • 互动评论Skill    • 登录Skill  │   │
│  │  特点：包含"成功路径" + "检查点" + "降级策略"                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Level 1: 原子操作Skills (主要由系统1执行)                            │   │
│  │  • 滑动操作Skill    • 点击操作Skill    • 输入操作Skill    • 等待Skill  │   │
│  │  特点：拟人化轨迹、随机时延、混沌变量                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 1: 设备控制层                                                         │
│  • 投屏：scrcpy/minicap (低延迟 <50ms)                                       │
│  • 控制：ADB / minitouch / HID硬件模拟                                        │
│  • 云手机API集成                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

------

### Skills 的具体设计（融合COTA理念）

#### 1. 原子操作Skills（系统1层）



```python
# 滑动操作Skill - 拟人化轨迹生成
class SwipeSkill:
    def __init__(self):
        self.motion_primitives = {
            'fast_skip': {'duration': (150, 250), 'curve': 'ease_out'},      # 快速划走
            'slow_browse': {'duration': (400, 600), 'curve': 'ease_in_out'}, # 缓慢浏览
            'hesitate': {'duration': (800, 1200), 'curve': 'bezier'},        # 犹豫滑动
        }
    
    def execute(self, intent, start_pos, end_pos):
        """
        intent: 来自系统2的宏观意图 ("interested", "bored", "neutral")
        """
        primitive = self.select_primitive(intent)
        
        # 生成贝塞尔曲线轨迹 + 高斯噪声
        trajectory = generate_bezier_curve(
            start_pos, end_pos, 
            control_points=random.choice([1, 2, 3]),  # 随机控制点数量
            noise_level=0.02  # 微颤模拟
        )
        
        # 添加混沌变量：偶尔"误触"或"回滑"
        if random.random() < 0.05:  # 5%概率执行非理性行为
            trajectory = add_chaos_variation(trajectory)
        
        return execute_touch_sequence(trajectory, primitive['duration'])
```

#### 2. 任务流程Skills（系统2规划 + 系统1执行）



```yaml
# Skill: tiktok_upload_v2.yaml
skill_name: "tiktok_upload"
version: "2.0"
success_rate_target: 0.99

# 系统2的决策逻辑
planning:
  steps:
    - id: "open_app"
      action: "click"
      target: "tiktok_icon"
      check: "is_home_screen_visible"
      timeout: 10
      
    - id: "click_upload"
      action: "click"
      target: "plus_button"
      check: "is_upload_screen_visible"
      timeout: 10
      
    - id: "select_video"
      action: "select_video"
      params: {from_path: "{{video_path}}"}
      check: "is_video_preview_visible"
      timeout: 15
      
    - id: "add_caption"
      action: "input_text"
      target: "caption_field"
      params: {text: "{{generated_caption}}"}
      check: "text_entered"
      
    - id: "add_hashtags"
      action: "add_hashtags"
      params: {tags: "{{generated_hashtags}}"}
      
    - id: "publish"
      action: "click"
      target: "publish_button"
      check: "is_publish_success"
      timeout: 30

# 检查点定义（系统2验证）
checkpoints:
  - after: "select_video"
    verify: "video_duration_matches"
    on_fail: "retry_or_skip"
    
  - after: "publish"
    verify: "video_appears_on_profile"
    timeout: 60

# 异常处理映射（触发系统2）
exception_handlers:
  "popup_network_error":
    skill: "handle_network_error"
    priority: "high"
    
  "popup_storage_full":
    skill: "handle_storage_error"
    priority: "critical"
    
  "ui_element_not_found":
    skill: "adapt_ui_change"
    priority: "high"
    escalate_to: "strong_llm"  # 升级到大模型
```

#### 3. 异常恢复Skills（系统2专属）



```python
class ExceptionRecoverySkill:
    """
    当系统1遇到无法处理的异常时，唤醒系统2执行恢复
    """
    
    def handle(self, exception_type, screenshot, context):
        # 系统2进行语义分析
        analysis = self.vlm.analyze(
            image=screenshot,
            prompt=f"""
            分析当前界面状态，识别异常类型：{exception_type}
            历史操作：{context.action_history}
            
            请输出：
            1. 异常的具体描述
            2. 可能的恢复策略（1-3个选项）
            3. 推荐的下一步操作
            """
        )
        
        # 选择恢复策略
        recovery_plan = self.select_recovery_strategy(analysis)
        
        # 如果是未知异常，升级到大模型
        if recovery_plan.confidence < 0.7:
            return self.escalate_to_strong_llm(screenshot, context)
        
        # 执行恢复（通过系统1）
        return self.execute_recovery(recovery_plan)
```

------

### 异步协同的具体实现



```python
class COTACoordinator:
    """
    系统1和系统2的协调器
    """
    
    def __init__(self):
        self.system2 = VLMModel()  # 慢思考
        self.system1 = FastPolicyNetwork()  # 快反应
        self.state = "idle"
        
    async def run(self, task):
        # 系统2先进行任务规划
        plan = await self.system2.plan(task)
        
        for step in plan.steps:
            # 系统2下达宏观指令
            intent = await self.system2.get_intent(step)
            
            # 系统1执行具体动作
            while True:
                # 系统1以高帧率运行
                observation = await self.get_observation()
                
                # 检查是否需要唤醒系统2
                if self.need_system2(observation, intent):
                    # 异常情况：唤醒系统2
                    recovery = await self.system2.handle_exception(
                        observation, self.system1.get_state()
                    )
                    intent = recovery.new_intent
                
                # 系统1执行动作
                action = self.system1.act(observation, intent)
                await self.execute_action(action)
                
                # 检查步骤完成
                if self.step_completed(observation, step):
                    break
                
                # 微动作维持活性
                await self.system1.maintain_liveness()
    
    def need_system2(self, observation, intent):
        """
        判断是否需要唤醒系统2
        """
        # 情况1：遇到未知UI元素
        if observation.has_unknown_element():
            return True
        
        # 情况2：操作失败（点击无响应）
        if observation.last_action_failed():
            return True
        
        # 情况3：出现弹窗
        if observation.has_popup():
            return True
        
        # 情况4：长期任务需要重新规划
        if self.should_replan():
            return True
        
        return False
```

------

### 针对你场景的优化建议

#### 1. 养号任务的上下文管理（解决长上下文问题）



```python
class NurturingSession:
    """
    养号任务采用"切片 + 记忆"模式
    """
    
    def __init__(self, duration_minutes, persona):
        self.duration = duration_minutes
        self.persona = persona
        self.memory = VectorDatabase()  # 长期记忆
        
    async def run(self):
        # 将长任务切分为短片段
        segments = self.create_segments(self.duration)
        
        for segment in segments:
            # 每个片段独立执行，避免上下文爆炸
            context = {
                'persona': self.persona,
                'memory': self.memory.retrieve_relevant(),  # 只加载相关记忆
                'segment_goal': segment.goal
            }
            
            # 执行片段
            result = await self.execute_segment(context)
            
            # 更新记忆
            self.memory.add(result.key_observations)
            
            # 定期清空短期上下文
            self.system2.clear_short_term_memory()
```

#### 2. 上传任务的100%成功率保障



```python
class ReliableUploader:
    """
    三层保障机制
    """
    
    async def upload(self, video_path, metadata):
        # 第1层：确定性Skills执行
        for attempt in range(3):
            result = await self.skill_executor.execute(
                skill="tiktok_upload_v2",
                params={"video": video_path, **metadata}
            )
            
            if result.status == "SUCCESS":
                return result
            
            # 第2层：系统2异常恢复
            if result.status == "EXCEPTION":
                recovery = await self.system2.recover(result)
                if recovery.should_continue:
                    continue
            
            # 第3层：大模型兜底
            if attempt == 2:
                return await self.strong_llm_rescue(result)
        
        # 最终失败：人工介入
        return await self.human_escalation()
```

------

### 技术栈推荐（基于COTA报告）



| 组件               | 推荐方案                   | 说明                   |
| :----------------- | :------------------------- | :--------------------- |
| **系统2 (VLM)**    | Qwen2.5-VL-7B / GPT-4o     | 本地化部署，INT4量化   |
| **系统1 (快反应)** | 自研策略网络 / AutoGLM底层 | 模仿学习训练           |
| **投屏**           | scrcpy / minicap           | <50ms延迟              |
| **控制**           | minitouch + HID硬件        | 绕过ADB检测            |
| **Skills管理**     | 自研 + MCP协议             | 标准化接口             |
| **记忆**           | ChromaDB / Pinecone        | 向量存储               |
| **基座**           | GELab-Zero                 | 开源，已解决多设备调度 |

------

### 实施路线图



```
Phase 1: 基础验证 (2-4周)
├── 搭建GELab-Zero基座
├── 验证VLM对TikTok内容的识别准确率
├── 跑通"截图-理解-动作"闭环
└── 验证单机单账号养号效果

Phase 2: 双系统融合 (4-6周)
├── 实现系统1的快反应模块
├── 训练运动原语（滑动/点击/长按）
├── 实现异步协同协议
└── 添加微动作/混沌变量

Phase 3: Skills体系 (4-6周)
├── 设计Skills分层架构
├── 实现异常恢复Skills
├── 建立Skills迭代机制
└── 集成大模型兜底

Phase 4: 规模化 (持续)
├── GPU集群部署
├── 多设备并发控制
├── 自动化流水线
└── 持续优化成功率
```

------

### 总结

COTA架构给你的Skills方案带来了**三个关键升级**：

1. **执行层升级**：从单一的LLM调用，变为"慢思考+快反应"双系统，解决了延迟和拟人化问题
2. **Skills分层**：将Skills按执行速度分层，原子操作给系统1，异常恢复给系统2
3. **活性维持**：通过微动作和混沌变量，有效规避TikTok的行为风控