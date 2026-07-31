/* ========================================
   每日深度思辨 —— 思辨对话系统
   ======================================== */

const Dialogue = {
  event: null,
  currentPhase: 0,
  currentStep: 0,
  messages: [],
  isProcessing: false,
  mode: 'local',
  noteShown: false,

  init(event) {
    this.event = event;
    this.currentPhase = 0;
    this.currentStep = 0;
    this.messages = [];
    this.isProcessing = false;
    this.noteShown = false;

    this.detectBackend();
    this.render();
    setTimeout(() => this.nextPhase(), 600);
  },

  async detectBackend() {
    try {
      const resp = await fetch('http://localhost:8765/api/health', {
        signal: AbortSignal.timeout(2000)
      });
      if (resp.ok) {
        this.mode = 'api';
      }
    } catch {
      this.mode = 'local';
    }
  },

  render() {
    const tabContents = document.getElementById('tab-contents');
    const phases = this.event.dialogue.phases;
    const totalPhases = phases.length;

    // 阶段指示器 dots
    const dotsHtml = Array.from({length: totalPhases}, (_, i) =>
      `<span class="phase-dot${i === 0 ? ' active' : ''}"></span>`
    ).join('');

    tabContents.innerHTML = `
      <div class="tab-content active dialogue-view">
        <div class="dialogue-container">
          <div class="dialogue-header">
            <div class="dialogue-header-left">
              <span style="font-size: 16px;">&#x1F3DB;</span>
              <span class="dialogue-title">思辨对话</span>
            </div>
            <div class="phase-indicator" id="phase-dots">
              ${dotsHtml}
            </div>
          </div>

          <div class="dialogue-messages" id="dialogue-messages">
            <div style="text-align: center; padding: var(--space-lg); color: var(--ink-light); font-size: 13px; font-family: var(--font-display);">
              对话即将开始...
            </div>
          </div>

          <div class="dialogue-input-area">
            <div class="dialogue-actions">
              <button class="dialogue-action-btn" id="btn-new-angle" disabled>换个角度</button>
              <button class="dialogue-action-btn" id="btn-generate-note" disabled>生成今日笔记</button>
            </div>
            <div class="dialogue-input-wrapper">
              <textarea
                class="dialogue-input"
                id="dialogue-input"
                placeholder="输入你的思考..."
                rows="1"
                disabled
              ></textarea>
              <button class="dialogue-send" id="btn-send" disabled>
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M2 2l12 6-12 6 3-6-3-6z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    // 绑定事件
    this.bindEvents();
  },

  bindEvents() {
    const input = document.getElementById('dialogue-input');
    const sendBtn = document.getElementById('btn-send');

    sendBtn.addEventListener('click', () => this.sendMessage());

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // 自适应高度
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    document.getElementById('btn-generate-note').addEventListener('click', () => {
      this.generateNote();
    });
  },

  // 进入下一阶段
  async nextPhase() {
    if (this.isProcessing) return;
    this.isProcessing = true;

    const phases = this.event.dialogue.phases;
    if (this.currentPhase >= phases.length) {
      this.isProcessing = false;
      return;
    }

    this.currentStep = 0;
    this.updatePhaseIndicator();

    // 获取当前阶段的系统消息（远程中转优先，无中转用预置）
    let msg = null;
    if (this.currentPhase === 0) {
      // 第一阶段：用 startDialogue（远程优先）
      msg = await DataAPI.startDialogue(this.event.id, 1);
    } else {
      // 后续阶段：预置对话（respondDialogue 在用户回答后调用）
      const phaseData = phases[this.currentPhase];
      msg = phaseData ? phaseData.messages[0] : null;
    }

    if (!msg) {
      this.isProcessing = false;
      this.finishDialogue();
      return;
    }

    // 显示系统消息
    await this.showSystemMessage(msg);
    this.currentPhase++;

    // 最后一个阶段（总结）不需要用户输入
    if (this.currentPhase >= phases.length) {
      this.enableInput(false);
      setTimeout(() => this.finishDialogue(), 1200);
    } else {
      this.enableInput(true);
    }
    this.isProcessing = false;
  },

  // 对话完成：自动生成笔记
  finishDialogue() {
    if (!this.noteShown) {
      this.noteShown = true;
      setTimeout(() => this.generateNote(), 800);
    }
  },

  async showSystemMessage(msg) {
    // 添加消息到列表
    this.messages.push({ role: 'system', text: msg.text, classical: msg.classical });

    const container = document.getElementById('dialogue-messages');

    // 移除"对话即将开始"
    if (container.querySelector('div')) {
      const placeholder = container.querySelector('div[style]');
      if (placeholder && !container.querySelector('.message')) {
        placeholder.remove();
      }
    }

    // 显示"思考中"
    const typingEl = document.createElement('div');
    typingEl.className = 'message system';
    typingEl.innerHTML = `
      <div class="message-avatar">思</div>
      <div class="message-bubble">
        <div class="message-typing">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;
    container.appendChild(typingEl);
    this.scrollToBottom();

    // 模拟思考延迟
    await delay(this.mode === 'api' ? 2000 : 1000);

    // 替换为真实消息
    typingEl.remove();

    // 渲染真实消息
    let msgHtml = `
      <div class="message system">
        <div class="message-avatar">思</div>
        <div class="message-bubble">
          <p>${msg.text}</p>
    `;

    if (msg.classical) {
      msgHtml += `
          <div class="message-classical">
            <div class="quote-text">${msg.classical.quote}</div>
            <div class="quote-source">—— ${msg.classical.source}</div>
          </div>
      `;
    }

    msgHtml += `
        </div>
      </div>
    `;

    container.insertAdjacentHTML('beforeend', msgHtml);
    this.scrollToBottom();
  },

  async sendMessage() {
    if (this.isProcessing) return;

    const input = document.getElementById('dialogue-input');
    const text = input.value.trim();
    if (!text) return;

    // 添加用户消息
    this.messages.push({ role: 'user', text });

    const container = document.getElementById('dialogue-messages');
    const userMsg = document.createElement('div');
    userMsg.className = 'message user';
    userMsg.innerHTML = `
      <div class="message-avatar">你</div>
      <div class="message-bubble">
        <p>${this.escapeHtml(text)}</p>
      </div>
    `;
    container.appendChild(userMsg);
    this.scrollToBottom();

    // 清空输入
    input.value = '';
    input.style.height = 'auto';
    this.enableInput(false);

    // 请求系统回应（远程中转优先，无中转用预置下一阶段）
    const response = await DataAPI.respondDialogue(
      this.event.id,
      this.currentPhase,   // 当前已完成阶段数（即下一阶段索引）
      text,
      this.messages.map(m => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text }))
    );

    if (response && response.text) {
      // 显示思考中动画
      const container = document.getElementById('dialogue-messages');
      const typingEl = document.createElement('div');
      typingEl.className = 'message system';
      typingEl.innerHTML = `
        <div class="message-avatar">思</div>
        <div class="message-bubble">
          <div class="message-typing"><span></span><span></span><span></span></div>
        </div>
      `;
      container.appendChild(typingEl);
      this.scrollToBottom();

      await delay(response.fromApi ? 2500 : 900);

      // 替换为真实回应
      typingEl.remove();
      await this.showSystemMessage({ role: 'system', text: response.text, classical: null });
      this.currentPhase++;
    } else {
      // 没有更多内容（对话结束）
      this.finishDialogue();
      return;
    }

    // 更新阶段指示器
    this.updatePhaseIndicator();

    // 判断对话是否完成
    const phases = this.event.dialogue.phases;
    if (this.currentPhase >= phases.length) {
      this.enableInput(false);
      setTimeout(() => this.finishDialogue(), 800);
    } else {
      this.enableInput(true);
    }
  },

  enableInput(enabled) {
    const input = document.getElementById('dialogue-input');
    const sendBtn = document.getElementById('btn-send');
    const noteBtn = document.getElementById('btn-generate-note');

    if (input) {
      input.disabled = !enabled;
      input.placeholder = enabled ? '输入你的思考...' : '思辨者正在思考...';
    }
    if (sendBtn) sendBtn.disabled = !enabled;
    if (noteBtn) noteBtn.disabled = !enabled;
  },

  updatePhaseIndicator() {
    const dots = document.querySelectorAll('#phase-dots .phase-dot');
    dots.forEach((dot, i) => {
      dot.classList.remove('active', 'done');
      if (i < this.currentPhase) dot.classList.add('done');
      if (i === this.currentPhase) dot.classList.add('active');
    });
  },

  async generateNote() {
    if (this.isProcessing) return;

    // 从mock数据获取笔记
    const note = this.event.dialogue.note;
    this.showNoteModal(note);
  },

  showNoteModal(note) {
    // 移除旧modal
    const old = document.querySelector('.note-overlay');
    if (old) old.remove();

    const overlay = document.createElement('div');
    overlay.className = 'note-overlay';
    overlay.innerHTML = `
      <div class="note-modal">
        <div class="note-modal-header">
          <span class="note-modal-title">今日思辨笔记</span>
          <button class="note-modal-close" id="btn-close-note">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M2 2l10 10M12 2l-10 10"/>
            </svg>
          </button>
        </div>

        <div class="note-section">
          <div class="note-section-title">核心命题</div>
          <div class="note-section-content">${note.coreProposition}</div>
        </div>

        <div class="note-section">
          <div class="note-section-title">主流观点扫描</div>
          <div class="note-section-content">${note.mainstreamView}</div>
        </div>

        <div class="note-section">
          <div class="note-section-title">另类视角</div>
          <div class="note-section-content">${note.alternativeView}</div>
        </div>

        <div class="note-section">
          <div class="note-section-title">学科视角荟萃</div>
          <div class="note-section-content">${note.multidisciplinaryInsight}</div>
        </div>

        <div class="note-section">
          <div class="note-section-title">我的判断</div>
          <div class="note-section-content">${note.personalJudgment}</div>
        </div>

        <div class="note-section">
          <div class="note-section-title">行动启示</div>
          <div class="note-section-content">${note.actionTakeaway}</div>
        </div>

        <div class="note-modal-footer">
          <button class="btn btn-secondary" id="btn-close-note2">关闭</button>
          <button class="btn btn-primary" id="btn-copy-note">复制笔记</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    // 关闭事件
    const closeModal = () => overlay.remove();
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal();
    });
    overlay.querySelector('#btn-close-note').addEventListener('click', closeModal);
    overlay.querySelector('#btn-close-note2').addEventListener('click', closeModal);

    // 复制
    overlay.querySelector('#btn-copy-note').addEventListener('click', () => {
      const noteText = this.formatNoteText(note);
      navigator.clipboard.writeText(noteText).then(() => {
        const btn = overlay.querySelector('#btn-copy-note');
        btn.textContent = '已复制';
        setTimeout(() => btn.textContent = '复制笔记', 2000);
      });
    });
  },

  formatNoteText(note) {
    return `【今日思辨笔记】${new Date().toLocaleDateString('zh-CN')}

━━━ 核心命题 ━━━
${note.coreProposition}

━━━ 主流观点扫描 ━━━
${note.mainstreamView}

━━━ 另类视角 ━━━
${note.alternativeView}

\u2501\u2501\u2501 学科视角荟萃 \u2501\u2501\u2501
${note.multidisciplinaryInsight}

\u2501\u2501\u2501 我的判断 \u2501\u2501\u2501
${note.personalJudgment}

━━━ 行动启示 ━━━
${note.actionTakeaway}

---
生成自：每日深度思辨 · AI产品经理思维训练工具`;
  },

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  scrollToBottom() {
    const container = document.getElementById('dialogue-messages');
    if (container) {
      setTimeout(() => {
        container.scrollTop = container.scrollHeight;
      }, 100);
    }
  }
};
